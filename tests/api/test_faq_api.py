"""B3 路由族 API 测试——17 条 HTTP 路由全往返：形状/错误包/身份闸/审核流闭环。

装配：sqlite 底座＋假对象存储＋桩 LLM（dependency_overrides 替换服务定位，
不触 main.py lifespan；红线：任何测试不得真实调用 MiniMax/GLM 端点）。
种子＝合同 DTO 九条问答＋四簇候选（seed_demo_if_empty）。
"""

from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_faq, get_security
from app.api.errors import install_error_handlers
from app.api.faq import router as faq_router
from app.api.security import router as security_router
from app.domains.faq import FaqService
from tests.domains.faq.conftest import (
    FakeObjectStorage,
    RecordingAudit,
    StubCompleter,
    StubEmbedder,
    other_vector,
    same_vector,
)


@pytest.fixture
async def client(tmp_path: Any) -> AsyncIterator[tuple[TestClient, FakeObjectStorage, StubCompleter, RecordingAudit]]:  # noqa: E501
    from app.domains.faq.store import ensure_faq_tables, seed_demo_if_empty
    from app.domains.security import SecurityService
    from app.domains.security.store import ensure_audit_table
    from app.infra.db import ConnectionManager, DatabaseSpec
    from app.infra.eventbus import InMemoryEventBus

    spec = DatabaseSpec(
        name="primary", role="primary", driver="sqlite", host="", port=0,
        database=str(tmp_path / "faq-api.db"), user="", password="",
        pool_size=2, max_overflow=1,
    )
    manager = ConnectionManager([spec])
    await ensure_faq_tables(manager.engine())
    await seed_demo_if_empty(manager.engine())
    await ensure_audit_table(manager.engine())  # B12 审计表（api 层写口）
    storage = FakeObjectStorage()
    completer = StubCompleter(
        answers={
            "faq.candidate.draft": "月度递减率按环比计算。",
            "faq.draft.from_refs": "指标口径草稿。（来源：C1 指标卡「自然递减率」）",
            "faq.ledger_merged.suggestion": "修订建议稿。",
        }
    )
    audit = RecordingAudit()
    service = FaqService(
        manager, completer, storage,
        embedder=StubEmbedder({
            "产量完成率咋算的": same_vector(), "产量完成率怎么算？": same_vector(),
            "时率是什么意思": other_vector(),
        }),
        eventbus=InMemoryEventBus(),
        audit=audit,
        ontology_names_loader=_ontology_loader,
        ledger_loader=_ledger_loader,
        slice_loader=_slice_loader,
    )
    test_app = FastAPI()
    install_error_handlers(test_app)
    test_app.include_router(faq_router)
    test_app.include_router(security_router)  # B12 审计读面（补齐断言消费）
    test_app.dependency_overrides[get_faq] = lambda: service
    test_app.dependency_overrides[get_security] = lambda: SecurityService(manager)
    with TestClient(test_app) as test_client:
        yield test_client, storage, completer, audit
    await manager.dispose()


async def _ontology_loader() -> list[tuple[str, str]]:
    return [("指标卡", "产量完成率"), ("指标卡", "自然递减率"), ("术语", "时率")]


async def _ledger_loader(kind: str, ref_id: int) -> tuple[str, str, str] | None:
    if (kind, ref_id) == ("metric", 3):
        return ("自然递减率", "月：1 − q_t / q_(t−1)", "C1 指标卡「自然递减率」")
    return None


async def _slice_loader(report_id: str, fragment_id: str) -> tuple[str, str] | None:
    if (report_id, fragment_id) == ("rpt-n02", "f1"):
        return ("N-02（渤中28-1-N2）于 2019-06-15 投产。", "《N-02 井完井报告》章节 01")
    return None


# ---------- 端点 1/2：清单与详情 ----------


