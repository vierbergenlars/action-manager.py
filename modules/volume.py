import subprocess
import logging
import abc
import math

from .core import AbstractControl, action, Button

logger = logging.getLogger(__name__)


class AbstractVolumeControl(AbstractControl, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def _set_muted(self, muted: bool) -> bool:
        pass

    @abc.abstractmethod
    def _set_volume(self, volume: float) -> bool:
        pass

    @property
    def muted(self):
        return self._muted

    @muted.setter
    def muted(self, muted):
        if self._muted != muted:
            logger.info("Setting muted to %s", muted)
            if self._set_muted(muted):
                self._muted = muted

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, volume):
        if volume < 0:
            logger.warning("Cannot set volume to %d, clamping to zero", volume)
            volume = 0
        if volume > 90000:
            logger.warning("Cannot set volume to %d, clamping to 90000", volume)
            volume = 90000
        if self.muted:
            self.muted = False
        if self._volume != volume:
            logger.info("Setting volume to %s", volume)
            if self._set_volume(volume / 90000.0):
                self._volume = volume

    def __init__(self):
        super().__init__()
        self._muted = False
        self._volume = 0

    def respond_to(self, command):
        if command[0] == '=':
            self.volume = int(command[1:]) * 9000
        elif command == 'm1':
            self.muted = True
        elif command == 'm0':
            self.muted = False
        elif command == 'mt':
            self.muted = not self.muted
        elif command == '+':
            self.volume += 3000
        elif command == '-':
            self.volume -= 3000
        elif command == 'r':
            self.volume = 30000
        else:
            return False
        return True

    def __str__(self):
        return action(
            self.create_pipe_command('+'),
            action(
                self.create_pipe_command('-'),
                self.action_bars(create_bars(self.volume) if not self.muted else '  (mute)  '),
                button=Button.SCROLL_DOWN
            ),
            button=Button.SCROLL_UP
        )

    def action_bars(self, bars):
        return ''.join([action(self.create_pipe_command('=%d' % (i + 1)), c, button=Button.LEFT) for i, c in
                        zip(range(len(bars)), bars)])

    def load_state(self, state):
        self.volume = state['volume']
        self.muted = state['muted']

    def dump_state(self):
        return dict(volume=self.volume, muted=self.muted)


def create_bars(volume):
    num_bars = float(volume) / 9000.0
    return ('/' * math.floor(num_bars)) + partial_bar(num_bars - math.floor(num_bars)) + (
        ' ' * (10 - math.ceil(num_bars)))


def partial_bar(bar_size):
    if bar_size == 0.0:
        return ''
    elif bar_size < 0.3:
        return ' '
    elif bar_size < 0.6:
        return '.'
    elif bar_size < 0.9:
        return '-'
    return '/'


class PaCtlVolumeControl(AbstractVolumeControl):
    def _set_volume(self, volume: float) -> bool:
        try:
            self._pactl('set-sink-volume', str(int(volume*90000)))
            return True
        except subprocess.CalledProcessError:
            logger.exception("Error setting volume")
            return False

    def _set_muted(self, muted: bool) -> bool:
        try:
            self._pactl('set-sink-mute', str(int(muted)))
            return True
        except subprocess.CalledProcessError:
            logger.exception("Error setting mute")
            return False

    def _pa_get_sinks(self):
        return [l.split(b'\t')[0].decode() for l in
                subprocess.check_output(["pactl", "list", "short", "sinks"], stdin=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL).split(b'\n') if len(l) > 0]

    def _pactl(self, command, arg):
        for i in self._pa_get_sinks():
            logger.debug("Calling pactl: %s %s %s", command, i, arg)
            subprocess.check_call(["pactl", command, i, arg], stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

