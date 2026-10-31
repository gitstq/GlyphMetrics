# -*- coding: utf-8 -*-
"""
GlyphMetrics - cluster-aware, ANSI-aware terminal text measurement.

    >>> import glyphmetrics as gm
    >>> gm.str_width("hello")
    5
    >>> gm.str_width("你好")          # two wide CJK ideographs
    4
    >>> gm.str_width("\\x1b[31mERROR\\x1b[0m")   # escape sequences are invisible
    5
    >>> len("👨‍👩‍👧")                  # naive code point count
    5
    >>> gm.str_width("👨‍👩‍👧")          # one glyph, two cells
    2

Pure standard library.  No dependencies.  Python 3.8+
"""

from __future__ import annotations

from ._core import (
    center,
    char_width,
    grapheme_len,
    graphemes,
    has_ansi,
    iter_graphemes,
    ljust,
    pad,
    rjust,
    str_width,
    strip_ansi,
    truncate,
    truncate_front,
    wrap,
    GlyphMetricsError,
    UnicodeVersionError,
)
from .tables import UNICODE_VERSION

__version__ = "1.0.0"
__author__ = "gitstq"
__license__ = "MIT"
__all__ = [
    # measurement
    "char_width", "str_width",
    # clusters
    "iter_graphemes", "graphemes", "grapheme_len",
    # escape handling
    "strip_ansi", "has_ansi",
    # layout
    "pad", "ljust", "rjust", "center", "truncate", "truncate_front", "wrap",
    # meta
    "UNICODE_VERSION", "__version__", "GlyphMetricsError", "UnicodeVersionError",
]
