"""api.chat SSE 测试——00 §6 信封＋三帧语义（P0-08 骨架判据保持）＋P1-08a 主链
往返＋P1-08c 树叙事时序与断线重连真恢复。

覆盖：帧信封渲染、提问形态全帧流（域四层流水线＋node 步进）、树帧先于 token
（不交错乱序——时序断言）、断线重连两形态（Last-Event-ID 中段续传→收场②骨架
判据保持；resume_run_id run 恢复→已持久化帧序列重放：done 全量/挂起前缀/
running ③收场/未知 run 404）、Last-Event-ID 非整数 400、未认证 401（A1 权限行
同闸）、resume 端点（澄清续推往返/404/409/400 错误包）。
装配：sqlite 底座＋真 ChatService（假缝——tests/domains/chat/conftest 同构）＋
真 SecurityService（B12 审计读面）。
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
from app.domains.chat import domain as d
from app.domains.chat.store import ChatStore, ensure_chat_tables
from app.domains.security import SecurityService
from app.domains.security.store import ensure_audit_table
from app.infra.db import ConnectionManager, DatabaseSpec
from tests.domains.chat.conftest import Seams, make_service

ACTOR = {"X-Dev-User": "aqiang"}  # 五角色键（身份桩；缺头亦落默认角色）

TREE_FRAMES = {"stage", "sec_check", "match", "assembly", "verdict",
               "node", "node_line", "notice"}


@pytest.fixture
async def env(tmp_path: Any) -> AsyncIterator[tuple[TestClient, ConnectionManager]]:
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
        yield test_client, manager
    await manager.dispose()


def test_render_frame_envelope() -> None:
    """00 §6.1 帧信封：id/event/data 三行＋空行收束；中文不转义。"""
    assert render_frame(3, "done", {}) == "id: 3\nevent: done\ndata: {}\n\n"
    frame = render_frame(1, "stage", {"note": "阶段"})
    assert frame.startswith("id: 1\nevent: stage\ndata: {\"note\": \"阶段\"}\n\n")


def test_fresh_ask_streams_business_frames(env: Any) -> None:
    """提问形态（P1-08a 填肉＋P1-08c 树叙事）：19 类帧流真跑——session 起手、
    done 收尾；node 帧族沿实时路径推进（N1 安检/N3 装配/N5 裁决族在流）。"""
    client = env[0]
    resp = client.post("/api/chat/asks", json={"question": "渤海油田产量"}, headers=ACTOR)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    assert resp.headers["cache-control"] == "no-cache"
    events = _parse_frames(resp.text)
    assert events[0] == ("session", {"run_id": events[0][1]["run_id"],
                                     "thread_id": events[0][1]["thread_id"]})
    assert events[0][1]["run_id"].startswith("run-")
    names = [name for name, _ in events]
    assert names[-1] == "done"
    assert names.count("sec_check") == 3
    assert names.count("match") == 6
    assert "verdict" in names
    node_keys = [data["key"] for name, data in events if name == "node"]
    assert node_keys[:2] == ["N1", "N1"]  # N1 统一安检 process→finish 起步
    assert {"N3", "N4", "N5", "N5b", "N6", "N17", "S0", "S6"} <= set(node_keys)


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


def test_tree_frames_precede_tokens(env: Any) -> None:
    """token 帧切片与树帧不交错乱序（P1-08c 时序断言）：首个 token 之前是全部
    stage/sec_check/match/assembly/verdict/node/node_line/notice 帧。"""
    client = env[0]
    resp = client.post(
        "/api/chat/asks", json={"question": "产量完成率如何"}, headers=ACTOR,
    )
    frames = _parse_frames(resp.text)
    names = [name for name, _ in frames]
    assert "token" in names  # 生成路径——token 切片在流
    first_token = names.index("token")
    assert first_token > 0
    assert not TREE_FRAMES.intersection(names[first_token:])
    assert names[-1] == "done" and names[-2] == "answer"


def test_reconnect_last_event_id_only_keeps_skeleton_closing(env: Any) -> None:
    """重连形态①（仅 Last-Event-ID 头——无法定位 run）：断点续序（7→8）＋
    replay_truncated 帧（resume_point＝断点）＋00 §6.2 收场②合同话术原文——
    不静默丢帧（P0-08 骨架判据保持）。"""
    client = env[0]
    resp = client.post(
        "/api/chat/asks",
        json={},
        headers={**ACTOR, "Last-Event-ID": "7"},
    )
    assert resp.status_code == 200
    expected_data = json.dumps(
        {"resume_point": 7, "message": REPLAY_TRUNCATED_MESSAGE}, ensure_ascii=False,
    )
    assert resp.text == f"id: 8\nevent: replay_truncated\ndata: {expected_data}\n\n"


def test_run_recovery_replays_done_run(env: Any) -> None:
    """断线重连形态②（resume_run_id run 恢复——P1-08c 真恢复）：done run 重放
    已持久化帧序列 session(resume)→verdict→citation→answer→done——已出内容不丢
    （与原流同形同值）。"""
    client = env[0]
    first = _parse_frames(client.post(
        "/api/chat/asks", json={"question": "产量完成率如何"}, headers=ACTOR,
    ).text)
    run_id = first[0][1]["run_id"]
    first_data = _frames_by_name(first)
    replay = _parse_frames(client.post(
        "/api/chat/asks", json={"resume_run_id": run_id}, headers=ACTOR,
    ).text)
    assert [name for name, _ in replay] == ["session", "verdict", "citation", "answer", "done"]
    assert replay[0][1]["resume"] is True and replay[0][1]["run_id"] == run_id
    assert replay[1][1] == first_data["verdict"][0]
    assert replay[2][1] == first_data["citation"][0]
    assert replay[3][1] == first_data["answer"][0]


def test_run_recovery_replays_from_breakpoint_frame_id(env: Any) -> None:
    """run 恢复＋Last-Event-ID 头：重放流帧序号自断点续枚举（重放帧与原流帧
    id 不对齐——能补的是持久化内容而非原流断点后的原帧序列，如实登记）。"""
    client = env[0]
    first = _parse_frames(client.post(
        "/api/chat/asks", json={"question": "产量完成率如何"}, headers=ACTOR,
    ).text)
    run_id = first[0][1]["run_id"]
    replay = client.post(
        "/api/chat/asks",
        json={"resume_run_id": run_id},
        headers={**ACTOR, "Last-Event-ID": "42"},
    ).text
    assert replay.startswith("id: 43\nevent: session\n")


def test_run_recovery_pending_clarify_replays_up_to_clarify(env: Any) -> None:
    """挂起 run 恢复：session→verdict→clarify（pending_interrupt 持久帧回放）——
    流收束不发 done（镜像原 ask 挂起形态；决策回流仍走端点 5）。"""
    client = env[0]
    first = _parse_frames(client.post(
        "/api/chat/asks", json={"question": "有效产量是多少"}, headers=ACTOR,
    ).text)
    run_id = first[0][1]["run_id"]
    clarify = next(data for name, data in first if name == "clarify")
    replay = _parse_frames(client.post(
        "/api/chat/asks", json={"resume_run_id": run_id}, headers=ACTOR,
    ).text)
    assert [name for name, _ in replay] == ["session", "verdict", "clarify"]
    assert replay[-1][1] == clarify


def test_run_recovery_running_run_truncates_honestly(env: Any) -> None:
    """running run 恢复：持久前缀（session/verdict）＋replay_truncated ③收场
    （生成已随断连取消——「回答生成已被取消…」合同话术）。"""
    client, manager = env
    import asyncio

    store = ChatStore(manager)

    async def _seed() -> str:
        session = await store.ensure_session(None, user_id="aqiang", title="t")
        run = await store.create_run(session.id)
        run.verdict = {"chain": "检索问答链", "slots": "∅",
                       "confidence": "低（证据不足）", "need_clarify": False}
        await store.save_run(run)
        return run.id

    # TestClient 事件循环外直接驱动——asyncio.run 独立循环安全（sqlite 文件库）
    run_id = asyncio.run(_seed())
    replay = _parse_frames(client.post(
        "/api/chat/asks", json={"resume_run_id": run_id}, headers=ACTOR,
    ).text)
    assert [name for name, _ in replay] == ["session", "verdict", "replay_truncated"]
    assert replay[-1][1]["message"] == d.REPLAY_CANCELLED_MESSAGE


def test_run_recovery_unknown_run_is_404(env: Any) -> None:
    """run 恢复：run 不存在＝无可恢复对象——开流前 404（A1 错误码草案；
    P0-08「run 存在性不校验」判据随真恢复退役）。"""
    client = env[0]
    resp = client.post(
        "/api/chat/asks", json={"resume_run_id": "run-missing"}, headers=ACTOR,
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "chat_run_not_found"


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


def _frames_by_name(frames: list[tuple[str, dict[str, Any]]]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for name, data in frames:
        out.setdefault(name, []).append(data)
    return out


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
    client, _manager = env
    resp = client.post("/api/chat/asks", json={"question": "渤海油田产量"}, headers=ACTOR)
    assert resp.status_code == 200
    logs = client.get(
        "/api/security/audit-logs", params={"action": "chat.ask.received"}, headers=ACTOR,
    )
    assert logs.status_code == 200
    assert logs.json()["total"] >= 1


def test_endpoint_2_sessions_list(env: Any) -> None:
    """A1 端点 2（P1-11 真接线）：空列表→ask 后有会话（title＝首问，updated_at
    倒序）；身份隔离——他人会话不出列。"""
    client, _manager = env
    empty = client.get("/api/chat/sessions", headers=ACTOR)
    assert empty.status_code == 200
    assert empty.json() == {"items": []}

    client.post("/api/chat/asks", json={"question": "渤海油田产量"}, headers=ACTOR)
    client.post("/api/chat/asks", json={"question": "躺井是什么意思"}, headers=ACTOR)
    listed = client.get("/api/chat/sessions", headers=ACTOR).json()["items"]
    assert [item["title"] for item in listed] == ["躺井是什么意思", "渤海油田产量"]  # 倒序
    assert listed[0]["id"].startswith("sess-")
    assert listed[0]["group"] is None and listed[0]["scenario_id"] is None  # 场景注册表随其票
    assert "T" in listed[0]["updated_at"]  # isoformat 展示串

    other = client.get(
        "/api/chat/sessions", headers={"X-Dev-User": "xiaoli"}
    ).json()["items"]
    assert other == []  # 身份桩隔离（会话归属 user_id）


def test_endpoint_6_assets_projection_and_filters(env: Any) -> None:
    """A1 端点 6（P1-11 真接线）：各注册表现取投影（token 结晶体）＋q/type 筛
    ＋type 越界 400。"""
    client, _manager = env
    listed = client.get("/api/chat/assets", headers=ACTOR)
    assert listed.status_code == 200
    items = listed.json()["items"]
    types = {item["type"] for item in items}
    assert {"指标卡", "术语", "FAQ", "工作流"} <= types
    metric = next(item for item in items if item["type"] == "指标卡")
    assert metric == {"type": "指标卡", "name": "产量完成率", "token": "指标卡·产量完成率"}
    faq = next(item for item in items if item["type"] == "FAQ")
    assert faq["token"] == "FAQ·N-02 井是什么时候投产的？"

    filtered = client.get(
        "/api/chat/assets", params={"q": "产量完成率"}, headers=ACTOR
    ).json()["items"]
    assert filtered and all("产量完成率" in item["name"] for item in filtered)

    typed = client.get(
        "/api/chat/assets", params={"type": "术语"}, headers=ACTOR
    ).json()["items"]
    assert typed and {item["type"] for item in typed} == {"术语"}

    bad = client.get("/api/chat/assets", params={"type": "报表"}, headers=ACTOR)
    assert bad.status_code == 400
    assert bad.json()["code"] == "chat_param_invalid"


def test_endpoint_6_assets_unregistered_actor_401(env: Any) -> None:
    """非五角色键 → 401（身份闸同 asks——CurrentActor 统一依赖）；缺头落默认
    角色不 401（00 §2.4，asks 同判例）。"""
    client, _manager = env
    assert client.get(
        "/api/chat/assets", headers={"X-Dev-User": "nobody"}
    ).status_code == 401
    assert client.get(
        "/api/chat/sessions", headers={"X-Dev-User": "nobody"}
    ).status_code == 401
    assert client.get("/api/chat/assets").status_code == 200  # 缺头＝默认角色
