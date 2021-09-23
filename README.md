# CrossCompute

Transform your notebook or script into a web-based resource.

- Reports are documents that update when the data changes.
- Tools are forms that transform input variables into output variables.
- Widgets are interactive visualizations that update when the data changes.
- Dashboards are widgets in a layout.
- Wizards are step-by-step questions that generate a specific web-based report.

```bash
# Update package
pip install crosscompute -U

# Initialize configuration
crosscompute

# Serve analytics
crosscompute serve.yml
```

[See documentation](https://github.com/crosscompute/crosscompute-docs).

[See examples and tutorials](https://crosscompute.com).

## Usage

## Development

```bash
git clone https://github.com/crosscompute/crosscompute
cd crosscompute
pip install -e .[test]
pytest --cov=crosscompute --cov-report term-missing:skip-covered --cov-config=tox.ini tests
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
