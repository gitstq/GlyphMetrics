<div align="center">

# 🔤 GlyphMetrics

**字素簇感知 · ANSI 感知的终端文本宽度测量库**

[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)](#-快速开始)
[![Unicode](https://img.shields.io/badge/Unicode-16.0.0-orange.svg)](https://www.unicode.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)

🌍 **简体中文** | [繁體中文](./README.zh-TW.md) | [English](./README.en.md)

</div>

---

## 🎉 项目介绍

写终端界面时，你一定被这句话坑过：

> 「明明 `len()` 都一样长，为什么表格的边线歪了？」

因为终端不是按**字符**排版的，而是按**格子（cell）**排版的。而"一个字符占几格"这件事，比你想象的复杂得多：

| 文本 | `len()` | 朴素宽度求和 | 终端实际占格 | 谁在捣乱 |
|------|:---:|:---:|:---:|------|
| `hello` | 5 | 5 | **5** | 岁月静好 |
| `你好` | 2 | 2 | **4** | 中日韩全角字符占 2 格 |
| `\x1b[31mERROR\x1b[0m` | 14 | 12 | **5** | ANSI 颜色转义不可见 |
| `é`（组合形式） | 2 | 2 | **1** | 组合附加符号宽度为 0 |
| `👨‍👩‍👧` | 5 | 8 | **2** | ZWJ 把三个人连成一个字形 |
| `🇩🇪` | 2 | 4 | **2** | 两个区域指示符合成一个国旗 |

**GlyphMetrics 就是来解决这件事的。** 它是一个纯标准库实现的零依赖 Python 库，给出的是**终端真正会占几格**这个答案。

### 🧬 和 wcwidth 有什么不一样？

[wcwidth](https://github.com/jquast/wcwidth) 是该领域被广泛使用的基础库，GlyphMetrics 站在同一套 Unicode 标准之上，但补齐了两件它在设计上不太看重的事：

| 维度 | wcwidth | GlyphMetrics |
|------|---------|--------------|
| 计算粒度 | 逐个码点求和 | **先切分字素簇，再度量整个簇** |
| 家庭 emoji `👨‍👩‍👧` | 6 格（逐码点累加） | **2 格**（一个字形）✅ |
| 国旗 `🇩🇪` | 4 格 | **2 格** ✅ |
| ANSI 转义序列 | 需调用者先自行剥离 | **内建，自动跳过** ✅ |
| 带颜色的对齐/截断 | 需调用者自己确保不切断转义 | **内建 `pad`/`truncate`，且自动补 `\x1b[0m`** ✅ |
| 运行时依赖 | 无 | 无 |
| 附带工具 | 仅有库 | 库 + **可直接使用的 CLI** ✅ |

> 💡 灵感来源：WCWIDTH 的历史包袱主要来自"逐码点"模型。现代终端字体早已支持 ZWJ 表情 Fa 序列与国旗，
> 《Unicode 标准附录 #29》(UAX #29) 也早已给出了完整的字素簇定义——GlyphMetrics 选择按标准来。

---

## ✨ 核心特性

- 🧩 **字素簇优先**：依照 UAX #29 实现 GB3–GB13 规则，家庭 emoji、肤色修饰符、国旗、天城文书、Hangul 拆字都为 renders 为一个整体字形。
- 🎨 **ANSI 全通透**：`\x1b[31m`、`\x1b[38;5;208m`、OSC 超链接等一律按 0 格计算；`str_width` 直接传带色字符串即可，**无需先剥色**。
- ✂️ **安全截断**：`truncate()` 绝不切开字素簇，且会在末尾自动补 `\x1b[0m`，不会让你的终端染上一片红。
- 📏 **真·对齐**：`pad()` / `ljust()` / `rjust()` / `center()` 保留原有颜色，只在可见部分补空格。
- 🇺🇳 **东亚宽度完整支持**：内置 `East_Asian_Width` 全表，并支持可选将 Ambiguous 字符按宽字符处理（`ambiguous_as_wide=True`）。
- 😀 **Unicode 16.0.0**：数据表由官方 UCD 文件生成，ship 代码库内，**离线可用**。
- 🪶 **真正的零依赖**：`dependencies` 字段为空。`python3` 自带的一切就够了。
- ⚡ **性能不妥协**：ASCII 路径走 C 层 `str.translate`；重复测量走 LRU 缓存。见下方[性能基准](#-性能基准)。
- 🖥️ **自带 CLI**：`width` / `clusters` / `pad` / `truncate` / `wrap` / `table` / `demo`，调试排版问题不用写脚本。
- 🧪 **46 个单元测试**：覆盖 emoji ZWJ、国旗、VS15/VS16、keycap、ANSI、CRLF、Hangul 拆字等边界。

---

## 🚀 快速开始

### 环境要求

- Python **3.8 及以上**（用到 `str.isascii()` 与 f-string，均在 3.8 可用）
- 无其他要求——**没有 pip 安装依赖这一步**

### 安装

```bash
# 方式一：pip（推荐）
pip install glyphmetrics

# 方式二：源码直接安装
git clone https://github.com/gitstq/GlyphMetrics.git
cd GlyphMetrics
pip install -e .

# 方式三：零安装——把 glyphmetrics/ 目录拷进你的项目即可
# 这是纯 Python 包，不需要打包元信息就能用
```

### 三行上手

```python
import glyphmetrics as gm

gm.str_width("你好")                    # -> 4   (两个全角汉字)
gm.str_width("\x1b[31mERROR\x1b[0m")    # -> 5   (颜色转义不占格)
gm.str_width("👨‍👩‍👧")                # -> 2   (5 个码点，1 个字形，2 格)
```

### CLI 尝鲜

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

## 📖 详细使用指南

### 🧱 一、基础度量 API

| 函数 | 作用 | 示例 |
|------|------|------|
| `char_width(ch, ...)` | 单个字符的宽度 | `char_width("你")` → `2` |
| `str_width(s, ...)` | 字符串占格数（含 ANSI 处理） | `str_width("你好")` → `4` |
| `graphemes(s)` | 返回字素簇列表 | `graphemes("👨‍👩‍👧")` → `['👨‍👩‍👧']` |
| `grapheme_len(s)` | 用户感知字符数（≠ `len()`） | `grapheme_len("👨‍👩‍👧")` → `1` |
| `iter_graphemes(s)` | 惰性产出 `(start, end)` 切片 | 用于手写分词逻辑 |

```python
gm.char_width("α")                        # 1（Ambiguous 默认窄）
gm.char_width("α", ambiguous_as_wide=True)  # 2（可切换为宽）
gm.str_width("αβγ", ambiguous_as_wide=True) # 6
gm.grapheme_len("é")                      # 1 —— 即使写成 'e' + U+0301 的组合形式
```

### 🎨 二、ANSI 处理

```python
STR = "\x1b]8;;https://example.com\x07点击这里\x1b]8;;\x07"

gm.strip_ansi(STR)          # '点击这里'          —— 剥色
gm.has_ansi(STR)            # True                —— 是否含转义
gm.str_width(STR)           # 8                   —— 超链接标记不计宽
```

⚠️ **注意**：制表符 `\t` 在 GlyphMetrics 中计为 **0 格**（它是控制字符）。如需 4/8 格的视觉效果，请先调用 `str.expandtabs(4)`。

### 📐 三、排版 API（对齐、截断、折行）

```python
# 对齐 —— 会保留原有颜色
gm.pad("\x1b[31mAB\x1b[0m", 6)   # '\x1b[31mAB\x1b[0m    '
gm.strip_ansi(gm.pad("\x1b[31mAB\x1b[0m", 6))   # 'AB    '

gm.rjust("价格", 10)              # '        价格'
gm.center("状态", 10, fill="─")   # '───状态───'

# 截断 —— 绝不切开字素簇，并自动补复位序列
gm.truncate("你好世界", 4)                       # '你…'   （1 格给省略号，剩 3 格只够一个全角字）
gm.truncate("\x1b[31mHello World\x1b[0m", 5)     # '\x1b[31mHell…\x1b[0m'
gm.truncate_front("/very/long/path/file.txt", 12)  # '…th/file.txt'（保留尾部）

# 折行
gm.wrap("中华人民共和国万岁世界人民大团结万岁", 8)
# -> ['中华人民', '共和国万', '岁世界人', '民大团结', '万岁']
#    每行严格 8 格（末行除外），且不会把汉字切成半个
```

### 🖥️ 四、CLI 命令一览

| 命令 | 说明 | 示例 |
|------|------|------|
| `width` / `w` | 测量宽度 | `glyphmetrics width '你好'` |
| `chars` | 逐字符 / 逐簇明细 | `glyphmetrics chars '👍🏽'` |
| `clusters` / `c` | 列出字素簇 | `glyphmetrics clusters '👨‍👩‍👧'` |
| `pad` | 对齐到指定宽度 | `glyphmetrics pad '标题' -w 20 -a center` |
| `truncate` / `t` | 截断 | `glyphmetrics t '很长的文本' -w 10` |
| `strip` | 剥离 ANSI | `glyphmetrics strip "$(printf '\033[31mx\033[0m')"` |
| `wrap` | 折行 | `glyphmetrics wrap '日语→顔文字(˘ω˘)ｽﾔｧ…' -w 16` |
| `table` | 渲染混排对齐表格（含中文/韩文/emoji） | `glyphmetrics table` |
| `demo` | 对比 `len()` 与真实格数 | `glyphmetrics demo` |
| `version` | 版本与 Unicode 版本 | `glyphmetrics version` |

`width` 与 `clusters` 支持 `--json`，方便管道处理：

```bash
$ glyphmetrics width '你好' --json
{"width": 4, "codepoints": 2, "graphemes": 2}
```

### 🎛️ 五、把 GlyphMetrics 接进你的 TUI

最小示例：一个永不歪斜的表格。

```python
import glyphmetrics as gm

rows = [("中国", "简体中文"), ("Deutschland", "Deutsch"), ("Flag", "🇩🇪 🇯🇵")]
w = [max(gm.str_width(r[i]) for r in rows) + 2 for i in range(2)]

for a, b in rows:
    print("|" + gm.pad(" " + a, w[0]) + "|" + gm.pad(" " + b, w[1]) + "|")
```

进阶用例见 docs 中的 [docs/USAGE.zh-CN.md](./docs/USAGE.zh-CN.md)（含日志对齐、进度条、进度百分比右侧对齐三个真实场景）。

---

## ⚡ 性能基准

测试环境：Python 3.11，文本长度约 **7,200 码点**，`wcwidth` 版本 0.5.3 作为参照。

| 场景 | GlyphMetrics | wcwidth | 结论 |
|------|-------------:|--------:|------|
| 纯拉丁文本（冷调用） | **4.6 µs** | 9.7 µs | 🏆 快 **2.1×**（走 `str.translate` 快速路径） |
| 混合中日韩/emoji（冷调用） | 5,021 µs | **982 µs** | 慢约 5×（代价来自字素簇切分） |
| 混合中日韩/emoji（重复调用） | **147 µs** | 991 µs | 🏆 快 **6.8×**（LRU 缓存命中） |

> 📌 **怎么选**：终端 UI 会反复重绘同样的标题、表头、单元格内容——这正是 GlyphMetrics 缓存命中率最高的场景。
> 若你的场景是"每次都是全新巨型字符串"，且确认不含 emoji ZWJ 序列，wcwidth 仍然更快——这也是我们诚实标注的原因。

---

## 🔬 与 wcwidth 的差异明细

我们遍历了 **1,112,032 个码点**逐个比对，共 **4,566 处（0.41%）** 不同。每一类都是**有意为之**，列举如下以免争议：

| 差异类型 | 数量 | 代表字符 | GlyphMetrics 的判定依据 |
|----------|-----:|----------|--------------------------|
| wcwidth 0 → GM 1 | 4,357 | 天城文元音符号 `U+093E` 等 SpacingMark (Mc) | UAX #11 未将其归为零宽；`rich` 等现代库同样判为 1 格 |
| wcwidth 2 → GM 1 | 157 | `U+16FF2`、`U+187F8`、`U+1FAEF` | 这些码点在 **Unicode 16.0** 中尚未分配，属版本差异 |
| wcwidth -1 → GM 0 | 33 | C1 控制字符 `U+007F`–`U+009F` | 控制字符返回 0 可避免污染累计宽度（可用 `control_width` 调整） |
| wcwidth 1 → GM 0 | 14 | 软连字符 `U+00AD`、阿拉伯数字标 `U+0600` | 它们属 `Cf` 格式字符，终端不渲染 |
| wcwidth 0 → GM 2 | 5 | Hangul 声调符 `U+302E`/`U+302F` | 依 `East_Asian_Width=W` 判定为全角 |

> 🧭 争议时以 Unicode 官方数据文件为准：`glyphmetrics chars "字符"` 会打印该字符的判定与 Unicode 名称，
> 而 [tools/build_tables.py](./tools/build_tables.py) 完整记录了每一张表的推导过程。

---

## 💡 设计思路与迭代规划

### 🏗️ 设计理念

1. **标准优先，不做经验主义的拼接。** 所有宽度和簇边界都来自 UCD 官方数据文件，而不是"看某个终端好像这样"的主观判断。生成器脚本公开可复现。
2. **表格内置 > 运行时计算。** 用 8 张区间表（约 30 KB）换取零运行时依赖和纯二分查找——这也是离线环境能跑通的前提。
3. **绝不破坏调用者的字符串。** `pad` 返回的仍是带色的原串；`truncate` 会自动补 `\x1b[0m`；真正的"所见阁数"与"原始内容"解耦。
4. **快路径是设计的一部分。** ASCII 走 `str.translate`，无组合符号的低位文本走缓存求和，重复测量走 LRU——从一开始就写了三层拥堵缓。

### 🗺️ 迭代规划

| 版本 | 计划内容 | 状态 |
|------|---------|------|
| v1.0.0 | 核心度量 / 簇切分 / ANSI / 排版 / CLI / 三语文档 | ✅ 已发布 |
| v1.1.0 | `wrap()` 支持 UAX #14 断行机会（LB 规则）；`break_words=False` 时不硬切长词 | 🔜 规划中 |
| v1.2.0 | 派生区间表进一步压缩（≤ 15 KB），并支持 `--no-emoji-wide` 策略开关 | 🧭 调研中 |
| v2.0.0 | Unicode 17 数据表；可选 C 扩展加速路径 | 🧭 规划中 |

欢迎在 [Issues](https://github.com/gitstq/GlyphMetrics/issues) 提出你希望优先的方向。

---

## 📦 打包与部署指南

GlyphMetrics 是**纯 Python 库**，无需编译产物，跨平台。

### 本地打包

```bash
python3 -m pip install --upgrade build
python3 -m build          # 产出 dist/glyphmetrics-1.0.0.tar.gz 与 .whl
```

### 一键自检

```bash
bash scripts/smoke.sh     # 单测 + CLI 冒烟 + 表格回归
```

### 集成方式

| 场景 | 推荐做法 |
|------|---------|
| 应用 / 服务 | `pip install glyphmetrics`，或直接钉版 `glyphmetrics==1.0.0` |
| 嵌入式 / 内网 | 把 `glyphmetrics/` 包目录拷入项目（约 60 KB，含数据表） |
| Docker | `python:3.11-slim` + `pip install --no-cache-dir glyphmetrics`，镜像增量约 100 KB |
| PyInstaller / 单文件 | 无需额外 hidden import；数据表是 `.py` 源码，会被正常打包 |

### 支持的运行环境

Windows 10+ · macOS 12+ · Linux · WSL2 · Docker（Python 3.8–3.13）

---

## 🤝 贡献指南

欢迎 Star ⭐、Issue 🐛 与 PR 🔧！流程、提交规范（Angular 规范）与 Issue 模板见 [CONTRIBUTING.md](./CONTRIBUTING.md)。

新增 Unicode 版本只需三步：

```bash
python3 tools/build_tables.py --ucd-dir ./ucd --unicode-version 17.0.0
python3 tests/test_core.py
git add glyphmetrics/tables.py && git commit -m "feat: 升级 Unicode 数据表至 17.0.0"
```

---

## 📄 开源协议

本项目基于 **[MIT License](./LICENSE)** 开源。

Unicode 数据表由 [Unicode Character Database](https://www.unicode.org/Public/UCD/latest/) 生成，
数据的再分发遵循 Unicode 的 [Terms of Use](https://www.unicode.org/license.txt)。

若 GlyphMetrics 让终端界面对齐工整了一点点，点个 ⭐ 就是对我们最大的肯定 🙏
