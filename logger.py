# logger.py

import blessed
from load_config import ConfigLoader

term = blessed.Terminal()
config = ConfigLoader()

class Logger:

    @staticmethod
    def print_user_input(*args, **kwargs):
        Logger.print_helper(config.get('user_input_color'), *args, **kwargs)

    @staticmethod
    def print_ganglia_output(*args, **kwargs):
        Logger.print_helper(config.get('ganglia_output_color'), *args, **kwargs)

    @staticmethod
    def print_error(*args, **kwargs):
        Logger.print_helper(config.get('error_color'), *args, **kwargs)

    @staticmethod
    def print_info(*args, **kwargs):
        Logger.print_helper(config.get('info_color'), *args, **kwargs)

    @staticmethod
    def print_debug(*args, **kwargs):
        Logger.print_helper(config.get('debug_color'), *args, **kwargs)

    @staticmethod
    def print_helper(color_name, *args, **kwargs):
        color_method = getattr(term, color_name, term.white)
        print(f"{color_method}", end="")
        print(*args, **kwargs)
        print(f"{term.white}", end="", flush=True)

    @staticmethod
    def print_legend():
        """Prints a banner style legend"""
        print(term.magenta("===================="))
        print(term.magenta("    COLOR LEGEND   "))
        print(term.magenta("===================="))
        Logger.print_user_input(config.get("user_label"))
        Logger.print_ganglia_output(config.get("ganglia_label"))
        Logger.print_error("Warnings/Errors")
        Logger.print_info("Informational Messages")
        Logger.print_debug("Debug Messages")
        print(term.magenta("===================="))

