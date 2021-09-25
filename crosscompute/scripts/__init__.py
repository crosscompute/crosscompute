from .. import __version__
# from sys import argv


def launch():
    print(DEFAULT_CONFIGURATION)
    # print(argv)
    # configuration = load_configuration()
    # if not configuration:
    # check if configuration file exists
    # if not, create one
    # if it does exist, launch server
    # print('whee!')
    # make default configuration
    # render default configuration to yaml, ini, toml


def get_configuration_path(configuration_folder):
    pass


def load_configuration(configuration_path):
    pass


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
