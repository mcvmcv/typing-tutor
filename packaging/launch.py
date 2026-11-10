"""Entry point for the PyInstaller build (it needs a script, not a module)."""

import sys

from typing_tutor.app import main

sys.exit(main())
