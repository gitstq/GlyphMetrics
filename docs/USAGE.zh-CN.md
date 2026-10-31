# 📖 GlyphMetrics 实战用法（简体中文）

[返回 README](../README.md)

这一页放的是**可以抄走的真实场景**，而不是 API 罗列。所有代码都可以直接运行，依赖只有 GlyphMetrics。

---

## 🪵 场景一：日志级别永不歪斜

**痛点**：日志里 `INFO` / `WARNING` / `CRITICAL` 长度不同，`INFO` 后面跟一段中文，
用 `str.ljust(8)` 排版后面对齐全乱（因为 `ljust` 按码点数补空格，而一个汉字占 2 格）。

```python
import time
import glyphmetrics as gm

LEVELS = [
    ("INFO",     "\x1b[36m", "服务启动完成"),
    ("WARNING",  "\x1b[33m", "磁盘剩余空间不足"),
    ("CRITICAL", "\x1b[31m", "主数据库连接中断，正在重连"),
    ("DEBUG",    "\x1b[90m", "cache hit ratio = 96.4%"),
]
RESET = "\x1b[0m"
LEVEL_W = 10   # 级别列固定 10 格

for level, color, msg in LEVELS:
    ts = time.strftime("%H:%M:%S")
    print(f"{color}{gm.pad(level, LEVEL_W)}{RESET}{ts}  {msg}")
```

输出效果（`级别列`严格 10 格，颜色完好保留）：

```
INFO      00:01:02  服务启动完成
WARNING   00:01:02  磁盘剩余空间不足
CRITICAL  00:01:02  主数据库连接中断，正在重连
DEBUG     00:01:02  cache hit ratio = 96.4%
```

> ✅ 关键点：`gm.pad(level, 10)` 补空格时按**可见格数**计算，
> 所以即便消息里全是汉字，也不会把后面的时间戳推歪。

---

## 📊 场景二：终端表格，中日韩 emoji 混排也不崩

**痛点**：`format` 的对齐宽度按码点数算，中文/emoji 一进场就全线错位。

```python
import glyphmetrics as gm

HEADER = ("城市", "语言", "问候语", "占格")
ROWS = [
    ("中国北京", "简体中文", "你好，世界", ""),
    ("中國香港", "繁體中文", "香港，台灣", ""),
    ("日本東京", "日本語", "こんにちは", ""),
    ("대한민국", "한국어", "안녕하세요", ""),
    ("España",  "Español", "Gracias 👋", ""),
    ("Flag",    "Regional", "🇩🇪 🇯🇵 🇺🇸", ""),
]

# 第 4 列自动填上第 3 列的真实占格数
table = [HEADER] + [(a, b, c, str(gm.str_width(c))) for a, b, c, _ in ROWS]

widths = [max(gm.str_width(r[i]) for r in table) + 2 for i in range(4)]
rule = "+" + "+".join("-" * w for w in widths) + "+"

print(rule)
print("|" + "|".join(gm.pad(" " + c, widths[i]) for i, c in enumerate(HEADER)) + "|")
print(rule)
for row in table[1:]:
    print("|" + "|".join(gm.pad(" " + c, widths[i]) for i, c in enumerate(row)) + "|")
print(rule)
```

CLI 里内置了同样的演示：

```bash
glyphmetrics table
```

> ✅ 关键点：用 `gm.str_width` 算列宽、用 `gm.pad` 填充，两者配合才能保证
> 「数字怎么快，看到的就怎么宽」。

---

## 🎯 场景三：进度条 + 右侧百分比

**痛点**：要在终端右边缘显示 ` 42%`，需要知道左边内容占了几格，代码一般是错的。

```python
import sys
import glyphmetrics as gm

def progress(label, percent, total=40):
    filled = int(total * percent / 100)
    bar = "█" * filled + "░" * (total - filled)
    right = f" {percent:>3}%"
    cols_left = 60 - gm.str_width(label) - gm.str_width(bar) - gm.str_width(right)
    pad = " " * max(cols_left, 1)
    sys.stdout.write(f"\r{label} {bar}{pad}{right}")
    sys.stdout.flush()

for p in range(0, 101, 20):
    progress("处理「日本語テキスト」", p)
print()
progress("处理『한국어 텍스트』", 100)
print()
```

> ✅ 关键点：`░`/`█`(U+2593/U+2588) 这类制表符属 Ambiguous 宽度，
> 默认按 1 格处理；若你的终端把它们渲染成 2 格，加 `ambiguous_as_wide=True` 即可对齐。

---

## ✂️ 场景四：长路径的安全省略

```python
import glyphmetrics as gm

def elide(path, avail):
    """按可用格数省略路径，优先保留文件名。"""
    if gm.str_width(path) <= avail:
        return path
    return gm.truncate_front(path, avail)

for avail in (10, 16, 24):
    print(f"{avail:>2} 格 -> {elide('/usr/local/lib/python3.11/site-packages/glyphmetrics/tables.py', avail)}")
```

```text
10 格 -> …tables.py
16 格 -> …trics/tables.py
24 格 -> …/glyphmetrics/tables.py
```

> ✅ 关键点：`truncate_front` 从**头部**省略，保留最有信息量的尾部文件名，
> 这正是日志与路径展示最常见的需求。

---

## 🧪 场景五：在测试里断言「不会断20就会歪」

把排布约束写进单测，比事后截图检查可靠得多。

```python
import unittest
import glyphmetrics as gm

class LayoutTests(unittest.TestCase):
    def test_every_padded_row_has_same_visible_width(self):
        rows = ["INFO", "WARNING", "CRITICAL", "错误", "デバッグ"]
        widths = {gm.str_width(gm.pad(r, 12)) for r in rows}
        self.assertEqual(widths, {12})

    def test_truncate_never_exceeds_budget(self):
        samples = ["你好世界", "👨‍👩‍👧👨‍👩‍👧", "Grüße aus München", "\x1b[31mRED\x1b[0m"]
        for s in samples:
            for w in range(1, 12):
                self.assertLessEqual(gm.str_width(gm.truncate(s, w)), w)

if __name__ == "__main__":
    unittest.main()
```

---

## 🔧 排错手册

| 现象 | 原因 | 解决办法 |
|------|------|---------|
| 表格差 1 格 | 破折号 `—`(U+2014) 等 Ambiguous 字符 | 统一加 `ambiguous_as_wide=True`，或先从数据里替换掉 |
| 含 `\t` 的行算不准 | 制表符被当作控制字符（0 格） | 度量前先 `s.expandtabs(4)` |
| emoji 后面多了一小段乱码 | ZWJ 序列被按码点切断了 | 用本库的 `truncate` / `wrap`，别用 Python 原生切片 |
| 颜色"传染"到后续输出 | ANSI 状态没复位 | `truncate` 会自动补 `\x1b[0m`；手动拼接时记得自己补 |
