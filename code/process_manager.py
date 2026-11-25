import os

from shell_state import ShellState


def decode_wait_status(wait_status: int) -> int:
    """
    Convert an operating-system wait status into a shell exit status.
    """

    if os.WIFEXITED(wait_status):
        return os.WEXITSTATUS(wait_status)

    if os.WIFSIGNALED(wait_status):
        return 128 + os.WTERMSIG(wait_status)

    return 1


def wait_for_process(pid: int) -> int:
    """
    Wait for a specific child process to finish.

    Returns its shell-style exit status.
    """

    while True:
        try:
            waited_pid, wait_status = os.waitpid(pid, 0)

            if waited_pid == pid:
                return decode_wait_status(wait_status)

        except InterruptedError:
            # Retry if the system call was interrupted.
            continue


def reap_background_jobs(state: ShellState) -> list[tuple[int, str, int]]:
    """
    Check registered background jobs without blocking.

    Completed children are collected and removed from the
    active background_jobs dictionary.

    Returns a list of newly completed jobs.
    """

    completed = []

    # Use a snapshot because jobs may be removed during iteration.
    for pid, command in list(state.background_jobs.items()):

        try:
            waited_pid, wait_status = os.waitpid(pid, os.WNOHANG)

        except InterruptedError:
            continue

        except ChildProcessError:
            # Another part of the program already collected this child.
            state.remove_background_job(pid)
            continue

        except OSError:
            continue

        # A result of zero means the child is still running.
        if waited_pid == 0:
            continue

        exit_status = decode_wait_status(wait_status)

        state.remove_background_job(pid)

        job_result = (pid, command, exit_status)

        state.completed_jobs.append(job_result)
        completed.append(job_result)

    return completed
