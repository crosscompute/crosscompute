from invisibleroads_macros_log import format_path


class CrossComputeError(Exception):

    def __str__(self):
        text = super().__str__()
        if hasattr(self, 'automation_definition'):
            automation_definition = self.automation_definition
            automation_name = automation_definition.name
            automation_version = automation_definition.version
            text += f' for {automation_name} {automation_version}'
        if hasattr(self, 'path'):
            text += f' in {format_path(self.path)}'
        return text


class CrossComputeConfigurationError(CrossComputeError):
    pass


class CrossComputeConfigurationNotFoundError(CrossComputeConfigurationError):
    pass


class CrossComputeConfigurationFormatError(CrossComputeError):
    pass


class CrossComputeDataError(CrossComputeError):
    pass


class CrossComputeExecutionError(CrossComputeError):
    pass
