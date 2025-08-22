from menu import MenuContext
from menus import MainMenu


def main() -> int:
    menu_context = MenuContext()
    menu_context.add_menu(MainMenu())
    menu_context.show()

    return 0


if __name__ == "__main__":
    main()
