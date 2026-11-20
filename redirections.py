"""
redirections.py - the redirections  >  >>  < 

INTERFACE (to agree with Member 1, the parser):
    A command's redirections are a list of (operator, filename) tuples, in the
    order they were typed, with the operator and the filename already removed
    from the argument list:

        say hello > f.txt     ->  args = ['say', 'hello']
                                  redirs = [('>', 'f.txt')]

USED BY:
    - Member 3 (executor), inside a forked child, BEFORE exec():
          redirections.apply_redirections(redirs)
    - Member 1/2 (dispatcher), for a builtin that runs inside the shell:
          with redirections.redirected(redirs):
              run_the_builtin()

This module never parses text and never creates processes.
"""
import os
from contextlib import contextmanager

from io_helpers import STDIN, STDOUT, redirect_fd, saved_stdio

# operator -> (flags for os.open, descriptor to redirect)
_MODES = {
    '>':  (os.O_WRONLY | os.O_CREAT | os.O_TRUNC,  STDOUT),   # create or empty the file
    '>>': (os.O_WRONLY | os.O_CREAT | os.O_APPEND, STDOUT),   # create or add at the end
    '<':  (os.O_RDONLY,                             STDIN),    # the file must exist
}
REDIRECT_OPS = tuple(_MODES)

FILE_PERMISSIONS = 0o644     # rw-r--r--, reduced by the umask when the file is created


class RedirectionError(Exception):
    """A redirection could not be set up (missing file, permission denied...)."""

    def __init__(self, filename, reason):
        super().__init__(f'{filename}: {reason}')
        self.filename = filename
        self.reason = reason


def open_redirect(op, filename):
    """Open the file for one redirection.
    Returns (fd, target): the new descriptor and the descriptor (0 or 1) it replaces."""
    if op not in _MODES:
        raise ValueError(f'unknown redirection operator: {op}')
    flags, target = _MODES[op]
    try:
        fd = os.open(filename, flags, FILE_PERMISSIONS)
    except OSError as e:
        raise RedirectionError(filename, e.strerror)
    return fd, target


def apply_redirections(redirs):
    """Apply every redirection to the CURRENT process (0 = stdin, 1 = stdout).

    Steps for each one:   fd = os.open(file)   ->   os.dup2(fd, 0 or 1)   ->   os.close(fd)
    If several redirections target the same descriptor, the last one wins
    (the earlier files are still created or truncated, like in Bash).

    Raises RedirectionError on failure; the caller decides what to do
    (a child prints the message and exits with status 1; a builtin reports it
    and continues).
    """
    for op, filename in redirs:
        fd, target = open_redirect(op, filename)
        redirect_fd(fd, target)


@contextmanager
def redirected(redirs):
    """Run a builtin with redirections inside the shell process itself.

        with redirected([('>', 'f.txt')]):
            print('hello')            # goes to f.txt
        print('back on screen')       # stdout restored here

    Restoring is guaranteed, even when the builtin raises an exception.
    """
    with saved_stdio():
        apply_redirections(redirs)
        yield
