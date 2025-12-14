
import sys
from .cli import main as cli_main
from .main import main as app_main

def main():
    # List of commands that trigger CLI mode
    # Derived from bin/hyprwhspr and lib/cli.py
    if len(sys.argv) > 1:
        # Any arguments implies CLI usage, as the main app (daemon) 
        # is headless and configured via config file/shortcuts.
        cli_main()
    else:
        app_main()

if __name__ == "__main__":
    main()