def test_endpoint_1_list_items_shape(client: Any) -> None:
    c = client[0]
    resp = c.get("/api/faq/items")
    assert resp.status_code == 200
    body = resp.json()
    assert body["grand_total"] == 9 and body["total"] == 9
    first = body["items"][0]
    assert first["id"] == "faq-1" and first["status"] == "serve"
    assert first["similar_questions"] == ["「月度完成率口径」（主任常问）"]
    assert first["hook"] is None  # 种子 hook 恒 null（合同注源）
    neg = c.get("/api/faq/items", params={"status": "neg"}).json()
    assert [i["id"] for i in neg["items"]] == ["faq-9"]
    kw = c.get("/api/faq/items", params={"keyword": "油价"}).json()
    assert [i["id"] for i in kw["items"]] == ["faq-9"]
    assert c.get("/api/faq/items", params={"status": "bogus"}).status_code == 400


def test_endpoint_2_detail(client: Any) -> None:
    c = client[0]
    body = c.get("/api/faq/items/faq-1").json()
    assert body["maintainer"] == "小李" and body["version"] == 1
    assert body["similar_questions"][0]["id"] == "sq-101"
    assert c.get("/api/faq/items/faq-404").status_code == 404
    assert c.get("/api/faq/items/faq-404").json()["code"] == "faq_not_found"


# ---------- 端点 3/17：新增入库＋审核发布（审核流闭环） ----------


def test_endpoint_3_create_then_17_review_full_loop(client: Any) -> None:
    c, _storage, _completer, _audit = client
    created = c.post("/api/faq/items", json={
        "question": "配注合格率是什么？",
        "answer": "分层实注÷配注，达标井次占比（Owner：采油工艺所）",
        "is_negative": False,
        "hook": {"kind": "metric", "name": "配注合格率"},
    })
    assert created.status_code == 200
    body = created.json()
    assert body["id"] == "faq-10" and body["status"] == "pending_review"
    assert body["hint"] == "已提交审核：「配注合格率是什么？」——审核发布后命中即秒回。"
    # 待审核筛可见＋行标——发布前不被消费
    pending = c.get("/api/faq/items", params={"status": "pending"}).json()
    assert [i["id"] for i in pending["items"]] == ["faq-10"]
    reviewed = c.post("/api/faq/items/faq-10/review", json={"action": "publish"})
    assert reviewed.status_code == 200
    rbody = reviewed.json()
    assert rbody["status"] == "serve" and rbody["version"] == 2
    assert "审核通过已发布" in rbody["hint"]
    # 审核流闭环：发布后进「服务中」筛、详情可查
    serve = c.get("/api/faq/items", params={"status": "serve"}).json()
    assert "faq-10" in [i["id"] for i in serve["items"]]
    # 重复审核 409
    assert c.post("/api/faq/items/faq-10/review", json={"action": "publish"}).status_code == 409
    # 负例登记 → 发布落 negative
    neg = c.post("/api/faq/items", json={
        "question": "帮我预测明年油价走势", "answer": "（不该答）", "is_negative": True,
    }).json()
    reviewed_neg = c.post(f"/api/faq/items/{neg['id']}/review", json={"action": "publish"}).json()
    assert reviewed_neg["status"] == "negative"
    # reject → disabled
    rej = c.post("/api/faq/items", json={"question": "待驳回条目", "answer": "x"}).json()
    rejected = c.post(f"/api/faq/items/{rej['id']}/review", json={"action": "reject"})
    assert rejected.json()["status"] == "disabled"
    # 空值占位（不拒空）
    empty = c.post("/api/faq/items", json={}).json()
    detail = c.get(f"/api/faq/items/{empty['id']}").json()
    assert detail["question"] == "（未填问题）" and detail["answer"] == "（未填答案）"


def test_endpoint_17_review_action_invalid_400(client: Any) -> None:
    c = client[0]
    assert c.post("/api/faq/items/faq-1/review", json={"action": "bogus"}).status_code == 400


# ---------- 端点 4：重复校验（非阻断） ----------


