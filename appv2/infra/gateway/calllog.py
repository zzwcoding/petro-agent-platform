"""infra.gateway.calllog —— LLM 调用全量留痕（V2-80f——发送 messages＋返回全文）。

「LLM 收发完整记录」唯一定义处：gateway.complete（B6 唯一出口）逐调用落一行
JSONL 到 logs/llm_calls/YYYYMMDD.jsonl（按日分文件）——发送 messages 逐条全文、
返回 content 全文、token/耗时/路由别名、run_id/caller 归属；失败尝试（429/超时/
切换）同样留痕（error 字段）。开关 LLM_CALL_LOG（缺省 on，off＝零写）；留痕故障
绝不影响调用（异常降级 LOGGER.warning）。

注意：JSONL 含完整 messages（含系统提示词）——logs/ 目录不入仓（.gitignore），
生产环境若启用需自行管控文件权限。
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from appv2.infra.clock import ISO_FMT, now

LOGGER = logging.getLogger(__name__)

_LOG_DIR = Path("logs/llm_calls")


def _enabled() -> bool:
    """开关（缺省 on；LLM_CALL_LOG=off 零写）。"""
    return os.environ.get("LLM_CALL_LOG", "on").strip().lower() != "off"


def record_call(
    *,
    alias: str,
    caller: str,
    run_id: str,
    messages: list[dict[str, Any]],
    requested: str = "",
    content: str | None = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    cached_tokens: int = 0,
    duration_ms: int = 0,
    error: str | None = None,
) -> None:
    """单次调用→一行 JSONL（成功记 response；失败记 error——发送面同样全留）。

    任何异常降级 LOGGER.warning——留痕故障不影响调用（旁路观测纪律）。
    """
    if not _enabled():
        return
    try:
        at = now()
        rec = {
            "ts": at.strftime(ISO_FMT) if isinstance(at, datetime) else str(at),
            "run_id": str(run_id or ""),
            "caller": str(caller or ""),
            "requested": str(requested or ""),
            "alias": str(alias or ""),
            "messages": messages,
            "response": None
            if error
            else {
                "content": content or "",
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cached_tokens": cached_tokens,
                "duration_ms": duration_ms,
            },
            "error": error,
        }
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        path = _LOG_DIR / f"{at:%Y%m%d}.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        LOGGER.warning("llm calllog 写入失败（降级不影响调用）", exc_info=True)

