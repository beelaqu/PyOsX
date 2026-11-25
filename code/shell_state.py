import os
import re

from dataclasses import dataclass, field


_VARIABLE_NAME_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


@dataclass
class ShellState:
    """
    Stores the shared state of the PyOsX shell.

    This object is shared between the shell, parser,
    dispatcher, builtins, executor and other modules.
    """

    # Controls whether the shell should continue running
    running: bool = True

    # Exit status of the last executed command
    last_status: int = 0

    # PID of the most recently launched background process
    last_background_pid: int | None = None

    # Shell variables
    variables: dict[str, str] = field(default_factory=dict)

    # Names of variables exported to external programs
    exported_variables: set[str] = field(default_factory=set)

    # Commands entered during the current session
    command_history: list[str] = field(default_factory=list)

    # Background processes: PID -> command
    background_jobs: dict[int, str] = field(default_factory=dict)
    # Completed background jobs: (PID, command, exit_status)
    completed_jobs: list[tuple[int, str, int]] = field(
        default_factory=list
    )

    def set_variable(self, name: str, value: str, export: bool = False):
        """Create or update a shell variable."""

        if not _VARIABLE_NAME_PATTERN.fullmatch(name):
            raise ValueError(f"Invalid variable name: {name}")

        self.variables[name] = str(value)

        if export:
            self.exported_variables.add(name)

    def get_variable(self, name: str, default=None):
        """
        Retrieve a shell variable.

        If it is not defined as a shell variable,
        try the inherited environment.
        """

        return self.variables.get(name, os.environ.get(name, default))

    def export_variable(self, name: str):
        """Mark a variable for export to external programs."""

        if not _VARIABLE_NAME_PATTERN.fullmatch(name):
            raise ValueError(f"Invalid variable name: {name}")

        if name not in self.variables:
            self.variables[name] = os.environ.get(name, "")

        self.exported_variables.add(name)

    def get_exported_environment(self):
        """
        Return the environment that should be passed
        to external programs.
        """

        environment = os.environ.copy()

        for name in self.exported_variables:
            if name in self.variables:
                environment[name] = self.variables[name]

        return environment

    def set_last_status(self, status: int):
        """Update the previous command's exit status."""

        self.last_status = int(status)

    def register_background_job(self, pid: int, command: str):
        """Register a background process."""

        pid = int(pid)

        if pid <= 0:
            raise ValueError("Background process PID must be positive.")

        self.background_jobs[pid] = command
        self.last_background_pid = pid

    def remove_background_job(self, pid: int) -> bool:
        """Remove a completed background process."""

        return self.background_jobs.pop(pid, None) is not None
