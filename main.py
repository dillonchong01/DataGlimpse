from flask import Flask, render_template, request, redirect, url_for, session, send_file
import math
import os
import io
import sqlite3
import base64
from flask_caching import Cache
from summary_functions import read_data, get_column_summary, get_dataframe_summary
from editing_functions import apply_edits
from plotting_functions import get_plot

app = Flask(__name__)
app.secret_key = 'unique'

# Initialize Temporary Folder to Store Files
UPLOAD_FOLDER = 'temp'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Clear Data in Temporary Folder
for filename in os.listdir(UPLOAD_FOLDER):
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.isfile(file_path) or os.path.islink(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')

allowed_extensions = {'.csv', '.sqlite', '.sqlite3', '.db'}

def allowed_file(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext in allowed_extensions

# Function to get Uploaded Dataframe from Cache, else read
def get_uploaded_dataframe():
    if 'uploaded_file' not in session:
        return None, redirect(url_for('upload_file')), None
    
    filename = session.get('uploaded_file')
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    
    if not os.path.exists(file_path):
        return None, ("File Not Found", 404), None

    # Attempt to Read Data of Uploaded File
    df = cache.get(filename)
    if df is None:
        try:
            df = read_data(file_path)
        except Exception as e:
            return None, (f"Error reading file: {str(e)}", 400), None
        cache.set(filename, df, timeout=3600)

    return df, None, filename


# Initialize Cache
cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache'})


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    # Check if Request was Posted
    if request.method == 'POST':
        file = request.files.get('file')
        if not file:
            return "No File Uploaded", 400
        if not allowed_file(file.filename):
            return "Unsupported File Type", 400

        # Generate and Save File to Temporary Folder
        ext = os.path.splitext(file.filename)[1].lower()
        filename = f'uploaded_file{ext}'
        file_path = os.path.join(UPLOAD_FOLDER, filename)

        # Clear Cache if Old File Exists
        cached_df = cache.get(filename)
        if cached_df is not None and not cached_df.empty:
            cache.delete(filename)

        file.save(file_path)
        session['uploaded_file'] = filename

        return redirect(url_for('view_data', page=1))

    # If no request posted, show Upload Page
    return render_template('index.html')


@app.route('/data/page/<int:page>')
def view_data(page=1):
    # Get Dataframe from Cache
    df, error, _ = get_uploaded_dataframe()
    if error:
        return redirect(url_for('upload_file'))

    # Loads 100 Rows per Page
    page_size = 100
    total_pages = math.ceil(len(df) / page_size)

    # Return to Page 1 if Out of Bounds
    if page < 1 or page > total_pages:
        return redirect(url_for('view_data', page=1))

    start = (page - 1) * page_size
    end = start + page_size
    page_data = df.iloc[start:end]

    return render_template(
        'page.html',
        page_data=page_data.to_dict(orient='records'),  # pass list of dicts for rows
        page=page,  # current page number
        total_pages=total_pages,
        columns=list(df.columns)
    )


@app.route('/summary/<column>')
def column_summary(column):
    # Get Dataframe from Cache
    df, error, _ = get_uploaded_dataframe()
    if error:
        return redirect(url_for('upload_file'))
    
    # Get Previous Page
    from_page = request.args.get('from', 'view')

    try:
        summary = get_column_summary(df, column)
    except Exception as e:
        return f"Error Processing Summary: {str(e)}", 400

    return render_template('summary.html', column=column, summary=summary, from_page=from_page, is_col=True)


@app.route('/general_summary/')
def general_summary():
    # Get Dataframe from Cache
    df, error, _ = get_uploaded_dataframe()
    if error:
        return redirect(url_for('upload_file'))

    # Get Previous Page
    from_page = request.args.get('from', 'view')

    try:
        summary = get_dataframe_summary(df)
    except Exception as e:
        return f"Error Processing Summary: {str(e)}", 400

    return render_template('summary.html', column='dataframe', summary=summary, from_page=from_page, is_col=False)


@app.route('/edit', methods=['GET', 'POST'])
def edit_data():
    # Get Dataframe from Cache
    df, error, filename = get_uploaded_dataframe()
    if error:
        return redirect(url_for('upload_file'))
    
    if request.method == 'POST':
        df, log_text = apply_edits(df, request.form)
        cache.set(filename, df, timeout=3600)

        # Append log_text to File
        log_path = os.path.join(UPLOAD_FOLDER, 'edit_logs.txt')
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(log_text + "\n")

        return redirect(url_for('view_data', page=1))
    
    # Get Number of Unique Values per Column
    unique_values_map = {
        col: df[col].dropna().nunique() for col in df.columns
    }
    # Get Column Datatypes
    dtypes_map = {col: str(dtype) for col, dtype in df.dtypes.items()}

    return render_template('edit.html',
                           columns=list(df.columns),
                           unique_values_map=unique_values_map,
                           dtypes_map=dtypes_map)


@app.route('/eda', methods=['GET', 'POST'])
def eda():
    df, error, _ = get_uploaded_dataframe()
    if error:
        return redirect(url_for('upload_file'))

    columns = list(df.columns)

    # Variable Counts for each Plot Type
    plot_var_counts = {
        'histogram': 1,
        'density': 1,
        'barchart': 1,
        'piechart': 1,
        'boxplot': [1, 2],
        'violin': 2,
        'scatter': 2,
        'line': 2,
        'heatmap': 2
    }

    plot_type = request.form.get('plot_type')
    var1 = request.form.get('var1')
    var2 = request.form.get('var2')
    var_count = plot_var_counts.get(plot_type) if plot_type else None

    fig = None
    if plot_type and var1:
        if var_count == 1:
            fig = get_plot(df, var1, plot_type)
        elif isinstance(var_count, list) and 2 in var_count:
            if var2:
                fig = get_plot(df, var1, plot_type, var2)
            else:
                fig = get_plot(df, var1, plot_type)
        elif var_count == 2 and var2:
            fig = get_plot(df, var1, plot_type, var2)
    
    if fig:
        img = io.BytesIO()
        fig.savefig(img, format='png')
        img.seek(0)
        plot_data = base64.b64encode(img.getvalue()).decode('utf8')
    else:
        plot_data = None

    return render_template('eda.html', columns=columns, plot_types=list(plot_var_counts.keys()),
                           plot_type=plot_type, var1=var1, var2=var2, var_count=var_count, plot_data=plot_data)

@app.route('/download')
def download_data():
    df, error, _ = get_uploaded_dataframe()
    if error:
        return redirect(url_for('upload_file'))
    
    fmt = request.args.get('format', 'csv').lower() 
    if fmt == 'csv':
        # Convert df to CSV and Send
        csv_data = df.to_csv(index=False)
        return send_file(io.BytesIO(csv_data.encode()), mimetype='text/csv', as_attachment=True, download_name='DataGlimpse.csv')
    
    elif fmt == 'db':
        # Write df to a Temporary SQLite File
        temp_db_path = os.path.join(UPLOAD_FOLDER, 'temp_download.db')
        
        # Remove Old Temp File if exists
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)
        
        # Save to SQLite and Send
        conn = sqlite3.connect(temp_db_path)
        df.to_sql('data', conn, index=False, if_exists='replace')
        conn.close()
        return send_file(temp_db_path, mimetype='application/x-sqlite3', as_attachment=True,download_name='DataGlimpse.db')
    
    # Obtain Data Transformation Logs
    elif fmt == 'log_txt':
        log_path = os.path.join(UPLOAD_FOLDER, 'edit_logs.txt')
        if not os.path.exists(log_path):
            return "No logs available", 404
        
        return send_file(log_path, mimetype='text/plain', as_attachment=True, download_name='Data_Transformation.txt')
    
    else:
        return "Unsupported Download Format", 400
    

if __name__ == '__main__':
    app.run(debug=True)