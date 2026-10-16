"""understanding 块验收（RT-W4-01a：-A 半面——装配／解析／`route` 闭世界／分派／事件／上报）。

票面对象＝`specs/understanding.md`「验收测试」表逐行（本票 11 行：规格表行序 1／2／5／6／7／8／
9／10／11／12／13——`#` 列保留规格表行序、不重编；测试标识与规格列逐字一致）：

| # | 测试 | 验收标准（规格列原文） |
|---|---|---|
| 1 | `::full_route_candidates_in_roster` | route=full 时返回 Understanding，且候选全部出自名录 |
| 2 | `::candidate_out_of_roster_violates` | 候选出现名录外名字 → 判违约（不静默丢弃） |
| 5 | `::malformed_json_raises_no_fallback` | （长行另记，见下） |
| 6 | `::route_enum_closed_world` | route 越界取值 → 判失败（不猜、不取默认） |
| 7 | `::task_book_three_zones` | 任务书三区顺序正确、数据区标来源且置于末尾 |
| 8 | `::data_zone_from_live_projection` | 台账投影变化 → 数据区文本随之变 |
| 9 | `::assembled_once_raw_not_in_dialogue` | 任务书每 run 只装配一次；模型原话不进对话层 |
| 10 | `::dispatch_by_route_only` | 程序只按 route 分派（换任意 route 取值都不触发词面判断） |
| 11 | `::no_lexicon_or_regex_in_understanding` | （长行另记，见下） |
| 12 | `::reporting_signal_present` | 「如实上报」的机读信号在场（notice ＋ step payload 字段） |
| 13 | `::understanding_text_event_emitted` | 理解文本发 `text` 事件（kind=understanding） |

两行超行宽者另记（`#` 与测试标识逐字同规格表、验收标准列逐字转抄）：

- 5｜`::malformed_json_raises_no_fallback`｜应答 JSON 不合 schema → 抛 UnderstandingParseError，
  不静默降级
- 11｜`::no_lexicon_or_regex_in_understanding`｜程序侧无词表／正则语义判断（AST 扫描本模块；
  **豁免面＝形态处理**——数字形判定与集合成员判定不算语义词表／正则）

本票**不含** -B 半面 5 行（规格表行序 3／4／14／15／16——归 RT-W4-01b）：直答结构核验的闭世界
判据、fail-closed 默认与样例集在本件**零断言**（防一头两认）；本件不预先落任何词面／形态判据。

**测试网钉**：pin-26（对话层纯度——落点行 9＝本块**渲染面**：模型原话经过程档案留痕、`dialogue`
零写入；写入面挂 `specs/bookkeeping.md`、字段面挂 `specs/state.md`，三处各认一面不重复）。

**跨文件对读件（转译输入半面）**：`tests/domains/test_v2_parsing.py::understanding_malformed_none_no_fallback`
——本件行 5 以**同一组合格外输入**双面同判（`parse_understanding` 返 `None` → 本块抛
`UnderstandingParseError`）对读该件（规格风险 4 检测手段；`specs/parsing.md` 接口⑤）。

**逐字稿面**：三区文本、段序与题干段为 `prompts` 单点（`specs/prompts.md` 行为 3–5）；本件的
活体面断言经**相位黑盒**观测（`interpret` 追加到链首的任务书），不另立第二份合同字面。
**待裁登记（流水 54①，本票按现状落、不自行改写）**：输出契约区文案与样例集实仓词属 Owner 审定
文案面；本件不对该两处文案的措辞下断言（只按区界断言）。

**已登记张力（本件如实标注、不静默）**：行 7 的「数据区…置于末尾」与规格行为 1「输出契约区
（末尾、短）」措辞相抵——本件按 `specs/prompts.md` 行为 3 的段序（指令区→数据区→输出契约区→
题干段）落判据：三区相对序正确 ＋ 数据区带来源标记 ＋ 数据区为**活体数据面的末位**（其后仅剩
两块固定短段：输出契约区与题干段；活体台账词只出现在数据区，不在固定短段）。登记交主窗。
"""

from __future__ import annotations

import ast
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

from appv2.runtimev2.gateway_adapter import ScriptedCompleter, set_completer
from appv2.runtimev2.parsing import Direct, Understanding, parse_understanding
from appv2.runtimev2.prompts import (
    TASK_BOOK_EXAMPLES,
    TASK_BOOK_OUTPUT_CONTRACT,
    TASK_BOOK_REDLINE,
    TASK_BOOK_SCENE,
    TASK_BOOK_TASK,
)
from appv2.runtimev2.state import RunState
from appv2.runtimev2.transport import EVENT_KINDS, NOTICE_TYPES, EventBus, SseEvent
from appv2.runtimev2.understanding import UnderstandingParseError, interpret

