import pandas as pd

def rename_columns(df,hpx_flag):
    """Rename columns in the DataFrame."""
    if hpx_flag:
        return df.rename(columns={
            'View Name': 'screenName',
            'View Mode': 'screenMode',
            'Action': 'action',
            'Control Name': 'controlName'
        })
    else:
        return df.rename(columns={
            'Activity': 'activity',
            'Screen Path': 'screenPath',
            'Screen Name': 'screenName',
            'Screen Mode': 'screenMode',
            'Action': 'action',
            'Control Name': 'controlName'})


def split_and_duplicate_rows(df, column, delimiter='|'):
    """Split values in a column by a delimiter and duplicate rows."""
    rows = []
    for _, row in df.iterrows():
        value = row[column]
        if isinstance(value, str):
            values = value.strip('<>').split(delimiter)
        else:
            values = [value]
        for val in values:
            new_row = row.copy()
            new_row[column] = val.strip() if isinstance(val, str) else val
            rows.append(new_row)
    return pd.DataFrame(rows)
