# CrossCompute

Publish your tool by writing a configuration file.

Please see https://crosscompute.com for examples and tutorials.

```bash
pip install -U crosscompute
```

## Add Tool

```
export CROSSCOMPUTE_TOKEN=YOUR-TOKEN

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
