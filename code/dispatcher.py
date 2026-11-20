from dataclasses import dataclass
from typing import Callable

from parser import Token
from shell_state import ShellState


# A callback that executes one command or pipeline stage.
CommandRunner = Callable[[list[Token]], int]


class DispatchError(ValueError):
    """Raised when a command cannot be dispatched."""


@dataclass(frozen=True)
class DispatcherHandlers:
    """
    Functions supplied by the other PyOsX modules.

    This keeps the dispatcher independent from their
    internal implementations.
    """

    run_builtin: Callable[[list[str], ShellState], int | None]

    resolve_alias: Callable[[list[str]], list[str]]

    execute_external: Callable[[list[str], ShellState], int]

    execute_pipeline: Callable[
        [list[Token], ShellState, CommandRunner], int
    ]

    execute_redirection: Callable[
        [list[Token], ShellState, CommandRunner], int
    ]

    execute_background: Callable[
        [list[Token], ShellState, CommandRunner], int
    ]


def _get_argv(tokens: list[Token]) -> list[str]:
    """Convert WORD tokens into a regular argument list."""

    if any(token.kind != "WORD" for token in tokens):
        raise DispatchError(
            "Unexpected operator in a simple command."
        )

    return [token.value for token in tokens]


def _dispatch_simple(
    tokens: list[Token],
    state: ShellState,
    handlers: DispatcherHandlers
) -> int:
    """Dispatch a command that has no shell operators."""

    args = _get_argv(tokens)

    if not args:
        raise DispatchError("Empty command.")

    # Builtins have priority over external commands.
    builtin_status = handlers.run_builtin(args, state)

    if builtin_status is not None:
        return int(builtin_status)

    # Resolve aliases before external execution.
    resolved_args = handlers.resolve_alias(args)

    if not resolved_args:
        raise DispatchError("Alias resolved to an empty command.")

    if not all(isinstance(arg, str) for arg in resolved_args):
        raise DispatchError("Alias must return a list of strings.")

    return int(handlers.execute_external(resolved_args, state))


def _dispatch_stage(
    tokens: list[Token],
    state: ShellState,
    handlers: DispatcherHandlers
) -> int:
    """
    Dispatch one pipeline stage.

    A stage can be a simple command or a command with redirection.
    """

    operator_values = [
        token.value
        for token in tokens
        if token.kind == "OPERATOR"
    ]

    # A pipeline stage cannot contain another pipeline operator.
    if "->" in operator_values:
        raise DispatchError("Unexpected nested pipeline.")

    # Background execution applies to the entire command,
    # not to an individual pipeline stage.
    if "&" in operator_values:
        raise DispatchError(
            "Background operator must be at the end of the command."
        )

    redirection_operators = {">", ">>", "<"}

    if any(op in redirection_operators for op in operator_values):

        # Member 4 handles the redirection syntax and file descriptors.
        # The callback tells it how to execute the resulting command.
        return int(
            handlers.execute_redirection(
                tokens,
                state,
                lambda command_tokens: _dispatch_simple(
                    command_tokens, state, handlers
                )
            )
        )

    return _dispatch_simple(tokens, state, handlers)


def _dispatch_foreground(
    tokens: list[Token],
    state: ShellState,
    handlers: DispatcherHandlers
) -> int:
    """Dispatch a foreground command or pipeline."""

    has_pipeline = any(
        token.kind == "OPERATOR" and token.value == "->"
        for token in tokens
    )

    if has_pipeline:
        # Member 4 splits the pipeline into stages.
        # Each stage comes back to this dispatcher's routing logic.
        return int(
            handlers.execute_pipeline(
                tokens,
                state,
                lambda stage_tokens: _dispatch_stage(
                    stage_tokens, state, handlers
                )
            )
        )

    return _dispatch_stage(tokens, state, handlers)


def dispatch_command(
    tokens: list[Token],
    state: ShellState,
    handlers: DispatcherHandlers
) -> int:
    """
    Main dispatcher entry point.

    Routes commands to builtins, external execution,
    pipelines, redirections or background execution.

    Updates the shell's last command status.
    """

    if not tokens:
        return state.last_status

    if not all(isinstance(token, Token) for token in tokens):
        raise TypeError("Expected a list of parser Token objects.")

    background_positions = [
        index
        for index, token in enumerate(tokens)
        if token.kind == "OPERATOR" and token.value == "&"
    ]

    try:
        if background_positions:

            # Only one '&' is allowed, and it must be the last token.
            if (
                len(background_positions) != 1
                or background_positions[0] != len(tokens) - 1
            ):
                raise DispatchError(
                    "'&' must appear once, at the end of a command."
                )

            command_tokens = tokens[:-1]

            if not command_tokens:
                raise DispatchError(
                    "Background operator requires a command."
                )

            # Member 3 handles process creation and background jobs.
            # The callback executes the command normally in the child.
            status = handlers.execute_background(
                command_tokens,
                state,
                lambda command: _dispatch_foreground(
                    command, state, handlers
                )
            )

        else:
            status = _dispatch_foreground(tokens, state, handlers)

        state.set_last_status(status)
        return int(status)

    except DispatchError:
        state.set_last_status(2)
        raise
