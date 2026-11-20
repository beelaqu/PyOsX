import unittest

from parser import Token, ParseError, parse_command, to_argv


class TestParser(unittest.TestCase):

    def values(self, command):
        return [
            (token.kind, token.value)
            for token in parse_command(command)
        ]

    def test_simple_command(self):
        self.assertEqual(
            to_argv(parse_command("ls -l /home")),
            ["ls", "-l", "/home"]
        )

    def test_double_quotes(self):
        self.assertEqual(
            to_argv(parse_command('say "hello world"')),
            ["say", "hello world"]
        )

    def test_single_quotes(self):
        self.assertEqual(
            to_argv(parse_command("say 'hello world'")),
            ["say", "hello world"]
        )

    def test_custom_pipe(self):
        self.assertEqual(
            self.values("show file.txt->wc -l"),
            [
                ("WORD", "show"),
                ("WORD", "file.txt"),
                ("OPERATOR", "->"),
                ("WORD", "wc"),
                ("WORD", "-l")
            ]
        )

    def test_redirections(self):
        self.assertEqual(
            self.values("say hello >> output.txt"),
            [
                ("WORD", "say"),
                ("WORD", "hello"),
                ("OPERATOR", ">>"),
                ("WORD", "output.txt")
            ]
        )

    def test_background(self):
        self.assertEqual(
            self.values("sleep 5 &"),
            [
                ("WORD", "sleep"),
                ("WORD", "5"),
                ("OPERATOR", "&")
            ]
        )

    def test_quoted_operator_is_a_word(self):
        self.assertEqual(
            self.values('say "->"'),
            [
                ("WORD", "say"),
                ("WORD", "->")
            ]
        )

    def test_empty_command(self):
        self.assertEqual(parse_command(""), [])

    def test_unclosed_quote(self):
        with self.assertRaises(ParseError):
            parse_command('say "hello')

    def test_wrong_pipe_operator(self):
        with self.assertRaises(ParseError):
            parse_command("show file.txt | wc -l")

    def test_to_argv_rejects_operators(self):
        tokens = parse_command("sleep 5 &")

        with self.assertRaises(ParseError):
            to_argv(tokens)


if __name__ == "__main__":
    unittest.main()
