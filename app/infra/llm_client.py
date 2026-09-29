"""infra.llm_client —— 供应商 SDK 内嵌 adapter（B6：全平台唯一允许碰 LiteLLM 的地方）。

边界（specs/api/98 §4 llm_client 行 / §6-B6；ADR-0003 裁决 13）：
- LiteLLM SDK 方式嵌主平台进程内（不起 proxy 服务）；本模块是 `litellm`
  唯一 import 点——业务模块禁直连供应商 SDK/HTTP，全平台模型调用唯一经
  `gateway.complete`（gateway 是本 adapter 的唯一消费方，98 §4 卡面原文）。
- 按 models.yaml 注册表构造调用（调用形状＝文件头注释 2026-09-29 双端点
  实测：litellm.completion(model="anthropic/<model>", api_base, api_key,
  messages, max_tokens)）；别名是唯一入口（业务代码只认别名，E1）。
- 异步面：平台依赖定型 asyncio（ADR-0003 裁决 3），落 `litellm.acompletion`
  （与头注释 completion 同形状的异步形式）；SDK 层重试恒关（num_retries=0，
  W-F2-4「重试只走网关层，无 SDK×网关套娃放大」——重试归 gateway 域循环）。
- 切换判据分类（椒图蓝本，ADR-0003 裁决 13）：网络错/超时/5xx ＝可切备
  （UpstreamUnavailable）；4xx/429 ＝不可切（UpstreamRejected，直抛调用方）。
- 无状态：每次调用现读注册表（config 热加载后下一次调用即生效）；密钥经
  占位符解析供给，绝不写日志、绝不出现在异常文本里。

B16：本模块只依赖 stdlib/litellm/infra.config——不 import domains/api。
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import litellm

from app.infra.config import ModelEntry, get_models_config


class UpstreamError(Exception):
    """供应商调用失败基类；switchable＝是否允许网关切备用（椒图判据）。"""

    switchable = False

    def __init__(self, alias: str, reason: str) -> None:
        super().__init__(f"模型调用失败 alias={alias!r}: {reason}")
        self.alias = alias
        self.reason = reason


class UpstreamUnavailable(UpstreamError):
    """网络错/超时/5xx——网关可切备用（switchable=True）。"""

    switchable = True


class UpstreamRejected(UpstreamError):
    """4xx/429——业务性拒绝，切备无意义（switchable=False，直抛调用方）。"""


class AliasNotRegistered(KeyError):
    """未注册的调用别名（B6：别名是唯一入口，拼错模型名在此拦截）。"""


@dataclass(frozen=True, slots=True)
class LlmCompletion:
    """单次上游应答的 adapter 视图（gateway 域再投影为业务 Completion）。"""

    content: str
    prompt_tokens: int
    completion_tokens: int
    usage_estimated: bool  # True＝上游无 usage，按 chars/4 估算（椒图蓝本）
    duration_ms: int
    model: str  # 实际应答的部署形（provider/model，切换留痕用）


def _entry(alias: str) -> ModelEntry:
    for entry in get_models_config().models:
        if entry.alias == alias:
            return entry
    raise AliasNotRegistered(alias)


def classify_upstream_failure(alias: str, exc: Exception) -> UpstreamError:
    """litellm 异常 → 可切/不可切二值（椒图判据单点；网络错/超时/5xx 可切）。

    - Timeout / APIConnectionError：网络错与超时——可切。
    - 带 status_code 的异常：>=500 可切；429/4xx 不可切（换部署也救不了
      请求本身的问题，切了只会把备用也打挂）。
    - 其余：不可切（保守——只有明确的基础设施类失败才配切备）。
    """
    import litellm.exceptions as lex

    if isinstance(exc, (lex.Timeout, lex.APIConnectionError)):
        return UpstreamUnavailable(alias, f"网络错/超时: {type(exc).__name__}")
    status = getattr(exc, "status_code", None)
    if isinstance(status, int) and status >= 500:
        return UpstreamUnavailable(alias, f"上游 {status}")
    if isinstance(status, int):
        return UpstreamRejected(alias, f"上游拒绝 {status}: {type(exc).__name__}")
    return UpstreamRejected(alias, f"{type(exc).__name__}: {exc}")


class LlmClient:
    """单别名单次调用出口（路由/fallback/重试/记账都在 gateway 域——本类无状态）。"""

    async def complete(
        self,
        alias: str,
        messages: list[dict[str, str]],
        *,
        timeout_seconds: float,
        max_tokens: int = 4096,
        **params: Any,
    ) -> LlmCompletion:
        """按注册表构造一次上游调用（per-attempt 超时；SDK 重试恒关）。"""
        entry = _entry(alias)
        started = time.monotonic()
        try:
            resp = await litellm.acompletion(
                model=f"{entry.provider}/{entry.model}",
                api_base=entry.base_url or None,
                api_key=entry.api_key or None,
                messages=messages,
                timeout=timeout_seconds,
                num_retries=0,  # W-F2-4：重试只走网关层，SDK 层恒关防套娃放大
                **params,
            )
        except Exception as exc:
            raise classify_upstream_failure(alias, exc) from exc
        duration_ms = int((time.monotonic() - started) * 1000)

        content = resp["choices"][0]["message"]["content"] or ""
        usage = resp.get("usage") or {}
        prompt = int(usage.get("prompt_tokens") or 0)
        completion = int(usage.get("completion_tokens") or 0)
        estimated = prompt == 0 and completion == 0
        if estimated:
            # 椒图蓝本：无 usage 时 chars/4 估算（推理模型流不可控时的兜底口径）。
            prompt = sum(len(m.get("content") or "") for m in messages) // 4
            completion = len(content) // 4
        return LlmCompletion(
            content=content,
            prompt_tokens=prompt,
            completion_tokens=completion,
            usage_estimated=estimated,
            duration_ms=duration_ms,
            model=f"{entry.provider}/{entry.model}",
        )
