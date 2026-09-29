"""gateway 测试共享夹具：受控 models.yaml（字面测试值，非真实凭证）＋注册表缓存复位。

注册表真源纪律：infra.config 的 _models_cache 是进程级缓存——每个用例结束
复位，防测试配置泄漏进其他测试（生产路径不受影响）。
"""

from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest

import app.infra.config as infra_config
from app.infra.config import load_models_config
from app.infra.db import ConnectionManager

# 受控注册表（字面量均为测试假值；结构同 config/models.yaml——D1 真源形状）。
TEST_YAML = """\
# 测试用模型注册表（字面假值）
models:
  - alias: petro-main
    provider: anthropic
    model: MiniMax-M3
    base_url: https://main.example.test
    api_key: sk-test-main
    context_window: 1000000
    group: standard
    name: MiniMax-M3
    access: Anthropic 兼容接口 · 测试线路
    note: 问答/问数/问智默认出口
  - alias: petro-lite
    provider: anthropic
    model: glm-5.3-flash
    base_url: https://lite.example.test
    api_key: sk-test-lite
    context_window: 1000000
    group: lite
    name: glm-5.3-flash
    access: Anthropic 兼容接口 · 测试线路
    note: 备用/降级组——fallback 与预算熔断的便宜出口
routing:
  default: petro-main
  fallback_order: [petro-main, petro-lite]
prices:
  default:
    input_per_mtok: 1.0
    output_per_mtok: 3.0
gateway:
  allowed_fails: 2
  cooldown_seconds: 60
  num_retries: 3
  request_timeout: 30
"""


@pytest.fixture(autouse=True)
def _reset_models_cache() -> Iterator[None]:
    """用例结束复位进程级注册表缓存（测试隔离）。"""
    yield
    infra_config._models_cache = None


@pytest.fixture
def models_yaml(tmp_path: Path) -> Path:
    """受控 models.yaml 路径（字面假值；写回测试直接改本文件）。"""
    path = tmp_path / "models.yaml"
    path.write_text(TEST_YAML, encoding="utf-8")
    return path


@pytest.fixture
def primed_registry(models_yaml: Path) -> Path:
    """以受控文件预热注册表缓存（get_models_config 的进程级真源）。"""
    load_models_config(models_yaml)
    return models_yaml


@pytest.fixture
async def gateway_db(tmp_path: Path) -> AsyncIterator[ConnectionManager]:
    from app.domains.gateway.store import ensure_gateway_tables
    from app.infra.db import DatabaseSpec

    spec = DatabaseSpec(
        name="primary",
        role="primary",
        driver="sqlite",
        host="",
        port=0,
        database=str(tmp_path / "gateway.db"),
        user="",
        password="",
        pool_size=2,
        max_overflow=1,
    )
    manager = ConnectionManager([spec])
    await ensure_gateway_tables(manager.engine())  # 幂等建表（P0-04 惯例）
    yield manager
    await manager.dispose()
