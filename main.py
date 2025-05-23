from flask import Flask, render_template, request, redirect, url_for, session, send_file
import math
import os
import io
from flask_caching import Cache
from summary_functions import read_data, get_column_summary, get_dataframe_summary
from editing_functions import apply_edits
from plotting_functions import get_plot

app = Flask(__name__)
app.secret_key = 'unique'

# Initialize Temporary Folder to Store Files
UPLOAD_FOLDER = 'temp'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
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
        cache.set(filename, df, timeout=300)

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
        return error

    # Loads 50 Rows per Page
    page_size = 50
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
        return error
    
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
        return error

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
        return error
    
    if request.method == 'POST':
        df = apply_edits(df, request.form)
        cache.set(filename, df, timeout=300)
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
        return error

    columns = list(df.columns)

    # Default: all plot types
    single_var_types = ['histogram', 'boxplot', 'barchart', 'density']
    two_var_types = ['scatter', 'line', 'heatmap']

    var1 = None
    var2 = None
    plot_types = single_var_types + two_var_types  # default, if nothing selected yet

    if request.method == 'POST':
        var1 = request.form.get('var1')
        var2 = request.form.get('var2')
        # Adjust plot types based on selection
        if var2 and var2.strip():
            plot_types = two_var_types
        else:
            plot_types = single_var_types

        plot_type = request.form.get('plot_type')

        if var1 and plot_type:
            fig = get_plot(df, var1, plot_type, var2)
            img = io.BytesIO()
            fig.savefig(img, format='png')
            img.seek(0)
            return send_file(img, mimetype='image/png')

    return render_template('eda.html', columns=columns, plot_types=plot_types, var1=var1, var2=var2)


if __name__ == '__main__':
    app.run(debug=True)