_REPO_ROOT = Path(__file__).resolve().parents[2]
_UNDERSTANDING_DIR = _REPO_ROOT / "appv2" / "runtimev2" / "understanding"

# ── 规格逐字面（独立于实现书写——实现漂移即红；真源 specs/understanding.md）──────────────
_SPEC_ROUTE_FULL = "full"
_SPEC_ROUTE_DIRECT = "direct"
_SPEC_TEXT_EVENT = "text"
_SPEC_TEXT_EVENT_KIND = "understanding"
_SPEC_NOTICE_KEYS = {"type", "gates", "content"}
_SPEC_STEP_KEYS = ("run_id", "seq", "step", "status", "title", "manifest", "payload")
_SPEC_PROCESS_NOTE_KEYS = {"phase", "title", "digest"}
_SPEC_DRAFT_KIND_DIRECT = "direct"
_SPEC_INTENT_ANSWER = "answer"
_SPEC_CALLER = "understand"  # 模型调用归因桶（真源 specs/gateway_adapter.md 行为 5 三桶族）
# 数据区来源标记（标来源面——真源 specs/understanding.md 行为 2；字面同 prompts 渲染单点）
_DATA_ZONE_HEAD = "【环境】（以下由系统按当前数据现状动态装配）"
# 机读上报字段名（本块自立的机读面——行 12「step payload 字段」的字段名即此；改名即红）
_PAYLOAD_PHASE_KEY = "phase"
_PAYLOAD_EVENT_KEY = "event"
_PAYLOAD_CANDIDATES_KEY = "metric_candidates"
_PAYLOAD_OFFENDERS_KEY = "offenders"
_PAYLOAD_RAW_EXCERPT_KEY = "raw_excerpt"
_EVENT_CANDIDATE_VIOLATION = "candidate_out_of_roster"
_EVENT_PARSE_FAILURE = "parse_failure"
# 过程档案条目（本块两标题：装配一次标记 ＋ 模型原话留痕）
_TASK_BOOK_NOTE_TITLE = "任务书装配"

# ── fixture 投影（台账活体投影形——`tools.ledger_facts` 十入面：metrics／aliases／terms／…）──
_METRIC_ROWS: tuple[dict[str, Any], ...] = (
    {"slot": "日产油量", "name": "日产油量", "binding_state": "bound"},
    {"slot": "含水率", "name": "含水率", "binding_state": "unbound"},
)
_ALIASES: dict[str, str] = {"产油量": "日产油量"}
# 名录闭世界（fixture 面独立算出：slot ∪ 指标名 ∪ 别名——行 1／2 的判据基准）
_ROSTER: frozenset[str] = frozenset(
    {row["slot"] for row in _METRIC_ROWS}
    | {row["name"] for row in _METRIC_ROWS}
    | set(_ALIASES)
)
_OUT_OF_ROSTER = "库存总量"  # 名录外生词（fixture 词集外的名字）

_QUESTION = "K12-3 井最近日产油量是多少？"
_WATERMARK = "2026-08-24"


def _ledger_dump(
    *,
    metrics: Sequence[Mapping[str, Any]] = _METRIC_ROWS,
    aliases: Mapping[str, str] = _ALIASES,
) -> dict[str, Any]:
    return {
        "metrics": [dict(row) for row in metrics],
        "aliases": dict(aliases),
        "terms": [{"value": "躺井", "term": "躺井", "banned": False}],
        "objects": [{"value": "井"}],
        "relations": [{"value": "属于"}],
        "families_map": {"月报": ["monthly"]},
    }


def _state(**overrides: Any) -> RunState:
    values: dict[str, Any] = {
        "run_id": "run-ut-01",
        "question": _QUESTION,
        "actor": "laowang",
        "ledger_dump": _ledger_dump(),
    }
    values.update(overrides)
    return RunState(**values)


def _full_reply(text: str, candidates: Sequence[str]) -> str:
    return json.dumps(
        {"route": _SPEC_ROUTE_FULL, "text": text, "metric_candidates": list(candidates)},
        ensure_ascii=False,
    )


def _direct_reply(text: str) -> str:
    return json.dumps({"route": _SPEC_ROUTE_DIRECT, "text": text}, ensure_ascii=False)


def _interpret_all(
    state: RunState, *replies: str, watermark: str = ""
) -> tuple[list[Any], EventBus]:
    """注入剧本化 completer（同面替身）与 per-run 总线跑读题；返回（逐次返回值，总线）。

    剧本按调用序取条（同 caller 队列多轮 replay）——单回调用例传一条，重入用例传两条。
    """
    previous = set_completer(ScriptedCompleter({_SPEC_CALLER: list(replies)}))
    bus = EventBus()
    try:
        outs = [interpret(state, bus=bus, watermark=watermark) for _ in replies]
    finally:
        set_completer(previous)
    return outs, bus


