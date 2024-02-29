"""Main entrypoint for shroudstone.

By default, launches the GUI; unless any CLI arguments are provided, in which case we fall back to CLI."""
import sys

def main():
    if len(sys.argv) > 1:
        import shroudstone.cli
        shroudstone.cli.app()
    else:
        import shroudstone.gui.app
        shroudstone.gui.app.run()

if __name__ == "__main__":
    main()
