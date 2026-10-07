#!/usr/bin/env python3
"""L-04 轻量跑批脚本——golden 意图回归闸（闸 B 硬闸载体）＋判分辅助表。

用法：
    # 全量实跑（对本地起服——服务地址照 rerun.py 惯例走 RERUN_BASE）：
    RERUN_BASE=http://localhost:8000 uv run python eval/results/tools/plan_rerun.py \
        --tag L04G --sleep 2
    # 离线自检（不起服：golden schema 校验＋提取/判定纯函数内置判例）：
    uv run python eval/results/tools/plan_rerun.py --tag SMOKE --dry-run

纪律（沿用 rerun.py／eval/README）：题干原句不改写；每题只问一遍、脚本自身零重试；
SSE 帧全量存档 eval/results/frames/{tag}-{qid}.json；题间间隔 --sleep。
增量（票面交付物②）：意图机器判——从帧提取实际槽位与 golden 期望逐字段等值比对
（字段集与 L-01 compare_query_plans PLAN_COMPARE_FIELDS 同源：metric_slot /
window.start / window.end / limit_effective / ranking / direction）。
退出码＝机器判结果（全绿 0、有红 1）；答案数值部分只进判分辅助表（人审件），
不进退出码——闸看机器判、人审看辅助表，两不相混（票内定案）。
实际槽位提取口径（票内定案）：N7.1 finish 节点行解析为主，N7.3 模板 SQL 行取窗
端点/排名/方向/条数，verdict slots 佐证；解析失败＝该题落「人审列」不进机器判绿红。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence

import httpx

sys.path.insert(0, str(Path(__file__).parent))

from ask import parse_frames, parse_sse_text  # noqa: E402

BASE = os.environ.get("RERUN_BASE", "http://localhost:8000")
HEADERS = {"X-Dev-User": "aqiang"}
FRAMES_DIR = Path(__file__).parent.parent / "frames"
DEFAULT_GOLDEN = Path(__file__).parent.parent / "golden" / "plan-golden-v1.json"

# —— 机器判三态（绿/红进退出码；人审不进）——
JUDGE_GREEN = "绿"
JUDGE_RED = "红"
JUDGE_HUMAN = "人审"

# 执行语义字段集（与 L-01 compare_query_plans PLAN_COMPARE_FIELDS 同源口径——
# app/domains/chat/domain.py:1719；window.label/is_default 记注记不判分歧）。
GOLDEN_JUDGE_FIELDS: tuple[str, ...] = (
    "metric_slot", "window.start", "window.end", "limit_effective", "ranking", "direction",
)

EXPECTED_PATH_FAST = "快路"
EXPECTED_PATH_SLOW = "慢路触发"
EXPECTED_PATH_NONE = "不触发"

# —— N7.1 finish 节点行解析（主口径——「指标＝{slot}（台账「{name}」）· 时间＝{label}
# · 条数＝{n}」，默认窗尾注「（默认窗——问句无显式时间）」；chains.py N7.1 现行文案）——
_N71_OK_PREFIX = "三要素齐："
_N71_METRIC_RE = re.compile(r"指标＝(.+?)（台账「(.+?)」）")
_N71_DEGRADE_MARK = "指标槽位未命中"
_N71_ASKBACK_MARK = "时间窗缺参"
# —— N7.3 模板 SQL 行解析（窗端点/排名/方向/条数——render_plan_sql 现行形状）——
_SQL_WINDOW_RE = re.compile(r"m\.prod_date >= '(\d{4}-\d{2}-\d{2})' AND m\.prod_date < '(\d{4}-\d{2}-\d{2})'")
_SQL_RANK_MARK = "GROUP BY w.well_id"
_SQL_DIRECTION_RE = re.compile(r"ORDER BY SUM\([^)]*\)\s*(ASC|DESC)")
_SQL_LIMIT_RE = re.compile(r"LIMIT\s+(\d+)")
# —— verdict slots 佐证（「指标＝{slot} · …」）——
_VERDICT_METRIC_RE = re.compile(r"指标＝([^\s·]+)")
_N72_EXTABLE_RE = re.compile(r"外表 (.+?) 不在本轮选表命中集")


@dataclass(frozen=True, slots=True)
class ExtractedSlots:
    """帧 → 实际槽位提取结果（ok=三要素齐行在案；失败携 reason 落人审列）。"""

    ok: bool
    reason: str = ""
    metric_slot: str | None = None
    window_start: str | None = None
    window_end: str | None = None
    limit_effective: int | None = None
    ranking: bool | None = None
    direction: str | None = None  # 明细模板 ORDER BY 无方向字面——不可提取＝None
    verdict_metric: str | None = None
    chain: str | None = None
    n71_note: str = ""
    extable_named: tuple[str, ...] = ()  # N7.2 外表点名行（辅助列——不进机器判）

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok, "reason": self.reason, "metric_slot": self.metric_slot,
            "window_start": self.window_start, "window_end": self.window_end,
            "limit_effective": self.limit_effective, "ranking": self.ranking,
            "direction": self.direction, "verdict_metric": self.verdict_metric,
            "chain": self.chain, "extable_named": list(self.extable_named),
        }


def extract_plan_slots(frames: Sequence[Mapping[str, Any]]) -> ExtractedSlots:
    """SSE 帧 → 实际槽位（票内定案提取口径：N7.1 行为主、N7.3 SQL 佐证、verdict 佐证）。"""
    metric = window = None
    n71_note = ""
    chain: str | None = None
    verdict_metric: str | None = None
    sql_text = ""
    extable: list[str] = []
    for f in frames:
        name, data = f.get("event"), f.get("data") or {}
        if name == "verdict":
            chain = data.get("chain")
            m = _VERDICT_METRIC_RE.search(str(data.get("slots") or ""))
            if m is not None:
                verdict_metric = m.group(1)
        elif name == "node" and data.get("key") == "N7.1" and data.get("state") == "finish":
            note = str(data.get("note") or "")
            if note.startswith(_N71_OK_PREFIX):
                metric, n71_note = note, note
                mm = _N71_METRIC_RE.search(note)
                if mm is not None:
                    metric = mm.group(1)
            elif _N71_DEGRADE_MARK in note:
                return ExtractedSlots(ok=False, reason="降级解释链（解析缺件）——未产计划",
                                      chain=chain, n71_note=note)
            elif _N71_ASKBACK_MARK in note:
                return ExtractedSlots(ok=False, reason="缺参反问（模糊时间窗）——未产计划",
                                      chain=chain, n71_note=note)
        elif name == "node_line" and data.get("key") == "N7.3":
            text = str(data.get("text") or "")
            if "模板装配 SQL" in text:
                sql_text = text
        elif name == "node_line" and data.get("key") == "N7.2":
            m = _N72_EXTABLE_RE.search(str(data.get("text") or ""))
            if m is not None:
                extable.append(m.group(1))
    if not n71_note:
        return ExtractedSlots(ok=False, reason=f"未产计划（chain={chain or '未知'}——无 N7.1 三要素齐行）",
                              chain=chain, verdict_metric=verdict_metric)
    window_start = window_end = None
    limit_effective: int | None = None
    ranking: bool | None = None
    direction: str | None = None
    if sql_text:
        wm = _SQL_WINDOW_RE.search(sql_text)
        if wm is not None:
            window_start, window_end = wm.group(1), wm.group(2)
        lm = _SQL_LIMIT_RE.search(sql_text)
        if lm is not None:
            limit_effective = int(lm.group(1))
        ranking = _SQL_RANK_MARK in sql_text
        dm = _SQL_DIRECTION_RE.search(sql_text)
        if dm is not None:
            direction = dm.group(1).lower()
    return ExtractedSlots(
        ok=True,
        metric_slot=metric,
        window_start=window_start,
        window_end=window_end,
        limit_effective=limit_effective,
        ranking=ranking,
        direction=direction,
        verdict_metric=verdict_metric,
        chain=chain,
        n71_note=n71_note,  # 整行保留（时间标签＋默认窗尾注——辅助表与注记消费）
        extable_named=tuple(extable),
    )


@dataclass(frozen=True, slots=True)
class PlanJudgment:
    """机器判结果（绿/红进退出码；人审列不进——票内定案两不相混）。"""

    status: str
    divergent_fields: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


def judge_intent(
    expected: Mapping[str, Any] | None,
    actual: ExtractedSlots,
    *,
    expected_path: str = EXPECTED_PATH_FAST,
) -> PlanJudgment:
    """意图比对纯函数（票面交付物②——golden 期望 vs 帧提取实际逐字段等值）。

    三路：逐字段等值→绿；字段缺失/值分歧→红并列明字段；期望缺件（whole 或
    字段级 None）→人审/跳判。解析失败→人审列不进机器判绿红（票内定案）。
    expected_path=不触发 的触发边界题另守「不产问数计划」边界（破界即红）。
    """
    if expected_path == EXPECTED_PATH_NONE:
        if actual.ok:
            return PlanJudgment(
                JUDGE_RED, ("metric_slot",),
                (f"触发边界破：期望不触发却产了计划（{actual.metric_slot}）——不该快路直进却直进",),
            )
        return PlanJudgment(JUDGE_GREEN, (), (f"边界守住（{actual.reason}）",))
    if not actual.ok:
        return PlanJudgment(JUDGE_HUMAN, (), (f"解析失败——{actual.reason}；落人审列",))
    if expected is None:
        return PlanJudgment(JUDGE_HUMAN, (), ("期望缺件（expected_intent=null——本批慢路题不钉五槽位）",))
    win = expected.get("window") or {}
    exp: dict[str, Any] = {
        "metric_slot": expected.get("metric_slot"),
        "window.start": win.get("start"),
        "window.end": win.get("end"),
        "limit_effective": expected.get("limit_effective"),
        "ranking": expected.get("ranking"),
        "direction": expected.get("direction"),
    }
    act: dict[str, Any] = {
        "metric_slot": actual.metric_slot,
        "window.start": actual.window_start,
        "window.end": actual.window_end,
        "limit_effective": actual.limit_effective,
        "ranking": actual.ranking,
        "direction": actual.direction,
    }
    divergent: list[str] = []
    notes: list[str] = []
    for fname in GOLDEN_JUDGE_FIELDS:
        if exp[fname] is None:
            continue  # 期望缺件——该字段不判（明细题 direction 不钉同此）
        if act[fname] is None:
            divergent.append(fname)
            notes.append(f"{fname}：实际侧缺件（帧未提取到）")
        elif act[fname] != exp[fname]:
            divergent.append(fname)
            notes.append(f"{fname}：期望 {exp[fname]!r} ≠ 实际 {act[fname]!r}")
    if (
        actual.verdict_metric is not None
        and actual.metric_slot is not None
        and actual.verdict_metric != actual.metric_slot
    ):
        if "metric_slot" not in divergent:
            divergent.append("metric_slot")
        notes.append(
            f"verdict slots 佐证矛盾：verdict={actual.verdict_metric!r} vs N7.1={actual.metric_slot!r}"
        )
    if expected_path == EXPECTED_PATH_SLOW and not divergent:
        notes.append("慢路预期题被快路解出——「触发但快路可解」过宽桶实证（注记归 L-03 分桶，不判绿红）")
    status = JUDGE_RED if divergent else JUDGE_GREEN
    return PlanJudgment(status, tuple(divergent), tuple(notes))


def window_pin_stale(q: Mapping[str, Any], *, today: date, anchor_date: date) -> bool:
    """golden 窗口锚过期判（相对窗按执行日重锚——锚过期落人审并提示重锚，不机器判）。

    - rule=去年：锚定年内稳定（当年任意日有效）——跨年过期；
    - 其余（今年/本月/默认窗/近 N/……）：窗端点随执行日漂移——仅锚定日当日有效；
    - expected_intent=None（无窗可锚）→永不过期。
    """
    intent = q.get("expected_intent")
    if not isinstance(intent, Mapping):
        return False
    rule = str((intent.get("window") or {}).get("rule") or "")
    if rule == "去年":
        return today.year != anchor_date.year
    return today != anchor_date


# ---------- golden 载入与校验 ----------

FAMILY_COUNTS = {"三指标×快路": 6, "慢路触发": 6, "默认窗": 2, "触发边界": 4, "红例族": 6}
BOUND_METRICS = ("日产油量", "日产液量", "油压")
_INTENT_KEYS = {"metric_slot", "window", "limit_requested", "limit_effective", "ranking", "direction"}


def load_golden(path: str | Path) -> dict[str, Any]:
    """golden JSON 载入＋schema 闸（24 题五族矩阵/qid 唯一/必填字段——本体进测试闸）。"""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    questions = raw.get("questions")
    if not isinstance(questions, list) or not questions:
        raise ValueError("golden 缺 questions 非空数组")
    qids: set[str] = set()
    counts: dict[str, int] = {}
    for q in questions:
        for key in ("qid", "family", "question", "expected_path", "answer_essentials", "tags"):
            if not q.get(key):
                raise ValueError(f"{q.get('qid', '?')} 缺必填字段 {key}")
        if q["qid"] in qids:
            raise ValueError(f"qid 重复：{q['qid']}")
        qids.add(q["qid"])
        if q["expected_path"] not in (EXPECTED_PATH_FAST, EXPECTED_PATH_SLOW, EXPECTED_PATH_NONE):
            raise ValueError(f"{q['qid']} expected_path 非法：{q['expected_path']}")
        if q.get("anchor_scope") not in ("day", "year"):
            raise ValueError(f"{q['qid']} anchor_scope 必须是 day/year")
        counts[q["family"]] = counts.get(q["family"], 0) + 1
        intent = q.get("expected_intent")
        if intent is not None:
            if set(intent) - _INTENT_KEYS:
                raise ValueError(f"{q['qid']} expected_intent 含白名单外键 {set(intent) - _INTENT_KEYS}")
            if intent.get("metric_slot") not in BOUND_METRICS:
                raise ValueError(f"{q['qid']} metric_slot 不在三绑定指标：{intent.get('metric_slot')}")
        if q["expected_path"] == EXPECTED_PATH_SLOW and intent is not None:
            raise ValueError(f"{q['qid']} 慢路题本批不钉意图（期望缺件），expected_intent 须为 null")
        if not isinstance(q["tags"], list) or not q["tags"]:
            raise ValueError(f"{q['qid']} tags 须非空数组（覆盖标签）")
    if counts != FAMILY_COUNTS:
        raise ValueError(f"覆盖矩阵与票面分配不符：{counts}（应 {FAMILY_COUNTS}）")
    return raw


# ---------- 少样本构建替身（票面交付物③——L-02 未合入的接口形状验证件）----------

DRAFT_ALLOWED_KEYS = ("metric_slot", "window", "limit_requested", "ranking", "direction")

FEWSHOT_SYSTEM_PROMPT = (
    "你是问数入口的意图解析器。把用户问句翻译成受约束的 JSON 源槽位意图草案："
    "只准产 metric_slot/window/limit_requested/ranking/direction 五键；"
    "metric_slot 只能取注册指标（日产油量/日产液量/油压）；window 用半开区间 "
    "{start,end}（ISO 日期）；limit_requested 只填问句显式条数（没写为 null）；"
    "ranking 布尔；direction 取 asc/desc。禁止产 actor/measure_column/unit/"
    "metric_name/limit_effective/external_tables——那些由服务端重推导。"
)


def golden_intent_to_draft_payload(intent: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """golden 期望意图 → QueryPlanDraft 五源槽位载荷（与 domain.DRAFT_ALLOWED_KEYS 同形）。"""
    if intent is None:
        return None
    win = intent.get("window") or {}
    return {
        "metric_slot": intent.get("metric_slot"),
        "window": {"start": win.get("start"), "end": win.get("end")},
        "limit_requested": intent.get("limit_requested"),
        "ranking": bool(intent.get("ranking")),
        "direction": intent.get("direction") or "desc",
    }


def build_fewshot_messages(
    samples: Sequence[Mapping[str, Any]],
    *,
    k: int = 3,
    system_prompt: str = FEWSHOT_SYSTEM_PROMPT,
) -> list[dict[str, str]]:
    """golden 样例 → messages（方案 §2.1 输入契约形状：system＋K 组问句/意图交替）。

    L-02 构建器未合入：本替身按 golden 顺序取前 K 条「有意图」样例（期望缺件题
    跳过，不产 null 载荷）；L-02 合入后由其构建器替换——messages 形状即对接合同。
    """
    msgs: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    taken = 0
    for s in samples:
        if taken >= k:
            break
        payload = golden_intent_to_draft_payload(s.get("expected_intent"))
        if payload is None:
            continue
        msgs.append({"role": "user", "content": str(s["question"])})
        msgs.append({"role": "assistant", "content": json.dumps(payload, ensure_ascii=False)})
        taken += 1
    return msgs


# ---------- 跑批主流程（形态照 rerun.py：HTTP 流式、帧存档、题间间隔、零重试）----------


async def ask_once(c: httpx.AsyncClient, question: str) -> dict[str, Any]:
    t0 = time.monotonic()
    async with c.stream(
        "POST", f"{BASE}/api/chat/asks", json={"question": question}, headers=HEADERS
    ) as resp:
        if resp.status_code != 200:
            body = (await resp.aread()).decode("utf-8", "replace")
            return {"error": {"status": resp.status_code, "body": body[:400]}}
        chunks: list[str] = []
        async for piece in resp.aiter_text():
            chunks.append(piece)
    raw = "".join(chunks)
    frames = parse_sse_text(raw)
    parsed = parse_frames(frames)
    parsed["duration_s"] = round(time.monotonic() - t0, 1)
    return {"frames": frames, "parsed": parsed}


def judge_row(
    q: Mapping[str, Any], data: Mapping[str, Any], *, today: date, anchor_date: date
) -> tuple[PlanJudgment, ExtractedSlots]:
    """单题判定（窗口锚过期优先落人审；其余走意图比对纯函数）。"""
    frames = data.get("frames") or []
    extracted = extract_plan_slots(frames)
    if window_pin_stale(q, today=today, anchor_date=anchor_date):
        note = (
            f"窗口锚过期（anchor_date={anchor_date} ≠ today={today}，"
            f"anchor_scope={q.get('anchor_scope')}）——按执行日重锚 golden 后机器判"
        )
        return PlanJudgment(JUDGE_HUMAN, (), (note,)), extracted
    judgment = judge_intent(
        q.get("expected_intent"), extracted, expected_path=str(q.get("expected_path") or EXPECTED_PATH_FAST)
    )
    return judgment, extracted


async def run_batch(args: argparse.Namespace) -> int:
    golden = load_golden(args.golden)
    anchor_date = date.fromisoformat(str(golden["anchor_date"]))
    today = date.today()
    questions: list[dict[str, Any]] = list(golden["questions"])
    if args.limit:
        questions = questions[: args.limit]
    out_path = FRAMES_DIR.parent / f"{args.tag}-plan判定.jsonl"
    print(f"golden={args.golden}（{len(questions)} 题 · anchor={anchor_date} · today={today}）")
    print(f"BASE={BASE} 判定表→{out_path} 帧存档→{FRAMES_DIR}/{args.tag}-*.json")

    counts = {JUDGE_GREEN: 0, JUDGE_RED: 0, JUDGE_HUMAN: 0}
    reds: list[str] = []
    done = 0
    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=10, read=300, write=10, pool=10)) as c:
        with out_path.open("a", encoding="utf-8") as out:
            for q in questions:
                qid = str(q["qid"])
                row: dict[str, Any] = {
                    "qid": qid, "family": q["family"], "question": q["question"],
                    "expected_path": q["expected_path"], "tags": q["tags"],
                    "answer_essentials": q["answer_essentials"],
                }
                try:
                    data = await ask_once(c, q["question"])
                except Exception as exc:  # noqa: BLE001 —— 单题失败不断跑批（rerun.py 同款）
                    row["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
                    row["machine"] = JUDGE_HUMAN
                    row["notes"] = [f"请求失败落人审列：{row['error'][:120]}"]
                    counts[JUDGE_HUMAN] += 1
                    out.write(json.dumps(row, ensure_ascii=False) + "\n")
                    out.flush()
                    done += 1
                    print(f"[{done}/{len(questions)}] {qid} ⚠ 请求失败 {row['error'][:80]}")
                    await asyncio.sleep(args.sleep)
                    continue
                frame_path = FRAMES_DIR / f"{args.tag}-{qid}.json"
                frame_path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
                judgment, extracted = judge_row(q, data, today=today, anchor_date=anchor_date)
                counts[judgment.status] += 1
                if judgment.status == JUDGE_RED:
                    reds.append(qid)
                p = data.get("parsed") or {}
                row.update({
                    "machine": judgment.status,
                    "divergent": list(judgment.divergent_fields),
                    "notes": list(judgment.notes),
                    "extracted": extracted.as_dict(),
                    "expected_intent": q.get("expected_intent"),
                    "chain": extracted.chain or p.get("chain"),
                    "answer_head": (p.get("answer_text") or "")[:160],
                    "duration_s": p.get("duration_s"),
                    "frame_file": frame_path.name,
                    "error": data.get("error"),
                })
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
                out.flush()
                done += 1
                mark = {JUDGE_GREEN: "✓", JUDGE_RED: "✗", JUDGE_HUMAN: "人"}[judgment.status]
                print(
                    f"[{done}/{len(questions)}] {qid} {mark} {judgment.status}"
                    + (f" 分歧={'/'.join(judgment.divergent_fields)}" if judgment.divergent_fields else "")
                )
                await asyncio.sleep(args.sleep)
    print(f"\n完成 {done} 题：绿 {counts[JUDGE_GREEN]} ／ 红 {counts[JUDGE_RED]} ／ 人审 {counts[JUDGE_HUMAN]}")
    print(f"判定表：{out_path}")
    if reds:
        print(f"机器判红题（退出码 1）：{'、'.join(reds)}")
        return 1
    print("机器判全绿（退出码 0；人审列数值对照 answer_essentials × answer_head）")
    return 0


# ---------- 离线自检（--dry-run：不起服——golden 闸＋提取/判定内置判例）----------


def _selftest_frames_ok() -> list[dict[str, Any]]:
    return [
        {"event": "verdict", "data": {"chain": "状态机六站链", "slots": "指标＝日产油量 · 报告＝《R》"}},
        {"event": "node", "data": {"key": "N7.1", "state": "finish",
                                   "note": "三要素齐：指标＝日产油量（台账「日产油量（吨）」）· "
                                           "时间＝去年 · 条数＝50——确定性校验通过"}},
        {"event": "node_line", "data": {"key": "N7.3", "text": (
            "模板装配 SQL：\nSELECT w.well_id AS 井号, SUM(m.oil_output) AS t\n"
            "FROM agg.fct_daily_metering m JOIN agg.dim_well w ON w.well_id = m.well_id\n"
            "WHERE m.prod_date >= '2025-01-01' AND m.prod_date < '2026-01-01'\n"
            "GROUP BY w.well_id\nORDER BY SUM(m.oil_output) DESC\nLIMIT 50")}},
    ]


def selftest() -> list[tuple[str, bool, str]]:
    """内置判例（与 tests/tools/test_plan_golden_judge.py 同口径的离线最小集）。"""
    expected = {
        "metric_slot": "日产油量",
        "window": {"rule": "去年", "start": "2025-01-01", "end": "2026-01-01"},
        "limit_effective": 50, "ranking": True, "direction": "desc",
    }
    ext = extract_plan_slots(_selftest_frames_ok())
    j = judge_intent(expected, ext)
    checks = [
        ("提取-排名全槽位", ext.ok and ext.window_start == "2025-01-01" and ext.direction == "desc", ""),
        ("判定-逐字段等值绿", j.status == JUDGE_GREEN, j.notes and str(j.notes) or ""),
        ("判定-字段缺失红", judge_intent(expected, ExtractedSlots(ok=True, metric_slot="日产油量")).status == JUDGE_RED, ""),
        ("判定-期望缺件人审", judge_intent(None, ext).status == JUDGE_HUMAN, ""),
        ("边界-不触发守住绿", judge_intent(None, ExtractedSlots(ok=False, reason="x"),
                                          expected_path=EXPECTED_PATH_NONE).status == JUDGE_GREEN, ""),
        ("边界-不触发破界红", judge_intent(None, ext, expected_path=EXPECTED_PATH_NONE).status == JUDGE_RED, ""),
        ("锚-去年年内有效", not window_pin_stale({"expected_intent": expected},
                                                today=date(2026, 10, 7), anchor_date=date(2026, 10, 7)), ""),
        ("锚-跨年过期", window_pin_stale({"expected_intent": expected},
                                        today=date(2027, 1, 1), anchor_date=date(2026, 10, 7)), ""),
    ]
    return [(name, ok, note) for name, ok, note in checks]


async def main() -> int:
    ap = argparse.ArgumentParser(description="L-04 golden 意图回归闸跑批（机器判退出码）")
    ap.add_argument("--golden", default=str(DEFAULT_GOLDEN))
    ap.add_argument("--tag", required=True, help="帧存档与判定表前缀（如 L04G）")
    ap.add_argument("--sleep", type=float, default=2.0, help="题间间隔秒")
    ap.add_argument("--limit", type=int, default=0, help="只跑前 N 题（冒烟用；0=全量）")
    ap.add_argument("--dry-run", action="store_true", help="离线自检：不起服，golden 闸＋内置判例")
    args = ap.parse_args()

    golden = load_golden(args.golden)  # schema 闸——不合法即异常退出非零
    matrix = golden.get("coverage_matrix") or {}
    signoff = golden.get("owner_signoff") or {}
    print(f"golden 闸过：{len(golden['questions'])} 题 · 矩阵={matrix} · "
          f"Owner 签认={'已签' if signoff.get('approved') else '未签（golden 不算数——拍板 5）'}")
    if args.dry_run:
        failures = [c for c in selftest() if not c[1]]
        for name, ok, _note in selftest():
            print(f"  {'✓' if ok else '✗'} {name}")
        if failures:
            print(f"自检失败 {len(failures)} 项")
            return 1
        print("离线自检全过（提取/判定/锚新鲜度内置判例）")
        return 0
    return await run_batch(args)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
