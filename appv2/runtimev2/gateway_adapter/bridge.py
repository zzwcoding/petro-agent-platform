"""gateway_adapter.bridge —— 生产桥主干（模型调用唯一出口的实作）。

规格 `specs/gateway_adapter.md` 行为 1–8／10（本票＝-03a 生产桥主干单链）：
入参面固定三件（`messages`／`caller`／`run_id`，**无自由 `params`**）→ 经 `infra` 的
供应商出口（B6：`gateway.complete`）发起 → 回执恒十键（`ModelReply`）→ 重试只对
可重试类 → 耗尽 fail-closed（**原异常上抛**）。

- **唯一出口**：本块是全工程唯一允许直引 `appv2.infra.llm_client`／`appv2.infra.gateway`
  的 runtimev2 块（R7 契约的例外面 ＋ V2 B6 契约：`litellm` 唯一接触点＝
  `appv2.infra.llm_client`）。出口以**显式注入缝**装配（`set_completer`）——生产注入
  本桥 `GatewayBridge`，测试注入同面替身 `ScriptedCompleter`（离线零触网）。
- **重试分层（两件事，不许并成一句）**：`infra` 侧判据回答「要不要**切备用部署**」
  （网络错／超时／5xx 可切；**429 不可切**——换部署救不了请求本身）；本块回答
  「**同一个调用要不要再试一次**」——**429 可重试**。
- **失败类别闭世界（本块自立）**：`rate_limited`（429）｜`timeout`｜
  `upstream_unavailable`（网络错／5xx）｜`rejected`（4xx 业务性拒绝）——可重试＝前三类，
  `rejected` 不重试、不误伤。类别映射**单点**＝`classify_failure`（本块唯一一次；
  **不复用** `infra.llm_client.classify_upstream_failure` 的判据、不引
  `tools.registry.classify_exception`——只**摄入原始失败事实**（异常类型／状态码）后映射）。
- **失败也留痕**：每次失败尝试都产出失败回执（`failure_reply`：`error` 非 None、
  `content` 空串、归因面齐备）且都真的发到出口（infra 侧逐尝试落 calllog，含失败与
  `error` 字段）——**留痕条数＝尝试次数**。
- **本块零判断**：不读词表、不判语义、不做业务分支（只有「可重试／不可重试」这类
  结构分派）。

重试次数与退避的**现状锚**＝旧运行时 env 面 `appv2/runtime/llm.py`:47-49 的
`GATEWAY_429_RETRIES`／`GATEWAY_429_BACKOFF`（env 可覆写、调用时读——非 import 冻结）；
**正式数值阶段 5 随真机定**——本件照抄现状锚，不新定数值（规格行为 6）。
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections.abc import Awaitable, Callable, Iterator, Mapping, Sequence
from typing import Any, Protocol

from appv2.infra.gateway import Completion
from appv2.infra.llm_client import UpstreamRejected, UpstreamUnavailable
from appv2.runtimev2.gateway_adapter.reply import ModelReply

_LOGGER = logging.getLogger(__name__)

# ── 重试次数与退避（现状锚，见模块 docstring）──────────────────
GATEWAY_429_RETRIES_ENV = "GATEWAY_429_RETRIES"
GATEWAY_429_BACKOFF_ENV = "GATEWAY_429_BACKOFF"
GATEWAY_429_RETRIES_DEFAULT = 3
GATEWAY_429_BACKOFF_DEFAULT: tuple[float, ...] = (5.0, 20.0, 60.0)

# ── 失败类别闭世界（本块自立——规格行为 7）────────────────────
# 四类名面量**各只出现一次**（单点定义；机检＝`::no_second_classification_source`）。
RATE_LIMITED = "rate_limited"  # 429 限流
TIMEOUT = "timeout"  # 超时
UPSTREAM_UNAVAILABLE = "upstream_unavailable"  # 网络错／5xx
REJECTED = "rejected"  # 4xx 业务性拒绝
FAILURE_KINDS: tuple[str, ...] = (RATE_LIMITED, TIMEOUT, UPSTREAM_UNAVAILABLE, REJECTED)
# 可重试＝前三类（429／超时／网络错・5xx）；`rejected` 一次即抛（不误伤）。
RETRYABLE_FAILURE_KINDS: frozenset[str] = frozenset(
    (RATE_LIMITED, TIMEOUT, UPSTREAM_UNAVAILABLE)
)

# 因果链下钻上限（infra 出口在无可切候选时以 `NoAvailableRoute` 收口，原始失败挂在
# `__cause__` 上——摄入原始失败事实需顺链取；设上限防环）。
_CAUSE_HOPS = 5


class Egress(Protocol):
    """供应商出口缝（生产＝`infra.gateway.GatewayService`；B6 唯一消费方＝本块）。"""

    async def complete(
        self, alias: str, messages: list[dict[str, str]], *, caller: str, **params: Any
    ) -> Completion: ...


class Completer(Protocol):
    """同面缝（生产＝`GatewayBridge`；测试＝替身 `ScriptedCompleter`）——签名与回执形状同一。"""

    async def complete(
        self, messages: Sequence[Mapping[str, str]], *, caller: str, run_id: str = ""
    ) -> ModelReply: ...


def _failure_facts(exc: BaseException) -> Iterator[BaseException]:
    """失败事实链：异常本身逐跳顺 `__cause__`／`__context__` 下钻（最多 `_CAUSE_HOPS` 跳）。"""
    fact: BaseException | None = exc
    for _ in range(_CAUSE_HOPS + 1):
        if fact is None:
            return
        yield fact
        fact = fact.__cause__ or fact.__context__


def classify_failure(exc: BaseException) -> str:
    """原始失败事实 → 失败类别（**单点映射**；四类闭世界，见模块 docstring）。

    只摄入原始失败事实（异常类型／状态码／`UpstreamError` 的 `reason` 前缀），
    不复用 `infra` 的「可切／不可切」判据（那是回答「要不要切备用部署」的另一个问题）。
    未识别的失败＝**保守不重试**（归 `rejected` 侧：原异常上抛、fail-closed）。
    """
    for fact in _failure_facts(exc):
        if isinstance(fact, TimeoutError):  # 内建超时（py3.12 含 asyncio.TimeoutError）
            return TIMEOUT
        status = getattr(fact, "status_code", None)
        if status == 429:
            return RATE_LIMITED
        if isinstance(status, int) and status >= 500:
            return UPSTREAM_UNAVAILABLE
        if isinstance(status, int) and 400 <= status < 500:
            return REJECTED
        if isinstance(fact, UpstreamUnavailable):
            return UPSTREAM_UNAVAILABLE
        if isinstance(fact, UpstreamRejected):
            # B6 出口不带 status_code 属性——429 认 `reason` 单源前缀
            # （`llm_client.classify_upstream_failure` 单源格式化「上游拒绝 429:」，
            #  与 `tools.registry.classify_exception` 同口径判法）。
            if str(getattr(fact, "reason", "")).startswith("上游拒绝 429:"):
                return RATE_LIMITED
            return REJECTED
    return REJECTED


def failure_reply(
    *, caller: str, run_id: str, error: str, alias: str = "", duration_ms: int = 0
) -> ModelReply:
    """失败尝试的回执（**本块单点**）——十字段恒在场：`content` 空串、`error` 非 None。

    用量面无实测值（尝试失败）＝标注估算（`usage_estimated=True`——不许把未知当实测）；
    `cached_tokens` 未上报＝0（钉 `pin-25` 的回执面）；归因面齐备（`caller`／`run_id`）
    ——失败同样进记账归因面（规格「失败必须留痕」）。
    """
    return ModelReply(
        content="",
        caller=caller,
        run_id=run_id,
        alias=alias,
        prompt_tokens=0,
        completion_tokens=0,
        cached_tokens=0,
        usage_estimated=True,
        duration_ms=duration_ms,
        error=error,
    )


def _reply_of(
    completion: Completion, *, caller: str, run_id: str, duration_ms: int
) -> ModelReply:
    """成功应答 → 回执（十字段恒在场）：用量实测透传、别名取路由实服结果、`error`＝None。"""
    return ModelReply(
        content=completion.content,
        caller=caller,
        run_id=run_id,
        alias=completion.served_alias,
        prompt_tokens=completion.prompt_tokens,
        completion_tokens=completion.completion_tokens,
        # 上游未上报时＝0（钉 pin-25；infra 业务投影现不带该键，带则透传）。
        cached_tokens=int(getattr(completion, "cached_tokens", 0) or 0),
        usage_estimated=completion.usage_estimated,
        duration_ms=duration_ms,
        error=None,
    )


def _elapsed_ms(started: float) -> int:
    """实测耗时（毫秒）——时间缝＝`time.monotonic`（同 `infra.llm_client` 口径）。"""
    return int((time.monotonic() - started) * 1000)


def _error_text(exc: BaseException) -> str:
    """失败事实的留痕文本（类型＋消息——同 infra calllog 的 error 列口径）。"""
    return f"{type(exc).__name__}: {exc}"


def _configured_retries() -> int:
    """重试次数＝缺省（现状锚），env `GATEWAY_429_RETRIES` 覆写（调用时读，非 import 冻结）。"""
    raw = os.environ.get(GATEWAY_429_RETRIES_ENV, "").strip()
    if not raw:
        return GATEWAY_429_RETRIES_DEFAULT
    try:
        return max(0, int(raw))
    except ValueError:
        return GATEWAY_429_RETRIES_DEFAULT


def _configured_backoff() -> tuple[float, ...]:
    """退避等待序列（秒）＝缺省（现状锚），env `GATEWAY_429_BACKOFF` 逗号分隔覆写。"""
    raw = os.environ.get(GATEWAY_429_BACKOFF_ENV, "").strip()
    if not raw:
        return GATEWAY_429_BACKOFF_DEFAULT
    try:
        values = tuple(float(piece) for piece in raw.split(",") if piece.strip())
    except ValueError:
        return GATEWAY_429_BACKOFF_DEFAULT
    return values or GATEWAY_429_BACKOFF_DEFAULT


class GatewayBridge:
    """生产桥：一次调用的出口发起与回执装配（重试只对可重试类；耗尽原异常上抛）。"""

    def __init__(
        self,
        egress: Egress,
        *,
        retries: int | None = None,
        backoff: Sequence[float] | None = None,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        """注入供应商出口；重试次数／退避缺省取现状锚 env 面（可显式覆写）；`sleep`＝等待缝。"""
        self._egress = egress
        self._retries = _configured_retries() if retries is None else max(0, retries)
        self._backoff = tuple(_configured_backoff() if backoff is None else backoff)
        self._sleep = sleep if sleep is not None else asyncio.sleep

    async def complete(
        self, messages: Sequence[Mapping[str, str]], *, caller: str, run_id: str
    ) -> ModelReply:
        """一次调用：出口发起 → 回执装配；失败按类别重试，耗尽／不可重试＝原异常上抛。"""
        sent = [dict(message) for message in messages]
        attempt = 0
        while True:
            started = time.monotonic()
            try:
                completion = await self._egress.complete(
                    "", sent, caller=caller, run_id=run_id
                )
            except Exception as exc:  # CancelledError 属 BaseException（py3.12）——不吞
                duration_ms = _elapsed_ms(started)
                kind = classify_failure(exc)
                traced = failure_reply(
                    caller=caller,
                    run_id=run_id,
                    error=_error_text(exc),
                    duration_ms=duration_ms,
                )
                _LOGGER.warning(
                    "gateway_adapter 失败尝试留痕：attempt=%d/%d caller=%s run_id=%s"
                    " kind=%s error=%s",
                    attempt + 1,
                    self._retries + 1,
                    caller,
                    run_id,
                    kind,
                    traced.error,
                )
                if kind not in RETRYABLE_FAILURE_KINDS or attempt >= self._retries:
                    raise
                await self._sleep(self._backoff_delay(attempt))
                attempt += 1
                continue
            return _reply_of(
                completion, caller=caller, run_id=run_id, duration_ms=_elapsed_ms(started)
            )

    def _backoff_delay(self, attempt: int) -> float:
        """第 attempt 次失败后的等待时长（序列用尽驻留末项；空序列＝零等待）。"""
        if not self._backoff:
            return 0.0
        return self._backoff[min(attempt, len(self._backoff) - 1)]


_completer: Completer | None = None


def set_completer(completer: Completer | None) -> Completer | None:
    """显式注入缝（装配点）：生产注入本桥 `GatewayBridge`，测试注入同面替身（`None`＝复位）。

    返回先前注入者（供成对恢复——同 `infra.clock.set_clock` 形）。生产装配路径**不读**
    任何环境变量决定出口（pin-27 同款纪律：只经显式注入缝）。
    """
    global _completer
    previous = _completer
    _completer = completer
    return previous


def _configured_completer() -> Completer:
    """当前注入的同面缝；未注入＝抛错（fail-closed——模型调用无出口，不静默兜底）。"""
    if _completer is None:
        raise RuntimeError(
            "gateway_adapter 出口未注入（set_completer 未调用）——模型调用无出口，fail-closed"
        )
    return _completer


async def complete(
    messages: Sequence[Mapping[str, str]], *, caller: str, run_id: str
) -> ModelReply:
    """模型调用唯一出口（卡面签名）——薄转发到已注入的同面缝（生产桥／替身）。

    **无第二套逻辑**：实作只在注入的缝里（生产＝`GatewayBridge`）；本函数只转发，
    供发起方单点 `bookkeeping.call_model` 调用（规格行为 1 的桥接规则：从状态取
    `run_id`、以 `(messages, caller, run_id)` 调本块、回执的用量与归因面交记账）。
    """
    return await _configured_completer().complete(messages, caller=caller, run_id=run_id)
