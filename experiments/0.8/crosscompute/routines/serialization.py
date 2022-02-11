class FairDumper(yaml.SafeDumper):
    # https://ttl255.com/yaml-anchors-and-aliases-and-how-to-disable-them

    def ignore_aliases(self, data):
        return True

    def represent_str(self, data):
        parent_instance = super()
        return parent_instance.represent_scalar(
            'tag:yaml.org,2002:str', data, style='|',
        ) if '\n' in data else parent_instance.represent_str(data)


FairDumper.add_representer(str, FairDumper.represent_str)


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


def load_table_csv(source_path, variable_id):
    try:
        csv_reader = csv.reader(open(source_path, 'rt'))
    except IOError:
        raise CrossComputeExecutionError({
            'variable': f'could not load {variable_id} from {source_path}'})
    columns = next(csv_reader)
    rows = [[parse_number_safely(_) for _ in row] for row in csv_reader]
    return {'columns': columns, 'rows': rows}
