from invisibleroads.scripts import Script

from ...routines import get_token


class AddToolScript(Script):

    def configure(self, argument_subparser):
        argument_subparser.add_argument('path-or-folder-or-uri')

    def run(self, args, argv):
        token = get_token()
        print(token)
