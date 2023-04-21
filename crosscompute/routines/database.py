import shlex
from logging import getLogger
from os.path import isfile
from pathlib import Path
from time import time

from invisibleroads_macros_disk import is_path_in_folder
from watchfiles import Change, DefaultFilter

from ..constants import (
    Info,
    BATCH_ROUTE,
    STEP_CODE_BY_NAME,
    STEP_ROUTE)
from .configuration import (
    get_folder_plus_path)


class DiskDatabase():

    def __init__(self, configuration, changes, with_restart):
        self._configuration = configuration
        self._changes = changes
        self._memory = learn(configuration, with_restart)

    def grok(self, paths):
        changed_infos = []
        variable_ids = []
        for path in paths:
            try:
                infos = self.get(path)
            except KeyError:
                continue
            for info in infos:
                if info['code'] == Info.VARIABLE:
                    variable_id = info['id']
                    if info['id'] in variable_ids:
                        continue
                    variable_ids.append(variable_id)
                changed_infos.append(info)
        if changed_infos:
            self._changes[time()] = changed_infos
        L.debug(changed_infos)
        return changed_infos

    def get(self, path):
        path = Path(path).absolute()
        configuration = self._configuration
        for automation_definition in configuration.automation_definitions:
            automation_folder = automation_definition.folder
            runs_folder = automation_folder / 'runs'
            if is_path_in_folder(path, runs_folder):
                run_id = path.resolve().relative_to(runs_folder).parts[0]
                batch_uri = BATCH_ROUTE.format(batch_slug=run_id)
                memory = DiskMemory()
                add_variable_infos_from_folder(
                    memory, automation_definition, runs_folder / run_id,
                    batch_uri)
                infos = memory.get(path)
                break
        else:
            infos = self._memory.get(path)
        return infos


class DiskMemory():

    def __init__(self):
        self._infos_by_path = {}
        self._infos_by_folder = {}

    def add(self, path, info):
        path = Path(path).absolute()
        if not path.exists() or path.is_file():
            d = self._infos_by_path
        elif path.is_dir() and info['code'] == Info.DATASET:
            d = self._infos_by_folder
        else:
            L.warning(f'{path} must be a file')
            return
        if path not in d:
            d[path] = []
        d[path].append(info)

    def get(self, path):
        path = Path(path).absolute()
        if path in self._infos_by_path:
            return self._infos_by_path[path]
        for folder, infos in self._infos_by_folder.items():
            if folder in path.parents:
                return infos
        raise KeyError


class PositiveFileFilter(DefaultFilter):

    def __call__(self, change, path):
        is_positive = change != Change.deleted
        is_file = isfile(path)
        return is_positive and is_file and super().__call__(change, path)


def learn(configuration, with_restart):
    memory = DiskMemory()
    add_variable_infos(memory, configuration)
    if with_restart:
        add_code_infos(memory, configuration)
        add_script_infos(memory, configuration)
        add_dataset_infos(memory, configuration)
        add_template_infos(memory, configuration)
        add_style_infos(memory, configuration)
    return memory


def add_code_infos(memory, configuration):
    info = {'code': Info.CONFIGURATION}
    # Get automation configuration paths
    memory.add(configuration.path, info)
    for import_configuration in configuration.import_configurations:
        memory.add(import_configuration['path'], info)
    # Get batch configuration paths
    for automation_definition in configuration.automation_definitions:
        automation_folder = automation_definition.folder
        # Use raw batch definitions
        raw_batch_definitions = automation_definition.get('batches', [])
        for raw_batch_definition in raw_batch_definitions:
            batch_configuration = raw_batch_definition.get('configuration', {})
            if 'path' not in batch_configuration:
                continue
            memory.add(automation_folder / batch_configuration['path'], info)


def add_script_infos(memory, configuration):
    info = {'code': Info.SCRIPT}
    for automation_definition in configuration.automation_definitions:
        automation_folder = automation_definition.folder
        for i, script_definition in enumerate(
                automation_definition.script_definitions):
            script_info = info | {'index': i}
            if 'command' in script_definition:
                for term in shlex.split(script_definition.command):
                    file_path = automation_folder / term
                    if file_path.exists():
                        memory.add(file_path, script_info)
                continue
            if 'path' in script_definition:
                file_path = automation_folder / script_definition.path
                memory.add(file_path, script_info)
                continue
            if 'function' in script_definition:
                module_name = script_definition['function'].split('.')[0]
                file_name = module_name + '.py'
                file_path = automation_folder / file_name
                if file_path.exists():
                    memory.add(file_path, script_info)


def add_dataset_infos(memory, configuration):
    info = {'code': Info.DATASET}
    for automation_definition in configuration.automation_definitions:
        automation_folder = automation_definition.folder
        for dataset_definition in automation_definition.dataset_definitions:
            reference_configuration = dataset_definition.reference
            reference_path = get_folder_plus_path(reference_configuration)
            if reference_path:
                file_path = automation_folder / reference_path
                memory.add(file_path, info)


def add_variable_infos(memory, configuration):
    for automation_definition in configuration.automation_definitions:
        automation_folder = automation_definition.folder
        # Use computed batch definitions
        for batch_definition in automation_definition.batch_definitions:
            add_variable_infos_from_folder(
                memory,
                automation_definition,
                automation_folder / batch_definition.folder,
                batch_definition.uri)


def add_variable_infos_from_folder(
        memory, automation_definition, absolute_batch_folder, batch_uri):
    info = {'code': Info.VARIABLE}
    automation_uri = automation_definition.uri
    uri = automation_uri + batch_uri
    d = automation_definition.variable_definitions_by_step_name
    for step_name, variable_definitions in d.items():
        step_code = STEP_CODE_BY_NAME[step_name]
        step_uri = STEP_ROUTE.format(step_code=step_code)
        folder = absolute_batch_folder / step_name
        for variable_definition in variable_definitions:
            variable_id = variable_definition.id
            if variable_id != 'return_code':
                info_uri = uri + step_uri
            else:
                info_uri = uri
            variable_info = info | {
                'id': variable_id, 'uri': info_uri, 'step': step_code}
            variable_configuration = variable_definition.configuration
            if 'path' in variable_configuration:
                path = folder / variable_configuration['path']
                memory.add(path, variable_info)
            path = folder / variable_definition.path
            memory.add(path, variable_info)


def add_template_infos(memory, configuration):
    info = {'code': Info.TEMPLATE}
    for automation_definition in configuration.automation_definitions:
        automation_folder = automation_definition.folder
        automation_uri = automation_definition.uri
        template_info = info | {'uri': automation_uri}
        d = automation_definition.template_definitions_by_step_name
        for step_name, template_definitions in d.items():
            for template_definition in template_definitions:
                if 'path' not in template_definition:
                    continue
                path = automation_folder / template_definition.path
                step_code = STEP_CODE_BY_NAME[step_name]
                memory.add(path, template_info | {'step': step_code})
        d = automation_definition.template_path_by_id
        for template_id, template_path in d.items():
            path = automation_folder / template_path
            memory.add(path, template_info)


def add_style_infos(memory, configuration):
    info = {'code': Info.STYLE}
    automation_definitions = configuration.automation_definitions
    for automation_definition in automation_definitions:
        automation_folder = automation_definition.folder
        for style_definition in automation_definition.style_definitions:
            if 'path' not in style_definition:
                continue
            path = automation_folder / style_definition['path']
            memory.add(path, info)


L = getLogger(__name__)
