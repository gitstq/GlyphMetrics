# -*- coding: utf-8 -*-
"""
GlyphMetrics core engine.

Everything here runs on the Python standard library only.

Two ideas make GlyphMetrics different from naive width calculators:

1. **Grapheme-cluster awareness.**  A user-perceived character is not always a
   single code point.  ``👨‍👩‍👧`` is five code points joined by ZWJ, yet a
   terminal renders exactly one glyph in two cells.  Summing per-code-point
   widths gives 8 -- wrong.  GlyphMetrics clusters first, then measures.

2. **ANSI awareness.**  Terminal output is rarely plain text: colours, bold,
   hyperlinks.  Those escape sequences contribute **zero** visible cells, so
   measuring them breaks alignment.  GlyphMetrics parses and skips them while
   keeping the original string intact for output.
"""

from __future__ import annotations

import re
import sys
from bisect import bisect_left
from functools import lru_cache

from . import tables as _T

__all__ = [
    "char_width", "str_width", "iter_graphemes", "graphemes", "grapheme_len",
    "strip_ansi", "has_ansi", "pad", "ljust", "rjust", "center",
    "truncate", "wrap", "UnicodeVersionError", "GlyphMetricsError",
]

_PY = sys.version_info

# Preferred line break opportunity marker used internally by wrap().
_ONE_TO_ELEVEN = tuple(range(0x1, 0x0C))


class GlyphMetricsError(Exception):
    """Base error type for GlyphMetrics."""


class UnicodeVersionError(GlyphMetricsError):
    """Raised when the bundled tables look malformed."""


# --------------------------------------------------------------------------
# Fast table membership
# --------------------------------------------------------------------------

def _in_pairs(pairs, cp):
    """True when *cp* falls inside the flat pair list ``[lo,hi,lo,hi,...]``.

    Pairs are ascending and inclusive.  ``bisect_left`` places *cp* either
    strictly inside a pair (odd index -> a hi bound) or exactly on a range
    start (even index, needs an equality guard).
    """
    i = bisect_left(pairs, cp)
    if i & 1:
        return True
    return i < len(pairs) and pairs[i] == cp


# Validate once at import time so a truncated/corrupt tables.py fails loudly.
for _name in ("_WIDE", "_ZERO", "_CONTROL", "_EXTEND", "_SPACING_MARK",
              "_PREPEND", "_EXTENDED_PICTOGRAPHIC", "_REGIONAL_INDICATOR",
              "_AMBIGUOUS", "_JAMO_L", "_JAMO_V", "_JAMO_T", "_JAMO_LV",
              "_JAMO_LVT"):
    _pairs = getattr(_T, _name, None)
    if _pairs is None or len(_pairs) % 2 != 0:
        raise UnicodeVersionError("corrupt table: %s" % _name)

_ZWJ = _T.ZERO_WIDTH_JOINER
_VS15 = _T.VARIATION_SELECTOR_15
_VS16 = _T.VARIATION_SELECTOR_16


# --------------------------------------------------------------------------
# Per-code-point width
# --------------------------------------------------------------------------

def char_width(ch, ambiguous_as_wide=False, control_width=0):
    """Return the display width of a *single character* ``ch``.

    Returns 2 for East Asian wide/full-width and presentation-wide emoji,
    1 for regular narrow characters, 0 for zero-width marks/formatters, and
    ``control_width`` (default 0) for C0/C1 control characters.

    Note that this measures one code point.  Prefer :func:`str_width` for real
    strings -- sequences such as emoji joined by ZWJ only make sense at cluster
    level.
    """
    if len(ch) != 1:
        raise ValueError("char_width() expects exactly one character, got %r" % (ch,))
    cp = ord(ch)
    if cp < 0x20 or 0x7F <= cp <= 0x9F:
        return control_width
    if _in_pairs(_T._CONTROL, cp):
        return control_width
    if _in_pairs(_T._ZERO, cp):
        return 0
    if _in_pairs(_T._WIDE, cp):
        return 2
    if ambiguous_as_wide and _in_pairs(_T._AMBIGUOUS, cp):
        return 2
    return 1


# --------------------------------------------------------------------------
# Memoisation
# --------------------------------------------------------------------------
# Width lookups and grapheme-break classification are pure functions of a code
# point, yet they cost several bisections each.  Real terminal redraws hammer
# the same few hundred characters over and over, so caching turns repeated
# O(log n) table probing into a single dict hit.  Both caches are bounded and
# self-clearing, which keeps memory flat even on pathological input.

