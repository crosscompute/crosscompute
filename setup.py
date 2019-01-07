import sys
from os.path import abspath, dirname, join
from setuptools import find_packages, setup


ENTRY_POINTS = """
[console_scripts]
crosscompute = crosscompute.scripts:launch
[crosscompute]
run = crosscompute.scripts.run:RunScript
serve = crosscompute.scripts.serve:ServeScript
work = crosscompute.scripts.work:WorkScript
[pyramid.scaffold]
cc-python = crosscompute.scaffolds:PythonToolTemplate
"""


REQUIREMENTS = [
    'invisibleroads-macros>=0.9.5.1',
    'invisibleroads>=0.2.0',
    'invisibleroads-posts>=0.6.1',
    'invisibleroads-uploads>=0.4.2.3',
    'markupsafe',
    'mistune',
    'pudb',
    'pyramid',
    'pyramid-jinja2',
    'requests',
    'simplejson',
    'six',
    'socketIO-client>=0.7.2',
    'stevedore',
]
if sys.version_info[0] < 3:
    REQUIREMENTS.append('subprocess32')


FOLDER = dirname(abspath(__file__))
DESCRIPTION = '\n\n'.join(open(join(FOLDER, x)).read().strip() for x in [
    'README.rst', 'CHANGES.rst'])
setup(
    name='crosscompute',
    version='0.7.7.1',
    description='Publish your own tools by writing a configuration file',
    long_description=DESCRIPTION,
    classifiers=[
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Framework :: Pyramid',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    author='CrossCompute Inc',
    author_email='support@crosscompute.com',
    url='https://crosscompute.com/docs',
    keywords='web pyramid pylons crosscompute',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    setup_requires=[
        'pytest-runner',
    ],
    install_requires=REQUIREMENTS,
    tests_require=[
        'beautifulsoup4',
        'mock',
        'pytest',
        'pytest-mock',
        'werkzeug',
        'webob',
    ],
    entry_points=ENTRY_POINTS)
