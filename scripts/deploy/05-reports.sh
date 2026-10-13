#!/bin/bash
# 评测报告线上展示：eval/results/ V1/V2 冻结基线报告 → 阿里云 ECS 8.163.33.135:/reports/
# 用法：bash scripts/deploy/05-reports.sh
set -e
KEY="$HOME/.ssh/aliyun-fieldforge.pem"
HOST="root@8.163.33.135"
WEB="/opt/petro-agent-platform/web-dist/reports"    # nginx :80 根下
KEEP="/opt/petro-agent-platform/reports-static"     # 正本留存
HERE="$(cd "$(dirname "$0")" && pwd)"               # scripts/deploy/
REPO="$(git -C "$HERE" rev-parse --show-toplevel)"
SITE="$(mktemp -d)"

cp "$REPO/eval/results/V1版本测试报告.html" "$SITE/v1-report.html"
cp "$REPO/eval/results/V2版本测试报告.html" "$SITE/v2-report.html"
cp "$HERE/reports-index.html" "$SITE/index.html"

echo "==== 部署 ===="
ssh -i "$KEY" "$HOST" "mkdir -p $WEB $KEEP"
scp -i "$KEY" -q "$SITE"/* "$HOST:$WEB/"
ssh -i "$KEY" "$HOST" "cp $WEB/* $KEEP/ && echo 正本已存 reports-static"

echo "==== 冒烟 ===="
for p in "" v1-report.html v2-report.html; do
  code=$(curl -s -o /dev/null -w '%{http_code}' "http://8.163.33.135/reports/$p")
  echo "/reports/$p -> $code"
done
echo "入口：http://8.163.33.135/reports/"