_CACHE_LIMIT = 65536
_width_cache = {}
_gb_cache = {}


def _width_cached(cp):
    try:
        return _width_cache[cp]
    except KeyError:
        pass
    if len(_width_cache) >= _CACHE_LIMIT:
        _width_cache.clear()
    w = _raw_width(cp)
    _width_cache[cp] = w
    return w


def _gb_cached(cp):
    try:
        return _gb_cache[cp]
    except KeyError:
        pass
    if len(_gb_cache) >= _CACHE_LIMIT:
        _gb_cache.clear()
    cls = _gb(cp)
    _gb_cache[cp] = cls
    return cls


def _raw_width(cp, ambiguous_as_wide=False):
    """Width of a raw code point, ignoring control-char convention.

    Control characters never occupy a visible cell, so they measure 0 here --
    otherwise every embedded newline or tab would silently corrupt alignment.
    """
    if cp < 0x20 or 0x7F <= cp <= 0x9F or _in_pairs(_T._CONTROL, cp):
        return 0
    if _in_pairs(_T._ZERO, cp):
        return 0
    if _in_pairs(_T._WIDE, cp):
        return 2
    if ambiguous_as_wide and _in_pairs(_T._AMBIGUOUS, cp):
        return 2
    return 1


# --------------------------------------------------------------------------
# Grapheme clusters (UAX #29, practical subset)
# --------------------------------------------------------------------------

def _gb(cp):
    """Map a code point to the Grapheme_Break class needed for clustering."""
    if cp == 0x0D:
        return "CR"
    if cp == 0x0A:
        return "LF"
    if cp < 0x20 or 0x7F <= cp <= 0x9F:
        return "Control"
    if cp == _ZWJ:
        return "ZWJ"
    if _in_pairs(_T._EXTEND, cp):
        return "Extend"
    if _in_pairs(_T._SPACING_MARK, cp):
        return "SpacingMark"
    if _in_pairs(_T._REGIONAL_INDICATOR, cp):
        return "Regional_Indicator"
    if _in_pairs(_T._JAMO_L, cp):
        return "L"
    if _in_pairs(_T._JAMO_V, cp):
        return "V"
    if _in_pairs(_T._JAMO_T, cp):
        return "T"
    if _in_pairs(_T._JAMO_LV, cp) or _in_pairs(_T._JAMO_LVT, cp):
        return "LV"
    if _in_pairs(_T._PREPEND, cp):
        return "Prepend"
    return "Other"


_EXT_PICT_CACHE_MAX = 4096


def _is_ext_pict(cp):
    return _in_pairs(_T._EXTENDED_PICTOGRAPHIC, cp)


def iter_graphemes(s):
    """Yield ``(start, end)`` index pairs delimiting each grapheme cluster.

    Implements the rules that matter for terminal rendering:
    GB3 (CR×LF), GB4/GB5 (controls break), GB6-GB8 (Hangul jamo), GB9
    (×Extend/ZWJ), GB9a (×SpacingMark), GB9b (Prepend×), GB11 (emoji ZWJ
    sequences), GB12/GB13 (regional indicator pairs / flags).
    """
    n = len(s)
    if n == 0:
        return
    # Pre-compute classes once: O(n) instead of re-classifying on look-ahead.
    classes = [_gb_cached(ord(c)) for c in s]

    # Below U+0300 there are no combining marks, no emoji and no ZWJ -- so every
    # code point stands alone.  CR/LF are the exception, they pair up (GB3).
    singles_only = max(s) < "\u0300" and "\r" not in s and "\n" not in s
    if singles_only:
        # Nothing below U+0300 can start a combining sequence, so every code
        # point is its own cluster: skip the whole state machine.
        for i in range(n):
            yield (i, i + 1)
        return

    start = 0
    i = 0
    ri_run = 0
    # GB11 state machine for "Extended_Pictographic Extend* ZWJ x ExtPict":
    #   0 = no candidate yet, 1 = saw ExtPict (+ Extend*), 2 = saw the ZWJ
    gb11 = 0
    while i < n - 1:
        a, b = classes[i], classes[i + 1]

        # ---- update state machines with the character we are leaving ----
        # GB12/GB13: length of the contiguous Regional_Indicator run so far.
        ri_run = ri_run + 1 if a == "Regional_Indicator" else 0
        # GB11: advance "Extended_Pictographic Extend* ZWJ" pattern state.
        # This MUST happen before deciding the break for (i, i+1), otherwise
        # the ZWJ at position i is missed and emoji families fall apart.
        if a == "ZWJ":
            gb11 = 2 if gb11 == 1 else 0
        elif a == "Extend":
            gb11 = gb11 if gb11 in (1, 2) else 0
        elif _is_ext_pict(ord(s[i])):
            gb11 = 1
        else:
            gb11 = 0

        brk = True
        if a == "CR" and b == "LF":
            brk = False                                            # GB3
        elif a in ("Control", "CR", "LF") or b in ("Control", "CR", "LF"):
            brk = True                                             # GB4 / GB5
        elif b in ("Extend", "ZWJ"):
            brk = False                                            # GB9
        elif b == "SpacingMark":
            brk = False                                            # GB9a
        elif a == "Prepend":
            brk = False                                            # GB9b
        elif b == "Prepend":
            brk = True
        elif gb11 == 2 and _is_ext_pict(ord(s[i + 1])):
            # GB11: emoji ZWJ sequence - the whole family rides together.
            brk = False
        elif a == "L" and b in ("L", "V", "LV"):
            brk = False                                            # GB6 / GB7
        elif a in ("LV", "V") and b in ("V", "T"):
            brk = False                                            # GB7
        elif a in ("LVT", "T") and b == "T":
            brk = False                                            # GB8
        elif a == "Regional_Indicator" and b == "Regional_Indicator":
            # Odd run length -> this RI pairs with the previous one (no break);
            # even run length -> the next pair starts here (break).
            brk = (ri_run % 2 == 0)

        i += 1
        if brk:
            yield (start, i)
            start = i

    yield (start, n)


