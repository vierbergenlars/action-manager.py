from collections import OrderedDict

import pulsectl
import logging
from ..cycle import OrderedDictCycleAction
from .naming_map import description
from .sink_filter import all as sink_filter_all
from .sink_input_filter import all as sink_input_filter_all
from functools import partial

logger = logging.getLogger(__name__)

__all__ = ['PulseCtlDefaultSinkCycleAction']


class PulseProxy:
    class PulseServerInfo:
        def __init__(self, realobj, proxy):
            self.__realobj = realobj
            self.__proxy = proxy

        @property
        def default_sink_name(self):
            if self.__proxy._fake_default_sink_name is None:
                return self.__realobj.default_sink_name
            elif self.__realobj.default_sink_name == self.__proxy._real_default_sink_name:
                return self.__proxy._fake_default_sink_name
            else:
                return self.__realobj.default_sink_name

    def __init__(self, name, sink_filter: callable, sink_input_filter: callable):
        self.__pulse = pulsectl.Pulse(name)
        self.__sink_filter = partial(sink_filter, pulse=self)
        self.__sink_input_filter = partial(sink_input_filter, pulse=self)
        self._fake_default_sink_name = None
        self._real_default_sink_name = None

    def server_info(self):
        return self.PulseServerInfo(self.__pulse.server_info(), self)

    @property
    def __real_default_sink(self):
        default_sink_name = self.__pulse.server_info().default_sink_name
        return self.__find_sink_by(lambda sink: sink.name == default_sink_name)

    def sink_default_set(self, value: pulsectl.PulseSinkInfo):
        real_default_sink = self.__real_default_sink
        if not self.__sink_filter(real_default_sink):  # Current default sink is filtered out
            self._fake_default_sink_name = value.name  # Fake setting of default sink
            self._real_default_sink_name = real_default_sink.name  # Save real default sink
        else:  # Current default sink is not filtered out
            self.__pulse.sink_default_set(value)
            self._fake_default_sink_name = None
            self._real_default_sink_name = None

    def sink_list(self):
        return list(filter(self.__sink_filter, self.__pulse.sink_list()))

    def sink_info(self, *a, **k):
        return self.__pulse.sink_info(*a, **k)

    def sink_input_list(self):
        return list(filter(self.__sink_input_filter, self.__pulse.sink_input_list()))

    def sink_input_move(self, *a, **k):
        return self.__pulse.sink_input_move(*a, **k)

    def __find_sink_by(self, filter_: callable):
        return next(filter(filter_, self.__pulse.sink_list()))


class PulseCtlDefaultSinkCycleAction(OrderedDictCycleAction):
    """
    A cycle action that allows to select the pulseaudio fallback sink,
    and also moves active sink inputs to that sink.
    """
    def __init__(self, naming_map: callable = description, sink_filter: callable = sink_filter_all,
                 sink_input_filter: callable = sink_input_filter_all):
        """
        :param naming_map: A function that maps a sink object to a visual representation. Must accept an arbitrary number of keyword arguments
        :param sink_filter: A filter that is applied on all sinks to select the ones that should be shown.
            Must accept an arbitrary number of keyword arguments
            The fallback sink will only be changed when the current fallback sink is not filtered out.
        :param sink_input_filter: A filter that is applied on all sink inputs to select the ones that should be moved to the new fallback sink.
            Must accept an arbitrary number of keyword arguments
            Sink inputs that do not match the filter are never moved
        """
        self.__od = OrderedDict()
        super().__init__(self.__od)
        self.__pulse = PulseProxy(self.__class__.__name__, sink_filter=sink_filter,
                                  sink_input_filter=partial(sink_input_filter, sink_filter=sink_filter))
        self.__naming_func = partial(naming_map, pulse=self.__pulse)
        self.__update_items()
        self.current = self.__pulse.server_info().default_sink_name

    @OrderedDictCycleAction.current.setter
    def current(self, value):
        # if self.current == value:
        #    return
        if value not in self.__od:
            return

        while self.current != value:
            super().next()

        self.__update_default_sink()

    def __update_default_sink(self):
        default_sink = self.__od[self.current]

        self.__pulse.sink_default_set(default_sink)
        logger.debug('%s.__update_default_sink: Set default sink to %r', self.__class__.__name__, default_sink)
        for sink_input in self.__pulse.sink_input_list():
            try:
                self.__pulse.sink_input_move(sink_input.index, default_sink.index)
                logger.debug('%s.__move_sink_inputs: Moved sink input %r to sink %r', self.__class__.__name__,
                             sink_input, default_sink)
            except pulsectl.PulseOperationFailed:
                logger.exception('Failed moving sink input %d to sink %d', sink_input.index, default_sink.index)

    def __update_items(self):
        changed = False
        sinks = self.__pulse.sink_list()
        for sink in sinks:
            if sink.name not in self.__od:
                logger.debug('%s.__update_items: Added sink %r', self.__class__.__name__, sink)
                changed = True
            self.__od[sink.name] = sink
        to_delete = []
        for k, sink in self.__od.items():
            if sink not in sinks:
                logger.debug('%s.__update_items: Removed sink %r', self.__class__.__name__, sink)
                to_delete.append(k)
                changed = True
        for k in to_delete:
            del self.__od[k]

        default_name = self.__pulse.server_info().default_sink_name
        if self.current != default_name:
            self.current = default_name
            changed = True
        return changed

    def periodic(self):
        return self.__update_items()

    @property
    def items(self):
        self.__update_items()
        return map(self.__naming_func, super().items())

    def prev(self):
        super().prev()
        self.__update_default_sink()

    def next(self):
        super().next()
        self.__update_default_sink()

    def __str__(self):
        return self.__naming_func(self.__od[self.current])
