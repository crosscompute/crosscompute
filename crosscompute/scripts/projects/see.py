from .. import LoggingScript


class SeeProjectScript(LoggingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)

    def run(self, args, argv):
        super().run(args, argv)
        print('see project', args, argv)
