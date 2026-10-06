# 数据面 worker 镜像（云部署——deploy/cloud/compose.yml tpa-worker 消费）
# 构建上下文＝data-plane 仓根（app/ worker/ deploy/worker-requirements.txt）
# 进料/质检/agg 三面常驻周期（python -m worker.scheduler）；DP-02 退役的 serve
# 问答面不进镜像（deploy/Dockerfile 已标 DEPRECATED 留档）。
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1
COPY deploy/worker-requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ \
      -r /tmp/requirements.txt && rm /tmp/requirements.txt
COPY app/ app/
COPY worker/ worker/
COPY migrations/ migrations/
CMD ["python", "-m", "worker.scheduler"]
