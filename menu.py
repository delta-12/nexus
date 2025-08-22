from abc import ABC, abstractmethod
from collections import deque
from typing import Any, Callable


class Stack:
    def __init__(self) -> None:
        self.stack = deque()

    def is_empty(self) -> bool:
        return 0 == len(self.stack)

    def push(self, value: Any) -> None:
        self.stack.append(value)

    def pop(self) -> Any:
        value = None
        if not self.is_empty():
            value = self.stack.pop()
        return value

    def peek(self) -> Any:
        value = None
        if not self.is_empty():
            value = self.stack[-1]
        return value


class Menu(ABC):
    def __init__(self, title: str, prompt: str) -> None:
        self.title = title
        self.prompt = prompt

    @abstractmethod
    def on_display(self) -> str:
        return ""

    @abstractmethod
    def on_select(self, selection: str) -> bool:
        return False

    @abstractmethod
    def on_update(self, stack: Stack) -> None:
        return

    def get_prompt(self) -> str:
        return self.prompt

    def display(self) -> str:
        return f"{self.title}\n{self.on_display()}"


class MenuContext:
    def __init__(self) -> None:
        self.stack = Stack()

    def add_menu(self, menu: Menu) -> None:
        self.stack.push(menu)

    def show(self) -> None:
        while not self.stack.is_empty():
            menu = self.stack.pop()
            print(menu.display())
            selection = input(menu.get_prompt())
            # TODO handle selection at context level if necessary (e.g. quit or return to main menu)
            valid = menu.on_select(selection)
            if valid:
                menu.on_update(self.stack)
            else:
                self.stack.push(menu)


class ListMenu(Menu):
    def __init__(
        self, title: str, prompt: str, choices: dict[str, Callable | None]
    ) -> None:
        super().__init__(title, prompt)
        self.choices = choices
        self.selection = None
        self.index = None

    def on_display(self) -> str:
        choices = ""
        for index, choice in enumerate(self.choices):
            choices += f"    {index + 1}. {choice}\n"
        return choices[:-1]

    def on_select(self, selection: str) -> bool:
        valid = True
        try:
            self.index = int(selection) - 1
            if self.index not in range(len(self.choices)):
                raise IndexError
            callback = list(self.choices.values())[self.index]
            if callback is not None:
                callback()
        except (ValueError, IndexError):
            valid = False
        return valid


class TextMenu(Menu):
    def on_display(self) -> str:
        return ""