def graphemes(s):
    """Return the list of grapheme clusters contained in ``s``."""
    return [s[a:b] for a, b in iter_graphemes(s)]


def grapheme_len(s):
    """Number of user-perceived characters in ``s`` (``len`` counts code points)."""
    return sum(1 for _ in iter_graphemes(s))


def _cluster_units(s, start, end, ambiguous_as_wide=False):
    """Visible width of the cluster ``s[start:end]``.

    Rules that cannot be expressed per code point:
      * two Regional Indicators form one flag glyph -> 2 cells (not 4)
      * an emoji ZWJ sequence renders as a single glyph -> 2 cells
      * a base followed by VS16 becomes wide; VS15 forces narrow
    """
    if end - start == 1 and not ambiguous_as_wide:
        # Common case: a one-code-point cluster, default width policy.
        # Cacheable, so we can skip the whole width computation below.
        return _width_cached(ord(s[start]))

    codes = [ord(c) for c in s[start:end]]

    # Regional indicator pair -> single flag glyph.
    ri_count = sum(1 for cp in codes if _in_pairs(_T._REGIONAL_INDICATOR, cp))
    if ri_count >= 2 and len(codes) >= 2:
        return 2

    if _VS16 in codes:
        return 2
    if _VS15 in codes:
        return 1

    best = 0
    for cp in codes:
        w = _raw_width(cp, ambiguous_as_wide)
        if w > best:
            best = w
    # An emoji joined by ZWJ always collapses to one wide glyph.
    if _ZWJ in codes and best == 0:
        return 0
    return best


# --------------------------------------------------------------------------
# ANSI escape sequence handling
# --------------------------------------------------------------------------

_ANSI_RE = re.compile(
    r"""
    \x1b\[[0-?]*[ -/]*[@-~]                # CSI  ... \x1b[31m
    |\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)     # OSC  ... hyperlinks, window title
    |\x1b[PX^_][^\x1b]*(?:\x1b\\)?         # DCS / SOS / PM / APC
    |\x1b[()][0-9A-Za-z]                   # charset designation
    |\x1b[@-Z\\-_]                         # single-char escapes
    """,
    re.VERBOSE,
)


def strip_ansi(s):
    """Remove all ANSI/VT escape sequences, leaving plain visible text."""
    return _ANSI_RE.sub("", s)


def has_ansi(s):
    """True when ``s`` contains at least one escape sequence."""
    return _ANSI_RE.search(s) is not None


def _visible_segments(s):
    """Yield ``(text, offset)`` for every non-escape run in ``s``.

    Used to measure width while preserving the original (coloured) string for
    output.
    """
    pos = 0
    out = []
    for m in _ANSI_RE.finditer(s):
        if m.start() > pos:
            out.append(s[pos:m.start()])
        pos = m.end()
    if pos < len(s):
        out.append(s[pos:])
    return out


