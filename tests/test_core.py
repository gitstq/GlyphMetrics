# -*- coding: utf-8 -*-
"""
Test suite for GlyphMetrics.

Runs with zero third-party dependencies:
    python3 -m unittest discover -s tests
or simply:
    python3 tests/test_core.py
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import glyphmetrics as gm  # noqa: E402


class TestCharWidth(unittest.TestCase):

    def test_ascii(self):
        self.assertEqual(gm.char_width("a"), 1)
        self.assertEqual(gm.char_width("Z"), 1)
        self.assertEqual(gm.str_width("hello"), 5)

    def test_empty(self):
        self.assertEqual(gm.str_width(""), 0)
        self.assertEqual(gm.grapheme_len(""), 0)

    def test_cjk_wide(self):
        self.assertEqual(gm.char_width("你"), 2)
        self.assertEqual(gm.char_width("好"), 2)
        self.assertEqual(gm.str_width("你好"), 4)
        self.assertEqual(gm.char_width("한"), 2)        # Hangul syllable
        self.assertEqual(gm.char_width("あ"), 2)        # Hiragana

    def test_fullwidth_forms(self):
        self.assertEqual(gm.char_width("Ａ"), 2)        # fullwidth A
        self.assertEqual(gm.str_width("ＡＢＣ"), 6)

    def test_combining_marks_are_zero(self):
        self.assertEqual(gm.char_width("́"), 0)    # combining acute
        # decomposed e-acute still occupies one cell
        self.assertEqual(gm.str_width("é"), 1)
        # precomposed also one cell
        self.assertEqual(gm.str_width("é"), 1)

    def test_zero_width_joiner_and_space(self):
        self.assertEqual(gm.char_width("‍"), 0)
        self.assertEqual(gm.char_width("​"), 0)    # ZWSP
        self.assertEqual(gm.char_width("﻿"), 0)    # BOM

    def test_ambiguous_narrow_by_default(self):
        # Greek/Cyrillic are East Asian Ambiguous -> 1 by default, 2 on request
        self.assertEqual(gm.char_width("α"), 1)
        self.assertEqual(gm.char_width("α", ambiguous_as_wide=True), 2)
        self.assertEqual(gm.str_width("αβγ"), 3)
        self.assertEqual(gm.str_width("αβγ", ambiguous_as_wide=True), 6)

    def test_control_chars_do_not_break_layout(self):
        self.assertEqual(gm.str_width("\x1b"), 0)
        self.assertEqual(gm.str_width("a\nb"), 2)   # newlines contribute 0

    def test_char_width_rejects_multi_char(self):
        with self.assertRaises(ValueError):
            gm.char_width("ab")


class TestEmoji(unittest.TestCase):

    def test_simple_emoji_is_two_cells(self):
        self.assertEqual(gm.str_width("👍"), 2)

    def test_emoji_with_skin_tone_modifier(self):
        # U+1F44D + U+1F3FD -> one glyph, two cells
        seq = "\U0001F44D\U0001F3FD"
        self.assertEqual(gm.grapheme_len(seq), 1)
        self.assertEqual(gm.str_width(seq), 2)

    def test_flag_is_two_cells_not_four(self):
        flag = "\U0001F1E9\U0001F1EA"      # 🇩🇪
        self.assertEqual(gm.grapheme_len(flag), 1)
        self.assertEqual(gm.str_width(flag), 2)
        # two separate flags = 2 clusters
        two = "\U0001F1E9\U0001F1EA\U0001F1EF\U0001F1F5"   # 🇩🇪🇯🇵
        self.assertEqual(gm.grapheme_len(two), 2)
        self.assertEqual(gm.str_width(two), 4)

    def test_three_regional_indicators(self):
        # odd run: first RI stands alone, remaining pair is a flag
        seq = "\U0001F1E9\U0001F1EA\U0001F1EF"
        clusters = gm.graphemes(seq)
        self.assertEqual(len(clusters), 2)

    def test_family_zwj_sequence(self):
        family = "\U0001F468‍\U0001F469‍\U0001F467"   # 👨‍👩‍👧
        self.assertEqual(len(family), 5)                       # 5 code points
        self.assertEqual(gm.grapheme_len(family), 1)           # 1 glyph
        self.assertEqual(gm.str_width(family), 2)              # 2 cells
        self.assertLess(gm.str_width(family), 8)               # naive would give 8

    def test_variation_selector_16_forces_wide(self):
        # ❤ U+2764 is narrow by itself
        heart = "❤"
        self.assertEqual(gm.str_width(heart), 1)
        # with VS16 it becomes the emoji presentation, two cells
        self.assertEqual(gm.str_width(heart + "️"), 2)

    def test_variation_selector_15_forces_narrow(self):
        watch = "⌚"                       # EAW = W in most tables -> 2
        narrow = watch + "︎"          # VS15 -> text presentation
        self.assertEqual(gm.str_width(narrow), 1)

    def test_keycap_sequence(self):
        keycap = "1️⃣"     # '1' + VS16 + U+20E3
        self.assertEqual(gm.grapheme_len(keycap), 1)
        self.assertEqual(gm.str_width(keycap), 2)


class TestHangul(unittest.TestCase):

    def test_jamo_cluster(self):
        # decomposed 한 = U+1112 U+1161 U+11AB -> one cluster
        seq = "한"
        self.assertEqual(gm.grapheme_len(seq), 1)
        self.assertEqual(gm.str_width(seq), 2)

    def test_precomposed_syllable(self):
        self.assertEqual(gm.str_width("한"), 2)


class TestANSI(unittest.TestCase):

    def test_has_ansi(self):
        self.assertTrue(gm.has_ansi("\x1b[31m"))
        self.assertFalse(gm.has_ansi("plain"))

    def test_strip_ansi(self):
        self.assertEqual(gm.strip_ansi("\x1b[31mERROR\x1b[0m"), "ERROR")
        self.assertEqual(gm.strip_ansi("\x1b[1;32;40mOK\x1b[0m"), "OK")

    def test_strip_osc_hyperlink(self):
        s = "\x1b]8;;https://example.com\x07link\x1b]8;;\x07"
        self.assertEqual(gm.strip_ansi(s), "link")

    def test_colored_text_width(self):
        colored = "\x1b[38;5;208m你好\x1b[0m"
        self.assertEqual(gm.str_width(colored), 4)
        self.assertEqual(gm.str_width("\x1b[31mERROR\x1b[0m"), 5)

    def test_tab_counts_as_one_cell(self):
        # tabs must be handled by expandtabs() before measuring
        self.assertEqual(gm.str_width("a\tb"), 2)


class TestGraphemes(unittest.TestCase):

    def test_cluster_indices_cover_input(self):
        for s in ["hello", "你好世界", "\U0001F468‍\U0001F469‍\U0001F467", "🇩🇪🇯🇵"]:
            pieces = [s[a:b] for a, b in gm.iter_graphemes(s)]
            self.assertEqual("".join(pieces), s)

    def test_crlf_is_one_cluster(self):
        self.assertEqual(gm.grapheme_len("a\r\nb"), 3)

    def test_grapheme_len_vs_len(self):
        s = "\U0001F468‍\U0001F469‍\U0001F467"
        self.assertEqual(len(s), 5)
        self.assertEqual(gm.grapheme_len(s), 1)


class TestLayout(unittest.TestCase):

    def test_pad_left(self):
        self.assertEqual(gm.pad("hi", 5), "hi   ")
        self.assertEqual(gm.str_width(gm.pad("hi", 5)), 5)

    def test_pad_right(self):
        self.assertEqual(gm.rjust("hi", 5), "   hi")

    def test_pad_center(self):
        r = gm.center("hi", 6)
        self.assertEqual(gm.str_width(r), 6)
        self.assertEqual(r, "  hi  ")

    def test_pad_preserves_ansi(self):
        s = "\x1b[31mAB\x1b[0m"
        padded = gm.pad(s, 6)
        self.assertEqual(gm.str_width(padded), 6)
        self.assertIn("\x1b[31m", padded)
        # visible content must be exactly "AB" plus 4 spaces
        self.assertEqual(gm.strip_ansi(padded), "AB    ")

    def test_pad_does_not_shrink_wide_content(self):
        r = gm.pad("你好", 3)
        self.assertEqual(gm.str_width(r), 3)

    def test_pad_invalid_align(self):
        with self.assertRaises(ValueError):
            gm.pad("x", 5, align="block")

    def test_truncate_ascii(self):
        # width is inclusive of the ellipsis: 3 cells -> "ab…" (2 + 1)
        self.assertEqual(gm.truncate("abcdef", 3), "ab…")
        self.assertEqual(gm.str_width(gm.truncate("abcdef", 3)), 3)
        self.assertEqual(gm.truncate("abcdef", 3, ellipsis=""), "abc")
        self.assertEqual(gm.truncate("abc", 10), "abc")

    def test_truncate_wide(self):
        r = gm.truncate("你好世界", 4)
        self.assertLessEqual(gm.str_width(r), 4)

    def test_truncate_never_splits_cluster(self):
        s = "🇩🇪🇯🇵🇺🇸"
        for w in range(1, 7):
            out = gm.truncate(s, w)
            self.assertLessEqual(gm.str_width(out), w)
            # result must consist of whole clusters
            self.assertEqual(out.replace("…", ""),
                             "".join(gm.graphemes(out.replace("…", ""))))

    def test_truncate_keeps_ansi_and_closes_it(self):
        s = "\x1b[31mHello World\x1b[0m"
        out = gm.truncate(s, 5)
        self.assertIn("\x1b[31m", out)
        self.assertTrue(out.endswith("\x1b[0m"))
        self.assertLessEqual(gm.str_width(out), 5)

    def test_truncate_width_zero(self):
        self.assertEqual(gm.truncate("anything", 0), "")

    def test_truncate_front_keeps_tail(self):
        path = "/very/long/path/file.txt"
        out = gm.truncate_front(path, 12)
        self.assertLessEqual(gm.str_width(out), 12)
        self.assertTrue(out.endswith("file.txt") or out.endswith(".txt…")
                        or out.endswith("…"))
        self.assertTrue(out.startswith("…"))

    def test_wrap_basic(self):
        lines = gm.wrap("the quick brown fox jumps over the lazy dog", 12)
        for line in lines:
            self.assertLessEqual(gm.str_width(line), 12)
        self.assertEqual(" ".join(lines), "the quick brown fox jumps over the lazy dog")

    def test_wrap_cjk(self):
        lines = gm.wrap("中华人民共和国万岁世界人民大团结万岁", 8)
        for line in lines:
            self.assertLessEqual(gm.str_width(line), 8)
        self.assertEqual("".join(lines), "中华人民共和国万岁世界人民大团结万岁")

    def test_wrap_long_word_hard_split(self):
        lines = gm.wrap("A" * 30, 10)
        self.assertTrue(all(gm.str_width(l) <= 10 for l in lines))
        self.assertEqual("".join(lines), "A" * 30)

    def test_wrap_zero_width_raises(self):
        with self.assertRaises(ValueError):
            gm.wrap("text", 0)


class TestConsistency(unittest.TestCase):
    """Property checks across a wide slice of the code point space."""

    def test_width_is_never_negative_for_plain_text(self):
        sample = "".join(chr(c) for c in range(0x20, 0x2FFFF, 0x1F))
        total = gm.str_width(sample)
        self.assertGreater(total, 0)

    def test_pad_result_always_has_requested_width(self):
        for s in ["", "a", "你好", "\U0001F468‍\U0001F469‍\U0001F467", "\x1b[31mx\x1b[0m"]:
            natural = gm.str_width(s)
            for w in range(0, 12):
                out = gm.pad(s, w)
                if natural <= w:
                    self.assertEqual(gm.str_width(out), w,
                                     "pad(%r, %d) should be exactly %d cells" % (s, w, w))
                else:
                    self.assertLessEqual(gm.str_width(out), w,
                                         "pad(%r, %d) overflowed its budget" % (s, w))

    def test_deterministic(self):
        s = "\U0001F1E9\U0001F1EA你好a"
        self.assertEqual(gm.str_width(s), gm.str_width(s))


if __name__ == "__main__":
    unittest.main(verbosity=2)
