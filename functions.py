import pandas as pd
import io
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sqlite3
import os


def read_data(file_path):
    ext = os.path.splitext(file_path)[1].lower()

    # Read CSV Files
    if ext == '.csv':
        return pd.read_csv(file_path)

    # Read SQLite Files
    elif ext in ['.sqlite', '.sqlite3', '.db']:
        conn = sqlite3.connect(file_path)
        table = conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchone()[0]
        df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
        conn.close()
        return df
    
    # Return Error if Unsupported File Type
    else:
        raise ValueError(f"Unsupported File Type: {ext}")
    

def get_general_summary(series):
    # Get Data Type
    col_summary = {'Data Type': str(series.dtype)}
    # Get Number of Unique Values
    num_unique = series.nunique(dropna=True)
    col_summary['Unique Values'] = f'{num_unique} (Out of {len(series)})'
    # Get Number of "Missing Values"
    uppercase_series = series.astype(str).str.strip().str.lower()
    MISSING_VALUES = ['NONE', 'NIL', 'NA', 'NULL', 'N/A', '', ' ']
    missing = {}
    for value in MISSING_VALUES:
        count = (uppercase_series == value).sum()
        if count > 0:
            missing[value] = count
    if series.isna().sum() > 0:
        missing['NA'] = series.isna().sum()
    missing_count = sum(missing.values())
    missing_percentage = round(missing_count / len(series) * 100, 4)
    col_summary['Missing Values'] = missing or 0
    if missing_percentage > 0:
        col_summary['Missing Values (%)'] = f'{missing_percentage}% ({missing_count} of {len(series)})'
    
    return col_summary


def update_binary_summary(series, col_summary):
    col_summary['Recommendation'] = "Convert to Binary Column"
    # Get Count of Each Variable 
    col_summary['Value Counts (Binary)'] = {
        str(k): f"{v} ({(v / len(series) * 100):.2f}%)" for k, v in series.value_counts().items()
    }


def update_numeric_summary(numeric_series, col_summary):
    zero_count = numeric_series.eq(0).sum()
    if zero_count:
        col_summary['Zero'] = int(zero_count)
    q1 = numeric_series.quantile(0.25)
    q3 = numeric_series.quantile(0.75)
    mean = round(numeric_series.mean(), 4)
    median = numeric_series.median()
    sd = round(numeric_series.std(), 4)
    minimum, maximum = numeric_series.min(), numeric_series.max()
    iqr = q3 - q1
    outliers_count = numeric_series[(numeric_series < q1 - 1.5 * iqr) | (numeric_series > q3 + 1.5 * iqr)].count()
    
    if not pd.isna(mean):
        col_summary['Mean'] = float(mean)
    if not pd.isna(median):
        col_summary['Median']= float(median)
    if pd.notna(minimum) and pd.notna(maximum):
        col_summary['Range'] = f'{float(minimum)} - {float(maximum)}'
    if not pd.isna(sd):
        col_summary['Standard Deviation']= float(sd)
    if not pd.isna(q1):
        col_summary['Lower Quartile'] = float(q1)
    if not pd.isna(q3):
        col_summary['Upper Quartile'] = float(q3)
    if outliers_count:
        col_summary['Outlier Count (1.5x IQR)'] = int(outliers_count)


def update_categorical_summary(series, col_summary):
    categories = series.dropna().unique()

    # Sort Categories
    categories = sorted(map(str, categories))
    categories = ', '.join(categories)

    # Show Categories (Max String Length of 300)
    if len(categories) > 300:
        categories = categories[:300] + '...'
    col_summary['Categories'] = categories

    # Get Top Categories
    top_categories = series.value_counts().head(10)
    col_summary['Top Categories'] = {
        str(k): f"{v} ({(v / len(series) * 100):.2f}%)" for k, v in top_categories.items()
    }


def update_datetime_summary(date_series, col_summary):
    # Extract Date and Time Separately
    dates = date_series.dt.date
    times = date_series.dt.time

    unique_dates = dates.unique()

    # If No Date, return Time Range
    if len(unique_dates) == 1 and unique_dates[0] == pd.Timestamp.today().date():
        min_time = min(times)
        max_time = max(times)
        col_summary['Time Range'] = f"{min_time} to {max_time}"
    # Else, return Day Range
    else:
        min_date = min(dates)
        max_date = max(dates)
        col_summary['Date Range'] = f"{min_date} to {max_date}"


