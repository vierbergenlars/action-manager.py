from collections import OrderedDict
from .cycle import OrderedDictCycleAction, CycleControl
from .core import WrappingControl, action
from .util import process_reaper
import logging
import os
import stat
import subprocess
import argparse
try:
    import tkinter
except ImportError:
    tkinter = None
import math
import threading
import re
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_ITEMS_BEFORE_POPUP=3

class ScreenLayoutAction(WrappingControl):
    def __init__(self, *a, **k):
        self.__screen_layout_cycle = ScreenLayoutCycleAction(*a, **k)
        super().__init__(CycleControl(self.__screen_layout_cycle, scroll_actions=False))
 
    def __str__(self):
        parent = super().__str__()
        if tkinter is not None and len(self.__screen_layout_cycle) > MAX_ITEMS_BEFORE_POPUP:
            parent = re.sub(r'(?:<action=`[^`]+`(?: button=\d)?>)+([^<>]*)(?:<\/action>)+', r'\1', parent) # Clear all action tags
            parent = action(
                self.create_pipe_command('screenlayout'),
                parent
            )
 
        return parent

class ScreenLayoutCycleAction(OrderedDictCycleAction):
    def __init__(self, name: callable):
        self.__od = OrderedDict()
        super().__init__(self.__od)
        self.__inhibited = True
        self.__naming_func = name
        self.__default_layout = None

    def configure(self, argument_parser: argparse.ArgumentParser):
        argument_parser.add_argument('--screenlayout-dir', help='Directory containing screenlayout shell files.', type=str)
        argument_parser.add_argument('--screenlayout-default', help='Default screenlayout shell file basename', type=str)

    @property
    def enabled(self):
        return self.args.screenlayout_dir is not None
    
    def bind_arguments(self, args):
        super().bind_arguments(args)
        self.__load_layouts(args.screenlayout_dir)
        if args.screenlayout_default:
            layout_dir = Path(args.screenlayout_dir)
            layout_default = layout_dir / args.screenlayout_default
            if not layout_default.exists():
                logger.error('Default layout %s does not exist in directory %s. Continuing without default', args.screenlayout_default, args.screenlayout_dir)
            else:
                self.__default_layout = str(layout_default)


    def next(self):
        super().next()
        self.__set_screen_layout(next_layout=self.next, item=self.current)
    
    def prev(self):
        super().prev()
        self.__set_screen_layout(next_layout=self.prev, item=self.current)
    
    def periodic(self):
        if self.__inhibited:
            self.__inhibited = False
            self.__set_screen_layout(next_layout=self.next, item=self.current)
            return True
        return False

    def respond_to(self, command: str):
        if command == 'screenlayout':
            if tkinter is not None and len(self) > MAX_ITEMS_BEFORE_POPUP:
                threading.Thread(target=self.__create_tk()).start()
            else:
                self.next()
            return True
        elif command == 'screenlayout-reset':
            if not self.__default_layout:
                logger.error('Default layout is not set. Cannot reset layout')
                return False
            self.__inhibited = False
            self.__set_screen_layout(next_layout=lambda: None, item=self.__default_layout)
            return True
        else:
            return super().respond_to(command)

    def __str__(self):
        return self.__naming_func(super().__str__())

    def __load_layouts(self, directory):
        self.__od.clear()
        entries = os.scandir(directory)
        for entry in entries:
            if entry.is_file():
                mode = entry.stat().st_mode
                if mode & stat.S_IXUSR or mode & stat.S_IXGRP or mode & stat.S_IXOTH:
                    logger.debug('Found file %s', entry.path)
                    self.__od[entry.path] = entry.name

    def __set_screen_layout(self, next_layout, item):
        if self.__inhibited:
            logger.info('Screen layout is inhibited.')
            return
        logger.info('Starting screenlayout %s', item)
        try:
            layout_proc = subprocess.Popen([item])
            self.current = item
            if layout_proc.wait():
                logger.warning('Screenlayout failed, continueing to next layout.')
                next_layout()
        except Exception:
            logger.exception('Screenlayout failed. Continueing to next layout')
            next_layout()



    def __create_tk(self):
        options = list(self.__od.keys())[1:] # Skip the first option, it is the current one
        num_options = len(options)
        cols=math.ceil(math.sqrt(num_options))
        rows = math.ceil(num_options / cols)
        root = tkinter.Tk(className="screenlayout")
        root.update_idletasks()
        width = root.winfo_screenwidth()//3
        height = root.winfo_screenheight()//3
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        root.geometry('{}x{}+{}+{}'.format(width, height, x, y))
        def create_callback(item):
            def cb():
                self.__inhibited = False
                self.__set_screen_layout(lambda: None, item)
                root.destroy()
            return cb

        for i in range(0, cols):
            for j in range(0, rows):
                if i + cols * j < num_options:
                    item = options[i +  cols * j]
                    args = dict(
                        relx=i / cols,
                        rely=j / rows,
                        relwidth=1.0 / cols,
                        relheight=1.0 / rows,
                    )
                    button = tkinter.Button(root, text=self.__naming_func(self.__od[item]), command=create_callback(item)).place(**args)
        root.mainloop()
