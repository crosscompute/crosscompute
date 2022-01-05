# TODO: Be explicit about relative vs absolute folders
# TODO: Precompile notebook scripts
import subprocess
from os import getenv, listdir
from os.path import isdir, join, relpath, splitext
from pyramid.config import Configurator
from time import time

from watchgod import watch
from .configuration import (
    get_automation_definitions,
    get_display_configuration,
    load_configuration,
    make_automation_name,
    prepare_batch)
from ..constants import (
    CONFIGURATION_EXTENSIONS,
    DISK_DEBOUNCE_IN_MILLISECONDS,
    DISK_POLL_IN_MILLISECONDS,
    HOST,
    PORT,
    STYLE_EXTENSIONS,
    # TEMPLATE_EXTENSIONS,
)
from ..macros import StoppableProcess, format_path, make_folder
from ..views import AutomationViews, EchoViews


    def get_app(self, automation_queue, is_static=False, base_uri=''):
        # TODO: Decouple from pyramid
        automation_views = AutomationViews(
            self.automation_definitions,
            automation_queue,
            self.timestamp_object)
        echo_views = EchoViews(
            self.automation_folder,
            self.timestamp_object)
        with Configurator() as config:
            config.include('pyramid_jinja2')
            config.include(automation_views.includeme)
            if not is_static:
                config.include(echo_views.includeme)

            def update_renderer_globals():
                renderer_environment = config.get_jinja2_environment()
                renderer_environment.globals.update({
                    'BASE_URI': base_uri,
                    'IS_STATIC': is_static,
                })

            config.action(None, update_renderer_globals)
        return config.make_wsgi_app()

    def watch(
            self, run_server, disk_poll_in_milliseconds,
            disk_debounce_in_milliseconds):
        server_process = StoppableProcess(target=run_server)
        server_process.start()
        for changes in watch(
                self.automation_folder,
                min_sleep=disk_poll_in_milliseconds,
                debounce=disk_debounce_in_milliseconds):
            for changed_type, changed_path in changes:
                # TODO: Continue only if path is in the configuration
                # TODO: Continue only if the file hash has changed
                L.debug('%s %s', changed_type, changed_path)
                changed_extension = splitext(changed_path)[1]
                if changed_extension in CONFIGURATION_EXTENSIONS:
                    server_process.stop()
                    # TODO: Try path then folder
                    self.initialize_from_path(self.configuration_path)
                    server_process = StoppableProcess(target=run_server)
                    server_process.start()
                elif changed_extension in STYLE_EXTENSIONS:
                    for d in self.automation_definitions:
                        d['display'] = get_display_configuration(d)
                    self.timestamp_object.value = time()
                # elif changed_extension in TEMPLATE_EXTENSIONS:
                    # self.timestamp_object.value = time()
                else:
                    # TODO: Send partial updates
                    self.timestamp_object.value = time()
