"""E2 /api/quality 路由族 API 测试——九端点全往返：错误包/权限预埋/B12 审计/壳 501。

装配：sqlite 底座＋真 QualityService＋真 SecurityService（dependency_overrides
替换服务定位，不触 main.py lifespan；retrieval API 测试同款）；rescan 执行缝
按用例替换 override（替身纪律：只许测试替身）。红线：本域零 LLM 调用。
合同锚：E2-数据质量台.md v0.5（端点形状/错误码/行为约定 5）、00 §3（错误包）。
"""

from collections.abc import AsyncIterator
from typing import Any, NamedTuple

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_quality, get_security
from app.api.errors import install_error_handlers
from app.api.quality import router as quality_router
from app.domains.dataops.quality import (
    RESCAN_GREEN_NOTE,
    QualityService,
)
from app.domains.dataops.quality.domain import build_dedupe_key
from app.domains.dataops.quality.store import QuarantineRow, ensure_quality_tables
from app.domains.security import SecurityService
from app.domains.security.store import ensure_audit_table
from app.infra.clock import freeze
from app.infra.db import ConnectionManager, DatabaseSpec
from tests.domains.dataops.quality.conftest import (
    add_issue,
    add_quarantine,
    add_water_line,
    green_executor,
    seed_rule,
)

AQIANG_HEADERS: dict[str, str] = {"X-Dev-User": "aqiang"}
DAY = "2026-09-14"


class Env(NamedTuple):
    client: TestClient
    db_path: str
    manager: ConnectionManager
    app: FastAPI


async def _seed_fixture(manager: ConnectionManager) -> None:
    """夹具期直插（manager 所在 loop）——池连接 dispose 后由请求 loop 重建。"""
    await seed_rule(
        manager, 5, kind="超范围", crit="越界即 fail；矛盾行清单制", action="告警"
    )
    await seed_rule(
        manager, 8, kind="写法不统一", crit="映射表全命中", action="隔离", autofix=True
    )
    # 13-20 仅登记档代表行（值照抄迁移 0015 种子——零发明；守卫用例消费）
    await seed_rule(
        manager, 13, kind="引用完整",
        rule="引用的编号要能在关联的表里找到对应记录",
        crit="详见规则库总册", enabled=False, action="—（总册）",
    )
    await add_issue(
        manager, id="p8", lane=0, rule_no=8, hit_count=1,
        dedupe_key=build_dedupe_key(8, "EQUIP-01", DAY),
        title="规则 8 · 停机原因码旧码未映射",
        desc="equip_status 旧码 R3 未按映射表换成 BELT",
        owner="责任：作业区资料员",
    )
    await add_issue(
        manager, id="p5", lane=1, rule_no=5, hit_count=1,
        dedupe_key=build_dedupe_key(5, "N-05", DAY),
    )
    await add_issue(
        manager, id="p10", lane=3, rule_no=5, hit_count=1,
        dedupe_key=build_dedupe_key(5, "N-10", DAY),
        close_note="告警类规则核实为真实关井——不涉及隔离行，记录原因后关闭",
    )
    qrow = await add_quarantine(
        manager, batch_id="QT-20260914-01", rule_no=8, action="隔离",
        loc="设备状态 equip_status",
        payload={"code": "R3", "note": "停机原因旧码 R3 未按映射表换成 BELT"},
    )
    async with manager.session() as session:
        row = await session.get(QuarantineRow, qrow.id)
        assert row is not None
        row.issue_id = "p8"
    await add_quarantine(
        manager, batch_id="b-20260913-T2", rule_no=5, action="整批拒收",
        loc="批次 b-20260913-T2", payload={"rows": 120},
    )
    await add_water_line(manager, "原始层", "2026-09-14")
    await add_water_line(manager, "清洗层", "2026-09-14")
    await add_water_line(manager, "汇总层", "2026-09-11")


