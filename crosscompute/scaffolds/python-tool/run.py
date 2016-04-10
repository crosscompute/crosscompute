from argparse import ArgumentParser
from invisibleroads_macros.disk import make_enumerated_folder_for, make_folder
from invisibleroads_macros.log import format_summary


def run(target_folder):
    return []


if __name__ == '__main__':
    argument_parser = ArgumentParser()
    argument_parser.add_argument(
        '--target_folder',
        metavar='FOLDER', type=make_folder)

    args = argument_parser.parse_args()
    d = run(
        args.target_folder or make_enumerated_folder_for(__file__))
    print(format_summary(d))
