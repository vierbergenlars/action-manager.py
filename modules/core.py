import abc
import os
import argparse

import sys
import enum
import logging

logger = logging.getLogger(__name__)


class AbstractControl(metaclass=abc.ABCMeta):
    """
    Base class for all modules
    """

    def __init__(self):
        """
        Creates a new control
        """
        self.args = None
        self.__name = None

    @property
    def visible(self):
        """
        Determines if the module is visible in the command bar

        :return: bool
        """
        return self.enabled

    @property
    def enabled(self):
        """
        Determines if the module is enabled.

        Disabled modules do not receive any signals.
        :return: bool
        """
        return True

    def configure(self, argument_parser: argparse.ArgumentParser):
        """
        Configures the argument parser to accept extra arguments handled by this module

        :param argument_parser: The argument parser to add arguments to
        :return: void
        """
        pass

    def bind_arguments(self, args: argparse.Namespace):
        """
        Binds arguments delivered by the argument parser to this module.

        When overriding this method, the parent function always has to be called.

        :param args:  The Namespace object returned by ArgumentParser.parse_args()
        :return: void
        """
        self.args = args

    def periodic(self):
        """
        Called periodically during the runtime of the daemon.

        Actions that are independent of user input should be handled here,
        use respond_to() to handle user input.

        Will only be called for modules that report to be enabled

        :return: bool Whether the displayed information is changed by the executed operations.
        """
        return False

    def cleanup(self):
        """
        Called during the shutdown of the daemon to clean up the module's resources.

        Will only be called for modules that report to be enabled
        :return: void
        """
        pass

    def respond_to(self, command: str):
        """
        Responds to a user command

        Actions that are dependent on user commands should be handled here,
        use periodic() to handle periodic actions independent of user input

        Will only be called for modules that report to be enabled
        :param command: The command received from the user
        :return: bool Whether the displayed information is changed by the executed operations.
        """
        return False

    def respond_to_ex(self, command: str):
        """
        Responds to a non-cleaned user command

        Namespaced commands still contain the namespace of this class, which has to be
        removed from the command before it is passed on to respond_to()

        :param command: The uncleaned command from the user
        :return: bool Whether the displayed information is changed by the executed operations.
        """
        logger.debug('%s.respond_to_ex: %s', self.__class__.__name__, command)
        if command[0] == ':':
            split_command = command.split(':', 2)
            if len(split_command) == 3:
                if split_command[1] != self.get_namespace():
                    logger.error('%s.respond_to_ex: Unsollicited command (mismatch %s <-> %s)', self.__class__.__name__, split_command[1], self.get_namespace())
                    return False
                command = ':' + split_command[2]
                logger.debug('%s.respond_to: %s', self.__class__.__name__, command)
                return self.respond_to(command)
            logger.warning('%s.respond_to_ex: Could not split into full command.', self.__class__.__name__)
        else:
            logger.debug('%s.respond_to: %s', self.__class__.__name__, command)
            return self.respond_to(command)

    def __str__(self):
        """
        Creates the string representation of the module to show on the action bar

        Will only be called for modules that report to be visible
        :return: str
        """
        return super().__str__()

    def load_state(self, state):
        """
        Loads state previously saved by this module

        State is loaded once at daemon startup, if there is a statefile present.

        Will only be called for modules that report to be enabled
        :param state: Whatever was returned by dump_state() on the previous run
        :return: void
        """
        pass

    def load_state_ex(self, state: dict):
        """
        Loads all state previously saved

        Usually this method filters the state of this module out of the global state to pass to load_state()

        Controls that wrap other controls typically want to override this function to pass the whole
        state to their children to avoid putting state in containers named after te wrapper.

        :param state: Dictionary containing the saved state
        :return: void
        """
        if self.__class__.__name__ in state:
            self.load_state(state[self.__class__.__name__])

    def dump_state(self):
        """
        Dumps current state of this module

        State is dumped once at daemon shutdown, if there is a statefile present.

        Will only be called for modules that report to be enabled
        :return: any pickleable object representing the state of this module
        """
        return None

    def dump_state_ex(self):
        """
        Dumps state of this module including unique identifying information for this module

        Controls that wrap other controls typically want to override this function to dump the whole
        state of their children to avoid putting state in containers named after te wrapper.

        Will only be called for modules that report to be enabled
        :return: dict
        """
        return {self.__class__.__name__: self.dump_state()}

    def get_namespace(self):
        """
        :return: The class-specific part of the namespace to use for namespaced commands. It cannot contain colons
        """
        return self.__class__.__name__

    def set_name(self, name: str):
        """
        Sets the namespace to use for namespaced commands

        This method may be overridden to customize the namespace used for the class
        It must call parent().set_name() with the desired name
        :param name: The namespace to use for namespaced commands
        """
        self.__name = name
        logger.debug('%s.set_name: Set name to %s', self.__class__.__name__, name)

    def set_name_ex(self, name: str):
        """
        Sets the namespace to use for namespaced commands

        This method must not be overridden
        :param name: Namespace used by the object one up the hierarchy
        """
        self.set_name('%s:%s' % (name, self.get_namespace()))

    def create_pipe_command(self, command: str):
        """
        Creates a shell command that will pass :command to the daemon through the controlpipe

        :param command: The command to pass
        :return: str Shell command that will pass the given command through the controlpipe
        """
        if command[0] == ':':
            command = self.__name + command
        return '{}/command.sh {} {}'.format(os.path.abspath(sys.path[0]), command,
                                            os.path.abspath(self.args.command_pipe.name))