@pytest.fixture
async def env(tmp_path: Any) -> AsyncIterator[Env]:
    db_path = str(tmp_path / "quality-api.db")
    spec = DatabaseSpec(
        name="primary", role="primary", driver="sqlite", host="", port=0,
        database=db_path, user="", password="", pool_size=2, max_overflow=1,
    )
    manager = ConnectionManager([spec])
    await ensure_quality_tables(manager.engine())
    await ensure_audit_table(manager.engine())
    await _seed_fixture(manager)
    # 夹具期连接建于 pytest-asyncio 夹具循环，TestClient 每请求独立 portal
    # 循环——跨循环复用池连接必炸（wells PG 测试同款处置：先 dispose 弃池）。
    await manager.dispose()
    test_app = FastAPI()
    install_error_handlers(test_app)
    test_app.include_router(quality_router)
    test_app.dependency_overrides[get_quality] = lambda: QualityService(manager)
    test_app.dependency_overrides[get_security] = lambda: SecurityService(manager)
    with TestClient(test_app) as test_client:
        yield Env(client=test_client, db_path=db_path, manager=manager, app=test_app)
    await manager.dispose()


def _audit_rows(db_path: str) -> list[tuple[str, str, str]]:
    """audit_log 全行（stdlib sqlite3 直读——retrieval API 测试同款绕行）。"""
    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(
            "SELECT who, action, content FROM audit_log ORDER BY id"
        ).fetchall()
    finally:
        conn.close()


def _transition_rows(db_path: str, issue_id: str) -> list[tuple[int, int, int, str]]:
    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(
            "SELECT seq, from_lane, to_lane, operator FROM quality_issue_transition "
            "WHERE issue_id = ? ORDER BY seq",
            (issue_id,),
        ).fetchall()
    finally:
        conn.close()


# ---------- (a) 规则投影与启停（读面反映＋B12 审计行） ----------


