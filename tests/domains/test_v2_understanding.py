"""understanding 块验收（RT-W4-01a／-01b：装配／解析／路由闭世界／分派／事件／上报／直答核验）。

票面对象＝`specs/understanding.md`「验收测试」表逐行（-A 票 11 行：规格表行序 1／2／5／6／7／8／
9／10／11／12／13；-B 票 5 行：3／4／14／15／16——`#` 列保留规格表行序、不重编；测试标识与规格列
逐字一致）：

| # | 测试 | 验收标准（规格列原文） |
|---|---|---|
| 1 | `::full_route_candidates_in_roster` | route=full 时返回 Understanding，且候选全部出自名录 |
| 2 | `::candidate_out_of_roster_violates` | 候选出现名录外名字 → 判违约（不静默丢弃） |
| 3 | `::direct_on_greeting` | 寒暄句（道谢／道别）→ route=direct，文本不含数据或事实断言 |
| 4 | `::direct_with_assertion_rejected` | route=direct 但文本含数值形 → 不合格，退回 full |
| 5 | `::malformed_json_raises_no_fallback` | （长行另记，见下） |
| 6 | `::route_enum_closed_world` | route 越界取值 → 判失败（不猜、不取默认） |
| 7 | `::task_book_three_zones` | 任务书三区顺序正确、数据区标来源且置于末尾 |
| 8 | `::data_zone_from_live_projection` | 台账投影变化 → 数据区文本随之变 |
| 9 | `::assembled_once_raw_not_in_dialogue` | 任务书每 run 只装配一次；模型原话不进对话层 |
| 10 | `::dispatch_by_route_only` | 程序只按 route 分派（换任意 route 取值都不触发词面判断） |
| 11 | `::no_lexicon_or_regex_in_understanding` | （长行另记，见下） |
| 12 | `::reporting_signal_present` | 「如实上报」的机读信号在场（notice ＋ step payload 字段） |
| 13 | `::understanding_text_event_emitted` | 理解文本发 `text` 事件（kind=understanding） |
| 14 | `::route_defaults_fail_closed` | （长行另记，见下） |
| 15 | `::direct_boundary_cases_rejected` | （长行另记，见下） |
| 16 | `::retention_non_direct_unchanged` | （长行另记，见下） |

五行超行宽者另记（`#` 与测试标识逐字同规格表、验收标准列逐字转抄）：

- 5｜`::malformed_json_raises_no_fallback`｜应答 JSON 不合 schema → 抛 UnderstandingParseError，
  不静默降级
- 11｜`::no_lexicon_or_regex_in_understanding`｜程序侧无词表／正则语义判断（AST 扫描本模块；
  **豁免面＝形态处理**——数字形判定与集合成员判定不算语义词表／正则）
- 14｜`::route_defaults_fail_closed`｜路由默认 fail-closed：拿不准／可能有关 → 完整流程；灰区
  （我能问什么／预测明年油价）→ 完整流程
- 15｜`::direct_boundary_cases_rejected`｜【边界集】**名录内**指标名／**结构卡内**表名／全角数字
  → 直答判不合格
- 16｜`::retention_non_direct_unchanged`｜【保留集】寒暄仍走 direct；route=full 的既有候选校验
  行为不变

**-B 半面（行 3／4／14／15／16）的判据面**：直答结构核验（`closure.direct_assertion_hits`）——
**数值形**（NFKC 归一后按 ASCII 数字位）命中即判不合格 → 退回 `route="full"` 的 `Understanding`
＋过程档案一条「直答退回」注记＋如实上报两件套（不抛错、不静默、不直答收口）。**2026-10-18
V2-83 判据收窄**：指标名/表名单独出现不再命中（问候/能力介绍是介绍不是数据断言；真机
`run-a11920fb` 误退根治）——见行 15 保留集。**行 14 的判据面读法（如实登记）**：行为 11 的
「默认倾向 fail-closed」按真源（`walk/05-理解-定路由.md` §七 第 3 条）是**给模型的判断原则**、
非程序规则——本件两面落判据：
①**原则在场**（装配进任务书的指令区例外条款与题干段收束句——模型唯一决策输入，经相位黑盒观测）；
②**灰区不落直答口**（拿不准／可能有关／灰区句的直答认领，其应答带数值断言 → 结构核验
命中 → 程序确定性退回完整流程）。**程序侧零词面判据**（不判「相关性」、不设灰区词表——行为 4）：
灰区问句本身归完整流程靠模型按该原则判、程序按 `route` 分派（本件以「判 full → 走 full 分派」的
同问句对照面同时断言）。

**测试网钉**：pin-26（对话层纯度——落点行 9＝本块**渲染面**：模型原话经过程档案留痕、`dialogue`
零写入；写入面挂 `specs/bookkeeping.md`、字段面挂 `specs/state.md`，三处各认一面不重复）。

**跨文件对读件（转译输入半面）**：`tests/domains/test_v2_parsing.py::understanding_malformed_none_no_fallback`
——本件行 5 以**同一组合格外输入**双面同判（`parse_understanding` 返 `None` → 本块抛
`UnderstandingParseError`）对读该件（规格风险 4 检测手段；`specs/parsing.md` 接口⑤）。

**2026-10-16 补（流水 67·L3 阻塞修复批）——本件新增行 17–20**（规格「验收测试」表同批补录）：schema
拒回喂重试恰一次（行为 13）。四行判据面＝`::schema_reject_feedback_retry_once`（首拒→回喂→次读合规
则正常走通，零 `failed`）／`::schema_reject_twice_raises_with_feedback_trace`（两读皆拒照抛＋拒因
留痕，上限恰一次）／`::schema_feedback_three_segment_payload`（载荷三段带路形逐支）／
`::schema_feedback_prefix_extension`（回喂＝追加形、前缀延伸逐字不破）。端到端两面在
`tests/domains/test_v2_four_phase.py`（`::test_four_phase_understand_schema_feedback_retry_recovers`／
`::test_four_phase_understand_schema_feedback_twice_fails`——`specs/agent-loop.md` 验收表同批挂）。
**行 12 的步序面随本批改判**：解析失败案＝记账步 2（两读）＋报告步 1（回喂不另记步、不重复上报）。

**2026-10-17 补（EB5a·schema 零交付三题定位修复）——本件新增行 5c**：EB3 全量复跑里 NQ-C3／NQ-D3／
NQ-M1 三题**整题零交付**，定位＝理解步严格解析两次皆拒、同一形（**题干引号被照搬进 `text` 值且不
转义**）；旧形「回喂恰一次 → 收敛拒答」只给拒答正文（判分记 ❌）。修法＝**引号自修受理**（行为 13
首段）：严格解析不合格 → 过确定性引号自修一次（既有共用件 `parsing.parse_with_quote_repair`，零模型
零占轮，修好＝受理 ＋ `emission_quote_repair` notice）→ 修不好才回喂 → 仍拒才收敛拒答。本件行 5c
＝三题**题面原句＋真机应答原话**重演（失败形 → 受理 → 真交付）；行 5b（NQ-D2 帧回归）随本批由
「收敛拒答」改判「引号自修受理」——同一真机形在新行为下**不再是拒答**。

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
from appv2.runtimev2.parsing import Direct, Understanding, parse_understanding, repair_inner_quotes
from appv2.runtimev2.prompts import (
    RECOMMENDATION_TEMPLATE,
    SYSTEM_BACKGROUND,
    TASK_BOOK_EXAMPLES,
    TASK_BOOK_OUTPUT_CONTRACT,
    TASK_BOOK_REDLINE,
    TASK_BOOK_SCENE,
    TASK_BOOK_TASK,
    understand_system_contract,
)
from appv2.runtimev2.state import RunState
from appv2.runtimev2.transport import EVENT_KINDS, NOTICE_TYPES, EventBus, SseEvent
from appv2.runtimev2.understanding import interpret
from appv2.runtimev2.understanding.closure import direct_assertion_hits, numeric_form_hit
from appv2.runtimev2.understanding.constants import (
    CONVERGE_DRAFT_TEMPLATE,
    CONVERGE_NOTE_TITLE,
)
from appv2.runtimev2.understanding.errors import excerpt

_REPO_ROOT = Path(__file__).resolve().parents[2]
_UNDERSTANDING_DIR = _REPO_ROOT / "appv2" / "runtimev2" / "understanding"

# 收敛拒答正文的稳定头部（模板首段——文案本体真源＝`understanding.constants`；本件只判「是拒答」）
_REFUSAL_MARK = CONVERGE_DRAFT_TEMPLATE.split("{", 1)[0]
_CONVERGE_NOTE_TITLE = CONVERGE_NOTE_TITLE
# 引号自修受理面（行为 13 首段；2026-10-17 EB5a）——notice 取值与注记标题的规格逐字面
_QUOTE_REPAIR_NOTICE = "emission_quote_repair"
_QUOTE_REPAIR_NOTE_TITLE = "读题引号自修"

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
# 数据区来源标记（标来源面——真源 specs/understanding.md 行为 2；字面同 prompts 渲染单点；
# 2026-10-17 V2-82 换一行功能段头——原「【环境】」表头＋「【本系统】」四句介绍随删）
_DATA_ZONE_HEAD = (
    "【环境数据】（以下由系统按当前数据现状动态装配——业务相关性只看领域是否沾边；"
    "数据止于下方水位日）"
)
# 题干段头（prompts 行为 3「题干段置末」的行首标记；字面同 prompts 渲染单点）
_QUESTION_HEAD = "【待解构的题干】"
# 机读上报字段名（本块自立的机读面——行 12「step payload 字段」的字段名即此；改名即红）
_PAYLOAD_PHASE_KEY = "phase"
_PAYLOAD_EVENT_KEY = "event"
_PAYLOAD_CANDIDATES_KEY = "metric_candidates"
_PAYLOAD_OFFENDERS_KEY = "offenders"
_PAYLOAD_RAW_EXCERPT_KEY = "raw_excerpt"
_EVENT_CANDIDATE_VIOLATION = "candidate_out_of_roster"
_EVENT_PARSE_FAILURE = "parse_failure"
# 过程档案条目（本块三标题：装配一次标记 ＋ 模型原话留痕 ＋ -B 直答退回注记）
_TASK_BOOK_NOTE_TITLE = "任务书装配"
_READ_NOTE_TITLE = "读题"
_DIRECT_REJECT_NOTE_TITLE = "直答退回"
# -B 直答结构核验面（行为 5／11；机读上报的字段名与命中的两轴 kind 闭世界）
_EVENT_DIRECT_REJECTED = "direct_rejected"
_PAYLOAD_DIRECT_TEXT_KEY = "direct_text"
_PAYLOAD_CLOSURE_HITS_KEY = "closure_hits"
_PAYLOAD_HIT_KIND_KEY = "kind"
_PAYLOAD_HIT_TOKEN_KEY = "token"
_KIND_NUMERIC = "numeric_form"
# fail-closed 判断原则的在场片段（逐字取自 prompts 单点合同文本——本件只断言「原则在场」，
# 不对整段措辞下断言；prompts 侧改述即红＝登记交主窗）
_FAIL_CLOSED_CLAUSE = "只要可能有关"
_HESITANT_CLAUSE = "哪怕你拿不准"
_NARROW_EXIT_CLAUSE = "只有确定与业务毫无关系"
_QUESTION_SEGMENT_HEAD = "先判与业务的相关性"
# 2026-10-18 V2-87：题干段收束句随输出形统一改 JSON 两出口（V1「两行式／直答」措辞退役）
_GREETING_ONLY_CLAUSE = "确定无关的寒暄闲聊＝输出 route=\"direct\" 的 JSON"

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
# 结构卡集合 fixture（卡头合同形「表/账/库 名（…」——真源 `tools` 的 `table_schema` 发现面清单；
# 行 15 的判据基准。全名＋短名两形态均由卡头提取，同 `tools` 卡名口径）
_SCHEMA_CARDS: tuple[str, ...] = (
    "表 agg.fct_daily_metering（日产计量事实表·PK well_id+prod_date）：well_id（井号）、"
    "prod_date（日期）、oil_output（日产油量·吨）——问数计划（data_query）唯一取数事实表",
    "表 agg.dim_well（井维度·PK well_id）：well_id（井号）、block_name（区块）",
    "账 sem_metric（指标台账）：id/原名/slot_name/定义/粒度/单位/状态",
    "库 kb 片段清单（检索库·doc_retrieve 检索面）：报告级/片段级两级",
)

_QUESTION = "K12-3 井最近日产油量是多少？"
_WATERMARK = "2026-08-24"


def _ledger_dump(
    *,
    metrics: Sequence[Mapping[str, Any]] = _METRIC_ROWS,
    aliases: Mapping[str, str] = _ALIASES,
    cards: Sequence[str] = _SCHEMA_CARDS,
) -> dict[str, Any]:
    return {
        "metrics": [dict(row) for row in metrics],
        "aliases": dict(aliases),
        "terms": [{"value": "躺井", "term": "躺井", "banned": False}],
        "objects": [{"value": "井"}],
        "relations": [{"value": "属于"}],
        "families_map": {"月报": ["monthly"]},
        "cards": list(cards),
    }


def _state(**overrides: Any) -> RunState:
    """读题相位单测夹具——**按生产链形**注入链首背景块（2026-10-17 H 批）。

    生产链首由编排建链时落（`orchestration._initial_state`：背景块 system 条 → 题面 user 条 →
    本相位任务书）：本夹具同构注入，使相位单测的链形与真机一致（`_task_book_of` 的「链首＝背景块」
    判据面随之成立）；相位本体不产该条（挂点多在编排，本块零第二挂载点）。
    """
    values: dict[str, Any] = {
        "run_id": "run-ut-01",
        "question": _QUESTION,
        "actor": "laowang",
        "ledger_dump": _ledger_dump(),
        "messages": [{"role": "system", "content": SYSTEM_BACKGROUND}],
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
    outs, bus, _completer = _interpret_all_with_calls(state, *replies, watermark=watermark)
    return outs, bus


def _interpret_all_with_calls(
    state: RunState, *replies: str, runs: int | None = None, watermark: str = ""
) -> tuple[list[Any], EventBus, ScriptedCompleter]:
    """同 `_interpret_all`，另回**替身本体**（读 `completer.calls`＝逐次实发消息链——前缀延伸判据
    面）。

    `runs`＝`interpret` 的调用次数（缺省＝`len(replies)`，同 `_interpret_all` 重入形）；传 `1` 配
    多条剧本＝**单次进入的多轮调用**（schema 拒回喂重试恰此形：一次 `interpret` 内两读）。
    """
    completer = ScriptedCompleter({_SPEC_CALLER: list(replies)})
    previous = set_completer(completer)
    bus = EventBus()
    total = len(replies) if runs is None else runs
    try:
        outs = [interpret(state, bus=bus, watermark=watermark) for _ in range(total)]
    finally:
        set_completer(previous)
    return outs, bus, completer


def _interpret(state: RunState, reply: str, *, watermark: str = "") -> tuple[Any, EventBus]:
    outs, bus = _interpret_all(state, reply, watermark=watermark)
    return outs[0], bus


def _interpret_with_calls(
    state: RunState, *replies: str, watermark: str = ""
) -> ScriptedCompleter:
    """跑读题并回**替身本体**（读 `completer.calls`＝逐次实发请求面——规章段观测面）。"""
    _outs, _bus, completer = _interpret_all_with_calls(state, *replies, watermark=watermark)
    return completer


def _system_contract_of(completer: ScriptedCompleter, index: int) -> str:
    """第 `index` 次调用的**规章段**（请求首条 system 条的内容——2026-10-17 H 批承载位判据）。"""
    _caller, messages = completer.calls[index]
    assert messages and messages[0]["role"] == "system", messages[:1]
    return str(messages[0]["content"])


async def _frames(bus: EventBus) -> list[SseEvent]:
    """读尽一条已收束总线的帧（先 `close`——未收束会等待新帧）。"""
    bus.close()
    return [frame async for frame in bus.stream(0)]


def _task_book_of(state: RunState) -> str:
    """链首任务书**动态段**（本块装配的接入形：链首背景块之后的首条 user 消息）。

    2026-10-17 H 批：链首＝**背景块 system 条**（每链恰一条），任务书动态段紧随其后。
    """
    assert state.messages, "链上空——任务书未装配"
    assert state.messages[0]["role"] == "system", state.messages[0]
    first = state.messages[1]
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


def _reject_notes(state: RunState) -> list[dict[str, Any]]:
    """过程档案里的「直答退回」注记（-B 退回口径的留痕面；同标题多条＝重复计入即红）。"""
    return [
        entry for entry in state.process_notes if entry.get("title") == _DIRECT_REJECT_NOTE_TITLE
    ]


def _closure_hits_of(state: RunState) -> list[Any]:
    """直答退回报告步的逐条命中项（恰一条报告步；缺席即红——退回面不许静默）。"""
    reports = _report_steps(state)
    assert len(reports) == 1, reports
    hits = reports[0]["payload"][_PAYLOAD_CLOSURE_HITS_KEY]
    assert isinstance(hits, list)
    return hits


def _assert_rejected_direct(state: RunState, text: str) -> None:
    """退回面的公共断言（行 4／15 共用——不直答收口、注记恰一条、上报两件套齐、dialogue 零写）。"""
    assert len(state.notices) == 1
    notice = state.notices[0]
    assert set(notice) == _SPEC_NOTICE_KEYS and notice["type"] in NOTICE_TYPES
    report = _report_steps(state)[0]
    payload = report["payload"]
    assert payload[_PAYLOAD_PHASE_KEY] == _SPEC_CALLER
    assert payload[_PAYLOAD_EVENT_KEY] == _EVENT_DIRECT_REJECTED
    assert payload[_PAYLOAD_DIRECT_TEXT_KEY] == text  # 被判不合格的直答文本如实留痕
    assert report["status"] == "failed"  # 如实态（不恒 ok）
    assert _reject_notes(state) and len(_reject_notes(state)) == 1
    assert set(_reject_notes(state)[0]) == _SPEC_PROCESS_NOTE_KEYS
    hits = _closure_hits_of(state)
    assert hits  # 命中项非空（判不合格必有判据点名——退回不许静默）
    for hit in hits:
        assert set(hit) == {_PAYLOAD_HIT_KIND_KEY, _PAYLOAD_HIT_TOKEN_KEY}
        assert hit[_PAYLOAD_HIT_TOKEN_KEY] in text  # 命中 token 逐字出自被判文本
    names = "、".join(
        f"{hit[_PAYLOAD_HIT_KIND_KEY]}:{hit[_PAYLOAD_HIT_TOKEN_KEY]}" for hit in hits
    )
    assert names in notice["content"]  # 与 notice 同一次判定产物（不各自生成）
    assert state.dialogue == []  # pin-26 渲染面：退回注记入过程档案、对话层零写入


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


# ---------- 3 寒暄句 → route=direct，文本不含数据或事实断言 ----------


_GREETING_LINES: tuple[str, ...] = (
    "谢谢你，辛苦了。",
    "好的，再见——有需要再叫我。",
    "早上好，麻烦你了。",
)


async def test_direct_on_greeting() -> None:
    """#3｜寒暄句（道谢／道别）→ route=direct，文本不含数据或事实断言——行为 5／11 的窄口。

    「文本不含数据或事实断言」＝**结构面机读复核**（数值形零命中——形态判定，不判语义）；
    窄口内直答仍免核验：收口三键落位、理解字段与事件面零写（单出口互斥）、
    零退回面（无「直答退回」注记、无注记、无报告步）。
    """
    for text in _GREETING_LINES:
        state = _state()
        out, bus = _interpret(state, _direct_reply(text))

        assert isinstance(out, Direct) and out.route == _SPEC_ROUTE_DIRECT
        assert out.text == text
        assert direct_assertion_hits(state, text) == ()  # 数值形零命中
        assert numeric_form_hit(text) == ""  # 数值形面同判（含小数／百分号／千分位样态）
        assert state.draft == text and state.draft_kind == _SPEC_DRAFT_KIND_DIRECT
        assert state.next_intent == _SPEC_INTENT_ANSWER
        assert state.understanding == "" and state.metric_candidates == []
        assert _reject_notes(state) == [] and state.notices == [] and _report_steps(state) == []
        assert [entry["title"] for entry in state.process_notes] == [
            _TASK_BOOK_NOTE_TITLE,
            _READ_NOTE_TITLE,
        ]
        assert state.dialogue == []
        assert await _frames(bus) == []  # 直答零旁白（无理解文本事件）


# ---------- 4 route=direct 但文本含数值形 → 不合格，退回 full ----------


_REJECTED_DIRECT_CASES: tuple[tuple[str, str], ...] = (
    ("K12-3 井上月的日产油量是 128 吨。", _KIND_NUMERIC),  # 数值形（≥1 位连续阿拉伯数字形）
    ("本月抽油机时率 95.5%。", _KIND_NUMERIC),  # 小数＋百分号（数值形组成）
    ("全年产量 1,000 吨。", _KIND_NUMERIC),  # 千分位（数值形组成）
)


async def test_direct_with_assertion_rejected() -> None:
    """#4｜route=direct 但文本含数值形 → 不合格，退回 full——行为 5 ＋接口「直答退回不抛错」。

    **2026-10-18 V2-83 判据收窄**：只认数值形（数据断言）；指标名/表名单独出现不再退回
    （问候/能力介绍保留集见 `::direct_boundary_cases_rejected`）。
    退回口径**唯一**：`route="full"` 的 `Understanding`（不抛错、不静默、不直答收口）＋过程档案
    一条「直答退回」注记（钉 `pin-26` 渲染面：入档案、`dialogue` 零写入）＋如实上报两件套；退回后
    走 `full` 分派——理解文本双出口（状态字段 ＋ `text` 事件）随同一承接面出场。
    """
    for text, kind in _REJECTED_DIRECT_CASES:
        state = _state()
        out, bus = _interpret(state, _direct_reply(text))

        # 退回形＝Understanding（不抛错、不返回半成品；候选不发明——直答应答本无候选）
        assert isinstance(out, Understanding) and out.route == _SPEC_ROUTE_FULL
        assert out.text == text and out.metric_candidates == []
        # 不直答收口：收口三键零写
        assert state.draft == "" and state.draft_kind == "" and state.next_intent == ""
        # 过程档案注记 ＋ 如实上报两件套 ＋ dialogue 零写
        _assert_rejected_direct(state, text)
        assert kind in [hit[_PAYLOAD_HIT_KIND_KEY] for hit in _closure_hits_of(state)]
        assert _closure_hits_of(state) == [
            {_PAYLOAD_HIT_KIND_KEY: hit_kind, _PAYLOAD_HIT_TOKEN_KEY: token}
            for hit_kind, token in direct_assertion_hits(state, text)
        ]
        # 退回面走 full 分派：理解文本双出口（状态字段与事件同源）
        assert state.understanding == text
        frames = await _frames(bus)
        assert [frame.event for frame in frames] == [_SPEC_TEXT_EVENT]
        assert frames[0].data == {"content": text, "kind": _SPEC_TEXT_EVENT_KIND}
        assert len(state.steps) == 2  # 记账步 1 ＋ 报告步 1（不为同一调用重复记账）


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


def test_malformed_json_converges_to_refusal() -> None:
    """#5｜应答 JSON 不合 schema → 回喂重试恰一次后**收敛拒答**——行为 7／13 尾。

    **2026-10-17 EB3 D4.4 改判**：真机证据 `eval/results/frames/EB2-NQ-D2.json`（模型两次都在 JSON
    字符串里带未转义引号 → 旧「抛 `UnderstandingParseError` → 编排收 `failed`」整 run 零交付）
    ——两读皆拒改为 `bookkeeping.direct_answer` 落拒答正文（直答旁路三键）＋返回该 `Direct`：
    **不判 `failed`、不零交付**；仍**不返回半成品**（理解双通道字段零写入）、**不取默认路由**、
    不静默（如实上报两件套照出一份）。**2026-10-17 EB5a 补**：拒前先过**确定性引号自修**一次——
    本件这组输入**都不是引号病**（两行式／非 JSON／类型不符／route 越界），自修零命中，
    故仍走「回喂恰一次 → 收敛拒答」；引号病形的改判见下 5b／5c 两节。

    **跨文件对读**（转译输入半面）：同一组合格外输入在 `parse_understanding` 侧返 `None`。
    """
    for raw in _MALFORMED_REPLIES:
        state = _state()
        out, _bus = _interpret(state, raw)
        # 收敛拒答形（非抛错）：拒答正文经直答旁路三键落定，与返回值同源
        assert isinstance(out, Direct) and out.route == _SPEC_ROUTE_DIRECT
        assert state.draft == out.text and state.draft_kind == "direct"
        assert state.next_intent == "answer"
        assert _REFUSAL_MARK in out.text
        # 唯一转译出口的输入半面：同一输入 parsing 侧返 None（不降级、不返回半成品）
        assert parse_understanding(raw) is None
        # 不返回半成品／不取默认路由：理解双通道字段零写入
        assert state.understanding == "" and state.metric_candidates == []
        # 如实上报（不许静默）：notice ＋ 报告步 payload 字段
        assert len(state.notices) == 1
        assert set(state.notices[0]) == _SPEC_NOTICE_KEYS
        assert state.notices[0]["type"] in NOTICE_TYPES
        reports = _report_steps(state)
        assert len(reports) == 1
        assert reports[0]["payload"][_PAYLOAD_EVENT_KEY] == _EVENT_PARSE_FAILURE
        assert reports[0]["payload"][_PAYLOAD_RAW_EXCERPT_KEY] == excerpt(raw)
        assert reports[0]["status"] == "failed"
        # 收敛留痕（过程档案一条；pin-26 渲染面：入档案、不入 dialogue）
        assert [entry["title"] for entry in state.process_notes].count(_CONVERGE_NOTE_TITLE) == 1
        assert state.dialogue == []

    # 超长应答：片段截断**可见**（截断标记在场，不静默硬切）
    state = _state()
    long_raw = "不是 JSON" + "。" * 500
    out, _bus = _interpret(state, long_raw)
    assert isinstance(out, Direct)
    assert _report_steps(state)[0]["payload"][_PAYLOAD_RAW_EXCERPT_KEY].endswith("…")


# ---------- 5b EB2-NQ-D2 帧回归（题面原句＋真机应答原话）----------
# 题面原句（逐字取自 `eval/results/frames/EB2-NQ-D2.json` 的 blackbox 记录）
_NQ_D2_QUESTION = (
    '报告 1.2 节对一季度产量完成情况"两种口径并行披露"。请完整回答：(a) 一季度计划配产多少万吨？'
    '(b) 两支口径各自的名称、实际完成（万吨）与完成率分别是多少？按哪支口径判定"未完成计划"？'
    '(c) 两支口径相差几个百分点、报告如何定性这个差异（是不是产量虚增）？差异对应的检修影响量'
    '是多少？(d) 台账提示里「有效产量」这个指标对数前必须先做什么？'
    '旧称「老完成率」现在处于什么状态？'
)
# 真机应答原话（`logs/llm_calls/20261017.jsonl` run-679ec537 首读——**JSON 字符串内未转义引号**：
# `按哪支口径判定"未完成计划"`；首读回喂后同形，旧形 4.8s 内整 run `failed`、`answer_text` 空）
_NQ_D2_RAW = (
    '{"route":"full","text":"理解：报表 1.2 节一季度产量完成情况按两种口径并行披露，要求完整回答：'
    '(a) 一季度计划配产量（万吨）；(b) 两支口径各自的名称、实际完成量（万吨）、完成率，并指出按哪支'
    '口径判定"未完成计划"；(c) 两支口径相差几个百分点、报告如何定性该差异（是否构成产量虚增）、'
    '差异对应的检修影响量；(d) 台账提示里"有效产量"指标对数前必须先做的事，以及旧称"老完成率"'
    '当前所处状态。","metric_candidates":["配产量","有效产量","产量完成率"]}'
)
# 引号自修后的 `text` 值（真机原话**逐字不动**、只把值内裸引号换成中文引号——本件判据面；
# 由 `parsing.repair_inner_quotes` 的确定性规则算出，非人工誊写）
_NQ_D2_RAW_TEXT_REPAIRED = (
    "理解：报表 1.2 节一季度产量完成情况按两种口径并行披露，要求完整回答：(a) 一季度计划配产量"
    "（万吨）；(b) 两支口径各自的名称、实际完成量（万吨）、完成率，并指出按哪支口径判定"
    "「未完成计划」；(c) 两支口径相差几个百分点、报告如何定性该差异（是否构成产量虚增）、"
    "差异对应的检修影响量；(d) 台账提示里「有效产量」指标对数前必须先做的事，以及旧称"
    "「老完成率」当前所处状态。"
)


def test_nq_d2_frame_question_quote_repair_admits() -> None:
    """#5b｜EB2-NQ-D2 帧回归：题面原句＋真机应答原话 → **引号自修受理**（真交付，非拒答）。

    该帧的失败形＝**JSON 字符串内未转义引号**（`按哪支口径判定"未完成计划"`）——严格解析不合格；
    旧形整 run `failed` 且 `answer_text` 空（判分记「run 级零交付 ❌」）；EB3 D4.4 改判「收敛拒答」
    （仍是零交付），**EB5a 起改判为受理**：确定性引号自修（`parsing.parse_with_quote_repair`，零模型
    零占轮）→ 全文可解析 → 正常分派 `route="full"` → run 续跑四相位**真作答**。

    判据：返回 `Understanding`（不是拒答 `Direct`）／值内裸引号换中文引号、**文本其余逐字不动**／
    `emission_quote_repair` notice ＋「读题引号自修」注记在场／模型调用**恰 1 次**（不占回喂上限、
    不触发第二次读）／零报告步（不成拒）／理解双通道照常写入。
    """
    state = _state(question=_NQ_D2_QUESTION)
    outs, _bus, completer = _interpret_all_with_calls(state, _NQ_D2_RAW, runs=1)
    out = outs[0]
    assert isinstance(out, Understanding) and out.route == _SPEC_ROUTE_FULL
    assert out.text == _NQ_D2_RAW_TEXT_REPAIRED
    assert out.metric_candidates == ["配产量", "有效产量", "产量完成率"]
    assert parse_understanding(_NQ_D2_RAW) is None  # 严格面同判（真机形确为不合 schema）
    assert len(completer.calls) == 1  # 自修不占回喂上限：绝不触发第二次读
    assert set(state.notices[0]) == _SPEC_NOTICE_KEYS
    assert state.notices[0]["type"] == _QUOTE_REPAIR_NOTICE
    titles = [entry["title"] for entry in state.process_notes]
    assert titles.count(_QUOTE_REPAIR_NOTE_TITLE) == 1 and titles.count(_READ_NOTE_TITLE) == 1
    parse_failures = [
        step
        for step in _report_steps(state)
        if step["payload"].get(_PAYLOAD_EVENT_KEY) == _EVENT_PARSE_FAILURE
    ]
    assert parse_failures == []  # 受理非拒：零解析失败报告步
    assert state.understanding == out.text and state.metric_candidates == out.metric_candidates
    assert state.dialogue == []


# ---------- 5c EB5a 三题帧回归（题面原句＋真机应答原话；2026-10-17 EB5a）----------
# 三题＝EB3 全量复跑里「整题零交付」那三题（`eval/results/frames/EB3-NQ-C3.json` ／
# `EB3-NQ-D3.json`／`EB3-NQ-M1.json`；真机 run_id 依次 run-7fec93ff／run-e15407fa／run-74dd2bb0）。
# 三题同形：**题面里的成对引号被照搬进 `text` 值且不转义**（C3 更甚——题面用全角「」、模型回话
# 却把它归一成半角 `"` 再照抄；D3／M1 题面本来就是半角引号）。两次读题同形 → 严格解析两次皆拒。
# 题面原句逐字取自各帧 blackbox 记录；应答原话逐字取自 `logs/llm_calls/20261017.jsonl`（首读形）。
_NQ_C3_QUESTION = (
    "某评审人声称：「报告 4.2 节记载本井采用 20/40 目砾石挤压充填防砂，防砂精度 175 微米，"
    "充填作业占船日 4.0 天。请按附录A 给出本井实际充填砾石量与充填井段。」请逐项指出该说法与报告"
    "不符之处，并作答：\n（1）本井实际防砂方式与筛管型号、防砂精度各是什么？\n"
    "（2）「20/40 目砾石挤压充填」在报告中的真实身份是什么？报告是否给出砾石量与充填井段？\n"
    "（3）「占船日 4.0 天」在 4.2 节语境下的含义是什么？报告中另有两处「4.0 天」分别指什么"
    "（指出章节与口径）？"
)
_NQ_C3_RAW = (
    '{"route": "full", "text": "理解：判断评审人关于报告4.2节防砂说法与报告的逐项不符之处，并作答'
    '（1）本井实际防砂方式与筛管型号、防砂精度；（2）"20/40目砾石挤压充填"在报告中的真实身份及'
    '报告是否给出实施后的砾石量与充填井段；（3）"占船日4.0天"在4.2节语境下的含义及报告中另两处'
    '"4.0天"分别指什么（指出章节与口径）。", "metric_candidates": []}'
)
_NQ_D3_QUESTION = (
    '有人推断："Y-26 井 3 月 6 日分层测试三段吸水比例为 51%/34%/15%，各段相对均匀，可见 Y-26 的'
    '欠注属于层间矛盾型；所以二季度治理应当像 Y-24 一样，先在 4 月上旬实施冻胶调剖封堵 I 层大孔道，'
    '验证通过后再提配注。"这个推断对不对？请依据报告逐点纠正：Y-26 的欠注类型判定是什么、判定证据'
    '有哪两条（提示：一条在第三章、一条在 2.2 表）、二季度对 Y-26 的实际治理措施和提配安排是什么？'
    '"冻胶调剖封堵 I 层大孔道"到底是给哪口井安排的？'
)
_NQ_D3_RAW = (
    '{"route":"full","text":"判断并纠正关于 Y-26 井欠注类型与二季度治理措施的推断，要求：①给出 '
    'Y-26 的欠注类型判定；②给出判定证据两条（第三章一条，2.2 表一条）；③给出二季度对 Y-26 的实际'
    '治理措施和提配安排；④说明"冻胶调剖封堵 I 层大孔道"实际安排在哪口井。","metric_candidates":[]}'
)
_NQ_M1_QUESTION = (
    "结合第一章、第二章、第七章回答五个子问：①本报告口径下 2027 年 1 月躺井 3 井次是哪三口井？"
    '②其中属于杆断的是哪两口、这两口的平均检泵周期是多少天？③三口中属于"泵漏"的是哪口井、'
    '其检泵周期是多少天？④第七章 2027-01 行"其中杆断"一栏填的是几？'
    '⑤该行的"检泵作业(井次)"一栏填的是几？'
)
_NQ_M1_RAW = (
    '{"route":"full","text":"结合第一章、第二章、第七章回答五个子问：①本报告口径下 2027 年 1 月躺井'
    ' 3 井次分别对应哪三口井；②其中属于杆断的是哪两口、这两口的平均检泵周期是多少天；③三口中属于'
    '"泵漏"的是哪口井、其检泵周期是多少天；④第七章 2027-01 行"其中杆断"一栏填的是几；'
    '⑤该行的"检泵作业(井次)"一栏填的是几。","metric_candidates":["检泵周期"]}'
)
_EB5A_CASES: tuple[tuple[str, str, str, str], ...] = (
    (
        "NQ-C3",
        _NQ_C3_QUESTION,
        _NQ_C3_RAW,
        "理解：判断评审人关于报告4.2节防砂说法与报告的逐项不符之处，并作答（1）本井实际防砂方式与"
        "筛管型号、防砂精度；（2）「20/40目砾石挤压充填」在报告中的真实身份及报告是否给出实施后的"
        "砾石量与充填井段；（3）「占船日4.0天」在4.2节语境下的含义及报告中另两处「4.0天」分别指"
        "什么（指出章节与口径）。",
    ),
    (
        "NQ-D3",
        _NQ_D3_QUESTION,
        _NQ_D3_RAW,
        "判断并纠正关于 Y-26 井欠注类型与二季度治理措施的推断，要求：①给出 Y-26 的欠注类型判定；"
        "②给出判定证据两条（第三章一条，2.2 表一条）；③给出二季度对 Y-26 的实际治理措施和提配"
        "安排；④说明「冻胶调剖封堵 I 层大孔道」实际安排在哪口井。",
    ),
    (
        "NQ-M1",
        _NQ_M1_QUESTION,
        _NQ_M1_RAW,
        "结合第一章、第二章、第七章回答五个子问：①本报告口径下 2027 年 1 月躺井 3 井次分别对应哪"
        "三口井；②其中属于杆断的是哪两口、这两口的平均检泵周期是多少天；③三口中属于「泵漏」的是"
        "哪口井、其检泵周期是多少天；④第七章 2027-01 行「其中杆断」一栏填的是几；"
        "⑤该行的「检泵作业(井次)」一栏填的是几。",
    ),
)


@pytest.mark.parametrize(("qid", "question", "raw", "text_repaired"), _EB5A_CASES)
def test_eb5a_zero_delivery_three_questions_quote_repair_admits(
    qid: str, question: str, raw: str, text_repaired: str
) -> None:
    """#5c｜EB5a 三题帧回归：失败形重演 → **引号自修受理**（`completed` 有正文，不再整题零交付）。

    三题（`qid`）在 EB3 全量复跑里死在**同一处把守**：理解步严格解析两次皆拒（同一形：题干引号被
    照搬进 `text` 值不转义）→ 旧形走「回喂恰一次 → 收敛拒答」→ 用户只拿到「没能读懂」的拒答正文，
    判分记「整题零交付 ❌」。EB5a 起：**首读即过确定性引号自修受理**（零模型零占轮）→ 返回
    `route="full"` 的 `Understanding` → 编排续跑四相位真作答。

    判据（逐题）：返回 `Understanding` 非拒答／`text` 值内引号换中文引号、其余逐字同真机原话
    （期望文本另以逐字稿落 `_EB5A_CASES` 第 4 项）／候选原样保留／模型调用**恰 1 次**（自修不占
    回喂上限）／`emission_quote_repair` notice ＋「读题引号自修」注记在场／零解析失败报告步
    （不成拒）／未走直答旁路。
    """
    state = _state(question=question)
    outs, _bus, completer = _interpret_all_with_calls(state, raw, runs=1)
    out = outs[0]
    assert parse_understanding(raw) is None, qid  # 真机形确为不合 schema（严格面同判）
    assert isinstance(out, Understanding) and out.route == _SPEC_ROUTE_FULL, qid
    assert len(completer.calls) == 1, qid  # 引号自修不占回喂上限
    assert out.text == text_repaired, qid
    assert state.notices[0]["type"] == _QUOTE_REPAIR_NOTICE, qid
    assert [entry["title"] for entry in state.process_notes].count(
        _QUOTE_REPAIR_NOTE_TITLE
    ) == 1, qid
    parse_failures = [
        step
        for step in _report_steps(state)
        if step["payload"].get(_PAYLOAD_EVENT_KEY) == _EVENT_PARSE_FAILURE
    ]
    assert parse_failures == [], qid
    assert state.next_intent != _SPEC_INTENT_ANSWER, qid
    assert state.understanding == out.text, qid
    assert state.draft == "" and state.draft_kind == "", qid  # 未走直答旁路（真交付路径）
    assert state.dialogue == [], qid
    # 修复只动引号层：去引号后与真机原话的 `text` 值同形（值内容零改写、零截断）
    raw_text = _raw_text_field(raw)
    repaired_text = text_repaired
    for mark in ('"', "「", "」"):
        raw_text = raw_text.replace(mark, "")
        repaired_text = repaired_text.replace(mark, "")
    assert repaired_text == raw_text, qid


def _raw_text_field(raw: str) -> str:
    """真机应答原文里 `text` 值的**逐字切面**（未转义引号形的纯字符切片——本件比对基准）。"""
    open_quote = raw.index(":", raw.index('"text"')) + 1
    start = raw.index('"', open_quote) + 1
    return raw[start : raw.rindex(",", 0, raw.index('"metric_candidates"')) - 1]


# ---------- 5d NQ-M3 帧回归（围栏包裹形；2026-10-17 F2）----------
# 题面原句（逐字取自 `eval/results/frames/EB4-NQ-M3.json` blackbox；真机 run＝`run-e318723a`）
_NQ_M3_QUESTION = (
    '"本油田本月电潜泵生产井的躺井井次和检泵作业井次分别是多少？请从第一章和第二章分别给出。"'
    "若报告中不存在该口径，请引用报告明示的句子说明前提为什么不成立，并说明本月的躺井井次、"
    "检泵作业井次实际发生在什么井型上。"
)
# 真机应答原话（`logs/llm_calls/20261017.jsonl` run-e318723a 的两条 understand 记录**逐字同形**——
# 整答被 markdown 围栏包裹：围栏内的 JSON 本体合法且完整，不合 schema 只因**包围层**）
_NQ_M3_RAW = (
    "```json\n"
    '{"route": "full", "text": "理解：问本油田本月电潜泵生产井的躺井井次和检泵作业井次各是多少，'
    "要求从第一章和第二章分别给出；若报告中不存在该口径，则引用报告明示句子说明前提不成立，"
    '并说明本月躺井井次与检泵作业井次实际发生在什么井型上。", "metric_candidates": []}\n'
    "```"
)


def test_f2_nq_m3_frame_fenced_reply_converges_with_text() -> None:
    """#5d｜NQ-M3 帧回归：**围栏包裹形**不在引号自修族覆盖内 → 收敛拒答**有正文**（非零交付）。

    该帧（`EB4-NQ-M3.json`；EB4 终判「新病灶 3：零交付未根除」）的畸形＝**markdown 围栏包裹**
    （` ```json … ``` `）——围栏内 JSON 本体合法、不合 schema 只因包围层；**非引号形**，故 EB5a 的
    引号自修受理不覆盖（下判据 ②）。两次读题同形 → 回喂恰一次仍拒 → 收敛拒答。

    判据：①严格面返 `None`；②**该形只能收敛不能自修**（`repair_inner_quotes` 无病不修 → `None`——
    引号族零覆盖的机器证据）；③收敛拒答落直答旁路三键（`draft`／`draft_kind="direct"`／
    `next_intent="answer"`）——run 收口 `completed`、**不判 `failed`、不零交付**；④拒答正文＝程序
    确定性文案（统一收敛句「没能完全读懂这道题，请补充说明」＋材料面如实——本相位结构上零材料），
    **不刷原始应答片段**；⑤模型调用恰 2 次（回喂恰一次，绝无第三次）；⑥原文只进机读面（报告步
    payload ＋ notice）。
    """
    state = _state(question=_NQ_M3_QUESTION)
    outs, _bus, completer = _interpret_all_with_calls(state, _NQ_M3_RAW, runs=1)
    out = outs[0]
    # ① 严格面同判（真机形确为不合 schema）
    assert parse_understanding(_NQ_M3_RAW) is None
    # ② 判定依据的机器证据：围栏形在手＝非引号病形（自修族无病不修）
    assert repair_inner_quotes(_NQ_M3_RAW) is None
    # ③ 收敛拒答：返回拒答 `Direct`＋直答旁路三键（非抛错、非零交付）
    assert isinstance(out, Direct)
    assert _REFUSAL_MARK in out.text
    assert state.draft == out.text and state.draft_kind == _SPEC_DRAFT_KIND_DIRECT
    assert state.next_intent == _SPEC_INTENT_ANSWER
    # ④ 正文＝确定性文案（统一收敛句＋材料面如实），原始应答片段不刷进正文
    assert "没能完全读懂这道题，请补充说明" in out.text
    assert "已获材料：无" in out.text
    assert "```json" not in out.text and "metric_candidates" not in out.text
    assert state.process_notes[-1]["title"] == _CONVERGE_NOTE_TITLE
    # ⑤ 上限恰一次：两次调用（首读＋回喂一次），绝无第三次
    assert len(completer.calls) == 2
    assert len(state.steps) == 3  # 记账步 2 ＋ 报告步 1
    # ⑥ 原文只进机读面（报告步 payload 携片段＋如实上报 notice 一份）
    assert len(_report_steps(state)) == 1
    assert len(state.notices) == 1 and set(state.notices[0]) == _SPEC_NOTICE_KEYS
    assert state.understanding == "" and state.metric_candidates == []
    assert state.dialogue == []


# ---------- 6 route 越界取值 → 判失败（不猜、不取默认） ----------


def test_route_enum_closed_world() -> None:
    """#6｜route 越界取值 → 判失败（不猜、不取默认）——接口定义「`route` 是闭世界」。

    闭世界仅 `full`｜`direct`；越界（含大小写变形／缺键／`null`／空表）一律**不合 schema** →
    回喂重试恰一次仍不合 → **收敛拒答**（2026-10-17 EB3 D4.4：不再抛错、不再零交付），
    **无默认路由**：理解双通道字段均零写入（程序不替模型选 `full`／`direct`）。
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
        out, _bus = _interpret(state, raw)
        assert isinstance(out, Direct) and state.draft_kind == "direct"
        assert _REFUSAL_MARK in out.text
        assert state.understanding == "" and state.metric_candidates == []
        assert state.next_intent == "answer"  # 收口旁路——非「默认路由到某相位」
        assert parse_understanding(raw) is None  # 与 parsing 面同判（无默认通道）

    # 两形互斥的合法面：同一次调用只回一支（行 6 的对照面——合法值恒落对）
    state = _state()
    out, _bus = _interpret(state, _direct_reply("不客气。"))
    assert isinstance(out, Direct) and out.route == _SPEC_ROUTE_DIRECT


