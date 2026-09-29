"""security 领域单测——身份桩三态（有头/无头/非法值）、组闸、审计四槽 digest。

合同锚：00 §2.3/2.4（身份桩与 401 语义）、§9.1（五角色/who 格式，照抄
roles.js）、§8.1（四槽/digest）、§2.3（403＝直调越权）；docs/prd.md 拍板
默认角色＝阿强。
"""

import re
from datetime import datetime

import pytest

from app.domains.security import (
    DEFAULT_ROLE_KEY,
    ROLE_REGISTRY,
    AuditRow,
    ForbiddenError,
    UnauthenticatedError,
    audit_digest,
    authorize,
    resolve_actor,
)
from app.infra.clock import freeze
from app.infra.crypto import sm3_digest

# ---------- 身份桩：有头 ----------


@pytest.mark.parametrize("key", sorted(ROLE_REGISTRY))
def test_resolve_actor_with_each_frozen_role_key(key: str) -> None:
    actor = resolve_actor(key)
    assert actor.user_id == key
    assert actor.display == ROLE_REGISTRY[key].display  # label 全名照抄 roles.js（00 §9.1）
    assert actor.who == actor.display  # who 槽＝label 全名


def test_resolve_actor_strips_surrounding_whitespace() -> None:
    actor = resolve_actor("  xiaoli ")
    assert actor.user_id == "xiaoli"
    assert actor.display == "小李 · 地质/质检"


# ---------- 身份桩：无头（缺省落默认角色——不 401） ----------


@pytest.mark.parametrize("absent", [None, "", "   "])
def test_resolve_actor_missing_header_falls_to_default_role(absent: str | None) -> None:
    actor = resolve_actor(absent)
    assert DEFAULT_ROLE_KEY == "aqiang"  # docs/prd.md 拍板：默认角色＝阿强
    assert actor.user_id == "aqiang"
    assert actor.display == "阿强 · 平台运维"


# ---------- 身份桩：非法值（401＝身份解析失败，00 §2.3） ----------


def test_resolve_actor_unknown_key_raises_unauthenticated() -> None:
    with pytest.raises(UnauthenticatedError, match="身份解析失败") as exc_info:
        resolve_actor("ghost")
    assert "ghost" in str(exc_info.value)  # 人话原因带原值（排障）


def test_resolve_actor_keys_match_exactly_no_case_folding() -> None:
    # 五角色键为 roles.js 冻结值——不做人名大小写归一（避免静默放宽身份面）。
    with pytest.raises(UnauthenticatedError):
        resolve_actor("Xiaoli")


# ---------- 页面组闸（00 §2.3 403＝直调越权；规则照抄 roles.js MENU 组级 roles） ----------


def test_authorize_settings_group_is_aqiang_only() -> None:
    authorize(resolve_actor("aqiang"), "设置中心")  # 不抛即过
    for key in ("laowang", "xiaoli", "zhuren", "shixi"):
        with pytest.raises(ForbiddenError, match="设置中心"):
            authorize(resolve_actor(key), "设置中心")


def test_authorize_group_membership_frozen_from_roles_js() -> None:
    # 工作台/报告库/指标与术语/平台：组级 roles 缺省＝全员可见。
    for group in ("工作台", "报告库", "指标与术语", "平台"):
        for key in ROLE_REGISTRY:
            authorize(resolve_actor(key), group)  # 不抛即过
    # 考核与质量：roles: ['xiaoli', 'aqiang', 'zhuren']。
    for key in ("xiaoli", "aqiang", "zhuren"):
        authorize(resolve_actor(key), "考核与质量")
    for key in ("laowang", "shixi"):
        with pytest.raises(ForbiddenError):
            authorize(resolve_actor(key), "考核与质量")


# ---------- 审计四槽 digest（00 §8.1；SM3 永不落正文——00 §11） ----------


def _row(**overrides: object) -> AuditRow:
    base: dict[str, object] = {
        "who": "小李 · 地质/质检",
        "action": "kb.library_config.saved",
        "content": "库配置保存（下次入库定型）",
    }
    base.update(overrides)
    return AuditRow(**base)  # type: ignore[arg-type]


def test_audit_digest_deterministic_hex64_and_slot_sensitive() -> None:
    with freeze("2026-09-29T10:00:00"):
        row = _row()
        first = audit_digest(row)
        assert first == audit_digest(_row())  # 同四槽同指纹（确定性）
        assert re.fullmatch(r"[0-9a-f]{64}", first)  # SM3 hex 64（99 §1.7.3 应用层计算）
        assert audit_digest(_row(who="系统")) != first  # 任一槽变即变
        assert audit_digest(_row(action="x")) != first
        assert audit_digest(_row(content="y")) != first
        assert audit_digest(_row(at=datetime(2026, 9, 29, 10, 0, 1))) != first


def test_audit_digest_canonical_is_time_who_action_content() -> None:
    at = datetime(2026, 9, 29, 10, 0, 0)
    row = _row(at=at)
    canonical = f"2026-09-29T10:00:00|{row.who}|{row.action}|{row.content}"
    assert audit_digest(row) == sm3_digest(canonical)  # 口径见 domain.audit_digest


def test_audit_row_resolved_at_defaults_to_clock() -> None:
    with freeze("2026-09-29T09:30:00"):
        assert _row().resolved_at() == datetime(2026, 9, 29, 9, 30, 0)  # B14 唯一时钟


def test_audit_row_explicit_at_wins_over_clock() -> None:
    explicit = datetime(2026, 1, 1, 0, 0, 0)
    with freeze("2026-09-29T09:30:00"):
        assert _row(at=explicit).resolved_at() == explicit  # 回放/测试显式时间槽优先
