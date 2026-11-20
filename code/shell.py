from parser import ParseError, parse_command
from shell_state import ShellState


def shell_loop():
    """Main interactive loop of PyOsX."""

    # Create one shared state for the shell session
    state = ShellState()

    print("Welcome to PyOsX!")
    print("Type Ctrl+D to exit.")

    while state.running:
        try:
            command = input("pyosx> ")

            if not command.strip():
                continue

            # Store the command in the current session history
            state.command_history.append(command)

            try:
                tokens = parse_command(command)

                if not tokens:
                    continue

                # Temporary output while execution is not integrated
                print(
                    "Parsed tokens:",
                    [(token.kind, token.value) for token in tokens]
                )

            except ParseError as error:
                state.set_last_status(2)
                print(f"pyosx: syntax error: {error}")

        except KeyboardInterrupt:
            state.set_last_status(130)
            print("\nUse Ctrl+D to exit.")

        except EOFError:
            state.running = False
            print("\nGoodbye!")
