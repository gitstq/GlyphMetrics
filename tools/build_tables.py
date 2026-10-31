#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GlyphMetrics — Unicode table generator (offline build step)

Reads official Unicode Character Database (UCD) files and emits a compact,
zero-dependency Python data module used at runtime.

This script is ONLY needed when upgrading to a new Unicode version.
The generated `glyphmetrics/tables.py` is committed to the repository, so
end users never need network access or any third-party package.

Usage:
    python3 tools/build_tables.py --ucd-dir /tmp/ucd [--out glyphmetrics/tables.py]

Required UCD files (Unicode 16.0.0 by default):
    EastAsianWidth.txt
    emoji-data.txt
    auxiliary/GraphemeBreakProperty.txt
    extracted/DerivedGeneralCategory.txt
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import sys

# --------------------------------------------------------------------------
# UCD parsing helpers
# --------------------------------------------------------------------------

# Characters that are conceptually "zero width" but not covered by their
# General_Category (Hangul medial/final jamo are Lo but occupy no cell).
_EXTRA_ZERO_RANGES = [
    (0x1160, 0x11FF),   # HANGUL JUNGSEONG / JONGSEONG (medial & final jamo)
    (0x2060, 0x2064),   # word joiner / invisible operators
    (0xFFA0, 0xFFA0),   # halfwidth hangul filler
]
_REGIONAL_INDICATOR = (0x1F1E6, 0x1F1FF)
_ZWJ = 0x200D


