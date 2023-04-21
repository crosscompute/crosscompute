# TODO: Return unvalidated configuration when there is an exception
# TODO: Watch multiple folders if not all under parent folder
from concurrent.futures import (
    ThreadPoolExecutor, as_completed)
from logging import getLogger
from pathlib import Path

from invisibleroads_macros_web.port import find_open_port

from ..constants import (
    AUTOMATION_PATH,
    HOST,
    MAXIMUM_PORT,
    MINIMUM_PORT,
    PORT,
    TOKEN_LENGTH)
from ..exceptions import (
    CrossComputeConfigurationError,
    CrossComputeConfigurationFormatError,
    CrossComputeConfigurationNotFoundError,
    CrossComputeDataError,
    CrossComputeError)
from ..macros.security import DictionarySafe
from ..settings import (
    StoppableProcess,
    multiprocessing_context)
from .configuration import load_configuration
from .interface import Automation
from .printer import (
    BatchPrinter,
    printer_by_name)
from .server import DiskServer
from .work import (
    prepare_automation,
    process_loop,
    run_automation)


class DiskAutomation(Automation):

    @classmethod
    def load(Class, path_or_folder=None):
        instance = Class()
        path_or_folder = Path(path_or_folder)
        if path_or_folder.is_dir():
            instance._initialize_from_folder(path_or_folder)
        else:
            instance._initialize_from_path(path_or_folder)
        return instance

    def run(self, environment, is_in=None, with_rebuild=True):
        definitions = self.definitions
        if is_in:
            definitions = [_ for _ in definitions if is_in(_)]
        for automation_definition in definitions:
            prepare_automation(automation_definition, with_rebuild)
        for automation_definition in definitions:
            run_automation(automation_definition, environment, with_rebuild)

    def serve(
            self, environment, host=HOST, port=PORT, with_restart=True,
            with_prefix=True, with_hidden=True, root_uri='',
            allowed_origins=None):
        with multiprocessing_context.Manager() as manager:
            safe = DictionarySafe(manager.dict(), TOKEN_LENGTH)
            uris = manager.list()
            tasks = manager.list()
            changes = manager.dict()
            DiskServer(
                process_loop, environment, safe,
                uris, tasks, changes,
                host, port, root_uri, allowed_origins,
                with_restart, with_prefix, with_hidden,
            ).watch(self.configuration, self._reload)

    def print(self, environment, view_name=None):
        port = find_open_port(
            minimum_port=MINIMUM_PORT, maximum_port=MAXIMUM_PORT)
        self.run(
            environment,
            is_in=lambda _: _.get_variable_definitions('print'))
        server_process = StoppableProcess(
            name='serve',
            target=self.serve,
            args=(environment,),
            kwargs={'port': port, 'with_restart': False})
        server_process.start()
        Printer = printer_by_name[view_name] if view_name else BatchPrinter
        try:
            batch_printer = Printer(f'http://127.0.0.1:{port}', is_draft=False)
            for automation_definition in self.definitions:
                batch_definitions = automation_definition.batch_definitions
                batch_printer.add(automation_definition, batch_definitions)
            batch_printer.run()
        except KeyboardInterrupt:
            pass
        except Exception as e:
            L.exception(e)
        finally:
            server_process.stop()

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


L = getLogger(__name__)
