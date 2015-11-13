import subprocess
from invisibleroads_macros.disk import cd
from os.path import join

from conftest import TESTS_FOLDER


def run(tool_name, result_arguments=None):
    command_terms = ['crosscompute', 'run', tool_name]
    for k, v in (result_arguments or {}).items():
        command_terms.extend(['--%s' % k, str(v)])
    print command_terms
    with cd(TESTS_FOLDER):
        process = subprocess.Popen(
            command_terms, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    standard_output, standard_error = process.communicate()
    print(standard_output)
    print(standard_error)
    return standard_output, standard_error


def test_run_with_good_integer_input():
    standard_output = run('load-integer', {'x_integer': 2})[0]
    assert 'xx_integer = 4' in standard_output


def test_run_with_bad_integer_input():
    standard_output = run('load-integer', {'x_integer': 'abc'})[0]
    assert 'x_integer.error = expected_integer' in standard_output


def test_run_with_bad_integer_output():
    standard_output = run('save-bad-integer')[0]
    assert 'z_integer.error = expected_integer' in standard_output


def test_run_with_good_table_input():
    standard_output = run('load-table', {
        'a_table_path': join(TESTS_FOLDER, 'good.csv'),
    })[0]
    assert 'row_count = 3' in standard_output


def test_run_with_bad_table_input():
    standard_output = run('load-table', {
        'a_table_path': join(TESTS_FOLDER, 'cc.ini'),
    })[0]
    assert 'a_table.error = unsupported_format' in standard_output


def test_run_with_bad_table_output():
    standard_output = run('save-bad-table')[0]
    assert 'b_table.error = unsupported_format' in standard_output


if __name__ == '__main__':
    from argparse import ArgumentParser
    argument_parser = ArgumentParser()
    argument_parser.add_argument('--x_integer')
    argument_parser.add_argument('--y_integer')
    argument_parser.add_argument('--a_table_path')
    argument_parser.add_argument('--save_bad_integer', action='store_true')
    argument_parser.add_argument('--save_bad_table', action='store_true')
    args = argument_parser.parse_args()
    if args.x_integer:
        xx_integer = int(args.x_integer) ** 2
        print('xx_integer = %s' % xx_integer)
    if args.y_integer:
        yy_integer = int(args.y_integer) ** 2
        print('yy_integer = %s' % yy_integer)
    if args.a_table_path:
        from crosscompute_table._pandas import read_csv
        table = read_csv(args.a_table_path)
        print('column_count = %s' % len(table.columns))
        print('row_count = %s' % len(table.values))
    if args.save_bad_integer:
        print('z_integer = abc')
    if args.save_bad_table:
        print('b_table_path = cc.ini')
