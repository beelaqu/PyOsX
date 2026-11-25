import signal
import time
import unittest

from jobs import execute_background, install_sigchld_handler
from parser import parse_command
from process_manager import reap_background_jobs
from shell_state import ShellState


class TestBackgroundJobs(unittest.TestCase):

    def setUp(self):
        self.state = ShellState()

    def wait_for_job(self, pid, timeout=3):
        """Wait for a background job to be collected."""

        deadline = time.monotonic() + timeout

        while pid in self.state.background_jobs:
            reap_background_jobs(self.state)

            if time.monotonic() >= deadline:
                return False

            time.sleep(0.01)

        return True

    def test_background_launch_and_reaping(self):
        tokens = parse_command("demo argument")

        status = execute_background(
            tokens,
            self.state,
            lambda command: 7
        )

        pid = self.state.last_background_pid

        self.assertEqual(status, 0)
        self.assertIsNotNone(pid)
        self.assertIn(pid, self.state.background_jobs)

        self.assertTrue(self.wait_for_job(pid))

        completed = [
            job for job in self.state.completed_jobs
            if job[0] == pid
        ]

        self.assertEqual(len(completed), 1)
        self.assertEqual(completed[0], (pid, "demo argument", 7))

    def test_background_pid_is_stored(self):
        tokens = parse_command("demo")

        execute_background(
            tokens,
            self.state,
            lambda command: 0
        )

        self.assertGreater(self.state.last_background_pid, 0)

    def test_child_state_is_separate_from_parent(self):
        tokens = parse_command("demo")

        def child_runner(command):
            self.state.set_variable("CHILD_ONLY", "yes")
            return 0

        status = execute_background(
            tokens,
            self.state,
            child_runner
        )

        pid = self.state.last_background_pid

        self.assertEqual(status, 0)
        self.assertTrue(self.wait_for_job(pid))

        self.assertIsNone(self.state.get_variable("CHILD_ONLY"))

    def test_sigchld_handler_reaps_job(self):
        previous_handler = install_sigchld_handler(self.state)

        try:
            tokens = parse_command("demo")

            execute_background(
                tokens,
                self.state,
                lambda command: 0
            )

            pid = self.state.last_background_pid

            deadline = time.monotonic() + 3

            while pid in self.state.background_jobs:
                if time.monotonic() >= deadline:
                    break
                time.sleep(0.01)

            self.assertNotIn(pid, self.state.background_jobs)

            completed_pids = [
                job[0] for job in self.state.completed_jobs
            ]

            self.assertIn(pid, completed_pids)

        finally:
            signal.signal(signal.SIGCHLD, previous_handler)

    def test_empty_background_command(self):
        status = execute_background(
            [],
            self.state,
            lambda command: 0
        )

        self.assertEqual(status, 2)

    def test_invalid_runner(self):
        status = execute_background(
            parse_command("demo"),
            self.state,
            None
        )

        self.assertEqual(status, 2)


if __name__ == "__main__":
    unittest.main()
