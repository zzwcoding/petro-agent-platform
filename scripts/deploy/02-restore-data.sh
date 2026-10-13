#!/usr/bin/env bash
# 云上恢复数据—— faithful 本地态。前置：01 底座已起、搬家包已在 ~/deploy-staging/。
# 用法（ECS）：STAGING=~/deploy-staging bash 02-restore-data.sh
set -euo pipefail
STAGING="${STAGING:-$HOME/deploy-staging}"

echo "== 1/3 PG 恢复（先清后灌——目标库应为全新 pgdata 卷）"
docker exec -i petro-agent-platform-pg-1 pg_restore -U petro -d petro --clean --if-exists < "$STAGING/pg.dump"
docker exec petro-agent-platform-pg-1 psql -U petro -d petro -tAc \
  "select 'reports='||count(*) from kb_report" 
docker exec petro-agent-platform-pg-1 psql -U petro -d petro -tAc \
  "select 'metering='||count(*) from agg.fct_daily_metering"

echo "== 2/3 MinIO 卷恢复（运行中解包，解完重启让其重扫）"
docker exec petro-agent-platform-minio-1 sh -c "cd /data && tar xzf -" < "$STAGING/minio-data.tgz"
docker compose restart minio

echo "== 3/3 Neo4j 卷恢复（运行中解包，解完重启）"
docker exec petro-agent-platform-neo4j-1 sh -c "cd /data && tar xzf -" < "$STAGING/neo4j-data.tgz"
docker compose restart neo4j

echo "== 数据恢复完成（核对上面 reports=6 / metering=31390）"
