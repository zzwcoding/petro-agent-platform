"""infra.llm_client —— 供应商 SDK 内嵌 adapter（B6：全平台唯一允许碰 LiteLLM 的地方）。

V2 复制层（V2-01 自 V1 app/infra/llm_client.py 复制清理——仅模块路径
app.* → appv2.*，语义逐字节同形；litellm 为 V1 既有依赖复制沿用）。

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
- embedding 适配（P1-11 选型接线，Owner 2026-10-02 拍板 MiniMax 优先）：
  `LlmClient.embeddings(alias, texts, input_type)`——MiniMax /v1/embeddings
  （2026-10-02 curl 实测：HTTP 200，embo-01 · 1536 维 · 已归一化 · 无需
  GroupId；向量库文本 type=db、检索文本 type=query——query/db 分离算法）。
  供应商 SDK 接触仍单点在本模块（此处为 httpx 直连——该端点非 OpenAI 形状，
  litellm 无此 provider 形），业务面只认别名 petro-embed（B6 纪律不变）。
- 无状态：每次调用现读注册表（config 热加载后下一次调用即生效）；密钥经
  占位符解析供给，绝不写日志、绝不出现在异常文本里。

B16：本模块只依赖 stdlib/litellm/httpx/appv2.infra.config——不 import 上层模块。
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any

import httpx
import litellm

from appv2.infra.config import ModelEntry, get_models_config


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


@dataclass(frozen=True, slots=True)
class LlmEmbedding:
    """单次向量化应答的 adapter 视图（P1-11——kb/faq EmbeddingBackend 消费）。"""

    vectors: list[list[float]]
    total_tokens: int
    duration_ms: int
    model: str


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
        """按注册表构造一次上游调用（G-01：真流式消费——调用方形状不变）。

        - 超时语义两刀：litellm timeout＝连接＋首帧（TTFT）；帧间空闲超时＝
          stream.idle_timeout（连续无新帧判上游假死）。非流式时代线上静默、
          「总时长」是唯一死活判据，误杀长生成（百科整页写不完必超 30s）——
          流式下每一帧都是活信号，写多久都不掐，只有帧停了才断。
        - 总时长护栏 stream.max_seconds 独立存在：防"持续出帧但失控"的 runaway。
        - 记账口径不变：usage 优先取末帧（include_usage），缺失 chars/4 估算；
        - 空闲超时/护栏抛 UpstreamUnavailable（可切备——复用网关 fallback/重试/
          熔断面）；litellm 异常仍走 classify_upstream_failure 同一分类面。
        """
        entry = _entry(alias)
        stream_cfg = get_models_config().stream
        started = time.monotonic()
        stream = None
        parts: list[str] = []
        usage: dict[str, Any] = {}
        try:
            try:
                stream = await litellm.acompletion(
                    model=f"{entry.provider}/{entry.model}",
                    api_base=entry.base_url or None,
                    api_key=entry.api_key or None,
                    messages=messages,
                    timeout=timeout_seconds,  # 连接＋首帧（TTFT）
                    num_retries=0,  # W-F2-4：重试只走网关层，SDK 层恒关防套娃放大
                    stream=True,
                    stream_options={"include_usage": True},
                    **params,
                )
            except UpstreamError:
                raise
            except Exception as exc:
                raise classify_upstream_failure(alias, exc) from exc

            while True:
                if time.monotonic() - started > stream_cfg.max_seconds:
                    raise UpstreamUnavailable(
                        alias,
                        f"流总时长超 {stream_cfg.max_seconds:.0f}s 护栏——判失控可切备",
                    )
                try:
                    chunk = await asyncio.wait_for(
                        _frame_next(stream), timeout=stream_cfg.idle_timeout
                    )
                except StopAsyncIteration:
                    break  # 正常收流终点
                except TimeoutError:  # asyncio.TimeoutError 别名（py3.12）——帧间空闲超时
                    raise UpstreamUnavailable(
                        alias,
                        f"流空闲超时：{stream_cfg.idle_timeout:.0f}s 无新帧——判上游假死可切备",
                    ) from None
                except UpstreamError:
                    raise
                except Exception as exc:
                    raise classify_upstream_failure(alias, exc) from exc
                piece, frame_usage = _chunk_fields(chunk)
                if piece:
                    parts.append(piece)
                if frame_usage:
                    usage = frame_usage
        finally:
            await _aclose_stream(stream)

        duration_ms = int((time.monotonic() - started) * 1000)
        content = "".join(parts)
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

    async def embeddings(
        self, alias: str, texts: list[str], *, input_type: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> LlmEmbedding:
        """按注册表构造一次向量化调用（P1-11——B6 单点：embedding 只经此缝）。

        - 形状（2026-10-02 curl 实测，models.yaml 头注释同源）：POST
          {base_url}/v1/embeddings，Bearer 鉴权；体 `{"model", "texts",
          "type"}`——type 二选一 db（被检索文本）/query（检索文本），query/db
          分离算法必须分型调用；返回 `vectors[N][1536]`（已归一化）＋
          total_tokens＋base_resp（base_resp.status_code≠0＝业务失败）。
        - 切换判据与 complete 同款（椒图判据单点复用）；HTTP 层 4xx/5xx 与
          base_resp 业务错都走 classify_upstream_failure 同一分类面。
        - 密钥只进请求头，绝不入异常文本/日志；transport 形参＝测试注桩缝
          （httpx.MockTransport——生产恒 None 不经此参数）。
        """
        if not texts:
            raise ValueError("embeddings texts 不能为空")
        if input_type not in ("db", "query"):
            raise ValueError(f"input_type 越界：{input_type!r}（允许 db|query）")
        entry = _entry(alias)
        started = time.monotonic()
        try:
            async with httpx.AsyncClient(
                timeout=_timeout_seconds(entry), transport=transport
            ) as client:
                resp = await client.post(
                    f"{entry.base_url.rstrip('/')}/v1/embeddings",
                    headers={
                        "Authorization": f"Bearer {entry.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"model": entry.model, "texts": list(texts), "type": input_type},
                )
        except httpx.TimeoutException as exc:
            raise UpstreamUnavailable(alias, f"超时: {type(exc).__name__}") from exc
        except httpx.HTTPError as exc:
            raise UpstreamUnavailable(alias, f"网络错: {type(exc).__name__}") from exc
        except Exception as exc:
            raise classify_upstream_failure(alias, exc) from exc
        duration_ms = int((time.monotonic() - started) * 1000)
        if resp.status_code != 200:
            raise classify_upstream_failure(
                alias, _HttpStatusError(resp.status_code, _safe_body(resp))
            )
        payload = _parse_json(alias, resp)
        base = payload.get("base_resp") or {}
        status_code = int(base.get("status_code") or 0)
        if status_code != 0:
            # MiniMax 业务错（1004 鉴权失败/1002 限流族）——鉴权类 4xx 不可切
            raise classify_upstream_failure(
                alias,
                _HttpStatusError(
                    401 if status_code == 1004 else 502,
                    f"base_resp={base.get('status_code')}:{base.get('status_msg')}",
                ),
            )
        vectors = payload.get("vectors")
        if not isinstance(vectors, list) or any(not isinstance(v, list) for v in vectors):
            raise UpstreamRejected(alias, "vectors 形状不可解析")
        return LlmEmbedding(
            vectors=[[float(x) for x in v] for v in vectors],
            total_tokens=int(payload.get("total_tokens") or 0),
            duration_ms=duration_ms,
            model=f"{entry.provider}/{entry.model}",
        )


class _HttpStatusError(Exception):
    """HTTP 状态错的最小承载（喂 classify_upstream_failure 的形状适配）。"""

    def __init__(self, status_code: int, body: str) -> None:
        super().__init__(f"HTTP {status_code}: {body[:200]}")
        self.status_code = status_code


async def _frame_next(stream: Any) -> Any:
    """流迭代器单步（StopAsyncIteration 透传——消费循环的正常终点）。"""
    return await stream.__anext__()


def _get(obj: Any, key: str) -> Any:
    """帧字段取值——attr/mapping 双形兼容（litellm 帧对象与测试假帧）。"""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _chunk_fields(chunk: Any) -> tuple[str, dict[str, Any]]:
    """流帧 → (增量文本, usage 映射)。

    usage 兼容 dict 与 pydantic Usage 对象（litellm 流末帧＝Usage 实例非 dict，
    isinstance 闸会把它整个丢掉——计费静默降级为估算，审查 B/C 项回改）。
    """
    piece: Any = ""
    choices = _get(chunk, "choices")
    if choices:
        delta = _get(choices[0], "delta")
        piece = _get(delta, "content")
    usage: dict[str, Any] = {}
    frame_usage = _get(chunk, "usage")
    if frame_usage is not None:
        prompt = _get(frame_usage, "prompt_tokens")
        completion = _get(frame_usage, "completion_tokens")
        usage = {
            "prompt_tokens": int(prompt) if isinstance(prompt, (int, float)) else 0,
            "completion_tokens": int(completion) if isinstance(completion, (int, float)) else 0,
        }
    return (piece if isinstance(piece, str) else "", usage)


async def _aclose_stream(stream: Any) -> None:
    """关闭流释放连接（成功收流与异常弃流同径）。

    litellm 流对象＝CustomStreamWrapper——只有 aclose 没有 close（aclose 内部
    才真正释放底层 HTTP 连接）；close 兜底兼容测试假流。关闭失败不掩盖主路径异常。
    """
    aclose = getattr(stream, "aclose", None)
    if aclose is not None:
        try:
            out = aclose()
            if asyncio.iscoroutine(out):
                await out
        except Exception:  # 弃流清理面失败不掩盖主路径异常
            return
        return
    close = getattr(stream, "close", None)
    if close is None:
        return
    try:
        out = close()
        if asyncio.iscoroutine(out):
            await out
    except Exception:  # 同上——清理面静默
        pass


def _timeout_seconds(entry: ModelEntry) -> float:
    """per-attempt 超时＝gateway 段 request_timeout（同一配置面，D1 热加载生效）。"""
    return float(get_models_config().gateway.request_timeout)


def _safe_body(resp: httpx.Response) -> str:
    """错误体摘要（绝不回显请求头/密钥——响应体不含密钥，截断防刷屏）。"""
    try:
        return resp.text[:200]
    except Exception:
        return ""


def _parse_json(alias: str, resp: httpx.Response) -> dict[str, Any]:
    try:
        payload = resp.json()
    except Exception as exc:
        raise UpstreamRejected(alias, "响应体非 JSON") from exc
    return payload if isinstance(payload, dict) else {}
