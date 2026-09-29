#!/usr/bin/env bash
# ci.sh —— petro-ontology CI：三个确定性闸，任一红则非零退出。
# 1. 脚本单测（tools/test_*.py，schema_check 的 AC1–7 单测）
# 2. 出厂集回归（fixture_run：schema_check 对最小域+非法变体 = AC1–7，防判据漂移）
# 3. 语义闸本体（schema_check 对 petro/ 全量；bohai/ 为对齐底稿不闸——增补中的元素过闸后才进 petro/）
# 教学性产物（lessons/朗读关/教学文）不产不查（Owner 2026-09-29：跳过工程体系中的教学步骤）。
set -uo pipefail
cd "$(dirname "$0")"

fail=0
step() {
  echo ""
  echo "=== $1 ==="
  shift
  "$@" || fail=1
}

step "脚本单测（tools/test_*.py）" python3 -m unittest discover -s tools -p 'test_*.py' -v
step "出厂集 fixture_run"        python3 tools/fixture_run.py --require-fixtures
if [ -d petro ] && [ -n "$(ls -A petro 2>/dev/null)" ]; then
  step "语义闸 schema_check petro/" python3 tools/schema_check.py petro
else
  echo ""
  echo "=== 语义闸 schema_check petro/ ==="
  echo "petro/ 为空（七域模型未开建）——跳过，建域后本闸生效"
fi

echo ""
if [ "$fail" -eq 0 ]; then
  echo "CI: 全绿"
else
  echo "CI: 有红"
fi
exit "$fail"
