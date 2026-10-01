"""api.chat SSE 测试——00 §6 信封＋三帧语义（P0-08 骨架判据保持）＋P1-08a 主链往返。

覆盖：帧信封渲染、提问形态全帧流（域四层流水线）、重连形态 replay_truncated 帧
（00 §6.2 合同话术原文＋断点续序——infra.sse_channel 未建判据不动）、
Last-Event-ID 非整数 400、未认证 401（A1 权限行同闸）、resume 端点（澄清续推
往返/404/409/400 错误包）。装配：sqlite 底座＋真 ChatService（假缝——
tests/domains/chat/conftest 同构）＋真 SecurityService（B12 审计读面）。
"""

import json
from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.chat import REPLAY_TRUNCATED_MESSAGE, render_frame
from app.api.chat import router as chat_router
from app.api.deps import get_chat, get_security
from app.api.errors import install_error_handlers
from app.api.security import router as security_router
from app.domains.chat.store import ensure_chat_tables
from app.domains.security import SecurityService
from app.domains.security.store import ensure_audit_table
from app.infra.db import ConnectionManager, DatabaseSpec
from tests.domains.chat.conftest import Seams, make_service

ACTOR = {"X-Dev-User": "aqiang"}  # 五角色键（身份桩；缺头亦落默认角色）


@pytest.fixture
async def env(tmp_path: Any) -> AsyncIterator[tuple[TestClient, str]]:
    spec = DatabaseSpec(
        name="primary", role="primary", driver="sqlite", host="", port=0,
        database=str(tmp_path / "chat-api.db"), user="", password="",
        pool_size=2, max_overflow=1,
    )
    manager = ConnectionManager([spec])
    await ensure_chat_tables(manager.engine())
    await ensure_audit_table(manager.engine())
    test_app = FastAPI()
    install_error_handlers(test_app)
    test_app.include_router(chat_router)
    test_app.include_router(security_router)  # B12 审计读面（断言消费）
    test_app.dependency_overrides[get_chat] = lambda: make_service(manager, Seams())
    test_app.dependency_overrides[get_security] = lambda: SecurityService(manager)
    with TestClient(test_app) as test_client:
        yield test_client, str(tmp_path / "chat-api.db")
    await manager.dispose()


def test_render_frame_envelope() -> None:
    """00 §6.1 帧信封：id/event/data 三行＋空行收束；中文不转义。"""
    assert render_frame(3, "done", {}) == "id: 3\nevent: done\ndata: {}\n\n"
    frame = render_frame(1, "stage", {"note": "阶段"})
    assert frame.startswith("id: 1\nevent: stage\ndata: {\"note\": \"阶段\"}\n\n")


def test_fresh_ask_streams_business_frames(env: Any) -> None:
    """提问形态（P1-08a 填肉）：19 类帧流真跑——session 起手、done 收尾。"""
    client = env[0]
    resp = client.post("/api/chat/asks", json={"question": "渤海油田产量"}, headers=ACTOR)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    assert resp.headers["cache-control"] == "no-cache"
    events = _parse_frames(resp.text)
    assert events[0] == ("session", {"run_id": events[0][1]["run_id"],
                                     "thread_id": events[0][1]["thread_id"]})
    assert events[0][1]["run_id"].startswith("run-")
    assert [name for name, _ in events][-1] == "done"
    assert [name for name, _ in events].count("sec_check") == 3
    assert [name for name, _ in events].count("match") == 6
    assert "verdict" in [name for name, _ in events]


def _parse_frames(text: str) -> list[tuple[str, dict[str, Any]]]:
    frames: list[tuple[str, dict[str, Any]]] = []
    for block in text.split("\n\n"):
        if not block.strip():
            continue
        event = data = None
        for line in block.split("\n"):
            if line.startswith("event: "):
                event = line.removeprefix("event: ")
            elif line.startswith("data: "):
                data = json.loads(line.removeprefix("data: "))
        assert event is not None and data is not None
        frames.append((event, data))
    return frames


def test_resume_with_last_event_id_emits_replay_truncated(env: Any) -> None:
    """重连形态（Last-Event-ID 头）：断点续序（7→8）＋replay_truncated 帧＋
    00 §6.2 收场②合同话术原文——不静默丢帧（P0-08 骨架判据保持）。"""
    client = env[0]
    resp = client.post(
        "/api/chat/asks",
        json={"resume_run_id": "run-x"},
        headers={**ACTOR, "Last-Event-ID": "7"},
    )
    assert resp.status_code == 200
    expected_data = json.dumps({"message": REPLAY_TRUNCATED_MESSAGE}, ensure_ascii=False)
    assert resp.text == f"id: 8\nevent: replay_truncated\ndata: {expected_data}\n\n"


def test_resume_with_run_id_only_starts_frame_at_zero(env: Any) -> None:
    """重连形态（仅 resume_run_id，无头）：无断点则帧序从 0 起。"""
    client = env[0]
    resp = client.post(
        "/api/chat/asks", json={"resume_run_id": "run-x"}, headers=ACTOR
    )
    assert resp.status_code == 200
    assert resp.text.startswith("id: 0\nevent: replay_truncated\n")


