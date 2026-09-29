"""infra.llm_client 单测——B6 adapter 的调用构造/usage 兜底/切换判据二值分类。

红线：任何测试不得真实调用 MiniMax/GLM 端点——litellm.acompletion 全量打桩。
合同锚：models.yaml 头注释（已验证调用形状）、ADR-0003 裁决 13（椒图判据：
网络错/超时/5xx 可切，4xx/429 不可切；W-F2-4 重试只走网关层）。
"""

from pathlib import Path
from typing import Any

import litellm
import litellm.exceptions as lex
import pytest

import app.infra.config as infra_config
from app.infra.config import load_models_config
from app.infra.llm_client import (
    AliasNotRegistered,
    LlmClient,
    UpstreamRejected,
    UpstreamUnavailable,
    classify_upstream_failure,
)

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
    infra_config._models_cache = None


@pytest.fixture
def client(tmp_path: Path) -> LlmClient:
    path = tmp_path / "models.yaml"
    path.write_text(TEST_YAML, encoding="utf-8")
    load_models_config(path)
    return LlmClient()


def _fake_response(
    content: str = "线路正常", usage: dict[str, int] | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "id": "chatcmpl-test-1",
    }
    if usage is not None:
        body["usage"] = usage
    return body


class _Capture:
    """acompletion 桩：记录入参并按脚本应答（永不触网）。"""

    def __init__(self, script: Any) -> None:
        self.script = script  # 返回值或异常实例
        self.calls: list[dict[str, Any]] = []

    async def __call__(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        out = self.script
        if isinstance(out, Exception):
            raise out
        return out


# ---------- 调用构造（注册表 → litellm 形状） ----------


async def test_complete_builds_call_from_registry(
    client: LlmClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    capture = _Capture(_fake_response(usage={"prompt_tokens": 2140, "completion_tokens": 1380}))
    monkeypatch.setattr(litellm, "acompletion", capture)
    result = await client.complete(
        "petro-main", [{"role": "user", "content": "你好"}], timeout_seconds=30
    )
    call = capture.calls[0]
    # models.yaml 头注释的已验证形状：anthropic/<model> + api_base + api_key
    assert call["model"] == "anthropic/MiniMax-M3"
    assert call["api_base"] == "https://main.example.test"
    assert call["api_key"] == "sk-test-main"  # 测试字面假值——真实凭证经 ${VAR} 注入
    assert call["messages"] == [{"role": "user", "content": "你好"}]
    assert call["timeout"] == 30  # per-attempt 超时透传
    assert call["num_retries"] == 0  # W-F2-4：SDK 层重试恒关（防套娃放大）
    assert result.content == "线路正常"
    assert (result.prompt_tokens, result.completion_tokens) == (2140, 1380)
    assert result.usage_estimated is False
    assert result.model == "anthropic/MiniMax-M3"  # 部署形（切换留痕 served_model 口径）


async def test_complete_unknown_alias_rejected(
    client: LlmClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(litellm, "acompletion", _Capture(_fake_response()))  # 不应被触达
    with pytest.raises(AliasNotRegistered):
        await client.complete("petro-ghost", [{"role": "user", "content": "x"}], timeout_seconds=5)


# ---------- usage 兜底（椒图蓝本：无 usage 时 chars/4 估算） ----------


async def test_complete_estimates_tokens_without_usage(
    client: LlmClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(litellm, "acompletion", _Capture(_fake_response(content="abcd" * 10)))
    result = await client.complete(
        "petro-lite",
        [{"role": "user", "content": "x" * 40}],
        timeout_seconds=5,
    )
    assert result.usage_estimated is True
    assert result.prompt_tokens == 10  # 40//4
    assert result.completion_tokens == 10  # 40//4


# ---------- 切换判据二值分类（椒图：网络错/超时/5xx 可切；4xx/429 不切） ----------


@pytest.mark.parametrize(
    ("exc", "expect_switchable"),
    [
        (lex.Timeout(message="t", model="m", llm_provider="p"), True),  # 超时（status 408）
        (lex.APIConnectionError(message="c", model="m", llm_provider="p"), True),  # 网络错
        (lex.InternalServerError(message="i", llm_provider="p", model="m"), True),  # 5xx
        (lex.BadRequestError(message="b", model="m", llm_provider="p"), False),  # 4xx
        (lex.RateLimitError(message="r", llm_provider="p", model="m"), False),  # 429
        (RuntimeError("意外异常无 status"), False),  # 保守——不可切
    ],
)
def test_classify_upstream_failure(exc: Exception, expect_switchable: bool) -> None:
    classified = classify_upstream_failure("petro-main", exc)
    assert classified.switchable is expect_switchable
    assert (isinstance(classified, UpstreamUnavailable)) is expect_switchable
    assert isinstance(classified, UpstreamUnavailable | UpstreamRejected)


async def test_sdk_exception_never_escapes_unclassified(
    client: LlmClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """B6：litellm 原生异常不出本模块——统一归类为 UpstreamError 族。"""
    monkeypatch.setattr(
        litellm,
        "acompletion",
        _Capture(lex.Timeout(message="t", model="m", llm_provider="p")),
    )
    with pytest.raises(UpstreamUnavailable):
        await client.complete("petro-main", [{"role": "user", "content": "x"}], timeout_seconds=1)
