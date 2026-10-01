"""真装配冒烟（KB_SMOKE=1 门控）——演示文本真传走完五步→台账/任务/向量可查。

跑法（tickets/phase1/README.md P1-02a 验收）：
    KB_SMOKE=1 uv run pytest tests/test_kb_smoke_real.py -q

真装配含义：main.py lifespan 真起（真实 primary PG@5433 演示库＋ensure_kb_tables
含 pgvector 扩展）＋真 MinIO（compose reports 桶——presigned PUT 经 HTTP 真传，
平台不经手文件字节）＋真 gateway.complete（petro-main→MiniMax 线路，摘要/问题
块真生成——B6 唯一出口）。素材＝设定书 §A.1 井档案样本既有事实文本，零发明。
门控：环境变量 KB_SMOKE=1 未设即 skip（不进常规门禁——打真实 LLM 花钱）。
"""

import os
import time
import uuid

import pytest

pytestmark = [
    pytest.mark.skipif(
        os.environ.get("KB_SMOKE") != "1",
        reason="真装配冒烟需 KB_SMOKE=1（真实 PG/MinIO/LLM——不进常规门禁）",
    )
]

# 素材（设定书 §A.1 N-02 井档案样本＋§A.2 样本行既有事实——逐句注源，零发明）
DEMO_TEXT = """N-02 井完井报告（演示文本）

1 井基本情况
N-02 井（渤中28-1-N2）位于渤南区块 CEP-A 平台，井别采油（EW），
2019-06-15 投产，当前状态生产中。

2 完井段
完井段详见射孔与防砂参数表；防砂方式筛管完井。

3 投产信息
本井 2019-06-15 投产后维持自喷生产，日产油约 48.6 吨（§A.2 样本行）。
"""


def _wait_done(client: object, task_id: str, *, timeout: float = 180) -> dict:
    deadline = time.monotonic() + timeout
    last: dict = {}
    while time.monotonic() < deadline:
        last = client.get(f"/api/kb/tasks/{task_id}").json()  # type: ignore[attr-defined]
        if last["state"] in ("done", "failed", "stuck"):
            return last
        time.sleep(1.0)
    raise TimeoutError(f"任务未在 {timeout}s 内终态：{last}")


def test_real_assembly_smoke() -> None:

    from fastapi.testclient import TestClient

    from app.main import app

    tag = uuid.uuid4().hex[:6]
    with TestClient(app) as client:  # lifespan 真起——真 PG 建表＋真 MinIO/LLM 装配
        assert client.get("/health").json() == {"status": "ok"}

        # ① 建库（completion 完井报告类——四开关全开含图谱）
        lib = client.post(
            "/api/kb/libs",
            json={"lib_name": f"冒烟·完井报告库-{tag}", "biz_template": "completion"},
        )
        assert lib.status_code == 201, lib.text
        lib_id = lib.json()["lib_id"]

        # ② 直传受理（两拍第一拍）——presigned PUT 真凭证
        up = client.post(
            "/api/kb/uploads",
            json={
                "filename": f"N-02 井完井报告（冒烟 {tag}）.txt",
                "size": len(DEMO_TEXT.encode("utf-8")),
                "lib_id": lib_id,
            },
        )
        assert up.status_code == 200, up.text
        receipt = up.json()
        assert receipt["bucket"] == "报告原文"

        # ③ 客户端直传对象存储（平台不经手文件字节——HTTP PUT 打真 MinIO）
        import httpx

        put_resp = httpx.put(receipt["put_url"], content=DEMO_TEXT.encode("utf-8"))
        assert put_resp.status_code == 200, put_resp.text

        # ④ 确认入库（两拍第二拍——config_snapshot 定型）→ 五步真跑
        confirm = client.post(f"/api/kb/uploads/{receipt['upload_id']}/confirm")
        assert confirm.status_code == 200, confirm.text
        confirm_body = confirm.json()
        assert confirm_body["state"] == "running"
        snapshot = confirm_body["config_snapshot"]
        final = _wait_done(client, confirm_body["task_id"])
        assert final["state"] == "done", final
        assert [n["key"] for n in final["nodes"]] == [
            "parse", "chunk", "embed", "index", "enrich",
        ]
        assert all(n["state"] == "finish" for n in final["nodes"])
        assert snapshot == final["config_snapshot"]  # 定型快照全程不变

        # ⑤ 产物两卡（真 LLM 生成——富化子任务失败不阻塞整卷（F32），
        # 故摘要/问题允许缺卡；缺卡即 LLM 子任务失败，管线仍 done）
        adds = client.get(f"/api/kb/tasks/{confirm_body['task_id']}/additions").json()
        if adds["summary"] is not None:
            assert adds["summary"]["type"] == "摘要块"
        if adds["questions"] is not None:
            assert adds["questions"]["items"]

        # ⑥ 台账/详情/任务/活动流
        reports = client.get(
            "/api/kb/reports", params={"keyword": tag}
        ).json()
        assert reports["total"] == 1
        report = reports["items"][0]
        assert report["status"] == "已入库" and report["refs"] > 0
        detail = client.get(f"/api/kb/reports/{report['id']}").json()
        assert detail["fragments"]
        tasks = client.get("/api/kb/tasks", params={"source": "上传入库"}).json()
        assert any(t["id"] == confirm_body["task_id"] for t in tasks["items"])
        acts = client.get(f"/api/kb/libs/{lib_id}/activities").json()
        actions = {a["action"] for a in acts["items"]}
        assert {"新建库", "上传报告", "入库完成"} <= actions

        # ⑦ 向量真库可查（pgvector——演示库直查）
        import asyncio

        from sqlalchemy import text

        from app.infra.config import load_database_specs
        from app.infra.db import ConnectionManager

        async def _count_vectors() -> int:
            manager = ConnectionManager(load_database_specs())
            try:
                async with manager.readonly() as session:
                    row = await session.execute(
                        text(
                            "SELECT count(*) FROM kb_fragment f "
                            "JOIN kb_report r ON r.id = f.report_id "
                            "WHERE r.id = :rid AND f.embedding IS NOT NULL"
                        ),
                        {"rid": report["id"]},
                    )
                    return int(row.scalar_one())
            finally:
                await manager.dispose()

        embedded = asyncio.run(_count_vectors())
        assert embedded > 0, "向量半边未落库（pgvector）"
