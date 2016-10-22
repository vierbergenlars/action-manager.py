#!/usr/bin/env python3
import logging
import modules
import modules.core

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
).run()