# ---------- 7 任务书三区顺序正确、数据区标来源且置于末尾 ----------


def test_task_book_three_zones() -> None:
    """#7｜任务书两段序正确、数据区标来源且置于末——行为 1／2（Δ 口径见件头「已登记张力」）。

    **2026-10-17 H 批（角色分家）**：三区拆两段——**规章段**（指令区四常量→输出契约区）＝system
    承载位（准入＝调用请求首条 `{"role": "system"}` 的内容）；**动态段**（数据区→题干段）＝user 条
    入链。判据：规章段内两件相对序唯一；动态段带**来源标记**恰一份、活体台账词只在数据区、题干段
    为末段。
    """
    state = _state()
    completer = _interpret_with_calls(state, _full_reply("用户问日产油量。", ["日产油量"]))
    book = _task_book_of(state)
    contract = _system_contract_of(completer, 0)

    order = [
        TASK_BOOK_SCENE,
        TASK_BOOK_TASK,
        TASK_BOOK_EXAMPLES,
        TASK_BOOK_REDLINE,  # 指令区内四常量相对序：场景→任务→样例→红线
        TASK_BOOK_OUTPUT_CONTRACT,
    ]
    positions = [contract.index(marker) for marker in order]
    assert positions == sorted(positions) and len(set(positions)) == len(positions)

    # 数据区标来源（行为 2 的「标来源」面）：来源标记恰一份（在动态段）
    assert book.count(_DATA_ZONE_HEAD) == 1
    # 数据区置于（活体数据面的）末尾：活体台账词只在数据区、不在其后的固定短段
    data_zone_start = book.index(_DATA_ZONE_HEAD)
    metric_line = "日产油量、含水率"  # 指标名录行＝名字级顿号串（2026-10-17 V2-82 换形）
    assert book.index(metric_line) > data_zone_start
    assert book.index(metric_line) < book.index(_QUESTION_HEAD)
    assert book.rstrip().endswith("现在输出。）")  # 题干段为装配尾段（prompts 行为 3 段序）
    # 三区之外零活体数据段：装配体里只此一处来源标记；规章件不入动态段
    assert data_zone_start == 0
    for marker in order:
        assert marker not in book


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
    # 链首＝背景块 system 条恰一条（2026-10-17 H 批：每链恰一条、恒在链首）+ 任务书 + 两应答
    assert [m["role"] for m in state.messages] == [
        "system",
        "user",
        "assistant",
        "assistant",
    ]
    assert state.messages[0]["content"] == SYSTEM_BACKGROUND
    # 模型原话＝链上留痕（应答追加链尾——agent-loop 行为 2 追加式）
    assert [m["content"] for m in state.messages[2:]] == [first, second]

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
    实际出现＝名录**集合成员判定**，数字形判定归 -B）。扫描面＝本块源码全树（`rglob`，计数下界断言
    防空转）；探测非空转。

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

    两案：**候选违约**与**解析失败**——各两件套齐备（notice 恰三键且 `type` ∈ `NOTICE_TYPES`；
    报告步 payload 携如实字段、状态 `failed`），且**常规路径零补记步**（模型调用步由
    `bookkeeping.call_model` 单点记账——步序不翻倍）。第三类「直答退回」由 -B 的
    `::direct_with_assertion_rejected`／`::direct_boundary_cases_rejected` 承接（三件套同形：
    注记 ＋ notice ＋ 报告步——本件不重复计）。
    """
    # 案一：候选违约
    violation_state = _state()
    _interpret(violation_state, _full_reply("问日产油量与库存总量。", ["日产油量", _OUT_OF_ROSTER]))
    assert len(violation_state.steps) == 2  # 记账步 1 ＋ 报告步 1（不翻倍）
    assert len(_report_steps(violation_state)) == 1

    # 案二：解析失败（2026-10-16 补·流水 67：schema 拒先回喂重试恰一次——步序＝记账步 2＋报告步 1；
    # 2026-10-17 EB3 D4.4：两读皆拒＝收敛拒答——本件只判上报面，拒答口径在行 5／18）
    failure_state = _state()
    _interpret(failure_state, "两行式已退场：理解：x／指标候选：y")
    assert len(failure_state.steps) == 3
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


# ---------- 14 路由默认 fail-closed：拿不准／可能有关／灰区 → 完整流程 ----------


_FAIL_CLOSED_CASES: tuple[tuple[str, str], ...] = (
    # 灰区一：系统自身能力问句（真源 walk/05 §七 灰区归属——归完整流程）
    ("我能问什么？", "你可以问我井的日产油量、含水率这类台账指标，也能看 2026 年的月报结论。"),
    # 灰区二：预测类（同源）
    ("帮我预测明年油价。", "明年油价预计 70 美元/桶左右。"),
    # 拿不准／可能有关（V2-80a 判断原则的「哪怕一点关联」侧）
    ("老王家那口井咋样了？", "K12-3 井昨天的日产油量是 128 吨。"),
)


async def test_route_defaults_fail_closed() -> None:
    """#14｜路由默认 fail-closed：拿不准／可能有关 → 完整流程；灰区 → 完整流程——行为 11。

    行为 11 按真源（`walk/05` §七 第 3 条）是**给模型的判断原则、非程序规则**——本件两面落判据：

    ① **原则在场**：装配进任务书的指令区例外条款（可能有关／含糊／拿不准 → 完整流程；只有确定
       无关才直答）与题干段收束句——任务书是模型唯一决策输入，经相位黑盒观测（**2026-10-17 H 批：
       指令区在规章段＝调用请求首条 system 条**＋题干段在链上 user 条）；
    ② **fail-closed 一侧**：拿不准／可能有关／灰区句的直答认领，其应答必带数据／事实断言 → 直答
       结构核验命中 → 程序**确定性退回** `route="full"`（不直答收口）；同一问句模型判 `full` 时走
       完整流程（分派只由 `route` 决定——程序侧零词面判据，不设灰区词表：**行为 4**）。
    """
    # 案一：原则在模型唯一决策输入（任务书两段）里在场——规章段（system 请求首条）＋动态段（链上）
    contract_state = _state()
    completer = _interpret_with_calls(contract_state, _full_reply("问日产油量。", ["日产油量"]))
    book = _task_book_of(contract_state)
    contract = _system_contract_of(completer, 0)
    assert TASK_BOOK_TASK in contract  # 指令区例外条款整段在场（prompts 单点合同文本）
    for clause in (_FAIL_CLOSED_CLAUSE, _HESITANT_CLAUSE, _NARROW_EXIT_CLAUSE):
        assert clause in contract  # 可能有关／拿不准 → 完整流程；只有确定无关 → 直答
    for clause in (_QUESTION_SEGMENT_HEAD, _GREETING_ONLY_CLAUSE):
        assert clause in book  # 题干段收束句同口径（先判相关性）

    # 案二：灰区／拿不准句的直答认领 → 结构核验命中 → 退回完整流程（fail-closed 一侧）
    for question, direct_text in _FAIL_CLOSED_CASES:
        state = _state(question=question)
        out, _bus = _interpret(state, _direct_reply(direct_text))
        assert isinstance(out, Understanding) and out.route == _SPEC_ROUTE_FULL
        assert state.draft == "" and state.draft_kind == "" and state.next_intent == ""
        _assert_rejected_direct(state, direct_text)
        assert _closure_hits_of(state)  # 命中判据点名（数值形／名录名至少其一）

    # 案三：同一灰区句判 full → 走完整流程（分派只由 route 定；程序侧零词面判据）
    for question, _direct_text in _FAIL_CLOSED_CASES:
        state = _state(question=question)
        out, bus = _interpret(state, _full_reply("问井的日产油量口径。", []))
        assert isinstance(out, Understanding) and out.route == _SPEC_ROUTE_FULL
        assert state.draft == "" and state.next_intent == ""  # 直答口未开
        assert [frame.event for frame in await _frames(bus)] == [_SPEC_TEXT_EVENT]


# ---------- 15 【边界集】数值形 → 直答判不合格；指标名/表名单出现 → 不退回 ----------


_BOUNDARY_IN_WORLD: tuple[tuple[str, str, str], ...] = (
    ("看一下２０２６年的数据。", _KIND_NUMERIC, "２"),  # 全角数字（NFKC 归一后同一判据）
    ("含水率 95.5%。", _KIND_NUMERIC, "9"),  # 小数＋百分号（数值形组成）
    ("产量涨了 12.5%。", _KIND_NUMERIC, "1"),  # 数值断言（含指标名也只按数值形判）
)
# 2026-10-18 V2-83 判据收窄：指标名/表名单出现＝介绍/能力枚举，不是数据断言 → 保留直答
_BOUNDARY_RETAINED: tuple[str, ...] = (
    "含水率这个指标我看下。",  # 名录内指标名（slot）
    "产油量的口径是什么？",  # 名录内别名面
    "查一下 agg.dim_well。",  # 结构卡内表名（全名）
    "dim_well 这张表里有啥？",  # 结构卡内表名（短名）
    "你好！我是「问一问」——油田生产数据问答助手。可以直接问我生产数据或报告里的问题，"
    "比如某口井的日产油量、区块的产量完成率、本月抽油机时率，或月报、完井报告结论。",
)
_BOUNDARY_OUT_OF_WORLD: tuple[str, ...] = (
    "库存总量是多少？",  # 名录外生词
    "井口压力怎么样？",  # 闭世界外（非名录、非结构卡、无数字形）
)


async def test_direct_boundary_cases_rejected() -> None:
    """#15｜【边界集】数值形 → 直答判不合格；指标名/表名单出现 → 不退回——行为 5（V2-83 收窄）。

    边界两侧同判：数值形**内**三类各命中 → 退回 `route="full"`（逐条判据点名如实上报）；
    指标名/表名单独出现（含真机问候原句）＝介绍不是断言 → **保留直答**（2026-10-18 V2-83，
    真机 `run-a11920fb` 误退根治）；闭世界**外**的生词不算命中（行为 5 末句：结构判据，不做
    语义猜测）→ 窄口内直答仍成立。
    """
    for text, kind, token in _BOUNDARY_IN_WORLD:
        state = _state()
        out, _bus = _interpret(state, _direct_reply(text))
        assert isinstance(out, Understanding) and out.route == _SPEC_ROUTE_FULL
        _assert_rejected_direct(state, text)
        assert {_PAYLOAD_HIT_KIND_KEY: kind, _PAYLOAD_HIT_TOKEN_KEY: token} in _closure_hits_of(
            state
        )

    # 保留集：指标名/表名单出现不判不合格（能力介绍/术语询问/问候枚举）
    for text in _BOUNDARY_RETAINED:
        state = _state()
        out, _bus = _interpret(state, _direct_reply(text))
        assert isinstance(out, Direct) and out.route == _SPEC_ROUTE_DIRECT
        assert direct_assertion_hits(state, text) == ()
        assert state.draft == text and _reject_notes(state) == [] and state.notices == []

    # 边界外：生词零命中 → 仍走直答（不误伤——判据锁闭世界，非词表猜语义）
    for text in _BOUNDARY_OUT_OF_WORLD:
        state = _state()
        out, _bus = _interpret(state, _direct_reply(text))
        assert isinstance(out, Direct) and out.route == _SPEC_ROUTE_DIRECT
        assert direct_assertion_hits(state, text) == ()
        assert state.draft == text and _reject_notes(state) == [] and state.notices == []


# ---------- 16 【保留集】寒暄仍走 direct；route=full 的既有候选校验不变 ----------


async def test_retention_non_direct_unchanged() -> None:
    """#16｜【保留集】寒暄仍走 direct；route=full 的既有候选校验行为不变——行为 5／8／11。

    保留面三条：① 寒暄仍走直答收口（核验面只在**命中**时介入，未命中零改道）；② `route="full"` 的
    候选出自名录校验**不变**（名录外候选判违约并如实上报——-A 行 2 行为不因本票回退）；③ 两判据面
    互不串（直答退回的报告步事件名 ≠ 候选违约；退回不发明候选）。
    """
    # 保留一：寒暄仍走 direct
    for text in ("不客气。", "再见。"):
        state = _state()
        out, bus = _interpret(state, _direct_reply(text))
        assert isinstance(out, Direct) and out.route == _SPEC_ROUTE_DIRECT and out.text == text
        assert state.draft == text and state.draft_kind == _SPEC_DRAFT_KIND_DIRECT
        assert state.next_intent == _SPEC_INTENT_ANSWER
        assert state.understanding == "" and state.metric_candidates == []
        assert _reject_notes(state) == [] and state.notices == [] and _report_steps(state) == []
        assert await _frames(bus) == []

    # 保留二：route=full 的候选校验行为不变（名录外候选 → 违约上报，不静默丢弃）
    state = _state()
    out, _bus = _interpret(
        state, _full_reply("问日产油量与库存总量。", ["日产油量", _OUT_OF_ROSTER])
    )
    assert isinstance(out, Understanding) and out.route == _SPEC_ROUTE_FULL
    assert state.metric_candidates == ["日产油量", _OUT_OF_ROSTER]  # 候选原样保留
    assert _reject_notes(state) == []  # full 路径不产退回注记（两判据面互不串）
    reports = _report_steps(state)
    assert len(reports) == 1
    assert reports[0]["payload"][_PAYLOAD_EVENT_KEY] == _EVENT_CANDIDATE_VIOLATION
    assert reports[0]["payload"][_PAYLOAD_OFFENDERS_KEY] == [_OUT_OF_ROSTER]

    # 保留三：退回面不冒用候选违约面（候选零发明；事件名＝直答退回）
    state = _state()
    rejected_text = "日产油量是 1 吨。"
    _interpret(state, _direct_reply(rejected_text))
    assert state.metric_candidates == []
    events = [step["payload"][_PAYLOAD_EVENT_KEY] for step in _report_steps(state)]
    assert events == [_EVENT_DIRECT_REJECTED]
    assert state.notices[0]["content"]  # 退回通报在人读面可见（不静默）


# ---------- 17–20 schema 拒回喂重试恰一次（2026-10-16 补·流水 67） ----------

# 真机 `run-60bc4aaa` 原形（旧的「两行式」被塞进 `text`、漏 `metric_candidates` 必填键）：
# 候选取 fixture 名录内词（本组只测 schema 面——别名／名录外候选的违约上报归行 2，不在此重测）。
_RETRY_BAD = json.dumps(
    {"route": _SPEC_ROUTE_FULL, "text": "理解：问井的日产油量。\n指标候选：日产油量"},
    ensure_ascii=False,
)
_RETRY_GOOD = _full_reply("问井的日产油量。", ["日产油量"])
_RETRY_NOTE_TITLE = "读题回喂重试"
_FEEDBACK_TAIL = (
    "——只修正不合项，其余内容照旧，重新输出一个 JSON 对象（不要输出 JSON 之外的解释文字）。"
)


def _retry_notes(state: RunState) -> list[dict[str, Any]]:
    """过程档案里的「读题回喂重试」注记（回喂面留痕；同标题多条＝重复计入即红）。"""
    return [e for e in state.process_notes if e.get("title") == _RETRY_NOTE_TITLE]


def _read_notes(state: RunState) -> list[dict[str, Any]]:
    """过程档案里的「读题」注记（每次模型应答恰一条——两读＝两条）。"""
    return [e for e in state.process_notes if e.get("title") == _READ_NOTE_TITLE]


def test_schema_reject_feedback_retry_once() -> None:
    """#17｜首读缺 `metric_candidates` → 回喂 → 次读合规 → 正常分派（零 failed；调用恰 2 次）。

    行为 13 的**修参面**：回喂＝拒因载荷追加链尾后**同相位再读一次**（不判死、不补默认）；
    两次调用各记一条步（`call_model` 单点）；回喂支**零副作用**（不发 notice、不记步、报告面零写）。
    """
    state = _state()
    outs, _bus, completer = _interpret_all_with_calls(state, _RETRY_BAD, _RETRY_GOOD, runs=1)
    out = outs[0]

    # 次读合规 → 正常走 `full` 分派（双出口照旧；理解字段取**次读**结论）
    assert isinstance(out, Understanding) and out.route == _SPEC_ROUTE_FULL
    assert out.text == "问井的日产油量。" and out.metric_candidates == ["日产油量"]
    assert state.understanding == "问井的日产油量。"
    assert state.metric_candidates == ["日产油量"]
    # 零 failed：无报告步、无 notice（回喂支零副作用——如实上报只在两读皆拒时出一份）
    assert _report_steps(state) == [] and state.notices == []
    # 调用恰 2 次（上限恰一次）；两次各记一条步（call_model 单点记账，本块不另记步）
    assert [caller for caller, _messages in completer.calls] == [_SPEC_CALLER, _SPEC_CALLER]
    assert len(state.steps) == 2
    # 链形：背景块（system）→ 任务书 → 首答（原话留痕）→ 回喂载荷（user）→ 次答（assistant）；
    # 追加式不重写（2026-10-17 H 批：链首恒一条背景块）
    assert [m["role"] for m in state.messages] == [
        "system",
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert state.messages[0]["content"] == SYSTEM_BACKGROUND
    assert state.messages[2]["content"] == _RETRY_BAD
    assert state.messages[4]["content"] == _RETRY_GOOD
    # 两次请求首条＝system 规章段（读题合同），且**不含**已入链的内容（规章随请求、不入链）
    for index in (0, 1):
        contract = _system_contract_of(completer, index)
        assert contract == understand_system_contract()
        assert TASK_BOOK_SCENE in contract and TASK_BOOK_OUTPUT_CONTRACT in contract
        assert contract not in [str(m["content"]) for m in state.messages]
    # 过程档案：读题注记×2（两读各一条）＋回喂重试注记×1＋装配标记（pin-26 渲染面）
    assert len(_read_notes(state)) == 2 and len(_retry_notes(state)) == 1
    assert state.dialogue == []  # 回喂载荷入链、不入对话层（过程记录不混层）


def test_schema_reject_twice_converges_to_refusal() -> None:
    """#18｜两读皆拒 → **收敛拒答**＋拒因留痕；**上限恰一次**（第三次永不发生）。

    2026-10-17 EB3 D4.4 改判（原「抛 `UnderstandingParseError` → 编排收 `failed`」退役——真机
    `eval/results/frames/EB2-NQ-D2.json` 整 run 零交付）：仍不合 schema → `direct_answer` 落拒答
    正文（`draft`／`draft_kind="direct"`／`next_intent="answer"`）＋返回该 `Direct`；如实上报照出
    一份（报告步＋notice——回喂支不重复上报）；拒因留痕三面在场：链上载荷 ＋ 过程档案注记 ＋ 报告步。
    """
    for raw in (_RETRY_BAD, json.dumps({"route": "partial", "text": "x"}), "不是 JSON"):
        state = _state()
        outs, _bus, _completer = _interpret_all_with_calls(state, raw, runs=1)
        out = outs[0]
        assert isinstance(out, Direct)
        # 收敛拒答（非抛错、非零交付）：拒答正文落直答旁路三键，与返回值同源
        assert _REFUSAL_MARK in out.text
        assert state.draft == out.text and state.draft_kind == "direct"
        assert state.next_intent == "answer"
        # 上限恰一次：两次调用、绝无第三次；步数＝2 记账步 ＋ 1 报告步
        assert len(state.steps) == 3
        # 拒因留痕（链上载荷 ＋ 过程档案注记）：回喂载荷在链上（首答之后）
        assert [m["role"] for m in state.messages] == [
            "system",
            "user",
            "assistant",
            "user",
            "assistant",
        ]
        assert state.messages[3]["content"].startswith("【拒因】")
        assert len(_retry_notes(state)) == 1 and len(_read_notes(state)) == 2
        # 收敛注记（过程档案）＋如实上报照出一份（不因回喂翻倍）；不返回半成品
        assert state.process_notes[-1]["title"] == _CONVERGE_NOTE_TITLE
        assert len(state.notices) == 1 and len(_report_steps(state)) == 1
        assert state.understanding == "" and state.metric_candidates == []
        assert state.dialogue == []


def test_schema_feedback_three_segment_payload() -> None:
    """#19｜拒因载荷三段带路形（【拒因】指名不合项 ＋【期望形】＋ 尾行；自足、壳恰一遍）。

    逐支（真机原形＝缺必填字段；类型不符；`route` 越界；非 JSON）：【拒因】段**指名哪一条**
    （取 `parsing.understanding_schema_feedback` 的诊断出口——本块零 schema 重判）；
    【期望形】段＝理解面输出契约两形＋无命中＝空数组；尾行＝修正指令；**壳恰一遍**（不叠字）。
    """
    cases: tuple[tuple[str, str], ...] = (
        (_RETRY_BAD, "缺必填字段 `metric_candidates`"),
        (
            json.dumps({"route": _SPEC_ROUTE_FULL, "text": 3, "metric_candidates": []}),
            "字段类型不符：`text` 须为字符串",
        ),
        (
            json.dumps({"route": "partial", "text": "x"}),
            "`route` 取值越界（闭世界仅「full」｜「direct」）",
        ),
        ("不是 JSON", "应答不是合法 JSON"),
    )
    for raw, reason in cases:
        state = _state()
        _interpret_all_with_calls(state, raw, _RETRY_GOOD, runs=1)
        # 链＝[背景, 题面, 任务书, 首答, 回喂载荷]（H 批链首背景条）
        feedback = state.messages[3]["content"]
        segments = feedback.split("\n")
        # 段一【拒因】：具体不合项逐字在场（「哪一条」说清——不空转、不笼统）
        assert segments[0] == f"【拒因】{reason}"
        # 段二【期望形】：两形＋必填与空数组形（照合同与样例集）
        assert segments[1].startswith("【期望形】")
        assert '"route":"full"' in segments[1] and '"route":"direct"' in segments[1]
        assert '"metric_candidates":["〈台账名录里的指标名〉"]' in segments[1]
        assert "空数组 []" in segments[1]
        # 段三尾行：修正指令（重发一个 JSON）
        assert segments[2] == _FEEDBACK_TAIL
        assert len(segments) == 3  # 恰三段（schema 面无「台账相关行」段）
        # 壳恰一遍（载荷自足——链上直投，不二次套壳）
        assert feedback.count("【拒因】") == 1 and feedback.count("【期望形】") == 1
        assert feedback.count(_FEEDBACK_TAIL) == 1
        # 过程档案注记携同一载荷（同一次拼装产物——不各自生成）
        assert _retry_notes(state)[0]["digest"].startswith(f"【拒因】{reason}")


def test_schema_feedback_prefix_extension() -> None:
    """#20｜回喂＝**追加形**：第二次调用的消息链＝第一次的**前缀延伸**（前置内容逐字不动）。

    「拒因追加链尾」的 KV 纪律面（`pin-22` 只追加）：逐字前缀延伸 ⇒ 常驻前缀可命中缓存；
    首答（模型原话）与回喂载荷在两链间**原样在场**（不改写、不重排、不删除）。
    """
    state = _state()
    outs, _bus, completer = _interpret_all_with_calls(state, _RETRY_BAD, _RETRY_GOOD, runs=1)
    assert len(outs) == 1
    first = completer.calls[0][1]
    second = completer.calls[1][1]
    assert second[: len(first)] == first  # 逐字前缀延伸（真源 KV 纪律）
    assert len(second) == len(first) + 2
    # 追加两件＝首答原话（assistant）＋回喂载荷（user）；规章段与链首背景条逐字未动
    assert second[0] == first[0] and second[0]["role"] == "system"
    assert second[0]["content"] == _system_contract_of(completer, 0)
    assert second[1]["content"] == SYSTEM_BACKGROUND  # 链首背景块（H 批）
    assert _DATA_ZONE_HEAD in str(second[2]["content"])  # 任务书动态段（数据区）逐字未动
    assert second[len(first) :] == [
        {"role": "assistant", "content": _RETRY_BAD},
        {"role": "user", "content": state.messages[3]["content"]},
    ]


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
    # （夹具自带链首背景块＝生产链形，非本相位写入——故「链」判据＝未增条）
    assert state.messages == [{"role": "system", "content": SYSTEM_BACKGROUND}]
    assert state.steps == []
    assert state.process_notes == [] and state.notices == []
    assert state.understanding == "" and state.metric_candidates == []
    assert state.subjects == () and state.terms == ()  # V2-82a 字段面同判（零副作用的另两面）


# ══════════════════════════════════════════════════════════════════════════════════════
# V2-82a（票②a-1，2026-10-17）：程序预识别推荐行 ＋ 主体/术语结构化槽 ＋ 分歧留痕
# ══════════════════════════════════════════════════════════════════════════════════════

_PG_QUESTION = "W-11 井的日产油量是多少？"  # 题面点名井号＋台账指标名（两候选面同时在场）
_PG_SUBJECTS = "W-11"
_PG_TERMS = "日产油量"
# 分歧留痕条目标题（规格逐字面——实现漂移即红）
_SPEC_SUBJECT_DIVERGENCE_TITLE = "主体识别分歧"


def _full_reply_with_slots(
    text: str,
    candidates: Sequence[str],
    *,
    subjects: Sequence[str] | None = None,
    terms: Sequence[str] | None = None,
) -> str:
    """理解应答 JSON（V2-82a：可携 `subjects`／`terms`；`None`＝键缺席——缺省＝空元）。"""
    payload: dict[str, Any] = {
        "route": _SPEC_ROUTE_FULL,
        "text": text,
        "metric_candidates": list(candidates),
    }
    if subjects is not None:
        payload["subjects"] = list(subjects)
    if terms is not None:
        payload["terms"] = list(terms)
    return json.dumps(payload, ensure_ascii=False)


def test_program_recommendation_line_present_at_data_zone_tail() -> None:
    """推荐行｜环境块尾注入「程序预识别」一行（逐字稿模板＋程序候选值）；位置＝数据区块尾、
    题干段之前（题干段仍置末）。
    """
    state = _state(question=_PG_QUESTION)
    _interpret(state, _full_reply("问 W-11 井日产油量。", [_PG_TERMS]))
    book = _task_book_of(state)
    line = RECOMMENDATION_TEMPLATE.format(subjects=_PG_SUBJECTS, terms=_PG_TERMS)
    assert line in book
    assert book.index(_DATA_ZONE_HEAD) < book.index(line) < book.index(_QUESTION_HEAD)
    assert book.rstrip().endswith("现在输出。）")  # 题干段仍为末段


def test_program_recommendation_line_renders_none_placeholder() -> None:
    """推荐行｜空候选面＝「无」（逐字稿「空＝无」）；空 dump（未接线 run 同形）不崩——
    井号面照常、术语面落「无」。
    """
    empty_terms = _state(question=_PG_QUESTION, ledger_dump={})
    _interpret(empty_terms, _full_reply("问日产油量。", []))
    assert RECOMMENDATION_TEMPLATE.format(subjects=_PG_SUBJECTS, terms="无") in _task_book_of(
        empty_terms
    )

    no_subject = _state(question="这道题怎么看？")
    _interpret(no_subject, _full_reply("此题无主体。", []))
    assert RECOMMENDATION_TEMPLATE.format(subjects="无", terms="无") in _task_book_of(no_subject)


def test_subject_terms_written_and_divergence_noted() -> None:
    """分歧留痕｜模型给出的主体与程序候选集合不一致 → `state.subjects` 照抄落位 ＋
    过程档案有界一句「主体识别分歧：程序推荐{…}/模型给出{…}」（有界 ≤100 字）。
    """
    state = _state(question=_PG_QUESTION)
    _interpret(
        state,
        _full_reply_with_slots(
            "问 Y-41 井日产油量。", [_PG_TERMS], subjects=["Y-41"], terms=[_PG_TERMS]
        ),
    )
    assert state.subjects == ("Y-41",) and state.terms == (_PG_TERMS,)
    notes = [
        entry
        for entry in state.process_notes
        if entry["title"] == _SPEC_SUBJECT_DIVERGENCE_TITLE
    ]
    assert len(notes) == 1
    assert notes[0]["phase"] == _SPEC_CALLER
    assert notes[0]["digest"] == f"程序推荐{_PG_SUBJECTS}/模型给出Y-41"
    assert len(notes[0]["digest"]) <= 100  # 有界（票面「截断 ≤100 字」）
    assert state.dialogue == []  # 留痕入过程档案、不入对话层（pin-26）


def test_subject_agreement_zero_note_and_slots_written() -> None:
    """零漂移半边｜模型给出的主体与程序候选集合一致（含序不同）→ **零分歧注记**；
    字段面照常落位（分歧留痕是注记、不是写入闸）。
    """
    state = _state(question=_PG_QUESTION)
    _interpret(
        state,
        _full_reply_with_slots(
            "问 W-11 井日产油量。", [_PG_TERMS], subjects=[_PG_SUBJECTS], terms=[_PG_TERMS]
        ),
    )
    assert state.subjects == (_PG_SUBJECTS,) and state.terms == (_PG_TERMS,)
    assert [
        entry
        for entry in state.process_notes
        if entry["title"] == _SPEC_SUBJECT_DIVERGENCE_TITLE
    ] == []
    assert [entry["title"] for entry in state.process_notes] == [
        _TASK_BOOK_NOTE_TITLE,
        _READ_NOTE_TITLE,
    ]
