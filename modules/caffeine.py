import subprocess
import logging


from modules.toggle import ToggleAction, ToggleControl
from .util import process_reaper, backoff

logger = logging.getLogger(__name__)


class CaffeineToggleAction(ToggleAction):
    def __init__(self):
        super().__init__(False)

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


def CaffeineControl():
    return ToggleControl('c', CaffeineToggleAction())
