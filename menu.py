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
        self.main_menu = None

    def add_menu(self, menu: Menu) -> None:
        self.stack.push(menu)
        if self.main_menu is None:
            self.main_menu = menu

    def show(self) -> None:
        while not self.stack.is_empty():
            print("\033c")
            menu = self.stack.pop()
            print(menu.display())
            selection = input(menu.get_prompt())
            # TODO handle selection at context level if necessary (e.g. quit or return to main menu)
            valid = menu.on_select(selection)
            if valid:
                menu.on_update(self.stack)
                if self.stack.is_empty():
                    self.stack.push(self.main_menu)
            else:
                self.stack.push(menu)


class Choice:
    def __init__(
        self,
        title: str,
        callback: Callable | None = None,
        next_menu: Menu | None = None,
    ) -> None:
        self.title = title
        self.callback = callback
        self.next_menu = next_menu

    def get_title(self) -> str:
        return self.title

    def get_next_menu(self) -> Menu | None:
        return self.next_menu

    def on_select(self) -> None:
        if self.callback is not None:
            self.callback()


class ListMenu(Menu):
    def __init__(self, title: str, prompt: str, choices: list[Choice]) -> None:
        super().__init__(title, prompt)
        self.choices = choices
        self.selection = None
        self.index = None

    def on_display(self) -> str:
        choices = ""
        for index, choice in enumerate(self.choices):
            choices += f"    {index + 1}. {choice.get_title()}\n"
        return choices[:-1]

    def on_select(self, selection: str) -> bool:
        valid = True
        try:
            self.index = int(selection) - 1
            if self.index not in range(len(self.choices)):
                raise IndexError
            self.choices[self.index].on_select()
        except (ValueError, IndexError):
            valid = False
        return valid

    def on_update(self, stack: Stack) -> None:
        if self.index is not None and self.index in range(len(self.choices)):
            stack.push(self.choices[self.index].get_next_menu())


class TextMenu(Menu):
    def on_display(self) -> str:
        return ""
