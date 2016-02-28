from os.path import abspath, dirname, join
from setuptools import setup, find_packages


FOLDER = dirname(abspath(__file__))
DESCRIPTION = '\n\n'.join(open(join(FOLDER, x)).read().strip() for x in [
    'README.rst', 'CHANGES.rst'])
setup(
    name='crosscompute',
    version='0.4.3',
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
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    setup_requires=[
        'invisibleroads>=0.1.4',
        'pytest-runner',
    ],
    install_requires=[
        'invisibleroads_macros>=0.6.6',
        'invisibleroads_posts>=0.4.6',
        'invisibleroads_repositories>=0.1.3',
        'pyramid',
        'pyramid_jinja2',
        'six',
        'stevedore',
    ],
    tests_require=[
        'beautifulsoup4',
        'pytest',
        'werkzeug',
    ],
    entry_points={
        'console_scripts': [
            'crosscompute = crosscompute.scripts:launch',
        ],
        'crosscompute': [
            'setup = crosscompute.scripts.setup:SetupScript',
            'run = crosscompute.scripts.run:RunScript',
            'serve = crosscompute.scripts.serve:ServeScript',
        ],
        'pyramid.scaffold': [
            'tool = crosscompute.scaffolds:ToolTemplate',
        ],
    })
