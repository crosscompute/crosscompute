# CrossCompute

Automate your Jupyter notebooks and scripts as web-based reports, tools, widgets, dashboards, wizards.

- Reports are documents that update when the data changes.
- Tools are forms that transform input variables into output variables.
- Widgets are interactive visualizations that update when the data changes.
- Dashboards are widgets in a layout.
- Wizards are step-by-step questions that generate a specific web-based report.

[See examples and tutorials](https://crosscompute.com).

## Usage

```bash
# Update package
pip install crosscompute -U

# Initialize configuration
crosscompute

# Serve analytics
crosscompute serve.yml
```

[See documentation](https://github.com/crosscompute/crosscompute-docs).

## Development

```bash
# Clone repository
git clone https://github.com/crosscompute/crosscompute

# Install with dependencies for tests
cd crosscompute
pip install -e .[test]

# Run tests
pytest \
    --cov=crosscompute \
    --cov-config=tox.ini \
    --cov-report term-missing:skip-covered \
    tests

# Build package for PyPI
pip install build
python -m build --sdist --wheel

# Publish package on PyPI
pip install twine --upgrade
python -m twine upload dist/*
```

## Acknowledgments

- Olga Creutzburg
- Salah Ahmed
- Rodrigo Guarachi
- Polina Chernomaz
- Miguel Ángel Gordián
- Noé Domínguez Porras
- Marta Moreno
- Ning Wei
- Kashfi Fahim
- Elaine Chan
- Aida Shoydokova
- Jennifer Ruda
