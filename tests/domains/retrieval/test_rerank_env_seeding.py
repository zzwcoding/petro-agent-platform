"""retrieval 服务单测——rerank 档位环境级播种三态（DE-10：env 仅播种，DB 行恒胜）。

背景：rerank 档位存 DB 配置行，换新库（无配置行）静默回落默认 fast 已实证两次
（Q8 云上全量误跑 fast；Q9 前重播种 #CFG-20261007-01）。本票语义定案：

- 无行＋env 在位 → 以 env 值建种子行（其余节＝合同默认，行格式零变化）；
- 无行＋env 缺省 → 现状行为零变化（首读种子仍默认 fast）；
- 有行＋env 在位 → DB 胜（跳过播种——运行中经 D2 变更单改档后重启不丢）；
- env 值非法 → RerankTierEnvError 拒绝启动（main lifespan 不捕获＝应用起不来，
  禁静默回落——M-01 反静默降级病灶同口径）。

测试两层（FX-08 起）：域层三态判定单点（sqlite 底座，
tests/domains/retrieval/conftest.py——文件形态存储，不打真库）＋lifespan
接线级（TestLifespanWiring——monkeypatch.setenv＋with TestClient(app) 真穿
app/main.py 播种段；域层单点只保证语义，保证不了接线存在性——审查
R2-02 裁决）。
"""

import logging
from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.main as app_main
from app.domains.retrieval import (
    RERANK_TIERS,
    RerankTierEnvError,
    RetrievalService,
    default_config_dict,
    parse_rerank_tier,
    rerank_seed_config_dict,
)
from app.domains.retrieval.domain import RERANK_TIER_ENV
from app.infra.db import ConnectionManager, DatabaseSpec
from app.main import app
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
        """合法域＝合同枚举 RERANK_TIERS 同源（遍历常量——扩档即自动覆盖，
        R2-06：不硬编码三档；compound 属 DB 域内合法档）。"""
        for tier in RERANK_TIERS:
            assert parse_rerank_tier(tier) == tier
            assert rerank_seed_config_dict(tier)["rerank"] == tier


def test_env_var_name_constant() -> None:
    """变量名单源（main 装配缝与 compose 注入同名——防止两处漂移）。"""
    assert RERANK_TIER_ENV == "RERANK_TIER"


class TestLifespanWiring:
    """lifespan 接线级测试（FX-08——R2-02 修复）：真穿 app/main.py 播种段。

    票内替身定案（边界红线：生产代码零改动）：播种点在 main.lifespan 偏后段
    （verify_midplatform_route＋十二个 ensure_*_tables＋seed_demo_if_empty 之后
    ——顺序不许为测试改）。依赖链处理＝其余全照生产代码跑（sqlite 底座：各
    ensure_* 建表方言守卫齐备、列类型带 sqlite 变体、服务/存储/图/LLM 构造均
    懒建连），只替两处真外部依赖：
    ①app.main.load_database_specs → tmp_path sqlite 规格（config/database.yaml
      真文件指向 localhost PG，测试环境无 PG）；
    ②ConnectionManager.verify_midplatform_route → no-op——sqlite 上写探针
      （CREATE TEMP TABLE）必然成功＝「未被拒」恒拒启动，该中台只读校验对
      sqlite 底座无真实语义，替身是该例可替身性的定案（播种段在其后）。
    断言读库走独立 ConnectionManager 重开同一 sqlite 文件（TestClient 的
    lifespan 在自持事件循环里装配并 dispose，跨循环不复用其引擎）。
    """

    @staticmethod
    def _sqlite_specs(tmp_path: Any) -> list[DatabaseSpec]:
        return [
            DatabaseSpec(
                name="primary",
                role="primary",
                driver="sqlite",
                host="",
                port=0,
                database=str(tmp_path / "lifespan.db"),
                user="",
                password="",
                pool_size=2,
                max_overflow=1,
            )
        ]

    @pytest.fixture
    def lifespan_sqlite(self, monkeypatch: Any, tmp_path: Any) -> None:
        async def _skip_probe(_self: ConnectionManager) -> None:
            return None

        monkeypatch.setattr(
            app_main, "load_database_specs", lambda: self._sqlite_specs(tmp_path)
        )
        monkeypatch.setattr(ConnectionManager, "verify_midplatform_route", _skip_probe)

    async def _version_rows_after_startup(self, tmp_path: Any) -> list[Any]:
        fresh = ConnectionManager(self._sqlite_specs(tmp_path))
        try:
            return await version_rows(fresh)
        finally:
            await fresh.dispose()

    async def test_invalid_env_rejects_startup(
        self, lifespan_sqlite: None, monkeypatch: Any
    ) -> None:
        """非法值 → 进入 with（触发 lifespan）即抛 RerankTierEnvError——拒绝启动。"""
        monkeypatch.setenv(RERANK_TIER_ENV, "turbo")
        with pytest.raises(RerankTierEnvError, match="turbo"):
            with TestClient(app):
                pass  # 启动即抛错，永不到达
        # 拒启动路径 lifespan 中断在 manager.dispose() 之前（播种段后无清理）——
        # app.state.db 在播种点之前已装配，这里显式收口池中 sqlite 连接
        # （aiosqlite 工作线程），防未处理线程异常泄漏到后续用例。
        await app.state.db.dispose()

    async def test_legal_env_seeds_row_at_startup(
        self, lifespan_sqlite: None, monkeypatch: Any, tmp_path: Any
    ) -> None:
        """合法值 → 启动完成（进入 yield）且种子行落位（v1/via=None——与首读
        种子同构，行格式零变化）。"""
        monkeypatch.setenv(RERANK_TIER_ENV, "llm")
        with TestClient(app):
            assert isinstance(app.state.retrieval, RetrievalService)  # 装配完成
        rows = await self._version_rows_after_startup(tmp_path)
        assert [r.version_no for r in rows] == ["v1"]  # 播种非变更版本推进
        assert rows[0].config["rerank"] == "llm"
        assert rows[0].via is None  # 种子非变更产生

    async def test_no_env_startup_zero_change(
        self, lifespan_sqlite: None, monkeypatch: Any, caplog: Any, tmp_path: Any
    ) -> None:
        """无 env → 现状零变化：启动无播种日志、版本轴零写入（首读才种子）。"""
        monkeypatch.delenv(RERANK_TIER_ENV, raising=False)
        with caplog.at_level(logging.INFO, logger="main"):
            with TestClient(app):
                pass
        assert [r for r in caplog.records if "RERANK_TIER" in r.getMessage()] == []
        assert await self._version_rows_after_startup(tmp_path) == []
