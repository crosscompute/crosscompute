# TODO: Return unvalidated configuration when there is an exception
# TODO: Watch multiple folders if not all under parent folder
from concurrent.futures import (
    ProcessPoolExecutor, ThreadPoolExecutor, as_completed)
from datetime import datetime
from logging import getLogger
from pathlib import Path
from time import sleep

from ..constants import (
    AUTOMATION_PATH,
    DISK_DEBOUNCE_IN_MILLISECONDS,
    DISK_POLL_IN_MILLISECONDS,
    HOST,
    PORT,
    TOKEN_LENGTH)
from ..exceptions import (
    CrossComputeConfigurationError,
    CrossComputeConfigurationFormatError,
    CrossComputeConfigurationNotFoundError,
    CrossComputeDataError,
    CrossComputeError)
from ..macros.security import DictionarySafe
from ..settings import multiprocessing_context
from .configuration import load_configuration
from .interface import Automation
from .server import DiskServer
from .work import (
    get_script_engine,
    process_loop,
    update_datasets)


class DiskAutomation(Automation):

    @classmethod
    def load(Class, path_or_folder=None):
        instance = Class()
        path_or_folder = Path(path_or_folder)
        if path_or_folder.is_dir():
            instance._initialize_from_folder(path_or_folder)
        else:
            instance._initialize_from_path(path_or_folder)
        with ThreadPoolExecutor() as executor:
            futures = []
            for automation_definition in instance.definitions:
                futures.extend(executor.submit(
                    _.get_command_string
                ) for _ in automation_definition.script_definitions)
            for future in as_completed(futures):
                future.result()
        return instance

    def run(self, environment, with_rebuild=True):
        for automation_definition in self.definitions:
            prepare_automation(automation_definition, with_rebuild)
        recurring_definitions = []
        for automation_definition in self.definitions:
            run_automation(
                automation_definition, environment, with_rebuild)
            if automation_definition.interval_timedelta:
                recurring_definitions.append(automation_definition)
        if not recurring_definitions:
            return
        while True:
            for automation_definition in recurring_definitions:
                last = automation_definition.interval_datetime
                delta = automation_definition.interval_timedelta
                if datetime.now() > last + delta:
                    run_automation(
                        automation_definition, environment, with_rebuild=False)
            sleep(1)

    def serve(
            self, environment, host=HOST, port=PORT, with_restart=True,
            with_prefix=True, with_hidden=True, root_uri='',
            allowed_origins=None,
            disk_poll_in_milliseconds=DISK_POLL_IN_MILLISECONDS,
            disk_debounce_in_milliseconds=DISK_DEBOUNCE_IN_MILLISECONDS):
        with multiprocessing_context.Manager() as manager:
            tasks = manager.list()
            changes = manager.dict()
            safe = DictionarySafe(manager.dict(), TOKEN_LENGTH)
            DiskServer(
                process_loop, environment, safe, tasks, changes, host, port,
                with_restart, with_prefix, with_hidden, root_uri,
                allowed_origins,
            ).watch(
                self.configuration,
                disk_poll_in_milliseconds,
                disk_debounce_in_milliseconds,
                self._reload)

    def _reload(self):
        path = self.path
        if path.exists():
            self._initialize_from_path(path)
        else:
            self._initialize_from_folder(self.folder)
        return self.configuration

    def _initialize_from_folder(self, folder):
        paths = list(folder.iterdir())
        default_automation_path = folder / AUTOMATION_PATH
        if default_automation_path in paths:
            paths.remove(default_automation_path)
            paths.insert(0, default_automation_path)
        for path in paths:
            if path.is_dir():
                continue
            try:
                self._initialize_from_path(path)
            except CrossComputeConfigurationFormatError:
                continue
            except (CrossComputeConfigurationError, CrossComputeDataError):
                raise
            except CrossComputeError:
                continue
            break
        else:
            raise CrossComputeConfigurationNotFoundError(
                'configuration not found')

    def _initialize_from_path(self, path):
        configuration = load_configuration(path)
        self.configuration = configuration
        self.path = path
        self.folder = configuration.folder
        self.definitions = configuration.automation_definitions


def prepare_automation(automation_definition, with_rebuild=True):
    engine = get_script_engine(automation_definition.engine_name, with_rebuild)
    engine.prepare(automation_definition)


def run_automation(automation_definition, user_environment, with_rebuild=True):
    ds = []
    run_batch = get_script_engine(
        automation_definition.engine_name, with_rebuild).run_batch
    concurrency_name = automation_definition.batch_concurrency_name
    update_datasets(automation_definition)
    try:
        if concurrency_name == 'single':
            ds.extend(_run_automation_single(
                automation_definition, run_batch, user_environment))
        else:
            ds.extend(_run_automation_multiple(
                automation_definition, run_batch, user_environment,
                concurrency_name))
    except CrossComputeError as e:
        e.automation_definition = automation_definition
        L.error(e)
    automation_definition.interval_datetime = datetime.now()
    return ds


def _run_automation_single(automation_definition, run_batch, user_environment):
    ds = []
    for batch_definition in automation_definition.batch_definitions:
        ds.append(run_batch(
            automation_definition, batch_definition, user_environment))
    return ds


def _run_automation_multiple(
        automation_definition, run_batch, user_environment, concurrency_name):
    ds = []
    if concurrency_name == 'thread':
        BatchExecutor = ThreadPoolExecutor
    else:
        BatchExecutor = ProcessPoolExecutor
    with BatchExecutor() as executor:
        futures = []
        for batch_definition in automation_definition.batch_definitions:
            futures.append(executor.submit(
                run_batch, automation_definition, batch_definition,
                user_environment))
        try:
            for future in as_completed(futures):
                ds.append(future.result())
        except KeyboardInterrupt:
            pass
    return ds


L = getLogger(__name__)
