import json
from pathlib import Path
from sys import argv
from time import sleep


def save_status(text):
    save_variable('status', text)


def save_variable(key, value):
    try:
        with (output_folder / 'variables.dictionary').open('rt') as f:
            d = json.load(f)
    except (OSError, json.JSONDecodeError):
        d = {}
    d[key] = value
    with (output_folder / 'variables.dictionary').open('wt') as f:
        json.dump(d, f)
    print(d)


def save_text(name, value):
    with (output_folder / name).open('wt') as f:
        f.write(value)


def save_json(name, value):
    with (output_folder / name).open('wt') as f:
        json.dump(value, f)


output_folder = Path(argv[1])
save_status('set string')
sleep(3)
save_status('set number')
save_variable('count', 10)
sleep(3)
save_status('set text')
save_variable('description', 'whee')
sleep(3)
save_status('set markdown')
save_variable('page', '# A')
sleep(3)
save_status('set radio 0')
save_json('choices.json', {'options': [
    {'name': 'A', 'value': 'a'},
    {'name': 'B', 'value': 'b'}]})
save_variable('choices', 'a')
sleep(3)
save_status('set radio 1')
save_json('choices.json', {'options': [
    {'name': 'A', 'value': 'a'},
    {'name': 'B', 'value': 'b'},
    {'name': 'C', 'value': 'c'}]})
sleep(3)
save_status('set radio 2')
save_variable('choices', 'c')
sleep(3)
save_status('set radio 3')
save_json('choices.json', {'options': [
    {'name': 'A', 'value': 'a'},
    {'name': 'B', 'value': 'b'}]})
sleep(3)
save_status('set radio 4')
save_variable('choices', 'd')
sleep(3)
save_status('set checkbox 0')
save_json('options.json', {'options': [
    {'name': 'A', 'value': 'a'},
    {'name': 'B', 'value': 'b'}]})
save_variable('options', 'a\nb')
sleep(3)
save_status('set checkbox 1')
save_json('options.json', {'options': [
    {'name': 'A', 'value': 'a'},
    {'name': 'B', 'value': 'b'},
    {'name': 'C', 'value': 'c'}]})
sleep(3)
save_status('set checkbox 2')
save_variable('options', 'c')
sleep(3)
save_status('set checkbox 3')
save_json('options.json', {'options': [
    {'name': 'A', 'value': 'a'},
    {'name': 'B', 'value': 'b'}]})
sleep(3)
save_status('set checkbox 4')
save_variable('options', 'd')
sleep(3)
save_status('set frame')
save_variable('window', 'https://crosscompute.com')
sleep(3)
save_status('set link 0')
save_text('document.txt', 'hmm')
sleep(3)
save_status('set link 1')
save_json('document.json', {'file-name': 'x.txt'})
sleep(3)
save_status('set link 2')
save_json('document.json', {'link-text': 'x'})
sleep(3)
save_status('set link 3')
save_json('document.json', {'file-name': 'y.txt', 'link-text': 'y'})
