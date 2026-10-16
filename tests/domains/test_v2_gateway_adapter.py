"""gateway_adapter 生产桥验收（RT-W2-03a：骨架＋接口＋生产桥主干＋全部 3 条 pin 行；
RT-W2-03b：替身面指针＋元面＋【边界集】／【保留集】）。

票面对象＝`specs/gateway_adapter.md`「验收测试」表第 1–10 行（RT-W2-03a 落，逐字，测试
标识同规格列：`::single_model_egress`／`::params_face_fixed`／`::reply_all_keys_and_cached_zero`／
`::complete_is_async`／`::attribution_per_call`／`::retry_only_on_retryable`／
`::no_second_classification_source`／`::exhausted_fail_closed`／
`::frozen_clock_four_branches`／`::usage_estimated_flagged`）＋第 14–16 行（RT-W2-03b 落：
`::no_judgement_in_gateway_adapter`／`::boundary_empty_huge_ratelimit_clock`／
`::retention_normal_call_unchanged`）。

规格表第 11–13 行（替身同面／不静默兜底／观测面只读）绑**既有**织网地基件
`tests/runtimev2/test_gateway_adapter_fake.py`（该件 14 测；`tests/runtimev2/` 合计 45 测
——本件不转抄其断言，防两处真源漂移）。

测试网钉（同规格「与闸的挂钩表」；3 条 pin 行全在 RT-W2-03a，RT-W2-03b 零 pin 行）：
- `pin-25`（P1，回执面）→ `::reply_all_keys_and_cached_zero`（`cached_tokens` 未上报＝0；
  其「透传 calllog JSONL」的**落痕面归 infra**，本件不冒充覆盖）；
- `pin-27`（P0，时钟面）→ `::frozen_clock_four_branches`（缺省冻结日＋`real` 须显式；
  「帧 `frozen_date`」半面不属本块）；
- `pin-28`（P1，调用盖章面）→ `::attribution_per_call`（每次调用 `run_id` 盖章、
  计费可对账；落盘面挂 `specs/persistence.md`、全盖章面挂 `specs/agent-loop.md`）。

形状真源＝RT-W2-03a 落地的面（`ModelReply` 十字段／`complete` 签名／冻结时钟四分支／
`ScriptedCompleter` 签名）——RT-W2-03b 只加行为与元／边界·保留断言，不改形状。

织网义务 B7b 落点＝`::retry_only_on_retryable`：按新规格行为 6 织**可重试断言**
（限流／超时／网络错／5xx 可重试；4xx 业务性拒绝不重试）——旧钉
`tests/domains/test_v2_llm_429_retry.py` 的「网络错一次即抛」相抵断言同批改写。
"""

from __future__ import annotations

import ast
import inspect
import logging
import os
import re
from collections import Counter
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import FrozenInstanceError, asdict, dataclass, fields
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from appv2.infra.clock import freeze
from appv2.infra.gateway import Completion, NoAvailableRoute
from appv2.infra.llm_client import UpstreamRejected, UpstreamUnavailable
from appv2.runtimev2.gateway_adapter import (
    EVAL_FROZEN_DATE_DEFAULT,
    EVAL_FROZEN_DATE_ENV,
    EVAL_FROZEN_DATE_REAL,
    GatewayBridge,
    ModelReply,
    ScriptedCompleter,
    complete,
    failure_reply,
    frozen_date,
    set_completer,
)
from appv2.runtimev2.gateway_adapter import bridge as bridge_module
from appv2.runtimev2.gateway_adapter import fake as fake_module
from appv2.runtimev2.gateway_adapter import reply as reply_module

_REPO_ROOT = Path(__file__).resolve().parents[2]
_V2_DIR = _REPO_ROOT / "appv2" / "runtimev2"
_BLOCK_DIR = _V2_DIR / "gateway_adapter"
_LOG_NAME = "appv2.runtimev2.gateway_adapter.bridge"

# 规格行为 7 的四类名面量对应常量名（单点定义扫描用）
_KIND_CONSTANTS = ("RATE_LIMITED", "TIMEOUT", "UPSTREAM_UNAVAILABLE", "REJECTED")
# 规格行为 7 的四类闭世界取值（逐字）
_KIND_VALUES = ("rate_limited", "timeout", "upstream_unavailable", "rejected")
# 行为 1：发起方单点＝`bookkeeping.call_model`（其余相位不得自行发起模型调用）
_MODEL_CALL_CALLER_BLOCKS = {"bookkeeping"}
# 本块只许引 infra 的这三个面（B6 两条出口＋时钟：B14 时间唯一出口）
_BLOCK_INFRA_FACE = {"appv2.infra.gateway", "appv2.infra.llm_client", "appv2.infra.clock"}
# 供应商模型出口（B6）：全 runtimev2 树只许本块直引（R7 契约的例外面）
_EGRESS_MODULES = {"appv2.infra.gateway", "appv2.infra.llm_client"}
# 禁手写替代：裸 HTTP 客户端／供应商 SDK（边界红线④）
_RAW_CLIENT_ROOTS = {
    "httpx",
    "requests",
    "litellm",
    "openai",
    "aiohttp",
    "urllib3",
    "socket",
    "http",
    "urllib",
}


# ---------- 共享替身与装配 ----------


def _messages(*texts: str) -> list[dict[str, str]]:
    return [{"role": "user", "content": text} for text in texts]


def _answer(content: str = "应答正文", **overrides: Any) -> Completion:
    """出口成功应答（infra 业务投影 `Completion` 形状）。"""
    base: dict[str, Any] = {
        "content": content,
        "prompt_tokens": 12,
        "completion_tokens": 7,
        "usage_estimated": False,
        "call_id": "call-1",
        "cost_yuan": 0.0,
        "fallback": False,
        "served_alias": "petro-main",
    }
    base.update(overrides)
    return Completion(**base)


