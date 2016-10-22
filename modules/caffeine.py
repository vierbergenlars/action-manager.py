import subprocess
import logging

import time

from .core import AbstractControl, action

logger = logging.getLogger(__name__)


class CaffeineControl(AbstractControl):
    def __init__(self):
        super().__init__()
        self.caffeine_enabled = False
        self._activity_proc = None
        self._activity_proc_lastrun = 0

    @property
    def enabled(self):
        return self.args.caffeine_enabled

    def configure(self, argument_parser):
        argument_parser.add_argument('--caffeine-enabled', help='Use the caffeine module', action='store_true')
        argument_parser.add_argument('--caffeine-timeout',
                                     help='Time between user activity reports to xscreensaver (in seconds)',
                                     type=int,
                                     default=10)

    def respond_to(self, command):
        if command == 'caffeine':
            self.caffeine_enabled = not self.caffeine_enabled
            logger.info("Set caffeine enabled %r", self.caffeine_enabled)
            return True

    def __str__(self):
        return action(self.create_pipe_command('caffeine'), 'C' if self.caffeine_enabled else 'c')

    def periodic(self):
        if self._activity_proc is not None:
            if self._activity_proc.returncode is None:
                self._activity_proc.poll()
            else:
                logger.debug("Reaped subprocess: %s", self._activity_proc)
                self._activity_proc = None

        if self.caffeine_enabled and self._activity_proc is None:
            if self._activity_proc_lastrun + self.args.caffeine_timeout < time.time():
                logger.debug("Poking screensaver")
                self._activity_proc = subprocess.Popen(['xscreensaver-command', '-deactivate'], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self._activity_proc_lastrun = time.time()

    def dump_state(self):
        return dict(caffeine_enabled=self.caffeine_enabled)

    def load_state(self, state):
        self.caffeine_enabled = state['caffeine_enabled']
