from os.path import abspath, dirname, join
from setuptools import find_packages, setup


ENTRY_POINTS = """
[console_scripts]
crosscompute = crosscompute.scripts:launch
[crosscompute]
help = crosscompute.scripts.help:HelpScript
run = crosscompute.scripts.run:RunScript
serve = crosscompute.scripts.serve:ServeScript
[pyramid.scaffold]
cc-python = crosscompute.scaffolds:PythonToolTemplate
"""
FOLDER = dirname(abspath(__file__))
DESCRIPTION = '\n\n'.join(open(join(FOLDER, x)).read().strip() for x in [
    'README.rst', 'CHANGES.rst'])
setup(
    name='crosscompute',
    version='0.4.5',
    description='Publish your own tools by writing a configuration file',
    long_description=DESCRIPTION,
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Pyramid',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    author='Roy Hyunjin Han',
    author_email='rhh@crosscompute.com',
    url='https://crosscompute.com/docs',
    keywords='web pyramid pylons crosscompute',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    setup_requires=[
        'pytest-runner',
    ],
    install_requires=[
        'invisibleroads_macros>=0.6.8',
        'invisibleroads_posts>=0.4.8',
        'invisibleroads_uploads>=0.0.2',
        'mistune',
        'pyramid',
        'pyramid_jinja2',
        'six',
        'stevedore',
        'subprocess32',
    ],
    tests_require=[
        'beautifulsoup4',
        'lxml',
        'pytest',
        'werkzeug',
    ],
    entry_points=ENTRY_POINTS)
