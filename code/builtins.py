import os
import sys

def builtin_path(args):
    print(os.getcwd())

def builtin_quit(args):
    sys.exit(0)

def builtin_osinfo(args):
    print("Systèmes d'Exploitation -- UIR/ESIN")
def builtin_go(args):
    os.chdir(args[0])
def builtin_say(args):
    print(" ".join(args))
def builtin_info(args):
    print("BUILTINS:")
    print("  go")
    print("  quit")
    print("  path")
    print("  say")
    print("  info")
    print("  past")
    print("  osinfo")

    print("\nALIASES:")
    print("  list  -> ls")
    print("  show  -> cat")
    print("  copy  -> cp")
    print("  move  -> mv")
    print("  del   -> rm")
    print("  newdir -> mkdir")
    print("  newfile -> touch")
from history import history

def builtin_past(args):
    for cmd in history:
        print(cmd)
from history import get_history

def builtin_past(args):
    for cmd in get_history():
        print(cmd)
