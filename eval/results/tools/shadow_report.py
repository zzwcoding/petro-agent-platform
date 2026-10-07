#!/usr/bin/env python3
"""L-03 影子报告生成脚本（闸 A 拍板唯一数字依据——票面交付物①）。

用法：
    # 实跑报告（读 L-02 影子 JSONL，产出 markdown 报告）：
    uv run python eval/results/tools/shadow_report.py \
        --tag L03 --log logs/shadow-plan.jsonl \
        --judge eval/results/L03S-plan判定.jsonl --asked 36
    # 离线干跑自检（零文件零网络——内置样例 JSONL 手算对账）：
    uv run python eval/results/tools/shadow_report.py --dry-run

纪律（票面定案）：离线聚合——只读 L-02 影子 JSONL，零网络、零模型调用、零仓内依赖
改动（标准库 json/argparse/hashlib）；聚合逻辑＝脚本内纯函数；报告每一个数都来自
日志实读，不预设不推算；样本不足处如实标注「样本不足」。eval 侧脚本照 rerun.py
惯例不进 tests/，过 ruff（机器闸扫 tools/）。

四节实测数字（与 L-02 影子行字段一一对应——app/domains/chat/domain.py shadow_plan_json）：
  1. 一致率三分桶：一致/分歧/不可比 计数与占比；一致率＝一致/(一致＋分歧)——
     口径：分母只取触发比对行（trigger 非空），不可比单列不进分母，过窄观测行
     （trigger 为空）不是比对结果、不计入；
  2. 触发双分桶（方案 §2.2 路径 3）：过宽＝触发且比对一致（bucket 字段）、
     过窄＝谓词未触发且落降级/缺参澄清（bucket 字段）原始计数＋触发原因分布；
  3. 成本曲线（延迟）：latency_ms p50/p95/max（最近秩法）＋分布直方（脚本内定档）；
  4. 成本曲线（token）：prompt/completion 合计、单问均值、null 占比（usage 缺失如实列）。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

# 与 app/domains/chat/domain.py 常量同字面（报告脚本零仓内依赖——字面快照，
# 值演进时本表随 L-02 字段合同同步）。
STATE_MATCH = "一致"
STATE_DIVERGE = "分歧"
STATE_INCOMPARABLE = "不可比"
TRI_STATES = (STATE_MATCH, STATE_DIVERGE, STATE_INCOMPARABLE)
BUCKET_OVERWIDE = "过宽：触发但快路可解"
BUCKET_OVERNARROW = "过窄：该触发未触发"
COMPARE_FIELDS = (
    "metric_slot", "window.start", "window.end", "limit_effective", "ranking", "direction",
)

# 延迟直方分档（毫秒，脚本内定案——单次 LLM 调用 8s 超时兜底为上界参照）。
LATENCY_BINS: tuple[tuple[int, int | None], ...] = (
    (0, 500), (500, 1000), (1000, 2000), (2000, 4000), (4000, 8000), (8000, None),
)

SAMPLE_ROWS: tuple[dict[str, Any], ...] = (
    # 内置干跑样例（票面验收：三态齐全＋双分桶判例＋token null 行——数字经手算对账）。
    {"ts": "2026-10-08T10:00:01.000", "run_id": "run-s00001", "question": "各井日产油量是多少？",
     "trigger": "词面不齐", "draft_state": STATE_MATCH, "elapsed_ms": 620, "divergent": None,
     "note": None, "latency_ms": 500, "prompt_tokens": 100, "completion_tokens": 20,
     "bucket": BUCKET_OVERWIDE, "breaker": None},
    {"ts": "2026-10-08T10:00:05.000", "run_id": "run-s00002", "question": "上月产量完成率排名前三",
     "trigger": "词面不齐", "draft_state": STATE_MATCH, "elapsed_ms": 1610, "divergent": None,
     "note": None, "latency_ms": 1500, "prompt_tokens": 200, "completion_tokens": 30,
     "bucket": BUCKET_OVERWIDE, "breaker": None},
    {"ts": "2026-10-08T10:00:09.000", "run_id": "run-s00003", "question": "上个月哪口井产得最多？",
     "trigger": "词面不齐", "draft_state": STATE_DIVERGE, "elapsed_ms": 2600,
     "divergent": "window.start,window.end", "note": None, "latency_ms": 2500,
     "prompt_tokens": 300, "completion_tokens": 40, "bucket": None, "breaker": None},
    {"ts": "2026-10-08T10:00:13.000", "run_id": "run-s00004", "question": "去年各井含水率是多少？",
     "trigger": "解析缺件", "draft_state": STATE_INCOMPARABLE, "elapsed_ms": 3520,
     "divergent": None, "note": "draft 侧（未产出或被 validator 拒）缺解析——不可比",
     "latency_ms": 3500, "prompt_tokens": 400, "completion_tokens": 50,
     "bucket": None, "breaker": None},
    {"ts": "2026-10-08T10:00:17.000", "run_id": "run-s00005", "question": "三季度累积亏空是多少？",
     "trigger": "解析缺件", "draft_state": STATE_INCOMPARABLE, "elapsed_ms": 0,
     "divergent": None, "note": "drafter 异常 TimeoutError: llm", "latency_ms": None,
     "prompt_tokens": None, "completion_tokens": None, "bucket": None, "breaker": None},
    {"ts": "2026-10-08T10:00:21.000", "run_id": "run-s00006",
     "question": "最近各井日产油量怎么样？",
     "trigger": None, "draft_state": STATE_INCOMPARABLE, "elapsed_ms": 0, "divergent": None,
     "note": "过窄桶：快路信号判齐但快路未出数——落缺参澄清（模糊时间窗不代猜）",
     "latency_ms": None, "prompt_tokens": None, "completion_tokens": None,
     "bucket": BUCKET_OVERNARROW, "breaker": None},
    {"ts": "2026-10-08T10:00:25.000", "run_id": "run-s00007", "question": "去年各井配产量是多少？",
     "trigger": "解析缺件", "draft_state": STATE_INCOMPARABLE, "elapsed_ms": 0,
     "divergent": None, "note": "熔断短路", "latency_ms": None, "prompt_tokens": None,
     "completion_tokens": None, "bucket": None, "breaker": "tripped"},
)


# ---------- 纯函数：载入与聚合（票面定案——聚合逻辑留脚本内） ----------


def load_rows(path: str | Path) -> list[dict[str, Any]]:
    """影子 JSONL → 记录列表（跳过空行；缺键按 null 兜底——L-01 旧行向后兼容）。"""
    rows: list[dict[str, Any]] = []
    with Path(path).open(encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            stripped = line.strip()
            if not stripped:
                continue
            row = json.loads(stripped)
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{lineno} 非对象行")
            for key in ("run_id", "draft_state", "question"):
                if key not in row:
                    raise ValueError(f"{path}:{lineno} 缺必填键 {key}（非 L-02 影子行？）")
            rows.append(row)
    return rows


def file_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def triggered(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """触发比对行（trigger 非空）——一致率与成本曲线的口径分母。"""
    return [r for r in rows if r.get("trigger")]


def pct(part: int, whole: int) -> str:
    return f"{part / whole * 100:.1f}%" if whole else "样本不足"


def percentile(values: list[int], p: float) -> int | None:
    """最近秩法（sorted 就绪后取 ceil(n*p)-1 位——确定性，不引依赖）。"""
    if not values:
        return None
    ordered = sorted(values)
    import math

    idx = max(0, math.ceil(len(ordered) * p / 100) - 1)
    return ordered[min(idx, len(ordered) - 1)]


@dataclass(frozen=True, slots=True)
class ShadowStats:
    """影子日志四节聚合结果（全数字来自实读——零预设零推算）。"""

    total_rows: int
    unique_questions: int
    triggered_rows: int
    breaker_rows: int
    state_counts: dict[str, int]
    divergent_rows: int
    divergent_field_counts: dict[str, int]
    divergent_shape_counts: dict[str, int]
    bucket_overwide: int
    bucket_overnarrow: int
    trigger_reason_counts: dict[str, int]
    latency_values: list[int]
    latency_null_rows: int
    token_rows: int  # usage 非空行数
    prompt_total: int
    completion_total: int
    token_null_rows: int
    ts_min: str
    ts_max: str


def aggregate(rows: list[dict[str, Any]]) -> ShadowStats:
    """记录列表 → 四节聚合（纯函数——干跑自检与实跑共用同一路径）。"""
    tri = triggered(rows)
    state_counts = {s: sum(1 for r in tri if r.get("draft_state") == s) for s in TRI_STATES}
    diverge_rows = [r for r in tri if r.get("draft_state") == STATE_DIVERGE]
    field_counts: dict[str, int] = {}
    shape_counts: dict[str, int] = {}
    for r in diverge_rows:
        fields = tuple(f for f in COMPARE_FIELDS if f in str(r.get("divergent") or "").split(","))
        for f in fields:
            field_counts[f] = field_counts.get(f, 0) + 1
        if fields:
            shape = ",".join(fields)
            shape_counts[shape] = shape_counts.get(shape, 0) + 1
    reason_counts: dict[str, int] = {}
    for r in tri:
        reason = str(r.get("trigger") or "")
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
    latencies = [int(r["latency_ms"]) for r in tri if r.get("latency_ms") is not None]
    tok_rows = [
        r for r in tri
        if r.get("prompt_tokens") is not None or r.get("completion_tokens") is not None
    ]
    ts_list = sorted(str(r.get("ts") or "") for r in rows)
    return ShadowStats(
        total_rows=len(rows),
        unique_questions=len({str(r.get("question") or "") for r in rows}),
        triggered_rows=len(tri),
        breaker_rows=sum(1 for r in rows if r.get("breaker") == "tripped"),
        state_counts=state_counts,
        divergent_rows=len(diverge_rows),
        divergent_field_counts=dict(sorted(field_counts.items(), key=lambda kv: -kv[1])),
        divergent_shape_counts=dict(sorted(shape_counts.items(), key=lambda kv: -kv[1])),
        bucket_overwide=sum(1 for r in rows if r.get("bucket") == BUCKET_OVERWIDE),
        bucket_overnarrow=sum(1 for r in rows if r.get("bucket") == BUCKET_OVERNARROW),
        trigger_reason_counts=dict(sorted(reason_counts.items(), key=lambda kv: -kv[1])),
        latency_values=latencies,
        latency_null_rows=len(tri) - len(latencies),
        token_rows=len(tok_rows),
        prompt_total=sum(int(r.get("prompt_tokens") or 0) for r in tok_rows),
        completion_total=sum(int(r.get("completion_tokens") or 0) for r in tok_rows),
        token_null_rows=sum(
            1 for r in tri if r.get("prompt_tokens") is None and r.get("completion_tokens") is None
        ),
        ts_min=ts_list[0] if ts_list else "",
        ts_max=ts_list[-1] if ts_list else "",
    )


def load_judge_index(path: str | Path | None) -> dict[str, dict[str, Any]]:
    """plan_rerun 判定表 → 问句→（qid/family/expected_path）索引（可选——逐题表题源列）。"""
    if path is None:
        return {}
    index: dict[str, dict[str, Any]] = {}
    with Path(path).open(encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if not stripped:
                continue
            row = json.loads(stripped)
            q = str(row.get("question") or "")
            if q:
                index[q] = row
    return index


# ---------- 报告渲染 ----------


def _esc(text: Any) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def _short(text: Any, width: int = 42) -> str:
    s = _esc(text)
    return s if len(s) <= width else s[: width - 1] + "…"


def render_report(
    stats: ShadowStats,
    rows: list[dict[str, Any]],
    *,
    tag: str,
    log_path: str,
    log_sha: str,
    judge: dict[str, dict[str, Any]],
    asked: int | None,
    env_note: str,
    traffic_note: str,
    rerun_cmd: str,
) -> str:
    """聚合结果 → markdown 报告（四节实测数字＋逐题表＋双分桶样本＋重跑命令）。"""
    now = datetime.now().isoformat(timespec="seconds")
    match_n = stats.state_counts[STATE_MATCH]
    diverge_n = stats.state_counts[STATE_DIVERGE]
    incomparable_n = stats.state_counts[STATE_INCOMPARABLE]
    consist = pct(match_n, match_n + diverge_n)
    lines: list[str] = []
    ap = lines.append
    ap(f"# L-03 影子报告（{tag}）——闸 A 拍板数字依据")
    ap("")
    ap(f"- 报告生成时刻：{now}")
    ap(f"- 环境：{_esc(env_note)}")
    ap(f"- 流量集口径：{_esc(traffic_note)}")
    asked_note = (
        f"（跑批总问句 {asked}——含未触发问句，由 --asked 提供）"
        if asked is not None
        else "（--asked 未提供——总问句数缺，占总问句比不呈现）"
    )
    ap(
        f"- 问句总数：{stats.total_rows} 行影子日志"
        + asked_note
        + f"；去重问句 {stats.unique_questions} 条"
    )
    ap(f"- 影子行时间范围：{stats.ts_min} ～ {stats.ts_max}")
    ap(f"- 数据文件：`{log_path}`（SHA256 `{log_sha[:16]}…`）")
    ap(
        "- 一致率口径：分母＝触发比对行（trigger 非空，即真调过 LLM#plan 并完成双路比对的行）；"
        "不可比单列不进分母；过窄观测行（trigger 为空——谓词漏触发观测）不是比对结果，不计入。"
        "每一个数都来自影子 JSONL 实读（票面纪律：零预设零推算填充）。"
    )
    ap("")

    # —— 第一节：一致率三分桶 ——
    ap("## 一、一致率三分桶（L-01 比对算子三态）")
    ap("")
    tri_line = (
        f"触发比对行 {stats.triggered_rows} 行"
        f"（熔断短路 {stats.breaker_rows} 行——见逐题表 breaker 列）"
    )
    ap(tri_line)
    ap("")
    ap("| 三态 | 行数 | 占触发比对行比 |")
    ap("|---|---|---|")
    for state in TRI_STATES:
        note = "（单列不进一致率分母）" if state == STATE_INCOMPARABLE else ""
        share = pct(stats.state_counts[state], stats.triggered_rows)
        ap(f"| {state} | {stats.state_counts[state]} | {share}{note} |")
    ap("")
    consist_line = (
        f"**一致率＝一致/(一致＋分歧)＝{match_n}/({match_n}＋{diverge_n})＝{consist}**"
        f"（不可比 {incomparable_n} 行不进分母）"
    )
    ap(consist_line)
    ap("")
    diverge_head = f"分歧字段 TOP 形态（六字段——分歧行 {stats.divergent_rows} 行）："
    ap(diverge_head)
    ap("")
    if stats.divergent_rows:
        ap("| 分歧字段组合 | 行数 |")
        ap("|---|---|")
        for shape, n in stats.divergent_shape_counts.items():
            ap(f"| `{shape}` | {n} |")
        ap("")
        ap("单字段出现次数（一行情可含多字段）：")
        ap("")
        ap("、".join(f"`{f}`×{n}" for f, n in stats.divergent_field_counts.items()))
    else:
        ap("样本不足（分歧行 0 行——无分歧字段形态可列）")
    ap("")

    # —— 第二节：触发双分桶 ——
    ap("## 二、触发双分桶（方案 §2.2 路径 3）")
    ap("")
    ap("| 桶 | 原始计数 | 口径 |")
    ap("|---|---|---|")
    wide_line = f"| 过宽（触发但快路可解） | {stats.bucket_overwide} | 触发且一致（bucket 直聚） |"
    ap(wide_line)
    ap(
        f"| 过窄（该触发未触发） | {stats.bucket_overnarrow} | "
        "谓词 False 且落降级/缺参澄清（bucket 字段直聚） |"
    )
    share = (
        f"触发总次数 {stats.triggered_rows}／占总问句比 {pct(stats.triggered_rows, asked)}"
        if asked is not None
        else f"触发总次数 {stats.triggered_rows}（--asked 未提供——占总问句比缺）"
    )
    ap("")
    ap(f"**{share}**；触发原因分布：")
    ap("")
    ap("| 触发原因 | 次数 |")
    ap("|---|---|")
    for reason, n in stats.trigger_reason_counts.items():
        ap(f"| {_esc(reason) or '（空＝过窄观测行不计）'} | {n} |")
    ap("")

    # —— 第三节：成本曲线（延迟）——
    ap("## 三、成本曲线（延迟 latency_ms——LLM#plan 调用本身）")
    ap("")
    lat = stats.latency_values
    if lat:
        mean = sum(lat) / len(lat)
        p50, p95 = percentile(lat, 50), percentile(lat, 95)
        ap(f"非空样本 {len(lat)} 行（null {stats.latency_null_rows} 行——熔断短路/异常行如实列）；")
        p_line = f"**p50＝{p50} ms ／ p95＝{p95} ms ／ max＝{max(lat)} ms**"
        ap(p_line + f"（均值 {mean:.0f} ms；p50/p95 最近秩法）")
    else:
        ap("样本不足（latency 非空 0 行）")
    ap("")
    ap("分布直方（分档脚本内定：0–500／500–1000／1000–2000／2000–4000／4000–8000／≥8000 ms）：")
    ap("")
    ap("| 分档 (ms) | 行数 | 直方 |")
    ap("|---|---|---|")
    for lo, hi in LATENCY_BINS:
        label = f"{lo}–{hi - 1}" if hi is not None else f"≥{lo}"
        n = sum(1 for v in lat if v >= lo and (hi is None or v < hi))
        ap(f"| {label} | {n} | {'█' * min(n, 40)} |")
    ap("")

    # —— 第四节：成本曲线（token）——
    ap("## 四、成本曲线（token）")
    ap("")
    if stats.token_rows:
        combined = stats.prompt_total + stats.completion_total
        per = combined / stats.token_rows
        per_p = stats.prompt_total / stats.token_rows
        per_c = stats.completion_total / stats.token_rows
        ap(
            f"usage 非空 {stats.token_rows} 行：prompt 合计 {stats.prompt_total}＋completion 合计 "
            f"{stats.completion_total}＝**{combined}**；"
            f"单问均值（合计÷非空行）{per:.1f}"
            f"（prompt {per_p:.1f}／completion {per_c:.1f}）"
        )
    else:
        ap("样本不足（usage 非空 0 行——token 合计与均值不呈现）")
    ap("")
    token_null_line = (
        f"token 为 null 的触发比对行 {stats.token_null_rows}／{stats.triggered_rows}"
        f"＝{pct(stats.token_null_rows, stats.triggered_rows)}"
        "（usage 缺失如实列——异常/短路行无 usage）"
    )
    ap(token_null_line)
    ap("")

    # —— 逐题表 ——
    ap("## 五、逐题表（影子行全量，ts 升序）")
    ap("")
    ap("| # | 时刻 | run_id | 题源 | 问句 | 触发 | 三态 | 分歧 | 延迟ms | tokens | 桶 | 熔断 |")
    ap("|---|---|---|---|---|---|---|---|---|---|---|---|")
    ordered = sorted(rows, key=lambda r: str(r.get("ts") or ""))
    for i, r in enumerate(ordered, 1):
        q = str(r.get("question") or "")
        src_row = judge.get(q)
        src = (
            f"{src_row.get('qid')}·{src_row.get('family')}·{src_row.get('expected_path')}"
            if src_row
            else "题册补题"
        )
        tokens = (
            f"{r.get('prompt_tokens')}+{r.get('completion_tokens')}"
            if r.get("prompt_tokens") is not None or r.get("completion_tokens") is not None
            else "null"
        )
        latency_cell = r.get("latency_ms") if r.get("latency_ms") is not None else "null"
        ap(
            f"| {i} | {_short(r.get('ts'), 23)} | {_short(r.get('run_id'), 12)} | {src} | "
            f"{_short(q)} | {_esc(r.get('trigger') or '—')} | {_esc(r.get('draft_state'))} | "
            f"{_esc(r.get('divergent') or '—')} | {latency_cell} | "
            f"{tokens} | {_esc(r.get('bucket') or '—')} | {_esc(r.get('breaker') or '—')} |"
        )
    ap("")

    # —— 双分桶典型样本 ——
    ap("## 六、双分桶典型样本（原问句在案）")
    ap("")
    bucket_labels = (
        (BUCKET_OVERWIDE, "过宽（触发但快路可解）"),
        (BUCKET_OVERNARROW, "过窄（该触发未触发）"),
    )
    for bucket, label in bucket_labels:
        samples = [r for r in ordered if r.get("bucket") == bucket]
        ap(f"### {label}——原始计数 {len(samples)}")
        ap("")
        if len(samples) < 3:
            ap(
                f"> **样本不足**（实跑仅 {len(samples)} 例，票面验收要 ≥3——"
                "按纪律如实标注不推算填充，补量口径呈 Owner 定）"
            )
            ap("")
        if samples:
            ap("| 原问句 | 触发原因 | 三态 | 分歧字段 | 时刻 |")
            ap("|---|---|---|---|---|")
            for r in samples[:5]:
                ap(
                    f"| {_esc(r.get('question'))} | {_esc(r.get('trigger') or '—')} | "
                    f"{_esc(r.get('draft_state'))} | {_esc(r.get('divergent') or '—')} | "
                    f"{_short(r.get('ts'), 23)} |"
                )
        ap("")

    # —— 重跑 ——
    ap("## 七、重跑")
    ap("")
    ap("```bash")
    ap(rerun_cmd)
    ap("```")
    ap("")
    ap("> 重跑纪律（票面验收）：同命令执行产出同构报告（数字可因新流量不同——结构必须同构）。")
    ap("")
    return "\n".join(lines)


# ---------- 干跑自检（内置样例手算对账——票面验收①） ----------


def dry_run() -> int:
    """内置样例聚合 → 与手算数字逐项断言（三态齐全＋双分桶判例＋token null 行在案）。"""
    stats = aggregate(list(SAMPLE_ROWS))
    expect = {
        "total_rows": 7,
        "unique_questions": 7,
        "triggered_rows": 6,  # 过窄观测行（trigger 空）不计
        "breaker_rows": 1,
        "一致": 2,
        "分歧": 1,
        "不可比": 3,
        "bucket_overwide": 2,
        "bucket_overnarrow": 1,
        "latency_nonnull": 4,
        "p50": 1500,  # 最近秩：sorted [500,1500,2500,3500]，ceil(4*.5)-1=1 → 1500
        "p95": 3500,  # ceil(4*.95)-1=3 → 3500
        "max": 3500,
        "token_rows": 4,
        "prompt_total": 1000,
        "completion_total": 140,
        "token_null_rows": 2,  # 触发行内 null：异常行＋熔断行（过窄观测行不在触发行分母）
        "shape_top": ("window.start,window.end", 1),
    }
    latv = stats.latency_values
    uniq_n, trig_n, breaker_n = stats.unique_questions, stats.triggered_rows, stats.breaker_rows
    wide_n, narrow_n = stats.bucket_overwide, stats.bucket_overnarrow
    tok_null = stats.token_null_rows
    checks: list[tuple[str, bool, str]] = [
        ("总行数", stats.total_rows == expect["total_rows"], str(stats.total_rows)),
        ("去重问句", uniq_n == expect["unique_questions"], str(uniq_n)),
        ("触发比对行", trig_n == expect["triggered_rows"], str(trig_n)),
        ("熔断行", breaker_n == expect["breaker_rows"], str(breaker_n)),
        ("三态-一致", stats.state_counts[STATE_MATCH] == expect["一致"], str(stats.state_counts)),
        ("三态-分歧", stats.state_counts[STATE_DIVERGE] == expect["分歧"], ""),
        ("三态-不可比", stats.state_counts[STATE_INCOMPARABLE] == expect["不可比"], ""),
        ("过宽桶", wide_n == expect["bucket_overwide"], str(wide_n)),
        ("过窄桶", narrow_n == expect["bucket_overnarrow"], str(narrow_n)),
        ("延迟非空", len(latv) == expect["latency_nonnull"], str(len(latv))),
        ("p50", percentile(latv, 50) == expect["p50"], str(percentile(latv, 50))),
        ("p95", percentile(latv, 95) == expect["p95"], str(percentile(latv, 95))),
        ("max", max(latv) == expect["max"], str(max(latv))),
        ("usage非空行", stats.token_rows == expect["token_rows"], str(stats.token_rows)),
        ("prompt合计", stats.prompt_total == expect["prompt_total"], str(stats.prompt_total)),
        ("completion合计", stats.completion_total == expect["completion_total"], ""),
        ("token null 行", tok_null == expect["token_null_rows"], str(tok_null)),
    ]
    top_shape = next(iter(stats.divergent_shape_counts.items()), None)
    shape_ok = top_shape == expect["shape_top"]
    checks.append(("分歧TOP形态", shape_ok, str(stats.divergent_shape_counts)))
    report = render_report(
        stats, list(SAMPLE_ROWS), tag="DRYSAMPLE",
        log_path="（内置样例——无文件）", log_sha="0" * 64,
        judge={}, asked=10, env_note="干跑自检", traffic_note="内置样例 7 行",
        rerun_cmd="uv run python eval/results/tools/shadow_report.py --dry-run",
    )
    sample_states = {r["draft_state"] for r in SAMPLE_ROWS}
    sample_buckets = {r["bucket"] for r in SAMPLE_ROWS if r.get("bucket")}
    tri_ok = all(s in sample_states for s in TRI_STATES)
    buckets_ok = {BUCKET_OVERWIDE, BUCKET_OVERNARROW} <= sample_buckets
    null_ok = any(r.get("prompt_tokens") is None for r in SAMPLE_ROWS)
    checks.append(("样例三态齐全", tri_ok, ""))
    checks.append(("样例双分桶判例", buckets_ok, ""))
    checks.append(("样例 token null 行", null_ok, ""))
    checks.append(("报告渲染不抛错", "一致率" in report and "逐题表" in report, ""))
    failures = [c for c in checks if not c[1]]
    for name, ok, note in checks:
        print(f"  {'✓' if ok else '✗'} {name}" + (f"（{note}）" if note and not ok else ""))
    if failures:
        print(f"干跑自检失败 {len(failures)} 项")
        return 1
    print("干跑自检全过（样例三态齐全＋双分桶判例＋token null 行；四节数字与手算一致）")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="L-03 影子报告生成（离线聚合 L-02 影子 JSONL——零网络零模型）",
    )
    ap.add_argument("--tag", default="L03", help="报告标题与输出文件名前缀")
    ap.add_argument("--log", default="logs/shadow-plan.jsonl", help="影子 JSONL 路径")
    ap.add_argument("--out", default=None, help="输出 markdown（缺省 shadow-report-<tag>.md）")
    ap.add_argument("--judge", default=None, help="plan_rerun 判定表（可选——联 golden 题源）")
    ap.add_argument("--asked", type=int, default=None, help="跑批总问句数（可选——占比分母）")
    ap.add_argument("--env-note", default="本地 dev", help="环境描述（进报告头）")
    ap.add_argument("--traffic-note", default="", help="流量集口径（缺省自动标注）")
    ap.add_argument("--dry-run", action="store_true", help="离线自检：内置样例手算对账")
    args = ap.parse_args()
    if args.dry_run:
        return dry_run()
    log_path = Path(args.log)
    if not log_path.is_file():
        print(f"影子日志不存在：{log_path}", file=sys.stderr)
        return 1
    rows = load_rows(log_path)
    if not rows:
        print(f"影子日志为空：{log_path}", file=sys.stderr)
        return 1
    stats = aggregate(rows)
    judge = load_judge_index(args.judge)
    traffic = args.traffic_note or (
        f"golden 首批＋题册补题（判定表{'已联' if judge else '未联'}；"
        f"总问句{'已提供' if args.asked is not None else '未提供'}）"
    )
    out = Path(args.out) if args.out else Path("eval/results") / f"shadow-report-{args.tag}.md"
    rerun_parts = [
        "uv run python eval/results/tools/shadow_report.py",
        f"--tag {args.tag}", f"--log {args.log}", f"--out {out}",
    ]
    if args.judge:
        rerun_parts.append(f"--judge {args.judge}")
    if args.asked is not None:
        rerun_parts.append(f"--asked {args.asked}")
    if args.env_note != "本地 dev":
        rerun_parts.append(f"--env-note '{args.env_note}'")
    if args.traffic_note:
        rerun_parts.append(f"--traffic-note '{args.traffic_note}'")
    report = render_report(
        stats, rows, tag=args.tag, log_path=str(log_path), log_sha=file_sha256(log_path),
        judge=judge, asked=args.asked, env_note=args.env_note, traffic_note=traffic,
        rerun_cmd=" ".join(rerun_parts),
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")
    print(f"报告已产出：{out}（影子行 {stats.total_rows}，触发 {stats.triggered_rows}，"
          f"一致率分母 {stats.state_counts[STATE_MATCH] + stats.state_counts[STATE_DIVERGE]}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
