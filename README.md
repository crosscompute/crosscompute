# CrossCompute

Automate your work by writing a configuration file.

Please see https://crosscompute.com for examples and tutorials.

```bash
pip install -U crosscompute
```

## Usage

```bash
# export CROSSCOMPUTE_CLIENT=https://crosscompute.com
# export CROSSCOMPUTE_ECHOES=https://services.crosscompute.com
# export CROSSCOMPUTE_SERVER=https://services.crosscompute.com
export CROSSCOMPUTE_TOKEN=YOUR-TOKEN
crosscompute
```

### Run Automation

```bash
crosscompute automations run
crosscompute automations run automation.yml
```

### Add Tool

```bash
git clone git@github.com:crosscompute/crosscompute-examples
cd crosscompute-examples/add-numbers

# Mock
crosscompute tools add tool.yml --mock

# Real
crosscompute tools add tool.yml
```

### See Tool

```
crosscompute tools see
crosscompute tools see | jq
crosscompute tools see | jq .[].id
crosscompute tools see TOOL-ID
```

### Run Worker

```bash
crosscompute workers run
```

### See Project

```
crosscompute projects see
crosscompute projects see | jq
crosscompute projects see | jq '.[] | {id:.id, name:.name}'
crosscompute projects see PROJECT-ID
```

### Set Project

```
crosscompute projects set project.yml
```

### Add Result

```
crosscompute results add result.yml
```

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
- Miguel Angel Gordián
- Noé Domínguez Porras
- Marta Moreno
- Ning Wei
- Elaine Chan
- Aida Shoydokova
- Jennifer Ruda