class GroupedControl(AbstractControl):
    """
    Groups a set of modules into one module, separated by a given string
    """

    def __init__(self, *modules, separator=' | '):
        """
        Creates a new grouped control

        :param modules: Modules to group in this module, in the order they should be displayed
        :param separator: Separator string used inbetween two modules
        """
        super().__init__()
        self.__modules = modules
        self.__separator = separator

    def bind_arguments(self, args):
        super().bind_arguments(args)
        [m.bind_arguments(args) for m in self.__modules]

    @property
    def enabled(self):
        return any([m.enabled for m in self.__modules])

    @property
    def visible(self):
        return any([m.visible for m in self.__modules if m.enabled])

    def configure(self, argument_parser):
        [m.configure(argument_parser) for m in self.__modules]

    def load_state_ex(self, state):
        [m.load_state_ex(state) for m in self.__modules if m.enabled]

    def cleanup(self):
        [m.cleanup() for m in self.__modules if m.enabled]

    def respond_to(self, command):
        if command[0] != ':':
            return any([m.respond_to(command) for m in self.__modules if m.enabled])
        split_command = command.split(':', maxsplit=2)
        if len(split_command) == 3:
            index = int(split_command[1])
            return self.__modules[index].respond_to_ex(':' + split_command[2])

    def periodic(self):
        return any([m.periodic() for m in self.__modules if m.enabled])

    def dump_state_ex(self):
        data = dict()
        for m in self.__modules:
            if m.enabled:
                data.update(m.dump_state_ex())
        return data

    def set_name(self, name: str):
        super().set_name(name)
        [m.set_name_ex('%s:%d' % (name, i)) for i, m in enumerate(self.__modules)]

    def __passthrough_log(self, fn, s):
        logger.debug('%s.%s(): %s', self.__class__.__name__, fn, s)
        return s

    def __str__(self):
        return self.__separator.join([self.__passthrough_log('__str__', str(m)) for m in self.__modules if m.visible])


def action(command, text, **kwargs):
    """
    Creates an xmobar action tag

    :param command: The action (command to execute on click)
    :param text: The text where the action is applied upon
    :param kwargs: Extra parameters for the action tag (known case: button)
    :return: str The xmobar action tag
    """
    return '<action=`{}`{}>{}</action>'.format(command, ' ' + (
        ' '.join(['{}={}'.format(k, v) for k, v in kwargs.items()])) if len(kwargs) else '', text)


class WrappingControl(AbstractControl):
    """
    Generic wrapper for a module

    All method calls are passed through to the child module.
    This wrapper does not affect the state, it is passed through cleanly
    """

    def __init__(self, child_control: AbstractControl) -> None:
        """
        Creates a new module wrapper

        :param child_control: The child module to wrap
        """
        super().__init__()
        self.child = child_control

    def cleanup(self):
        self.child.cleanup()

    def dump_state_ex(self):
        return self.child.dump_state_ex()

    def load_state(self, state):
        self.child.load_state(state)

    def respond_to(self, command):
        return self.child.respond_to_ex(command)

    @property
    def enabled(self):
        return self.child.enabled

    def dump_state(self):
        self.child.dump_state()

    def configure(self, argument_parser):
        self.child.configure(argument_parser)

    def bind_arguments(self, args):
        super().bind_arguments(args)
        self.child.bind_arguments(args)

    @property
    def visible(self):
        return self.child.visible

    def periodic(self):
        return self.child.periodic()

    def load_state_ex(self, state):
        self.child.load_state_ex(state)

    def set_name(self, name: str):
        super().set_name(name)
        self.child.set_name_ex(name)

    def __str__(self):
        return self.child.__str__()


class ActionWrapperControl(WrappingControl):
    """
    Wraps a module output in an additional action
    """

    def __init__(self, control: AbstractControl, action: str, buttons: str = None) -> None:
        """
        Creates an action wrapper

        :param control: The module to wrap
        :param action: The shell command to execute when :buttons are pressed on the child module
        :param buttons: Optionally, which buttons will trigger the shell command (May be a Button, or a number of OR-ed buttons)
        """
        super().__init__(control)
        self.__action = action
        self.__buttons = buttons

    def __str__(self):
        if self.__buttons:
            return action(self.__action, super().__str__(), button=self.__buttons)
        else:
            return action(self.__action, super().__str__())


@enum.unique
class Button(enum.Enum):
    """
    A mouse button

    A set of multiple mouse buttons can be constructed by OR-ing buttons together
        e.g.: Button.LEFT|Button.RIGHT
    """
    LEFT = '1'
    MIDDLE = '2'
    RIGHT = '3'
    SCROLL_UP = '4'
    SCROLL_DOWN = '5'

    def __str__(self):
        return self.value

    def __or__(self, other):
        """
        Add multiple buttons together

        :param other: Button to add to this one
        :return: An set of multiple buttons
        """
        if isinstance(other, self.__class__):
            return _Buttons([self, other])
        return NotImplemented


class _Buttons(frozenset):
    """
    Internal class that represents a set of Button enums and that can be further chained with itself of another Button
    """

    def __str__(self):
        return ''.join([str(b) for b in self])

    def __or__(self, other):
        """
        Add another Button of _Buttons set to the set
        :param other: Button or _Buttons to add to this set of Buttons
        :return: The superset of this set of buttons and the other set of buttons
        """
        if isinstance(other, self.__class__):
            return _Buttons(self.union(other))
        elif isinstance(other, Button):
            return _Buttons(self.union({other}))
        return NotImplemented
