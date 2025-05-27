import numpy as np
import pandas as pd
import matplotlib.dates as mdates
from matplotlib.figure import Figure

def get_plot(data, var1, plot_type, var2=None):
    # Prepare Data
    if var2 is not None:
        df = data[[var1, var2]].dropna()
        x = df[var1]
        y = df[var2]
    else:
        x = data[var1].dropna()
        y = None

    # Coerce Numeric Columns to Numeric (If Not Already)
    if plot_type in ['histogram', 'density', 'boxplot', 'scatter']:
        x = pd.to_numeric(x, errors='coerce')
    if y is not None and plot_type in ['violin', 'scatter', 'line']:
        y = pd.to_numeric(y, errors='coerce')
    # For Heatmap, if more than 75% of values can be converted to numeric, treat it as numeric
    if plot_type in ['heatmap']:
        coerced_x = pd.to_numeric(x, errors='coerce')
        if coerced_x.notna().sum() / len(x) >= 0.75:
            x = coerced_x.dropna()
        coerced_y = pd.to_numeric(y, errors='coerce')
        if coerced_y.notna().sum() / len(y) >= 0.75:
            y = coerced_y.dropna()
    
    # Coerce DateTime Columns to DateTime (If Not Already)
    if plot_type == 'line':
        coerced_x = pd.to_datetime(x, errors='coerce', infer_datetime_format=True)
        if coerced_x.notna().sum() / len(x) >= 0.75:
            x = coerced_x.dropna()

    # Dynamic Graph Size (Depending on Number of Categorical Points)
    x_unique = len(x.unique()) if not pd.api.types.is_numeric_dtype(x) else 1
    y_unique = len(y.unique()) if (y is not None and not pd.api.types.is_numeric_dtype(y)) else 1
    width = max(6, min(20, x_unique * 0.6))
    height = max(4, min(15, y_unique * 0.5))
    if x_unique == 1 and y_unique != 1:
        width = height * 1.5
    elif y_unique == 1 and x_unique != 1:
        height = width / 1.5
    fig = Figure(figsize=(width, height))
    ax = fig.subplots()

    if plot_type == 'histogram':
        ax.hist(x, bins=30, color='blue', alpha=0.7)
        ax.set_title(f'Histogram of {var1}')
        ax.set_xlabel(var1)
        ax.set_ylabel('Frequency')

    elif plot_type == 'density':
        counts, bins, _ = ax.hist(x, bins=50, density=True, alpha=0.0)
        bin_centers = 0.5 * (bins[:-1] + bins[1:])
        ax.plot(bin_centers, counts, color='purple')
        ax.set_title(f'Density Plot of {var1}')
        ax.set_xlabel(var1)
        ax.set_ylabel('Density')

    elif plot_type == 'barchart':
        counts = x.value_counts()
        ax.bar(counts.index.astype(str), counts.values, color='green', alpha=0.7)
        ax.set_title(f'Bar Chart of {var1}')
        ax.set_xlabel(var1)
        ax.set_ylabel('Count')
        ax.tick_params(axis='x', rotation=45)

    elif plot_type == 'piechart':
        counts = x.value_counts()
        ax.pie(counts.values, labels=counts.index.astype(str), autopct='%1.1f%%')
        ax.set_title(f'Pie Chart of {var1}')

    elif plot_type == 'boxplot':
        # Boxplot for 1 Numeric Var
        if var2 is None:
            ax.boxplot(x.dropna(), vert=True)
            ax.set_title(f'Boxplot of {var1}')
            ax.set_ylabel(var1)
            ax.set_xticks([])
        # Boxplot for Numeric Var, across Categories
        else:
            grouped = [x[y == cat].dropna() for cat in y.dropna().unique()]
            ax.boxplot(grouped, labels=y.dropna().unique())
            ax.set_title(f'Boxplot of {var1} by {var2}')
            ax.set_xlabel(var2)
            ax.set_ylabel(var1)
            ax.tick_params(axis='x', rotation=45)

    elif plot_type == 'violin':
        grouped = [y[x == cat] for cat in x.unique()]
        ax.violinplot(grouped, showmeans=False, showmedians=True)
        ax.set_xticks(range(1, len(grouped) + 1))
        ax.set_xticklabels(x.unique())
        ax.set_title(f'Violin Plot of {var2} by {var1}')
        ax.set_xlabel(var1)
        ax.set_ylabel(var2)
        ax.tick_params(axis='x', rotation=45)

    elif plot_type == 'scatter':
        ax.scatter(x, y, alpha=0.7)
        ax.set_title(f'Scatter Plot of {var1} vs {var2}')
        ax.set_xlabel(var1)
        ax.set_ylabel(var2)

    elif plot_type == 'line':
        grouped = df.groupby(x)[var2].mean()
        x_vals = grouped.index
        y_vals = grouped.values
        ax.plot(x_vals, y_vals)
        ax.set_title(f'Line Plot of {var2} by {var1}')
        ax.set_xlabel(var1)
        ax.set_ylabel(var2)

        # Max 15 Labels
        format_linegraph_xaxis(ax, x_vals)
        ax.tick_params(axis='x', rotation=45)
        

    elif plot_type == 'heatmap':
        if pd.api.types.is_numeric_dtype(y):
            y_binned = pd.cut(y, bins=10)
            y_labels = [f"{interval.left:.2f} - {interval.right:.2f}" for interval in y_binned.cat.categories]
            pivot = pd.crosstab(y_binned, x)
            im = ax.imshow(pivot, cmap='Blues')
            fig.colorbar(im, ax=ax)
            ax.set_xticks(np.arange(len(pivot.columns)))
            ax.set_yticks(np.arange(len(pivot.index)))
            ax.set_xticklabels(pivot.columns, rotation=45)
            ax.set_yticklabels(y_labels)
            ax.set_xlabel(var1)
            ax.set_ylabel(var2)
            ax.set_title(f'Heatmap of Binned {var2} vs {var1}')

        else:
            pivot = pd.crosstab(y, x)
            im = ax.imshow(pivot, cmap='Blues')
            fig.colorbar(im, ax=ax)
            ax.set_xticks(np.arange(len(pivot.columns)))
            ax.set_yticks(np.arange(len(pivot.index)))
            ax.set_xticklabels(pivot.columns, rotation=45)
            ax.set_yticklabels(pivot.index)
            ax.set_title(f'Heatmap of {var2} vs {var1}')

        ax.set_xlabel(var1)
        ax.set_ylabel(var2)

    else:
        raise ValueError(f"Unsupported plot type: {plot_type}")

    fig.tight_layout()
    return fig


def format_linegraph_xaxis(ax, x_vals, max_labels=15):
    n = len(x_vals)
    step = max(1, n // max_labels)
    ticks = range(0, n, step)
    ax.set_xticks([x_vals[i] for i in ticks])

    if pd.api.types.is_datetime64_any_dtype(x_vals):
        dates = pd.to_datetime(x_vals)
        years = len(dates.year.unique())
        months = len(dates.month.unique())
        days = len(dates.day.unique())

        if days == 1 and months == 1 and years == 1:
            # If Same Day, Show HH:MM
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        elif years == 1:
            # If Same Year, Show DD-MM HH:MM
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        else:
            # Else, Show full Date
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
    else:
        ax.set_xticklabels([str(x_vals[i]) for i in ticks])

    ax.tick_params(axis='x', rotation=45)