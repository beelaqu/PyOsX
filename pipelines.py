"""
pipelines.py - pipelines with the custom operator  ->  (Member 4).

    opsh> show file.txt -> wc -l

INTERFACE with Member 1 (parser/dispatcher):
    stages = [(args, redirs), (args, redirs), ...]
    one tuple per command, in order, split on '->' by the parser.
    Redirections are allowed on any stage:   show < in.txt -> sort > out.txt

INTERFACE with Member 3 (executor / process manager). This module receives
Member 3's functions as parameters, so there is only ONE process manager:

    exec_in_child(args, redirs)
        Runs INSIDE a freshly forked child and never returns: it resets the
        signal handlers, applies the stage's own redirections, then runs the
        builtin (in the child, so 'go' cannot change the shell's directory)
        or calls os.execvp().

    wait_foreground(pids) -> int
        Waits for ALL the children and returns the exit status of the LAST one.

    prepare_background_child()      (optional, only used when background=True)
        Called in each child before the pipe wiring (setpgid, stdin=/dev/null).

    register_background(pids, cmdline)   (only used when background=True)
        Lets Member 3's job table remember the PIDs (for $!, SIGCHLD...).

How a pipeline of N commands works (N-1 pipes, N children):

    cmd1 --[pipe 1]--> cmd2 --[pipe 2]--> cmd3 ...
    fd 1 of cmd1 = write end of pipe 1,  fd 0 of cmd2 = read end of pipe 1, etc.

THE RULE THAT PREVENTS HANGS: a reader only sees end-of-file when EVERY copy
of the write end is closed. So every process closes every pipe end it does not
use: the child right after dup2, the parent right after each fork.
"""

import os
import sys

from io_helpers import (STDIN, STDOUT, close_all, flush_std, redirect_fd,
                        safe_close)


def _child_stage(args, redirs, stdin_fd, stdout_fd, unused_fd,
                 exec_in_child, prepare_background_child):
    """Code run by ONE child of the pipeline. It never returns."""
    try:
        if prepare_background_child is not None:
            prepare_background_child()          # before the wiring, so the pipe wins over /dev/null
        if stdin_fd is not None:
            redirect_fd(stdin_fd, STDIN)        # dup2(read end, 0), then close the original
        if stdout_fd is not None:
            redirect_fd(stdout_fd, STDOUT)      # dup2(write end, 1), then close the original
        safe_close(unused_fd)                   # the read end of the pipe we WRITE into
        exec_in_child(args, redirs)             # builtin or exec(): does not return
    except BaseException as e:                  # a child must never return into the shell loop
        sys.stderr.write(f'opsh: {e}\n')
    os._exit(1)


def run_pipeline(stages, exec_in_child, wait_foreground, background=False,
                 prepare_background_child=None, register_background=None,
                 cmdline=''):
    """Run stages connected by pipes.

    Foreground: waits and returns the exit status of the last command.
    Background: registers the PIDs (register_background) and returns 0 at once.
    """
    if not stages:
        raise ValueError('empty pipeline')

    flush_std()                     # do not let the children inherit unflushed text
    pids = []
    prev_read = None                # read end of the pipe coming from the previous stage
    last = len(stages) - 1

    for i, (args, redirs) in enumerate(stages):
        read_end = write_end = None
        if i != last:
            read_end, write_end = os.pipe()     # pipe between stage i and stage i+1

        try:
            pid = os.fork()
        except OSError:                         # out of processes: clean up, then report
            close_all([prev_read, read_end, write_end])
            if pids:
                wait_foreground(pids)
            raise

        if pid == 0:                            # ---------- child ----------
            _child_stage(args, redirs, prev_read, write_end, read_end,
                         exec_in_child, prepare_background_child)

        # ---------- parent ----------
        pids.append(pid)
        safe_close(prev_read)       # that pipe is now fully owned by the children
        safe_close(write_end)       # the parent must NEVER keep a write end open
        prev_read = read_end        # kept for the next stage (None after the last one)

    if background:
        if register_background is not None:
            register_background(pids, cmdline)
        return 0
    return wait_foreground(pids)
