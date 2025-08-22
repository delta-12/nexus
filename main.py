from menu import MenuContext
from menus import MAIN_MENU


def main() -> int:
    menu_context = MenuContext()
    menu_context.add_menu(MAIN_MENU)
    menu_context.show()

    return 0


if __name__ == "__main__":
    main()