def plot_distribution(series, col_summary, num_unique):
    # Histogram
    plt.figure(figsize=(8,4))
    hist_ax = series.plot(kind='hist', bins=min(15, num_unique), edgecolor='black')
    hist_ax.xaxis.get_major_formatter().set_scientific(False)
    hist_ax.xaxis.get_major_formatter().set_useOffset(False)
    plt.xlabel('Value')
    plt.ylabel('Frequency')
    for patch in hist_ax.patches:
        height = patch.get_height()
        x = patch.get_x() + patch.get_width() / 2
        hist_ax.text(x, height, f'{int(height)}', ha='center', va='bottom', fontsize=7)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close()
    buf.seek(0)
    img_base64_hist = base64.b64encode(buf.read()).decode('utf-8')
    col_summary['Distribution (Histogram)'] = f'<img src="data:image/png;base64,{img_base64_hist}">'

    # Boxplot
    plt.figure(figsize=(4,6))
    box_ax = series.plot(kind='box', vert=True, patch_artist=True, notch=True)
    box_ax.yaxis.get_major_formatter().set_scientific(False)
    box_ax.yaxis.get_major_formatter().set_useOffset(False)
    plt.ylabel('Value')
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close()
    buf.seek(0)
    img_base64_box = base64.b64encode(buf.read()).decode('utf-8')
    col_summary['Distribution (Boxplot)'] = f'<img src="data:image/png;base64,{img_base64_box}">'

def get_column_summary(df, col):
    series = df[col]

    # Thresholds for Conversion
    CATEGORY_THRESHOLD = min(100, len(series) / 100)
    NUMERIC_THRESHOLD = 95
    DATETIME_THRESHOLD = 95

    # Get General Summary
    col_summary = get_general_summary(series)
    num_unique = series.nunique(dropna=True)

    # If Constant Column
    if num_unique == 1:
        col_summary['Recommendation'] = "Constant Column, can be removed"
        return col_summary

    # If Binary Column, update Col Summary with Binary Summary
    if num_unique == 2:
        update_binary_summary(series, col_summary)
        return col_summary

    # If Index Column
    if num_unique == len(series):
        col_summary['Recommendation'] = "Index Column (Every row has unique value)"
        return col_summary

    # If Numerical Column or should be Parsed to Numerical Column, get Numeric Summary
    numeric_series = pd.to_numeric(series, errors='coerce')
    numeric_percentage = round(numeric_series.notna().sum() / len(series) * 100, 4)
    if numeric_percentage >= NUMERIC_THRESHOLD or pd.api.types.is_numeric_dtype(series):
        # Update Col Summary with Numeric Summary
        update_numeric_summary(numeric_series, col_summary)
        
        # Get Distribution Graphs
        plot_distribution(numeric_series, col_summary, num_unique)

        # If Numerical values are more than threshold, recommend to parse to Numerical
        if not pd.api.types.is_numeric_dtype(series):
            col_summary['Recommendation'] = f'Convert to Numeric Variable ({numeric_percentage}% can be converted)'

    # If Categorical Column or should be Parsed to Categorical Column, get Categorical Summary
    if series.dtype == 'object' and num_unique <= CATEGORY_THRESHOLD:
        update_categorical_summary(series, col_summary)

        # Recommend to parse to Categorical
        col_summary['Recommendation'] = f'Convert to Categorical Variable'

    # Check if DateTime Variable
    date_series = pd.to_datetime(series, errors='coerce')
    date_percentage = round(date_series.notna().sum() / len(series) * 100, 4)
    if series.dtype == 'object' and date_percentage > DATETIME_THRESHOLD:
        # Update Col Summary with DateTime Summary
        update_datetime_summary(date_series, col_summary)

        # Recommend to parse to DateTime
        col_summary.pop('Recommendation', None)
        col_summary['Recommendation'] = f'Convert to DateTime Variable ({date_percentage}% can be converted)'

    return col_summary