import os
import sys

from shell_state import ShellState


BUILTIN_NAMES = {
    "go",
    "quit",
    "path",
    "say",
    "info",
    "past",
    "osinfo",
    "export",
}


def _error(message: str) -> None:
    """Print a PyOsX error to standard error."""
    print(f"pyosx: {message}", file=sys.stderr)


def builtin_path(args: list[str], state: ShellState) -> int:
    """Print the current working directory."""
    print(os.getcwd())
    return 0


def builtin_quit(args: list[str], state: ShellState) -> int:
    """Stop the interactive shell."""

    if len(args) > 1:
        _error("usage: quit [status]")
        return 2

    status = 0

    if args:
        try:
            status = int(args[0])
            if not 0 <= status <= 255:
                raise ValueError
        except ValueError:
            _error("quit: status must be an integer between 0 and 255")
            return 2

    state.running = False
    return status


def builtin_go(args: list[str], state: ShellState) -> int:
    """Change the shell's current working directory."""

    if len(args) > 1:
        _error("usage: go [directory]")
        return 2

    if args:
        destination = args[0]
    else:
        destination = state.get_variable("HOME") or os.path.expanduser("~")

    destination = os.path.expanduser(destination)

    old_directory = os.getcwd()

    try:
        os.chdir(destination)
    except OSError as error:
        _error(f"go: {error}")
        return 1

    new_directory = os.getcwd()

    state.set_variable("OLDPWD", old_directory)
    state.set_variable("PWD", new_directory)

    return 0


def builtin_say(args: list[str], state: ShellState) -> int:
    """Print the supplied arguments."""
    print(" ".join(args))
    return 0


def builtin_info(args: list[str], state: ShellState) -> int:
    """Display available builtins and aliases."""

    print("BUILTINS:")
    for name in sorted(BUILTIN_NAMES):
        print(f"  {name}")

    print("\nALIASES:")
    print("  list    -> ls")
    print("  show    -> cat")
    print("  copy    -> cp")
    print("  move    -> mv")
    print("  del     -> rm")
    print("  newdir  -> mkdir")
    print("  newfile -> touch")

    return 0


def builtin_osinfo(args: list[str], state: ShellState) -> int:
    """Display the required course information."""
    print("Systèmes d'Exploitation -- UIR/ESIN")
    return 0


def builtin_past(args: list[str], state: ShellState) -> int:
    """Display commands recorded during the current session."""

    for index, command in enumerate(state.command_history, start=1):
        print(f"{index}  {command}")

    return 0


def builtin_export(args: list[str], state: ShellState) -> int:
    """Export one or more shell variables."""

    if not args:
        _error("usage: export NAME[=VALUE] ...")
        return 2

    try:
        for item in args:
            if "=" in item:
                name, value = item.split("=", 1)
                state.set_variable(name, value, export=True)
            else:
                state.export_variable(item)

    except ValueError as error:
        _error(f"export: {error}")
        return 1

    return 0


def run_builtin(args: list[str], state: ShellState) -> int | None:
    """
    Execute a builtin command.

    args includes the command name at index 0.

    Returns:
        int: command exit status if recognized.
        None: if the command is not a builtin.
    """

    if not args:
        return None

    command = args[0]
    operands = args[1:]

    builtins = {
        "path": builtin_path,
        "quit": builtin_quit,
        "go": builtin_go,
        "say": builtin_say,
        "info": builtin_info,
        "past": builtin_past,
        "osinfo": builtin_osinfo,
        "export": builtin_export,
    }

    function = builtins.get(command)

    if function is None:
        return None

    return function(operands, state)
