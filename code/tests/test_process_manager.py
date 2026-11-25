import os
import signal
import unittest

from process_manager import wait_for_process
from shell_state import ShellState
from process_manager import reap_background_jobs


class TestProcessManager(unittest.TestCase):

    def test_wait_for_process_exit_status(self):
        pid = os.fork()

        if pid == 0:
            os._exit(7)

        status = wait_for_process(pid)

        self.assertEqual(status, 7)

    def test_wait_for_process_signal_termination(self):
        pid = os.fork()

        if pid == 0:
            os.kill(os.getpid(), signal.SIGTERM)
            os._exit(1)

        status = wait_for_process(pid)

        self.assertEqual(status, 128 + signal.SIGTERM)

    def test_does_not_reap_unregistered_children(self):
        state = ShellState()

        pid = os.fork()

        if pid == 0:
            os._exit(0)

        completed = reap_background_jobs(state)

        self.assertEqual(completed, [])

        # The process must still be available for its actual parent.
        waited_pid, _ = os.waitpid(pid, 0)

        self.assertEqual(waited_pid, pid)


if __name__ == "__main__":
    unittest.main()
