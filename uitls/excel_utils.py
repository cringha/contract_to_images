
import pandas as pd
def read_row_value_to_dict(row, column_names):
    current = {}
    for col in column_names:
        value = row[col]
        if pd.notna(value):
            current[col] = value
        else:
            current[col] = ""
    return current


def trim_all_names(names):
    out = []
    for name in names:
        out.append(name.strip())
    return out


def read_excel_sheet_values(file_name, sheet_name):
    df = pd.read_excel(file_name, sheet_name)
    out_list = []

    names = df.columns.tolist()
    # print(names)
    names = trim_all_names(names)
    for _, row in df.iterrows():
        one = read_row_value_to_dict(row, names)
        out_list.append(one)

    return out_list
