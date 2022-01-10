# CrossCompute Analytics Automation Framework

Automate your Jupyter notebooks and scripts as web-based reports, tools, widgets, dashboards, forms. Use this framework to create your own automations, then serve locally or deploy on your own instance of the [CrossCompute Analytics Automation System](https://d.crosscompute.com).

- Reports are documents that update when the data changes.
- Forms are step-by-step questions that generate a specific web-based report.
- Tools are forms that transform input variables into output variables.
- Widgets are interactive visualizations that update when the data changes.
- Dashboards are widgets in a layout.

Here are some available extensions:

- [crosscompute-views-map](https://github.com/crosscompute/crosscompute-views-map)
- [jupyterlab-crosscompute](https://github.com/crosscompute/jupyterlab-crosscompute) (being updated to support >= 0.9)

Here are some available views:

- string
- number
- password
- email
- text
- markdown
- image
- map-mapbox (crosscompute-views-map)
- map-deck-screengrid (crosscompute-views-map)

## Usage

```bash
# Upgrade package
pip install crosscompute --upgrade

# Initialize configuration
crosscompute

# Serve automation
crosscompute automate.yml
```

Here are some tutorials and examples:
- [Examples](https://crosscompute.net) [[source](https://github.com/crosscompute/crosscompute-examples)]
- [Documentation](https://d.crosscompute.com) [[source](https://github.com/crosscompute/crosscompute-docs)]

## Development

```bash
# Clone repository
git clone https://github.com/crosscompute/crosscompute

# Install with dependencies for tests
cd crosscompute
pip install -e .[test]

# Run tests
pytest --cov=crosscompute --cov-report term-missing:skip-covered tests

# Build package for PyPI
pip install build
python -m build --sdist --wheel

# Publish package on PyPI
pip install twine --upgrade
python -m twine upload dist/*
```

## Acknowledgments

- [Olga Creutzburg](https://www.linkedin.com/in/olga-creutzburg)
- [Salah Ahmed](https://www.linkedin.com/in/salahspage)
- [Rodrigo Guarachi](https://www.linkedin.com/in/rmguarachi)
- [Polina Chernomaz](https://www.linkedin.com/in/polinac)
- [Miguel Ángel Gordián](https://www.linkedin.com/in/miguelgordian)
- [Noé Domínguez Porras](https://www.linkedin.com/in/noedominguez)
- [Marta Moreno](https://www.linkedin.com/in/marta-moreno-07364b82)
- [Ning Wei](https://www.linkedin.com/in/ning-wei-8152393b)
- [Kashfi Fahim](https://www.linkedin.com/in/kashfifahim)
- [Elaine Chan](https://www.linkedin.com/in/chanelaine)
- [Aida Shoydokova](https://www.linkedin.com/in/ashoydok)
- [Jennifer Ruda](https://www.linkedin.com/in/jruda)
