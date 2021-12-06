from crosscompute.constants import (
    AUTOMATION_NAME,
    AUTOMATION_VERSION,
    CONFIGURATION)


def do():
    configuration = CONFIGURATION.copy()
    automation_name = input(
        'automation_name [%s]: ' % AUTOMATION_NAME)
    automation_version = input(
        'automation_version [%s]: ' % AUTOMATION_VERSION)
    configuration['name'] = automation_name or AUTOMATION_NAME
    configuration['version'] = automation_version or AUTOMATION_VERSION
    print(configuration)


if __name__ == '__main__':
    do()
