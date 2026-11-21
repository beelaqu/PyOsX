ALIASES = {
    "list": "ls",
    "show": "cat",
    "copy": "cp",
    "move": "mv",
    "del": "rm",
    "newdir": "mkdir",
    "newfile": "touch",
}


def resolve_alias(args: list[str]) -> list[str]:
    """
    Resolve the command name while preserving its arguments.

    Example:
        ["list", "-l"] becomes ["ls", "-l"]
    """

    if not args:
        return []

    resolved_command = ALIASES.get(args[0], args[0])

    return [resolved_command, *args[1:]]
