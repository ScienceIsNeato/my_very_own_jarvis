# logger.py

# ANSI Color Code Globals
RESET_COLOR = '\033[0m'
BRIGHT_MAGENTA = '\033[95m'
BRIGHT_RED = '\033[91m'
YELLOW = '\033[93m'
GREEN = '\033[92m'
GREY = '\033[90m'
CYAN = '\033[96m'
RED = '\033[31m'
BLUE = '\033[34m'
WHITE = '\033[37m'

class Logger:

    @staticmethod
    def print_user_input(*args, **kwargs):
        print(f"{CYAN}", end="")
        print(*args, **kwargs)
        print(f"{RESET_COLOR}", end="", flush=True)

    @staticmethod
    def print_demon_output(*args, **kwargs):
        print(f"{RED}", end="")
        print(*args, **kwargs)
        print(f"{RESET_COLOR}", end="", flush=True)

    @staticmethod
    def print_error(*args, **kwargs):
        print(f"{YELLOW}", end="")
        print(*args, **kwargs)
        print(f"{RESET_COLOR}", end="", flush=True)

    @staticmethod
    def print_info(*args, **kwargs):
        print(f"{BLUE}", end="")
        print(*args, **kwargs)
        print(f"{RESET_COLOR}", end="", flush=True)

    @staticmethod
    def print_debug(*args, **kwargs):
        print(f"{GREY}", end="")
        print(*args, **kwargs)
        print(f"{RESET_COLOR}", end="", flush=True)

    @staticmethod
    def print_legend():
        """Prints a banner style legend"""

        # Define the maximum width for the output.
        MAX_WIDTH = 40

        def center_text(text, max_width):
            padding = max_width - len(text)
            left_padding = padding // 2
            right_padding = padding - left_padding
            return " " * left_padding + text + " " * right_padding

        print(f"{BRIGHT_MAGENTA}===================={RESET_COLOR}")
        print(f"{BRIGHT_MAGENTA}    COLOR LEGEND   {RESET_COLOR}")
        print(f"{BRIGHT_MAGENTA}===================={RESET_COLOR}")
        print(f"{CYAN}You{RESET_COLOR}")
        print(f"{RED}Him{RESET_COLOR}")
        print(f"{YELLOW}Warnings/Errors{RESET_COLOR}")
        print(f"{BLUE}Informational Messages{RESET_COLOR}")
        print(f"{GREY}Debug Messages{RESET_COLOR}")
        print(f"{BRIGHT_MAGENTA}===================={RESET_COLOR}")