@dataclass(frozen=True, slots=True)
class _CachedAnswer:
    """出口应答的「带 `cached_tokens`」形（上游真上报时回执面透传——不缺口）。"""

    content: str = "应答正文"
    prompt_tokens: int = 12
    completion_tokens: int = 7
    usage_estimated: bool = False
    served_alias: str = "petro-main"
    cached_tokens: int = 7


class _DuckFailure(Exception):
    """带结构化 `status_code` 的原始失败事实（真实 HTTP 形同判）。"""

    def __init__(self, status_code: int, text: str) -> None:
        super().__init__(text)
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class _Call:
    """出口逐调用留痕（caller／run_id 归因面 + 发送 messages 快照）。"""

    alias: str
    messages: list[dict[str, str]]
    caller: str
    run_id: str


class _ScriptedEgress:
    """供应商出口替身（B6 出口位）：按次序抛错／交付，末项驻留；逐调用留痕。"""

    def __init__(self, outcomes: Sequence[BaseException | Any]) -> None:
        self._outcomes = list(outcomes)
        self.calls: list[_Call] = []

    async def complete(
        self, alias: str, messages: list[dict[str, str]], *, caller: str, **params: Any
    ) -> Any:
        self.calls.append(
            _Call(
                alias=alias,
                messages=[dict(message) for message in messages],
                caller=caller,
                run_id=str(params.get("run_id", "")),
            )
        )
        outcome = self._outcomes[min(len(self.calls) - 1, len(self._outcomes) - 1)]
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def _recorder(waits: list[float]) -> Callable[[float], Awaitable[None]]:
    """退避等待注入面：记录每次等待时长，零真等（同旧件 `_backoff_sleep` 缝）。"""

    async def _instant(seconds: float) -> None:
        waits.append(seconds)

    return _instant


def _exhausted(cause: BaseException) -> NoAvailableRoute:
    """infra 出口的「全候选耗尽」收口形（`raise NoAvailableRoute(...) from last_error`）。"""
    error = NoAvailableRoute("petro-main")
    error.__cause__ = cause
    return error


def _bridge(
    egress: _ScriptedEgress,
    *,
    retries: int | None = None,
    backoff: Sequence[float] | None = None,
    waits: list[float] | None = None,
) -> GatewayBridge:
    """生产桥（等待缝注入＝零真等；重试参数缺省取现状锚 env 面）。"""
    return GatewayBridge(
        egress,
        retries=retries,
        backoff=backoff,
        sleep=None if waits is None else _recorder(waits),
    )


# ---------- AST 扫描器材（行 1／7／9 的机检面）----------


def _source(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def _block_sources() -> list[tuple[Path, ast.Module]]:
    """本块全部源码（含包根与替身件——「本块 import 只出现 infra」的扫描域）。"""
    return [(path, _source(path)) for path in sorted(_BLOCK_DIR.rglob("*.py"))]


def _v2_sources() -> list[tuple[Path, ast.Module]]:
    """全 runtimev2 树源码（旧码 `appv2/runtime/` 是重构退役面——不入扫描域，R5）。"""
    return [(path, _source(path)) for path in sorted(_V2_DIR.rglob("*.py"))]


def _imported_modules(tree: ast.Module) -> set[str]:
    """源码树里一切绝对 import 的模块名。"""
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module)
    return modules


def _docstring_ids(tree: ast.Module) -> set[int]:
    """模块／类／函数 docstring 字面量的节点 id（断言扫描时排除——docstring 不是定义点）。"""
    ids: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = node.body
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            ids.add(id(body[0].value))
    return ids


def _string_literal_sites(tree: ast.Module, value: str) -> list[int]:
    """非 docstring 字符串常量的位点（「单点定义」扫描用）。"""
    docstrings = _docstring_ids(tree)
    return [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and node.value == value
        and id(node) not in docstrings
    ]


def _functions_returning(tree: ast.Module, names: set[str]) -> set[str]:
    """返回指定常量名的函数名集（「类别映射单点函数」扫描用）。"""
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for sub in ast.walk(node):
            if (
                isinstance(sub, ast.Return)
                and isinstance(sub.value, ast.Name)
                and sub.value.id in names
            ):
                found.add(node.name)
    return found


def _named_sites(tree: ast.Module, name: str) -> int:
    """按名引用（`Name`／`Attribute`）某符号的位点数。"""
    count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == name:
            count += 1
        elif isinstance(node, ast.Attribute) and node.attr == name:
            count += 1
    return count


def _bridge_tree() -> ast.Module:
    """生产桥源码树（断言用）。"""
    return _source(_BLOCK_DIR / "bridge.py")


# ---------- 1 唯一出口（行为 1；边界红线③④的 AST 断言面）----------


async def test_single_model_egress() -> None:
    """唯一出口：模型调用点只在本块与 `bookkeeping.call_model`。"""
    # ① 本块 import 面＝infra 三面＋自身子模块（边界红线③「本块 import 只出现 infra」）
    for path, tree in _block_sources():
        for module in _imported_modules(tree):
            if not module.startswith("appv2"):
                continue
            if module == "appv2" or module.startswith("appv2.runtimev2.gateway_adapter"):
                continue
            assert module in _BLOCK_INFRA_FACE, f"{path.name} 引了 infra 外的 appv2 面：{module}"
    # ② 禁手写替代：裸 HTTP 客户端／供应商 SDK 零出现（边界红线④）
    for path, tree in _block_sources():
        for module in _imported_modules(tree):
            assert module.split(".")[0] not in _RAW_CLIENT_ROOTS, (
                f"{path.name} 出现裸 HTTP 客户端／SDK：{module}"
            )
    # ③ 全 runtimev2 树：供应商模型出口（B6）只许从本块直引
    for path, tree in _v2_sources():
        if path.parent == _BLOCK_DIR:
            continue
        for module in _imported_modules(tree):
            assert module not in _EGRESS_MODULES, f"{path} 直引了模型出口：{module}"
    # ④ 全 runtimev2 树：引本块（模型调用面）的只许发起方单点 `bookkeeping`
    for path, tree in _v2_sources():
        if path.parent == _BLOCK_DIR:
            continue
        if not any(
            module == "appv2.runtimev2.gateway_adapter"
            or module.startswith("appv2.runtimev2.gateway_adapter.")
            for module in _imported_modules(tree)
        ):
            continue
        parts = path.relative_to(_V2_DIR).parts
        owner = parts[0] if len(parts) > 1 else "<root>"
        assert owner in _MODEL_CALL_CALLER_BLOCKS, (
            f"{path} 自行发起模型调用（发起方只许 bookkeeping）"
        )

    # 出口未装配＝fail-closed（没有出口就不许有调用——不静默兜底）
    previous = set_completer(None)
    try:
        with pytest.raises(RuntimeError, match="set_completer"):
            await complete(_messages("问"), caller="v2.runtime.understand", run_id="run-1")
    finally:
        set_completer(previous)
    # 探测器非空转：伪造源上命中
    forged = ast.parse("from appv2.infra.gateway import Completion\n")
    assert "appv2.infra.gateway" in _imported_modules(forged)


