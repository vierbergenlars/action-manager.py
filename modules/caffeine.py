import subprocess
import logging

from .toggle import ToggleControl
from .util import process_reaper, backoff

__all__ = ['CaffeineControl']

logger = logging.getLogger(__name__)


class CaffeineControl(ToggleControl):
    def __init__(self, letter: str = 'c'):
        super().__init__(letter, False)

    def configure(self, argument_parser):
        argument_parser.add_argument('--caffeine-timeout',
                                     help='Time between user activity reports to xscreensaver (in seconds)',
                                     type=int,
                                     default=10)

    def bind_arguments(self, args):
        super().bind_arguments(args)
        self.periodic = process_reaper(backoff(self.args.caffeine_timeout)(self.__periodic))

    def __periodic(self):
        if self.state:
            logger.debug("Poking screensaver")
            return subprocess.Popen(['xscreensaver-command', '-deactivate'],
                                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
