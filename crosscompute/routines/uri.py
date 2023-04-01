import re

from ..constants import (
    STEP_CODE_BY_NAME)


def get_automation_slug(uri):
    match = AUTOMATION_PATTERN.match(uri)
    if not match:
        return
    return match.group(1)


def get_batch_slug(uri):
    match = BATCH_PATTERN.search(uri)
    if not match:
        return
    return match.group(1)


def get_step_code(uri):
    match = STEP_PATTERN.search(uri)
    if not match:
        return
    return match.group(1)


AUTOMATION_PATTERN = re.compile(r'/a/([^/]+)')
BATCH_PATTERN = re.compile(r'/b/([^/]+)')
STEP_PATTERN = re.compile(r'/([%s])$' % ''.join(STEP_CODE_BY_NAME.keys()))
