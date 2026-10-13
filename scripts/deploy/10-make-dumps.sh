#!/usr/bin/env bash
# 【本机侧】打数据搬家包——精益版：只搬云上要用的，历史运行数据不搬。
# 763MB 构成分析：agent_v2 检查点家族（checkpoint_write/blob/checkpoint/step/
# blackbox/run）≈718MB＝Q17 考试会话历史（云端空表起步）；gateway_spend_record
# 6MB＝考试计费账。真正要搬：public 知识面（kb_*/wiki/faq/台账/enrich 向量）
# ＋ agg/data_plane/raw（问数链）≈ 30MB ＋ MinIO 原件 ＋ Neo4j 图。
# 产物：~/petro-deploy-staging/{pg.dump, minio-data.tgz, neo4j-data.tgz, config-env.tgz}
# 数据静态（前端未上线、无写入流量），dump 即终态；搬家前若本地有新入库，重跑本脚本。
set -euo pipefail
STAGING="${STAGING:-$HOME/petro-deploy-staging}"
mkdir -p "$STAGING"

echo "== 1/4 PG：结构全量＋知识/数据面数据；排除 agent_v2_* 历史与考试计费账（仅数据）"
docker exec petro-agent-platform-pg-1 pg_dump -U petro -Fc petro \
  --exclude-table-data='agent_v2_*' \
  --exclude-table-data='gateway_spend_record' \
  > "$STAGING/pg.dump"
ls -lh "$STAGING/pg.dump"

echo "== 2/4 MinIO 对象卷（报告原件桶）"
docker cp petro-agent-platform-minio-1:/data - | gzip > "$STAGING/minio-data.tgz"
ls -lh "$STAGING/minio-data.tgz"

echo "== 3/4 Neo4j 图卷"
docker cp petro-agent-platform-neo4j-1:/data - | gzip > "$STAGING/neo4j-data.tgz"
ls -lh "$STAGING/neo4j-data.tgz"

echo "== 4/4 配置与密钥（config/database.yaml ＋ .env——scp 直传，不经 git/聊天）"
tar czf "$STAGING/config-env.tgz" config/database.yaml .env
ls -lh "$STAGING/config-env.tgz"

echo "== 搬家包就绪：$STAGING"
echo "传输：scp $STAGING/* <user>@<ecs>:~/deploy-staging/"
