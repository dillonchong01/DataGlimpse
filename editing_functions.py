import pandas as pd

def apply_edits(df, form_data):
    df = df.copy()
    columns_to_drop = []
    rename_map = {}

    for col in df.columns:
        # Check if Column is to be Dropped
        if form_data.get(f'dropcol_{col}') == 'on':
            columns_to_drop.append(col)
            continue

        # Drop NA
        if form_data.get(f'dropna_{col}') == 'on':
            df = df[df[col].notna()]

         # Convert Variable Type
        convert_type = form_data.get(f'convert_{col}')
        if convert_type == 'numeric':
            df[col] = pd.to_numeric(df[col], errors='coerce')
        elif convert_type == 'datetime':
            df[col] = pd.to_datetime(df[col], errors='coerce')
        elif convert_type == 'categorical':
            df[col] = df[col].astype('category')
        elif convert_type == 'binary':
            df[col] = df[col].apply(lambda x: 1 if str(x).lower() in ['true', '1', 'yes'] else 0)

        # Rename Column
        new_name = form_data.get(f'rename_{col}')
        if new_name and new_name.strip() and new_name != col:
            rename_map[col] = new_name.strip()

    # Apply renaming and dropping after loop
    if columns_to_drop:
        df.drop(columns=columns_to_drop, inplace=True)
    if rename_map:
        df.rename(columns=rename_map, inplace=True)

    return df