def test_endpoint_4_dup_check(client: Any) -> None:
    c = client[0]
    body = c.post("/api/faq/dup-checks", json={"question": "完成率公式是什么"}).json()
    assert body["hit"]["id"] == "faq-2"
    assert "建议改用合并相似问" in body["hint"]
    miss = c.post("/api/faq/dup-checks", json={"question": "全新无重复问句"}).json()
    assert miss == {"hit": None, "hint": None}
    assert c.post("/api/faq/dup-checks", json={"question": "  "}).status_code == 400


# ---------- 端点 5/6：相似问增删 ----------


def test_endpoint_5_6_similar_add_delete(client: Any) -> None:
    c = client[0]
    added = c.post("/api/faq/items/faq-1/similar-questions", json={"text": "主任的另一种问法"})
    assert added.status_code == 200
    abody = added.json()
    assert abody["id"] == "sq-104" and abody["version"] == 2
    dup = c.post("/api/faq/items/faq-1/similar-questions", json={"text": "躺井啥意思"})
    assert dup.status_code == 409  # 与其他条目相似问归一化重复（服务端兜底）
    removed = c.delete("/api/faq/items/faq-1/similar-questions/sq-104")
    assert removed.status_code == 200
    assert removed.json() == {"version": 3, "hint": "已删除——该问法不再命中本条。"}
    assert c.delete("/api/faq/items/faq-1/similar-questions/sq-404").status_code == 404
    assert c.post(
        "/api/faq/items/faq-999/similar-questions", json={"text": "x"}
    ).status_code == 404
    assert c.post(
        "/api/faq/items/faq-1/similar-questions", json={"text": " "}
    ).status_code == 400


# ---------- 端点 7/8：合并与停用启用 ----------


def test_endpoint_7_merge(client: Any) -> None:
    c, _s, _c2, _a = client
    merged = c.post("/api/faq/items/faq-2/merge", json={"target_id": "faq-1"})
    assert merged.status_code == 200
    body = merged.json()
    assert body["merged_count"] == "2 条 → 1 条"
    assert body["target"] == {"id": "faq-1", "similar_questions_count": 2}
    assert "两种问法现在命中同一条答案" in body["hint"]
    assert c.get("/api/faq/items/faq-2").status_code == 404  # 被并入条目删除
    assert c.post("/api/faq/items/faq-1/merge", json={"target_id": "faq-1"}).status_code == 400


def test_endpoint_8_state_toggle(client: Any) -> None:
    c = client[0]
    disabled = c.post("/api/faq/items/faq-4/state", json={"action": "disable"})
    assert disabled.json() == {"id": "faq-4", "status": "disabled", "version": 2}
    enabled = c.post("/api/faq/items/faq-4/state", json={"action": "enable"}).json()
    assert enabled["status"] == "serve" and enabled["version"] == 3
    assert c.post("/api/faq/items/faq-9/state", json={"action": "disable"}).status_code == 409
    assert c.post("/api/faq/items/faq-4/state", json={"action": "enable"}).status_code == 409
    assert c.post("/api/faq/items/faq-4/state", json={"action": "x"}).status_code == 400


# ---------- 端点 9：候选问题库 ----------


def test_endpoint_9_candidates(client: Any) -> None:
    c = client[0]
    body = c.get("/api/faq/candidates").json()
    assert body["total"] == 4
    assert [i["freq"] for i in body["items"]] == [23, 15, 11, 6]  # 频次倒序
    assert body["scan"] == {"running_task_id": None, "last_hint": None}
    c2 = next(i for i in body["items"] if i["id"] == "c2")
    assert c2["compare"]["verdict"] == "ok"
    assert "本体命中：指标卡 · 自然递减率" in c2["compare"]["hint"]
    assert c.get("/api/faq/candidates", params={"status": "bogus"}).status_code == 400


# ---------- 端点 10/11：扫库异步长任务 ----------


