from os.path import abspath, dirname, join
from setuptools import setup
from setuptools.command.test import test as TestCommand


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', 'Arguments to pass to py.test')]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest
        errno = pytest.main(self.pytest_args)
        exit(errno)


ENTRY_POINTS = """
[crosscompute]
run = crosscompute.scripts.run:RunScript
serve = crosscompute.scripts.serve:ServeScript
"""
REQUIREMENTS = [
    'configparser',
    'invisibleroads',
    'invisibleroads_macros',
    'invisibleroads_posts',
    'invisibleroads_repositories',
    'pyramid',
    'pyramid_jinja2',
    'six',
    'stevedore',
]
FOLDER = dirname(abspath(__file__))
DESCRIPTION = '\n\n'.join(open(join(FOLDER, x)).read().strip() for x in [
    'README.rst', 'CHANGES.rst'])
setup(
    name='crosscompute',
    version='0.2',
    description='Publish your computational model',
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
    url='https://crosscompute.com',
    keywords='web pyramid pylons crosscompute',
    package_dir={'': 'lib'},
    packages=['crosscompute'],
    include_package_data=True,
    zip_safe=False,
    install_requires=REQUIREMENTS,
    tests_require=['lxml', 'pytest', 'werkzeug'],
    cmdclass={'test': PyTest},
    entry_points=ENTRY_POINTS,
    scripts=['bin/crosscompute'])
