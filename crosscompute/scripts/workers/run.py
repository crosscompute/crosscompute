from invisibleroads.scripts import LoggingScript


class RunWorkerScript(LoggingScript):

    def configure(self, argument_subparser):
        super().configure(argument_subparser)
        argument_subparser.add_argument('token')

    def run(self, args, argv):
        super().run(args, argv)
        print('run worker', args, argv)
