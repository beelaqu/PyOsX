"""
io_helpers.py - reusable file-descriptor helpers for PyOsX

Every process has a table of file descriptors FD:
    0 = stdin    1 = stdout    2 = stderr
This module wraps the few operations the rest of the I/O code needs:
    - flush_std()      empty Python's output buffers
    - safe_close()     close a descriptor without crashing if it is invalid
    - redirect_fd()    "make descriptor B point to the same file as descriptor A"
    - saved_stdio()    save FDs, let the caller change them, then restore them

This module does not know anything about parsing, builtins or processes,
so redirections.py and pipelines.py can reuse it freely.
"""
import os
import sys
from contextlib import contextmanager

STDIN, STDOUT, STDERR = 0, 1, 2


def flush_std():
    """Flush Python's own stdout/stderr buffers.

    print() does not write to descriptor 1 immediately: Python keeps the text
    in a buffer. Two situations need an explicit flush:
      - before fork(): otherwise parent AND child would each print the text;
      - before restoring descriptor 1: otherwise the text would go to the
        restored (screen) descriptor instead of the redirected file.
    """
    for stream in (sys.stdout, sys.stderr): 
        try:
            stream.flush()
        except (OSError, ValueError):
            pass


def safe_close(fd):
    """Close fd if it is not None; ignore errors (already closed, invalid...)."""
    if fd is None:
        return
    try:
        os.close(fd)
    except OSError:
        pass


def close_all(fds):
    """Close every descriptor of an iterable (None entries are skipped)."""
    for fd in fds:
        safe_close(fd)


def redirect_fd(fd, target):
    """Make descriptor `target` refer to the same open file as `fd`, then
    close `fd`, which is no longer needed.

    os.dup2(fd, target) closes `target` if it was open, then makes it a copy of
    `fd`. Both numbers now point to the same open file, and the change
    survives exec(): that is how a program writes to a file without knowing.
    """
    if fd == target:            # already the right number (e.g. stdin was closed)
        return
    os.dup2(fd, target)
    os.close(fd)


@contextmanager
def saved_stdio():
    """Save descriptors 0, 1, 2 and restore them when the block ends.

    Needed for builtins: they run INSIDE the shell process, so a redirection
    changes the shell's own descriptors. Without a restore, the shell would
    keep writing to the file for the rest of its life.

        with saved_stdio():
            os.dup2(file_fd, 1)      # stdout -> file
            run_the_builtin()
        # here, stdout is back to normal, even if run_the_builtin() raised
    """
    flush_std()
    saved = {}
    try:
        for fd in (STDIN, STDOUT, STDERR):
            saved[fd] = os.dup(fd)      # dup() = a second number for the same file
        yield
    finally:
        flush_std()                     # flush BEFORE restoring stdout
        for fd, copy in saved.items():
            os.dup2(copy, fd)           # put the original file back on 0/1/2
            os.close(copy)