# ---------- 2 入参面固定三件（行为 2）----------


def test_params_face_fixed() -> None:
    """入参面固定三件、无自由 `params`（未知键报错）。"""
    egress_face = inspect.signature(complete)
    assert list(egress_face.parameters) == ["messages", "caller", "run_id"]  # 卡面签名
    bridge_face = inspect.signature(GatewayBridge.complete)
    # 生产面（+self）——规格行为 2 断言「参数集合恰为三者（+self）」
    assert list(bridge_face.parameters) == ["self", "messages", "caller", "run_id"]
    for face in (egress_face, bridge_face):
        for name in ("caller", "run_id"):
            assert face.parameters[name].kind is inspect.Parameter.KEYWORD_ONLY
        assert all(
            parameter.kind is not inspect.Parameter.VAR_KEYWORD
            for parameter in face.parameters.values()
        ), "无自由 params 面（**params 一类口子不对外开）"
    # 同面：生产桥与替身同形签名（行为 11 的签名半面；替身侧行 11 由
    # `tests/runtimev2/test_gateway_adapter_fake.py` 看守）
    assert list(bridge_face.parameters) == list(
        inspect.signature(ScriptedCompleter.complete).parameters
    )

    egress = _ScriptedEgress([_answer()])
    bridge = _bridge(egress)
    with pytest.raises(TypeError, match="alias"):
        complete(_messages("问"), caller="c", run_id="r", alias="petro-main")
    with pytest.raises(TypeError, match="params"):
        bridge.complete(_messages("问"), caller="c", run_id="r", params={"temperature": 0.2})
    # 生产面 `run_id` 必填（每调用盖章——钉 pin-28 的入参面）
    with pytest.raises(TypeError, match="run_id"):
        complete(_messages("问"), caller="c")
    with pytest.raises(TypeError, match="run_id"):
        bridge.complete(_messages("问"), caller="c")


# ---------- 3 回执面恒全键（行为 3；钉 pin-25 回执面）----------


async def test_reply_all_keys_and_cached_zero() -> None:
    """回执十键恒在场；`cached_tokens` 未上报＝0（`pin-25`）。"""
    keys = {field.name for field in fields(ModelReply)}
    assert keys == {
        "content",
        "caller",
        "run_id",
        "alias",
        "prompt_tokens",
        "completion_tokens",
        "cached_tokens",
        "usage_estimated",
        "duration_ms",
        "error",
    }
    # 成功路径：上游未上报 `cached_tokens`（infra 业务投影现形）→ =0（不缺口、不省略）
    egress = _ScriptedEgress([_answer("应答正文")])
    reply = await _bridge(egress).complete(
        _messages("问"), caller="v2.runtime.answer", run_id="run-3"
    )
    assert set(asdict(reply)) == keys
    assert reply.cached_tokens == 0
    assert (reply.content, reply.alias, reply.error) == ("应答正文", "petro-main", None)
    # 上游真上报＝透传（同一键不缺口、不填猜测值）
    reported = await _bridge(_ScriptedEgress([_CachedAnswer()])).complete(
        _messages("问"), caller="v2.runtime.answer", run_id="run-3"
    )
    assert reported.cached_tokens == 7
    # 失败路径：键集合与成功路径相等（`error` 非 None、`content` 空串）
    failed = failure_reply(
        caller="v2.runtime.answer", run_id="run-3", error="UpstreamRejected: 上游拒绝 400"
    )
    assert set(asdict(failed)) == keys
    assert (failed.content, failed.cached_tokens) == ("", 0)
    assert failed.error is not None


# ---------- 4 `complete` 是协程（行为 4）----------


def test_complete_is_async() -> None:
    """`complete` 是协程。"""
    assert inspect.iscoroutinefunction(complete)
    assert inspect.iscoroutinefunction(GatewayBridge.complete)
    coroutine = complete(_messages("问"), caller="v2.runtime.decision", run_id="run-4")
    assert inspect.iscoroutine(coroutine)
    coroutine.close()


# ---------- 5 归因面逐调用保留（行为 5；钉 pin-28 调用盖章面）----------


