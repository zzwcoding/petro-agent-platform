"""clarification.subject_ask —— 对象歧义的程序判定 ask（V2-82b——流水 88 裁决⑥）。

裁决⑥ 本有「目标/对象/口径歧义→ask」，但全靠 LLM 自觉（程序只验形状），B-正6（近三年 8 月
平均检泵周期——两个油田的数据都在材料里）即漏网例。本模块把「对象歧义」变成**程序行为**：
术语命中 ∧ 指标粒度要求主体 ∧ 题面无主体 ∧ 系统内油田实例≥2 → 程序直接弹 ask——
**一次模型调用也不发起**（不等 LLM 自觉）。

**2026-10-17 V2-82 批 EB6 修 1（A2 门误触）**：题面已点名主体（真机 NQ-C9：「Y-21 井」）而模型
未在 `subjects` 槽复述时，原判据只读模型槽 ⇒ 误弹 ask。修法＝**程序候选回退**：`state.subjects`
空 ∧ 题面程序抽得到主体 ⇒ **题面抽得到主体＝对象已定**——把程序候选**回填进 `state.subjects`**
并不弹 ask（照 V2-82a「LLM 与程序不一致以 LLM 为准」精神：此处 LLM 空＝程序补位，分歧留痕＝
`bookkeeping.note` 有界一句，见 `_note_program_backfill`）。判定序＝**LLM 槽非空 → 用 LLM 的（不问）
｜LLM 空 ∧ 程序候选非空 → 回填＋不问｜双空 → 走原门**。

判定门（逐条全中才弹；序＝由廉价到昂贵，外部读缝放最后）：

1. **题面无主体且程序候选亦空**——`state.subjects` 空（V2-82a 通道：模型在理解输出没给主体）
   且回退读程序候选亦空（程序候选非空者已在上一步回填收口，不到本条）；
2. **术语/指标命中**——`state.terms` 或 `state.metric_candidates` 非空（两槽皆空＝无话头）；
3. **指标粒度要求主体**——`state.terms or state.metric_candidates` 里**任一**名字解析到台账
   指标且其 grain 含「单井／区块／油田／平台」（`tools.subject_terms.metric_requires_subject`
   ——纯术语名解析不到指标即不弹：解释类问题不受本条波及）；
4. **系统内油田实例≥2**——`subject_instances()`（读面＝`query.production_field_instances`
   ——`agg.dim_well.field_name` 现值集，经 `tools.oilfield_instances` 归一）≥2 个
   （不足＝静默不出声）；
5. **预算尊重**——本 run 已发射 ask 数（口径同澄清相位 `_ask_count`）达 `budget.ask_cap`
   ⇒ 不弹，走原路（澄清相位自己的到顶截断照旧）。

**票面伪代码首句「`route != full` ⇒ 不弹」不另立判据**：澄清节点只在完整流程可达——直答
（`Understanding.route="direct"`）在理解相位即经 `bookkeeping.direct_answer` 交作答收口、
路由到 `answer` 节点，不经本入口；`RunState` 无 `route` 字段（理解态不在状态形状内），故该
条由链路结构保证（`understanding.interpret` 的 `_dispatch_full` 才落 `next_intent=decision`）。

**发射面与澄清相位同形**（票面「同 `clarification/core.py:828` 返回形」）：命中即
`state.pending_subject_options` 落实例候选（恢复腿映射用）＋落**同一计数载体**的步记录
（`PAYLOAD_ASK_FRAME`——`graph._consecutive_asks`／本块 `_ask_count` 同口径；**票面补足**：
不落此步则本条 ask 不计入连续反问预算，同一 run 可被重复弹问无上限），返回 `ClarifyAsk`；
`pending_ask` 帧投影、挂起态与 `ask` 帧发射**仍归编排**（`graph._suspend`——本块不写帧面）。

零模型调用、零工具直调（问句原文读点在编排）、盘面写入＝回填 `state.subjects` 一处（步记录／过程
档案经 `bookkeeping` 唯一写口）。

**依赖注入面（本块零工具直调红线）**：本块（clarification 包）源码**不 import 工具面／引擎面**
（AST 机检，`tests/domains/test_v2_clarification.py::test_discover_routed_not_direct_call`），且
**零问句原文读点**（同件 `::test_no_ask_when_time_resolvable`——`state.question` 属性访问探测），
故三件素材**由编排注入**：`grain_requires_subject`＝「名字 →（台账投影）该指标 grain 是否含
单井／区块／油田／平台」（tools 侧纯函数 `subject_terms.metric_requires_subject`，编排绑定传入）、
`subject_instances`＝油田实例名单读面（tools 侧归一函数 `subject_terms.oilfield_instances`
包着井名录同源读缝，编排绑定传入）与 `program_subjects`＝题面程序主体候选读面
（`Callable[[], Sequence[str]]`；生产绑定＝编排侧
`lambda: subject_candidates(state.question, state.ledger_dump)`——**问句与投影的读点在编排**）。
判据组合（回退四步＋原门四条＋预算尊重）仍在本块单点。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from appv2.runtimev2.bookkeeping import note, record_step
from appv2.runtimev2.clarification.constants import (
    ASK_FRAME_DETAIL_NONE,
    ASK_KIND_CLARIFY,
    NOTE_PHASE,
    PAYLOAD_ASK_FRAME,
    PAYLOAD_PHASE,
    STEP_TITLE_ASK,
    STEP_TITLE_PROMPT_CHARS,
    SUBJECT_ASK_PROMPT,
    SUBJECT_BACKFILL_DIGEST,
    SUBJECT_BACKFILL_NOTE_TITLE,
    SUBJECT_BACKFILL_SEP,
)
from appv2.runtimev2.clarification.core import _ask_count
from appv2.runtimev2.clarification.models import ClarifyAsk
from appv2.runtimev2.prompts import PHASE_CLARIFY
from appv2.runtimev2.state import ALL_FIELDS_OPTION, STEP_DECISION, RunState


def object_ambiguity_ask(
    state: RunState,
    *,
    grain_requires_subject: Callable[[str, Mapping[str, Any]], bool],
    subject_instances: Callable[[], Sequence[str]] | None,
    program_subjects: Callable[[], Sequence[str]] | None = None,
) -> ClarifyAsk | None:
    """对象歧义门（V2-82b）：命中 ⇒ `ClarifyAsk`（编排据此挂起）；未命中 ⇒ `None`（走原路）。

    `grain_requires_subject`＝「该名对应指标是否粒度要求主体」的纯函数（签名
    `(名字, 台账投影) -> bool`——生产引用＝`tools.subject_terms.metric_requires_subject`；
    `state.ledger_dump` 由本块取，注入面见模块 docstring）；`subject_instances`＝油田实例名单
    读面（`Callable[[], Sequence[str]]`——**已归一形**，生产引用＝
    `tools.subject_terms.oilfield_instances` 包着井名录同源读缝，由编排绑定；
    **判定通过前不调用**）；`program_subjects`＝题面程序主体候选读面（V2-82 批 EB6 修 1——
    `Callable[[], Sequence[str]]`，生产绑定＝编排侧
    `lambda: tools.subject_candidates(state.question, state.ledger_dump)`；**本块零问句读点**，
    故问句与投影的读点在编排）。三面缺位／调用异常一律按空（**读缝缺省纪律**同 `data_wells`
    域闸：未接线不误伤，不发明实例／不发明主体）。

    判定序（V2-82 批 EB6 修 1）：`state.subjects` 非空 → 不弹（LLM 已定主体，程序不抢判）；
    空 ∧ 程序候选非空 → **回填 `state.subjects` ＋留痕 ＋ 不弹**（题面抽得到主体＝对象已定）；
    双空 → 走原门。

    命中时的状态写入＝`pending_subject_options`（实例候选，恢复腿据此映射 `subjects`；
    回填路径写 `state.subjects`）；步记录经 `bookkeeping.record_step`（`PAYLOAD_ASK_FRAME`＝
    连续反问计数载体），回填留痕经 `bookkeeping.note`（`process_notes` 唯一写口）。
    """
    if state.subjects:
        return None
    backfilled = _program_of(program_subjects)
    if backfilled:
        state.subjects = backfilled
        _note_program_backfill(state, backfilled)
        return None
    names: tuple[str, ...] = state.terms or tuple(state.metric_candidates)
    if not names:
        return None
    dump = _dump_of(state)
    if not any(grain_requires_subject(name, dump) for name in names):
        return None
    instances = _instances_of(subject_instances)
    if len(instances) < 2:
        return None
    if _ask_count(state) >= int(state.budget.ask_cap):
        return None
    prompt = SUBJECT_ASK_PROMPT.format(name=names[0])
    options = [*instances, ALL_FIELDS_OPTION]
    state.pending_subject_options = tuple(instances)
    record_step(
        state,
        kind=STEP_DECISION,
        title=STEP_TITLE_ASK.format(
            round=int(state.rounds) + 1, prompt=prompt[:STEP_TITLE_PROMPT_CHARS]
        ),
        payload={
            PAYLOAD_PHASE: PHASE_CLARIFY,
            PAYLOAD_ASK_FRAME: {
                "kind": ASK_KIND_CLARIFY,
                "prompt": prompt,
                "options": list(options),
                "detail": ASK_FRAME_DETAIL_NONE,
            },
        },
    )
    return ClarifyAsk(prompt=prompt, options=options)


def _dump_of(state: RunState) -> Mapping[str, Any]:
    """台账投影面（缺失／形不合＝空映射——注入的 grain 判据对空投影恒 False，零漂移）。"""
    dump = state.ledger_dump
    return dump if isinstance(dump, Mapping) else {}


def _instances_of(
    subject_instances: Callable[[], Sequence[str]] | None,
) -> tuple[str, ...]:
    """油田实例名单（读面产物原样取；读面缺位／异常＝空集——不误伤、不冒充实例）。"""
    if subject_instances is None:
        return ()
    try:
        rows = subject_instances()
    except Exception:  # 读面异常＝本判据不出声（同 data_wells 域闸缺省纪律）
        return ()
    return tuple(str(item) for item in rows or ())


def _program_of(
    program_subjects: Callable[[], Sequence[str]] | None,
) -> tuple[str, ...]:
    """题面程序主体候选（读面缺位／异常＝空集——原门照走，不误伤、不发明主体）。

    空串候选如实剔除（读面产物形面，零发明）；`state.subjects` 回填的是**候选原形**
    （`tools.subject_candidates` 已归一的规范形——油田／平台名与井号归一形，本块不二次改写）。
    """
    if program_subjects is None:
        return ()
    try:
        rows = program_subjects()
    except Exception:  # 读面异常＝本判据不出声（同实例读缝缺省纪律）
        return ()
    return tuple(name for name in (str(item) for item in rows or ()) if name)


def _note_program_backfill(state: RunState, subjects: Sequence[str]) -> None:
    """程序补位留痕（V2-82 批 EB6 修 1）：LLM 槽空 ∧ 程序候选非空 → 过程档案有界一句。

    机制同 V2-82a 的主体识别分歧注记（`understanding._note_subject_divergence`）：只留痕、不改写
    判定，经唯一写口 `bookkeeping.note`（`phase`／`title`／`digest` 三键；digest 在写入点截断）。
    **本块零 `understanding` import**（依赖白名单红线），故标题／digest 字面自持一对，
    见 `clarification.constants` 该对常量的注；`dialogue` 零写入。
    """
    note(
        state,
        phase=NOTE_PHASE,
        title=SUBJECT_BACKFILL_NOTE_TITLE,
        digest=SUBJECT_BACKFILL_DIGEST.format(names=SUBJECT_BACKFILL_SEP.join(subjects)),
    )
