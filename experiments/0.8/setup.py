APPLICATION_REQUIREMENTS = [
    'geojson',
    'invisibleroads >= 0.3.4',
    'invisibleroads-macros-disk >= 1.1.0',
    'invisibleroads-macros-log >= 1.0.3',
    'invisibleroads-macros-security >= 1.0.1',
    'invisibleroads-macros-text >= 1.0.3',
    'markdown2',
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

    packages=find_packages(),
    zip_safe=True,
    extras_require={'test': TEST_REQUIREMENTS},
    install_requires=APPLICATION_REQUIREMENTS,
