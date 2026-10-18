"""orchestration.repair —— 核验失败动作＝**回炉修复**（V2-115；程序只检测、模型改写）。

真源＝`tickets/v2/V2-115-核验失败动作回炉修复.md`（含末尾「Kimi 评审修正」）＋
`docs/runtime-refactor/design/统筹方案-核验澄清评测.md` §2.2。落点纪律（Kimi 修正 1）：
**回炉归编排侧**（本模块＋`INTENT_REPAIR`，镜像 V2-96 explore 环）；`verification` 只检测与标红
（R8 零 LLM 红线不破——本模块经 `bookkeeping.call_model` 单点发起，不直引模型出口）。

一次回炉的固定序（票面任务 1–5）：

1. **检测（程序，零语义）**：`verification.detect_intended(state)`（判据单点＝`_verify_lines`，
   与核验面同一份）标出问题行——**不删**；
2. **回炉（LLM，语义）**：把「问题行＋本轮窗内正确材料」作为一次修复请求发模型，要求**只重写
   这些行**：改引标／改写成「本轮材料未覆盖」／删除该行；不得新增窗内无据的数值（`_rewrite_round`）；
3. **复检（程序）**：应用后同点再检测（`recheck`）；改写轮数到顶（`MAX_REPAIR_ROUNDS`）仍不过 ⇒
   模型输出**缺位说明**（`_gap_round`——不许程序删成空白）；说明自身仍无据／为空 ⇒ 正文置空，
   交 `verification` 的**零交付兜底**（程序确定性诚实说明，插入点在收口 `join` 之前）；
4. **留痕**：回炉请求／模型返回／复检结果全落**回炉步** payload（`kind=verify`，标题「核验回炉」；
   含逐行原句）——帧面零新增（Kimi 修正 2：SSE step 帧恰三键不动）。

**终止性**：改写轮每入一次 `repair_rounds += 1`，故至多 `MAX_REPAIR_ROUNDS` 次；到顶后的缺位说明轮
产出**确定性无标红**正文（模型说明干净则用之，脏／空则置空交核验兜底）⇒ 复检必过、核验收 `answer`。
本模块不判 failed、不删行、不新增帧型。
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from appv2.runtimev2.answering import answer_anchors
from appv2.runtimev2.bookkeeping import call_model, note, record_step, set_intent
from appv2.runtimev2.context import DEFAULT_MAX_OBSERVATIONS, render_materials
from appv2.runtimev2.orchestration.constants import (
    PAYLOAD_REPAIR_RECHECK_KEY,
    PAYLOAD_REPAIR_REQUEST_KEY,
    PAYLOAD_REPAIR_RESPONSE_KEY,
    PAYLOAD_REPAIR_ROUNDS_KEY,
)
from appv2.runtimev2.prompts import (
    REPAIR_SYSTEM_CONTRACT,
    assemble_repair_gap_prompt,
    assemble_repair_prompt,
)
from appv2.runtimev2.state import INTENT_VERIFY, MAX_REPAIR_ROUNDS, STEP_VERIFY, RunState
from appv2.runtimev2.verification import RewriteRecord, detect_intended

# 过程档案相位标记与回炉步标题（本块自有文案；步型引 `state.STEP_VERIFY` 真源）。
REPAIR_PHASE = "repair"
REPAIR_STEP_TITLE = "核验回炉"

# 模型调用归因桶（V2-125）：回炉轮**自有桶** `repair`——字面真源＝`bookkeeping` 归因桶闭世界
# （`appv2/runtimev2/bookkeeping/constants.py::CALLER_REPAIR`，本块不引其常量模块＝同四相位
# 先例）。此前复用 `answer` 桶 ⇒ 归因面把回炉调用与作答调用混作一桶（`counts()`／calllog
# 无法分开），本票立第四桶后回炉调用归因可辨（步型仍 `verify`）。
MODEL_CALLER = "repair"

# 回炉应答动作闭世界（两值——协议形，非语义词表）。
REPAIR_ACTION_REWRITE = "rewrite"
REPAIR_ACTION_DROP = "drop"
REPAIR_ACTIONS: frozenset[str] = frozenset({REPAIR_ACTION_REWRITE, REPAIR_ACTION_DROP})

# 回炉请求面文案（**V2-125 起迁 `prompts/`**——合同常量三件落 `prompts/constants.py` 族
# `repair_request`、携槽模板三件＋两装配函数落 `prompts/repair_round.py`；本模块只引不复制，
# 材料段由 `context.render_materials` 渲染后作 `materials_text` 注入）。


def run_repair(
    state: RunState,
    *,
    max_observations: int = DEFAULT_MAX_OBSERVATIONS,
    execution_date: str = "",
) -> dict[str, Any]:
    """回炉一步（编排节点入口）：检测 → （改写轮 ｜ 缺位说明轮）→ 复检 → 留痕 → 意图回 `verify`。

    改写轮（`state.repair_rounds < MAX_REPAIR_ROUNDS`）：发回炉请求、只重写标红行、`+1`、复检；
    缺位说明轮（到顶）：发缺位说明请求、应用（脏／空则置空交核验兜底）。两轮末一律
    `set_intent(INTENT_VERIFY)`——复检重入核验节点（判据单点复用，零第二份）。
    无标红（复检通过后误入）＝零动作，直接回 `verify` 收口。
    `execution_date`（V2-123）＝执行日时间量注入值（材料段「执行日」段＋期错位注记；
    缺省空串＝零漂移）。
    """
    flagged = detect_intended(state)
    if not flagged:
        set_intent(state, INTENT_VERIFY)
        return {}
    positions = _flagged_positions(state, flagged)
    if len(positions) != len(flagged):  # 行号映射失配（草稿与检测面不同源）＝本步零动作
        set_intent(state, INTENT_VERIFY)
        return {}
    if state.repair_rounds < MAX_REPAIR_ROUNDS:
        face = _rewrite_round(
            state,
            flagged,
            positions,
            max_observations=max_observations,
            execution_date=execution_date,
        )
    else:
        face = _gap_round(
            state,
            flagged,
            max_observations=max_observations,
            execution_date=execution_date,
        )
    _record_repair(state, face)
    set_intent(state, INTENT_VERIFY)
    return face


def _rewrite_round(
    state: RunState,
    flagged: Sequence[RewriteRecord],
    positions: Sequence[tuple[int, RewriteRecord]],
    *,
    max_observations: int,
    execution_date: str = "",
) -> dict[str, Any]:
    """改写轮：回炉请求 → 应用（只动标红行）→ `repair_rounds += 1` → 复检 → 留痕面。"""
    prompt = assemble_repair_prompt(
        [record.line for record in flagged],
        materials_text=_materials_text(
            state, max_observations=max_observations, execution_date=execution_date
        ),
    )
    raw = call_model(
        state,
        MODEL_CALLER,
        [{"role": "user", "content": prompt}],
        system=REPAIR_SYSTEM_CONTRACT,
    )
    actions = _parse_repair_actions(raw)
    lines = str(state.draft or "").split("\n")
    applied = _apply_actions(lines, positions, actions)
    state.draft = "\n".join(applied)
    state.repair_rounds += 1
    recheck = detect_intended(state)
    return _face(
        state,
        mode="rewrite",
        lines=[record.line for record in flagged],
        prompt=prompt,
        raw=raw,
        parsed=bool(actions),
        applied=[
            {"index": index, "action": actions[index][0], "text": actions[index][1]}
            for index in sorted(actions)
        ],
        recheck=recheck,
    )


def _gap_round(
    state: RunState,
    flagged: Sequence[RewriteRecord],
    *,
    max_observations: int,
    execution_date: str = "",
) -> dict[str, Any]:
    """缺位说明轮（改写到顶）：模型写缺位说明；说明自身无据／为空 ⇒ 置空交核验零交付兜底。

    「不许程序删成空白」的落点＝核验侧兜底（`verification.forced_gap_statement`——程序确定性
    诚实说明在收口 `join` 之前追加）；本轮的「置空」只是把交付面交给那个单点，不落空答。
    """
    prompt = assemble_repair_gap_prompt(
        state.repair_rounds,
        [record.line for record in flagged],
        materials_text=_materials_text(
            state, max_observations=max_observations, execution_date=execution_date
        ),
    )
    raw = call_model(
        state,
        MODEL_CALLER,
        [{"role": "user", "content": prompt}],
        system=REPAIR_SYSTEM_CONTRACT,
    )
    statement = raw.strip()
    state.draft = statement
    recheck = detect_intended(state)
    if not statement or recheck:
        state.draft = ""  # 交核验零交付兜底（程序确定性诚实说明）
        recheck = []
    return _face(
        state,
        mode="gap",
        lines=[record.line for record in flagged],
        prompt=prompt,
        raw=raw,
        parsed=bool(statement),
        applied=[statement] if statement else [],
        recheck=recheck,
    )


def _face(
    state: RunState,
    *,
    mode: str,
    lines: Sequence[str],
    prompt: str,
    raw: str,
    parsed: bool,
    applied: Sequence[Any],
    recheck: Sequence[RewriteRecord],
) -> dict[str, Any]:
    """回炉步 payload（四 additive 键——真源 §2.2；含逐行原句／模型原话／复检逐条）。"""
    return {
        PAYLOAD_REPAIR_ROUNDS_KEY: state.repair_rounds,
        PAYLOAD_REPAIR_REQUEST_KEY: {
            "mode": mode,
            "lines": list(lines),
            "prompt": prompt,
        },
        PAYLOAD_REPAIR_RESPONSE_KEY: {
            "raw": raw,
            "parsed": parsed,
            "applied": list(applied),
        },
        PAYLOAD_REPAIR_RECHECK_KEY: [
            {"line": record.line, "reason": record.reason} for record in recheck
        ],
    }


def _record_repair(state: RunState, face: Mapping[str, Any]) -> None:
    """回炉步落账（步＋过程档案；帧面零新增——step 帧恰三键由编排发射点照常发）。"""
    record_step(state, kind=STEP_VERIFY, title=REPAIR_STEP_TITLE, payload=dict(face))
    request = face.get(PAYLOAD_REPAIR_REQUEST_KEY) or {}
    note(
        state,
        phase=REPAIR_PHASE,
        title=f"核验回炉：第 {face.get(PAYLOAD_REPAIR_ROUNDS_KEY)} 轮（{request.get('mode')}）",
        digest=json.dumps(
            {
                "mode": request.get("mode"),
                "lines": len(request.get("lines") or ()),
                "recheck": len(face.get(PAYLOAD_REPAIR_RECHECK_KEY) or ()),
            },
            ensure_ascii=False,
        ),
    )


def _flagged_positions(
    state: RunState, flagged: Sequence[RewriteRecord]
) -> list[tuple[int, RewriteRecord]]:
    """标红记录 → 草稿**行号**映射（按出现序配对；同句重复逐个消费——确定性零猜）。

    检测面（`_verify_lines`）返回的原句与草稿逐字同源（同一 `str(state.draft)`），故按
    「草稿行序 × 记录原句」配对即可；配不满（缺记录）由调用方判零动作。
    """
    lines = str(state.draft or "").split("\n")
    remaining = list(flagged)
    positions: list[tuple[int, RewriteRecord]] = []
    for index, line in enumerate(lines):
        for record in remaining:
            if record.line == line:
                positions.append((index, record))
                remaining.remove(record)
                break
    return positions


def _apply_actions(
    lines: Sequence[str],
    positions: Sequence[tuple[int, RewriteRecord]],
    actions: Mapping[int, tuple[str, str]],
) -> list[str]:
    """只动标红行：`rewrite` 换整行／`drop` 删该行；无动作的行**一字不动**（保序）。"""
    out: list[str | None] = list(lines)
    for order, (line_index, _record) in enumerate(positions, start=1):
        entry = actions.get(order)
        if entry is None:
            continue
        action, text = entry
        out[line_index] = None if action == REPAIR_ACTION_DROP else text
    return [line for line in out if line is not None]


def _parse_repair_actions(raw: str) -> dict[int, tuple[str, str]]:
    """回炉应答解析：`{index: (action, text)}`——不合形＝空映射（不猜、不兜底；复检照咬）。"""
    obj = _json_object(raw)
    if obj is None:
        return {}
    items = obj.get("lines")
    if not isinstance(items, list):
        return {}
    actions: dict[int, tuple[str, str]] = {}
    for item in items:
        if not isinstance(item, Mapping):
            continue
        index = item.get("index")
        action = item.get("action")
        if not isinstance(index, int) or isinstance(index, bool) or index < 1:
            continue
        if action not in REPAIR_ACTIONS:
            continue
        text = item.get("text")
        if action == REPAIR_ACTION_REWRITE:
            if not isinstance(text, str) or not text.strip():
                continue
            actions[index] = (action, text.strip())
        else:
            actions[index] = (action, "")
    return actions


def _json_object(raw: str) -> dict[str, Any] | None:
    """从严到宽取回一个 JSON 对象（整串 → 首 `{` 至末 `}` 子串）；取不到＝`None`（零猜）。"""
    text = raw.strip()
    candidates = [text]
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        candidates.append(text[start : end + 1])
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except (TypeError, ValueError):
            continue
        if isinstance(value, dict):
            return value
    return None


def _materials_text(
    state: RunState, *, max_observations: int, execution_date: str = ""
) -> str:
    """本轮窗内材料段（渲染单点＝`context.render_materials`；锚＝`answer_anchors` 同源）。

    `execution_date`（V2-123）＝执行日时间量注入值（材料头「执行日」段＋期错位注记；
    缺省空串＝零漂移）。
    """
    text, _meta = render_materials(
        list(state.observations),
        max_observations=max_observations,
        anchors=answer_anchors(state),
        execution_date=execution_date,
    )
    return text
