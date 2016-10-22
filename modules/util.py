import sys
import os.path
from .core import AbstractControl


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

