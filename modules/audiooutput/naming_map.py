import pulsectl
from ..functional import *


def description(sink: pulsectl.PulseSinkInfo, **k) -> str:
    """
    Uses the description property as naming
    """
    return sink.description

