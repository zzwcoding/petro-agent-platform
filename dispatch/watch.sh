#!/usr/bin/env bash
# watch.sh —— dispatch/ 纯只读观看脚本（sdd-flow 双窗口协议配套）
# 用法: bash watch.sh [live|replay]   （默认 live；replay=从头回放全部留痕后退出）
# 纪律: 本脚本只读，任何时刻开关不影响系统；变量一律加 ${} 花括号（全角括号紧邻变量的 UTF-8 坑）。
set -u

BASE="$(cd "$(dirname "$0")" && pwd)"
JOURNAL="${BASE}/journal.jsonl"
MODE="${1:-live}"

format() {
  # 输入一行 journal JSON，输出人类可读一行
  python3 -c '
import json, sys
try:
    d = json.loads(sys.argv[1])
except Exception:
    sys.exit(0)
ts = d.get("ts", "?")[11:19]
frm = d.get("from", "?")
to = d.get("to", "?")
ev = d.get("event", "?")
txt = d.get("text", "")[:120]
print("%s  %8s -> %-8s [%s] %s" % (ts, frm, to, ev, txt))
' "$1"
}

replay() {
  [ -f "${JOURNAL}" ] || { echo "no journal yet: ${JOURNAL}"; exit 0; }
  while IFS= read -r line; do
    format "${line}"
  done < "${JOURNAL}"
}

case "${MODE}" in
  replay) replay ;;
  live)
    replay
    echo "--- watching ${JOURNAL} (Ctrl-C 退出，不影响系统) ---"
    tail -n 0 -f "${JOURNAL}" | while IFS= read -r line; do
      format "${line}"
    done
    ;;
  *) echo "usage: bash watch.sh [live|replay]" >&2; exit 2 ;;
esac
