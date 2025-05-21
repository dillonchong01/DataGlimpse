from flask import Flask, render_template, request, redirect, url_for, session
import math
import os
from flask_caching import Cache
from functions import read_data, get_column_summary

app = Flask(__name__)
app.secret_key = 'unique'

# Initialize Temporary Folder to Store Files
UPLOAD_FOLDER = 'temp'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
allowed_extensions = {'.csv', '.sqlite', '.sqlite3', '.db'}

def allowed_file(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext in allowed_extensions


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
    if 'uploaded_file' not in session:
        return redirect(url_for('upload_file'))
    filename = session.get('uploaded_file')

    file_path = os.path.join(UPLOAD_FOLDER, session['uploaded_file'])
    if not os.path.exists(file_path):
        return "File Not Found", 404

    # Attempt to Read Data of Uploaded File
    df = cache.get(filename)
    if df is None:
        try:
            df = read_data(file_path)
        except Exception as e:
            return f"Error reading file: {str(e)}", 400
        cache.set(filename, df, timeout=300)

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
    if 'uploaded_file' not in session:
        return redirect(url_for('upload_file'))

    filename = session.get('uploaded_file')
    file_path = os.path.join(UPLOAD_FOLDER, session['uploaded_file'])
    if not os.path.exists(file_path):
        return "File Not Found", 404

    df = cache.get(filename)
    if df is None:
        try:
            df = read_data(file_path)
        except Exception as e:
            return f"Error Processing File: {str(e)}", 400
        cache.set(filename, df, timeout=300)

    try:
        summary = get_column_summary(df, column)
    except Exception as e:
        return f"Error Processing Summary: {str(e)}", 400

    return render_template('col_summary.html', column=column, summary=summary)


if __name__ == '__main__':
    app.run(debug=True)