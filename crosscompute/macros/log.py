from invisibleroads_macros_log import get_timestamp, LONGSTAMP_TEMPLATE


def get_longstamp():
    return get_timestamp(template=LONGSTAMP_TEMPLATE)
