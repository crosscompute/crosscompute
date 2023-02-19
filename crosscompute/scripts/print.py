from argparse import ArgumentParser
from logging import getLogger

from invisibleroads_macros_disk import make_folder, make_random_folder
from invisibleroads_macros_log import get_timestamp, LONGSTAMP_TEMPLATE
from invisibleroads_macros_web.port import find_open_port

from crosscompute.constants import (
    MAXIMUM_PORT,
    MINIMUM_PORT,
    PRINTER_BY_NAME)
from crosscompute.exceptions import (
    CrossComputeConfigurationError,
    CrossComputeError)
from crosscompute.routines.automation import (
    DiskAutomation, run_automation)
from crosscompute.routines.log import (
    configure_argument_parser_for_logging,
    configure_logging_from)
from crosscompute.routines.variable import (
    format_text,
    get_data_by_id_from_folder)
from crosscompute.scripts.configure import (
    configure_argument_parser_for_configuring)
from crosscompute.scripts.run import (
    configure_argument_parser_for_running,
    configure_running_from)
from crosscompute.scripts.serve import (
    configure_argument_parser_for_serving,
    configure_serving_from,
    serve_with)
from crosscompute.settings import (
    StoppableProcess)


def do(arguments=None):
    a = ArgumentParser()
    configure_argument_parser_for_logging(a)
    configure_argument_parser_for_configuring(a)
    configure_argument_parser_for_serving(a)
    configure_argument_parser_for_running(a)
    args = a.parse_args(arguments)
    try:
        configure_logging_from(args)
        configure_serving_from(args)
        configure_running_from(args)
        automation = DiskAutomation.load(args.path_or_folder)
        print_with(automation, args)
    except CrossComputeError as e:
        L.error(e)
        return


def configure_printing_from(args):
    print_folder = args.print_folder
    if print_folder:
        make_folder(print_folder)
    else:
        args.print_folder = make_random_folder()


def print_with(automation, args):
    try:
        port = find_open_port(
            minimum_port=MINIMUM_PORT, maximum_port=MAXIMUM_PORT)
    except OSError as e:
        raise CrossComputeError(e)
    timestamp = get_timestamp(template=LONGSTAMP_TEMPLATE)
    print_packs = []
    for automation_definition in get_selected_automation_definitions(
            automation.definitions):
        # TODO: Consider using ds returned from run_automation
        run_automation(
            automation_definition, args.environment, with_rebuild=True)
        for print_definition in automation_definition.print_definitions:
            batch_dictionaries = get_batch_dictionaries(
                automation_definition, print_definition, timestamp)
            print_packs.append((print_definition, batch_dictionaries))
    args.port = port
    args.with_browser = False
    args.with_restart = False
    server_process = StoppableProcess(
        name='serve', target=serve_with, args=(automation, args))
    server_process.start()
    try:
        for print_definition, batch_dictionaries in print_packs:
            Printer = PRINTER_BY_NAME[print_definition.format]
            printer = Printer(f'http://127.0.0.1:{port}{args.root_uri}')
            printer.render(batch_dictionaries, print_definition)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        L.exception(e)
    finally:
        server_process.stop()


def get_selected_automation_definitions(automation_definitions):
    selected_automation_definitions = []
    for automation_definition in automation_definitions:
        for print_definition in automation_definition.print_definitions:
            print_format = print_definition.format
            if print_format:
                break
        else:
            L.warning(
                'no print formats defined for %s %s',
                automation_definition.name, automation_definition.version)
            continue
        selected_automation_definitions.append(automation_definition)
    if not selected_automation_definitions:
        raise CrossComputeConfigurationError(
            'print format not defined in any automation definitions')
    return selected_automation_definitions


def get_batch_dictionaries(automation_definition, print_definition, timestamp):
    batch_dictionaries = []
    automation_uri = automation_definition.uri
    name = print_definition.name
    folder = print_definition.folder
    extra_data_by_id = {'timestamp': {'value': timestamp}}
    for batch_definition in automation_definition.batch_definitions:
        name_template = name or batch_definition.name
        data_by_id = get_data_by_id(
            automation_definition, batch_definition) | extra_data_by_id
        path = format_text(folder / name_template, data_by_id)
        batch_dictionaries.append({
            'path': path,
            'uri': automation_uri + batch_definition.uri})
    return batch_dictionaries


def get_data_by_id(automation_definition, batch_definition):
    automation_folder = automation_definition.folder
    batch_folder = batch_definition.folder
    absolute_batch_folder = automation_folder / batch_folder
    input_data_by_id = get_data_by_id_from_folder(
        absolute_batch_folder / 'input',
        automation_definition.get_variable_definitions('input'))
    output_data_by_id = get_data_by_id_from_folder(
        absolute_batch_folder / 'output',
        automation_definition.get_variable_definitions('output'))
    return input_data_by_id | output_data_by_id


L = getLogger(__name__)


if __name__ == '__main__':
    do()