async def test_attribution_per_call() -> None:
    """归因面逐调用保留（`caller`／`run_id` 可分组）。"""
    egress = _ScriptedEgress([_answer("一"), _answer("二"), _answer("三")])
    bridge = _bridge(egress)
    replies = [
        await bridge.complete(_messages("问一"), caller="v2.runtime.understand", run_id="run-a"),
        await bridge.complete(_messages("问二"), caller="v2.runtime.understand", run_id="run-a"),
        await bridge.complete(_messages("问三"), caller="v2.runtime.answer", run_id="run-b"),
    ]
    # 逐调用交出口、不合并、不覆盖（逐调用顺序与归因面原样）
    assert [(call.caller, call.run_id) for call in egress.calls] == [
        ("v2.runtime.understand", "run-a"),
        ("v2.runtime.understand", "run-a"),
        ("v2.runtime.answer", "run-b"),
    ]
    assert [call.messages for call in egress.calls] == [
        _messages("问一"),
        _messages("问二"),
        _messages("问三"),
    ]
    # 可按 `caller`／`run_id` 分组（计费可对账）
    assert Counter((call.caller, call.run_id) for call in egress.calls) == Counter(
        {("v2.runtime.understand", "run-a"): 2, ("v2.runtime.answer", "run-b"): 1}
    )
    assert [(reply.caller, reply.run_id) for reply in replies] == [
        ("v2.runtime.understand", "run-a"),
        ("v2.runtime.understand", "run-a"),
        ("v2.runtime.answer", "run-b"),
    ]
    # 每次调用盖章：重试的每一次尝试都带同一 `run_id`（钉 pin-28）
    retried = _ScriptedEgress(
        [UpstreamRejected("petro-main", "上游拒绝 429: RateLimitError"), _answer("四")]
    )
    reply = await _bridge(retried, retries=1, backoff=(0.0,)).complete(
        _messages("问四"), caller="v2.runtime.decision", run_id="run-c"
    )
    assert [call.run_id for call in retried.calls] == ["run-c", "run-c"]
    assert (reply.caller, reply.run_id) == ("v2.runtime.decision", "run-c")
    # 模块级出口面＝薄转发到注入缝（替身可注入）：替身观测面与 calllog 行同口径
    scripted = ScriptedCompleter({"v2.runtime.understand": ["替身应答"]})
    previous = set_completer(scripted)
    try:
        injected = await complete(_messages("问五"), caller="v2.runtime.understand", run_id="run-d")
    finally:
        set_completer(previous)
    assert (injected.content, injected.caller, injected.run_id) == (
        "替身应答",
        "v2.runtime.understand",
        "run-d",
    )
    assert scripted.counts() == {"v2.runtime.understand": 1}
    assert scripted.messages_of("v2.runtime.understand") == [_messages("问五")]


# ---------- 6 重试只对可重试类（行为 6；B7b 存量改写落点）----------


async def test_retry_only_on_retryable(monkeypatch: pytest.MonkeyPatch) -> None:
    """非限流失败一次即抛（不误伤）；限流失败重试到上限。"""
    config = {"retries": 3, "backoff": (5.0, 20.0, 60.0)}
    # ① 不可重试类（4xx 业务性拒绝／未识别失败）→ 一次即抛、身份不变、零退避等待
    for refused in (
        UpstreamRejected("petro-main", "上游拒绝 400: BadRequestError"),
        _DuckFailure(status_code=400, text="HTTP 400: bad args"),
        ValueError("计划或参数错误"),
        NoAvailableRoute("petro-main"),  # 接不上原始失败事实＝未识别（保守不重试）
    ):
        egress = _ScriptedEgress([refused])
        waits: list[float] = []
        with pytest.raises(type(refused)) as excinfo:
            await _bridge(egress, waits=waits, **config).complete(
                _messages("问"), caller="v2.runtime.answer", run_id="run-6"
            )
        assert excinfo.value is refused, "不可重试类＝原异常上抛（不换形／不包装）"
        assert len(egress.calls) == 1, f"{type(refused).__name__} 不应重试"
        assert waits == [], "不可重试类零退避等待"
    # ② 可重试类（429／超时／网络错・5xx）→ 重试到上限后原异常上抛
    for retryable in (
        UpstreamRejected("petro-main", "上游拒绝 429: RateLimitError"),  # 429
        TimeoutError("上游超时"),  # 超时
        UpstreamUnavailable("petro-main", "网络错/超时: APIConnectionError"),  # 网络错
        _DuckFailure(status_code=503, text="HTTP 503: unavailable"),  # 5xx
        # 生产形：全候选耗尽 → `NoAvailableRoute` 收口，原始失败挂在因果链上（网络错）
        _exhausted(UpstreamUnavailable("petro-main", "网络错: APIConnectionError")),
    ):
        egress = _ScriptedEgress([retryable])
        waits = []
        with pytest.raises(type(retryable)) as excinfo:
            await _bridge(egress, waits=waits, **config).complete(
                _messages("问"), caller="v2.runtime.answer", run_id="run-6"
            )
        assert excinfo.value is retryable
        assert len(egress.calls) == 4, f"{type(retryable).__name__} 应打满首调＋3 重试"
        assert waits == [5.0, 20.0, 60.0], "退避按配置序列（用尽驻留末项）"
    # ③ 重试后成功＝恰一次交付（回执出自成功尝试）
    egress = _ScriptedEgress(
        [UpstreamRejected("petro-main", "上游拒绝 429: RateLimitError"), _answer("答到")]
    )
    waits = []
    reply = await _bridge(egress, retries=3, backoff=(5.0, 20.0, 60.0), waits=waits).complete(
        _messages("问"), caller="v2.runtime.answer", run_id="run-6"
    )
    assert (reply.content, len(egress.calls), waits) == ("答到", 2, [5.0])
    # ④ 现状锚 env 面可覆写（调用时读——非 import 冻结）
    monkeypatch.setenv(bridge_module.GATEWAY_429_RETRIES_ENV, "1")
    monkeypatch.setenv(bridge_module.GATEWAY_429_BACKOFF_ENV, "0.25")
    egress = _ScriptedEgress(
        [UpstreamRejected("petro-main", "上游拒绝 429: RateLimitError") for _ in range(2)]
    )
    waits = []
    with pytest.raises(UpstreamRejected):
        await _bridge(egress, waits=waits).complete(
            _messages("问"), caller="v2.runtime.answer", run_id="run-6"
        )
    assert len(egress.calls) == 2, "覆写后＝首调＋1 重试"
    assert waits == [0.25]


# ---------- 7 分类判据不另立（行为 7）----------


