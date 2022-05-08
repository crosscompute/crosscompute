def launch(argv=sys.argv):
    launch_script(
        'crosscompute',
        argv,
        description=__description__,
        epilogue=get_bash_configuration_text(),
        formatter_class=RawDescriptionHelpFormatter)
