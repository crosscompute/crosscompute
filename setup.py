import sys
from os.path import abspath, dirname, join
from setuptools import find_packages, setup


ENTRY_POINTS = """
[console_scripts]
crosscompute = crosscompute.scripts:launch
[crosscompute]
setup = crosscompute.scripts.setup:SetupScript
run = crosscompute.scripts.run:RunScript
serve = crosscompute.scripts.serve:ServeScript
work = crosscompute.scripts.work:WorkScript
[pyramid.scaffold]
cc-python = crosscompute.scaffolds:PythonToolTemplate
"""


REQUIREMENTS = [
    'invisibleroads-macros>=0.7.5',
    'invisibleroads-posts>=0.5.2',
    'invisibleroads-uploads>=0.1.1',
    'invisibleroads>=0.1.7',
    'markupsafe',
    'mistune',
    'pyramid',
    'pyramid_jinja2',
    'requests',
    'simplejson',
    'six',
    'socketIO_client>=0.7.2',
    'stevedore',
]
if sys.version_info[0] < 3:
    REQUIREMENTS.append('subprocess32')


FOLDER = dirname(abspath(__file__))
DESCRIPTION = '\n\n'.join(open(join(FOLDER, x)).read().strip() for x in [
    'README.rst', 'CHANGES.rst'])
setup(
    name='crosscompute',
    version='0.6.2',
    description='Publish your own tools by writing a configuration file',
    long_description=DESCRIPTION,
    classifiers=[
        'Programming Language :: Python',
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
        'pytest',
        'pytest-mock',
        'werkzeug',
    ],
    entry_points=ENTRY_POINTS)
