#!/usr/bin/env python3
"""L-03b 影子定向补测报告（意图命中率口径——L-03 首轮报告的 addendum）。

用法：
    # 实跑报告（影子日志＋SSE 帧＋题集三源联判，离线聚合零网络零模型）：
    uv run python eval/results/tools/shadow_report_addendum.py \
        --log logs/shadow-plan.jsonl --prior-log eval/results/frames/L03S-shadow-log-sample.jsonl \
        --tag L03B
    # 离线自检（零文件零网络——内置判例手算对账）：
    uv run python eval/results/tools/shadow_report_addendum.py --dry-run

口径（票面定案——定向补测流量：非 golden、不进题册、影子期质量代理指标）：
  意图命中率＝LLM 草案逐字段对出题人标签（author_intent）打分。影子观测件不落
  LLM 草案字段值（L-02 设计：草案只进比对不落日志），可判性受观测能力约束：
  - draft_state=一致   → LLM 六字段＝确定性解析（SSE 帧提取）→ 逐字段可判；
  - draft_state=分歧   → 非 divergent 字段＝确定性值可判；divergent 字段 LLM 真值
    不落日志 → 记「不可观测」（单列不进命中分母）；
  - draft_state=不可比＋note 含「确定性解析侧」→ LLM 草案产出且过 validator
    （在册指标）但具体值不落日志 → 全字段「不可观测」；
  - draft_state=不可比＋note 含「validator 拒：」→ 拒因明细携 LLM 给的
    metric_slot 值 → metric 单字段可判（对/错）；其余字段不可观测；
  - 其余（LLM 拒产/坏 JSON/异常）→ metric=「未产出」；无影子行 →「未调 LLM」。
  对照组（expected_trigger=false）不打意图分——只验证「不触发」。
四项数字（一致率三分桶/触发双分桶/延迟/token）复用 shadow_report.aggregate：
本轮行＝question ∈ 题集问句集；合并视图＝首轮样本 13 行＋本轮行。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

from ask import parse_sse_text
from plan_rerun import extract_plan_slots
from shadow_report import (
    BUCKET_OVERNARROW,
    BUCKET_OVERWIDE,
    STATE_DIVERGE,
    STATE_INCOMPARABLE,
    STATE_MATCH,
    aggregate,
    file_sha256,
    load_rows,
    pct,
)

TRAFFIC = Path(__file__).parent.parent / "golden" / "shadow-extra-traffic-L03b.json"
FRAMES_DIR = Path(__file__).parent.parent / "frames"

# 意图判定值域（judge_verdict 字段级）：对/错＝有 LLM 值证据且与标签比对完；不可观测＝
# LLM 真值不落日志；未产出＝LLM 无有效草案；未调＝LLM#plan 未被调；补窗＝模糊窗题
# LLM 侧补了具体窗（形态判例——缺的是用户事实，不判对错）。
V_HIT, V_MISS, V_OPAQUE = "对", "错", "不可观测"
V_ABSENT, V_UNCALLED, V_MADEUP = "未产出", "未调", "补窗形态"
INTENT_FIELDS = ("metric_slot", "window.start", "window.end", "ranking", "direction", "limit")
BOUND_METRICS = ("日产油量", "日产液量", "油压")
_REJECT_METRIC_RE = re.compile(r"metric_slot '([^']+)'")
_CHAIN_FAST = "状态机六站链"
_CHAIN_RETRIEVAL = "检索问答链"


def expected_window(rule: str, *, today: date) -> tuple[str, str] | None:
    """author_intent.window_rule → 期望窗端点（执行日实算——与 golden 锚机制同源语义）。

    模糊窗（模糊最近/模糊近期）返回 None——期望＝系统不产窗（缺参反问），LLM 补窗
    记形态判例不判对错。
    """
    if rule == "默认窗":
        return (str(today - timedelta(days=30)), str(today))
    if rule == "本月":
        return (str(today.replace(day=1)), str(today))
    if rule == "上月":
        start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        return (str(start), str(today.replace(day=1)))
    if rule == "去年":
        return (f"{today.year - 1}-01-01", f"{today.year}-01-01")
    return None  # 模糊最近/模糊近期


def parse_frames_file(path: Path) -> list[dict[str, Any]]:
    return parse_sse_text(path.read_text(encoding="utf-8", errors="replace"))


def frame_chain(frames: list[dict[str, Any]]) -> str:
    for f in frames:
        if f.get("event") == "verdict":
            chain = (f.get("data") or {}).get("chain")
            if chain:
                return str(chain)
    return ""


@dataclass(slots=True)
class IntentScore:
    """单题意图判定（逐字段值域见 V_* 常量；details 携判定依据进逐题表）。"""

    fields: dict[str, str] = field(default_factory=dict)
    details: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        for name in INTENT_FIELDS:
            self.fields.setdefault(name, V_OPAQUE)


def judge_intent(
    q: dict[str, Any],
    *,
    shadow_row: dict[str, Any] | None,
    frames: list[dict[str, Any]],
    today: date,
) -> tuple[str, IntentScore]:
    """单题形态＋意图判定（口径见模块 docstring——观测能力约束下的如实打分）。"""
    intent = q["author_intent"]
    exp_win = expected_window(str(intent["window_rule"]), today=today)
    exp_limit_eff = 50 if intent["limit_requested"] is None else int(intent["limit_requested"])
    score = IntentScore()
    vague = str(intent["window_rule"]).startswith("模糊")

    chain = frame_chain(frames)
    if not shadow_row:
        if chain != _CHAIN_FAST:
            form = "未触发（预期内——对照组）" if not q["expected_trigger"] else \
                f"未入链（verdict 裁决 {chain or '未知'}——LLM#plan 未被调）"
            for name in INTENT_FIELDS:
                score.fields[name] = V_UNCALLED
            return form, score
        if not q["expected_trigger"]:
            # 入六站链但谓词未触发（词面齐＋锚在册→快路可解直出）——无影子行是设计内。
            for name in INTENT_FIELDS:
                score.fields[name] = V_UNCALLED
            return "快路可解（谓词未触发——预期内，帧 N7.1 三要素齐）", score
        return "链内无影子行（意外形态——登记）", score

    trigger = str(shadow_row.get("trigger") or "")
    state = str(shadow_row.get("draft_state") or "")
    note = str(shadow_row.get("note") or "")
    if not trigger:
        form = f"过窄观测（{state}——{note[:40]}）" if note else f"过窄观测（{state}）"
        for name in INTENT_FIELDS:
            score.fields[name] = V_UNCALLED
        return form, score

    # —— 触发比对行：LLM 已被调 ——
    ext = extract_plan_slots(frames)
    det = {
        "metric_slot": ext.metric_slot,
        "window.start": ext.window_start,
        "window.end": ext.window_end,
        "ranking": ext.ranking,
        "direction": ext.direction,
        "limit": ext.limit_effective,
    }
    exp = {
        "metric_slot": str(intent["metric_slot"]),
        "window.start": exp_win[0] if exp_win else None,
        "window.end": exp_win[1] if exp_win else None,
        "ranking": bool(intent["ranking"]),
        "direction": str(intent["direction"]),
        "limit": exp_limit_eff,
    }

    def field_judge(name: str) -> None:
        """一致/分歧态下单字段判定（LLM 值＝确定性值的字段才可判）。"""
        if state == STATE_DIVERGE:
            raw_div = str(shadow_row.get("divergent") or "")
            divergent = {f.strip() for f in raw_div.split(",") if f.strip()}
            cmp_name = "limit" if name == "limit" else name
            if name in divergent or cmp_name in divergent:
                score.fields[name] = V_OPAQUE
                score.details.append(f"{name}：分歧行内——LLM 真值不落日志")
                return
        if name == "limit":
            exp_v, det_v = exp["limit"], det["limit"]
        else:
            exp_v, det_v = exp[name], det[name]
        if det_v is None:
            score.fields[name] = V_OPAQUE
            score.details.append(f"{name}：确定性侧缺件（帧未提取）——LLM 值无从证实")
            return
        score.fields[name] = V_HIT if det_v == exp_v else V_MISS
        if det_v != exp_v:
            score.details.append(f"{name}：标签 {exp_v!r} ≠ 确定性解析 {det_v!r}")

    if state in (STATE_MATCH, STATE_DIVERGE):
        for name in INTENT_FIELDS:
            field_judge(name)
        if vague:
            score.details.append("模糊窗题却出一致/分歧态——窗判分照常（标签端点已实算）")
        return f"触发比对（{state}）", score

    # —— 不可比 ——
    if "确定性解析侧" in note:
        # LLM 草案产出且过 validator（在册指标）但字段值不落日志。
        for name in INTENT_FIELDS:
            score.fields[name] = V_OPAQUE
        score.details.append("LLM 草案过 validator（metric 在册）——具体值不落日志不可判")
        if vague:
            score.fields["window.start"] = V_MADEUP
            score.fields["window.end"] = V_MADEUP
            score.details.append(
                "模糊窗题：LLM 补窗与否不可逐值证实（过 validator 仅证在册）——记补窗形态档"
            )
        return "不可比（确定性侧缺解析——LLM 草案在册但值不可观测）", score
    if "；validator 拒：" in note or note.startswith("validator 拒："):
        m = _REJECT_METRIC_RE.search(note)
        if m is not None:
            given = m.group(1)
            score.fields["metric_slot"] = V_HIT if given == exp["metric_slot"] else V_MISS
            score.details.append(f"validator 拒因携 LLM metric_slot={given!r}——可判")
        else:
            score.fields["metric_slot"] = V_ABSENT
        for name in INTENT_FIELDS:
            if name != "metric_slot":
                score.fields[name] = V_OPAQUE
        score.details.append(f"validator 拒：{note[:60]}")
        return "不可比（validator 拒——拒因在案）", score
    if "drafter 异常" in note:
        for name in INTENT_FIELDS:
            score.fields[name] = V_OPAQUE
        score.details.append(f"drafter 异常：{note[:60]}")
        return "不可比（drafter 异常）", score
    for name in INTENT_FIELDS:
        score.fields[name] = V_ABSENT
    score.details.append("LLM 无有效草案（拒产或坏 JSON）——全字段未产出")
    return "不可比（draft 侧缺解析）", score


# ---------- 报告渲染 ----------


def _esc(text: Any) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def _short(text: Any, width: int = 36) -> str:
    s = _esc(text)
    return s if len(s) <= width else s[: width - 1] + "…"


def render_report(
    judged: list[dict[str, Any]],
    *,
    tag: str,
    cur_stats: Any,
    merged_stats: Any,
    asked_total: int,
    log_sha: str,
    prior_sha: str,
    today: date,
    rerun_cmd: str,
) -> str:
    lines: list[str] = []
    ap = lines.append
    ap(f"# L-03b 影子定向补测报告（{tag}）——意图命中率口径（L-03 首轮 addendum）")
    ap("")
    ap(f"- 报告生成时刻：{datetime_now()}")
    ap(f"- 执行日（窗口实算基准）：{today.isoformat()}")
    ap(
        "- 流量口径：**定向补测流量**（首轮收尾疑点 1 样本缺口的补量轮）——在册指标＋刁钻问法"
        " 18 问，每问带出题人意图标签；**非 golden、不进题册**，影子期质量代理指标。"
    )
    ap(f"- 本轮影子日志 SHA256 `{log_sha[:16]}…`；首轮样本（合并视图用）SHA256 `{prior_sha[:16]}…`")
    ap("")
    ap("## 一、本轮流量形态总览（18 问）")
    ap("")
    form_counts: dict[str, int] = {}
    for row in judged:
        form_counts[row["form"]] = form_counts.get(row["form"], 0) + 1
    ap("| 形态 | 问数 |")
    ap("|---|---|")
    for form, n in sorted(form_counts.items(), key=lambda kv: -kv[1]):
        ap(f"| {_esc(form)} | {n} |")
    ap("")
    trig = [r for r in judged if r["form"].startswith("触发比对")]
    overwide = sum(1 for r in judged if r["shadow_bucket"] == BUCKET_OVERWIDE)
    overnarrow = sum(1 for r in judged if r["shadow_bucket"] == BUCKET_OVERNARROW)
    ap(
        f"触发行（trigger 非空）{cur_stats.triggered_rows}，其中比对出一致/分歧 {len(trig)}；"
        f"过宽桶 {overwide}／过窄桶 {overnarrow}（bucket 字段直聚）；"
        f"对照组未触发 {form_counts.get('未触发（预期内——对照组）', 0)}；"
        f"未入链 {form_counts.get('未入链（verdict 裁决 检索问答链——LLM#plan 未被调）', 0)}"
    )
    ap("")

    # —— 第二节：意图命中率（核心新口径）——
    ap("## 二、意图命中率（LLM 草案 × 出题人标签——观测能力约束口径）")
    ap("")
    scored = [r for r in judged if r["score"] is not None]
    metric_judgeable = [r for r in scored if r["score"].fields["metric_slot"] in (V_HIT, V_MISS)]
    metric_hits = [r for r in metric_judgeable if r["score"].fields["metric_slot"] == V_HIT]
    ap(f"**metric_slot 命中率：{len(metric_hits)}/{len(metric_judgeable)} 可判行**")
    ap("")
    all_verdicts = (V_HIT, V_MISS, V_OPAQUE, V_ABSENT, V_UNCALLED, V_MADEUP)
    op_counts: dict[str, int] = {v: 0 for v in all_verdicts}
    for r in scored:
        cur = r["score"].fields["metric_slot"]
        op_counts[cur] = op_counts.get(cur, 0) + 1
    ap("| metric_slot 判定 | 题数 | 说明 |")
    ap("|---|---|---|")
    desc = {
        V_HIT: "有 LLM 值证据且与标签一致",
        V_MISS: "有 LLM 值证据但与标签不一致",
        V_OPAQUE: "LLM 真值不落日志（分歧行内字段／validator 过但在册值未知）",
        V_ABSENT: "LLM 无有效草案（拒产/坏 JSON）",
        V_UNCALLED: "LLM#plan 未被调（未入链/过窄/对照组）",
        V_MADEUP: "模糊窗题补窗形态档（缺用户事实不判对错）",
    }
    for v in (V_HIT, V_MISS, V_OPAQUE, V_ABSENT, V_UNCALLED, V_MADEUP):
        if op_counts[v]:
            ap(f"| {v} | {op_counts[v]} | {desc[v]} |")
    ap("")
    ap("逐字段判定（window.start/window.end/ranking/direction/limit——可判行内对错）：")
    ap("")
    ap("| 字段 | 对 | 错 | 不可观测 | 未产出 | 未调 | 补窗形态 |")
    ap("|---|---|---|---|---|---|---|")
    for fname in INTENT_FIELDS:
        row = {v: 0 for v in (V_HIT, V_MISS, V_OPAQUE, V_ABSENT, V_UNCALLED, V_MADEUP)}
        for r in scored:
            row[r["score"].fields[fname]] += 1
        ap(
            f"| {fname} | {row[V_HIT]} | {row[V_MISS]} | {row[V_OPAQUE]} | "
            f"{row[V_ABSENT]} | {row[V_UNCALLED]} | {row[V_MADEUP]} |"
        )
    ap("")
    ap(
        "> 口径注：可判＝LLM 值有日志证据（一致态全字段；分歧态非 divergent 字段；"
        "validator 拒因携值仅 metric）。不可观测/未产出/未调均不进命中率分母——"
        "影子观测件不落草案字段值（L-02 设计），此命中率是**下界**口径。"
    )
    ap("")

    # —— 第三节：四项数字（本轮＋合并）——
    ap("## 三、四项数字（本轮行；括号内＝首轮样本＋本轮合并视图）")
    ap("")
    ap("| 项 | 本轮 | 合并（首轮 13 行＋本轮） |")
    ap("|---|---|---|")
    cur_m = cur_stats.state_counts[STATE_MATCH] + cur_stats.state_counts[STATE_DIVERGE]
    mer_m = merged_stats.state_counts[STATE_MATCH] + merged_stats.state_counts[STATE_DIVERGE]
    cur_tri = cur_stats.state_counts
    mer_tri = merged_stats.state_counts
    ap(
        f"| 一致率三分桶 | 一致 {cur_tri[STATE_MATCH]}／分歧 {cur_tri[STATE_DIVERGE]}／"
        f"不可比 {cur_tri[STATE_INCOMPARABLE]}"
        f"（一致率 {pct(cur_tri[STATE_MATCH], cur_m)}） | "
        f"一致 {mer_tri[STATE_MATCH]}／分歧 {mer_tri[STATE_DIVERGE]}／"
        f"不可比 {mer_tri[STATE_INCOMPARABLE]}"
        f"（一致率 {pct(mer_tri[STATE_MATCH], mer_m)}） |"
    )
    ap(
        f"| 触发双分桶 | 触发 {cur_stats.triggered_rows}（过宽 {cur_stats.bucket_overwide}／"
        f"过窄 {cur_stats.bucket_overnarrow}）；"
        f"占总问句比 {pct(cur_stats.triggered_rows, asked_total)} | "
        f"触发 {merged_stats.triggered_rows}（过宽 {merged_stats.bucket_overwide}／"
        f"过窄 {merged_stats.bucket_overnarrow}） |"
    )
    cur_lat, mer_lat = cur_stats.latency_values, merged_stats.latency_values

    def _lat_line(vals: list[int]) -> str:
        if not vals:
            return "样本不足"
        p50, p95 = percentile(vals, 50), percentile(vals, 95)
        return f"p50 {p50}／p95 {p95}／max {max(vals)} ms"

    lat_s, mer_s = _lat_line(cur_lat), _lat_line(mer_lat)
    ap(
        f"| 延迟（latency_ms） | {lat_s}（非空 {len(cur_lat)} 行） | "
        f"{mer_s}（非空 {len(mer_lat)} 行） |"
    )
    cur_tok = cur_stats.prompt_total + cur_stats.completion_total
    mer_tok = merged_stats.prompt_total + merged_stats.completion_total
    cur_per = cur_tok / cur_stats.token_rows if cur_stats.token_rows else 0
    mer_per = mer_tok / merged_stats.token_rows if merged_stats.token_rows else 0
    ap(
        f"| token | 合计 {cur_tok}（均值 {cur_per:.1f}／非空 {cur_stats.token_rows} 行） | "
        f"合计 {mer_tok}（均值 {mer_per:.1f}／非空 {merged_stats.token_rows} 行） |"
    )
    ap("")
    reasons = "、".join(
        f"{_esc(k)}×{v}" for k, v in cur_stats.trigger_reason_counts.items()
    ) or "（无触发行）"
    ap(f"触发原因分布（本轮）：{reasons}")
    ap("")

    # —— 第四节：逐题表 ——
    ap("## 四、逐题表（18 问全量——形态＋意图判定）")
    ap("")
    ap("| qid | 问句 | 预期 | 形态 | metric | win.start | win.end | rank | dir "
       "| limit | 判定依据 |")
    ap("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in judged:
        sc = r["score"]
        cells = [sc.fields[f] for f in INTENT_FIELDS] if sc else ["—"] * 6
        detail = "；".join(sc.details) if sc and sc.details else "—"
        exp = "触发" if r["expected_trigger"] else "不触发"
        ap(
            f"| {r['qid']} | {_short(r['question'], 22)} | {exp} | "
            f"{_short(r['form'], 26)} | {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} | "
            f"{cells[4]} | {cells[5]} | {_short(detail, 40)} |"
        )
    ap("")

    # —— 第五节：形态判例 ——
    ap("## 五、形态判例逐条（模糊窗／对照组／意外形态）")
    ap("")
    for r in judged:
        interesting = (
            r["form"].startswith("不可比")
            or "模糊" in str(r["author_intent"].get("window_rule", ""))
            or not r["expected_trigger"]
            or "意外" in r["form"]
        )
        if not interesting:
            continue
        exp = "触发" if r["expected_trigger"] else "不触发"
        sc = r["score"]
        det = "；".join(sc.details) if sc and sc.details else "（无可判字段）"
        ap(f"- **{r['qid']}「{r['question']}」**（预期{exp}）——{r['form']}。{det}")
    ap("")

    ap("## 六、重跑")
    ap("")
    ap("```bash")
    ap(rerun_cmd)
    ap("```")
    ap("")
    return "\n".join(lines)


def percentile(values: list[int], p: float) -> Any:
    if not values:
        return "—"
    import math

    ordered = sorted(values)
    idx = max(0, math.ceil(len(ordered) * p / 100) - 1)
    return ordered[min(idx, len(ordered) - 1)]


def datetime_now() -> str:
    from datetime import datetime

    return datetime.now().isoformat(timespec="seconds")


# ---------- 干跑自检 ----------

def _sample_traffic() -> list[dict[str, Any]]:
    return [
        {"qid": "T-01", "family": "判例", "question": "Q一致态",
         "expected_trigger": True,
         "author_intent": {"metric_slot": "日产油量", "window_rule": "默认窗",
                            "ranking": True, "direction": "desc", "limit_requested": None},
         "design_note": "判例"},
        {"qid": "T-02", "family": "判例", "question": "Q分歧行",
         "expected_trigger": True,
         "author_intent": {"metric_slot": "日产液量", "window_rule": "上月",
                            "ranking": True, "direction": "desc", "limit_requested": 3},
         "design_note": "判例"},
        {"qid": "T-03", "family": "判例", "question": "Q模糊窗",
         "expected_trigger": True,
         "author_intent": {"metric_slot": "日产液量", "window_rule": "模糊最近",
                            "ranking": True, "direction": "desc", "limit_requested": None},
         "design_note": "判例"},
    ]


def _sample_frames(chain: str, *, sql: bool) -> list[dict[str, Any]]:
    frames: list[dict[str, Any]] = [
        {"event": "verdict", "data": {"chain": chain, "slots": "指标＝日产油量 · 报告＝《R》"}},
        {"event": "node", "data": {"key": "N7.1", "state": "finish",
                                    "note": "三要素齐：指标＝日产油量（台账「日产油量（吨）」）· "
                                             "时间＝最近 30 天（默认）· 条数＝50——确定性校验通过"}},
    ]
    if sql:
        frames.append({"event": "node_line", "data": {"key": "N7.3", "text": (
            "模板装配 SQL：\nSELECT w.well_id AS 井号, SUM(m.oil_output) AS t\n"
            "FROM agg.fct_daily_metering m JOIN agg.dim_well w ON w.well_id = m.well_id\n"
            "WHERE m.prod_date >= '2026-09-08' AND m.prod_date < '2026-10-08'\n"
            "GROUP BY w.well_id\nORDER BY SUM(m.oil_output) DESC\nLIMIT 50")}})
    return frames


def dry_run() -> int:
    today = date(2026, 10, 8)
    qs = _sample_traffic()
    # 判例 1：一致态＋确定性全槽位——逐字段对默认窗标签（today-30=2026-09-08）。
    frames1 = _sample_frames(_CHAIN_FAST, sql=True)
    row1 = {"trigger": "词面不齐", "draft_state": STATE_MATCH, "divergent": None,
            "note": None, "bucket": BUCKET_OVERWIDE, "question": "Q一致态"}
    form1, s1 = judge_intent(qs[0], shadow_row=row1, frames=frames1, today=today)
    # 判例 2：分歧行 divergent=window.start——window.start 不可观测，metric/ranking 可判。
    frames2 = _sample_frames(_CHAIN_FAST, sql=False)  # 无 SQL——确定性窗缺件
    row2 = {"trigger": "解析缺件", "draft_state": STATE_DIVERGE, "divergent": "window.start",
            "note": None, "bucket": None, "question": "Q分歧行"}
    _form2, s2 = judge_intent(qs[1], shadow_row=row2, frames=frames2, today=today)
    # 判例 3：模糊窗＋不可比（确定性侧缺）——补窗形态档。
    row3 = {"trigger": "解析缺件", "draft_state": STATE_INCOMPARABLE, "divergent": None,
            "note": "确定性解析侧（快路缺件未产出计划）缺解析——不可比",
            "bucket": None, "question": "Q模糊窗"}
    frames3 = _sample_frames(_CHAIN_FAST, sql=False)
    form3, s3 = judge_intent(qs[2], shadow_row=row3, frames=frames3, today=today)
    # 判例 4：未入链（检索链无影子行）——对照组与触发预期两态。
    form4, s4 = judge_intent(
        {**qs[0], "question": "Q未入链", "expected_trigger": True},
        shadow_row=None, frames=_sample_frames(_CHAIN_RETRIEVAL, sql=False), today=today,
    )
    form5, s5 = judge_intent(
        {**qs[0], "question": "Q对照", "expected_trigger": False},
        shadow_row=None, frames=_sample_frames(_CHAIN_RETRIEVAL, sql=False), today=today,
    )
    # 判例 6：入链但谓词未触发（快路可解——预期不触发的正确形态）。
    form6, s6 = judge_intent(
        {**qs[0], "question": "Q快路", "expected_trigger": False},
        shadow_row=None, frames=_sample_frames(_CHAIN_FAST, sql=True), today=today,
    )
    exp_win1 = expected_window("默认窗", today=today)
    madeup_ok = s3.fields["window.start"] == V_MADEUP and s3.fields["metric_slot"] == V_OPAQUE
    checks: list[tuple[str, bool, str]] = [
        ("判例1-一致态形态", form1 == "触发比对（一致）", form1),
        ("判例1-metric对", s1.fields["metric_slot"] == V_HIT, str(s1.fields)),
        ("判例1-默认窗端点对",
         s1.fields["window.start"] == V_HIT and s1.fields["window.end"] == V_HIT,
         f"{s1.fields['window.start']}/{s1.fields['window.end']}（期望 {exp_win1}）"),
        ("判例1-默认limit50对", s1.fields["limit"] == V_HIT, str(s1.fields)),
        ("判例1-过宽桶", row1["bucket"] == BUCKET_OVERWIDE, ""),
        ("判例2-分歧内字段不可观测", s2.fields["window.start"] == V_OPAQUE, str(s2.fields)),
        ("判例2-metric可判（帧提取 vs 标签异指标→错）",
         s2.fields["metric_slot"] == V_MISS, str(s2.fields)),
        ("判例3-模糊窗补窗形态档", madeup_ok, str(s3.fields)),
        ("判例3-形态", "确定性侧缺解析" in form3, form3),
        ("判例4-未入链未调",
         s4.fields["metric_slot"] == V_UNCALLED and "未入链" in form4,
         f"{form4}/{s4.fields}"),
        ("判例5-对照组未触发",
         s5.fields["metric_slot"] == V_UNCALLED and "未触发" in form5, form5),
        ("判例6-快路可解预期内",
         s6.fields["metric_slot"] == V_UNCALLED and "快路可解" in form6, form6),
    ]
    failures = [c for c in checks if not c[1]]
    for name, ok, note in checks:
        print(f"  {'✓' if ok else '✗'} {name}" + (f"（{note}）" if note and not ok else ""))
    if failures:
        print(f"干跑自检失败 {len(failures)} 项")
        return 1
    print("干跑自检全过（一致/分歧/模糊窗/未入链/对照/快路可解 六判例 12 断言）")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="L-03b 影子定向补测报告（意图命中率——离线聚合三源：题集×影子日志×SSE 帧）",
    )
    ap.add_argument("--traffic", default=str(TRAFFIC))
    ap.add_argument("--tag", default="L03B")
    ap.add_argument("--log", default="logs/shadow-plan.jsonl", help="本轮影子 JSONL")
    ap.add_argument("--prior-log",
                    default=str(FRAMES_DIR / "L03S-shadow-log-sample.jsonl"),
                    help="首轮影子样本（合并视图——committed 13 行）")
    ap.add_argument("--frames-dir", default=str(FRAMES_DIR))
    ap.add_argument("--out", default=None, help="输出 markdown（缺省 shadow-report-<tag>.md）")
    ap.add_argument("--asked-total", type=int, default=18,
                    help="占总问句比分母（缺省 18＝本题集全量）")
    ap.add_argument("--dry-run", action="store_true", help="离线自检：内置判例手算对账")
    args = ap.parse_args()
    if args.dry_run:
        return dry_run()

    from datetime import datetime as _dt

    today = _dt.now().date()
    traffic = json.loads(Path(args.traffic).read_text(encoding="utf-8"))
    questions = traffic["questions"]
    q_by_question = {q["question"]: q for q in questions}
    qset = set(q_by_question)

    cur_rows = [r for r in load_rows(args.log) if str(r.get("question") or "") in qset]
    if not cur_rows:
        print(f"本轮影子行为 0：{args.log}（question 匹配题集 {len(qset)} 问）", file=sys.stderr)
        return 1
    prior_rows = load_rows(args.prior_log) if Path(args.prior_log).is_file() else []

    frames_dir = Path(args.frames_dir)
    judged: list[dict[str, Any]] = []
    for q in questions:
        qid = str(q["qid"])
        frame_path = frames_dir / f"{args.tag}-{qid}.txt"
        if not frame_path.is_file():
            frame_path = frames_dir / f"L03BSMOKE-{qid}.txt"  # 冒烟帧原样存档名
        frames = parse_frames_file(frame_path) if frame_path.is_file() else []
        rows = [r for r in cur_rows if str(r.get("question") or "") == q["question"]]
        row = rows[-1] if rows else None
        form, score = judge_intent(q, shadow_row=row, frames=frames, today=today)
        judged.append({
            "qid": qid, "question": q["question"], "family": q["family"],
            "expected_trigger": bool(q["expected_trigger"]), "author_intent": q["author_intent"],
            "design_note": q["design_note"], "form": form, "score": score,
            "shadow_row": row, "chain": frame_chain(frames),
            "shadow_bucket": (row or {}).get("bucket"),
        })

    cur_stats = aggregate(cur_rows)
    merged_stats = aggregate(prior_rows + cur_rows)
    out = Path(args.out) if args.out else Path("eval/results") / f"shadow-report-{args.tag}.md"

    def _rel(p: str) -> str:
        try:
            return str(Path(p).relative_to(Path.cwd()))
        except ValueError:
            return p

    rerun_parts = [
        "uv run python eval/results/tools/shadow_report_addendum.py",
        f"--tag {args.tag}", f"--log {_rel(args.log)}",
        f"--prior-log {_rel(args.prior_log)}",
        f"--asked-total {args.asked_total}",
    ]
    report = render_report(
        judged, tag=args.tag, cur_stats=cur_stats, merged_stats=merged_stats,
        asked_total=args.asked_total, log_sha=file_sha256(args.log),
        prior_sha=file_sha256(args.prior_log) if prior_rows else "（无）",
        today=today, rerun_cmd=" ".join(rerun_parts),
    )
    out.write_text(report, encoding="utf-8")
    metric_j = [
        r for r in judged
        if r["score"] and r["score"].fields["metric_slot"] in (V_HIT, V_MISS)
    ]
    metric_h = [r for r in metric_j if r["score"].fields["metric_slot"] == V_HIT]
    print(f"报告已产出：{out}")
    print(f"本轮行 {cur_stats.total_rows}（触发 {cur_stats.triggered_rows}）；"
          f"metric_slot 命中 {len(metric_h)}/{len(metric_j)} 可判")
    return 0


if __name__ == "__main__":
    sys.exit(main())