def _interpret(state: RunState, reply: str, *, watermark: str = "") -> tuple[Any, EventBus]:
    outs, bus = _interpret_all(state, reply, watermark=watermark)
    return outs[0], bus


async def _frames(bus: EventBus) -> list[SseEvent]:
    """读尽一条已收束总线的帧（先 `close`——未收束会等待新帧）。"""
    bus.close()
    return [frame async for frame in bus.stream(0)]


def _task_book_of(state: RunState) -> str:
    """链首任务书（本块装配的接入形：首条 user 消息）——黑盒观测面。"""
    assert state.messages, "链上空——任务书未装配"
    first = state.messages[0]
    assert first["role"] == "user", first
    return str(first["content"])


def _report_steps(state: RunState) -> list[dict[str, Any]]:
    """报告步（非模型调用步——调用步由 `bookkeeping.call_model` 单点记账，标题含「模型调用」）。"""
    return [
        step
        for step in state.steps
        if isinstance(step.get("payload"), Mapping)
        and _PAYLOAD_EVENT_KEY in step["payload"]
    ]


# ---------- 1 route=full：返回 Understanding 且候选全部出自名录 ----------


def test_full_route_candidates_in_roster() -> None:
    """#1｜route=full 时返回 Understanding，且候选全部出自名录（行为 6／8／12）。

    双出口（行为 12）：`state.understanding`／`state.metric_candidates` 与 `text` 事件同源；
    模型调用步＝`bookkeeping.call_model` 单点记账的一条（本块不为同一调用再记步）。
    """
    state = _state()
    text = "用户问 K12-3 井的日产油量（含别名口径）。"
    out, _bus = _interpret(state, _full_reply(text, ["日产油量", "产油量"]))

    assert isinstance(out, Understanding) and out.route == _SPEC_ROUTE_FULL
    assert set(out.metric_candidates) <= _ROSTER  # 候选全部出自名录（闭世界集合成员）
    assert out.text == text
    assert state.understanding == text
    assert state.metric_candidates == ["日产油量", "产油量"]
    assert state.notices == []  # 无违约 → 零注记（不凭空产信号）
    assert _report_steps(state) == []

    # 模型调用记账面：恰一条步（call_model 单点），归因桶＝理解桶
    assert len(state.steps) == 1
    step = state.steps[0]
    assert tuple(step) == _SPEC_STEP_KEYS
    assert step["payload"]["caller"] == _SPEC_CALLER
    assert str(step["title"]).startswith("模型调用")  # 记账面标题（prompts 侧零涉）
    assert state.dialogue == []  # 对话层零写入（pin-26 渲染面）


# ---------- 2 候选出现名录外名字 → 判违约（不静默丢弃） ----------


def test_candidate_out_of_roster_violates() -> None:
    """#2｜候选出现名录外名字 → 判违约（不静默丢弃）——行为 8 红线。

    候选**原样保留**（双出口与状态字段都不丢词）＋机读上报两件套点名（报告步 payload 全量候选
    与违约项 ＋ notice 逐字点名）。
    """
    state = _state()
    text = "用户问日产油量，并提到库存总量。"
    candidates = ["日产油量", _OUT_OF_ROSTER]
    out, _bus = _interpret(state, _full_reply(text, candidates))

    assert isinstance(out, Understanding)
    assert out.metric_candidates == candidates  # 返回值不静默丢弃
    assert state.metric_candidates == candidates  # 状态字段不静默丢弃
    assert not set(candidates) <= _ROSTER  # 判据面：确有名录外项

    reports = _report_steps(state)
    assert len(reports) == 1
    payload = reports[0]["payload"]
    assert payload[_PAYLOAD_PHASE_KEY] == _SPEC_CALLER
    assert payload[_PAYLOAD_EVENT_KEY] == _EVENT_CANDIDATE_VIOLATION
    assert payload[_PAYLOAD_CANDIDATES_KEY] == candidates
    assert payload[_PAYLOAD_OFFENDERS_KEY] == [_OUT_OF_ROSTER]
    assert reports[0]["status"] == "failed"  # 如实态（不恒 ok）

    assert len(state.notices) == 1
    notice = state.notices[0]
    assert set(notice) == _SPEC_NOTICE_KEYS
    assert notice["type"] in NOTICE_TYPES
    assert _OUT_OF_ROSTER in notice["content"] and notice["gates"] == []


# ---------- 5 应答 JSON 不合 schema → 抛 UnderstandingParseError（不静默降级） ----------


