from invisibleroads.scripts import Script


class RunWorkerScript(Script):

    def configure(self, argument_subparser):
        argument_subparser.add_argument('token')

    def run(self, args, argv):
        print('run worker', args)
