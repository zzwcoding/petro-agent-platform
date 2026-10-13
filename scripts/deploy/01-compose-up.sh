#!/usr/bin/env bash
# 云上底座：ECS 上起中间件四件（pg/redis/minio/neo4j；langfuse 属 observe profile 按需）。
# 用法：在 ECS 上、仓根目录执行。前置：docker＋docker compose v2 已装。
# ⚠ MinIO 镜像：2025 起 Hub 分发收紧（见 compose.yaml 注）——ECS 用自有镜像：
#   MINIO_IMAGE=registry.cn-<region>.aliyuncs.com/<ns>/minio:<tag> bash 01-compose-up.sh
set -euo pipefail
: "${MINIO_IMAGE:=minio/minio}"

docker compose up -d pg redis neo4j
MINIO_IMAGE="$MINIO_IMAGE" docker compose up -d minio
docker compose ps
echo "== 底座就绪：pg 5433 / redis 6379 / minio 9000 / neo4j 7687（建议安全组只对内网/本机开放）"
