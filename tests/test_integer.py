from crosscompute.tests import run, serve_bad_request


def test_bad_output(tmpdir):
    args = str(tmpdir), 'save-bad-integer'
    r = run(*args)
    assert 'bad_integer.error' in r['type_errors']


def test_bad_input(tmpdir):
    args = str(tmpdir), 'load-integer', {'x_integer': 'abc'}
    errors = serve_bad_request(*args)
    assert 'x_integer' in errors


def test_good_input(tmpdir):
    args = str(tmpdir), 'load-integer', {'x_integer': 2}
    r = run(*args)
    r['standard_outputs']['y_integer'] == 4


if __name__ == '__main__':
    from argparse import ArgumentParser
    argument_parser = ArgumentParser()
    argument_parser.add_argument('--x_integer')
    argument_parser.add_argument('--save_bad_integer', action='store_true')
    args = argument_parser.parse_args()
    if args.x_integer:
        y_integer = int(args.x_integer) ** 2
        print('y_integer = %s' % y_integer)
    if args.save_bad_integer:
        print('bad_integer = abc')
