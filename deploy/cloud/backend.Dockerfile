# 主平台后端镜像（云部署——deploy/cloud/compose.yml tpa-backend 消费）
# 构建上下文＝主仓根（app/ config/ migrations/ alembic.ini 本文件同层 requirements）
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1
COPY deploy/cloud/backend-requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ \
      -r /tmp/requirements.txt && rm /tmp/requirements.txt
COPY app/ app/
COPY config/ config/
COPY migrations/ migrations/
COPY alembic.ini .
EXPOSE 8000
# 健康检查走 /health（curl 不在 slim 底——用标准库 urllib）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