def parse_prop_file(path, wanted_props=None):
    """Parse a standard UCD data file into {propname: [(lo, hi), ...]}."""
    result = {}
    if not os.path.exists(path):
        raise SystemExit(f"[build_tables] missing UCD file: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split(";")]
            if len(parts) < 2:
                continue
            cps, prop = parts[0], parts[1]
            # DerivedGeneralCategory style: "0021 ; Po ; Po" -> keep first two
            # emoji-data style: "0023 ; Text ; number sign"
            prop = prop.split()[0] if prop else prop
            if wanted_props is not None and prop not in wanted_props:
                continue
            if ".." in cps:
                lo_s, hi_s = cps.split("..", 1)
                try:
                    lo, hi = int(lo_s, 16), int(hi_s, 16)
                except ValueError:
                    continue
            else:
                try:
                    lo = hi = int(cps, 16)
                except ValueError:
                    continue
            if hi > 0x10FFFF:
                hi = 0x10FFFF
            result.setdefault(prop, []).append((lo, hi))
    # normalize
    for prop, ranges in list(result.items()):
        result[prop] = normalize(ranges)
    return result


def parse_grambreak_file(path):
    """GraphemeBreakProperty.txt stores values in field 2 as *value* names."""
    return parse_prop_file(path)


def normalize(ranges):
    """Sort + merge overlapping/adjacent ranges."""
    if not ranges:
        return []
    ranges = sorted((int(a), int(b)) for a, b in ranges)
    merged = []
    cur_lo, cur_hi = ranges[0]
    for lo, hi in ranges[1:]:
        if lo <= cur_hi + 1:
            cur_hi = max(cur_hi, hi)
        else:
            merged.append((cur_lo, cur_hi))
            cur_lo, cur_hi = lo, hi
    merged.append((cur_lo, cur_hi))
    return merged


def union(*range_lists):
    flat = []
    for rl in range_lists:
        flat.extend(rl)
    return normalize(flat)


def subtract(base, holes):
    """base - holes (all are normalized range lists)."""
    if not holes:
        return normalize(base)
    holes = normalize(holes)
    out = []
    for lo, hi in base:
        pieces = [(lo, hi)]
        for hlo, hhi in holes:
            nxt = []
            for plo, phi in pieces:
                if hhi < plo or hlo > phi:
                    nxt.append((plo, phi))
                    continue
                if plo < hlo:
                    nxt.append((plo, hlo - 1))
                if phi > hhi:
                    nxt.append((hhi + 1, phi))
            pieces = nxt
            if not pieces:
                break
        out.extend(pieces)
    return normalize(out)


def flat_ints(ranges):
    """[ (a,b), (c,d) ] -> [a,b,c,d] for a compact literal."""
    out = []
    for lo, hi in ranges:
        out.append(lo)
        out.append(hi)
    return out


def fmt_int_list(ranges, per_line=10):
    vals = flat_ints(ranges)
    lines = []
    for i in range(0, len(vals), per_line * 2):
        chunk = vals[i:i + per_line * 2]
        lines.append("    " + ", ".join(str(v) for v in chunk) + ",")
    return "\n".join(lines)


def human(n):
    return f"{n:,}"


# --------------------------------------------------------------------------
# Main build
# --------------------------------------------------------------------------

def build(ucd_dir, version):
    eaw_path = os.path.join(ucd_dir, "EastAsianWidth.txt")
    emoji_path = os.path.join(ucd_dir, "emoji-data.txt")
    gbp_path = os.path.join(ucd_dir, "GraphemeBreakProperty.txt")
    gc_path = os.path.join(ucd_dir, "DerivedGeneralCategory.txt")

    print(f"[build_tables] Unicode version: {version}")

    eaw = parse_prop_file(eaw_path, {"W", "F", "A", "N", "Na", "H"})
    emoji = parse_prop_file(emoji_path)
    gbp = parse_grambreak_file(gbp_path)
    gc = parse_prop_file(gc_path)

    eaw_wide = union(eaw.get("W", []), eaw.get("F", []))
    eaw_ambiguous = eaw.get("A", [])

    # GlyphMetrics policy for WIDE (2 cells):
    #   East_Asian_Width in {W, F}
    #   + Regional Indicators (needed for flag sequences)
    #   + Emoji with default text-presentation OFF (Emoji_Presentation=Yes)
    emoji_presentation = emoji.get("Emoji_Presentation", [])
    wide_ranges = union(eaw_wide, [_REGIONAL_INDICATOR], emoji_presentation)
    print(f"[build_tables] WIDE code points        : {human(sum(b - a + 1 for a, b in wide_ranges))}"
          f" ({human(len(wide_ranges))} ranges)")

    # Grapheme cluster support sets
    extend = gbp.get("Extend", [])
    spacing_mark = gbp.get("SpacingMark", [])
    prepend = gbp.get("Prepend", [])
    # NOTE: in Unicode 16 the `Extended_Pictographic` property lives in
    # emoji-data.txt (not GraphemeBreakProperty.txt), and ZWJ is its own
    # Grapheme_Break value (it is *not* part of Extend in this file).
    ext_pict = emoji.get("Extended_Pictographic", [])
    zwj_ranges = union(gbp.get("ZWJ", []), [(_ZWJ, _ZWJ)])
    ri_ranges = union(gbp.get("Regional_Indicator", []), [_REGIONAL_INDICATOR])

    # Hangul syllable decomposition parts (UAX #29 rules GB6..GB8)
    hangul_l = gbp.get("L", [])
    hangul_v = gbp.get("V", [])
    hangul_t = gbp.get("T", [])
    hangul_lv = gbp.get("LV", [])
    hangul_lvt = gbp.get("LVT", [])

    # Anything wide never counts as zero-width.

    # ZERO width core :: Mn, Me (combining marks), Cf (format incl. ZWJ)
    zero_core = union(gc.get("Mn", []), gc.get("Me", []), gc.get("Cf", []))
    zero_core = union(zero_core, _EXTRA_ZERO_RANGES, zwj_ranges)
    # NOTE: ZERO and WIDE are orthogonal concepts - a skin-tone modifier is
    # both East Asian Wide *and* an Extend marker.  Removing wide code points
    # from these tables would silently break grapheme clustering, so they are
    # kept intact and width conflicts are resolved by evaluation order in
    # `_core._raw_width()` (zero wins over wide).
    zero_ranges = zero_core
    print(f"[build_tables] ZERO code points        : {human(sum(b - a + 1 for a, b in zero_ranges))}"
          f" ({human(len(zero_ranges))} ranges)")

    # Control characters: reported as width -1 (wcwidth compatible convention)
    control_ranges = union(gc.get("Cc", []))
    control_ranges = control_ranges
    print(f"[build_tables] CONTROL code points     : {human(sum(b - a + 1 for a, b in control_ranges))}")

    extend_ranges = union(extend)
    print(f"[build_tables] EXTEND code points      : {human(sum(b - a + 1 for a, b in extend_ranges))}"
          f" ({human(len(extend_ranges))} ranges)")
    print(f"[build_tables] SPACINGMARK             : {human(len(spacing_mark))} ranges")
    print(f"[build_tables] PREPEND                 : {human(len(prepend))} ranges")
    print(f"[build_tables] EXTENDED_PICTOGRAPHIC   : {human(len(ext_pict))} ranges")
    print(f"[build_tables] ZWJ / REGIONAL_IND      : {human(len(zwj_ranges))} / {human(len(ri_ranges))} ranges")
    print(f"[build_tables] HANGUL L/V/T/LV/LVT     : "
          f"{human(len(hangul_l))}/{human(len(hangul_v))}/{human(len(hangul_t))}/"
          f"{human(len(hangul_lv))}/{human(len(hangul_lvt))} ranges")

    header = f'''# -*- coding: utf-8 -*-
"""
GlyphMetrics - generated Unicode tables ({version})

!! THIS FILE IS AUTO-GENERATED BY tools/build_tables.py - DO NOT EDIT BY HAND !!

Derived purely from the Unicode Character Database (UCD) published by the
Unicode Consortium.  No runtime third-party dependency is introduced: every
set below is stored as a flat, ascending list of inclusive code point pairs,
[lo0, hi0, lo1, hi1, ...], searched with binary bisection.

Regenerate with:
    python3 tools/build_tables.py --ucd-dir <UCD> --unicode-version {version}
"""

from __future__ import annotations

UNICODE_VERSION = "{version}"
GENERATED_AT = "{_dt.datetime.now().strftime('%Y-%m-%d')}"

flat = []

_WIDE = [
{fmt_int_list(wide_ranges)}
]

_ZERO = [
{fmt_int_list(zero_ranges)}
]

_CONTROL = [
{fmt_int_list(control_ranges)}
]

_EXTEND = [
{fmt_int_list(extend_ranges)}
]

_SPACING_MARK = [
{fmt_int_list(spacing_mark)}
]

_PREPEND = [
{fmt_int_list(prepend)}
]

_EXTENDED_PICTOGRAPHIC = [
{fmt_int_list(ext_pict)}
]

_REGIONAL_INDICATOR = [
{fmt_int_list(ri_ranges)}
]

_JAMO_L = [
{fmt_int_list(hangul_l)}
]

_JAMO_V = [
{fmt_int_list(hangul_v)}
]

_JAMO_T = [
{fmt_int_list(hangul_t)}
]

_JAMO_LV = [
{fmt_int_list(hangul_lv)}
]

_JAMO_LVT = [
{fmt_int_list(hangul_lvt)}
]

# Characters whose East_Asian_Width is "Ambiguous" (A).  Rendered narrow by
# default; GlyphMetrics can optionally treat them as wide.
_AMBIGUOUS = [
{fmt_int_list(eaw_ambiguous)}
]

ZERO_WIDTH_JOINER = 0x200D
VARIATION_SELECTOR_15 = 0xFE0E   # text presentation  -> width 1
VARIATION_SELECTOR_16 = 0xFE0F   # emoji presentation -> width 2

__all__ = [
    "UNICODE_VERSION", "GENERATED_AT", "_WIDE", "_ZERO", "_CONTROL",
    "_EXTEND", "_SPACING_MARK", "_PREPEND", "_EXTENDED_PICTOGRAPHIC",
    "_REGIONAL_INDICATOR", "_AMBIGUOUS", "_JAMO_L", "_JAMO_V", "_JAMO_T",
    "_JAMO_LV", "_JAMO_LVT", "ZERO_WIDTH_JOINER",
    "VARIATION_SELECTOR_15", "VARIATION_SELECTOR_16",
]
'''
    return header


def main():
    ap = argparse.ArgumentParser(description="Generate GlyphMetrics Unicode tables")
    ap.add_argument("--ucd-dir", default="/tmp/ucd")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "glyphmetrics", "tables.py"))
    ap.add_argument("--unicode-version", default="16.0.0")
    args = ap.parse_args()

    content = build(args.ucd_dir, args.unicode_version)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(content)
    print(f"[build_tables] written -> {args.out} ({os.path.getsize(args.out):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
