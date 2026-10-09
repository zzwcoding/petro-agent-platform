"""V2-33 run_id 盖章——gateway 记账写账面钉测（sqlite 底座＋桩 backend，零触网）。

链路合同（tickets/v2/V2-33）：complete(**params) 的 run_id 归网关域消费（记账
归属槽——_DOMAIN_ONLY_PARAMS 剥除后不转发上游），_settle 落 SpendRecord.run_id
既有列（零迁移）；空串/缺省归一 NULL（账本列不落空串——0/3095 暗债补环不反转
成满表空串）。

调用面（runtime 盖章）钉测在 tests/domains/test_v2_runid_stamp.py；
rerun 归集面钉测在 tests/tools/test_rerun_spend.py。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import appv2.infra.config as v2_config
from appv2.infra.config import load_models_config
from appv2.infra.db import ConnectionManager, DatabaseSpec
from appv2.infra.gateway import GatewayService
from appv2.infra.gateway.store import SpendRecord, SpendStore, ensure_gateway_tables
from appv2.infra.llm_client import LlmCompletion

# 受控 models.yaml（tests/infra/test_v2_infra.py gate_yaml 同源——prices 缺失即拒记账）。
_GATE_YAML = """\
models:
  - alias: petro-main
    provider: anthropic
    model: MiniMax-M3
    group: primary
  - alias: petro-lite
    provider: anthropic
    model: glm-5.3-flash
    group: degrade
routing:
  default: petro-main
  fallback_order:
    - petro-main
    - petro-lite
gateway:
  allowed_fails: 3
  cooldown_seconds: 60
  num_retries: 0
  request_timeout: 8
prices:
  default:
    input_per_mtok: 1.0
    output_per_mtok: 3.0
stream:
  idle_timeout: 5
  max_seconds: 30
  llm_max_concurrency: 2
"""


class _CaptureBackend:
    """kwargs 捕获桩——断言「域级键剥除后才转发上游」的观测面。"""

    def __init__(self) -> None:
        self.kwargs: list[dict[str, Any]] = []

    async def complete(
        self,
        alias: str,
        messages: list[dict[str, str]],
        *,
        timeout_seconds: float,
        max_tokens: int = 4096,
        **kw: Any,
    ) -> LlmCompletion:
        self.kwargs.append(dict(kw))
        return LlmCompletion(
            content="应答",
            prompt_tokens=100,
            completion_tokens=10,
            usage_estimated=False,
            duration_ms=5,
            model=alias,
        )


@pytest.fixture
def gate_yaml(tmp_path: Path):  # type: ignore[no-untyped-def]
    path = tmp_path / "models.yaml"
    path.write_text(_GATE_YAML, encoding="utf-8")
    load_models_config(path)
    yield path
    v2_config._models_cache = None


@pytest.fixture
async def gateway_db(tmp_path: Path):
    spec = DatabaseSpec(
        name="primary",
        role="primary",
        driver="sqlite",
        host="",
        port=0,
        database=str(tmp_path / "v2-runid-gateway.db"),
        user="",
        password="",
        pool_size=2,
        max_overflow=1,
    )
    manager = ConnectionManager([spec])
    await ensure_gateway_tables(manager.engine())
    yield manager
    await manager.dispose()


async def _ledger_row(db: ConnectionManager, call_id: str) -> SpendRecord | None:
    """存储行直读（SpendView 是合同投影不带 run_id——列断言走 ORM 行）。"""
    async with db.readonly() as session:
        return await session.get(SpendRecord, call_id)


async def test_complete_stamps_run_id_into_ledger_row(
    gate_yaml: Path, gateway_db: ConnectionManager
) -> None:
    """run_id 进 complete 即落账本既有列（零迁移——acceptance 写账半边）。"""
    service = GatewayService(gateway_db, _CaptureBackend())
    out = await service.complete(
        "petro-main", [{"role": "user", "content": "q"}],
        caller="v2.runtime.understand", run_id="run-abc123",
    )
    row = await _ledger_row(gateway_db, out.call_id)
    assert row is not None
    assert row.run_id == "run-abc123"
    assert row.caller == "v2.runtime.understand"


async def test_complete_without_run_id_keeps_ledger_null(
    gate_yaml: Path, gateway_db: ConnectionManager
) -> None:
    """无 run 语境调用（演练 gateway.drill 族）＝列保持 NULL——不写空串。"""
    service = GatewayService(gateway_db, _CaptureBackend())
    out = await service.complete(
        "petro-main", [{"role": "user", "content": "q"}], caller="gateway.drill"
    )
    row = await _ledger_row(gateway_db, out.call_id)
    assert row is not None
    assert row.run_id is None


async def test_empty_run_id_normalized_to_null(
    gate_yaml: Path, gateway_db: ConnectionManager
) -> None:
    """空串 run_id（非 run 语境 adapter 无条件携）归一 NULL——账本列不落空串。"""
    service = GatewayService(gateway_db, _CaptureBackend())
    out = await service.complete(
        "petro-main", [{"role": "user", "content": "q"}],
        caller="v2.runtime.answer", run_id="",
    )
    row = await _ledger_row(gateway_db, out.call_id)
    assert row is not None
    assert row.run_id is None


async def test_run_id_not_forwarded_upstream(
    gate_yaml: Path, gateway_db: ConnectionManager
) -> None:
    """run_id 是域级键：记账消费后剥除——上游 backend kwargs 零 run_id（同 note）。"""
    backend = _CaptureBackend()
    service = GatewayService(gateway_db, backend)
    await service.complete(
        "petro-main", [{"role": "user", "content": "q"}],
        caller="v2.runtime.decision", run_id="run-xyz789",
    )
    assert backend.kwargs, "backend 未被调用"
    forwarded = backend.kwargs[0]
    assert "run_id" not in forwarded, f"run_id 漏剥直转上游：{sorted(forwarded)}"
    assert "note" not in forwarded  # 既有域级键语义不回退（P0-05 审查收口同路）


async def test_spend_view_projection_stays_contract_shaped(
    gate_yaml: Path, gateway_db: ConnectionManager
) -> None:
    """SpendView 投影零扩列：run_id 只进存储行，不漏 API 合同面（端点 4 形状红线）。"""
    service = GatewayService(gateway_db, _CaptureBackend())
    out = await service.complete(
        "petro-main", [{"role": "user", "content": "q"}],
        caller="v2.runtime.understand", run_id="run-readback",
    )
    store = SpendStore(gateway_db)
    view = await store.get(out.call_id)
    assert view is not None
    assert view.caller == "v2.runtime.understand"
    assert not hasattr(view, "run_id"), "SpendView 漏出 run_id——端点 4 合同面被扩列"
