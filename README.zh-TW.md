<div align="center">

# 🔤 GlyphMetrics

**字素簇感知 · ANSI 感知的終端文字寬度測量函式庫**

[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)](#-快速開始)
[![Unicode](https://img.shields.io/badge/Unicode-16.0.0-orange.svg)](https://www.unicode.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)

[简体中文](./README.md) | 🌍 **繁體中文** | [English](./README.en.md)

</div>

---

## 🎉 專案介紹

寫終端機介面時，你一定被這句話坑過：

> 「明明 `len()` 都一樣長，為什麼表格的框線歪了？」

因為終端機不是按**字元**排版的，而是按**格子（cell）**排版的。而「一個字元佔幾格」這件事，比你想的複雜得多：

| 文字 | `len()` | 樸素寬度加總 | 終端機實際佔格 | 誰在搗蛋 |
|------|:---:|:---:|:---:|------|
| `hello` | 5 | 5 | **5** | 歲月靜好 |
| `你好` | 2 | 2 | **4** | 中日韓全形字佔 2 格 |
| `\x1b[31mERROR\x1b[0m` | 14 | 12 | **5** | ANSI 顏色跳脫序列不可見 |
| `é`（組合形式） | 2 | 2 | **1** | 組合附加符號寬度為 0 |
| `👨‍👩‍👧` | 5 | 8 | **2** | ZWJ 把三個人連成一個字形 |
| `🇩🇪` | 2 | 4 | **2** | 兩個區域指示符合成一張國旗 |

**GlyphMetrics 就是要解決這件事。** 它以純標準函式庫實作、零相依，
給出的是**終端機真正會佔幾格**這個答案。

### 🧬 和 wcwidth 有什麼不一樣？

[wcwidth](https://github.com/jquast/wcwidth) 是這個領域被廣泛使用的基礎函式庫。
GlyphMetrics 站在同一套 Unicode 標準之上，但補上了兩件它在設計上不太看重的東西：

| 面向 | wcwidth | GlyphMetrics |
|------|---------|--------------|
| 計算粒度 | 逐個碼位加總 | **先切分字素簇，再度量整個簇** |
| 家庭 emoji `👨‍👩‍👧` | 6 格（逐碼位累加） | **2 格**（一個字形）✅ |
| 國旗 `🇩🇪` | 4 格 | **2 格** ✅ |
| ANSI 跳脫序列 | 需呼叫端自行剝離 | **內建，自動跳過** ✅ |
| 帶顏色的對齊/截斷 | 需呼叫端自己確保不切斷跳脫序列 | **內建 `pad`/`truncate`，且自動補 `\x1b[0m`** ✅ |
| 執行期相依套件 | 無 | 無 |
| 隨附工具 | 僅有函式庫 | 函式庫 + **可直接使用的 CLI** ✅ |

> 💡 靈感來源：wcwidth 的歷史包袱主要來自「逐碼位」模型。現代終端機字型早已支援 ZWJ 表情序列與國旗，
> 《Unicode 標準附錄 #29》(UAX #29) 也早已給出完整的字素簇定義——GlyphMetrics 選擇照標準來。

---

## ✨ 核心特色

- 🧩 **字素簇優先**：依循 UAX #29 實作 GB3–GB13 規則，家庭 emoji、膚色修飾符、國旗、天城文書、Hangul 拆字都視為一個整體字形。
- 🎨 **ANSI 全通透**：`\x1b[31m`、`\x1b[38;5;208m`、OSC 超連結等一律按 0 格計算；`str_width` 直接傳帶色字串即可，**不必先剝色**。
- ✂️ **安全截斷**：`truncate()` 絕不切開字素簇，且會在結尾自動補 `\x1b[0m`，不會讓你的終端機染上一片紅。
- 📏 **真·對齊**：`pad()` / `ljust()` / `rjust()` / `center()` 保留原有顏色，只在可見部分補空白。
- 🇺🇳 **東亞寬度完整支援**：內建 `East_Asian_Width` 全表，並可選將 Ambiguous 字元按寬字元處理（`ambiguous_as_wide=True`）。
- 😀 **Unicode 16.0.0**：資料表由官方 UCD 檔案產生，隨程式碼一併發佈，**完全離線可用**。
- 🪶 **真正的零相依**：`dependencies` 欄位是空的。`python3` 自帶的一切就夠了。
- ⚡ **效能不妥協**：ASCII 路徑走 C 層級的 `str.translate`；重複測量走 LRU 快取。見下方[效能基準](#-效能基準)。
- 🖥️ **自帶 CLI**：`width` / `clusters` / `pad` / `truncate` / `wrap` / `table` / `demo`，除錯排版問題不用另外寫指令稿。
- 🧪 **46 個單元測試**：涵蓋 emoji ZWJ、國旗、VS15/VS16、keycap、ANSI、CRLF、Hangul 拆字等邊界。

---

## 🚀 快速開始

### 環境需求

- Python **3.8 以上**（用到 `str.isascii()` 與 f-string，3.8 均已支援）
- 沒有其他需求——**不存在安裝相依套件這一步**

```bash
# 方式一：pip（推薦）
pip install glyphmetrics

# 方式二：由原始碼安裝
git clone https://github.com/gitstq/GlyphMetrics.git
cd GlyphMetrics
pip install -e .

# 方式三：完全不安裝——把 glyphmetrics/ 目錄複製進你的專案即可
# 這是純 Python 套件，不需要封裝元資訊就能用
```

### 三行上手

```python
import glyphmetrics as gm

gm.str_width("你好")                    # -> 4   （兩個全形漢字）
gm.str_width("\x1b[31mERROR\x1b[0m")    # -> 5   （顏色跳脫碼不佔格）
gm.str_width("👨‍👩‍👧")                # -> 2   （5 個碼位，1 個字形，2 格）
```

### CLI 試用

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

## 📖 詳細使用指南

### 🧱 一、基礎度量 API

| 函式 | 作用 | 範例 |
|------|------|------|
| `char_width(ch, ...)` | 單一字元寬度 | `char_width("你")` → `2` |
| `str_width(s, ...)` | 字串佔格數（含 ANSI 處理） | `str_width("你好")` → `4` |
| `graphemes(s)` | 回傳字素簇清單 | `graphemes("👨‍👩‍👧")` → `['👨‍👩‍👧']` |
| `grapheme_len(s)` | 使用者感知字元數（≠ `len()`） | `grapheme_len("👨‍👩‍👧")` → `1` |
| `iter_graphemes(s)` | 惰性產出 `(start, end)` 切片 | 用於自訂切分邏輯 |

```python
gm.char_width("α")                          # 1（Ambiguous 預設窄）
gm.char_width("α", ambiguous_as_wide=True)   # 2（可切換為寬）
gm.str_width("αβγ", ambiguous_as_wide=True)  # 6
gm.grapheme_len("é")                        # 1 —— 即使寫成 'e' + U+0301 的組合形式
```

### 🎨 二、ANSI 處理

```python
LINK = "\x1b]8;;https://example.com\x07點我\x1b]8;;\x07"

gm.strip_ansi(LINK)     # '點我'      —— 剝色
gm.has_ansi(LINK)       # True        —— 是否含跳脫序列
gm.str_width(LINK)      # 4           —— 超連結標記不計寬
```

⚠️ **注意**：定位字元 `\t` 在 GlyphMetrics 中計為 **0 格**（它是控制字元）。
若需要 4/8 格的視覺效果，請先呼叫 `str.expandtabs(4)`。

### 📐 三、排版 API（對齊、截斷、折行）

```python
# 對齊 —— 會保留原有顏色
gm.pad("\x1b[31mAB\x1b[0m", 6)                  # '\x1b[31mAB\x1b[0m    '
gm.strip_ansi(gm.pad("\x1b[31mAB\x1b[0m", 6))   # 'AB    '
gm.rjust("價格", 10)                             # '        價格'
gm.center("狀態", 10, fill="─")                  # '───狀態───'

# 截斷 —— 絕不切開字素簇，並自動補復位序列
gm.truncate("你好世界", 4)                        # '你…'
gm.truncate("\x1b[31mHello World\x1b[0m", 5)      # '\x1b[31mHell…\x1b[0m'
gm.truncate_front("/very/long/path/file.txt", 12)  # '…th/file.txt'（保留尾部）

# 折行
gm.wrap("中华人民共和国万岁世界人民大团结万岁", 8)
# -> ['中华人民', '共和国万', '岁世界人', '民大团结', '万岁']
#    每行嚴格 8 格（末行除外），且不會把漢字切成半個
```

### 🖥️ 四、CLI 指令一覽

| 指令 | 說明 | 範例 |
|------|------|------|
| `width` / `w` | 測量寬度 | `glyphmetrics width '你好'` |
| `chars` | 逐字元 / 逐簇明細 | `glyphmetrics chars '👍🏽'` |
| `clusters` / `c` | 列出字素簇 | `glyphmetrics clusters '👨‍👩‍👧'` |
| `pad` | 對齊到指定寬度 | `glyphmetrics pad '標題' -w 20 -a center` |
| `truncate` / `t` | 截斷 | `glyphmetrics t '很長的一段文字' -w 10` |
| `strip` | 剝離 ANSI | `glyphmetrics strip "$(printf '\033[31mx\033[0m')"` |
| `wrap` | 折行 | `glyphmetrics wrap '顔文字(˘ω˘)ｽﾔｧ…' -w 16` |
| `table` | 渲染混排對齊表格（含中文/韓文/emoji） | `glyphmetrics table` |
| `demo` | 比較 `len()` 與真實格數 | `glyphmetrics demo` |
| `version` | 版本與 Unicode 版本 | `glyphmetrics version` |

`width` 與 `clusters` 支援 `--json`，方便管線處理：

```bash
$ glyphmetrics width '你好' --json
{"width": 4, "codepoints": 2, "graphemes": 2}
```

### 🎛️ 五、把 GlyphMetrics 接進你的 TUI

最小範例：一個永不歪斜的表格。

```python
import glyphmetrics as gm

rows = [("中國", "简体中文"), ("Deutschland", "Deutsch"), ("Flag", "🇩🇪 🇯🇵")]
w = [max(gm.str_width(r[i]) for r in rows) + 2 for i in range(2)]

for a, b in rows:
    print("|" + gm.pad(" " + a, w[0]) + "|" + gm.pad(" " + b, w[1]) + "|")
```

進階情境（日誌對齊、進度條、路徑省略、把排版約束寫進測試）
請見 [docs/USAGE.zh-CN.md](./docs/USAGE.zh-CN.md)。

---

## ⚡ 效能基準

測試環境：Python 3.11，文字長度約 **7,200 個碼位**，以 `wcwidth` 0.5.3 作為對照。

| 情境 | GlyphMetrics | wcwidth | 結論 |
|------|-------------:|--------:|------|
| 純拉丁文字（冷啟動） | **4.6 µs** | 9.7 µs | 🏆 快 **2.1×**（走 `str.translate` 快速路徑） |
| 混合中日韓/emoji（冷啟動） | 5,021 µs | **982 µs** | 慢約 5×（代價來自字素簇切分） |
| 混合中日韓/emoji（重複呼叫） | **147 µs** | 991 µs | 🏆 快 **6.8×**（LRU 快取命中） |

> 📌 **怎麼選**：終端機 UI 會反覆重繪同樣的標題、表頭、儲存格內容——這正是 GlyphMetrics 快取命中率最高的情境。
> 若你的情境是「每次都是全新的巨型字串」，且確認不含 emoji ZWJ 序列，wcwidth 仍然更快——這也是我們誠實標註的原因。

---

## 🔬 與 wcwidth 的差異明細

我們遍歷了 **1,112,032 個碼位**逐個比對，共 **4,566 處（0.41%）** 不同。
每一類都是**刻意為之**，列舉如下以免爭議：

| 差異類型 | 數量 | 代表字元 | GlyphMetrics 的判定依據 |
|----------|-----:|----------|--------------------------|
| wcwidth 0 → GM 1 | 4,357 | 天城文母音符號 `U+093E` 等 SpacingMark (Mc) | UAX #11 未將其歸為零寬；`rich` 等現代函式庫同樣判為 1 格 |
| wcwidth 2 → GM 1 | 157 | `U+16FF2`、`U+187F8`、`U+1FAEF` | 這些碼位在 **Unicode 16.0** 中尚未指派，屬版本差異 |
| wcwidth -1 → GM 0 | 33 | C1 控制字元 `U+007F`–`U+009F` | 控制字元回傳 0 可避免污染累積寬度（可用 `control_width` 調整） |
| wcwidth 1 → GM 0 | 14 | 軟連字號 `U+00AD`、阿拉伯數字標記 `U+0600` | 它們屬 `Cf` 格式字元，終端機不渲染 |
| wcwidth 0 → GM 2 | 5 | Hangul 聲調符號 `U+302E` / `U+302F` | 依其 `East_Asian_Width=W` 判定為全形 |

> 🧭 有爭議時以 Unicode 官方資料檔為準：`glyphmetrics chars "字元"` 會印出判定結果與 Unicode 名稱，
> 而 [tools/build_tables.py](./tools/build_tables.py) 完整記錄了每一張表的推導過程。

---

## 💡 設計思路與迭代規劃

### 🏗️ 設計理念

1. **標準優先，不做經驗主義的拼接。** 所有寬度與簇邊界都來自 UCD 官方資料檔，而不是「看某個終端機好像這樣」的主觀判斷。產生器指令稿公開可重現。
2. **隨附表格 > 執行期計算。** 用 8 張區間表（約 30 KB）換取零執行期相依與純二元搜尋——這也是離線環境能跑通的前提。
3. **絕不破壞呼叫端的字串。** `pad` 回傳的仍是帶色的原串；`truncate` 會自動補 `\x1b[0m`；真正的「所見格數」與「原始內容」解耦。
4. **快速路徑是設計的一部分。** ASCII 走 `str.translate`，無組合符號的低位文字走快取加總，重複測量走 LRU——從一開始就寫了三層擁塞緩衝。

### 🗺️ 迭代規劃

| 版本 | 計畫內容 | 狀態 |
|------|---------|------|
| v1.0.0 | 核心度量 / 簇切分 / ANSI / 排版 / CLI / 三語文件 | ✅ 已發布 |
| v1.1.0 | `wrap()` 支援 UAX #14 斷行機會（LB 規則）；`break_words=False` 時不硬切長詞 | 🔜 規劃中 |
| v1.2.0 | 衍生區間表進一步壓縮（≤ 15 KB），並支援 `--no-emoji-wide` 策略開關 | 🧭 研究中 |
| v2.0.0 | Unicode 17 資料表；可選 C 擴充加速路徑 | 🧭 規劃中 |

歡迎在 [Issues](https://github.com/gitstq/GlyphMetrics/issues) 提出你希望優先的方向。

---

## 📦 打包與部署指南

GlyphMetrics 是**純 Python 函式庫**，無需編譯產物，跨平台。

```bash
python3 -m pip install --upgrade build
python3 -m build          # 產出 dist/glyphmetrics-1.0.0.tar.gz 與 .whl
```

一鍵自檢：

```bash
bash scripts/smoke.sh     # 單元測試 + CLI 冒煙 + 表格回歸
```

| 情境 | 建議做法 |
|------|---------|
| 應用程式 / 服務 | `pip install glyphmetrics`，或直接釘版 `glyphmetrics==1.0.0` |
| 嵌入式 / 內網 | 把 `glyphmetrics/` 套件目錄複製進專案（約 60 KB，含資料表） |
| Docker | `python:3.11-slim` + `pip install --no-cache-dir glyphmetrics`，映像增量約 100 KB |
| PyInstaller / 單檔封裝 | 無需額外 hidden import；資料表是 `.py` 原始碼，會被正常打包 |

支援環境：Windows 10+ · macOS 12+ · Linux · WSL2 · Docker（Python 3.8–3.13）

---

## 🤝 貢獻指南

歡迎 Star ⭐、Issue 🐛 與 PR 🔧！流程、提交規範（Angular 規範）與 Issue 範本見 [CONTRIBUTING.md](./CONTRIBUTING.md)。

升級 Unicode 版本只需三步：

```bash
python3 tools/build_tables.py --ucd-dir ./ucd --unicode-version 17.0.0
python3 tests/test_core.py
git commit -am "feat: 升級 Unicode 資料表至 17.0.0"
```

---

## 📄 開源授權

本專案以 **[MIT License](./LICENSE)** 開源。

Unicode 資料表由 [Unicode Character Database](https://www.unicode.org/Public/UCD/latest/) 產生，
資料再散佈遵循 Unicode 的 [Terms of Use](https://www.unicode.org/license.txt)。

若 GlyphMetrics 讓你的終端機畫面對齊工整了一點點，點個 ⭐ 就是我們最大的肯定 🙏
