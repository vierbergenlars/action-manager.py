#!/usr/bin/env python3
import logging
import modules
import modules.core
from modules.audiooutput import PulseCtlDefaultSinkCycleAction
from modules.audiooutput import naming_map, sink_filter, sink_input_filter

#logging.basicConfig(level=logging.DEBUG)

modules.Application(
    modules.GroupedControl(
        modules.CaffeineControl(),
        modules.RedshiftControl(),
        separator=''
    ),
    modules.ActionWrapperControl(
        modules.VolumeControl(),
        action='pavucontrol',
        buttons=modules.core.Button.RIGHT
    ),
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
    )
).run()


