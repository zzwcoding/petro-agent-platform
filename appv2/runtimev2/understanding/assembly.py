"""任务书装配（行为 1／2／9）——三区装配的消费面与「每 run 只装配一次」的幂等落地。

真源＝`specs/understanding.md` 行为 1（任务书分三区且顺序固定：指令区→数据区→输出契约区）、
行为 2（数据区每轮从活体投影现取、标来源、置于末尾）、行为 9（任务书**每 run 只装配一次**）。

**文本单点在 `prompts`**：三区合同文本与段序（含题干段）的真源＝`specs/prompts.md` 行为 3–5
与 `appv2/runtimev2/prompts.assemble_task_book`——本模块只**委托**该单点（本块零第二份合同字面、
零段序重排；`specs/prompts.md` 框架红线「禁手写替代」的消费方半面）。水位等时间量只经入参注入
（本块零时钟接触，B14 在装配面的形态）；数据区随 `state.ledger_dump` 活体投影现取（行为 2）。

**2026-10-17 V2-82a（程序预识别推荐行）**：`task_book` 在数据区块尾并入一行「程序预识别」
（主体/术语候选＝`program_candidates` 经 `tools` 包根取件；字面单点在 `prompts`）——推荐面
只给模型参考，判定仍在模型（`state.subjects`／`terms` 的落点与分歧留痕归 `interpret`）。

**幂等标记**：本块自立的「已装配」判据＝过程档案里的一条标记条目（`TASK_BOOK_NOTE_TITLE`）——
任务书本身是不可再算的活体文本（投影变则文本变），故不能以文本相等作为判据；标记走唯一写口
`bookkeeping.note`（相位禁直写 `process_notes`）。重复进入（同 run 回炉）＝**无操作**，不重复
追加链尾、不重复标记。
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from appv2.runtimev2.bookkeeping import append_contract, append_message, note
from appv2.runtimev2.prompts import RECOMMENDATION_TEMPLATE, assemble_task_book
from appv2.runtimev2.state import RunState
from appv2.runtimev2.understanding.constants import (
    PHASE,
    PROGRAM_CANDIDATE_EMPTY,
    PROGRAM_CANDIDATE_SEP,
    ROLE_USER,
    TASK_BOOK_NOTE_DIGEST,
    TASK_BOOK_NOTE_TITLE,
)
from appv2.tools import subject_candidates, term_candidates


def _projection(state: RunState) -> Mapping[str, Any]:
    """台账投影（缝缺省归一空投影——`None`／旧形按空投影计，同 `roster` 缝缺省口径）。"""
    dump = state.ledger_dump
    return dump if isinstance(dump, Mapping) else {}


def _listing(names: Iterable[str]) -> str:
    """候选展示形：顿号串；空＝「无」（票面逐字「空＝无」）。"""
    return PROGRAM_CANDIDATE_SEP.join(names) or PROGRAM_CANDIDATE_EMPTY


def program_candidates(state: RunState) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """程序预识别候选面（主体, 术语）——`tools` 包根取件（R6：本块不直引引擎）。

    零模型、零 I/O 的确定性抽取（真源＝`tools.subject_terms`）；空投影＝两空元组（不崩、
    不编造）。同一 state 两跑逐字相等（纯函数）。
    """
    dump = _projection(state)
    return subject_candidates(state.question, dump), term_candidates(state.question, dump)


def recommendation_line(state: RunState) -> str:
    """环境块「程序预识别」推荐行（V2-82a 逐字稿模板 ＋ 程序候选值）。

    文本字面单点在 `prompts`（`RECOMMENDATION_TEMPLATE`）、本块只填值；候选全空时渲染
    「主体候选：无；术语候选：无」（**行仍在场**——「程序没识别到」本身是给模型的信
    息，且模型与程序的分歧留痕以同一评价面为准）。
    """
    subjects, terms = program_candidates(state)
    return RECOMMENDATION_TEMPLATE.format(
        subjects=_listing(subjects), terms=_listing(terms)
    )


def task_book(state: RunState, *, watermark: str = "") -> str:
    """任务书装配（数据区〔含推荐行〕＋题干段）——委托 `prompts.assemble_task_book` 单点
    （行为 1／2）。

    **2026-10-17 V2-82a**：数据区尾并入「程序预识别」推荐行（本块拼值——经 `tools` 包根调
    `subject_candidates`／`term_candidates`，R6 合规：理解相位不直引 `anchors`）。

    纯文本进出、确定性：同 `state` 投影与同注入水位两次装配逐字相等；`state` 零写入。
    """
    return assemble_task_book(
        state, watermark=watermark, recommendation=recommendation_line(state)
    )


def task_book_assembled(state: RunState) -> bool:
    """本 run 是否已装配任务书（行为 9 的判据面）——过程档案标记条目在场即真。

    结构化存在性判定（零语义）：只按标记条目的 `title` 相等比对；条目形（旧检查点残形）非映射
    者一律不计（不抛错、不猜）。
    """
    for entry in state.process_notes:
        if isinstance(entry, Mapping) and entry.get("title") == TASK_BOOK_NOTE_TITLE:
            return True
    return False


def ensure_task_book(state: RunState, *, watermark: str = "") -> str | None:
    """每 run 只装配一次（行为 9）：首次 → 装配并追加链尾（＋过程档案标记）；重复 → 无操作。

    追加走唯一写口 `bookkeeping.append_message`（钉 `pin-22` 的写入点单点面）；标记走
    `bookkeeping.note`（任务书一次性）与 `bookkeeping.append_contract`（相位合同标记，V2-134）。
    返回值＝本次装配的文本（未装配＝`None`）——调用方可据此断言「只装配一次」的机读面
    （`None` ＝ 本次未装配）。

    **2026-10-19 V2-134（承载位回链）**：本函数追加的 user 条**含规章段**（`task_book` 已并入
    指令区＋输出契约区，见 `prompts.assemble_task_book`）；**链首背景块**（`system` 条）仍不在此挂
    ——真链首由编排建链时落（`orchestration` 的 run 播种面在题面 user 条**之前**挂背景块，每链恰
    一条；本函数也能被追问链复用，此处再挂即重复）。
    """
    if task_book_assembled(state):
        return None
    book = task_book(state, watermark=watermark)
    append_message(state, role=ROLE_USER, content=book)
    append_contract(state, PHASE)
    note(state, phase=PHASE, title=TASK_BOOK_NOTE_TITLE, digest=TASK_BOOK_NOTE_DIGEST)
    return book
