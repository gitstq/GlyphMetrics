# -*- coding: utf-8 -*-
"""Allow ``python -m glyphmetrics``."""
import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
