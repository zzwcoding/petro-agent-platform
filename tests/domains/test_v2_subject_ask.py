"""V2-82b 对象歧义程序判定 ask 的钉测（票②a-2——流水 88 裁决⑥）。

票面验收四面：
- **判定门四分支**：无主体＋粒度要求主体＋实例≥2 → 弹（prompt／options 逐字断言）；
  已给 `subjects` → 不弹；粒度不要求（纯术语解释）→ 不弹；实例<2 → 不弹；
- **恢复三分支**：选实例 → `subjects=(实例,)`；选都要 → 哨兵 `__all_fields__`；
  候选名单外的选择 → 不写主体（零发明）并清候选；ask 预算到顶 → 不弹（走原路）；
- **全链黑盒**：理解（无主体）→ 编排弹 ask（挂起帧四键）→ resume 选实例 → subjects 落状态；
- **弹 ask 路径零澄清 LLM 调用**（黑盒断言）。

素材链：油田实例名单＝`query.production_field_instances` 读缝（`agg.dim_well.field_name`
现值集）的 tools 侧归一形（`tools.oilfield_instances`）；粒度判定读台账 dump 的
`metrics[].grain`（`tools.metric_requires_subject`——本件用真快照投影 dump，非自造行）。

**V2-82 批 EB6 修 1（程序候选回退）**：判定序＝LLM 槽非空 → 用 LLM 的｜空 ∧ 程序候选非空 →
回填 `state.subjects` ＋不问｜双空 → 走原门；回退读面（题面程序主体候选）＝编排注入的零参读面
（生产绑定＝`tools.subject_candidates(state.question, state.ledger_dump)`，问句读点在编排）。
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

import pytest

from appv2.infra.clock import freeze
from appv2.knowledge import InMemoryKnowledgeStore, question_array_snapshot
from appv2.runtimev2.clarification import object_ambiguity_ask
from appv2.runtimev2.clarification.constants import (
    ASK_KIND_CLARIFY,
    PAYLOAD_ASK_FRAME,
)
from appv2.runtimev2.clarification.core import _ask_count
from appv2.runtimev2.context import wire_ledger_projection
from appv2.runtimev2.orchestration import RunExecutor
from appv2.runtimev2.persistence import MemoryTables, configure_tables
from appv2.runtimev2.state import ALL_FIELDS_OPTION, ALL_FIELDS_SENTINEL, Budget, RunState
from appv2.runtimev2.state import AskChoice as V2AskChoice
from appv2.tools import (
    OILFIELD_INSTANCES_CAP,
    dump_from_store,
    metric_requires_subject,
    oilfield_instances,
    subject_candidates,
)
from tests.domains.test_v2_four_phase import (
    V2LedgerPort,
    V2RunStore,
    v2_ask_frames,
    v2_data_match,
    v2_decompose,
    v2_ledger_dump,
    v2_matches,
    v2_registry,
    v2_resume,
    v2_run,
    v2_runtime,
)

# 判据素材（真源同产线一路：快照→读面→dump_from_store——`grain` 列随 dump 携出）
_DUMP: dict[str, Any] = dump_from_store(
    InMemoryKnowledgeStore(question_array_snapshot())
)
# 油田实例名单（真库三值形：读缝 raw 值集；本件用替身 loader 供给同一形）
_INSTANCES: tuple[str, ...] = ("渤中油田", "渤南油田", "渤西油田")

# 票面逐字稿（prompt／选项文案——本件逐字断言，不引模板常量自证）
_VERBATIM_PROMPT = "这道题问的是「{name}」——系统里有多个油田的数据。请确认要查哪一个："
_VERBATIM_ALL = "都要（分源对比）"


def _state(**overrides: Any) -> RunState:
    fields: dict[str, Any] = {"run_id": "run-subject-1", "ledger_dump": _DUMP}
    fields.update(overrides)
    return RunState(**fields)


# 读缝 raw 形（首尾空白——生产读缝原样出值，归一归编排侧绑的 tools 面）
_RAW_INSTANCES: tuple[str, ...] = (" 渤中油田", "渤南油田", "渤西油田 ")


def _raw_face() -> tuple[str, ...]:
    return _RAW_INSTANCES


def _gate(state: RunState, *, instances: Sequence[str] | None = _INSTANCES) -> Any:
    """门调用（注入面：grain 判据＝tools 纯函数真件；实例读面＝已归一名单／None／抛错）。"""
    if instances is None:
        face = None
    else:
        face = lambda: tuple(instances)  # noqa: E731
    return object_ambiguity_ask(
        state, grain_requires_subject=metric_requires_subject, subject_instances=face
    )


def _ask_step() -> dict[str, Any]:
    """既有 ask 步（连续反问计数载体——`PAYLOAD_ASK_FRAME` 键在场即计一）。"""
    return {
        "run_id": "run-subject-1",
        "seq": 1,
        "step": "decision",
        "status": "ok",
        "title": "澄清 r1：反问（旧问）",
        "manifest": None,
        "payload": {PAYLOAD_ASK_FRAME: {"kind": ASK_KIND_CLARIFY}},
    }


# ---------- ① 判定门四分支 ----------


def test_subject_ask_fires_with_verbatim_prompt_and_options() -> None:
    """无主体＋粒度要求主体＋实例≥2 → 弹；prompt／options 逐字，候选名单落状态。

    检定：术语槽（`state.terms`）与指标候选槽（`state.metric_candidates`）两通道都能触发；
    命中即落 `pending_subject_options`（恢复腿映射用）＋落**计数载体步**（连续反问预算口径）。
    """
    state = _state(terms=("检泵周期",))
    ask = _gate(state)
    assert ask is not None and ask.kind == ASK_KIND_CLARIFY
    assert ask.prompt == _VERBATIM_PROMPT.format(name="检泵周期")
    assert ask.options == ["渤中油田", "渤南油田", "渤西油田", _VERBATIM_ALL]
    assert state.pending_subject_options == _INSTANCES
    assert _ask_count(state) == 1  # 计数载体（同澄清相位口径）

    # 指标候选通道（术语槽空——names 取 metric_candidates，prompt 取 names[0]）
    state2 = _state(metric_candidates=["产量完成率"])
    ask2 = _gate(state2)
    assert ask2 is not None
    assert ask2.prompt == _VERBATIM_PROMPT.format(name="产量完成率")
    assert ask2.options[-1] == _VERBATIM_ALL


def test_subject_ask_skips_when_subjects_present() -> None:
    """已给主体（V2-82a 通道非空）→ 不弹（模型已定主体，程序不抢判）。"""
    state = _state(terms=("检泵周期",), subjects=("W-21",))
    assert _gate(state) is None
    assert state.pending_subject_options == ()


def test_subject_ask_skips_when_grain_does_not_require_subject() -> None:
    """粒度不要求主体 → 不弹：纯术语（解析不到指标）与「日／井」粒度指标两名都不弹。"""
    assert _gate(_state(terms=("躺井",))) is None
    assert _gate(_state(terms=("日产油量", "含水率"))) is None
    # 空投影（未取台账）＝判据恒假（不误伤）
    assert _gate(_state(terms=("检泵周期",), ledger_dump=None)) is None


def test_subject_ask_skips_when_instances_below_two() -> None:
    """系统内油田实例<2 → 不弹（单油田/空名单＝无歧义可问；读面缺位与异常同判空）。"""
    base = {"terms": ("检泵周期",)}
    assert _gate(_state(**base), instances=("渤中油田",)) is None
    assert _gate(_state(**base), instances=()) is None
    assert _gate(_state(**base), instances=None) is None

    def _broken() -> tuple[str, ...]:
        raise RuntimeError("读面不可达")

    assert (
        object_ambiguity_ask(
            _state(**base),
            grain_requires_subject=metric_requires_subject,
            subject_instances=_broken,
        )
        is None
    )


def test_subject_ask_respects_ask_budget() -> None:
    """ask 预算尊重：已发射 ask 数达 `budget.ask_cap` → 不弹（走原路）；未达顶照弹。"""
    capped = _state(terms=("检泵周期",), budget=Budget(ask_cap=1), steps=[_ask_step()])
    assert _gate(capped) is None
    assert capped.pending_subject_options == ()

    room = _state(terms=("检泵周期",), budget=Budget(ask_cap=2), steps=[_ask_step()])
    assert _gate(room) is not None


# ---------- ①b 程序候选回退（V2-82 批 EB6 修 1——A2 门误触；NQ-C9 题形） ----------

# 真机 NQ-C9 题面形（点名 Y-21 井——`eval/results/tools/suites_q6.py` 逐字摘要）
_Y21_QUESTION = (
    "请仅依据报告作答，报告没有记载的必须明说，不得推算补位：\n"
    "（1）第十章对照表中 Y-21 井「当前日产油」一栏记载的是什么？\n"
    "（2）2.1 节关于检泵周期的记载原文是什么？"
)
# 真机 B-正6 题面形（题面无主体可抽——回退判据不误伤的原门面）
_NO_SUBJECT_QUESTION = "近三年 8 月平均检泵周期是多少？"


def _gate_with_program(state: RunState, program: Any) -> Any:
    """门调用（回退读面注入形：`program=None`＝未接线；异常面＝抛错替身）。"""
    return object_ambiguity_ask(
        state,
        grain_requires_subject=metric_requires_subject,
        subject_instances=lambda: tuple(_INSTANCES),
        program_subjects=program,
    )


def test_subject_ask_backfills_program_candidates_and_skips_ask() -> None:
    """题面抽得到主体 → 回填 `state.subjects` ＋不弹 ask（修 1 的差分行）。

    对照①：同 state 不接回退读面 → 原门照弹（证明本 state 原为误触形——修 1 前的病灶面）；
    对照②：留痕＝`process_notes` 一条（机制同 V2-82a 分歧注记——`bookkeeping.note` 唯一写口）。
    """
    assert _gate(_state(question=_Y21_QUESTION, terms=("检泵周期",))) is not None  # 原门（误触形）
    state = _state(question=_Y21_QUESTION, terms=("检泵周期",))
    ask = _gate_with_program(state, lambda: ("Y-21",))
    assert ask is None  # 不弹
    assert state.subjects == ("Y-21",)  # 程序补位落主体槽
    assert state.pending_subject_options == ()  # 未落实例候选
    assert _ask_count(state) == 0  # 零 ask 计数（不进连续反问预算）
    assert state.process_notes == [
        {
            "phase": "clarify",
            "title": "主体程序回填",
            "digest": "模型未给主体——程序候选Y-21回填进 subjects",
        }
    ]


def test_subject_ask_backfill_reads_production_candidates() -> None:
    """回退读面的生产真件（`tools.subject_candidates`）在真题面上抽得出主体（素材面端到端）。"""
    state = _state(question=_Y21_QUESTION, terms=("检泵周期",))
    ask = _gate_with_program(
        state, lambda: subject_candidates(state.question, state.ledger_dump or {})
    )
    assert ask is None
    assert state.subjects == ("Y-21",)  # 井号归一形（RULE-PETRO-005 单点产物）


def test_subject_ask_llm_slot_wins_and_program_face_not_read() -> None:
    """判定序第一条：LLM 槽非空 → 用 LLM 的——回退读面一次也不调用、零留痕。"""

    def _explode() -> tuple[str, ...]:
        raise AssertionError("LLM 槽非空时不得读程序候选")

    state = _state(terms=("检泵周期",), subjects=("W-21",))
    assert _gate_with_program(state, _explode) is None
    assert state.subjects == ("W-21",)
    assert state.process_notes == []


def test_subject_ask_falls_through_when_program_candidates_empty() -> None:
    """判定序第三条：双空 → 走原门（题面无主体可抽＝原门判据面逐字不变）。

    覆盖：程序候选为空集／未接线（None）／读面异常／候选全空串（形面剔除）——四种都不得
    改变原门判定（B-正6 形题面照弹）。
    """
    for program in (lambda: (), None, lambda: ("",)):
        state = _state(question=_NO_SUBJECT_QUESTION, terms=("检泵周期",))
        assert _gate_with_program(state, program) is not None
        assert state.subjects == ()
        assert state.process_notes == []

    def _broken() -> tuple[str, ...]:
        raise RuntimeError("候选读面不可达")

    state = _state(question=_NO_SUBJECT_QUESTION, terms=("检泵周期",))
    assert _gate_with_program(state, _broken) is not None  # 读面异常＝原门照走（不误伤）


# ---------- ② 恢复三分支（编排 `_apply_choice`） ----------


def _apply(state: RunState, choice: V2AskChoice) -> None:
    configure_tables(MemoryTables())
    RunExecutor(registry=v2_registry(), store=V2RunStore())._apply_choice(state, choice)


def test_resume_instance_choice_lands_subject() -> None:
    """选实例 → `state.subjects=(实例,)`；候选名单写后即清；选择原话照旧留痕。"""
    state = _state(pending_subject_options=_INSTANCES)
    _apply(state, V2AskChoice(kind="clarify", choice="渤南油田"))
    assert state.subjects == ("渤南油田",)
    assert state.pending_subject_options == ()
    assert state.resume_choices[-1]["choice"] == "渤南油田"


def test_resume_all_choice_lands_sentinel() -> None:
    """选「都要（分源对比）」→ `subjects=(__all_fields__,)`（哨兵逐字，下游分源认这个值）。"""
    state = _state(pending_subject_options=_INSTANCES)
    _apply(state, V2AskChoice(kind="clarify", choice=ALL_FIELDS_OPTION))
    assert state.subjects == (ALL_FIELDS_SENTINEL,)
    assert ALL_FIELDS_SENTINEL == "__all_fields__"
    assert state.pending_subject_options == ()


def test_resume_choice_outside_options_keeps_subjects_unwritten() -> None:
    """候选名单外的选择 → 不写主体（零发明），候选照样清空（一问一答；下一次入口可再问）。"""
    state = _state(pending_subject_options=_INSTANCES, subjects=())
    _apply(state, V2AskChoice(kind="clarify", choice="渤海油田的"))
    assert state.subjects == ()
    assert state.pending_subject_options == ()


def test_resume_without_pending_options_is_zero_diff() -> None:
    """无对象歧义 ask 在场（既有澄清回收）→ 本映射零动作（subjects／候选都不动）。"""
    state = _state(subjects=("W-21",))
    _apply(state, V2AskChoice(kind="clarify", choice="继续"))
    assert state.subjects == ("W-21",)
    assert state.pending_subject_options == ()


# ---------- ③ 素材面（tools 侧两件） ----------


def test_oilfield_instances_normalizes_dedupes_and_caps() -> None:
    """实例名单归一（全角/空白折叠）＋去空＋去重保序＋封顶 3——库原形不改写。"""
    assert oilfield_instances((" 渤中油田 ", "渤南油田", "", None, "渤中油田")) == (
        "渤中油田",
        "渤南油田",
    )
    assert oilfield_instances(("渤中油田", "渤南油田", "渤西油田", "渤东油田")) == (
        "渤中油田",
        "渤南油田",
        "渤西油田",
    )
    assert len(oilfield_instances(("甲油田", "乙油田", "丙油田", "丁油田"))) == (
        OILFIELD_INSTANCES_CAP
    )
    assert oilfield_instances(()) == ()


def test_metric_requires_subject_reads_grain() -> None:
    """粒度判定读台账 dump 的 `metrics[].grain`：三标记命中／非命中／非指标名各判对。"""
    assert metric_requires_subject("检泵周期", _DUMP) is True  # 单井
    assert metric_requires_subject("产量完成率", _DUMP) is True  # 月/区块·油田
    assert metric_requires_subject("措施有效期", _DUMP) is True  # 单井·措施
    assert metric_requires_subject("日产油量", _DUMP) is False  # 日/井
    assert metric_requires_subject("抽油机时率", _DUMP) is False  # 月
    assert metric_requires_subject("躺井", _DUMP) is False  # 纯术语（解析不到指标）
    assert metric_requires_subject("查无此指标", _DUMP) is False
    assert metric_requires_subject("检泵周期", {}) is False  # 空投影


def test_production_field_instances_reads_dim_well_column(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """生产读缝形状钉：`agg.dim_well.field_name` 现值集投影（同表同源、schema 限定不丢）。

    读缝每次调用现读（无装配期快照）——本件以替身读面钉「loader 调用即现读」与列投影两件。
    """
    from appv2.query import pg_wells

    calls: list[int] = []

    async def fake_load(specs: tuple[Any, ...]) -> tuple[str, ...]:
        calls.append(len(calls) + 1)
        return ("渤中油田", "渤南油田") if len(calls) == 1 else ("渤西油田",)

    monkeypatch.setattr(pg_wells, "_load_field_instances", fake_load)
    loader = pg_wells.production_field_instances(())
    assert loader() == ("渤中油田", "渤南油田")
    assert loader() == ("渤西油田",)  # 第二次调用现读（非冻结快照）
    # schema 限定仍钉（agg 星型不在默认 search_path）＋ field_name 列在轻声明内
    assert pg_wells._DIM_WELL.schema == "agg"
    assert "field_name" in {column.name for column in pg_wells._DIM_WELL.c}


# ---------- ④ 全链黑盒（理解无主体 → 弹 ask → resume 选实例） ----------

_UNDERSTAND_NO_SUBJECT = json.dumps(
    {"route": "full", "text": "问近三年 8 月平均检泵周期。", "metric_candidates": ["检泵周期"]},
    ensure_ascii=False,
)


async def test_subject_ask_black_box_chain() -> None:
    """全链：理解（无主体）→ 编排弹 ask（挂起帧四键／零澄清 LLM）→ resume 选实例 → subjects 落状态。

    链路形状：挂起腿读到 `ask` 帧（其后收口 `verdict(waiting_ask)`）——本腿**零决策模型调用**
    （弹 ask 路径不调澄清 LLM）；恢复腿选实例后 `subjects` 落状态、run 照常续推至收口。
    """
    dump = v2_ledger_dump()
    script = {
        "understand": [_UNDERSTAND_NO_SUBJECT],
        "decision": [
            v2_decompose(
                subtask_id="s1",
                question="近三年 8 月平均检泵周期",
                ledger_notes="检泵周期｜已绑定｜2025-09-01~2025-09-03",
                chain="data",
            ),
            v2_matches(
                v2_data_match(
                    subtask_id="s1",
                    slot="检泵周期",
                    start="2025-09-01",
                    end="2025-09-03",
                )
            ),
        ],
        "answer": ["s1：近三年 8 月平均检泵周期 302 天 [1]。"],
    }
    wire_ledger_projection(V2LedgerPort(dump))
    with freeze("2026-10-08T09:00:00"):
        runtime, completer = v2_runtime(script=script, field_instances=_raw_face)
        events = await v2_run(runtime, "近三年 8 月平均检泵周期是多少？")
        asks = v2_ask_frames(events)
        assert len(asks) == 1
        frame = asks[0]["frame"]
        # 挂起帧四键齐备（transport 把守的既有形状）
        assert set(frame) == {"kind", "prompt", "options", "detail"}
        assert frame["kind"] == ASK_KIND_CLARIFY
        assert frame["prompt"] == _VERBATIM_PROMPT.format(name="检泵周期")
        # 读缝 raw 值 → 编排侧经 tools 归一（空白折叠）后作选项（选项序＝归一名单序）
        assert frame["options"] == ["渤中油田", "渤南油田", "渤西油田", _VERBATIM_ALL]
        run_id = asks[0]["run_id"]
        assert V2RunStore().run(run_id).status == "waiting_ask"
        # 弹 ask 路径零澄清 LLM 调用（本腿只有理解那一次）
        assert completer.counts() == {"understand": 1}
        # 候选名单随挂起态落检查点（恢复腿据此映射；存的是归一名单）
        assert V2RunStore().load(run_id).pending_subject_options == _INSTANCES

        resumed, _handle = await v2_resume(
            runtime, run_id, V2AskChoice(kind="clarify", choice="渤西油田")
        )
    assert not v2_ask_frames(resumed)  # 选了实例即不再问
    state = V2RunStore().load(run_id)
    assert state.subjects == ("渤西油田",)  # 选中项落主体槽
    assert state.pending_subject_options == ()
    assert [call for call in completer.calls if call[0] == "decision"]  # 恢复后照常走澄清


async def test_subject_ask_all_choice_black_box_sentinel() -> None:
    """全链第二支：选「都要（分源对比）」→ 哨兵 `__all_fields__` 落 `subjects`。"""
    script = {
        "understand": [_UNDERSTAND_NO_SUBJECT],
        "decision": [
            v2_decompose(
                subtask_id="s1",
                question="近三年 8 月平均检泵周期",
                ledger_notes="检泵周期｜已绑定｜2025-09-01~2025-09-03",
                chain="data",
            ),
            v2_matches(
                v2_data_match(
                    subtask_id="s1",
                    slot="检泵周期",
                    start="2025-09-01",
                    end="2025-09-03",
                )
            ),
        ],
        "answer": ["s1：近三年 8 月平均检泵周期 302 天 [1]。"],
    }
    wire_ledger_projection(V2LedgerPort(v2_ledger_dump()))
    with freeze("2026-10-08T09:00:00"):
        runtime, _completer = v2_runtime(script=script, field_instances=_raw_face)
        events = await v2_run(runtime, "近三年 8 月平均检泵周期是多少？")
        run_id = v2_ask_frames(events)[0]["run_id"]
        await v2_resume(runtime, run_id, V2AskChoice(kind="clarify", choice=ALL_FIELDS_OPTION))
    assert V2RunStore().load(run_id).subjects == (ALL_FIELDS_SENTINEL,)


async def test_subject_ask_face_missing_black_box_no_suspend() -> None:
    """读缝未接线（非生产装配）→ 门不出声：本 run 直落澄清 LLM（既有路径逐字不变）。"""
    script = {
        "understand": [_UNDERSTAND_NO_SUBJECT],
        "decision": [
            v2_decompose(
                subtask_id="s1",
                question="近三年 8 月平均检泵周期",
                ledger_notes="检泵周期｜已绑定｜2025-09-01~2025-09-03",
                chain="data",
            ),
            v2_matches(
                v2_data_match(
                    subtask_id="s1",
                    slot="检泵周期",
                    start="2025-09-01",
                    end="2025-09-03",
                )
            ),
        ],
        "answer": ["s1：近三年 8 月平均检泵周期 302 天 [1]。"],
    }
    wire_ledger_projection(V2LedgerPort(v2_ledger_dump()))
    with freeze("2026-10-08T09:00:00"):
        runtime, completer = v2_runtime(script=script)  # field_instances 缺省＝None
        events = await v2_run(runtime, "近三年 8 月平均检泵周期是多少？")
    assert v2_ask_frames(events) == []
    assert completer.counts().get("decision", 0) >= 1  # 走原路（澄清 LLM 在场）


async def test_subject_ask_black_box_program_backfill_no_ask() -> None:
    """全链（V2-82 批 EB6 修 1——A2 误触 NQ-C9 反例）：题面点名 Y-21 井、模型槽空 →
    **不弹 ask**、程序候选回填 `subjects`、澄清 LLM 照走（修前＝误弹挂起、零交付）。

    判据面同 `test_subject_ask_black_box_chain`（素材全在场：挂起腿在该形题面下修前必弹——
    对照断言见 `test_subject_ask_backfills_program_candidates_and_skips_ask`）；回退读面＝
    编排绑定（`tools.subject_candidates` ＋当场问句读点）。链路形状＝挂起腿整腿在场（
    ask 帧缺席、澄清 LLM 在场、`subjects` 随检查点落库）。
    """
    script = {
        "understand": [_UNDERSTAND_NO_SUBJECT],
        "decision": [v2_decompose(
            subtask_id="s1",
            question="近三年 8 月平均检泵周期",
            ledger_notes="检泵周期｜已绑定｜2025-09-01~2025-09-03",
            chain="data",
        )],
    }
    wire_ledger_projection(V2LedgerPort(v2_ledger_dump()))
    with freeze("2026-10-08T09:00:00"):
        runtime, completer = v2_runtime(script=script, field_instances=_raw_face)
        events = await v2_run(runtime, _Y21_QUESTION)
        assert v2_ask_frames(events) == []  # 零 ask（修前病灶面）
        assert completer.counts().get("decision", 0) >= 1  # 澄清 LLM 照走（未被门拦下）
        run_id = next(
            event.data["run_id"] for event in reversed(events) if "run_id" in event.data
        )
        state = V2RunStore().load(run_id)
    assert state.subjects == ("Y-21",)  # 程序补位落主体槽（恢复腿之外的新写点）
    assert V2RunStore().run(run_id).status == "completed"  # 续推至收口（修前＝挂起零交付）
    notes = [entry for entry in state.process_notes if entry.get("title") == "主体程序回填"]
    assert notes and "Y-21" in notes[-1]["digest"]  # 留痕（机制同 V2-82a 分歧注记）
