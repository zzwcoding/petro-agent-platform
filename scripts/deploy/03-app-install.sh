#!/usr/bin/env bash
# 云上应用安装：代码＋依赖＋systemd 常驻（V2 问一问后端 :8001，真实时钟）。
# 用法（ECS）：bash 03-app-install.sh <git-url-or-本地路径>
set -euo pipefail
REPO="${1:?用法: 03-app-install.sh <git-url-or-本地路径>}"
REF="${REF:-master}"
APP=/opt/petro-agent-platform

echo "== 1/4 代码（冻结点 $REF）"
if [ -d "$APP/.git" ]; then git -C "$APP" fetch --all && git -C "$APP" checkout "$REF" && git -C "$APP" pull --ff-only
else git clone "$REPO" "$APP" && git -C "$APP" checkout "$REF"; fi
cd "$APP"
git log --oneline -1

echo "== 2/4 依赖"
uv sync --frozen

echo "== 3/4 配置与密钥（搬家包解出——不经 git）"
STAGING="${STAGING:-$HOME/deploy-staging}"
tar xzf "$STAGING/config-env.tgz" -C "$APP"

echo "== 4/4 systemd 常驻"
install -m 644 scripts/deploy/petro-v2.service /etc/systemd/system/petro-v2.service
systemctl daemon-reload && systemctl enable --now petro-v2
sleep 3
systemctl --no-pager -l status petro-v2 | head -8
curl -s -o /dev/null -w "GET runs/{id} → HTTP %{http_code}（404=正常，服务已监听）\n" \
  http://127.0.0.1:8001/api/v2/chat/runs/run-nonexistent
