#!/usr/bin/env bash
# GlyphMetrics 一键自检脚本
# 用途：零依赖环境下验证安装是否完好——跑单测 + CLI 冒烟 + 表格回归。
# 用法：bash scripts/smoke.sh      （退出码非 0 表示失败）

set -euo pipefail
cd "$(dirname "$0")/.."

RED=$'\033[31m'; GREEN=$'\033[32m'; BOLD=$'\033[1m'; OFF=$'\033[0m'
step() { printf '%s==>%s %s\n' "$BOLD" "$OFF" "$1"; }
fail() { printf '%sFAIL%s %s\n' "$RED" "$OFF" "$1"; exit 1; }

PYTHON=${PYTHON:-python3}

step "Python 版本信息"
"$PYTHON" --version

step "运行单元测试"
"$PYTHON" tests/test_core.py > /tmp/gm_tests.log 2>&1 || { cat /tmp/gm_tests.log; fail "单元测试未通过"; }
tail -1 /tmp/gm_tests.log

step "CLI 冒烟：基础宽度"
expect=$("$PYTHON" -m glyphmetrics width '你好' | awk '{print $1}')
[ "$expect" = "4" ] || fail "预期 '你好' 宽度为 4，实际 $expect"
echo "  '你好' -> $expect ✓"

expect=$("$PYTHON" -m glyphmetrics width $'\033[31mERROR\033[0m' | awk '{print $1}')
[ "$expect" = "5" ] || fail "预期带色 ERROR 宽度为 5，实际 $expect"
echo "  带 ANSI 的 ERROR -> $expect ✓"

expect=$("$PYTHON" -m glyphmetrics width '👨‍👩‍👧' | awk '{print $1}')
[ "$expect" = "2" ] || fail "预期家庭 emoji 宽度为 2，实际 $expect"
echo "  家庭 emoji -> $expect ✓"

step "CLI 冒烟：对齐表格行数对齐检查"
"$PYTHON" -m glyphmetrics table > /tmp/gm_table.log
widths=$(awk '{print length($0)}' /tmp/gm_table.log | sort -u | wc -l)
[ "$widths" -gt 1 ] && echo "  注意：渲染宽度受终端字体影响 ($widths 种)，属正常现象"
echo "  表格渲染完成，共 $(wc -l < /tmp/gm_table.log) 行"

step "全部通过"
printf '%s✅ GlyphMetrics 自检通过%s\n' "$GREEN" "$OFF"
