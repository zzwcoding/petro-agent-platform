"""runtime.blackbox —— run 全程状态蒸馏与快照渲染（黑匣子语义单点——V2-54）。

「黑匣子记什么、怎么渲染」全仓唯一定义处：执行器收口发射（第①层——事件流出、
帧落盘器全量存档 SSE 故自动收录）与快照回放工具（第②层——tools/run_replay.py
薄胶水）共享本模块语义。纯函数零依赖（不触 clock/db/langgraph——B14/B3 与
ADR-0002 红线同守）。

排除键（体积与噪声面）：ledger_dump（词典层全量投影——巨体；回放按快照
ledger_dump 通道现渲染重建常驻注入）、manifests（逐步证据面——快照层在场）、
executed_payloads（执行指纹簿）、pending_* 内部机械态。
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

# ---------- 蒸馏白名单（final 状态键闭世界——新增状态键须显式入列） ----------

_DISTILL_KEYS: tuple[str, ...] = (
    "dialogue",
    "process_notes",
    "steps",
    "observations",
    "notices",
    "question_group",
    "precondition_verdicts",
    "resume_choices",
    "answer",
    "draft",
    "verdict",
    "rounds",
    "discover_used",
    "budget_hit",
    "pending_ask",
    "task_type",
    "window_miss_marks",
    "chain_switch_marks",
    "decision_error",
)

# ---------- 回放曲面通道白名单（蒸馏同族语义＋快照层超集） ----------

CURATED_CHANNELS: frozenset[str] = frozenset(
    {
        "question",
        "understanding",
        "task_type",
        "dialogue",
        "process_notes",
        "steps",
        "observations",
        "notices",
        "question_group",
        "precondition_verdicts",
        "resume_choices",
        "tool_matches",
        "subtask_results",
        "answer",
        "draft",
        "verdict",
        "rounds",
        "discover_used",
        "decision_error",
        "window_miss_marks",
        "chain_switch_marks",
        "budget_hit",
        "error",
        "status",
        "pending_ask",
    }
)


def distill(
    final: Mapping[str, Any] | None,
    *,
    run_id: str = "",
    error: str = "",
) -> dict[str, Any]:
    """运行终态→黑匣子记录（帧第①层与回放第②层共享的单一语义）。

    final=None（异常段无终态）＝骨架记录（身份面＋error，零状态键）；
    正常段按白名单拷贝状态键，外加 run_id/question/status/error 身份面。
    """
    record: dict[str, Any] = {
        "run_id": run_id,
        "question": "",
        "status": "",
        "error": error,
    }
    if final is None:
        return record
    for key in _DISTILL_KEYS:
        value = final.get(key)
        if value is None:
            continue
        record[key] = _plain(value)
    record["run_id"] = str(final.get("run_id") or run_id)
    record["question"] = str(final.get("question") or "")
    record["status"] = str(final.get("status") or "")
    return record


def pointer(
    record: Mapping[str, Any],
    *,
    stored: bool = False,
    bytes_written: int = 0,
) -> dict[str, Any]:
    """蒸馏记录→瘦指针（V2-55——wire 面只出指针防帧/仓膨胀，完整面在库）。

    帧落盘器全量存档 SSE 故指针即帧所载全部；过程档案经
    `agent_v2_blackbox` 表（RunStore.get_blackbox）或回放工具读取。
    """
    return {
        "run_id": str(record.get("run_id", "")),
        "question": str(record.get("question", "")),
        "status": str(record.get("status", "")),
        "error": str(record.get("error", "")),
        "stored": stored,
        "bytes": int(bytes_written),
        "counts": {
            "dialogue": len(record.get("dialogue") or []),
            "process_notes": len(record.get("process_notes") or []),
            "observations": len(record.get("observations") or []),
            "steps": len(record.get("steps") or []),
        },
    }


def render_snapshots(snapshots: list[dict[str, Any]], *, as_json: bool = False) -> str:
    """快照列→转写文本（人读缺省；as_json＝机器全量，直 dump 不再蒸馏）。"""
    if as_json:
        return json.dumps(snapshots, ensure_ascii=False, indent=2, default=str)
    lines: list[str] = []
    for snap in snapshots:
        lines.append(f"== 快照 {snap.get('checkpoint_id', '?')} ==")
        channels = snap.get("channels") or {}
        for name, value in channels.items():
            lines.extend(_render_channel(name, value))
    return "\n".join(lines)


# ---------- 内部位 ----------


def _plain(value: Any) -> Any:
    """状态值→JSON 安全面（Mapping/list 递归，非常规值降级 str——不因脏值翻车）。"""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return str(value)


def _head(value: str, limit: int = 96) -> str:
    text = value.replace("\n", " ⏎ ")
    return text if len(text) <= limit else text[:limit] + "…"


def _render_channel(name: str, value: Any) -> list[str]:
    """单通道→转写行（dialogue/process_notes/observations/steps 专属美化，其余短形）。"""
    if name == "dialogue" and isinstance(value, list):
        lines = [f"  dialogue（{len(value)} 轮）——自然对话层（用户原话与终稿）:"]
        for message in value:
            if isinstance(message, dict):
                role = str(message.get("role", "?"))
                content = str(message.get("content", ""))
            else:
                role, content = "?", str(message)
            lines.append(f"    [{role}] {_head(content)}")
        return lines
    if name == "process_notes" and isinstance(value, list):
        lines = [f"  process_notes（{len(value)} 条）——过程档案（有界摘要）:"]
        for note in value:
            if isinstance(note, dict):
                lines.append(
                    f"    [{note.get('phase', '?')}] "
                    f"{_head(str(note.get('title', '')), 30)}"
                    f"｜{_head(str(note.get('digest', '')), 80)}"
                )
            else:
                lines.append(f"    {_head(str(note))}")
        return lines
    if name == "observations" and isinstance(value, list):
        lines = [f"  observations（{len(value)} 支）——全字段:"]
        for obs in value:
            if not isinstance(obs, dict):
                lines.append(f"    {_head(str(obs))}")
                continue
            locator = obs.get("locator")
            kind = locator.get("kind", "-") if isinstance(locator, dict) else "-"
            source = str(obs.get("source", ""))
            lines.append(
                f"    [{obs.get('index')}] kind={kind} trust={obs.get('trust', '-')}"
                f" 源={_head(source, 40)}"
            )
            lines.append(f"        {_head(str(obs.get('content', '')))}")
        return lines
    if name == "steps" and isinstance(value, list):
        lines = [f"  steps（{len(value)} 条）:"]
        for step in value:
            if not isinstance(step, dict):
                lines.append(f"    {_head(str(step))}")
                continue
            lines.append(
                f"    [{step.get('seq')}] {step.get('step')}"
                f" {_head(str(step.get('title', '')), 60)}"
            )
            payload = step.get("payload")
            if payload:
                lines.append(f"        payload {_head(str(payload))}")
        return lines
    if isinstance(value, list):
        return [f"  {name}（{len(value)} 条）: {_head(str(value))}"]
    return [f"  {name}: {_head(str(value))}"]
