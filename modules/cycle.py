import abc
from collections import OrderedDict

from .core import AbstractControl, WrappingControl, action, Button
import logging

__all__ = ['AbstractCycleAction', 'OrderedDictCycleAction', 'CycleControl', 'ExpandedCycleControlAction']
logger = logging.getLogger(__name__)


class AbstractCycleAction(AbstractControl, metaclass=abc.ABCMeta):
    """
    Base class for all cycle actions
    """

    @abc.abstractmethod
    def next(self):
        """
        Go to the next item in the cycle
        """
        pass

    @abc.abstractmethod
    def prev(self):
        """
        Go to the previous item in the cycle
        """
        pass

    @abc.abstractproperty
    def current(self) -> object:
        """
        :return: An unique identifier for the current item in the cycle
        """
        return None

    @abc.abstractproperty
    def items(self):
        """
        :return: An iterator over all items in the cycler, as tuples of unique identifier to string representation
        """
        return iter([])

    def load_state(self, state):
        if 'current' in state:
            prev_current = self.current
            while self.current != state['current']:
                self.next()
                if prev_current == state['current']:
                    logger.warning('%s.load_state: Saved item is not present in cycle.', self.__class__.__name__)
                    break

    def dump_state(self):
        return {'current': self.current}

    def __str__(self):
        """
        :return: The visual representation of the current item in the cycle
        """
        return self.current


class OrderedDictCycleAction(AbstractCycleAction):
    """
    A cycle action that cycles through an ordered dictionary.
    Dictionary keys are used as unique identifiers, dictionary values are their visual represenation
    """
    def __init__(self, items: OrderedDict = None):
        super().__init__()
        self.__items = items if items is not None else OrderedDict()

    def prev(self):
        # prev: a b c -> c a b
        #       ^        ^
        #       Move last item to front
        for k in reversed(self.__items.keys()):
            self.__items.move_to_end(k, last=False)
            break

    def next(self):
        # next: a b c -> b c a
        #       ^        ^
        #       Move first item to back
        for k in self.__items.keys():
            self.__items.move_to_end(k)
            break

    @property
    def items(self):
        return iter(self.__items.items())

    @property
    def current(self):
        for k in self.__items.keys():
            return k

    @property
    def visible(self):
        return len(self.__items) > 1

    def __str__(self):
        return self.__items[self.current]


class CycleControl(WrappingControl):
    """
    Implements a simple cycle control.

    When clicked or scrolled over it changes to the previous/next value in a circular fashion.
    """

    def __init__(self, cycle_action: AbstractCycleAction):
        super().__init__(cycle_action)

    def respond_to(self, command: str):
        if command == ':next':
            self.child.next()
            return True
        elif command == ':prev':
            self.child.prev()
            return True

    def __str__(self):
        return action(
            command=self.create_pipe_command(':next'),
            button=Button.LEFT | Button.SCROLL_UP,
            text=action(
                command=self.create_pipe_command(':prev'),
                button=Button.RIGHT | Button.SCROLL_DOWN,
                text=str(self.child)
            )
        )


class ExpandedCycleControlAction(WrappingControl, AbstractCycleAction):
    """
    An expanded cycler that always shows all items in its child cycler, separated by a separator.

    Every item is clickable separately and will force a jump to that state.
    """
    def __init__(self, child_action: AbstractCycleAction, separator: str = ''):
        super().__init__(child_action)
        self.__separator = separator

    def next(self):
        self.child.next()

    def prev(self):
        self.child.prev()

    @property
    def items(self):
        return self.child.items

    @property
    def current(self):
        return self.child.current

    def __get_control_command(self, item_key):
        return ':set:%s' % item_key

    def respond_to(self, command: str):
        for item_key, _ in self.items:
            if command == self.__get_control_command(item_key):
                prev_current = self.current
                while self.current != item_key:
                    self.next()
                    if self.current == prev_current:
                        logger.error('%s.respond_to: Item %s not found in cycle.', self.__class__.__name__, item_key)
                return True

    def __str__(self):
        return self.__separator.join([action(
            command=self.create_pipe_command(self.__get_control_command(item_key)),
            button=Button.LEFT,
            text=item_value
        ) for item_key, item_value in self.items])
