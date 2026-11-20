import unittest

from parser import parse_command
from shell_state import ShellState
from dispatcher import (
    DispatcherHandlers,
    DispatchError,
    dispatch_command
)


class FakeHandlers:

    def __init__(self):
        self.events = []

    def run_builtin(self, args, state):
        self.events.append(("builtin", args))

        if args[0] == "say":
            return 0

        return None

    def resolve_alias(self, args):
        self.events.append(("alias", args))

        aliases = {
            "list": "ls",
            "show": "cat"
        }

        if args[0] in aliases:
            return [aliases[args[0]], *args[1:]]

        return args

    def execute_external(self, args, state):
        self.events.append(("external", args))
        return 17

    def execute_pipeline(self, tokens, state, runner):
        self.events.append(("pipeline", tokens))
        return 21

    def execute_redirection(self, tokens, state, runner):
        self.events.append(("redirection", tokens))
        return 22

    def execute_background(self, tokens, state, runner):
        self.events.append(("background", tokens))
        return 23

    def create_dispatcher_handlers(self):
        return DispatcherHandlers(
            run_builtin=self.run_builtin,
            resolve_alias=self.resolve_alias,
            execute_external=self.execute_external,
            execute_pipeline=self.execute_pipeline,
            execute_redirection=self.execute_redirection,
            execute_background=self.execute_background
        )


class TestDispatcher(unittest.TestCase):

    def setUp(self):
        self.state = ShellState()
        self.fake = FakeHandlers()
        self.handlers = self.fake.create_dispatcher_handlers()

    def test_builtin_command(self):
        tokens = parse_command("say hello")

        status = dispatch_command(tokens, self.state, self.handlers)

        self.assertEqual(status, 0)
        self.assertEqual(self.fake.events[0][0], "builtin")

    def test_external_command(self):
        tokens = parse_command("ls -l")

        status = dispatch_command(tokens, self.state, self.handlers)

        self.assertEqual(status, 17)
        self.assertEqual(self.fake.events[-1][0], "external")

    def test_alias_resolution(self):
        tokens = parse_command("list -l")

        dispatch_command(tokens, self.state, self.handlers)

        self.assertIn(
            ("external", ["ls", "-l"]),
            self.fake.events
        )

    def test_pipeline_routing(self):
        tokens = parse_command("show file.txt -> wc -l")

        status = dispatch_command(tokens, self.state, self.handlers)

        self.assertEqual(status, 21)
        self.assertEqual(self.fake.events[-1][0], "pipeline")

    def test_redirection_routing(self):
        tokens = parse_command("say hello > output.txt")

        status = dispatch_command(tokens, self.state, self.handlers)

        self.assertEqual(status, 22)
        self.assertEqual(self.fake.events[-1][0], "redirection")

    def test_background_routing(self):
        tokens = parse_command("sleep 10 &")

        status = dispatch_command(tokens, self.state, self.handlers)

        self.assertEqual(status, 23)

        event_name, command_tokens = self.fake.events[-1]

        self.assertEqual(event_name, "background")
        self.assertEqual(
            [token.value for token in command_tokens],
            ["sleep", "10"]
        )

    def test_background_operator_in_wrong_position(self):
        tokens = parse_command("sleep & 10")

        with self.assertRaises(DispatchError):
            dispatch_command(tokens, self.state, self.handlers)

        self.assertEqual(self.state.last_status, 2)

    def test_last_status_is_updated(self):
        tokens = parse_command("ls")

        dispatch_command(tokens, self.state, self.handlers)

        self.assertEqual(self.state.last_status, 17)

    def test_empty_command(self):
        self.state.set_last_status(5)

        status = dispatch_command([], self.state, self.handlers)

        self.assertEqual(status, 5)
        self.assertEqual(self.fake.events, [])


if __name__ == "__main__":
    unittest.main()
