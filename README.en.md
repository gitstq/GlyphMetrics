<div align="center">

# 🔤 GlyphMetrics

**Cluster-aware, ANSI-aware terminal text measurement for Python**

[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)](#-quick-start)
[![Unicode](https://img.shields.io/badge/Unicode-16.0.0-orange.svg)](https://www.unicode.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)

[简体中文](./README.md) | [繁體中文](./README.zh-TW.md) | 🌍 **English**

</div>

---

## 🎉 Introduction

If you have ever built a CLI dashboard, you have met this bug:

> "Both strings have the same `len()`, so why is my table border crooked?"

Because terminals do not lay out *characters* — they lay out **cells**. And how many cells a character occupies is messier than it looks:

| Text | `len()` | Naive sum | Real cells | What's going on |
|------|:---:|:---:|:---:|------|
| `hello` | 5 | 5 | **5** | calm and peaceful |
| `你好` | 2 | 2 | **4** | CJK ideographs are double-width |
| `\x1b[31mERROR\x1b[0m` | 14 | 12 | **5** | escape sequences are invisible |
| `é` (decomposed) | 2 | 2 | **1** | combining marks take no space |
| `👨‍👩‍👧` | 5 | 8 | **2** | ZWJ fuses three people into one glyph |
| `🇩🇪` | 2 | 4 | **2** | two regional indicators make one flag |

**GlyphMetrics exists to answer exactly one question:** *how many terminal cells will this string actually occupy?*

It is pure standard library, has **zero dependencies**, and works offline.

### 🧬 How is this different from `wcwidth`?

[wcwidth](https://github.com/jquast/wcwidth) is the de-facto baseline in this space. GlyphMetrics stands on the same Unicode standards, but closes two gaps that wcwidth deliberately leaves open:

| Aspect | wcwidth | GlyphMetrics |
|--------|---------|--------------|
| Unit of work | sum over code points | **segment grapheme clusters first, then measure the cluster** |
| Family emoji `👨‍👩‍👧` | 6 cells (summed up) | **2 cells** (one glyph) ✅ |
| Flag `🇩🇪` | 4 cells | **2 cells** ✅ |
| ANSI escapes | caller must strip them first | **built in, automatically skipped** ✅ |
| Aligning coloured text | caller must not cut an escape | **`pad`/`truncate` handle it and re-append `\x1b[0m`** ✅ |
| Runtime deps | none | none |
| Ships with | library only | library **+ ready-to-use CLI** ✅ |

> 💡 The design debt of wcwidth comes from its "one code point at a time" model. Modern terminal fonts render ZWJ
> emoji sequences and flags as single glyphs, and UAX #29 has specified grapheme clusters for years —
> GlyphMetrics simply follows the standard.

---

## ✨ Features

- 🧩 **Cluster-first.** Implements UAX #29 rules GB3–GB13, so ZWJ families, skin-tone modifiers, flags, Devanagari text and decomposed Hangul are all measured as *one* glyph.
- 🎨 **ANSI transparent.** CSI colour codes, OSC hyperlinks and friends count as zero cells. Pass a coloured string straight into `str_width` — no pre-stripping.
- ✂️ **Safe truncation.** `truncate()` never splits a cluster and always closes the escape with `\x1b[0m`, so your terminal never stays red.
- 📏 **Real alignment.** `pad()`, `ljust()`, `rjust()`, `center()` keep the original colour and pad only the visible part.
- 🇺🇳 **Full East Asian Width.** Ships the complete table, with an opt-in `ambiguous_as_wide=True` for terminals that render Greek/Cyrillic wide.
- 😀 **Unicode 16.0.0.** Tables generated from official UCD files and committed to the repo, so it works **fully offline**.
- 🪶 **Genuinely zero-dependency.** The `dependencies` list is empty. What ships with `python3` is enough.
- ⚡ **Performance that holds up.** ASCII goes through C-level `str.translate`; repeat measurements hit an LRU cache. See [benchmarks](#-benchmarks).
- 🖥️ **Batteries-included CLI.** `width`, `clusters`, `pad`, `truncate`, `wrap`, `table`, `demo` — debug layout issues without writing a script.
- 🧪 **46 unit tests.** Covering ZWJ emoji, flags, VS15/VS16, keycaps, ANSI, CRLF, decomposed Hangul and more.

---

## 🚀 Quick start

### Requirements

- Python **3.8+**
- That's it — no `pip install <dependency>` step exists

```bash
# Option 1: pip (recommended)
pip install glyphmetrics

# Option 2: from source
git clone https://github.com/gitstq/GlyphMetrics.git
cd GlyphMetrics
pip install -e .

# Option 3: no install at all - just copy the glyphmetrics/ package directory
# into your project. It is plain Python and needs no metadata to work.
```

### Three lines to get going

```python
import glyphmetrics as gm

gm.str_width("你好")                    # -> 4   (two fullwidth ideographs)
gm.str_width("\x1b[31mERROR\x1b[0m")    # -> 5   (colour codes take no room)
gm.str_width("👨‍👩‍👧")                # -> 2   (5 code points, 1 glyph, 2 cells)
```

### Try the CLI

```bash
$ glyphmetrics demo
INPUT          len()     codepts   gm cells  verdict
--------------------------------------------------------------
hello          5         5         5         OK
你好             2         4         4         OK
👍🏽             2         4         2         OK
👨‍👩‍👧          5         6         2         OK
🇩🇪             2         4         2         OK
ERROR          14        12        5         OK
```

---

## 📖 Detailed guide

### 🧱 1. Measurement API

| Function | Purpose | Example |
|----------|---------|---------|
| `char_width(ch, ...)` | width of a single character | `char_width("你")` → `2` |
| `str_width(s, ...)` | cells occupied by a string | `str_width("你好")` → `4` |
| `graphemes(s)` | list of grapheme clusters | `graphemes("👨‍👩‍👧")` → `['👨‍👩‍👧']` |
| `grapheme_len(s)` | perceived character count (≠ `len()`) | `grapheme_len("👨‍👩‍👧")` → `1` |
| `iter_graphemes(s)` | lazy `(start, end)` slices | for custom segmentation |

```python
gm.char_width("α")                          # 1  (Ambiguous, narrow by default)
gm.char_width("α", ambiguous_as_wide=True)   # 2  (opt in to wide)
gm.str_width("αβγ", ambiguous_as_wide=True)  # 6
gm.grapheme_len("é")                        # 1  — even written as 'e' + U+0301
```

### 🎨 2. ANSI handling

```python
LINK = "\x1b]8;;https://example.com\x07click here\x1b]8;;\x07"

gm.strip_ansi(LINK)     # 'click here'   — plain text back
gm.has_ansi(LINK)       # True           — does it contain escapes?
gm.str_width(LINK)      # 10             — hyperlink markers are free
```

⚠️ Tabs (``\t``) count as **0 cells** because they are control characters. If you want 4- or 8-space visuals, call `s.expandtabs(4)` before measuring.

### 📐 3. Layout API

```python
# Alignment preserves colour
gm.pad("\x1b[31mAB\x1b[0m", 6)                      # '\x1b[31mAB\x1b[0m    '
gm.strip_ansi(gm.pad("\x1b[31mAB\x1b[0m", 6))       # 'AB    '
gm.rjust("价格", 10)                                 # '        价格'
gm.center("状态", 10, fill="─")                      # '───状态───'

# Truncation never splits a cluster, and closes the escape for you
gm.truncate("你好世界", 4)                            # '你…'
gm.truncate("\x1b[31mHello World\x1b[0m", 5)          # '\x1b[31mHell…\x1b[0m'
gm.truncate_front("/very/long/path/file.txt", 12)     # '…th/file.txt'  (keeps the tail)

# Wrapping
gm.wrap("中华人民共和国万岁世界人民大团结万岁", 8)
# -> ['中华人民', '共和国万', '岁世界人', '民大团结', '万岁']
#    every line is exactly 8 cells wide, and no glyph is ever cut in half
```

### 🖥️ 4. CLI reference

| Command | Description | Example |
|---------|-------------|---------|
| `width` / `w` | measure width | `glyphmetrics width '你好'` |
| `chars` | per-character / per-cluster breakdown | `glyphmetrics chars '👍🏽'` |
| `clusters` / `c` | list grapheme clusters | `glyphmetrics clusters '👨‍👩‍👧'` |
| `pad` | align to a width | `glyphmetrics pad 'title' -w 20 -a center` |
| `truncate` / `t` | truncate | `glyphmetrics t 'a long piece of text' -w 10` |
| `strip` | strip ANSI | `glyphmetrics strip "$(printf '\033[31mx\033[0m')"` |
| `wrap` | wrap text | `glyphmetrics wrap 'ja→顔文字(˘ω˘)ｽﾔｧ…' -w 16` |
| `table` | render a mixed-width demo table | `glyphmetrics table` |
| `demo` | compare `len()` against real cells | `glyphmetrics demo` |
| `version` | version + Unicode version | `glyphmetrics version` |

`width` and `clusters` accept `--json` for pipelines:

```bash
$ glyphmetrics width '你好' --json
{"width": 4, "codepoints": 2, "graphemes": 2}
```

### 🎛️ 5. Wiring it into your TUI

A table that can never go crooked:

```python
import glyphmetrics as gm

rows = [("中国", "简体中文"), ("Deutschland", "Deutsch"), ("Flag", "🇩🇪 🇯🇵")]
w = [max(gm.str_width(r[i]) for r in rows) + 2 for i in range(2)]

for a, b in rows:
    print("|" + gm.pad(" " + a, w[0]) + "|" + gm.pad(" " + b, w[1]) + "|")
```

More real-world recipes — aligned logs, progress bars, path elision, layout assertions in tests — live in
[docs/USAGE.zh-CN.md](./docs/USAGE.zh-CN.md).

---

## ⚡ Benchmarks

Measured with Python 3.11 on strings of roughly **7,200 code points**, against `wcwidth` 0.5.3.

| Scenario | GlyphMetrics | wcwidth | Verdict |
|----------|-------------:|--------:|---------|
| Pure Latin (cold) | **4.6 µs** | 9.7 µs | 🏆 **2.1× faster** (`str.translate` fast path) |
| Mixed CJK/emoji (cold) | 5,021 µs | **982 µs** | ~5× slower (cost of cluster segmentation) |
| Mixed CJK/emoji (repeat calls) | **147 µs** | 991 µs | 🏆 **6.8× faster** (LRU cache hit) |

> 📌 **How to choose.** TUIs re-render the same titles, headers and cell values over and over — that is exactly
> where GlyphMetrics' cache hit rate peaks. If your workload is a firehose of brand-new giant strings and you are
> sure there are no ZWJ emoji in it, wcwidth is still faster. We would rather tell you this than hide it.

---

## 🔬 Divergence from `wcwidth`

We compared all **1,112,032 code points** one by one. **4,566 (0.41%)** differ, and every single category is a
deliberate decision, documented here so nothing stays hand-wavy:

| Divergence | Count | Representative | Rationale |
|------------|------:|----------------|-----------|
| wcwidth 0 → GM 1 | 4,357 | Devanagari vowel sign `U+093E` and other SpacingMarks (Mc) | UAX #11 does not classify them as zero-width; modern libraries like `rich` also return 1 |
| wcwidth 2 → GM 1 | 157 | `U+16FF2`, `U+187F8`, `U+1FAEF` | Unassigned in **Unicode 16.0** — a version difference, not a bug |
| wcwidth -1 → GM 0 | 33 | C1 controls `U+007F`–`U+009F` | Returning 0 keeps control chars from poisoning accumulated width (tune with `control_width`) |
| wcwidth 1 → GM 0 | 14 | soft hyphen `U+00AD`, Arabic number sign `U+0600` | These are `Cf` format characters that terminals do not render |
| wcwidth 0 → GM 2 | 5 | Hangul tone marks `U+302E` / `U+302F` | Follows their `East_Asian_Width=W` classification |

> 🧭 When in doubt we defer to the Unicode data files. `glyphmetrics chars "…"` prints the exact verdict and
> Unicode name, and [tools/build_tables.py](./tools/build_tables.py) shows how every table was derived.

---

## 💡 Design & roadmap

### 🏗️ Design principles

1. **Standards over folklore.** Every measurement comes from official UCD files, never from "well, my terminal
   seems to do this". The generator is reproducible.
2. **Shipped tables beat runtime computation.** Eight interval tables (~30 KB) buy zero runtime dependencies and
   plain binary-search lookups — this is also why it works offline.
3. **Never damage the caller's string.** `pad` returns coloured text as given; `truncate` appends `\x1b[0m`;
   "what you see" and "what you store" stay decoupled.
4. **Fast paths are part of the design,** not an afterthought: `str.translate` for ASCII, cached summation for
   low-plane text without combining marks, LRU for repeated measurements.

### 🗺️ Roadmap

| Version | Plan | Status |
|---------|------|--------|
| v1.0.0 | Core measurement / clustering / ANSI / layout / CLI / tri-lingual docs | ✅ released |
| v1.1.0 | UAX #14 line-break opportunities (LB rules) for `wrap()`; honour `break_words=False` | 🔜 next |
| v1.2.0 | Shrink derived tables to ≤ 15 KB; add a `--no-emoji-wide` policy switch | 🧭 exploring |
| v2.0.0 | Unicode 17 tables; optional C extension fast path | 🧭 planned |

Tell us what you want prioritised in [Issues](https://github.com/gitstq/GlyphMetrics/issues).

---

## 📦 Packaging & deployment

GlyphMetrics is pure Python: no compiled artefacts, no platform wheels, no surprises.

```bash
python3 -m pip install --upgrade build
python3 -m build        # -> dist/glyphmetrics-1.0.0.tar.gz and .whl
```

One-shot self check:

```bash
bash scripts/smoke.sh   # unit tests + CLI smoke + table regression
```

| Scenario | Recommended approach |
|----------|---------------------|
| Application / service | `pip install glyphmetrics`, pinned as `glyphmetrics==1.0.0` |
| Air-gapped / embedded | copy the `glyphmetrics/` directory (~60 KB incl. tables) into your tree |
| Docker | `python:3.11-slim` + `pip install --no-cache-dir glyphmetrics`; image delta ≈ 100 KB |
| PyInstaller / single file | no hidden imports needed — the tables are plain `.py` source |

Supported: Windows 10+ · macOS 12+ · Linux · WSL2 · Docker (Python 3.8–3.13)

---

## 🤝 Contributing

Stars ⭐, issues 🐛 and PRs 🔧 are all welcome. Workflow, Angular commit conventions and issue templates live in
[CONTRIBUTING.md](./CONTRIBUTING.md).

Upgrading the Unicode database is three commands:

```bash
python3 tools/build_tables.py --ucd-dir ./ucd --unicode-version 17.0.0
python3 tests/test_core.py
git commit -am "feat: upgrade Unicode tables to 17.0.0"
```

---

## 📄 License

Released under the **[MIT License](./LICENSE)**.

The Unicode tables are generated from the [Unicode Character Database](https://www.unicode.org/Public/UCD/latest/);
redistribution of that data follows Unicode's [Terms of Use](https://www.unicode.org/license.txt).

If GlyphMetrics straightened out even one crooked table for you, a ⭐ would make our day 🙏