_MALFORMED_REPLIES: tuple[str, ...] = (
    "理解：用户问日产油量。\n指标候选：日产油量",  # 旧两行式（V2 不再受理——零降级提取）
    "抱歉，这题我看不了。",  # 非 JSON
    "「route」: full",  # 残缺 JSON
    json.dumps({"route": _SPEC_ROUTE_FULL, "text": 3, "metric_candidates": []}),  # 类型不符
    json.dumps({"route": _SPEC_ROUTE_FULL, "text": "x"}),  # 缺 metric_candidates
    json.dumps({"route": _SPEC_ROUTE_DIRECT}),  # 缺 text
    json.dumps({"route": _SPEC_ROUTE_FULL, "text": "x", "metric_candidates": "日产油量"}),
    json.dumps(["full", "x"]),  # 顶层非对象
)


def test_malformed_json_raises_no_fallback() -> None:
    """#5｜应答 JSON 不合 schema → 抛 UnderstandingParseError，不静默降级——行为 7。

    **跨文件对读**（转译输入半面）：同一组合格外输入在 `parse_understanding` 侧返 `None`（对读件
    `tests/domains/test_v2_parsing.py::understanding_malformed_none_no_fallback`），本块以唯一
    转译出口抛同类错；**不返回半成品**（状态字段零写入）＋如实上报（notice ＋ step payload）。
    """
    for raw in _MALFORMED_REPLIES:
        state = _state()
        with pytest.raises(UnderstandingParseError) as excinfo:
            _interpret(state, raw)
        error = excinfo.value
        assert error.raw == raw
        assert error.excerpt and error.excerpt in str(error)
        # 唯一转译出口的输入半面：同一输入 parsing 侧返 None（不降级、不返回半成品）
        assert parse_understanding(raw) is None
        # 不返回半成品：两通道字段均零写入
        assert state.understanding == "" and state.metric_candidates == []
        assert state.draft == "" and state.draft_kind == ""
        # 如实上报（不许静默）：notice ＋ 报告步 payload 字段
        assert len(state.notices) == 1
        assert set(state.notices[0]) == _SPEC_NOTICE_KEYS
        assert state.notices[0]["type"] in NOTICE_TYPES
        reports = _report_steps(state)
        assert len(reports) == 1
        assert reports[0]["payload"][_PAYLOAD_EVENT_KEY] == _EVENT_PARSE_FAILURE
        assert reports[0]["payload"][_PAYLOAD_RAW_EXCERPT_KEY] == error.excerpt
        assert reports[0]["status"] == "failed"

    # 超长应答：片段截断**可见**（截断标记在场，不静默硬切）
    state = _state()
    long_raw = "不是 JSON" + "。" * 500
    with pytest.raises(UnderstandingParseError) as excinfo:
        _interpret(state, long_raw)
    assert excinfo.value.raw == long_raw
    assert excinfo.value.excerpt.endswith("…") and len(excinfo.value.excerpt) <= 200


# ---------- 6 route 越界取值 → 判失败（不猜、不取默认） ----------


def test_route_enum_closed_world() -> None:
    """#6｜route 越界取值 → 判失败（不猜、不取默认）——接口定义「`route` 是闭世界」。

    闭世界仅 `full`｜`direct`；越界（含大小写变形／缺键／`null`／空表）一律
    `UnderstandingParseError`，
    **无默认路由**：两通道字段均零写入。
    """
    cases: tuple[str, ...] = (
        json.dumps({"route": "partial", "text": "x"}),
        json.dumps({"route": "FULL", "text": "x", "metric_candidates": []}),
        json.dumps({"route": "理解", "text": "x", "metric_candidates": []}),
        json.dumps({"text": "x"}),  # 缺 route
        json.dumps({}),  # 空对象
        json.dumps({"route": None, "text": "x"}),
        json.dumps({"route": True, "text": "x"}),
    )
    for raw in cases:
        state = _state()
        with pytest.raises(UnderstandingParseError):
            _interpret(state, raw)
        assert state.understanding == "" and state.metric_candidates == []
        assert state.draft == "" and state.draft_kind == "" and state.next_intent == ""
        assert parse_understanding(raw) is None  # 与 parsing 面同判（无默认通道）

    # 两形互斥的合法面：同一次调用只回一支（行 6 的对照面——合法值恒落对）
    state = _state()
    out, _bus = _interpret(state, _direct_reply("不客气。"))
    assert isinstance(out, Direct) and out.route == _SPEC_ROUTE_DIRECT


# ---------- 7 任务书三区顺序正确、数据区标来源且置于末尾 ----------


