# -*- coding: utf-8 -*-
"""
Command line interface for GlyphMetrics.

Every subcommand reads from argv so it works both interactively and in scripts.
Stdin is supported with "-" for text taking commands.
"""

from __future__ import annotations

import argparse
import sys

from . import __version__
from ._core import _cluster_units
from .tables import UNICODE_VERSION
from ._core import (
    char_width,
    graphemes,
    grapheme_len,
    has_ansi,
    iter_graphemes,
    pad,
    str_width,
    strip_ansi,
    truncate,
    wrap,
)

RESET = "\x1b[0m"


def _read_text(value):
    """Resolve a positional argument, allowing "-" for stdin."""
    if value == "-":
        return sys.stdin.read().rstrip("\n")
    return value


def _out(text=""):
    sys.stdout.write(text + "\n")


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------

def cmd_width(args):
    text = _read_text(args.text)
    opts = dict(ambiguous_as_wide=args.ambiguous)
    total = str_width(text, **opts)
    if args.json:
        _out('{"width": %d, "codepoints": %d, "graphemes": %d}'
             % (total, len(text), grapheme_len(text)))
        return 0
    _out("%s%d%s  (codepoints=%d graphemes=%d)"
         % ("", total, "", len(text), grapheme_len(text)))
    return 0


def cmd_chars(args):
    text = _read_text(args.text)
    opts = dict(ambiguous_as_wide=args.ambiguous)
    _out("%-12s %-8s %-6s %s" % ("CODEPOINT", "WIDTH", "CELLS", "NAME"))
    for start, end in iter_graphemes(text):
        cluster = text[start:end]
        if len(cluster) > 1:
            codes = "+".join("U+%04X" % ord(c) for c in cluster)
            if len(codes) > 26:
                codes = codes[:23] + "..."
            _out("%-12s %-8s %-6d %s" % (codes, "cluster",
                                         _cluster_units(text, start, end,
                                                        args.ambiguous),
                                         "grapheme cluster"))
        else:
            ch = cluster[0]
            _out("%-12s %-8d %-6d %s"
                 % ("U+%04X" % ord(ch), char_width(ch, **opts),
                    char_width(ch, **opts),
                    _safe_name(ch)))
    return 0


def _safe_name(ch):
    import unicodedata
    try:
        return unicodedata.name(ch).title()
    except ValueError:
        return "<unnamed>"


def cmd_clusters(args):
    text = _read_text(args.text)
    out = graphemes(text)
    if args.json:
        import json
        _out(json.dumps(out, ensure_ascii=False))
        return 0
    for i, g in enumerate(out, 1):
        codes = " ".join("U+%04X" % ord(c) for c in g)
        _out("%3d. %s   <- %s" % (i, g, codes))
    return 0


def cmd_pad(args):
    text = _read_text(args.text)
    result = pad(text, args.width, align=args.align, fill=args.fill)
    _out("|%s|" % result)
    return 0


def cmd_truncate(args):
    text = _read_text(args.text)
    marker = "" if args.no_ellipsis else args.ellipsis
    result = truncate(text, args.width, ellipsis=marker)
    _out("|%s|" % result)
    return 0


def cmd_strip(args):
    text = _read_text(args.text)
    _out(strip_ansi(text))
    return 0


def cmd_wrap(args):
    text = _read_text(args.text)
    for line in wrap(text, args.width):
        _out(line)
    return 0


def cmd_table(args):
    """Render a demo table proving alignment under mixed-width content."""
    rows = [
        ("Region", "Language", "Sample", "Cells"),
        ("中国", "简体中文", "你好，世界", ""),
        ("中國香港", "繁體中文", "香港，台灣", ""),
        ("日本", "日本語", "こんにちは", ""),
        ("한국", "한국어", "안녕하세요", ""),
        ("Deutschland", "Deutsch", "Grüße!", ""),
        ("España", "Español", "Gracias — emoji 👨‍👩‍👧", ""),
        ("Flag", "Regional", "🇩🇪 🇯🇵 🇺🇸", ""),
        ("Combining", "Latin+mark", "é (e+U+0301)", ""),
        ("Accented", "Latin-1", "é (precomposed)", ""),
    ]
    cols = list(zip(*rows))
    widths = []
    for col in cols:
        widths.append(max(str_width(c) for c in col) + 2)
    # recompute column 3 since it holds the real samples
    for idx, col in enumerate(cols):
        widths[idx] = max(str_width(c) for c in col) + 2

    def rule():
        return "+" + "+".join("-" * w for w in widths) + "+"

    _out(rule())
    header = "|"
    for i, cell in enumerate(rows[0]):
        header += pad(" " + cell, widths[i]) + "|"
    _out(header)
    _out(rule())
    for row in rows[1:]:
        line = "|"
        for i, cell in enumerate(row):
            displayed = cell
            if i == 3:
                displayed = str(cell) if cell else "%d" % str_width(row[2])
            line += pad(" " + displayed, widths[i]) + "|"
        _out(line)
    _out(rule())
    return 0


