import os
import signal
import sys

from process_manager import reap_background_jobs
from shell_state import ShellState


def _write_error(message: str) -> None:
    """Write an error directly to standard error."""

    try:
        os.write(
            2,
            (message + "\n").encode("utf-8", errors="replace")
        )
    except OSError:
        pass


def install_sigchld_handler(state: ShellState):
    """
    Install a handler that collects completed background jobs.

    Must be called from the main Python thread.
    Returns the previous SIGCHLD handler.
    """

    previous_handler = signal.getsignal(signal.SIGCHLD)

    def handle_sigchld(signum, frame):
        reap_background_jobs(state)

    signal.signal(signal.SIGCHLD, handle_sigchld)

    return previous_handler


def execute_background(tokens, state: ShellState, runner) -> int:
    """
    Launch a command in the background.

    The child executes the supplied runner callback.
    The parent registers the child and immediately returns.

    Returns:
        0 on successful launch.
        1 on process creation failure.
        2 on invalid arguments.
    """

    if not tokens:
        _write_error("pyosx: background command is empty")
        return 2

    if not callable(runner):
        _write_error("pyosx: invalid background command runner")
        return 2

    # Construct a readable command description.
    command = " ".join(token.value for token in tokens)

    # Flush inherited buffers before fork().
    sys.stdout.flush()
    sys.stderr.flush()

    # Prevent SIGCHLD from being handled before the parent
    # registers the new process in ShellState.
    old_mask = signal.pthread_sigmask(
        signal.SIG_BLOCK,
        {signal.SIGCHLD}
    )

    try:
        pid = os.fork()

    except OSError as error:
        signal.pthread_sigmask(signal.SIG_SETMASK, old_mask)
        _write_error(f"pyosx: background fork failed: {error}")
        return 1

    if pid == 0:
        # CHILD PROCESS

        try:
            # Restore normal signal behavior in the child.
            signal.signal(signal.SIGINT, signal.SIG_DFL)
            signal.signal(signal.SIGCHLD, signal.SIG_DFL)

            # Restore the signal mask inherited from the parent.
            signal.pthread_sigmask(signal.SIG_SETMASK, old_mask)

            # Give the background job its own process group.
            os.setpgid(0, 0)

            # Run the command through the dispatcher's callback.
            status = runner(tokens)

            if not isinstance(status, int):
                status = 1

        except BaseException as error:
            _write_error(f"pyosx: background execution failed: {error}")
            status = 1

        # Flush output produced by builtins or the callback.
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except OSError:
            pass

        # Terminate the child without running copied Python cleanup.
        os._exit(status & 0xFF)

    # PARENT PROCESS

    try:
        # The child also calls setpgid() to avoid a race.
        os.setpgid(pid, pid)

    except OSError:
        # The child may have already exited or changed its group.
        pass

    try:
        # Register before allowing the SIGCHLD handler to run.
        state.register_background_job(pid, command)

    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, old_mask)

    print(f"[{pid}] {command}", flush=True)

    # The shell does not wait for the background process.
    return 0