def test_endpoint_10_11_scan_task_lifecycle(client: Any) -> None:
    import time

    c = client[0]
    accepted = c.post("/api/faq/scan-tasks")
    assert accepted.status_code == 202  # 受理 202（异步长任务）
    body = accepted.json()
    assert body["status"] == "running" and "扫描不会中断" in body["hint"]
    task_id = body["task_id"]
    # 重入 409（全局单例）
    assert c.post("/api/faq/scan-tasks").status_code == 409
    for _ in range(200):
        progress = c.get(f"/api/faq/scan-tasks/{task_id}").json()
        if progress["status"] == "done":
            break
        time.sleep(0.02)
    assert progress["new_cluster_count"] == 0
    assert "A1 问一问历史会话尚未上线" in progress["hint"]  # 料源空态说明
    listing = c.get("/api/faq/candidates").json()
    assert listing["scan"]["last_hint"] == progress["hint"]
    assert c.get("/api/faq/scan-tasks/scan-9999").status_code == 404


# ---------- 端点 12/13：向量比对与候选起草 ----------


def test_endpoint_12_13_compare_then_draft(client: Any) -> None:
    c, _storage, completer, _audit = client
    compared = c.post("/api/faq/candidates/c1/compare")
    assert compared.status_code == 200
    body = compared.json()
    assert body["status"] == "compared"
    assert body["compare"]["verdict"] == "dup"
    assert body["compare"]["dup_question"] == "产量完成率怎么算？"
    assert "建议改用合并相似问" in body["compare"]["hint"]
    assert c.post("/api/faq/candidates/c1/compare").status_code == 409  # 非 pending 409
    # dup 不关起草闸：草稿＝劝阻文案、不调 LLM、无挂接建议
    draft = c.post("/api/faq/candidates/c1/draft")
    assert draft.status_code == 200
    dbody = draft.json()
    assert dbody["status"] == "drafted"
    assert dbody["draft"] == "（疑似重复——不建议新增，请改用清单里的合并相似问。）"
    assert dbody["hook_suggestion"] is None
    assert not completer.calls
    # ok 面：c3 比对 → LLM 起草（溯源后缀＋挂接建议）
    compared3 = c.post("/api/faq/candidates/c3/compare").json()
    assert compared3["compare"]["verdict"] == "ok"
    draft3 = c.post("/api/faq/candidates/c3/draft")
    d3 = draft3.json()
    assert d3["draft"].endswith("（来源：术语 · 时率 · LLM 基于历史回答归纳，请人工核实）")
    assert d3["hook_suggestion"] == {"kind": "term", "name": "时率"}
    assert c.post("/api/faq/candidates/c4/draft").status_code == 409  # 未比对起草 409
    assert c.post("/api/faq/candidates/c99/compare").status_code == 404


# ---------- 端点 14：引用知识起草 ----------


def test_endpoint_14_drafts_from_refs(client: Any) -> None:
    c, _storage, completer, _audit = client
    body = c.post("/api/faq/drafts", json={"ledger_ref": {"kind": "metric", "id": 3}}).json()
    assert "（来源：C1 指标卡「自然递减率」）" in body["draft"]
    assert body["hook_suggestion"] == {"kind": "metric", "name": "自然递减率"}
    both = c.post("/api/faq/drafts", json={
        "ledger_ref": {"kind": "metric", "id": 3},
        "slice_ref": {"report_id": "rpt-n02", "fragment_id": "f1"},
    }).json()
    assert both["draft"] == "指标口径草稿。（来源：C1 指标卡「自然递减率」）"  # 桩应答原样出门
    prompt = completer.calls[-1][1]
    assert "月：1 − q_t / q_(t−1)（来源：C1 指标卡「自然递减率」）" in prompt  # 台账段服务端直取
    assert "N-02（渤中28-1-N2）于 2019-06-15 投产。（来源：《N-02 井完井报告》章节 01）" in prompt
    assert "逐段保留" in prompt  # 来源标注保留指令
    assert c.post("/api/faq/drafts", json={}).status_code == 400  # 两源全空 400
    assert c.post(
        "/api/faq/drafts", json={"ledger_ref": {"kind": "bogus", "id": 1}}
    ).status_code == 400
    assert c.post(
        "/api/faq/drafts", json={"ledger_ref": {"kind": "term", "id": 999}}
    ).status_code == 404


# ---------- 端点 15/16：导入与导出 ----------