def test_task_book_three_zones() -> None:
    """#7｜任务书三区顺序正确、数据区标来源且置于末尾——行为 1／2（Δ 口径见件头「已登记张力」）。

    三区（指令区四常量→数据区→输出契约区）相对序唯一；数据区带**来源标记**；数据区为**活体数据
    面的末位**（其后仅剩两块固定短段：输出契约区与题干段——活体台账词只在数据区出现）。
    """
    state = _state()
    _interpret(state, _full_reply("用户问日产油量。", ["日产油量"]))
    book = _task_book_of(state)

    order = [
        TASK_BOOK_SCENE,
        TASK_BOOK_TASK,
        TASK_BOOK_EXAMPLES,
        TASK_BOOK_REDLINE,  # 指令区内四常量相对序：场景→任务→样例→红线
        _DATA_ZONE_HEAD,
        TASK_BOOK_OUTPUT_CONTRACT,
    ]
    positions = [book.index(marker) for marker in order]
    assert positions == sorted(positions) and len(set(positions)) == len(positions)

    # 数据区标来源（行为 2 的「标来源」面）：来源标记恰一份
    assert book.count(_DATA_ZONE_HEAD) == 1
    # 数据区置于（活体数据面的）末尾：活体台账词只在数据区、不在其后的固定短段
    data_zone_start = book.index(_DATA_ZONE_HEAD)
    metric_line = "日产油量｜可出数"
    assert book.index(metric_line) > data_zone_start
    assert book.index(metric_line) < book.index(TASK_BOOK_OUTPUT_CONTRACT)
    assert book.rstrip().endswith("现在输出。）")  # 题干段为装配尾段（prompts 行为 3 段序）
    # 三区之外零活体数据段：装配体里只此一处来源标记
    assert book.index(TASK_BOOK_REDLINE) < data_zone_start


# ---------- 8 台账投影变化 → 数据区文本随之变 ----------


def test_data_zone_from_live_projection() -> None:
    """#8｜台账投影变化 → 数据区文本随之变——行为 2（数据区每轮从活体投影现取）。

    投影增行 → 文本同步增行（新增指标行在场且带绑定态）；水位（注入的时间量）同款现取。
    """
    base_state = _state()
    _interpret(base_state, _full_reply("问日产油量。", ["日产油量"]))
    base = _task_book_of(base_state)

    grown_state = _state(
        ledger_dump=_ledger_dump(
            metrics=(
                *_METRIC_ROWS,
                {"slot": "检泵周期", "name": "检泵周期", "binding_state": "unbound"},
            )
        )
    )
    _interpret(grown_state, _full_reply("问日产油量。", ["日产油量"]))
    grown = _task_book_of(grown_state)

    assert base != grown
    assert "检泵周期" in grown and "检泵周期" not in base
    assert "含水率" in base and "含水率" in grown  # 未变行照旧在场（不整块替换）
    assert _DATA_ZONE_HEAD in base and _DATA_ZONE_HEAD in grown

    # 时间量同款只经入参注入（B14：本块零时钟接触）：注入水位 → 数据区文本随之变
    stamped_state = _state()
    _interpret(
        stamped_state,
        _full_reply("问日产油量。", ["日产油量"]),
        watermark=_WATERMARK,
    )
    stamped = _task_book_of(stamped_state)
    assert _WATERMARK in stamped and _WATERMARK not in base


# ---------- 9 任务书每 run 只装配一次；模型原话不进对话层（pin-26 渲染面） ----------


def test_assembled_once_raw_not_in_dialogue() -> None:
    """#9｜任务书每 run 只装配一次；模型原话不进对话层——行为 9（pin-26 **渲染面**）。

    重入（同 run 二次进入）→ 链上任务书仍恰一份、装配标记恰一条；模型原话经过程档案（`note`）
    留痕；**`dialogue` 零写入**（对话层只装自然对话——渲染面口径，写入面归 `bookkeeping`
    `append_dialogue`、字段面归 `state` 行为 6）。
    """
    state = _state()
    first = _full_reply("第一次读题：问日产油量。", ["日产油量"])
    second = _full_reply("第二次读题：问日产油量。", ["日产油量"])
    outs, _bus = _interpret_all(state, first, second)

    assert len(outs) == 2
    book = _task_book_of(state)
    assert sum(1 for m in state.messages if m["content"] == book) == 1  # 每 run 只装配一次
    assert [m["role"] for m in state.messages] == ["user", "assistant", "assistant"]
    # 模型原话＝链上留痕（应答追加链尾——agent-loop 行为 2 追加式）
    assert [m["content"] for m in state.messages[1:]] == [first, second]

    # 过程档案留痕（行为 9）：模型原话入 `process_notes`、装配标记恰一条
    digests = [entry["digest"] for entry in state.process_notes]
    assert first in digests and second in digests
    markers = [
        entry for entry in state.process_notes if entry["title"] == _TASK_BOOK_NOTE_TITLE
    ]
    assert len(markers) == 1
    for entry in state.process_notes:
        assert set(entry) == _SPEC_PROCESS_NOTE_KEYS
        assert entry["phase"] == _SPEC_CALLER

    # pin-26 渲染面：模型原话**不进对话层**——`dialogue` 零写入（过程记录不混层）
    assert state.dialogue == []
    assert not any(
        first in str(entry.get("content", "")) for entry in state.dialogue
    )


