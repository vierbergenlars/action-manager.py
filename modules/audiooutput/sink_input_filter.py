import pulsectl
import logging

__all__ = ['all', 'connected_sink']
logger = logging.getLogger(__name__)


def all(sink_input: pulsectl.PulseSinkInputInfo, **k) -> bool:
    """
    Selects all output devices
    """
    return True


def connected_sink(sink_input: pulsectl.PulseSinkInputInfo, sink_filter: callable, pulse: pulsectl.Pulse, **k) -> bool:
    """
    Selects all output devices that are attached to a sink matching a sink filter
    """
    sink = pulse.sink_info(sink_input.sink)
    return sink_filter(sink)