def test_no_second_classification_source() -> None:
    """分类判据不在本块另立。"""
    # ① 四类名面量各只出现一次（单点定义）
    for kind in bridge_module.FAILURE_KINDS:
        sites = [
            site for _path, tree in _block_sources() for site in _string_literal_sites(tree, kind)
        ]
        assert len(sites) == 1, f"类别名面量 {kind} 出现 {len(sites)} 处（应单点定义）"
    # ② 映射单点：只有 `classify_failure` 返回类别常量
    bridge_tree = _source(_BLOCK_DIR / "bridge.py")
    assert _functions_returning(bridge_tree, set(_KIND_CONSTANTS)) == {"classify_failure"}
    # ③ 不复用他处判据：infra 的「可切／不可切」判据与 tools 的三分类零引用
    for forbidden in ("classify_upstream_failure", "classify_exception", "switchable"):
        assert (
            sum(_named_sites(tree, forbidden) for _path, tree in _block_sources()) == 0
        ), f"本块引了第二处失败分类判据：{forbidden}"
    # ④ 可重试性只由类别推出（单表；429／超时／网络错・5xx 可重试，rejected 不重试）
    assert bridge_module.RETRYABLE_FAILURE_KINDS == frozenset(
        {bridge_module.RATE_LIMITED, bridge_module.TIMEOUT, bridge_module.UPSTREAM_UNAVAILABLE}
    )
    assert bridge_module.REJECTED not in bridge_module.RETRYABLE_FAILURE_KINDS
    assert set(bridge_module.FAILURE_KINDS) == set(_KIND_VALUES)
    # 探测器非空转：伪造「两处映射」源上命中
    forged = ast.parse(
        "def a(exc):\n"
        "    return RATE_LIMITED\n"
        "def b(exc):\n"
        "    return RATE_LIMITED\n"
    )
    assert _functions_returning(forged, {"RATE_LIMITED"}) == {"a", "b"}


# ---------- 8 重试耗尽 fail-closed（行为 8）----------


async def test_exhausted_fail_closed(caplog: pytest.LogCaptureFixture) -> None:
    """重试耗尽 fail-closed：原异常上抛＋失败留痕。"""
    failures = [
        UpstreamRejected("petro-main", "上游拒绝 429: RateLimitError") for _ in range(3)
    ]
    egress = _ScriptedEgress(failures)
    waits: list[float] = []
    with caplog.at_level(logging.WARNING, logger=_LOG_NAME):
        with pytest.raises(UpstreamRejected) as excinfo:
            await _bridge(egress, retries=2, backoff=(0.0, 0.0), waits=waits).complete(
                _messages("问"), caller="v2.runtime.answer", run_id="run-8"
            )
    assert excinfo.value is failures[-1], "耗尽＝原异常上抛（不返回空应答、不静默降级）"
    assert len(egress.calls) == 3, "失败留痕条数＝尝试次数（每次尝试都真的发到出口）"
    traces = [record.getMessage() for record in caplog.records if record.name == _LOG_NAME]
    assert len(traces) == 3
    # 最后回执的 `error` 非 None（失败尝试也留痕——回执形状＝`failure_reply` 单点）
    last = failures[-1]
    assert traces[-1].endswith(f"error={type(last).__name__}: {last}")
    assert "attempt=3/3" in traces[-1]
    assert "kind=rate_limited" in traces[-1]
    traced = failure_reply(
        caller="v2.runtime.answer", run_id="run-8", error=f"{type(last).__name__}: {last}"
    )
    assert (traced.content, traced.caller, traced.run_id) == ("", "v2.runtime.answer", "run-8")
    assert traced.error is not None


# ---------- 9 冻结时钟四分支（行为 9；钉 pin-27 时钟面）----------


def test_frozen_clock_four_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    """冻结时钟四分支（缺省／`real`／ISO／非法）＋生产不读 env。"""
    real_day = date(2027, 3, 4)
    with freeze("2027-03-04T09:00:00"):  # 真实钟注入（`real` 分支读 `infra.clock`）
        # 未设 → 缺省冻结日（≠ 真实当日——冻结时钟不得静默回落真实钟）
        monkeypatch.delenv(EVAL_FROZEN_DATE_ENV, raising=False)
        assert frozen_date() == EVAL_FROZEN_DATE_DEFAULT
        assert frozen_date() != real_day
        # 空串＝未设（容器 env 置空形）
        monkeypatch.setenv(EVAL_FROZEN_DATE_ENV, "")
        assert frozen_date() == EVAL_FROZEN_DATE_DEFAULT
        # `real` 须显式 → 当日真实日期
        monkeypatch.setenv(EVAL_FROZEN_DATE_ENV, EVAL_FROZEN_DATE_REAL)
        assert frozen_date() == real_day
        # ISO 日期 → 该日
        monkeypatch.setenv(EVAL_FROZEN_DATE_ENV, "2026-01-02")
        assert frozen_date() == date(2026, 1, 2)
        # 非法值 → 抛错（fail-fast，不静默回落）
        for illegal in ("2026-13-45", "今天", "08/31/2026"):
            monkeypatch.setenv(EVAL_FROZEN_DATE_ENV, illegal)
            with pytest.raises(ValueError, match=EVAL_FROZEN_DATE_ENV):
                frozen_date()

    # 生产装配路径不读该环境变量（只经显式注入缝）：冻结钟 env 键只许出现在时钟件里，
    # 生产桥既不读该键、也不引该件
    key_owners = {
        path.name
        for path, tree in _block_sources()
        if _string_literal_sites(tree, EVAL_FROZEN_DATE_ENV)
    }
    assert key_owners == {"eval_clock.py"}, f"冻结钟 env 面越界：{key_owners}"
    assert _named_sites(_bridge_tree(), "EVAL_FROZEN_DATE_ENV") == 0
    assert _named_sites(_bridge_tree(), "frozen_date") == 0
    assert "appv2.runtimev2.gateway_adapter.eval_clock" not in _imported_modules(_bridge_tree())


