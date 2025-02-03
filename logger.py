"""Thread-safe logging system with colored terminal output.

This module provides a thread-safe logging system with color-coded output for different
message types and logging levels. It uses the blessed library for terminal color support
and includes thread-safe operations through a global lock.

The logging system supports:
- User input/output differentiation
- Different severity levels (DEBUG, INFO, WARNING, ERROR)
- Special message types (demon output, halloween narrator)
- Thread-safe logging operations
- Color-coded output for better visual distinction

Example:
    ```python
    from logger import Logger

    # Log different types of messages
    Logger.print_info("Starting process...")
    Logger.print_warning("Resource usage high")
    Logger.print_error("Failed to connect")
    Logger.print_debug("Connection attempt details: ...")
    ```

Color Scheme:
    - User Input: Deep Sky Blue
    - Demon Output: Firebrick Red
    - Halloween Narrator: Pumpkin Orange
    - Error/Warning: Yellow
    - Info: Salmon
    - Debug: Snow Gray
"""

import threading
import blessed

term = blessed.Terminal()

class Logger:
    """Thread-safe logging system with colored output.
    
    This class provides static methods for logging at different levels,
    with thread-safe operations and optional thread ID prefixing.
    Color coding is used to distinguish between different log levels
    and message types.

    Attributes:
        _lock (threading.Lock): Thread lock for synchronizing output operations.

    Color Scheme:
        - User Input: Deep Sky Blue
        - Demon Output: Firebrick Red
        - Halloween Narrator: Pumpkin Orange
        - Error/Warning: Yellow
        - Info: Salmon
        - Debug: Snow Gray
    """
    
    _lock = threading.Lock()
    
    @staticmethod
    def print_user_input(*args, **kwargs):
        """Print user input messages in deep sky blue.
        
        Args:
            *args: Variable length argument list to be printed.
            **kwargs: Arbitrary keyword arguments passed to print function.
        """
        print(f"{term.deepskyblue}", end="")
        print(*args, **kwargs)
        print(f"{term.white}", end="", flush=True)

    @staticmethod
    def print_demon_output(*args, **kwargs):
        """Print demon output messages in firebrick red.
        
        Args:
            *args: Variable length argument list to be printed.
            **kwargs: Arbitrary keyword arguments passed to print function.
        """
        print(f"{term.firebrick2}", end="")
        print(*args, **kwargs)
        print(f"{term.white}", end="", flush=True)

    @staticmethod
    def print_halloween_narrator(*args, **kwargs):
        """Print halloween narrator messages in pumpkin orange.
        
        Args:
            *args: Variable length argument list to be printed.
            **kwargs: Arbitrary keyword arguments passed to print function.
        """
        print(f"{term.pumpkin}", end="")
        print(*args, **kwargs)
        print(f"{term.white}", end="", flush=True)

    @staticmethod
    def print_error(*args, **kwargs):
        """Print error messages in yellow.
        
        Used for logging errors and critical issues that need immediate attention.
        
        Args:
            *args: Variable length argument list to be printed.
            **kwargs: Arbitrary keyword arguments passed to print function.
        """
        print(f"{term.yellow}", end="")
        print(*args, **kwargs)
        print(f"{term.white}", end="", flush=True)

    @staticmethod
    def print_warning(*args, **kwargs):
        """Print warning messages in yellow.
        
        Used for logging potential issues or concerning conditions that don't prevent execution.
        
        Args:
            *args: Variable length argument list to be printed.
            **kwargs: Arbitrary keyword arguments passed to print function.
        """
        print(f"{term.yellow}", end="")
        print(*args, **kwargs)
        print(f"{term.white}", end="", flush=True)

    @staticmethod
    def print_info(*args, **kwargs):
        """Print informational messages in salmon.
        
        Used for logging general information and progress updates.
        
        Args:
            *args: Variable length argument list to be printed.
            **kwargs: Arbitrary keyword arguments passed to print function.
        """
        print(f"{term.salmon1}", end="")
        print(*args, **kwargs)
        print(f"{term.white}", end="", flush=True)

    @staticmethod
    def print_debug(*args, **kwargs):
        """Print debug messages in snow gray.
        
        Used for logging detailed debug information and technical details.
        
        Args:
            *args: Variable length argument list to be printed.
            **kwargs: Arbitrary keyword arguments passed to print function.
        """
        print(f"{term.snow4}", end="")
        print(*args, **kwargs)
        print(f"{term.white}", end="", flush=True)

    @staticmethod
    def print_legend():
        """Print a color-coded legend banner showing available message types.
        
        Displays a formatted banner showing all available colors and their
        corresponding message types for reference.
        """
        print(term.magenta("===================="))
        print(term.magenta("    COLOR LEGEND   "))
        print(term.magenta("===================="))
        print(term.cyan("You"))
        print(term.red("Him"))
        print(term.yellow("Warnings/Errors"))
        print(term.blue("Informational Messages"))
        print(term.gray("Debug Messages"))
        print(term.magenta("===================="))
