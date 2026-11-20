import shlex
from dataclasses import dataclass


@dataclass(frozen=True)
class Token:
    """Represents one word or operator in a command."""

    kind: str
    value: str


class ParseError(ValueError):
    """Raised when a command contains invalid syntax."""


def _emit_word(raw_chars, tokens):
    """Convert a raw word into a decoded WORD token."""

    if not raw_chars:
        return

    raw_word = "".join(raw_chars)

    try:
        parts = shlex.split(raw_word, comments=False, posix=True)
    except ValueError as error:
        raise ParseError(str(error)) from error

    if len(parts) != 1:
        raise ParseError(f"Invalid command token: {raw_word!r}")

    tokens.append(Token("WORD", parts[0]))
    raw_chars.clear()


def parse_command(line):
    """
    Tokenize a command line.

    Returns a list of Token objects.
    Recognizes words, quotes, and PyOsX operators.
    """

    if not isinstance(line, str):
        raise TypeError("Command must be a string.")

    tokens = []
    raw_chars = []

    quote = None
    index = 0

    while index < len(line):
        char = line[index]

        # Inside single quotes: everything is literal
        if quote == "'":
            raw_chars.append(char)

            if char == "'":
                quote = None

            index += 1
            continue

        # Inside double quotes
        if quote == '"':
            if char == "\\" and index + 1 < len(line):
                raw_chars.extend([char, line[index + 1]])
                index += 2
                continue

            raw_chars.append(char)

            if char == '"':
                quote = None

            index += 1
            continue

        # Handle escaped characters outside quotes
        if char == "\\":
            if index + 1 >= len(line):
                raise ParseError("Trailing escape character.")

            raw_chars.extend([char, line[index + 1]])
            index += 2
            continue

        # Start a quoted word
        if char in ("'", '"'):
            raw_chars.append(char)
            quote = char
            index += 1
            continue

        # Recognize the custom pipe operator
        if line.startswith("->", index):
            _emit_word(raw_chars, tokens)
            tokens.append(Token("OPERATOR", "->"))
            index += 2
            continue

        # Recognize append redirection before output redirection
        if line.startswith(">>", index):
            _emit_word(raw_chars, tokens)
            tokens.append(Token("OPERATOR", ">>"))
            index += 2
            continue

        # Recognize individual operators
        if char in (">", "<", "&"):
            _emit_word(raw_chars, tokens)
            tokens.append(Token("OPERATOR", char))
            index += 1
            continue

        # The project uses -> instead of |
        if char == "|":
            raise ParseError("Use '->' instead of '|' for pipes.")

        # Whitespace separates words
        if char.isspace():
            _emit_word(raw_chars, tokens)
            index += 1
            continue

        # Regular character
        raw_chars.append(char)
        index += 1

    # Check for an unclosed quote
    if quote is not None:
        raise ParseError("Unclosed quotation mark.")

    # Add the final word
    _emit_word(raw_chars, tokens)

    return tokens


def to_argv(tokens):
    """
    Convert a simple command's WORD tokens into an argument list.

    Raises ParseError if operators are still present.
    """

    if any(token.kind != "WORD" for token in tokens):
        raise ParseError(
            "This command contains operators that are not "
            "executed yet."
        )

    return [token.value for token in tokens]
