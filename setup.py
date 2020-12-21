from crosscompute import __description__, __version__
from os.path import abspath, dirname, join
from setuptools import find_packages, setup


ENTRY_POINTS = '''
[console_scripts]
crosscompute = crosscompute.scripts:launch
[crosscompute]
projects.see = crosscompute.scripts.projects.see:SeeProjectsScript
projects.set = crosscompute.scripts.projects.set:SetProjectScript
tools.see = crosscompute.scripts.tools.see:SeeToolScript
tools.add = crosscompute.scripts.tools.add:AddToolScript
results.see = crosscompute.scripts.results.see:SeeResultScript
results.add = crosscompute.scripts.results.add:AddResultScript
workers.run = crosscompute.scripts.workers.run:RunWorkerScript
automations.run = crosscompute.scripts.automations.run:RunAutomationScript
'''
APPLICATION_CLASSIFIERS = [
    'Programming Language :: Python :: 3',
    'License :: OSI Approved :: MIT License',
]
APPLICATION_REQUIREMENTS = [
    'geojson',
    'invisibleroads >= 0.3.4',
    'invisibleroads-macros-disk >= 1.1.0',
    'invisibleroads-macros-log >= 1.0.3',
    'invisibleroads-macros-security >= 1.0.1',
    'invisibleroads-macros-text >= 1.0.3',
    'packaging >= 20.4',
    'pyramid',
    'pyyaml',
    'requests',
    'sseclient',
    'strictyaml',
    'tinycss2',
]
TEST_REQUIREMENTS = [
    'pytest-cov',
    'pytest-mock',
]
FOLDER = dirname(abspath(__file__))
DESCRIPTION = '\n\n'.join(open(join(FOLDER, x)).read().strip() for x in [
    'README.md',
    'CHANGES.md'])


setup(
    name='crosscompute',
    version=__version__,
    description=__description__,
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
