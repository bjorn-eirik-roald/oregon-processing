# Lazy-loaded commands: maps command name to module path
_COMMAND_MODULES = {
    "create_project": "oregon_processing.commands.create_project",
    "open_terminal": "oregon_processing.commands.open_terminal",
    "run_export_protocol": "oregon_processing.commands.run_export_protocol",
    "check_database_status": "oregon_processing.commands.check_database_status",
}

_COMMAND_CACHE = {}

import argparse
import sys
import importlib

def _get_command(command_name: str):
    """Lazily import and cache a command function."""
    if command_name not in _COMMAND_CACHE:
        module_path = _COMMAND_MODULES[command_name]
        module = importlib.import_module(module_path)
        _COMMAND_CACHE[command_name] = getattr(module, command_name)
    return _COMMAND_CACHE[command_name]

def _check_package_installed() -> bool:
    package_name = "oregon_processing"
    try:
        importlib.import_module(package_name)
        return True
    except ImportError:
        print(
            f"\n\nThe package '{package_name}' is not installed correctly. Run setup.cmd and try again.\n\n",
            file=sys.stderr,
        )
        return False

def main():

    if not _check_package_installed():
        return 1

    parser = argparse.ArgumentParser(description="Execute a command.")
    parser.add_argument(
        "command",
        choices=_COMMAND_MODULES.keys(),
        help="The name of the command to execute. Choices: %(choices)s"
    )
    args = parser.parse_args()

    command_name = args.command
    command_func = _get_command(command_name)
    result = command_func()
    return result if isinstance(result, int) else 0

if __name__ == "__main__":
    sys.exit(main())