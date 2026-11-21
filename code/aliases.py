ALIASES = {
    "list": "ls",
    "show": "cat",
    "copy": "cp",
    "move": "mv",
    "del": "rm",
    "newdir": "mkdir",
    "newfile": "touch"
}

def resolve_alias(command):
    return ALIASES.get(command, command)
