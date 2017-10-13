#!/usr/bin/env python3
import logging
import modules
import modules.core
from modules.audiooutput import PulseCtlDefaultSinkCycleAction
from modules.audiooutput import naming_map, sink_filter, sink_input_filter
from modules.cycle import CycleControl
from modules.toggle import CommandToggleControl
from modules.functional import *

logging.basicConfig(level=logging.DEBUG)
#logging.getLogger('modules.core').setLevel(logging.WARNING)

modules.Application(
    modules.ScreenLayoutAction(name=partial(drop_from, '.')),
    modules.GroupedControl(
        modules.CaffeineControl(),
        modules.RedshiftControl(),
        separator=''
    ),
    modules.GroupedControl(
        CycleControl(
            PulseCtlDefaultSinkCycleAction(
                naming_map=partial(
                    foldr, [
                        naming_map.description,
                        partial(
                            drop_kwargs,
                            partial(foldr, [
                                partial(drop_first_if_eq, 'Built-in Audio '),
                                first_char
                            ])
                        )
                    ]
                ),
                sink_filter=sink_filter.hardware_only,
                sink_input_filter=sink_input_filter.connected_sink
            ),
        ),
#        modules.ActionWrapperControl(
#            CommandToggleControl('eq', ['pactl', 'load-module', 'module-equalizer-sink'], ['pactl', 'unload-module', 'module-equalizer-sink']),
#            action='qpaeq',
#            buttons=modules.core.Button.RIGHT
#        ),
        modules.ActionWrapperControl(
            modules.VolumeControl(),
            action='pavucontrol',
            buttons=modules.core.Button.RIGHT
        ),
        separator=' '
    )
).run()


