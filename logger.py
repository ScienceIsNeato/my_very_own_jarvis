# logger.py

import blessed

term = blessed.Terminal()

class Logger:

    @staticmethod
    def print_user_input(*args, **kwargs):
        print(f"{term.deepskyblue}", end="")
        print(*args, **kwargs)
        print(f"{term.white}", end="", flush=True)

    @staticmethod
    def print_demon_output(*args, **kwargs):
        print(f"{term.firebrick2}", end="")
        print(*args, **kwargs)
        print(f"{term.white}", end="", flush=True)

    @staticmethod
    def print_halloween_narrator(*args, **kwargs):
        print(f"{term.pumpkin}", end="")
        print(*args, **kwargs)
        print(f"{term.white}", end="", flush=True)

    @staticmethod
    def print_error(*args, **kwargs):
        print(f"{term.yellow}", end="")
        print(*args, **kwargs)
        print(f"{term.white}", end="", flush=True)

    @staticmethod
    def print_warning(*args, **kwargs):
        print(f"{term.yellow}", end="")
        print(*args, **kwargs)
        print(f"{term.white}", end="", flush=True)

    @staticmethod
    def print_info(*args, **kwargs):
        print(f"{term.salmon1}", end="")
        print(*args, **kwargs)
        print(f"{term.white}", end="", flush=True)

    @staticmethod
    def print_debug(*args, **kwargs):
        print(f"{term.snow4}", end="")
        print(*args, **kwargs)
        print(f"{term.white}", end="", flush=True)

    @staticmethod
    def print_legend():
        """Prints a banner style legend"""
        print(term.magenta("===================="))
        print(term.magenta("    COLOR LEGEND   "))
        print(term.magenta("===================="))
        print(term.cyan("You"))
        print(term.red("Him"))
        print(term.yellow("Warnings/Errors"))
        print(term.blue("Informational Messages"))
        print(term.gray("Debug Messages"))
        print(term.magenta("===================="))