CSV_BODY = (
    "标准问,相似问法,负例问法,答案\n"
    "配注合格率是什么？,「配注达标率」,,'分层实注÷配注，达标井次占比'\n"
    "产量完成率怎么算？,,,'完全重复行'\n"
    "缺答案的行,,,\n"
).encode()


def test_endpoint_15_import_counts_and_audit(client: Any) -> None:
    """multipart 落位（P1-11）：file 字段 form-data 上传；filename 取上传件名。"""
    c, storage, _c2, _a = client
    resp = c.post(
        "/api/faq/import",
        params={"mode": "append", "dry_run": "true"},
        files={"file": ("faq.csv", CSV_BODY, "text/csv")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["dry_run"] is True
    assert (body["added"], body["merged"], body["skipped"], body["failed"]) == (1, 0, 1, 1)
    assert body["failures"] == [{"row": 3, "reason": "缺答案列——模板列必填"}]
    assert body["hint"].startswith("试校验通过（未入库）：可新增 1")
    real = c.post(
        "/api/faq/import",
        params={"mode": "append", "dry_run": "false"},
        files={"file": ("faq.csv", CSV_BODY, "text/csv")},
    ).json()
    assert real["added"] == 1 and real["skipped"] == 1 and real["failed"] == 1
    listing = c.get("/api/faq/items").json()
    assert listing["grand_total"] == 10  # 9 种子＋1 新增
    imported = next(i for i in listing["items"] if i["id"] == "faq-10")
    assert imported["status"] == "pending_review"  # 批量新增同走待审核（审核流做齐）
    assert any(k.startswith("faq/import/") for k in storage.objects)  # 文件落 MinIO 不过期
    assert c.post(
        "/api/faq/import", params={"mode": "bogus"},
        files={"file": ("faq.csv", CSV_BODY, "text/csv")},
    ).status_code == 400
    assert c.post(
        "/api/faq/import", params={"mode": "append"},
        files={"file": ("a.xlsx", b"x", "application/octet-stream")},
    ).status_code == 400
    assert c.post(
        "/api/faq/import", params={"mode": "append"},
        files={"file": ("empty.csv", b"", "text/csv")},
    ).status_code == 400


def test_endpoint_16_export_and_b12_audit_rows(client: Any) -> None:
    c, storage, _c2, _audit = client
    resp = c.post("/api/faq/export")
    assert resp.status_code == 200
    body = resp.json()
    assert body["columns"] == ["标准问", "相似问法", "负例问法", "答案"]  # 与导入模板对称
    assert body["download_url"].startswith("https://minio.test/get/")
    assert "已导出 FAQ 全库" in body["hint"]
    export_key = next(k for k in storage.objects if k.startswith("faq/export/"))
    text = storage.objects[export_key].decode("utf-8-sig")
    assert "帮我预测明年油价" in text  # 负例列随库带出
    # B12：关键写端点 api 层审计（faq.* 命名）
    logs = c.get(
        "/api/security/audit-logs", params={"pageSize": 50}
    ).json()["items"]
    actions = {row["action"] for row in logs}
    assert "faq.library.exported" in actions
    # 触发一次新增/停用/合并/导入后审计动作齐全
    c.post("/api/faq/items", json={"question": "审计用问答", "answer": "x"})
    c.post("/api/faq/items/faq-4/state", json={"action": "disable"})
    c.post("/api/faq/items/faq-2/merge", json={"target_id": "faq-1"})
    c.post("/api/faq/items/faq-10/review", json={"action": "publish"})
    c.post(
        "/api/faq/import",
        params={"mode": "append", "dry_run": "true"},
        files={"file": ("faq.csv", CSV_BODY, "text/csv")},
    )
    logs2 = c.get("/api/security/audit-logs", params={"pageSize": 50}).json()["items"]
    actions2 = {row["action"] for row in logs2}
    assert {
        "faq.entry.created", "faq.entry.reviewed", "faq.entry.state_changed",
        "faq.entry.merged", "faq.library.imported", "faq.library.exported",
    } <= actions2
