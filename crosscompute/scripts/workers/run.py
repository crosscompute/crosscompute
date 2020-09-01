from invisibleroads.scripts import LoggingScript


class RunWorkerScript(LoggingScript):

    def run(self, args, argv):
        super().run(args, argv)
        print('run worker', args, argv)
