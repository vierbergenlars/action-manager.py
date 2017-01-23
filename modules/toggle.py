from .core import AbstractControl, WrappingControl, action
import abc


class ToggleAction(AbstractControl, metaclass=abc.ABCMeta):
    def __init__(self, initial_state: bool = False):
        super().__init__()
        self.__state = initial_state

    def dump_state(self):
        return {'state': self.__state}

    def load_state(self, state):
        if 'state' in state:
            self.state = state['state']

    def toggle(self):
        self.state = not self.state

    @property
    def state(self):
        return self.__state

    @state.setter
    def state(self, state: bool):
        if self.__state == state:
            return
        if state:
            self.enable()
        else:
            self.disable()
        self.__state = state

    def enable(self):
        pass

    def disable(self):
        pass


class ToggleControl(WrappingControl):
    """Implements a simple toggle button"""

    def __init__(self, letter: str, toggle_action: ToggleAction):
        super().__init__(toggle_action)
        self.__letter = letter

    def respond_to(self, command):
        if command == ':toggle':
            self.child.toggle()
            return True

    def __str__(self):
        return action(
            self.create_pipe_command(':toggle'),
            self.__letter.upper() if self.child.state else self.__letter.lower()
        )
