"""真装配冒烟（FAQ_SMOKE=1 门控）——审核流闭环＋挖掘五拍一轮真跑。

跑法（tickets/phase1/README.md P1-06 验收）：
    FAQ_SMOKE=1 uv run pytest tests/test_faq_smoke_real.py -q

真装配含义：main.py lifespan 真起（真实 primary PG@5433 演示库＋ensure_faq_tables
＋演示种子）＋真 MinIO（导出直链真实预签名）＋真 gateway.complete（挖掘起草
petro-main→MiniMax 线路，B6 唯一出口——本轮仅端点 13 一次真调用，费用量级与
P0-05 演示证据同档）。比对向量＝LocalHashEmbedder 占位（无 LLM 成本）。

流程（票面：新增→待审核→发布→清单可见→挖掘起草一轮真跑）：
① 新增问答 → pending_review（待审核筛可见）→ review publish → serve（清单可见）
② 挖掘五拍：候选比对（三面去重真算）→ LLM 起草（真调用，溯源后缀在）
   → 携 source_candidate_id 入库（先进待审核）→ 发布 → 候选回写 published
③ B12 审计留痕查证（faq.* 动作族）＋导出直链签发（MinIO 真桶）。

重跑幂等：演示库状态不回滚——候选按状态就地取材（pending 首选走全五拍；
已比对/已起草候选复用在库草稿走后两拍，上轮真跑证据随 gateway 流水在案）。
"""

import os
import time

import pytest

pytestmark = [
    pytest.mark.skipif(
        os.environ.get("FAQ_SMOKE") != "1",
        reason="真装配冒烟需 FAQ_SMOKE=1（真实 PG/MinIO/LLM——不进常规门禁）",
    )
]


def _wait_scan_done(client: object, task_id: str, *, timeout: float = 30) -> dict:
    deadline = time.monotonic() + timeout
    last: dict = {}
    while time.monotonic() < deadline:
        last = client.get(f"/api/faq/scan-tasks/{task_id}").json()  # type: ignore[attr-defined]
        if last["status"] == "done":
            return last
        time.sleep(0.2)
    raise TimeoutError(f"扫库未在 {timeout}s 内终态：{last}")


def test_real_assembly_smoke() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:  # lifespan 真起——真 PG 建表＋种子＋真 MinIO/LLM
        assert client.get("/health").json() == {"status": "ok"}

        # 种子在库（九条直接发布——合同）
        listing = client.get("/api/faq/items").json()
        assert listing["grand_total"] >= 9

        # ① 新增 → 待审核 → 清单可见 → 发布 → 服务中（审核流闭环）
        created = client.post("/api/faq/items", json={
            "question": "配注合格率是什么？",
            "answer": "分层实注÷配注，达标井次占比（Owner：采油工艺所）",
            "is_negative": False,
            "hook": {"kind": "metric", "name": "配注合格率"},
        }).json()
        assert created["status"] == "pending_review"
        assert created["hint"] == (
            "已提交审核：「配注合格率是什么？」——审核发布后命中即秒回。"
        )
        pending = client.get("/api/faq/items", params={"status": "pending"}).json()
        assert created["id"] in [i["id"] for i in pending["items"]]
        reviewed = client.post(
            f"/api/faq/items/{created['id']}/review", json={"action": "publish"}
        ).json()
        assert reviewed["status"] == "serve"
        serve = client.get("/api/faq/items", params={"status": "serve"}).json()
        assert created["id"] in [i["id"] for i in serve["items"]]  # 发布后清单可见

        # ② 挖掘五拍真跑（候选按状态就地取材——状态机 compare 只认 pending、
        # draft 只认 compared；演示库状态不回滚，重跑不与状态机对撞）：
        # pending→全五拍（比对＋真 LLM 起草）／compared→起草拍（真 LLM）／
        # drafted→复用在库草稿／全 published（多轮重跑耗尽）→复用草稿普通入库。
        candidates = client.get("/api/faq/candidates").json()["items"]

        def _pick(*states: str) -> dict | None:
            return next((c for c in candidates if c["status"] in states), None)

        target = _pick("pending")
        if target is not None:  # 首拍：三面去重真算（pending→compared）
            compared = client.post(f"/api/faq/candidates/{target['id']}/compare").json()
            assert compared["status"] == "compared"
            assert compared["compare"]["verdict"] in ("ok", "dup")
            target["status"] = "compared"  # 本地同步——起草拍判定用
        target = target or _pick("compared")
        if target is not None and target["status"] == "compared":
            drafted = client.post(f"/api/faq/candidates/{target['id']}/draft")
            assert drafted.status_code == 200, drafted.text  # 真 LLM（petro-main）
            draft_body = drafted.json()
            assert draft_body["status"] == "drafted"
            assert draft_body["draft"].endswith("请人工核实）")  # 溯源后缀恒在
        else:
            target = _pick("drafted") or _pick("published")
            assert target is not None, "候选种子缺失——演示库须重置后重跑"
            # 已起草/已发布候选复用在库草稿（上轮真跑证据随 gateway 流水在案）
            draft_body = {"id": target["id"], "status": target["status"],
                          "draft": target["draft"] or ""}
        carry_anchor = draft_body["status"] == "drafted"  # published 复用不再携回写锚
        # 携 source_candidate_id 入库 → 先进待审核 → 发布 → 候选回写 published
        entry = client.post("/api/faq/items", json={
            "question": draft_body["draft"].split("（来源：")[0][:40],
            "answer": draft_body["draft"],
            "is_negative": False,
            "source_candidate_id": draft_body["id"] if carry_anchor else None,
        }).json()
        assert entry["status"] == "pending_review"
        if carry_anchor:
            assert entry["candidate"]["id"] == draft_body["id"]
        published_entry = client.post(
            f"/api/faq/items/{entry['id']}/review", json={"action": "publish"}
        ).json()
        assert published_entry["status"] == "serve"
        if carry_anchor:
            candidates = client.get(
                "/api/faq/candidates", params={"status": "published"}
            ).json()
            assert draft_body["id"] in [c["id"] for c in candidates["items"]]

        # 扫库（异步长任务——A1 未上线：空态说明收场，202→轮询）
        scan = client.post("/api/faq/scan-tasks")
        assert scan.status_code == 202
        scan_done = _wait_scan_done(client, scan.json()["task_id"])
        assert scan_done["new_cluster_count"] == 0
        assert "A1 问一问历史会话尚未上线" in (scan_done["hint"] or "")

        # ③ B12 审计留痕（faq.* 动作族）＋导出直链（MinIO 真桶真预签名）
        logs = client.get("/api/security/audit-logs", params={"page_size": 50}).json()
        actions = {row["action"] for row in logs["items"]}
        assert "faq.entry.created" in actions and "faq.entry.reviewed" in actions
        export = client.post("/api/faq/export").json()
        assert export["download_url"].startswith("http")
        assert export["columns"] == ["标准问", "相似问法", "负例问法", "答案"]
