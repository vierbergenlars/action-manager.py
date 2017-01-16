import subprocess
import logging

from .core import AbstractControl, action

logger = logging.getLogger(__name__)


class RedshiftControl(AbstractControl):
    def __init__(self):
        super().__init__()
        self._redshift_proc = None

    def configure(self, argument_parser):
        argument_parser.add_argument('--redshift-location', help='LAT:LON Your current location', type=str)
        argument_parser.add_argument('--redshift-temperature',
                                     help='DAY:NIGHT Color temperature to set at daytime/night', type=str)

    def bind_arguments(self, args):
        super().bind_arguments(args)
        if self.enabled and not self.redshift_error_message:
            self.redshift_enabled = True

    @property
    def redshift_enabled(self) -> bool:
        return bool(self._redshift_proc)

    @property
    def redshift_error_message(self):
        if self.enabled and not (self.args.redshift_location or self.args.redshift_temperature):
            return "Missing parameter(s) --redshift-location and/or --redshift-temperature"
        if self._redshift_proc is not None and self._redshift_proc.returncode is not None and self._redshift_proc.returncode != 0:
            logger.error("Redshift process died unexpectedly: %s", self._redshift_proc.communicate())
            return self._redshift_proc.communicate()[1].replace("\n", ' ')
        return None

    @redshift_enabled.setter
    def redshift_enabled(self, value: bool) -> None:
        if value == self.redshift_enabled:
            return
        if value:
            logger.info("Starting redshift: -l %s -t %s", self.args.redshift_location, self.args.redshift_temperature)
            self._redshift_proc = subprocess.Popen(
                ['redshift', '-l', self.args.redshift_location, '-t', self.args.redshift_temperature], stdin=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        else:
            logger.info("Terminating running redshift process")
            self._redshift_proc.terminate()

    def periodic(self):
        if self._redshift_proc:
            self._redshift_proc.poll()
            if self._redshift_proc.returncode is not None:
                self._redshift_proc = None
                return True

    def respond_to(self, command):
        if command == 'redshift':
            self.redshift_enabled = not self.redshift_enabled
            return True
        return False

    def cleanup(self):
        self.redshift_enabled = False
        if self._redshift_proc:
            self._redshift_proc.wait()

    def __str__(self):
        if not self.redshift_error_message:
            return action(self.create_pipe_command('redshift'), 'R' if self.redshift_enabled else 'r')
        return 'E: ' + self.redshift_error_message

    def load_state(self, state):
        self.redshift_enabled = state['redshift_enabled']

    def dump_state(self):
        return {'redshift_enabled': self.redshift_enabled}
