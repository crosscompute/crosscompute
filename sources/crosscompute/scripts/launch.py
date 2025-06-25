from argparse import ArgumentParser


def start(arguments=None):
    args = get_args(arguments)
    launch_id = get_launch_id_from(args)
    print(launch_id)


def get_args(arguments):
    a = ArgumentParser()
    args = a.parse_args(arguments)
    return args


def get_launch_id_from(args):
    # crosscompute configure
    # crosscompute debug
    # crosscompute run
    # crosscompute serve
    # crosscompute print
    # crosscompute add
    # crosscompute work
    pass
