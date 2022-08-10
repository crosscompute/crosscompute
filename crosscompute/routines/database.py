from pathlib import Path
from time import time

from invisibleroads_macros_disk import is_path_in_folder

from ..constants import (
    MODE_CODE_BY_NAME,
    MODE_ROUTE,
    RUN_ROUTE)


class DiskDatabase():

    def __init__(self, configuration, infos_by_timestamp):
        self._configuration = configuration
        self._infos_by_timestamp = infos_by_timestamp
        self._memory = learn(configuration)

    def grok(self, paths):
        changed_infos = []
        for path in paths:
            try:
                infos = self._get(path)
            except KeyError:
                continue
            changed_infos.extend(infos)
        if changed_infos:
            self._infos_by_timestamp[time()] = changed_infos
        return changed_infos

    def _get(self, path):
        configuration = self._configuration
        path = Path(path).resolve()
        for automation_definition in configuration.automation_definitions:
            automation_folder = automation_definition.folder
            runs_folder = automation_folder / 'runs'
            if not is_path_in_folder(path, runs_folder):
                continue
            run_id = path.relative_to(runs_folder).parts[0]
            run_uri = RUN_ROUTE.format(run_slug=run_id)
            memory = DiskMemory()
            add_variable_infos_from_folder(
                memory, configuration, runs_folder / run_id, run_uri)
            infos = memory.get(path)
            break
        else:
            infos = self._memory.get(path)
        return infos


class DiskMemory():

    def __init__(self):
        self._d = {}

    def add(self, path, info):
        path = Path(path).resolve()
        if path not in self._d:
            self._d[path] = []
        self._d[path].append(info)

    def get(self, path):
        path = Path(path).resolve()
        return self._d[path]


def learn(configuration):
    'Get c = configuration, v = variable, t = template, s = style'
    memory = DiskMemory()
    add_configuration_infos(memory, configuration)
    add_variable_infos(memory, configuration)
    add_template_infos(memory, configuration)
    add_style_infos(memory, configuration)
    return memory


def add_configuration_infos(memory, configuration):
    info = {'code': 'c'}
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


def add_variable_infos(memory, configuration):
    for automation_definition in configuration.automation_definitions:
        automation_folder = automation_definition.folder
        # Use computed batch definitions
        for batch_definition in automation_definition.batch_definitions:
            add_variable_infos_from_folder(
                memory,
                configuration,
                automation_folder / batch_definition.folder,
                batch_definition.uri)


def add_variable_infos_from_folder(
        memory, configuration, absolute_batch_folder, batch_uri):
    info = {'code': 'v'}
    for automation_definition in configuration.automation_definitions:
        automation_uri = automation_definition.uri
        uri = automation_uri + batch_uri
        d = automation_definition.variable_definitions_by_mode_name
        for mode_name, variable_definitions in d.items():
            mode_code = MODE_CODE_BY_NAME[mode_name]
            mode_uri = MODE_ROUTE.format(mode_code=mode_code)
            folder = absolute_batch_folder / mode_name
            for variable_definition in variable_definitions:
                variable_id = variable_definition.id
                if variable_id != 'return_code':
                    info_uri = uri + mode_uri
                else:
                    info_uri = uri
                variable_info = info | {'id': variable_id, 'uri': info_uri}
                variable_configuration = variable_definition.configuration
                if 'path' in variable_configuration:
                    path = folder / variable_configuration['path']
                    memory.add(path, variable_info)
                path = folder / variable_definition.path
                memory.add(path, variable_info)


def add_template_infos(memory, configuration):
    info = {'code': 't'}
    for automation_definition in configuration.automation_definitions:
        automation_folder = automation_definition.folder
        automation_uri = automation_definition.uri
        template_info = info | {'uri': automation_uri}
        d = automation_definition.template_definitions_by_mode_name
        for mode_name, template_definitions in d.items():
            for template_definition in template_definitions:
                if 'path' not in template_definition:
                    continue
                path = automation_folder / template_definition.path
                memory.add(path, template_info)
        d = automation_definition.template_path_by_id
        for template_id, template_path in d.items():
            path = automation_folder / template_path
            memory.add(path, template_info)


def add_style_infos(memory, configuration):
    info = {'code': 's'}
    automation_definitions = configuration.automation_definitions
    for automation_definition in automation_definitions:
        automation_folder = automation_definition.folder
        for style_definition in automation_definition.style_definitions:
            if 'path' not in style_definition:
                continue
            path = automation_folder / style_definition['path']
            memory.add(path, info)