# ---------- 10 程序只按 route 分派（换任意 route 取值都不触发词面判断） ----------


async def test_dispatch_by_route_only() -> None:
    """#10｜程序只按 route 分派（换任意 route 取值都不触发词面判断）——行为 4／6。

    **同一段文本**给两个 route 取值 → 两条分派面各自落位（full：理解字段＋旁白事件、直答面零写；
    direct：收口旁路三键、理解字段零写）——分派只由 `route` 取值决定（本半面零词面／形态判据，
    闭世界核验归 -B 且本件**不预设其判据**：故探针文本取**-B 闭世界外**的中性文本〔无阿拉伯数字、
    无名录指标名、无结构卡表名〕，本件不代 -B 断言直答认可面）。
    """
    body = "谢谢你，辛苦了。"

    full_state = _state(run_id="run-ut-route-full")
    full_out, full_bus = _interpret(full_state, _full_reply(body, []))
    direct_state = _state(run_id="run-ut-route-direct")
    direct_out, direct_bus = _interpret(direct_state, _direct_reply(body))

    assert isinstance(full_out, Understanding) and full_out.route == _SPEC_ROUTE_FULL
    assert isinstance(direct_out, Direct) and direct_out.route == _SPEC_ROUTE_DIRECT

    # full 分派面：理解双出口两件落位；直答旁路三件零写（单出口互斥）
    assert full_state.understanding == body
    assert full_state.draft == "" and full_state.draft_kind == "" and full_state.next_intent == ""
    # direct 分派面：收口旁路三键；理解字段零写
    assert direct_state.draft == body
    assert direct_state.draft_kind == _SPEC_DRAFT_KIND_DIRECT
    assert direct_state.next_intent == _SPEC_INTENT_ANSWER
    assert direct_state.understanding == "" and direct_state.metric_candidates == []

    # 事件面随 route 分派：full 发理解旁白；direct 零旁白（文本形不触发事件——不由词面决定）
    assert [frame.event for frame in await _frames(full_bus)] == [_SPEC_TEXT_EVENT]
    assert await _frames(direct_bus) == []


# ---------- 11 程序侧无词表／正则语义判断（AST；豁免面＝形态处理） ----------


_BANNED_STR_METHODS = {
    "startswith",
    "endswith",
    "lower",
    "upper",
    "casefold",
    "split",
    "partition",
    "format_map",
    "count",
}
_IDENTIFIER_SHAPE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _block_sources() -> list[tuple[Path, ast.Module]]:
    return [
        (path, ast.parse(path.read_text(encoding="utf-8")))
        for path in sorted(_UNDERSTANDING_DIR.rglob("*.py"))
    ]


def _imported_modules(tree: ast.Module) -> list[str]:
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return modules


def _lexicon_violations(tree: ast.Module) -> list[str]:
    """词表／正则面判据：正则面（import／属性）＋非标识符形字符串集合（语义词表）＋词面判方法。"""
    findings: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [alias.name for alias in node.names]
            if isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
            if any(name.split(".")[0] in {"re", "regex"} for name in names):
                findings.append(f"{node.lineno} 引入正则面：{names}")
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id in {"re", "regex"}:
                findings.append(f"{node.lineno} 使用正则面：{node.value.id}.{node.attr}")
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            values = [
                element.value
                for element in node.elts
                if isinstance(element, ast.Constant) and isinstance(element.value, str)
            ]
            if any(not _IDENTIFIER_SHAPE.fullmatch(value) for value in values):
                findings.append(f"{node.lineno} 非标识符形字符串集合（语义词表）：{values}")
        if isinstance(node, ast.Compare):
            for op in node.ops:
                if isinstance(op, (ast.In, ast.NotIn)):
                    for operand in (node.left, *node.comparators):
                        if isinstance(operand, ast.Constant) and isinstance(operand.value, str):
                            if not operand.value.isascii():
                                findings.append(
                                    f"{node.lineno} 非结构字符集的成员判据：{operand.value!r}"
                                )
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in _BANNED_STR_METHODS:
                findings.append(f"{node.lineno} 词面判方法：{node.func.attr}")
    return findings


def _membership_sites(tree: ast.Module) -> list[int]:
    """闭世界集合成员判定位点（形态处理豁免面的实际出现面——探测扫描面非空转）。"""
    return [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Compare)
        and any(isinstance(op, (ast.In, ast.NotIn)) for op in node.ops)
    ]


