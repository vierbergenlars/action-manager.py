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

try:
    import pyinotify
    logger.info('Inotify support enabled')
    class InotifyEventHandler(pyinotify.ProcessEvent):
        def my_init(self, action: callable):
            self.__action = action

        def process_default(self, event):
            logger.debug('Inotify received event.')
            self.__action()

    class Inotify:
        def __init__(self, directory, action):
            self.__directory = directory
            self.__wm = pyinotify.WatchManager()
            self.__notifier = pyinotify.ThreadedNotifier(self.__wm, default_proc_fun=InotifyEventHandler(action=action))
            self.__wd = None

        def start(self):
            self.__notifier.start()
            self.__wd = self.__wm.add_watch(self.__directory, pyinotify.IN_DELETE|pyinotify.IN_CREATE)[self.__directory]
            logger.debug('Added inotify watcher for %s', self.__directory)

        def stop(self):
            self.__wm.del_watch(self.__wd)
            self.__notifier.stop()
            logger.debug('Removed inotify watcher for %s', self.__directory)

except ImportError:
    logger.warn('pyinotify is not available, inotify support disabled')
    class Inotify:
        def __init__(self, *a, **k):
            pass

        def start(self):
            pass

        def stop(self):
            pass


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
        self.__inotify = None

    def configure(self, argument_parser: argparse.ArgumentParser):
        argument_parser.add_argument('--screenlayout-dir', help='Directory containing screenlayout shell files.', type=str)
        argument_parser.add_argument('--screenlayout-default', help='Default screenlayout shell file basename', type=str)

    @property
    def enabled(self):
        return self.args.screenlayout_dir is not None
    
    def bind_arguments(self, args):
        super().bind_arguments(args)
        self.__load_layouts(args.screenlayout_dir)
        self.__inotify = Inotify(args.screenlayout_dir, lambda: self.__load_layouts(args.screenlayout_dir))
        self.__inotify.start()
        if args.screenlayout_default:
            layout_dir = Path(args.screenlayout_dir)
            layout_default = layout_dir / args.screenlayout_default
            if not layout_default.exists():
                logger.error('Default layout %s does not exist in directory %s. Continuing without default', args.screenlayout_default, args.screenlayout_dir)
            else:
                self.__default_layout = str(layout_default)

    def cleanup(self):
        if self.__inotify:
            self.__inotify.stop()

    def next(self):
        super().next()
        logger.info("Setting screen layout to %s", self.current)
        self.__set_screen_layout(next_layout=self.next, item=self.current)
    
    def prev(self):
        super().prev()
        logger.info("Setting screen layout to %s", self.current)
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
            self.__set_screen_layout(next_layout=None, item=self.__default_layout)
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
                if next_layout:
                    logger.warning('Screenlayout failed, continueing to next layout.')
                    next_layout()
        except Exception:
            if next_layout:
                logger.exception('Screenlayout failed. Continueing to next layout')
                next_layout()

    def __create_tk(self):
        options = list(self.__od.keys())[1:] # Skip the first option, it is the current one
        num_options = len(options)
        cols=math.ceil(math.sqrt(num_options))
        rows = math.ceil(num_options / cols)
        root = tkinter.Tk(className="screenlayout")
        root.update_idletasks()
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        logger.debug("screen_width=%d; screen_height=%d", screen_width, screen_height)
        width = screen_width//3
        height = screen_height//3
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        logger.debug("geometry: width=%d, height=%d, x=%d, y=%d", width, height, x, y)
        root.geometry('{}x{}+{}+{}'.format(width, height, x, y))
        def create_callback(item):
            def cb():
                self.__inhibited = False
                current = self.current
                def restore_current():
                    self.__set_screen_layout(None, current)
                self.__set_screen_layout(restore_current, item)
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
