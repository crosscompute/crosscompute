from os.path import abspath, dirname, join
from setuptools import find_packages, setup


ENTRY_POINTS = '''
[console_scripts]
crosscompute = crosscompute.scripts:launch
[crosscompute]
tools.add = crosscompute.scripts.tools.add:AddToolScript
workers.run = crosscompute.scripts.workers.run:RunWorkerScript
'''
APPLICATION_CLASSIFIERS = [
    'Programming Language :: Python :: 3',
    'License :: OSI Approved :: MIT License',
]
APPLICATION_REQUIREMENTS = [
    'invisibleroads >= 0.2.4',
    'requests',
]
TEST_REQUIREMENTS = [
]
FOLDER = dirname(abspath(__file__))
DESCRIPTION = '\n\n'.join(open(join(FOLDER, x)).read().strip() for x in [
    'README.md', 'CHANGES.md'])


setup(
    name='crosscompute',
    version='0.8.0',
    description='Publish your tool by writing a configuration file',
    long_description=DESCRIPTION,
    long_description_content_type='text/markdown',
    classifiers=APPLICATION_CLASSIFIERS,
    author='CrossCompute Inc',
    author_email='support@crosscompute.com',
    url='https://github.com/crosscompute/crosscompute',
    keywords='crosscompute',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=True,
    extras_require={'test': TEST_REQUIREMENTS},
    install_requires=APPLICATION_REQUIREMENTS,
    entry_points=ENTRY_POINTS)
