"""G-06 信号量单测——全局 LLM 并发上限（并发探针计数 ≤ 上限；排队而非拒绝）。

DE-14 起：门为动态尺寸（acquire 时刻读当前配置判额，尺寸随热加载变动）——
本用例保持 G-06 原语义回归钉（超限排队、峰值 ≤ 上限、收流全释放）。
"""

import asyncio
from pathlib import Path

import pytest

import app.infra.config as infra_config
from app.domains.gateway import GatewayService
from app.domains.gateway.store import ensure_gateway_tables
from app.infra.config import load_models_config
from app.infra.db import ConnectionManager, DatabaseSpec

TEST_YAML = """\
models:
  - alias: petro-main
    provider: anthropic
    model: MiniMax-M3
    base_url: https://main.example.test
    api_key: sk-test
    context_window: 1000000
    group: standard
  - alias: petro-lite
    provider: anthropic
    model: glm-5.3-flash
    base_url: https://lite.example.test
    api_key: sk-test
    context_window: 1000000
    group: lite
routing:
  default: petro-main
  fallback_order: [petro-main, petro-lite]
prices:
  default:
    input_per_mtok: 1.0
    output_per_mtok: 3.0
gateway:
  allowed_fails: 99
  cooldown_seconds: 0
  num_retries: 0
  request_timeout: 5
stream:
  idle_timeout: 5
  max_seconds: 30
  llm_max_concurrency: 2
"""


@pytest.fixture(autouse=True)
def _gw_tables(tmp_path: Path):
    """幂等建表（记账落库需要）——gateway conftest 同款先例。"""
    import asyncio as _a

    spec = DatabaseSpec(name="primary", role="primary", driver="sqlite", host="",
                        port=0, database=str(tmp_path / "gw.db"), user="",
                        password="", pool_size=2, max_overflow=1)
    manager = ConnectionManager([spec])
    _a.run(_ensure_tables(manager))
    yield manager
    _a.run(manager.dispose())


@pytest.fixture
def yaml_path(tmp_path: Path) -> Path:
    path = tmp_path / "models.yaml"
    path.write_text(TEST_YAML, encoding="utf-8")
    load_models_config(path)
    return path


@pytest.fixture(autouse=True)
def _reset_cache():
    infra_config._models_cache = None
    yield
    infra_config._models_cache = None


async def _ensure_tables(manager) -> None:
    engine = manager.engine()
    await ensure_gateway_tables(engine)


class _SlowBackend:
    """并发探针后端：记录峰值并发（每调用占 0.2 秒）。"""

    def __init__(self) -> None:
        self.active = 0
        self.peak = 0

    async def complete(self, alias, messages, *, timeout_seconds, max_tokens=8, **kw):
        self.active += 1
        self.peak = max(self.peak, self.active)
        await asyncio.sleep(0.2)
        self.active -= 1

        class _C:
            content = "好"
            prompt_tokens = 1
            completion_tokens = 1
            usage_estimated = False
            duration_ms = 200
            model = alias

        return _C()


async def test_gate_caps_concurrent_calls(yaml_path: Path, _gw_tables) -> None:
    """6 路并发提问全部成功（排队等），上游峰值并发 ≤ 信号量上限 2。"""
    manager = _gw_tables
    gw = GatewayService(manager, _SlowBackend())
    results = await asyncio.gather(*[
        gw.complete("petro-main", [{"role": "user", "content": f"q{i}"}],
                    caller="diag.probe")
        for i in range(6)
    ])
    assert len(results) == 6  # 全部成功——排队等而非拒绝
    assert gw._llm_gate is not None
    assert gw._llm_gate.current_limit() == 2  # 上限 2（DE-14：动态门现值可读）
    assert gw._llm_gate.locked() is False  # 收流后闸释放
    await manager.dispose()
