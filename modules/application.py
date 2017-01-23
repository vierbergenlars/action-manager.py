import argparse
import pickle
import signal
import logging

import time
import traceback

from .core import GroupedControl
from .util import QuitControl, ChildReaperControl
import os
import stat

logger = logging.getLogger(__name__)


class CreateFileType(argparse.FileType):
    def __init__(self, mode='r', bufsize=-1, encoding=None, errors=None):
        super().__init__(mode, bufsize, encoding, errors)
        self.__mode = mode
        self.__bufsize = bufsize
        self.__encoding = encoding
        self.__errors = errors

    def __call__(self, string):
        try:
            return super().__call__(string)
        except argparse.ArgumentTypeError as e:
            return open(string, 'wb' if 'b' in self.__mode else 'w', self.__bufsize, self.__encoding, self.__errors)


class PipeFileType(argparse.FileType):
    def __init__(self, *args, lazy=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.lazy = lazy

    def __call__(self, string):
        try:
            mode = os.stat(string).st_mode
            if not stat.S_ISFIFO(mode):
                raise argparse.ArgumentTypeError('%s is not a fifo' % strign)
        except FileNotFoundError:
            pass
        if not self.lazy or string == '-':
            return super().__call__(string)
        else:
            return LazyFile(string, self._mode, self._bufsize, self._encoding, self._errors)

class LazyFile:
    def __init__(self, name, *args):
        self.name = name
        self.__args = args
        self.__file = None
    def __open(self):
        if self.__file is None:
            self.__file = open(self.name, *self.__args)
        return self.__file
    def close(self):
        return self.__open().close()
    @property
    def closed(self):
        return self.__open().closed
    def fileno(self):
        return self.__open().fileno()
    def flush(self):
        return self.__open().flush()
    def isatty(self):
        return self.__open().isatty()
    def read(self, *a):
        return self.__open().read(*a)
    def readable(self):
        return self.__open().readable()
    def readline(self):
        return self.__open().readline()
    def readlines(self):
        return self.__open().readlines()
    def seek(self):
        return self.__open().seek()
    def seekable(self):
        return self.__open().seekable()
    def tell(self):
        return self.__open().tell()
    def truncate(self):
        return self.__open().truncate()
    def writable(self):
        return self.__open().writable()
    def write(self, *a):
        return self.__open().write(*a)
    def writelines(self, *a):
        return self.__open().writelines(*a)


class Application(GroupedControl):
    def __init__(self, *modules, **kwargs):
        super().__init__(ChildReaperControl(), *modules, **kwargs)

    def configure(self, argument_parser):
        argument_parser.add_argument('output_pipe', type=PipeFileType('w', bufsize=1, lazy=True))
        argument_parser.add_argument('command_pipe', type=PipeFileType('r', bufsize=1, lazy=True))
        argument_parser.add_argument('--state-file', type=CreateFileType('r+b'))
        super().configure(argument_parser)

    def bind_arguments(self, args):
        super().bind_arguments(args)
        if args.state_file is not None and args.state_file.readable():
            try:
                state = pickle.load(args.state_file)
                logger.info("Loaded state: %r" % state)
                self.load_state_ex(state)
            except:
                traceback.print_exc()

    def cleanup(self):
        if self.args.state_file is not None:
            self.args.state_file.seek(0)
            self.args.state_file.truncate()
            state = self.dump_state_ex()
            logger.info("Dumped state: %r" % state)
            pickle.dump(state, self.args.state_file)
            self.args.state_file.close()

        super().cleanup()

    def respond_to_ex(self, command):
        if command == '':
            return False
        logger.info('Received command %s', command)
        return super().respond_to_ex(command)

    def handle_signal(self, signal, tb):
        raise Exception("Received signal %s"%signal)


    def run(self):
        parser = argparse.ArgumentParser(description='Action manager for xmobar')

        self.set_name_ex('')
        self.configure(parser)
        self.bind_arguments(parser.parse_args())

        for sig in {signal.SIGHUP, signal.SIGINT, signal.SIGQUIT, signal.SIGTERM}:
            signal.signal(sig, self.handle_signal)

        try:
            self.args.output_pipe.writelines(str(self)+"\n")
            while True:
                if self.respond_to_ex(str.rstrip(self.args.command_pipe.readline())) or self.periodic():
                    self.args.output_pipe.writelines(str(self) + "\n")
                else:
                    time.sleep(1)
        except BaseException as e:
            logger.exception('Received exception, shutting down')
        finally:
            self.cleanup()
