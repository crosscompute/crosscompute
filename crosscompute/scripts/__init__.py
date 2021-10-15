# TODO: Render output variables
import webbrowser
import yaml
from collections import defaultdict
from markdown import markdown
from os import listdir
from os.path import splitext
from pyramid.config import Configurator
from pyramid.response import Response
from sys import argv
from waitress import serve

from .. import __version__


def launch():
    print(DEFAULT_CONFIGURATION)
    print(argv)
    configuration_paths_by_format = get_configuration_paths_by_format()
    for (
        configuration_format,
        configuration_paths,
    ) in configuration_paths_by_format.items():
        if configuration_format != 'yaml':
            continue
        for configuration_path in configuration_paths:
            print(configuration_format, configuration_path)

        configuration = yaml.safe_load(open(configuration_path, 'rt'))
        print(configuration)
        if 'crosscompute' not in configuration:
            continue
        # TODO: Assert version
        break

    display_layout = configuration['display']['layout']
    if display_layout == 'output':
        template_dictionary = configuration['output']['templates'][0]
        template_path = template_dictionary['path']
        # TODO: Check if path is md or ipynb
        template_text = open(template_path, 'rt').read()
        template_html = markdown(template_text)
        print(template_html)

    def see_root(request):
        return Response(template_html)

    with Configurator() as config:
        config.add_route('root', '/')
        config.add_view(see_root, route_name='root')
        app = config.make_wsgi_app()

    # /resources/show-maps/batches/usa-maine
    # /resources/show-maps/tests/points
    # /~/show-maps/tests/points
    # /show-maps/tests/points

    webbrowser.open('http://localhost:8000')

    # server = make_server('0.0.0.0', 6543, app)
    # server.serve_forever()
    serve(app, host='0.0.0.0', port=8000)

    # configuration = load_configuration()
    # if not configuration:
    # check if configuration file exists
    # if not, create one
    # if it does exist, launch server
    print('whee!')
    # make default configuration
    # render default configuration to yaml, ini, toml


def get_configuration_paths_by_format(configuration_folder='.'):
    configuration_paths_by_format = defaultdict(list)
    for path in listdir(configuration_folder):
        root, extension = splitext(path)
        if extension in ['.cfg', '.ini']:
            configuration_format = 'ini'
        elif extension == '.toml':
            configuration_format = 'toml'
        elif extension in ['.yaml', '.yml']:
            configuration_format = 'yaml'
        else:
            continue
        configuration_paths_by_format[configuration_format].append(path)
    return dict(configuration_paths_by_format)


def load_configuration(configuration_path, configuration_format):
    pass


# TODO: Draft function that loads configuration file
# TODO: Render input markdown
# TODO: Implement rough crosscompute-image plugin


DEFAULT_CONFIGURATION = {
    'crosscompute': __version__,
    'name': 'Name of Your Resource',
    'version': '0.0.0',
}


'''
imports:
  - id: { id to use when referencing this import in your template }
    # Specify either path or uri or name
    path: { path to the configuration file that you want to import }
    uri: { uri to the configuration file that you want to import }
    name: { name of the resource that you want to import }
peers:
  - uri: { uri of a trusted peer with which you want to pool resources }
input:
  variables:
    - id: { id to use when referencing this variable in your template }
      view: { view to use when rendering this variable on the display }
      path: { path where your script loads this variable, relative to the
              input folder }
  templates:
    - path: { path to your markdown template or jupyter notebook wizard }
output:
  variables:
    - id: { id to use when referencing this variable in your template }
      view: { view to use when rendering this variable on the display }
      path: { path where your script loads this variable, relative to the
              output folder }
  templates:
    - path: { path to your markdown template or jupyter notebook wizard }
log:
  variables:
    - id: { id to use when referencing this variable in your template }
      view: { view to use when rendering this variable on the display }
      path: { path where your script loads this variable, relative to the
              log folder }
  templates:
    - path: { path to your markdown template or jupyter notebook wizard }
debug:
  variables:
    - id: { id to use when referencing this variable in your template }
      view: { view to use when rendering this variable on the display }
      path: { path where your script loads this variable, relative to the
              debug folder }
  templates:
    - path: { path to your markdown template or jupyter notebook wizard }
tests:
  - folder: { folder that contains an input subfolder with paths for
              input variables that define a specific test }
batches:
  - folder: { folder that contains an input subfolder with paths for
              input variables that define a specific batch }
script:
  folder: { folder where your script should run }
  # Specify either command or function
  command: { command to use to run your script, relative to the script folder }
  function: { function to use to run your script, specified using
              module.function syntax, relative to the script folder }
  schedule: { schedule to use to run your script, specified using extended
              crontab syntax -- second-of-minute minute-of-hour
              hour-of-day day-of-month month-of-year day-of-week }
repository:
  uri: { uri of repository that contains your script }
  folder: { folder that contains this configuration file }
environment:
  variables:
    - id: { id of the environment variable that you want to make available
            to your script }
  image: { image of the container that you want to use to run your script }
  processor: { type of the processor you want to use to run your script,
               either cpu or gpu }
  memory: { amount of memory you want to reserve to run your script }
display:
  style:
    path: { path to CSS stylesheet that will be used to render your templates }
  header:
    path: { path to markdown template that defines the header }
  footer:
    path: { path to markdown template that defines the footer }
  layout: { layout to use by default when rendering this resource }
  format: { format to use by default when rendering this resource }
payment:
  account: { account where the user should send payment when using this
             resource }
  amount: { amount of payment that the user should send }
  currency: { currency of payment }
  policy: { policy to use for payment, either before or after }
'''
