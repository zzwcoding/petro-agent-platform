"""appv2.infra.llm_client 空正文守卫（V2-84）——网关切备空应答不得静默当成功。

红线：全部打桩，**绝不触网**（`litellm.acompletion` 全量替换）。
合同锚：挂账 A2 同族；真机 `run-a11920fb`／`run-67dbaca5`（petro-lite 推理 token 耗尽、
`content` 恒空、`completion_tokens=4096`）＋2026-10-18 直连取证（reasoning=64, text=0）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import litellm
import pytest

import appv2.infra.config as v2_config
from appv2.infra.config import load_models_config
from appv2.infra.llm_client import LlmClient, UpstreamUnavailable

# 受控注册表（字面量均为测试假值；结构与生产 config/models.yaml 同构）。
TEST_YAML = """\
models:
  - alias: petro-main
    provider: anthropic
    model: MiniMax-M3
    base_url: https://main.example.test
    api_key: sk-test-main
    context_window: 1000000
    group: standard
  - alias: petro-lite
    provider: anthropic
    model: glm-5.3-flash
    base_url: https://lite.example.test
    api_key: sk-test-lite
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
  allowed_fails: 2
  cooldown_seconds: 60
  num_retries: 3
  request_timeout: 30
"""


@pytest.fixture(autouse=True)
def _reset_models_cache() -> None:
    """用例结束复位进程级注册表缓存（infra.config 全局态——测试隔离）。"""
    yield
    v2_config._models_cache = None


@pytest.fixture
def client(tmp_path: Path) -> LlmClient:
    path = tmp_path / "models.yaml"
    path.write_text(TEST_YAML, encoding="utf-8")
    load_models_config(path)
    return LlmClient()


def _chunk(piece: str = "", usage: dict[str, int] | None = None) -> dict[str, Any]:
    """单帧（dict 形——实现侧 `_chunk_fields` 兼容 attr/mapping 双形）。"""
    frame: dict[str, Any] = {"choices": [{"delta": {"content": piece}}]}
    if usage is not None:
        frame["usage"] = usage
    return frame


async def _stream(frames: list[dict[str, Any]]):
    for frame in frames:
        yield frame


class _Capture:
    """`acompletion` 桩：记录入参并按脚本应答（list＝流式帧序列，永不触网）。"""

    def __init__(self, frames: list[dict[str, Any]]) -> None:
        self.frames = frames
        self.calls: list[dict[str, Any]] = []

    async def __call__(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return _stream(self.frames)


async def test_empty_content_raises_switchable(
    client: LlmClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """推理 token 耗尽形（正文零字、completion=4096）→ UpstreamUnavailable（可切备）。"""
    monkeypatch.setattr(
        litellm,
        "acompletion",
        _Capture([_chunk("", usage={"prompt_tokens": 2140, "completion_tokens": 4096})]),
    )
    with pytest.raises(UpstreamUnavailable) as exc:
        await client.complete(
            "petro-lite", [{"role": "user", "content": "你好"}], timeout_seconds=5
        )
    assert "空正文" in exc.value.reason
    assert "4096" in exc.value.reason  # 用量入证（排查面）
    assert exc.value.switchable is True  # 网关可重试/切备（同网络错族）


async def test_whitespace_only_content_raises(
    client: LlmClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """纯空白正文同判（去空白后为空）。"""
    monkeypatch.setattr(litellm, "acompletion", _Capture([_chunk("  \n\t")]))
    with pytest.raises(UpstreamUnavailable):
        await client.complete("petro-lite", [{"role": "user", "content": "x"}], timeout_seconds=5)


async def test_nonempty_content_unaffected(
    client: LlmClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """非空正文逐字不动（只判不改）——守卫零误伤。"""
    monkeypatch.setattr(litellm, "acompletion", _Capture([_chunk("  线路正常  ")]))
    result = await client.complete(
        "petro-main", [{"role": "user", "content": "你好"}], timeout_seconds=5
    )
    assert result.content == "  线路正常  "  # 两侧空白保留（不 strip 正文）


async def test_empty_error_never_leaks_key(
    client: LlmClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """异常文本不含密钥（B6 纪律）。"""
    monkeypatch.setattr(litellm, "acompletion", _Capture([_chunk("")]))
    with pytest.raises(UpstreamUnavailable) as exc:
        await client.complete("petro-lite", [{"role": "user", "content": "x"}], timeout_seconds=5)
    assert "sk-test" not in str(exc.value)
