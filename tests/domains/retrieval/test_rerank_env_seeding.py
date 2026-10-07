"""retrieval 服务单测——rerank 档位环境级播种三态（DE-10：env 仅播种，DB 行恒胜）。

背景：rerank 档位存 DB 配置行，换新库（无配置行）静默回落默认 fast 已实证两次
（Q8 云上全量误跑 fast；Q9 前重播种 #CFG-20261007-01）。本票语义定案：

- 无行＋env 在位 → 以 env 值建种子行（其余节＝合同默认，行格式零变化）；
- 无行＋env 缺省 → 现状行为零变化（首读种子仍默认 fast）；
- 有行＋env 在位 → DB 胜（跳过播种——运行中经 D2 变更单改档后重启不丢）；
- env 值非法 → RerankTierEnvError 拒绝启动（main lifespan 不捕获＝应用起不来，
  禁静默回落——M-01 反静默降级病灶同口径）。

sqlite 底座（tests/domains/retrieval/conftest.py——内存形态存储，不打真库）；
播种点＝main.py lifespan 装配缝（app.state.retrieval 装配后调
seed_rerank_tier_from_env，本文件测域层三态判定单点，装配接线由该单点保证）。
"""

from typing import Any

import pytest

from app.domains.retrieval import (
    RerankTierEnvError,
    default_config_dict,
    parse_rerank_tier,
    rerank_seed_config_dict,
)
from app.domains.retrieval.domain import RERANK_TIER_ENV
from app.infra.db import ConnectionManager
from tests.domains.retrieval.conftest import version_rows


async def _effective_rerank(service: Any) -> str:
    return (await service.effective_config()).rerank


class TestEnvSeedingThreeStates:
    async def test_no_row_with_env_seeds_tier(
        self, service: Any, retrieval_db: ConnectionManager
    ) -> None:
        """态一：无行＋env=llm → 以 env 值建行，生效档位 llm。"""
        assert await service.seed_rerank_tier_from_env("llm") == "llm"
        assert await _effective_rerank(service) == "llm"
        rows = await version_rows(retrieval_db)
        assert [r.version_no for r in rows] == ["v1"]  # 种子行形状（非变更版本推进）
        assert rows[0].config["rerank"] == "llm"
        assert rows[0].via is None  # 种子非变更产生（与首读种子同构——行格式零变化）

    async def test_no_row_without_env_keeps_current_behavior(self, service: Any) -> None:
        """态二：无行＋env 缺省 → 无操作，现状零变化（首读种子默认 fast）。"""
        assert await service.seed_rerank_tier_from_env(None) is None
        assert await _effective_rerank(service) == "fast"

    async def test_row_present_env_db_wins(
        self, service: Any, retrieval_db: ConnectionManager
    ) -> None:
        """态三：有行＋env 在位 → DB 胜（跳过播种，版本轴零新行）。"""
        await service.effective_config()  # 先落默认 fast 种子行
        assert await service.seed_rerank_tier_from_env("llm") is None
        assert await _effective_rerank(service) == "fast"  # DB 行恒胜
        rows = await version_rows(retrieval_db)
        assert [r.version_no for r in rows] == ["v1"]  # 跳过播种＝零写入

    async def test_changed_row_survives_restart_with_env(
        self, service: Any, retrieval_db: ConnectionManager
    ) -> None:
        """运行中变更单改档后带 env 重启不丢（DB 行恒胜的票面原话语义）。"""
        await service.effective_config()
        await service.submit_change_request(
            {"rerank": "llm"}, updated_by="阿强 · 平台运维"
        )
        assert await _effective_rerank(service) == "llm"
        assert await service.seed_rerank_tier_from_env("fast") is None  # 跳过
        assert await _effective_rerank(service) == "llm"  # 改动不回退
        assert [r.version_no for r in await version_rows(retrieval_db)] == ["v1", "v2"]

    async def test_seeded_row_other_sections_are_contract_defaults(
        self, service: Any
    ) -> None:
        """播种行只定 rerank，其余节＝合同默认（DB 配置行格式零变化）。"""
        await service.seed_rerank_tier_from_env("llm")
        snapshot = await service.effective_config()
        expected = default_config_dict()
        expected["rerank"] = "llm"
        assert snapshot.sections_dict() == expected

    async def test_seed_then_first_read_is_idempotent(
        self, service: Any, retrieval_db: ConnectionManager
    ) -> None:
        """env 播种后首读不再重复种子（ensure_seeded 见行即返——幂等不覆盖）。"""
        await service.seed_rerank_tier_from_env("llm")
        await service.effective_config()
        await service.effective_config()
        assert [r.version_no for r in await version_rows(retrieval_db)] == ["v1"]
        assert await _effective_rerank(service) == "llm"


class TestInvalidEnvRejected:
    async def test_invalid_value_raises_and_writes_nothing(
        self, service: Any, retrieval_db: ConnectionManager
    ) -> None:
        """非法 env 值拒绝启动（抛错不静默回落）且零写入。"""
        with pytest.raises(RerankTierEnvError, match="turbo"):
            await service.seed_rerank_tier_from_env("turbo")
        assert await version_rows(retrieval_db) == []  # 拒绝启动路径零残留

    async def test_error_is_value_error(
        self, service: Any
    ) -> None:
        """RerankTierEnvError 是 ValueError 子类（拒启动语义＝装配异常上抛）。"""
        with pytest.raises(ValueError):
            parse_rerank_tier("ultra")

    async def test_all_contract_tiers_pass(self, service: Any) -> None:
        """合法域＝合同枚举 RERANK_TIERS 同源（compound 属 DB 域内合法档）。"""
        for tier in ("fast", "llm", "compound"):
            assert parse_rerank_tier(tier) == tier
        assert rerank_seed_config_dict("compound")["rerank"] == "compound"


def test_env_var_name_constant() -> None:
    """变量名单源（main 装配缝与 compose 注入同名——防止两处漂移）。"""
    assert RERANK_TIER_ENV == "RERANK_TIER"