def test_no_lexicon_or_regex_in_understanding() -> None:
    """#11｜程序侧无词表／正则语义判断（AST 扫描本模块；豁免面＝形态处理）——行为 4 的对策面。

    豁免面＝形态处理（**数字形判定与集合成员判定不算语义词表／正则**——规格验收行原文；本半面
    实际出现＝名录**集合成员判定**，数字形判定归 -B）。扫描面＝本块七个源文件；探测非空转。

    〔给 -B 的前向注（不预设其实现）〕本扫描面只禁**语义词表字面**（非标识符形字符串集合）与
    词面判方法（前缀／后缀／大小写折叠／切分／计数）——**数字形判定**若以字符形函数（如
    `str.isdigit`／`unicodedata`）或 ASCII 字符集表达，恒在豁免面内；若需以全角字符集字面成员
    判定表达，同批收窄本扫描面的字符集规则（`specs/understanding.md` 风险 2 的豁免面）。
    """
    sources = _block_sources()
    assert len(sources) >= 6, f"扫描面可疑（文件数 {len(sources)}）"
    for path, tree in sources:
        assert _lexicon_violations(tree) == [], f"{path.name}: {_lexicon_violations(tree)}"

    # 豁免面非空转：本块确有闭世界集合成员判定位点（名录对账——形态处理）
    membership = [line for _path, tree in sources for line in _membership_sites(tree)]
    assert membership, "集合成员判定缺席——扫描面空转"

    # 探测器非空转：词表／正则／词面判方法三形各被咬
    assert _lexicon_violations(ast.parse('WORDS = ["提及", "执行"]\n'))
    assert _lexicon_violations(ast.parse('import re\nre.search("理解", text)\n'))
    assert _lexicon_violations(ast.parse('if "谢谢" in text:\n    pass\n'))
    assert _lexicon_violations(ast.parse('text.startswith("理解：")\n'))
    assert _lexicon_violations(ast.parse('names.count("日产油量")\n'))


# ---------- 12 「如实上报」的机读信号在场（notice ＋ step payload 字段） ----------


def test_reporting_signal_present() -> None:
    """#12｜「如实上报」的机读信号在场（notice ＋ step payload 字段）——「不降级与静默禁令」。

    两案（-B 承接的「直答退回」案不在本件）：**候选违约**与**解析失败**——各两件套齐备
    （notice 恰三键且 `type` ∈ `NOTICE_TYPES`；报告步 payload 携如实字段、状态 `failed`），
    且**常规路径零补记步**（模型调用步由 `bookkeeping.call_model` 单点记账——步序不翻倍）。
    """
    # 案一：候选违约
    violation_state = _state()
    _interpret(violation_state, _full_reply("问日产油量与库存总量。", ["日产油量", _OUT_OF_ROSTER]))
    assert len(violation_state.steps) == 2  # 记账步 1 ＋ 报告步 1（不翻倍）
    assert len(_report_steps(violation_state)) == 1

    # 案二：解析失败
    failure_state = _state()
    with pytest.raises(UnderstandingParseError):
        _interpret(failure_state, "两行式已退场：理解：x／指标候选：y")
    assert len(failure_state.steps) == 2
    assert len(_report_steps(failure_state)) == 1

    # 常规路径（无上报面）：恰一条记账步、零报告步、零注记
    clean_state = _state()
    _interpret(clean_state, _full_reply("问日产油量。", ["日产油量"]))
    assert len(clean_state.steps) == 1 and _report_steps(clean_state) == []
    assert clean_state.notices == []

    for state in (violation_state, failure_state):
        assert len(state.notices) == 1
        notice = state.notices[0]
        assert set(notice) == _SPEC_NOTICE_KEYS and notice["type"] in NOTICE_TYPES
        assert notice["content"]
        report = _report_steps(state)[0]
        assert tuple(report) == _SPEC_STEP_KEYS
        assert report["step"] in {"decision"}  # 六值闭世界（理解轮无专属步型）
        assert report["payload"][_PAYLOAD_PHASE_KEY] == _SPEC_CALLER
        assert report["payload"][_PAYLOAD_EVENT_KEY] in {
            _EVENT_CANDIDATE_VIOLATION,
            _EVENT_PARSE_FAILURE,
        }


# ---------- 13 理解文本发 text 事件（kind=understanding） ----------


async def test_understanding_text_event_emitted() -> None:
    """#13｜理解文本发 `text` 事件（kind=understanding）——行为 12（发射单元 M1）。

    帧名 ∈ `EVENT_KINDS`、载荷形 `{content, kind}`（真源 `synth/S6-事件与帧目录.md` §一 text 行）；
    与 `state.understanding` 同源＝双出口（行为 12 的状态字段 ＋ 事件两件）。
    """
    state = _state()
    text = "用户问 K12-3 井日产油量，需要按指标口径取数。"
    out, bus = _interpret(state, _full_reply(text, ["日产油量"]))
    frames = await _frames(bus)

    texts = [frame for frame in frames if frame.event == _SPEC_TEXT_EVENT]
    assert len(texts) == 1
    frame = texts[0]
    assert frame.event in EVENT_KINDS
    assert frame.data == {"content": text, "kind": _SPEC_TEXT_EVENT_KIND}
    assert frame.data["content"] == state.understanding == out.text  # 双出口同源


