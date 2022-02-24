def save_table_csv(target_path, value, variable_id, value_by_id_by_path):
    try:
        columns = value['columns']
        rows = value['rows']
        with open(target_path, 'wt') as target_file:
            csv_writer = csv.writer(target_file)
            csv_writer.writerow(columns)
            csv_writer.writerows(rows)
    except (KeyError, csv.Error):
        raise CrossComputeExecutionError({
            'variable': f'could not save {variable_id} as a table csv'})
