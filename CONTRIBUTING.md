# 🤝 贡献指南 / Contributing

感谢你愿意为 GlyphMetrics 出力！🎉

## 🎯 项目边界（请先确认你的 PR 在范围内）

GlyphMetrics 刻意保持**小而锐利**，以下功能**不在**范围内：

- ❌ 成为终端 UI 框架（那是 rich / textual 的职责）
- ❌ 引入运行时第三方依赖（`dependencies` 必须保持为空）
- ❌ 网络请求（Unicode 数据表已内置，必须离线可用）

符合方向的 PR：宽度策略更准、字形簇算法更贴近 UAX #29、性能优化、文档翻译与小语种版本。

## 🧪 开发流程

```bash
git clone https://github.com/gitstq/GlyphMetrics.git
cd GlyphMetrics

# 安装为可编辑模式（不引入任何依赖）
python3 -m pip install -e .

# 跑测试，必须全绿
python3 tests/test_core.py          # 或：python3 -m unittest discover -s tests
```

新增功能**必须**附单元测试。我们的测试不依赖 pytest，直接用标准库 `unittest`，以保证零依赖也能验证。

## 🔤 提交规范

遵循 Angular 规范：

| 前缀 | 用途 |
|------|------|
| `feat:` | 新增功能 |
| `fix:` | 修复缺陷 |
| `docs:` | 文档更新 |
| `refactor:` | 重构，不改变行为 |
| `perf:` | 性能优化 |
| `test:` | 测试增补 |
| `chore:` | 构建 / 杂项 |

例如：`fix: 修正 VS16 作用于 emoji 基字符时的宽度判定`

## 🗂️ 升级 Unicode 版本

`glyphmetrics/tables.py` 是**生成产物但会被提交**，这样终端用户无需联网：

```bash
curl -O https://www.unicode.org/Public/UCD/latest/ucd/EastAsianWidth.txt
# ...下载其余三份 UCD 文件后：
python3 tools/build_tables.py --ucd-dir ./ucd --unicode-version 17.0.0
python3 tests/test_core.py     # 回归验证
```

提交时请把 build 脚本、tables.py、以及在 README 里提到的 Unicode 版本号**一起更新**。

## 🐛 提 Issue 请附上

1. 操作系统与终端名称（含版本）
2. Python 版本
3. 触发问题的字符串及其**十六进制码位序列**（`glyphmetrics chars "…"` 的输出即可）
4. 期望宽度 vs 实际宽度

码位序列是关键——绝大多数争议最终都要回到 Unicode 标准是怎么定义的。
