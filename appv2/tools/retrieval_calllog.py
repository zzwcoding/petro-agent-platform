"""tools.retrieval_calllog —— doc_retrieve 旁路留痕（V2-89——入参＋候选命中）。

「检索调用留痕」唯一定义处：`doc_retrieve` 每次**成功返回前**（含空集）逐调用落
一行 JSONL 到 `logs/retrieval_calls/YYYYMMDD.jsonl`（按日分片，日期取
`infra.clock.now()`）。目的＝复跑 A-正6 时直接判「W-111 是否出现在候选中」
（`接手-EB7vsEB8送窗差异` 取不到③：入参 need/budget/family_hints 与候选命中
此前不在任何留痕面）。

记录键闭世界（票面字段表逐字）：
`{"ts", "run_id", "sub_question_id", "need", "top_k", "hits": [{"id", "source",
"score", "chars", "has_section"}], "returned", "truncated"}`
——`need`＝RetrievalNeed 四字段投影（question/anchors/family_hints/budget，
入参可查）；`hits`＝入窗候选逐条（片段 id／report 级来源／原始腿分／长面字符数／
section 标记），**零片段正文、零密钥**（不落全文——只字符数）。

开关 `RETRIEVAL_CALL_LOG`（缺省 on；`off`＝零写）；留痕故障只 `LOGGER.warning`，
绝不向调用方冒泡（旁路观测纪律——与 `infra.gateway.calllog` 同范式）。
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from appv2.infra.clock import ISO_FMT, now
from appv2.retrieval import Observation, RetrievalNeed

LOGGER = logging.getLogger(__name__)

_LOG_DIR = Path("logs/retrieval_calls")

_ENV_SWITCH = "RETRIEVAL_CALL_LOG"


def _enabled() -> bool:
    """开关（缺省 on；RETRIEVAL_CALL_LOG=off 零写）。"""
    return os.environ.get(_ENV_SWITCH, "on").strip().lower() != "off"


def _need_record(need: RetrievalNeed) -> dict[str, Any]:
    """入参投影（RetrievalNeed 四字段逐字——question/anchors/family_hints/budget）。"""
    return {
        "question": str(need.question or ""),
        "anchors": [str(anchor) for anchor in need.anchors],
        "family_hints": [str(hint) for hint in need.family_hints],
        "budget": int(need.budget),
    }


def _hit_record(observation: Observation) -> dict[str, Any]:
    """候选命中单条投影（id／report 级 source／原始腿分／字符数／section 标记）。

    `chars`＝长面（`text`）字符数——**只留数不留文**（不落全文/密钥）；图谱边
    无片段 id＝空串如实（零发明）。
    """
    return {
        "id": str(observation.fragment_id or ""),
        "source": str(observation.report or ""),
        "score": float(observation.score),
        "chars": len(observation.text or ""),
        "has_section": bool(observation.section),
    }


def record_retrieval_call(
    *,
    sub_question_id: str = "",
    need: RetrievalNeed,
    top_k: int,
    hits: Sequence[Observation],
    returned: int,
    run_id: str = "",
    recalled: int = 0,
) -> None:
    """单次 doc_retrieve 检索→一行 JSONL（入参＋逐候选命中；空集照记）。

    票面签名五参逐字（sub_question_id/need/top_k/hits/returned）＋两个 additive
    关键字（run_id/recalled，缺省零漂移——JSON 必填字段 `run_id` 与截断判据
    `recalled` 的值源，旧调用形零破坏）。

    - `hits`＝本次入窗候选（RetrievalBundle.observations 逐条）；`returned`＝
      入窗条数（调用方按实走支数报）；
    - `truncated`＝`recalled > returned`（召回池大于入窗＝候选被供给窗裁掉——
      window_note 主段「共检索到 N 条材料，M 条用进了答案」同判据）；`recalled`
      缺位（旧构造/桩＝0）＝不判截断（False，零猜测）；
    - 任何异常降级 `LOGGER.warning`——留痕故障不影响工具返回。
    """
    if not _enabled():
        return
    try:
        at = now()
        record = {
            "ts": at.strftime(ISO_FMT) if isinstance(at, datetime) else str(at),
            "run_id": str(run_id or ""),
            "sub_question_id": str(sub_question_id or ""),
            "need": _need_record(need),
            "top_k": int(top_k),
            "hits": [_hit_record(observation) for observation in hits],
            "returned": int(returned),
            "truncated": bool(recalled > returned),
        }
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        path = _LOG_DIR / f"{at:%Y%m%d}.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        LOGGER.warning("retrieval calllog 写入失败（降级不影响工具返回）", exc_info=True)
