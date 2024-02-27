"""Entrypoint for the all-in-one-file shroudstone.exe.

By default, launches the GUI; unless any CLI arguments are provided, in which case we fall back to CLI."""
import sys
if len(sys.argv) > 1:
    import shroudstone.cli
    shroudstone.cli.app()
else:
    import shroudstone.gui.app
    shroudstone.gui.app.run()
