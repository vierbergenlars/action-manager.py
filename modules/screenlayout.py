from collections import OrderedDict
from .cycle import OrderedDictCycleAction
from .util import process_reaper
import logging
import os
import subprocess
import argparse

logger = logging.getLogger(__name__)

class ScreenLayoutCycleAction(OrderedDictCycleAction):
    def __init__(self, name: callable):
        self.__od = OrderedDict()
        super().__init__(self.__od)
        self.__inhibited = True
        self.__naming_func = name

    def configure(self, argument_parser: argparse.ArgumentParser):
        argument_parser.add_argument('--screenlayout-dir', help='Directory containing screenlayout shell files.', type=str)

    @property
    def enabled(self):
        return self.args.screenlayout_dir is not None
    
    def bind_arguments(self, args):
        super().bind_arguments(args)
        self.__load_layouts(args.screenlayout_dir)

    def next(self):
        super().next()
        self.__set_screen_layout(next_layout=self.next)
    
    def prev(self):
        super().prev()
        self.__set_screen_layout(next_layout=self.prev)
    
    def periodic(self):
        if self.__inhibited:
            self.__inhibited = False
            self.__set_screen_layout(next_layout=self.next)
            return True
        return False

    def __str__(self):
        return self.__naming_func(super().__str__())

    def __load_layouts(self, directory):
        entries = os.scandir(directory)
        for entry in entries:
            if entry.is_file():
                logger.debug('Found file %s', entry.path)
                self.__od[entry.path] = entry.name

    def __set_screen_layout(self, next_layout):
        if self.__inhibited:
            logger.info('Screen layout is inhibited.')
            return
        logger.info('Starting screenlayout %s', self.current)
        layout_proc = subprocess.Popen([self.current])
        if layout_proc.wait():
            logger.warning('Screenlayout failed, continueing to next layout.')
            next_layout()