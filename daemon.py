#!/usr/bin/env python3
import logging
import modules
import modules.core
from modules.audiooutput import PulseCtlDefaultSinkCycleAction
from modules.audiooutput import naming_map, sink_filter, sink_input_filter
from modules.cycle import *
from modules.toggle import CommandToggleControl

logging.basicConfig(level=logging.DEBUG)
logging.getLogger('modules.core').setLevel(logging.WARNING)

modules.Application(
    modules.GroupedControl(
        modules.CaffeineControl(),
        modules.RedshiftControl(),
        separator=''
    ),
    modules.GroupedControl(
        CycleControl(
            PulseCtlDefaultSinkCycleAction(
                naming_map=naming_map.partial(
                    naming_map.foldr, [
                        naming_map.description,
                        naming_map.partial(
                            naming_map.drop_kwargs,
                            naming_map.partial(naming_map.foldr, [
                                naming_map.partial(naming_map.drop_first_if_eq, 'Built-in Audio '),
                                naming_map.first_char
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