class TestRulesEndpoints:
    def test_list_rules_projects_auto_fix_camel_case(self, env: Env) -> None:
        body: dict[str, Any] = env.client.get(
            "/api/quality/rules", headers=AQIANG_HEADERS
        ).json()
        assert [r["no"] for r in body["items"]] == [5, 8, 13]
        r8 = body["items"][1]
        # 合同端点 1 DTO 逐字段（autoFix 冻结 camelCase——00 §14-R1 唯一例外键）
        assert r8 == {
            "no": 8, "kind": "写法不统一", "rule": "规则原文",
            "crit": "映射表全命中", "enabled": True, "action": "隔离", "autoFix": True,
        }

    def test_toggle_rule_roundtrip_and_audit_row(self, env: Env) -> None:
        resp = env.client.patch(
            "/api/quality/rules/8", json={"enabled": False}, headers=AQIANG_HEADERS
        )
        assert resp.status_code == 200
        assert resp.json() == {"no": 8, "enabled": False}
        rules = env.client.get(
            "/api/quality/rules", headers=AQIANG_HEADERS
        ).json()["items"]
        assert [r["enabled"] for r in rules] == [True, False, False]  # 读面反映
        assert _audit_rows(env.db_path) == [(
            "阿强 · 平台运维", "quality.rule_toggled",
            "质检规则 8 停用（停用＝质检任务跳过，规则保留不删）",
        )]

    def test_toggle_unknown_rule_404(self, env: Env) -> None:
        resp = env.client.patch(
            "/api/quality/rules/99", json={"enabled": False}, headers=AQIANG_HEADERS
        )
        assert resp.status_code == 404
        assert resp.json()["code"] == "quality_rule_not_found"

    def test_toggle_bad_body_400(self, env: Env) -> None:
        resp = env.client.patch(
            "/api/quality/rules/8", json={"on": True}, headers=AQIANG_HEADERS
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == "request_invalid"

    def test_toggle_registered_only_enable_rejected_422(self, env: Env) -> None:
        # 档位守卫（rev F1 修复）：13-20 仅登记档置 enabled=true → 422 拒启用
        # （防「已启用但 V1 任务只跑 1-12 恒跳过」静默矛盾——执行通道接通后放开）
        resp = env.client.patch(
            "/api/quality/rules/13", json={"enabled": True}, headers=AQIANG_HEADERS
        )
        assert resp.status_code == 422
        body = resp.json()
        assert body["code"] == "quality_rule_registered_only"
        assert "仅登记规则未实施" in body["message"]
        assert "不可启用" in body["message"]
        # 拒绝＝无写发生（读面仍停用）＋失败路径不达审计行（B12 先例同口径）
        rules = env.client.get(
            "/api/quality/rules", headers=AQIANG_HEADERS
        ).json()["items"]
        assert [r["enabled"] for r in rules] == [True, True, False]
        assert _audit_rows(env.db_path) == []

    def test_registered_only_read_face_intact_and_disable_allowed(self, env: Env) -> None:
        # 读面不遮蔽：仅登记档照常在列（0015 种子值原样投影）
        rules = env.client.get(
            "/api/quality/rules", headers=AQIANG_HEADERS
        ).json()["items"]
        assert rules[2] == {
            "no": 13, "kind": "引用完整",
            "rule": "引用的编号要能在关联的表里找到对应记录",
            "crit": "详见规则库总册", "enabled": False,
            "action": "—（总册）", "autoFix": False,
        }
        # enabled=false（停用回登记态）恒放行——幂等停用照收
        resp = env.client.patch(
            "/api/quality/rules/13", json={"enabled": False}, headers=AQIANG_HEADERS
        )
        assert resp.status_code == 200
        assert resp.json() == {"no": 13, "enabled": False}


# ---------- (b) 五态流转全路径（仅复核登记/关闭守卫 422/终态 409/rescan） ----------


def _walk(client: TestClient, issue_id: str, times: int) -> list[dict[str, Any]]:
    return [
        client.post(
            f"/api/quality/issues/{issue_id}/transitions", json={},
            headers=AQIANG_HEADERS,
        ).json()
        for _ in range(times)
    ]


class TestTransitionsEndpoint:
    def test_full_path_to_review_then_close_blocked_422(self, env: Env) -> None:
        bodies = _walk(env.client, "p8", 3)
        assert [b["lane"] for b in bodies] == [1, 2, 3]
        assert [b["state"] for b in bodies] == ["认领", "整改", "复核"]
        assert all(b["verify"] is None for b in bodies)  # 推进「复核」仅登记待复扫
        # 关闭守卫 422（合同端点 7 冻结状态码——verify/close_note 二者皆无）
        resp = env.client.post(
            "/api/quality/issues/p8/transitions", json={}, headers=AQIANG_HEADERS
        )
        assert resp.status_code == 422
        assert resp.json()["code"] == "quality_close_not_verified"

    def test_terminal_closed_rejected_409(self, env: Env) -> None:
        _walk(env.client, "p10", 4)  # close_note 免修路径走到关闭
        resp = env.client.post(
            "/api/quality/issues/p10/transitions", json={}, headers=AQIANG_HEADERS
        )
        assert resp.status_code == 409
        assert resp.json()["code"] == "quality_issue_state"

    def test_rescan_lane_guard_409_then_deferred_501_at_review(
        self, env: Env
    ) -> None:
        resp = env.client.post(
            "/api/quality/issues/p8/transitions", json={"action": "rescan"},
            headers=AQIANG_HEADERS,
        )
        assert resp.status_code == 409  # 分发态非复核——仅复核态可复扫
        assert resp.json()["code"] == "quality_issue_state"
        _walk(env.client, "p8", 3)
        resp = env.client.post(
            "/api/quality/issues/p8/transitions", json={"action": "rescan"},
            headers=AQIANG_HEADERS,
        )
        # 复核态复扫——执行缝缺省未接＝501 诚实壳（不 mock 假复扫结论）
        assert resp.status_code == 501
        assert resp.json()["code"] == "quality_task_channel_deferred"

    def test_rescan_with_executor_backfills_verify_and_audit(self, env: Env) -> None:
        # 注入替身执行器（M-05b 接通后同形——B9 缝只见 callable）
        env.app.dependency_overrides[get_quality] = lambda: QualityService(
            env.manager, rescan_executor=green_executor()
        )
        _walk(env.client, "p8", 3)
        resp = env.client.post(
            "/api/quality/issues/p8/transitions", json={"action": "rescan"},
            headers=AQIANG_HEADERS,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        # 复扫不是流转——lane 不变；verify 回填（全绿哨兵＋修正批次标识）
        assert body == {
            "id": "p8", "lane": 3, "state": "复核",
            "verify": {"batch": "批次 20260922-T1", "note": RESCAN_GREEN_NOTE},
        }
        assert _transition_rows(env.db_path, "p8") == [  # 复扫不追加流转行（三行＝流转）
            (1, 0, 1, "阿强 · 平台运维"),
            (2, 1, 2, "阿强 · 平台运维"),
            (3, 2, 3, "阿强 · 平台运维"),
        ]
        assert _audit_rows(env.db_path)[-1] == (
            "阿强 · 平台运维", "quality.issue_rescanned",
            f"问题单 p8 复扫（复核态人工触发，lane 不变）：{RESCAN_GREEN_NOTE}",
        )
        # 复扫全绿后关闭放行
        resp = env.client.post(
            "/api/quality/issues/p8/transitions", json={}, headers=AQIANG_HEADERS
        )
        assert resp.status_code == 200
        assert resp.json()["lane"] == 4

    def test_transition_writes_trace_and_audit_rows(self, env: Env) -> None:
        _walk(env.client, "p8", 2)
        assert _transition_rows(env.db_path, "p8") == [
            (1, 0, 1, "阿强 · 平台运维"),
            (2, 1, 2, "阿强 · 平台运维"),
        ]
        actions = [row[1] for row in _audit_rows(env.db_path)]
        assert actions == ["quality.issue_transitioned", "quality.issue_transitioned"]

    def test_unknown_issue_404_and_unknown_action_400(self, env: Env) -> None:
        resp = env.client.post(
            "/api/quality/issues/p99/transitions", json={}, headers=AQIANG_HEADERS
        )
        assert resp.status_code == 404
        assert resp.json()["code"] == "quality_issue_not_found"
        resp = env.client.post(
            "/api/quality/issues/p8/transitions", json={"action": "rollback"},
            headers=AQIANG_HEADERS,
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == "quality_param_invalid"


# ---------- 端点 6：问题单列表（lanes/筛选/分页预留/ai_note 投影/qrows） ----------


class TestIssuesEndpoint:
    def test_list_shape_filters_and_pagination(self, env: Env) -> None:
        body: dict[str, Any] = env.client.get(
            "/api/quality/issues", headers=AQIANG_HEADERS
        ).json()
        assert body["lanes"] == ["分发", "认领", "整改", "复核", "关闭"]
        assert body["total"] == 3
        assert body["page"] == 1 and body["page_size"] == 20  # 分页预留回显（v0.5）
        p8, p5, p10 = body["items"]  # lane 升序＋id 序（0→1→3）
        assert p8["id"] == "p8" and p8["lane"] == 0 and p8["rule_no"] == 8
        assert p8["hit_count"] == 1
        assert p8["qrows"] == [{
            "loc": "设备状态 equip_status",
            "note": "停机原因旧码 R3 未按映射表换成 BELT",
        }]
        # ai_note＝规则判据说明投影（v0.5 降级——零 LLM）
        assert p8["ai_note"] == "规则 8 判据：映射表全命中"
        assert p5["ai_note"] == "规则 5 判据：越界即 fail；矛盾行清单制"
        assert p5["qrows"] == []  # 告警类规则无隔离行
        assert p5["verify"] is None and p5["close_note"] is None
        assert p10["close_note"] == (
            "告警类规则核实为真实关井——不涉及隔离行，记录原因后关闭"
        )

        by_lane = env.client.get(
            "/api/quality/issues", params={"lane": 3}, headers=AQIANG_HEADERS
        ).json()
        assert [i["id"] for i in by_lane["items"]] == ["p10"] and by_lane["total"] == 1
        by_rule = env.client.get(
            "/api/quality/issues", params={"rule_no": 8}, headers=AQIANG_HEADERS
        ).json()
        assert [i["id"] for i in by_rule["items"]] == ["p8"]
        paged = env.client.get(
            "/api/quality/issues", params={"pageSize": 1}, headers=AQIANG_HEADERS
        ).json()
        assert [i["id"] for i in paged["items"]] == ["p8"] and paged["total"] == 3

    def test_lane_out_of_range_400(self, env: Env) -> None:
        resp = env.client.get(
            "/api/quality/issues", params={"lane": 9}, headers=AQIANG_HEADERS
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == "request_invalid"


# ---------- (e) 任务端点壳（3/4/5——501 诚实注记，不 mock 假任务） ----------


class TestTaskShells:
    @pytest.mark.parametrize(
        ("method", "path"),
        [("post", "/api/quality/tasks"), ("get", "/api/quality/tasks/QT-20260928-01"),
         ("get", "/api/quality/tasks")],
    )
    def test_shells_501_deferred(self, env: Env, method: str, path: str) -> None:
        resp = getattr(env.client, method)(path, headers=AQIANG_HEADERS)
        assert resp.status_code == 501
        body = resp.json()
        assert body["code"] == "quality_task_channel_deferred"
        assert "执行通道随数据面质检重建接通" in body["message"]


# ---------- (c) 端点 8：水位 T-1 判定 ----------


class TestFreshnessEndpoint:
    def test_three_tiers_judged_server_side(self, env: Env) -> None:
        with freeze("2026-09-15 08:00:00"):
            body: dict[str, Any] = env.client.get(
                "/api/quality/freshness", headers=AQIANG_HEADERS
            ).json()
        # 合同端点 8 示例同形：汇总层展示名「汇总层（问数用）」＋落后 3 天 · 超期
        assert body == {
            "items": [
                {"layer": "原始层", "to": "到 2026-09-14", "promise": "T-1",
                 "tag": "达标（承诺 T-1）", "color": "green"},
                {"layer": "清洗层", "to": "到 2026-09-14", "promise": "T-1",
                 "tag": "达标（承诺 T-1）", "color": "green"},
                {"layer": "汇总层（问数用）", "to": "到 2026-09-11", "promise": "T-1",
                 "tag": "落后 3 天 · 超期", "color": "gold"},
            ]
        }


# ---------- (d) 端点 9：隔离区过滤 ----------


class TestQuarantineEndpoint:
    def test_filters_and_shape(self, env: Env) -> None:
        body: dict[str, Any] = env.client.get(
            "/api/quality/quarantine", headers=AQIANG_HEADERS
        ).json()
        assert len(body["items"]) == 2
        first, second = body["items"]
        assert first == {
            "batch_id": "QT-20260914-01", "rule_no": 8, "action": "隔离",
            "loc": "设备状态 equip_status",
            "payload": {"code": "R3", "note": "停机原因旧码 R3 未按映射表换成 BELT"},
            "issue_id": "p8", "created_at": first["created_at"],
        }
        assert second["action"] == "整批拒收" and second["issue_id"] is None
        by_issue = env.client.get(
            "/api/quality/quarantine", params={"issue_id": "p8"}, headers=AQIANG_HEADERS
        ).json()
        assert [i["rule_no"] for i in by_issue["items"]] == [8]
        by_batch = env.client.get(
            "/api/quality/quarantine", params={"batch_id": "b-20260913-T2"},
            headers=AQIANG_HEADERS,
        ).json()
        assert [i["rule_no"] for i in by_batch["items"]] == [5]
        by_both = env.client.get(
            "/api/quality/quarantine",
            params={"batch_id": "QT-20260914-01", "rule_no": 8},
            headers=AQIANG_HEADERS,
        ).json()
        assert len(by_both["items"]) == 1
        empty = env.client.get(
            "/api/quality/quarantine", params={"issue_id": "d9"}, headers=AQIANG_HEADERS
        ).json()
        assert empty == {"items": []}
