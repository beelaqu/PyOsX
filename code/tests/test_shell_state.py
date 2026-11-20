import os
import unittest

from unittest.mock import patch
from shell_state import ShellState


class TestShellState(unittest.TestCase):

    def test_initial_state(self):
        state = ShellState()

        self.assertTrue(state.running)
        self.assertEqual(state.last_status, 0)
        self.assertIsNone(state.last_background_pid)
        self.assertEqual(state.variables, {})
        self.assertEqual(state.exported_variables, set())
        self.assertEqual(state.command_history, [])
        self.assertEqual(state.background_jobs, {})

    def test_set_and_get_variable(self):
        state = ShellState()

        state.set_variable("NAME", "Alex")

        self.assertEqual(state.get_variable("NAME"), "Alex")

    def test_invalid_variable_name(self):
        state = ShellState()

        with self.assertRaises(ValueError):
            state.set_variable("123NAME", "Alex")

    def test_environment_fallback(self):
        state = ShellState()

        with patch.dict(os.environ, {"PYOSX_TEST_ENV": "hello"}):
            self.assertEqual(
                state.get_variable("PYOSX_TEST_ENV"),
                "hello"
            )

    def test_unexported_variable_not_passed_to_child(self):
        state = ShellState()

        name = "PYOSX_UNEXPORTED_TEST"

        with patch.dict(os.environ, {}):
            os.environ.pop(name, None)

            state.set_variable(name, "secret")

            environment = state.get_exported_environment()

            self.assertNotIn(name, environment)

    def test_export_variable(self):
        state = ShellState()

        state.set_variable("PYOSX_EXPORT_TEST", "hello")
        state.export_variable("PYOSX_EXPORT_TEST")

        environment = state.get_exported_environment()

        self.assertEqual(
            environment["PYOSX_EXPORT_TEST"],
            "hello"
        )

    def test_export_undefined_variable(self):
        state = ShellState()

        state.export_variable("PYOSX_EMPTY_TEST")

        self.assertEqual(
            state.get_variable("PYOSX_EMPTY_TEST"),
            ""
        )

        self.assertIn(
            "PYOSX_EMPTY_TEST",
            state.get_exported_environment()
        )

    def test_set_last_status(self):
        state = ShellState()

        state.set_last_status(127)

        self.assertEqual(state.last_status, 127)

    def test_register_background_job(self):
        state = ShellState()

        state.register_background_job(1234, "sleep 10")

        self.assertEqual(state.background_jobs[1234], "sleep 10")
        self.assertEqual(state.last_background_pid, 1234)

    def test_remove_background_job(self):
        state = ShellState()

        state.register_background_job(1234, "sleep 10")

        result = state.remove_background_job(1234)

        self.assertTrue(result)
        self.assertNotIn(1234, state.background_jobs)

        # Removing a completed job must not erase the last PID.
        self.assertEqual(state.last_background_pid, 1234)


if __name__ == "__main__":
    unittest.main()
