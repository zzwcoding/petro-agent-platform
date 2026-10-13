# 主平台后端镜像（云部署——deploy/cloud/compose.yml tpa-backend/tpa-v2-backend 共用）
# 构建上下文＝主仓根（app/ appv2/ ontology/ config/ migrations/ alembic.ini
# q12_v2_launcher.py 本文件同层 requirements）。
# V2 后端（tpa-v2-backend＝q12_v2_launcher:8001）与 V1 后端（app.main:8000）同镜像——
# V2 运行面三件：appv2/＋ontology/（台账/术语/本体资产真源）＋q12_v2_launcher.py。
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1
COPY deploy/cloud/backend-requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ \
      -r /tmp/requirements.txt && rm /tmp/requirements.txt
COPY app/ app/
COPY appv2/ appv2/
COPY ontology/ ontology/
COPY config/ config/
COPY migrations/ migrations/
COPY alembic.ini .
COPY q12_v2_launcher.py .
EXPOSE 8000
# 健康检查走 /health（curl 不在 slim 底——用标准库 urllib）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
