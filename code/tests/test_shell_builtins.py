import os
import tempfile
import unittest

from contextlib import redirect_stdout
from io import StringIO

from shell_state import ShellState
from shell_builtins import run_builtin


class TestShellBuiltins(unittest.TestCase):

    def setUp(self):
        self.state = ShellState()

    def capture_output(self, args):
        output = StringIO()

        with redirect_stdout(output):
            status = run_builtin(args, self.state)

        return status, output.getvalue()

    def test_say(self):
        status, output = self.capture_output(
            ["say", "hello", "world"]
        )

        self.assertEqual(status, 0)
        self.assertEqual(output, "hello world\n")

    def test_osinfo(self):
        status, output = self.capture_output(["osinfo"])

        self.assertEqual(status, 0)
        self.assertIn("UIR/ESIN", output)

    def test_path(self):
        status, output = self.capture_output(["path"])

        self.assertEqual(status, 0)
        self.assertEqual(output.strip(), os.getcwd())

    def test_quit(self):
        status, _ = self.capture_output(["quit"])

        self.assertEqual(status, 0)
        self.assertFalse(self.state.running)

    def test_quit_with_status(self):
        status, _ = self.capture_output(["quit", "5"])

        self.assertEqual(status, 5)
        self.assertFalse(self.state.running)

    def test_past(self):
        self.state.command_history = ["path", "say hello"]

        status, output = self.capture_output(["past"])

        self.assertEqual(status, 0)
        self.assertIn("path", output)
        self.assertIn("say hello", output)

    def test_export(self):
        status, _ = self.capture_output(["export", "NAME=Alex"])

        self.assertEqual(status, 0)

        environment = self.state.get_exported_environment()

        self.assertEqual(environment["NAME"], "Alex")

    def test_unknown_command(self):
        result = run_builtin(["somecommand"], self.state)

        self.assertIsNone(result)

    def test_go(self):
        original_directory = os.getcwd()

        try:
            with tempfile.TemporaryDirectory() as temp_directory:
                status, _ = self.capture_output(["go", temp_directory])

                self.assertEqual(status, 0)
                self.assertEqual(os.getcwd(), temp_directory)

        finally:
            os.chdir(original_directory)


if __name__ == "__main__":
    unittest.main()