# ---------- 10 用量实测与估算可区分（行为 10）----------


async def test_usage_estimated_flagged() -> None:
    """用量实测与估算可区分（`usage_estimated`）。"""
    measured = await _bridge(
        _ScriptedEgress([_answer("实测应答", prompt_tokens=120, completion_tokens=80)])
    ).complete(_messages("问"), caller="v2.runtime.answer", run_id="run-10")
    assert measured.usage_estimated is False
    assert (measured.prompt_tokens, measured.completion_tokens) == (120, 80)
    estimated = await _bridge(
        _ScriptedEgress(
            [_answer("估算应答", prompt_tokens=7, completion_tokens=2, usage_estimated=True)]
        )
    ).complete(_messages("问"), caller="v2.runtime.answer", run_id="run-10")
    assert estimated.usage_estimated is True
    assert (estimated.prompt_tokens, estimated.completion_tokens) == (7, 2)  # 估算值原样标注
    # 两条路径取值不同（`usage_estimated` 不是恒定值——估算必须显式标注）
    assert measured.usage_estimated != estimated.usage_estimated
    assert measured.duration_ms >= 0 and estimated.duration_ms >= 0


# ---------- 11–13 替身面（同面／不静默兜底／观测面只读）----------

# 规格行 11–13 的测试标识绑**既有**织网地基件 `tests/runtimev2/test_gateway_adapter_fake.py`
# （`TestCardFace::test_complete_signature_matches_card`／
# `TestDefaultFallback::test_unscripted_without_default_fails_fast`／
# `TestObservationFaces::test_script_injection_readonly`）——本件不转抄其断言（防两处真源
# 漂移）；本件只在行 16 补跨面半面：替身与生产桥两条路径的回执键集相等（同一 `ModelReply`）。


# ---------- 14 本块零判断（AST 扫描；行为 13）----------

# 本块 import 白名单：stdlib 通用件（事件循环／日志／env／时间／数据类／类型）＋`infra` 三面
# （B6 两条出口＋B14 时钟）＋本包子模块。白名单外一律判失败——语义词表与正则（`re`）、
# 引擎与工具面、框架所需的 import 全在名单外。
_ALLOWED_BLOCK_IMPORTS = {
    "__future__",
    "asyncio",
    "collections.abc",
    "dataclasses",
    "datetime",
    "logging",
    "os",
    "time",
    "typing",
    "appv2.infra.clock",
    "appv2.infra.gateway",
    "appv2.infra.llm_client",
}
_ALLOWED_BLOCK_IMPORT_PREFIXES = ("appv2.runtimev2.gateway_adapter.",)
# 禁止调用面：文件／动态执行／事件发射／语义向量／正则判定（`complete` 不在禁列——本块
# 自己就是模型出口；`embeddings` 面不属本块，只走 `complete`）
_FORBIDDEN_BLOCK_CALLS = {
    "open",
    "print",
    "eval",
    "exec",
    "compile",
    "__import__",
    "emit",
    "embeddings",
    "findall",
    "sub",
    "search",
    "match",
    "fullmatch",
}
# 「消息内容面」名：分支判据不得触（本块只有「可重试／不可重试」这类结构分派）
_CONTENT_FACE_NAMES = {
    "messages",
    "message",
    "content",
    "prompt",
    "question",
    "intent",
    "word",
    "words",
}
# 分支判据里的中文明文白名单＝行为 7 的 B6 失败事实单源前缀（`classify_failure` 单点：
# 「上游拒绝 429:」是**结构事实**、非业务词表）——下述断言另钉它在块内只许一处。
_STRUCTURAL_FACT_LITERALS = ("上游拒绝 429:",)
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _callee_names(tree: ast.Module) -> list[tuple[int, str]]:
    """一切调用点的被调名（`Name`／`Attribute` 形——`x.foo()` 记 `foo`）。"""
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            found.append((node.lineno, func.id))
        elif isinstance(func, ast.Attribute):
            found.append((node.lineno, func.attr))
    return found


def _str_collections(tree: ast.Module) -> list[tuple[int, set[str]]]:
    """字符串集合字面量／`set|frozenset(...)` 的元素集（「自建词表」扫描用）。"""
    found: list[tuple[int, set[str]]] = []
    for node in ast.walk(tree):
        elements: list[ast.expr] = []
        if isinstance(node, (ast.Set, ast.Tuple, ast.List)):
            elements = list(node.elts)
        elif isinstance(node, ast.Dict):
            elements = [key for key in node.keys if key is not None]
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in {"set", "frozenset"}
        ):
            for argument in node.args:
                if isinstance(argument, (ast.Set, ast.Tuple, ast.List)):
                    elements.extend(argument.elts)
        else:
            continue
        strings = {
            element.value
            for element in elements
            if isinstance(element, ast.Constant) and isinstance(element.value, str)
        }
        if strings:
            found.append((node.lineno, strings))
    return found


def _branch_tests(tree: ast.Module) -> list[tuple[int, ast.expr]]:
    """一切分支判据（`if`／条件表达式／`while`／`match` 守卫）——「不做业务分支」的扫描面。"""
    found: list[tuple[int, ast.expr]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.IfExp, ast.While)):
            found.append((node.lineno, node.test))
        elif isinstance(node, ast.Match):
            found.extend(
                (case.guard.lineno, case.guard) for case in node.cases if case.guard is not None
            )
    return found


def _referenced_names(node: ast.AST) -> set[str]:
    """子树按名引用（`Name`／`Attribute`）到的标识符集。"""
    names: set[str] = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name):
            names.add(sub.id)
        elif isinstance(sub, ast.Attribute):
            names.add(sub.attr)
    return names


def _cjk_literals(node: ast.AST) -> list[str]:
    """子树里的中文明文常量（按业务词面分派＝语义判断的机检代理）。"""
    return [
        sub.value
        for sub in ast.walk(node)
        if isinstance(sub, ast.Constant)
        and isinstance(sub.value, str)
        and any("\u4e00" <= char <= "\u9fff" for char in sub.value)
    ]