def cmd_demo(args):
    """Show why naive len()/summing code points breaks a terminal layout."""
    samples = [
        "hello",
        "你好",
        "Grüße",
        "é",
        "👍🏽",
        "👨‍👩‍👧",
        "🇩🇪",
        "\x1b[31mERROR\x1b[0m",
    ]
    _out("")
    _out("%-14s %-9s %-9s %-9s %s"
         % ("INPUT", "len()", "codepts", "gm cells", "verdict"))
    _out("-" * 62)
    for s in samples:
        naive_cp = sum(char_width(c) for c in s)
        gm = str_width(s)
        verdict = "OK" if gm <= naive_cp else "?"
        _out("%-14s %-9d %-9d %-9d %s"
             % (_short(s), len(s), naive_cp, gm, verdict))
    _out("")
    _out("Truncation demo (width=8):")
    for s in ["Grüße bist du", "你好世界你好世界", "emoji 👨‍👩‍👧 corner"]:
        _out("   %-24s -> |%s|" % (_short(s), truncate(s, 8)))
    _out("")
    return 0


def _short(s):
    s = strip_ansi(s)
    if len(s) > 13:
        return s[:12] + "…"
    return s


def cmd_version(args):
    _out("GlyphMetrics %s" % __version__)
    _out("Unicode data version: %s" % UNICODE_VERSION)
    _out("Python: %s" % sys.version.split()[0])
    return 0


# --------------------------------------------------------------------------
# Parser
# --------------------------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(
        prog="glyphmetrics",
        description="Cluster-aware, ANSI-aware terminal text measurement.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  glyphmetrics width '你好'\n"
            "  glyphmetrics width '\x1b[31mERROR\x1b[0m'\n"
            "  glyphmetrics clusters '👨‍👩‍👧'\n"
            "  glyphmetrics pad '标题' -w 20 -a center\n"
            "  glyphmetrics demo\n"
        ),
    )
    p.add_argument("-V", "--version", action="store_true", help="show version")
    sub = p.add_subparsers(dest="command")

    def add_width_opt(sp):
        sp.add_argument("-A", "--ambiguous", action="store_true",
                        help="treat East Asian Ambiguous characters as wide")

    sp = sub.add_parser("width", aliases=["w"], help="measure display width")
    sp.add_argument("text")
    sp.add_argument("--json", action="store_true")
    add_width_opt(sp)
    sp.set_defaults(func=cmd_width)

    sp = sub.add_parser("chars", help="per-character / per-cluster breakdown")
    sp.add_argument("text")
    add_width_opt(sp)
    sp.set_defaults(func=cmd_chars)

    sp = sub.add_parser("clusters", aliases=["c"], help="list grapheme clusters")
    sp.add_argument("text")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_clusters)

    sp = sub.add_parser("pad", help="pad to an exact visible width")
    sp.add_argument("text")
    sp.add_argument("-w", "--width", type=int, required=True)
    sp.add_argument("-a", "--align", choices=["left", "right", "center"],
                    default="left")
    sp.add_argument("-f", "--fill", default=" ")
    sp.set_defaults(func=cmd_pad)

    sp = sub.add_parser("truncate", aliases=["t"], help="truncate to width")
    sp.add_argument("text")
    sp.add_argument("-w", "--width", type=int, required=True)
    sp.add_argument("-e", "--ellipsis", default="…")
    sp.add_argument("--no-ellipsis", action="store_true")
    sp.set_defaults(func=cmd_truncate)

    sp = sub.add_parser("strip", help="remove ANSI escape sequences")
    sp.add_argument("text")
    sp.set_defaults(func=cmd_strip)

    sp = sub.add_parser("wrap", help="wrap text to a width")
    sp.add_argument("text")
    sp.add_argument("-w", "--width", type=int, required=True)
    sp.set_defaults(func=cmd_wrap)

    sp = sub.add_parser("table", help="render a mixed-width demo table")
    sp.set_defaults(func=cmd_table)

    sp = sub.add_parser("demo", help="compare len() vs GlyphMetrics")
    sp.set_defaults(func=cmd_demo)

    sp = sub.add_parser("version", help="print version info")
    sp.set_defaults(func=cmd_version)

    return p


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    if argv and argv[0] in ("-V", "--version"):
        return cmd_version(None)
    args = parser.parse_args(argv)
    if getattr(args, "version", False):
        return cmd_version(args)
    if not getattr(args, "func", None):
        parser.print_help()
        return 1
    try:
        return args.func(args) or 0
    except BrokenPipeError:      # piping into head/less
        return 0
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
