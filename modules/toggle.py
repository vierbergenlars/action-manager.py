import abc

from .core import AbstractControl, action

__all__ = ['ToggleControl']

class ToggleControl(AbstractControl, metaclass=abc.ABCMeta):
    """
    Implements a simple toggle button

    The toggle button will show a text in upper or lower case, depending on the activation state of the button.
    A click on the button toggles the button by calling toggle()
    """
    def __init__(self, letter: str, initial_state: bool = False):
        """
        :param letter: The text to show on the toggle control. Will be upper- or lowercased when the button is activated or deactivated.
        :param initial_state: The initial state of the button (used only when there is no saved data yet)
        """
        super().__init__()
        self.__letter = letter
        self.__state = initial_state

    def dump_state(self):
        return {'state': self.__state}

    def load_state(self, state):
        if 'state' in state:
            self.state = state['state']

    def toggle(self):
        """
        Called when the button is clicked.
        """
        self.state = not self.state

    @property
    def state(self) -> bool:
        """
        :return: The current toggle state of the button
        """
        return self.__state

    @state.setter
    def state(self, state: bool):
        """
        Updates state and triggers enable() or disable() methods when state changed
        """
        if self.__state == state:
            return
        if state:
            self.enable()
        else:
            self.disable()
        self.__state = state

    def enable(self):
        """
        Called when the toggle button is enabled
        """
        pass

    def disable(self):
        """
        Called when the toggle button is disabled
        """
        pass

    def respond_to(self, command):
        if command == ':toggle':
            self.toggle()
            return True

    def __str__(self):
        return action(
            self.create_pipe_command(':toggle'),
            self.__letter.upper() if self.state else self.__letter.lower()
        )