def _judgement_findings(tree: ast.Module) -> list[str]:
    """零判断的机检面：白名单外 import／禁止调用／自建词表／触内容面或中文明文的分支判据。"""
    findings: list[str] = []
    for module in sorted(_imported_modules(tree)):
        if module in _ALLOWED_BLOCK_IMPORTS or module.startswith(_ALLOWED_BLOCK_IMPORT_PREFIXES):
            continue
        findings.append(f"import {module}")
    for line, name in _callee_names(tree):
        if name in _FORBIDDEN_BLOCK_CALLS:
            findings.append(f"L{line} 调用 {name}")
    for line, values in _str_collections(tree):
        for value in sorted(values):
            if not _IDENTIFIER.fullmatch(value):
                findings.append(f"L{line} 疑似词表项 {value!r}")
    for line, test in _branch_tests(tree):
        touched = _referenced_names(test) & _CONTENT_FACE_NAMES
        if touched:
            findings.append(f"L{line} 分支判据触消息内容面：{sorted(touched)}")
        for value in _cjk_literals(test):
            if value not in _STRUCTURAL_FACT_LITERALS:
                findings.append(f"L{line} 分支判据疑似语义明文 {value!r}")
    return findings


def test_no_judgement_in_gateway_adapter() -> None:
    """本块零判断（AST 扫描）。"""
    for path, tree in _block_sources():
        findings = _judgement_findings(tree)
        assert findings == [], f"{path.name}：{findings}"

    # 分支判据里唯一的中文明文＝B6 失败事实单源前缀（行为 7 的结构分派事实，非词表）
    # ——且块内只许一处（单点，不另立第二张词面）
    for literal in _STRUCTURAL_FACT_LITERALS:
        sites = [
            site
            for _path, tree in _block_sources()
            for site in _string_literal_sites(tree, literal)
        ]
        assert len(sites) == 1, f"结构性明文 {literal!r} 出现 {len(sites)} 处（应单点）"

    # 探测器非空转（词表／正则／文件 IO／消息内容面分支／中文明文分支五类各命中）
    forged = ast.parse(
        "import re\n"
        "WORDS = {'拒答', '无据'}\n"
        "open('痕迹.txt')\n"
        "if '是不是' in messages[0]['content']:\n"
        "    pass\n"
        "if kind == '拒答':\n"
        "    pass\n"
    )
    findings = _judgement_findings(forged)
    assert any(finding.startswith("import re") for finding in findings)
    assert any("词表项" in finding for finding in findings)
    assert any("调用 open" in finding for finding in findings)
    assert any("触消息内容面" in finding for finding in findings)
    assert any("疑似语义明文" in finding for finding in findings)


# ---------- 15 【边界集】（空 messages／超长 messages／限流失败／非法时钟值）----------


async def test_boundary_empty_huge_ratelimit_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    """【边界集】空 messages／超长 messages／限流失败／非法时钟值 → 各落对应分支。"""
    # ① 空 messages：原样转发（不补默认消息、不因空而抛、不静默兜底）
    empty = _ScriptedEgress([_answer("空问应答")])
    empty_reply = await _bridge(empty).complete(
        [], caller="v2.runtime.answer", run_id="run-15"
    )
    assert empty.calls[0].messages == []
    assert (empty_reply.content, empty_reply.caller, empty_reply.run_id) == (
        "空问应答",
        "v2.runtime.answer",
        "run-15",
    )
    assert empty_reply.error is None
    # 替身面同边界：空 messages 照常分流、`run_id` 可缺省；未剧本化仍当场抛错（不静默）
    stand_in = ScriptedCompleter({"m": ["甲"]})
    assert (await stand_in.complete([], caller="m")).content == "甲"
    assert (await stand_in.complete([], caller="m", run_id="run-15")).run_id == "run-15"
    with pytest.raises(AssertionError, match="ghost"):
        await stand_in.complete([], caller="ghost")

    # ② 超长 messages：逐字透传（本块不截断、不省略——截断面在 prompts／context）
    huge = "长" * 200_000
    long_egress = _ScriptedEgress([_answer("长问应答")])
    await _bridge(long_egress).complete(
        _messages(huge), caller="v2.runtime.answer", run_id="run-15"
    )
    assert long_egress.calls[0].messages == [{"role": "user", "content": huge}]
    many = _messages(*[f"第{n}问" for n in range(500)])
    many_egress = _ScriptedEgress([_answer("多问应答")])
    await _bridge(many_egress).complete(many, caller="v2.runtime.answer", run_id="run-15")
    assert many_egress.calls[0].messages == many  # 条数与次序原样

    # ③ 限流失败：可重试类落「退避重试」分支（零上限／到上限／空退避序列三边界）；
    #    4xx 业务性拒绝落「一次即抛」分支
    limiting = [
        UpstreamRejected("petro-main", "上游拒绝 429: RateLimitError") for _ in range(3)
    ]
    zero_cap = _ScriptedEgress(limiting)
    waits: list[float] = []
    with pytest.raises(UpstreamRejected) as excinfo:
        await _bridge(zero_cap, retries=0, backoff=(), waits=waits).complete(
            _messages("问"), caller="v2.runtime.answer", run_id="run-15"
        )
    assert excinfo.value is limiting[0]
    assert (len(zero_cap.calls), waits) == (1, [])  # 零上限＝不留第二次尝试、零等待
    capped = _ScriptedEgress(limiting)
    waits = []
    with pytest.raises(UpstreamRejected) as excinfo:
        await _bridge(capped, retries=2, backoff=(0.0,), waits=waits).complete(
            _messages("问"), caller="v2.runtime.answer", run_id="run-15"
        )
    assert excinfo.value is limiting[-1]
    assert (len(capped.calls), waits) == (3, [0.0, 0.0])  # 打满首调＋2 重试后原异常上抛
    bare_backoff = _ScriptedEgress(limiting)
    waits = []
    with pytest.raises(UpstreamRejected):
        await _bridge(bare_backoff, retries=1, backoff=(), waits=waits).complete(
            _messages("问"), caller="v2.runtime.answer", run_id="run-15"
        )
    assert (len(bare_backoff.calls), waits) == (2, [0.0])  # 退避序列空＝零等待（不静默跳过重试）
    refused = _ScriptedEgress(
        [UpstreamRejected("petro-main", "上游拒绝 400: BadRequestError")]
    )
    refused_waits: list[float] = []
    with pytest.raises(UpstreamRejected):
        await _bridge(refused, retries=3, backoff=(0.0,), waits=refused_waits).complete(
            _messages("问"), caller="v2.runtime.answer", run_id="run-15"
        )
    assert (len(refused.calls), refused_waits) == (1, [])  # 不可重试类一次即抛（不误伤）

    # ④ 非法时钟值：fail-fast（不静默回落真实钟／缺省冻结日，也不改写输入）
    for illegal in (
        "2026-13-45",
        "今天",
        "08/31/2026",
        "2026-8-31",
        "2026-08-31 ",
        "REAL",
    ):
        monkeypatch.setenv(EVAL_FROZEN_DATE_ENV, illegal)
        with pytest.raises(ValueError, match=EVAL_FROZEN_DATE_ENV):
            frozen_date()
        assert os.environ[EVAL_FROZEN_DATE_ENV] == illegal
    assert (EVAL_FROZEN_DATE_REAL, EVAL_FROZEN_DATE_DEFAULT) == ("real", date(2026, 8, 31))


