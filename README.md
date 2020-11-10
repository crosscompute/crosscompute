# CrossCompute

Automate your work by writing a configuration file.

Please see https://crosscompute.com for examples and tutorials.

```bash
pip install -U crosscompute
```

## Usage

```bash
# export CROSSCOMPUTE_CLIENT=https://crosscompute.com
# export CROSSCOMPUTE_SERVER=https://services.crosscompute.com
export CROSSCOMPUTE_TOKEN=YOUR-TOKEN
```

### Run Automation

```bash
crosscompute automations run
crosscompute automations run AUTOMATION-PATH
```

### Add Tool

```bash
git clone git@github.com:crosscompute/crosscompute-examples
cd crosscompute-examples/add-numbers

# Mock
crosscompute tools add .crosscompute.yml --mock

# Real
crosscompute tools add .crosscompute.yml
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

### Add Project

```
crosscompute projects add --name "Project X"
```

### Change Project

```
crosscompute projects change PROJECT-ID \
    --datasetId abc \
    --toolId def \
    --toolId ghi \
    --resultId jkl \
    --resultId mno
```

### Add Result

```
crosscompute results add \
    result.json \
    --name RESULT-NAME \
    --toolId TOOL-ID \
    --toolVersionId TOOL-VERSION-ID \
    --projectId PROJECT-ID
```

## Development

```bash
git clone https://github.com/crosscompute/crosscompute
cd crosscompute
pip install -e .[test]
pytest --cov=crosscompute --cov-report term-missing:skip-covered tests
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