def test_invalid_last_event_id_returns_400_error_package(env: Any) -> None:
    """Last-Event-ID 非整数＝请求还没进门（00 §3.2/R8）——HTTP 400 错误包，
    不开流（SSE 内异常才走 error 帧，00 §6.1）。"""
    client = env[0]
    resp = client.post(
        "/api/chat/asks",
        json={"resume_run_id": "run-x"},
        headers={**ACTOR, "Last-Event-ID": "abc"},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == "chat_last_event_id_invalid"
    assert "Last-Event-ID" in body["message"]


def test_empty_question_without_resume_form_is_400(env: Any) -> None:
    """question 为空且非重连/续跑模式 → 400（A1 错误码草案第一行）。"""
    client = env[0]
    for body in (None, {"question": ""}, {"question": "   "}):
        resp = client.post("/api/chat/asks", json=body, headers=ACTOR)
        assert resp.status_code == 400, resp.text
        assert resp.json()["code"] == "chat_param_invalid"


def test_unregistered_actor_returns_401(env: Any) -> None:
    """未认证 401（A1 权限行——SSE 通道鉴权与 D1 第三道同闸；非五角色键即失败）。"""
    client = env[0]
    resp = client.post(
        "/api/chat/asks", json={"question": "…"}, headers={"X-Dev-User": "not-a-role"}
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "security_unauthenticated"


def test_missing_actor_header_falls_back_to_default_role(env: Any) -> None:
    """缺头不 401（00 §2.4：缺省落默认角色）——闸语义不被骨架改写。"""
    client = env[0]
    resp = client.post("/api/chat/asks", json={"question": "产量如何"})
    assert resp.status_code == 200
    assert _parse_frames(resp.text)[0][0] == "session"


class TestResumeEndpoint:
    def test_clarify_resume_roundtrip(self, env: Any) -> None:
        """澄清续推（端点 5）：asks 澄清挂起 → resume 带 choice → done 收场。"""
        client = env[0]
        first = _parse_frames(client.post(
            "/api/chat/asks", json={"question": "有效产量是多少"}, headers=ACTOR,
        ).text)
        assert [name for name, _ in first][-1] != "done"  # 挂起收束
        run_id = first[0][1]["run_id"]
        clarify = next(data for name, data in first if name == "clarify")
        choice = next(c["value"] for c in clarify["choices"] if c["value"] != "默认口径 A")
        second = _parse_frames(client.post(
            f"/api/chat/runs/{run_id}/resume",
            json={"kind": "clarify", "choice": choice},
            headers=ACTOR,
        ).text)
        assert [name for name, _ in second][-1] == "done"
        assert "clarify" not in [name for name, _ in second]  # 有界循环——最多弹一次
        verdict = next(data for name, data in second if name == "verdict")
        assert verdict["need_clarify"] is False and verdict["chain"] == "检索问答链"

    def test_resume_unknown_run_is_404(self, env: Any) -> None:
        client = env[0]
        resp = client.post(
            "/api/chat/runs/run-missing/resume",
            json={"kind": "clarify", "choice": "A"},
            headers=ACTOR,
        )
        assert resp.status_code == 404
        assert resp.json()["code"] == "chat_run_not_found"

    def test_resume_on_terminal_run_is_409(self, env: Any) -> None:
        """对已终态 resume → 409（状态机约束——澄清帧最多弹一次）。"""
        client = env[0]
        first = _parse_frames(client.post(
            "/api/chat/asks", json={"question": "产量完成率如何"}, headers=ACTOR,
        ).text)
        run_id = first[0][1]["run_id"]
        resp = client.post(
            f"/api/chat/runs/{run_id}/resume",
            json={"kind": "clarify", "choice": "A"},
            headers=ACTOR,
        )
        assert resp.status_code == 409
        assert resp.json()["code"] == "chat_run_state"

    def test_approval_resume_without_suspension_is_409(self, env: Any) -> None:
        """审批回流：骨架期无审批挂起 run——非 interrupt 挂起态一律 409。"""
        client = env[0]
        first = _parse_frames(client.post(
            "/api/chat/asks", json={"question": "产量完成率如何"}, headers=ACTOR,
        ).text)
        run_id = first[0][1]["run_id"]
        resp = client.post(
            f"/api/chat/runs/{run_id}/resume",
            json={"kind": "approval", "decision": "approve"},
            headers=ACTOR,
        )
        assert resp.status_code == 409

    def test_action_reject_without_reason_is_400(self, env: Any) -> None:
        """Action 链驳回缺理由 → 400（N12「须写理由的驳回」——A1 错误码草案）。"""
        client = env[0]
        first = _parse_frames(client.post(
            "/api/chat/asks", json={"question": "产量完成率如何"}, headers=ACTOR,
        ).text)
        run_id = first[0][1]["run_id"]
        resp = client.post(
            f"/api/chat/runs/{run_id}/resume",
            json={"kind": "approval", "decision": "reject"},
            headers=ACTOR,
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == "chat_param_invalid"
        assert "理由" in resp.json()["message"]


def test_ask_received_audited(env: Any) -> None:
    """B12：asks 受理审计 chat.ask.received（票面——审计读面 action 筛可见）。"""
    client, _db_path = env
    resp = client.post("/api/chat/asks", json={"question": "渤海油田产量"}, headers=ACTOR)
    assert resp.status_code == 200
    logs = client.get(
        "/api/security/audit-logs", params={"action": "chat.ask.received"}, headers=ACTOR,
    )
    assert logs.status_code == 200
    assert logs.json()["total"] >= 1