# ---------- 16 【保留集】（常规成功调用的回执字段与归因行为不变）----------


class _ForwardingStub:
    """出口缝存根：原样收回执（钉「薄转发」——不改形／不包装／不复制）。"""

    def __init__(self, reply: ModelReply) -> None:
        self._reply = reply
        self.seen: list[tuple[Sequence[Mapping[str, str]], str, str]] = []

    async def complete(
        self, messages: Sequence[Mapping[str, str]], *, caller: str, run_id: str = ""
    ) -> ModelReply:
        self.seen.append((messages, caller, run_id))
        return self._reply


def _class_definitions(tree: ast.Module) -> set[str]:
    """模块内一切类定义名（「禁双定义」扫描用）。"""
    return {node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}


async def test_retention_normal_call_unchanged() -> None:
    """【保留集】常规成功调用的回执字段与归因行为不变。"""
    # 回执形状保留：十字段键序照规格接口定义；缺省面不变；`frozen`＋`slots` 不变
    assert [field.name for field in fields(ModelReply)] == [
        "content",
        "caller",
        "run_id",
        "alias",
        "prompt_tokens",
        "completion_tokens",
        "cached_tokens",
        "usage_estimated",
        "duration_ms",
        "error",
    ]
    blank = ModelReply(content="应答正文", caller="c", run_id="r")
    assert asdict(blank) == {
        "content": "应答正文",
        "caller": "c",
        "run_id": "r",
        "alias": "",
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "cached_tokens": 0,
        "usage_estimated": True,
        "duration_ms": 0,
        "error": None,
    }
    with pytest.raises(FrozenInstanceError):
        blank.content = "改"  # type: ignore[misc]
    assert not hasattr(blank, "__dict__")  # slots=True

    # 单一定义保留：块级唯一实现在 `reply.py`，替身件不自留第二处（阶段 5 只改为 import）
    assert ModelReply is reply_module.ModelReply is fake_module.ModelReply
    assert "ModelReply" not in _class_definitions(_source(_BLOCK_DIR / "fake.py"))

    # 常规成功调用：回执字段与归因面原样（内容与别名取路由实服、用量实测、失败面为 None）
    egress = _ScriptedEgress([_answer("常规应答")])
    reply = await _bridge(egress).complete(
        _messages("问"), caller="v2.runtime.answer", run_id="run-16"
    )
    assert set(asdict(reply)) == {field.name for field in fields(ModelReply)}
    assert (reply.content, reply.alias, reply.error) == ("常规应答", "petro-main", None)
    assert (reply.prompt_tokens, reply.completion_tokens, reply.cached_tokens) == (12, 7, 0)
    assert reply.usage_estimated is False and reply.duration_ms >= 0
    # 归因面逐调用原样交出口：`(caller, run_id)` 齐备；别名不由调用方传（路由决定随回执返回）
    assert [(call.caller, call.run_id) for call in egress.calls] == [
        ("v2.runtime.answer", "run-16")
    ]
    assert egress.calls[0].alias == "" and egress.calls[0].messages == _messages("问")

    # 跨面半面（同面·回执形状）：替身路径与生产桥路径的回执键集相等（同一 `ModelReply`）
    stand_in = ScriptedCompleter({"v2.runtime.answer": ["替身应答"]})
    stand_in_reply = await stand_in.complete(
        _messages("问"), caller="v2.runtime.answer", run_id="run-16"
    )
    assert isinstance(stand_in_reply, ModelReply)
    assert set(asdict(stand_in_reply)) == set(asdict(reply))
    assert (stand_in_reply.content, stand_in_reply.caller, stand_in_reply.run_id) == (
        "替身应答",
        "v2.runtime.answer",
        "run-16",
    )

    # 出口面＝薄转发：注入缝返回什么就回什么（不换形／不包装／不复制回执）
    sentinel = ModelReply(content="哨兵应答", caller="v2.runtime.answer", run_id="run-16")
    stub = _ForwardingStub(sentinel)
    previous = set_completer(stub)
    try:
        forwarded = await complete(_messages("问"), caller="v2.runtime.answer", run_id="run-16")
    finally:
        set_completer(previous)
    assert forwarded is sentinel
    assert stub.seen == [(_messages("问"), "v2.runtime.answer", "run-16")]
