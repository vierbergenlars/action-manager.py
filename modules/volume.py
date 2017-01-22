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
        return self._volume / 90000.0

    @volume.setter
    def volume(self, volume):
        if volume < 0:
            logger.warning("Cannot set volume to %d, clamping to zero", volume)
            volume = 0
        if volume > 1.0:
            logger.warning("Cannot set volume to %d, clamping to one", volume)
            volume = 1.0
        if self.muted:
            self.muted = False
        if int(self._volume) != int(volume*90000):
            logger.info("Setting volume to %s", volume)
            if self._set_volume(volume):
                self._volume = int(volume*90000)

    def __init__(self):
        super().__init__()
        self._muted = False
        self._volume = 0

    def respond_to(self, command):
        if command[0] == '=':
            self.volume = int(command[1:])/10.0
        elif command == 'm1':
            self.muted = True
        elif command == 'm0':
            self.muted = False
        elif command == 'mt':
            self.muted = not self.muted
        elif command == '+':
            self.volume += 1/30.0
        elif command == '-':
            self.volume -= 1/30.0
        elif command == 'r':
            self.volume = 1/3.0
        else:
            return False
        return True

    def __str__(self):
        return action(
            self.create_pipe_command('+'),
            action(
                self.create_pipe_command('-'),
                self.action_bars(create_bars(self._volume) if not self.muted else '  (mute)  '),
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

    def _pactl(self, command, arg):
        logger.debug("Calling pactl: %s %s %s", command, '@DEFAULT_SINK@', arg)
        subprocess.check_call(["pactl", command, '@DEFAULT_SINK@', arg], stdin=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)


try:
    import pulsectl

    class PulseCtlVolumeControl(AbstractVolumeControl):
        def __init__(self):
            super().__init__()
            self.__pulse = pulsectl.Pulse(self.__class__.__name__)
            self.__default_sink = None
            self.periodic()

        def periodic(self):
            server_info = self.__pulse.server_info()
            self.__default_sink = next(filter(lambda sink: sink.name == server_info.default_sink_name, self.__pulse.sink_list()))
            prev_muted = self.muted
            self.muted = bool(self.__default_sink.mute)
            prev_volume = self.volume
            if not self.muted:
                self.volume = self.__default_sink.volume.value_flat
            return prev_muted != self.muted or prev_volume != self.volume

        def _set_muted(self, muted: bool) -> bool:
            self.__pulse.sink_mute(self.__default_sink.index, muted)
            return True

        def _set_volume(self, volume: float) -> bool:
            self.__default_sink.volume.value_flat = volume
            self.__pulse.sink_volume_set(self.__default_sink.index, self.__default_sink.volume)
            return True


    VolumeControl = PulseCtlVolumeControl
except ImportError:
    VolumeControl = PaCtlVolumeControl
