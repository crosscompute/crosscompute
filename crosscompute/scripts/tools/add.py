from invisibleroads.scripts import Script


class AddToolScript(Script):

    def configure(self, argument_subparser):
        argument_subparser.add_argument('path-or-folder-or-uri')

    def run(self, args, argv):
        print('add tool', args)
