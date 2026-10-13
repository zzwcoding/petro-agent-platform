#!/bin/bash
# 语义数据看板部署：git 仓 docs/本体应用讲解/ → 阿里云 ECS 8.163.33.135:/onto/
# 用法：bash docs/本体应用讲解/deploy/build.sh
set -e
SRC="$(cd "$(dirname "$0")/.." && pwd)"          # docs/本体应用讲解/
DST="/tmp/onto-deploy/site"
KEY="$HOME/.ssh/aliyun-fieldforge.pem"
HOST="root@8.163.33.135"
WEB="/opt/petro-agent-platform/web-dist/onto"    # nginx :80 根下
KEEP="/opt/petro-agent-platform/onto-static"     # 正本留存

mkdir -p "$DST"
cp "$SRC/语义数据看板.html"            "$DST/canvas.html"
cp "$SRC/本体方法论·概念与应用要点手册.md" "$DST/xiangmu.md"
cp "$SRC/本体方法论·概念与应用要点手册.md" "$DST/zhishi.md"   # 索引页兼容入口
cp "$SRC/本体建模规格书·渤海油田示例.md"   "$DST/dizuo.md"
cp "$(dirname "$0")/index.html"       "$DST/index.html"

echo "==== 评测报告（V1/V2 冻结基线，随本体展示一并发布） ===="
REPO="$(git -C "$SRC" rev-parse --show-toplevel)"
cp "$REPO/eval/results/V1版本测试报告.html" "$DST/v1-report.html"
cp "$REPO/eval/results/V2版本测试报告.html" "$DST/v2-report.html"

echo "==== 渲染手册网页 ===="
cd "$(git -C "$SRC" rev-parse --show-toplevel)"
SITE_DIR="$DST" uv run --with markdown python3 "$SRC/deploy/render.py"

echo "==== 部署 ===="
ssh -i "$KEY" "$HOST" "mkdir -p $WEB $KEEP"
scp -i "$KEY" -q "$DST"/* "$HOST:$WEB/"
ssh -i "$KEY" "$HOST" "cp $WEB/* $KEEP/ && echo 正本已存 onto-static"
echo "==== 冒烟 ===="
for p in "" canvas.html jiangjie.html xiangmu.md dizuo.md v1-report.html v2-report.html; do
  code=$(curl -s -o /dev/null -w '%{http_code}' "http://8.163.33.135/onto/$p")
  echo "/onto/$p -> $code"
done
echo "入口：http://8.163.33.135/onto/"