# ---------- 元面机检：模型调用无旁路 ＋ import 面闭合（R7／R6／R5b／R5／R1 的降维面） ----------


_ALLOWED_APPV2_IMPORTS = {
    "appv2.tools",
    "appv2.runtimev2.state",
    "appv2.runtimev2.bookkeeping",
    "appv2.runtimev2.prompts",
    "appv2.runtimev2.parsing",
    "appv2.runtimev2.transport",
    "appv2.runtimev2.persistence",
    "appv2.runtimev2.understanding",
}
_FORBIDDEN_CALL_NAMES = {"complete", "ainvoke", "invoke", "agenerate", "generate", "set_completer"}


def _bypass_findings(sources: Sequence[tuple[Path, ast.Module]]) -> list[str]:
    findings: list[str] = []
    for path, tree in sources:
        for module in _imported_modules(tree):
            root = module.split(".")[0]
            if root == "appv2":
                allowed = any(
                    module == candidate or module.startswith(candidate + ".")
                    for candidate in _ALLOWED_APPV2_IMPORTS
                )
                if not allowed:
                    findings.append(f"{path.name} 越界引块：{module}")
            elif root in {"litellm", "langgraph", "langchain", "openai", "app"}:
                findings.append(f"{path.name} 越界依赖：{module}")
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in _FORBIDDEN_CALL_NAMES:
                    findings.append(f"{path.name}:{node.lineno} 自建模型调用旁路：{node.func.id}")
                if isinstance(node.func, ast.Attribute) and node.func.attr in {"complete"}:
                    findings.append(
                        f"{path.name}:{node.lineno} 自建模型调用旁路：.{node.func.attr}"
                    )
    return findings


def test_no_model_call_bypass_and_closed_import_face() -> None:
    """元面｜模型调用无旁路（R7＋「无旁路」断言）＋ import 面闭合（R1／R5／R5b／R6 的降维面）。

    发起点只在 `bookkeeping.call_model`（本块无自建客户端、无 `complete` 直呼）；import 面＝批准
    包根白名单（不直引 `gateway_adapter`／`appv2.infra.llm_client`／引擎／框架／旧码／其它相位）。
    """
    sources = _block_sources()
    assert sources
    assert _bypass_findings(sources) == []

    imported = {module for _path, tree in sources for module in _imported_modules(tree)}
    assert "appv2.runtimev2.gateway_adapter" not in imported
    assert not any(module.startswith("appv2.infra") for module in imported)
    assert not any(
        module.startswith(("appv2.knowledge", "appv2.query", "appv2.retrieval"))
        for module in imported
    )
    assert "appv2.runtimev2.bookkeeping" in imported  # 模型调用发起面（包根——R2 禁深层）
    assert "appv2.tools" in imported  # 名录面（只经公开面——R6）

    # 探测非空转：四形越界各被咬
    for source, needle in (
        ("from appv2.runtimev2.gateway_adapter import complete\n", "越界引块"),
        ("from appv2.infra.llm_client import embeddings\n", "越界引块"),
        ("from appv2.runtimev2.tool_matching import match\n", "越界引块"),
        ("import litellm\n", "越界依赖"),
        ("async def go(egress):\n    await egress.complete([])\n", "自建模型调用旁路"),
        ("complete([], caller='understand')\n", "自建模型调用旁路"),
    ):
        forged = [(Path("forged.py"), ast.parse(source))]
        assert any(needle in finding for finding in _bypass_findings(forged)), source


# ---------- 元面机检：总线未注入＝fail-closed（不静默丢弃旁白事件） ----------


def test_bus_missing_fails_closed_before_any_side_effect() -> None:
    """元面｜总线未注入＝入口 fail-closed 抛错（不静默跳过旁白事件），且零副作用（不半写）。

    本块两个关键词注入面（`bus`／`watermark`）见 `interpret` 模块注——`bus` 缺失即调用方断线，
    入口先抛错（同 `gateway_adapter._configured_completer` 先例：无出口不静默兜底）。
    """
    state = _state()
    previous = set_completer(ScriptedCompleter({_SPEC_CALLER: [_full_reply("问日产油量。", [])]}))
    try:
        with pytest.raises(RuntimeError):
            interpret(state)
    finally:
        set_completer(previous)
    # 零副作用（抛错在任何写口调用之前）：链／步／过程档案／通知／字段全空
    assert state.messages == [] and state.steps == []
    assert state.process_notes == [] and state.notices == []
    assert state.understanding == "" and state.metric_candidates == []
