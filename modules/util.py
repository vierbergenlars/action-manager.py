import sys
import os.path
from functools import wraps

import time

from .core import AbstractControl

__all__ = ['ChildReaperControl', 'QuitControl', 'backoff', 'process_reaper']

class QuitControl(AbstractControl):
    @property
    def visible(self):
        return False

    def respond_to(self, command):
        if command == 'q':
            sys.exit(0)
        elif command == 'refresh':
            return True


class ChildReaperControl(AbstractControl):
    @property
    def visible(self):
        return False

    def periodic(self):
        try:
            os.wait3(os.WNOHANG)
        except:
            pass


def backoff(backoff, default=None):
    def decorator(fn):
        last_called = 0

        @wraps(fn)
        def wrapper(*a, **kw):
            nonlocal last_called
            if last_called + backoff > time.time():
                return default
            last_called = time.time()
            return fn(*a, **kw)

        return wrapper

    return decorator


def process_reaper(fn):
    process = None

    @wraps(fn)
    def wrapper(*a, **kw):
        nonlocal process
        if process is not None:
            process.poll()
            if process.returncode is not None:
                process = None

        if process is None:
            process = fn(*a, **kw)

    return wrapper
