import errno
import os
import signal

from shell_state import ShellState
from process_manager import decode_wait_status
from process_manager import wait_for_process

def _write_error(message: str) -> None:
    """Write an error directly to standard error."""
    try:
        os.write(2, (message + "\n").encode("utf-8", errors="replace"))
    except OSError:
        pass


def _exit_code(wait_status: int) -> int:
    """Convert a waitpid status into a shell-style exit status."""

    if os.WIFEXITED(wait_status):
        return os.WEXITSTATUS(wait_status)

    if os.WIFSIGNALED(wait_status):
        return 128 + os.WTERMSIG(wait_status)

    return 1


def _execute_in_child(args: list[str], environment: dict[str, str]) -> None:
    """
    Replace the current child process with an external program.

    This function must only be called after fork().
    """

    try:
        # An external program should receive normal Ctrl+C behavior.
        signal.signal(signal.SIGINT, signal.SIG_DFL)

        # Install the environment exported by PyOsX.
        os.environ.clear()
        os.environ.update(environment)

        # Replace the child process with the requested program.
        os.execvp(args[0], args)

    except OSError as error:
        if error.errno == errno.ENOENT:
            _write_error(
                f"pyosx: {args[0]}: command not found"
            )
            os._exit(127)

        if error.errno == errno.EACCES:
            _write_error(
                f"pyosx: {args[0]}: permission denied"
            )
            os._exit(126)

        _write_error(f"pyosx: {args[0]}: {error.strerror}")
        os._exit(126)




            def execute_external(args: list[str], state: ShellState) -> int:
                """Execute an external command and return its exit status."""
            
                if not args or not all(isinstance(arg, str) for arg in args):
                    _write_error("pyosx: invalid external command arguments")
                    return 2
            
                if not args[0]:
                    _write_error("pyosx: empty command name")
                    return 2
            
                try:
                    environment = state.get_exported_environment()
                except (AttributeError, TypeError) as error:
                    _write_error(f"pyosx: invalid shell state: {error}")
                    return 1
            
                previous_sigint = None
            
                # Temporarily protect the parent shell from Ctrl+C.
                try:
                    previous_sigint = signal.signal(signal.SIGINT, signal.SIG_IGN)
                except ValueError:
                    pass
            
                try:
                    # Create the child process.
                    try:
                        pid = os.fork()
            
                    except OSError as error:
                        _write_error(f"pyosx: fork failed: {error}")
                        return 1
            
                    if pid == 0:
                        # CHILD PROCESS
                        _execute_in_child(args, environment)
                        os._exit(126)
            
                    # PARENT PROCESS
                    try:
                        return wait_for_process(pid)
            
                    except ChildProcessError:
                        _write_error("pyosx: child process could not be collected")
                        return 1
            
                    except OSError as error:
                        _write_error(f"pyosx: waitpid failed: {error}")
                        return 1
            
                finally:
                    # Restore the parent's original SIGINT behavior.
                    if previous_sigint is not None:
                        signal.signal(signal.SIGINT, previous_sigint)