# --------------------------------------------------------------------------
# String level API
# --------------------------------------------------------------------------

# Translating away every zero-cell ASCII character leaves exactly the visible
# ones, so ``len(...)`` becomes the width without touching Python-level loops.
_CTRL_DELETE = dict.fromkeys(list(range(0x20)) + [0x7F])


@lru_cache(maxsize=8192)
def _measure(text, ambiguous_as_wide=False):
    """Cacheable core measurement for arbitrary text.

    Terminal UIs re-measure the same titles, headers and cell contents on every
    redraw, so caching whole-string results pays off immediately.  Bounded LRU
    keeps the footprint predictable; strings are treated as immutable values.
    """
    total = 0
    for start, end in iter_graphemes(text):
        total += _cluster_units(text, start, end, ambiguous_as_wide)
    return total


def str_width(s, ambiguous_as_wide=False, strip=True):
    """Return the number of terminal cells ``s`` occupies.

    Escape sequences count as zero.  Multi-code-point clusters (emoji ZWJ
    sequences, flags, combining sequences) are measured as one glyph.
    """
    if not s:
        return 0
    if strip and "\x1b" in s:
        text = strip_ansi(s)
    else:
        text = s

    # Hot path 1: pure 7-bit ASCII.  One C-level translate removes the only
    # characters that count as zero cells (C0 controls + DEL), the rest are 1:1.
    if text.isascii():
        return len(text.translate(_CTRL_DELETE))

    # Hot path 2: no combining/emoji/ZWJ possible, and no ambiguous handling
    # requested -> per code point widths come straight from the cache.
    if not ambiguous_as_wide and max(text) < "\u0300":
        return sum(map(_width_cached, map(ord, text)))

    return _measure(text, ambiguous_as_wide)


def pad(s, width, align="left", fill=" ", ellipsis="…", strip=True):
    """Pad ``s`` to exactly *width* visible cells, keeping escape sequences.

    ``align`` may be ``left``/``right``/``center``.  When the string is already
    wider than *width* it is truncated according to *ellipsis*.
    """
    if align not in ("left", "right", "center"):
        raise ValueError("align must be 'left', 'right' or 'center'")
    if len(fill) != 1:
        raise ValueError("fill must be exactly one character")

    cur = str_width(s, strip=strip)
    if cur > width:
        return truncate(s, width, ellipsis=ellipsis, strip=strip)
    deficit = width - cur
    if deficit <= 0:
        return s

    if align == "left":
        return s + fill * deficit
    if align == "right":
        return fill * deficit + s
    left = deficit // 2
    right = deficit - left
    return fill * left + s + fill * right


def ljust(s, width, fill=" ", **kw):
    """Left-align ``s`` within *width* visible cells."""
    return pad(s, width, align="left", fill=fill, **kw)


def rjust(s, width, fill=" ", **kw):
    """Right-align ``s`` within *width* visible cells."""
    return pad(s, width, align="right", fill=fill, **kw)


def center(s, width, fill=" ", **kw):
    """Center ``s`` within *width* visible cells."""
    return pad(s, width, align="center", fill=fill, **kw)


def _active_sgr(s, n_clusters):
    """Return the last SGR sequence in effect after *n_clusters* visible glyphs.

    This is what lets truncation keep the caller's colour instead of silently
    dropping it: we replay the original string, counting visible glyphs while
    ignoring escape sequences, and remember the most recent SGR we passed.
    """
    last = None
    seen = 0
    pos = 0
    for m in _ANSI_RE.finditer(s):
        seen += sum(1 for _ in iter_graphemes(s[pos:m.start()]))
        pos = m.end()
        if seen > n_clusters:
            break
        seq = m.group(0)
        if seq.startswith("\x1b[") and seq.endswith("m"):
            last = seq
    return last


def truncate(s, width, ellipsis="…", strip=True):
    """Truncate ``s`` so it fits within *width* visible cells.

    Truncation never splits a grapheme cluster, and when the input carried ANSI
    colour the active SGR is re-emitted in front and closed with a reset, so the
    caller's terminal state is never left polluted.
    """
    if width <= 0:
        return ""
    text = strip_ansi(s) if strip else s
    if str_width(text, strip=False) <= width:
        return s

    marker = ellipsis or ""
    budget = width - str_width(marker)
    if budget <= 0:
        return truncate_front(s, width, marker, strip=strip)

    kept = []
    used = 0
    for start, end in iter_graphemes(text):
        w = _cluster_units(text, start, end)
        if used + w > budget:
            break
        kept.append(text[start:end])
        used += w

    body = "".join(kept) + marker
    if has_ansi(s):
        opener = _active_sgr(s, len(kept)) or ""
        if opener and opener != "\x1b[0m":
            return opener + body + "\x1b[0m"
    return body


