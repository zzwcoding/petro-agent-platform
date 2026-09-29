"""api.chat SSE 骨架测试——00 §6 信封 + 三帧语义（P0-08 预留件验收面）。

覆盖：提问形态 done 帧信封、重连形态 replay_truncated 帧（00 §6.2 合同话术
原文＋断点续序）、Last-Event-ID 非整数 400 错误包（00 §3.2）、未认证 401
（A1 权限行同闸）。端点业务零实现——不触 app.state，无 lifespan 依赖。
"""

import json

from fastapi.testclient import TestClient

from app.api.chat import REPLAY_TRUNCATED_MESSAGE, render_frame
from app.main import app

client = TestClient(app)

ACTOR = {"X-Dev-User": "aqiang"}  # 五角色键（身份桩；缺头亦落默认角色）


def test_render_frame_envelope() -> None:
    """00 §6.1 帧信封：id/event/data 三行＋空行收束；中文不转义。"""
    assert render_frame(3, "done", {}) == "id: 3\nevent: done\ndata: {}\n\n"
    frame = render_frame(1, "stage", {"note": "阶段"})
    assert frame.startswith("id: 1\nevent: stage\ndata: {\"note\": \"阶段\"}\n\n")


def test_ask_fresh_emits_done_frame_and_closes() -> None:
    """提问形态：单枚 done 帧（data:{}，00 §6.1 结束帧形）后关流——骨架占位收场。"""
    resp = client.post("/api/chat/asks", json={"question": "渤海油田产量"}, headers=ACTOR)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    assert resp.headers["cache-control"] == "no-cache"
    assert resp.text == "id: 0\nevent: done\ndata: {}\n\n"


def test_resume_with_last_event_id_emits_replay_truncated() -> None:
    """重连形态（Last-Event-ID 头）：断点续序（7→8）＋replay_truncated 帧＋
    00 §6.2 收场②合同话术原文——不静默丢帧。"""
    resp = client.post(
        "/api/chat/asks",
        json={"resume_run_id": "run-x"},
        headers={**ACTOR, "Last-Event-ID": "7"},
    )
    assert resp.status_code == 200
    expected_data = json.dumps({"message": REPLAY_TRUNCATED_MESSAGE}, ensure_ascii=False)
    assert resp.text == f"id: 8\nevent: replay_truncated\ndata: {expected_data}\n\n"


def test_resume_with_run_id_only_starts_frame_at_zero() -> None:
    """重连形态（仅 resume_run_id，无头）：无断点则帧序从 0 起。"""
    resp = client.post(
        "/api/chat/asks", json={"resume_run_id": "run-x"}, headers=ACTOR
    )
    assert resp.status_code == 200
    assert resp.text.startswith("id: 0\nevent: replay_truncated\n")


def test_invalid_last_event_id_returns_400_error_package() -> None:
    """Last-Event-ID 非整数＝请求还没进门（00 §3.2/R8）——HTTP 400 错误包，
    不开流（SSE 内异常才走 error 帧，00 §6.1）。"""
    resp = client.post(
        "/api/chat/asks",
        json={"resume_run_id": "run-x"},
        headers={**ACTOR, "Last-Event-ID": "abc"},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == "chat_last_event_id_invalid"
    assert "Last-Event-ID" in body["message"]


def test_unregistered_actor_returns_401() -> None:
    """未认证 401（A1 权限行——SSE 通道鉴权与 D1 第三道同闸；非五角色键即失败）。"""
    resp = client.post(
        "/api/chat/asks", json={"question": "…"}, headers={"X-Dev-User": "not-a-role"}
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "security_unauthenticated"


def test_missing_actor_header_falls_back_to_default_role() -> None:
    """缺头不 401（00 §2.4：缺省落默认角色）——闸语义不被骨架改写。"""
    resp = client.post("/api/chat/asks", json={"question": "…"})
    assert resp.status_code == 200
    assert resp.text == "id: 0\nevent: done\ndata: {}\n\n"
