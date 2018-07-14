import functools
import os

import arrow

from . import config

cache_dir = os.path.join(os.path.dirname(__file__), '..', 'cache')


def get_path(filename: str) -> str:
    return os.path.join(cache_dir, filename)


@functools.wraps(open)
def get_file(filename: str, *args, **kwargs):
    return open(get_path(filename), *args, **kwargs)


def is_stale(filename: str) -> bool:
    """
    Return whether the current cached file is stale.

    A cached file is stale iff:
    - the cached file does not exist, or
    - the tally was updated before the cutoff, and either
    - the cutoff has passed and 1 minute has passed since the last update, or
    - 5 minutes have passed since the last update.
    """
    now = arrow.utcnow().floor('second')

    try:
        mtime = os.stat(get_path(filename)).st_mtime
    except FileNotFoundError:
        return True
    mtime = arrow.Arrow.utcfromtimestamp(mtime)

    cutoff = arrow.get(config.cutoff)

    return mtime < cutoff and mtime <= now.replace(minutes=-5 if now < cutoff else -1)


def day_html_is_stale() -> bool:
    return is_stale('%d.html' % config.day_id)


def day_text_is_stale() -> bool:
    return is_stale('%d.txt' % config.day_id)


def read_cache(filename: str) -> str:
    with get_file(filename) as f:
        return f.read()


def read_day_html() -> str:
    return read_cache('%d.html' % config.day_id)


def read_day_text() -> str:
    return read_cache('%d.txt' % config.day_id)


def write_cache(filename: str, contents: str):
    with get_file(filename, 'w') as f:
        f.write(contents)


def write_day_html(contents: str):
    write_cache('%d.html' % config.day_id, contents)


def write_day_text(contents: str):
    write_cache('%d.txt' % config.day_id, contents)