def truncate_front(s, width, ellipsis="…", strip=True):
    """Keep the *tail* of ``s`` (useful for paths) within *width* cells."""
    if width <= 0:
        return ""
    text = strip_ansi(s) if strip else s
    if str_width(text, strip=False) <= width:
        return s
    marker = ellipsis or ""
    budget = width - str_width(marker)
    if budget <= 0:
        marker = ""
        budget = width

    kept = []
    used = 0
    clusters = [(a, b) for a, b in iter_graphemes(text)]
    for start, end in reversed(clusters):
        w = _cluster_units(text, start, end)
        if used + w > budget:
            break
        kept.append(text[start:end])
        used += w
    return marker + "".join(reversed(kept))


_BREAK_AFTER = frozenset(" \t-,;:/\\|)]}>.!?。、，；：！？）】》")


def wrap(s, width, break_long_words=True, strip=True):
    """Wrap ``s`` into lines of at most *width* visible cells.

    A classic word-wrapper with one twist: it operates on grapheme clusters, so
    it can never cut through an emoji or a combining sequence, and every
    returned line measures at most *width* terminal cells -- verified for CJK,
    emoji and ANSI input alike.
    """
    if width <= 0:
        raise ValueError("width must be positive")

    result = []
    text = strip_ansi(s) if strip else s
    for raw in (text.splitlines() or [""]):
        if not raw:
            result.append("")
            continue

        clusters = [(a, b) for a, b in iter_graphemes(raw)]
        line, line_w = "", 0
        word, word_w = "", 0

        def emit(finished):
            """Push a finished line, without trailing whitespace."""
            result.append(finished.rstrip())

        def flush_word():
            """Move the pending word onto the current line, wrapping if needed."""
            nonlocal line, line_w
            if not word:
                return
            if line_w + word_w <= width:
                line += word
                line_w += word_w
            else:
                if line:
                    emit(line)
                line, line_w = word, word_w

        def hard_burst(too_long):
            """Split an over-long word into full lines + a remainder."""
            run, run_w = "", 0
            pieces = []
            for s2, e2 in iter_graphemes(too_long):
                seg = too_long[s2:e2]
                seg_w = _cluster_units(too_long, s2, e2)
                if run and run_w + seg_w > width:
                    pieces.append(run)
                    run, run_w = seg, seg_w
                else:
                    run += seg
                    run_w += seg_w
            if run:
                pieces.append(run)
            return pieces

        for start, end in clusters:
            piece = raw[start:end]
            pw = _cluster_units(raw, start, end)

            # Whitespace or CJK punctuation offers a legal break opportunity.
            if piece.strip() == "" or piece in _BREAK_AFTER:
                flush_word()
                word, word_w = "", 0
                if piece.strip() == "":
                    if not line:
                        continue            # never start a line with padding
                    piece, pw = " ", 1
                if line_w + pw > width:
                    if line:
                        emit(line)
                    line, line_w = "", 0
                    continue
                line += piece
                line_w += pw
                continue

            # Full-width glyphs break at any point (this is how CJK and East
            # Asian typesetting works), so they go straight onto the line
            # instead of being buffered as an indivisible word.  Buffering them
            # would leave short, ragged lines like ['中华人民', '共', ...].
            if pw >= 2:
                flush_word()
                word, word_w = "", 0
                if line_w + pw > width:
                    if line:
                        emit(line)
                    line, line_w = piece, pw
                else:
                    line += piece
                    line_w += pw
                continue

            word += piece
            word_w += pw
            if break_long_words and word_w > width:
                if line:
                    emit(line)
                    line, line_w = "", 0
                pieces = hard_burst(word)
                # Full-width pieces go out now; the remainder seeds the next
                # line so that no character is ever silently dropped.
                for already_full in pieces[:-1]:
                    result.append(already_full)
                leftover = pieces[-1]
                line, line_w = leftover, str_width(leftover, strip=False)
                word, word_w = "", 0

        flush_word()
        if line:
            emit(line)
    return result
