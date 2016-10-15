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
[crosscompute.types]
integer = crosscompute.types:IntegerType
text = crosscompute.types:TextType
[pyramid.scaffold]
cc-python = crosscompute.scaffolds:PythonToolTemplate
"""


REQUIREMENTS = [
    'invisibleroads_macros>=0.7.2',
    'invisibleroads_posts>=0.5.1',
    'invisibleroads_uploads>=0.0.5',
    'mistune',
    'nbconvert',
    'pyramid',
    'pyramid_jinja2',
    'six',
    'stevedore',
]
if sys.version_info[0] < 3:
    REQUIREMENTS.append('subprocess32')


FOLDER = dirname(abspath(__file__))
DESCRIPTION = '\n\n'.join(open(join(FOLDER, x)).read().strip() for x in [
    'README.rst', 'CHANGES.rst'])
setup(
    name='crosscompute',
    version='0.5.5',
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
        'mock',
        'pytest',
        'werkzeug',
    ],
    entry_points=ENTRY_POINTS)
