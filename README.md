# CrossCompute

Publish your tool by writing a configuration file.

Please see https://crosscompute.com for examples and tutorials.

```bash
pip install -U crosscompute

export CROSSCOMPUTE_HOST=https://services.projects.crosscompute.com
export CROSSCOMPUTE_TOKEN=YOUR-TOKEN
```

## See Project

```
crosscompute projects see
```

## Add Tool

```
cd ~/Documents
git clone git@github.com:crosscompute/crosscompute-examples
cd crosscompute-examples/add-numbers

# Mock
crosscompute tools add .crosscompute.yml --mock

# Real
crosscompute tools add .crosscompute.yml
```

## Acknowledgments

- Olga Creutzburg
- Salah Ahmed
- Rodrigo Guarachi
- Polina Chernomaz
- Marta Moreno
- Ning Wei
- Miguel Angel Gordián
- Noé Domínguez Porras
- Elaine Chan
- Jennifer Ruda
- Aida Shoydokova
