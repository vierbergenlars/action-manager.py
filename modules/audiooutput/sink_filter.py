import pulsectl

__all__ = ['hardware_only', 'virtual_only', 'all']


def all(sink: pulsectl.PulseSinkInfo, **k) -> bool:
    """
    Selects all output devices
    """
    return True


def hardware_only(sink: pulsectl.PulseSinkInfo, **k) -> bool:
    """
    Selects hardware output devices
    """
    return sink.flags & 0x4 == 0x4


def virtual_only(sink: pulsectl.PulseSinkInfo, **k) -> bool:
    """
    Selects virtual output devices
    """
    return not hardware_only(sink)
