"""bookkeeping.ports —— 共享写口的落地（唯一入口；相位禁直写）。

真源＝`specs/bookkeeping.md` 接口定义节「共享写口（唯一入口；相位禁直写）」＋行为 2–10。
本模块是**全节点共享可变写面的唯一定义点**：步记录与序号（`record_step`／`next_seq`）、
对话链（`append_message`）、对话层（`append_dialogue`）、过程档案（`note`）、通知（`notice`）、
路由意图（`set_intent`）、合同标记（`append_contract`）——这些字段的写操作在 `appv2/runtimev2`
内**只允许出现在本模块对应函数里**（机检＝`tests/domains/test_v2_bookkeeping.py::single_write_port`
＋ `::no_direct_state_write_in_phases`；写入点单点面＝钉 `pin-22`，写入面＝`pin-22`／`pin-24`／
`pin-26`）。

闭世界取值一律**引真源、不复述**（越界一律抛错＝fail-closed，**合法降级路径＝无**）：步类型
`state.STEP_KINDS`、步状态 `persistence.STEP_STATUS_KINDS`、路由意图 `state.INTENT`、对话层来源
`state.DIALOGUE_ORIGINS`（＋来源↔角色不变量 `state.DIALOGUE_ORIGIN_ROLES`）、通知类型
（`transport.NOTICE_TYPES`）、触界闸名（`state.LIMIT_KINDS`——`LimitHit.limit` 七限额键名）、
对话链角色与合同追加相位与过程档案上限（本块自有，见 `constants`）。

依赖面（规格「框架与依赖红线」）：本模块（写口面）**运行逻辑只依赖 `state`**；`persistence` 只借
**类型与常量形状**（不落盘）——本模块不写库、不写文件、不发帧、不调模型、无词表判定。模型出口的
发起面在 `closing.call_model`（模型只经 `gateway_adapter`）。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast

from appv2.runtimev2.bookkeeping.constants import (
    CONTRACT_PHASES,
    MESSAGE_ROLES,
    NOTE_DIGEST_LIMIT,
    TRUNCATION_MARK,
)
from appv2.runtimev2.persistence import (
    STEP_STATUS_DEFAULT,
    STEP_STATUS_KINDS,
    StepRecord,
)
from appv2.runtimev2.state import (
    DIALOGUE_ORIGIN_ROLES,
    DIALOGUE_ORIGINS,
    INTENT,
    LIMIT_KINDS,
    STEP_KINDS,
    Manifest,
    RunState,
)
from appv2.runtimev2.transport import NOTICE_TYPES


def _joined(values: frozenset[str]) -> str:
    """闭世界取值逐字拼接（报错文案随集合生成，不写死条数）。"""
    return "／".join(sorted(values))


def _reject(field: str, value: object, world: frozenset[str]) -> ValueError:
    """闭世界越界（fail-closed）——不吞错、不返回哨兵值、不静默降级。"""
    return ValueError(f"{field} 越界（闭世界＝{_joined(world)}）：{value!r}")


def next_seq(state: RunState) -> int:
    """步序号＝**已有步记录数 ＋ 1**（行为 2）；取号单点在 `record_step` 内部。

    调用方**禁手加偏移**（现状的手工偏移导致序号与步数可不等，重写收正）：`next_seq` 与
    `len(state.steps) + 1` 恒等，`record_step` 不接任何序号入参。
    """
    return len(state.steps) + 1


def record_step(
    state: RunState,
    *,
    kind: str,
    title: str,
    status: str = STEP_STATUS_DEFAULT,
    payload: dict[str, Any] | None = None,
    manifest: Manifest | None = None,
) -> StepRecord:
    """步记录单点（行为 3／4／5）：七字段入 `state.steps`，序号内置取号、状态如实。

    - `run_id` 自 `state.run_id` 取——**不由调用方传**；
    - `kind` ∈ `STEP_KINDS`（越界抛错）；`status` 是**显式关键词参**，闭世界 `ok`｜`failed`｜
      `refused`（越界抛错）——**由调用方如实给**：本块不猜、不从 `payload` 推断语义、**不得恒
      `ok`**（失败态必须可表达）；
    - `manifest` 非空 → `Manifest.as_dict()` 投影；为空 → 写空——**键恒在场、不省略**；
    - `payload` 原样保真：空 `{}` 照写 `{}`、缺省写缺省（**禁 `payload or {}` 式假值归一**——
      两态读回必须可区分，钉 `pin-12` 承接面）。

    返回形＝`persistence.StepRecord` 的**装配面七字段**（`run_id`／`seq`／`step`／`status`／
    `title`／`manifest`／`payload`，同序入状态）；`StepRecord.created_at` **非装配入参**、由落盘层
    盖（登记＝`docs/runtime-refactor/spec-review/persistence-回工补写.md` 上报项 2：`created_at`
    不经 `record_step` 装配），故返回值＝入状态的七键投影本体（`state.steps[-1] is 返回值`）。
    """
    if kind not in STEP_KINDS:
        raise _reject("步类型（kind）", kind, STEP_KINDS)
    if status not in STEP_STATUS_KINDS:
        raise _reject("步状态（status）", status, STEP_STATUS_KINDS)
    entry: dict[str, Any] = {
        "run_id": state.run_id,
        "seq": next_seq(state),
        "step": kind,
        "status": status,
        "title": title,
        "manifest": manifest.as_dict() if manifest is not None else None,
        "payload": payload,
    }
    state.steps.append(entry)
    return cast(StepRecord, entry)


def append_message(state: RunState, *, role: str, content: str) -> None:
    """对话链（`messages`）追加唯一入口（行为 7——钉 `pin-22` 的**写入面**）：只追加、不改写。

    `role` ∈ `user`｜`assistant`｜`system`（同 `state.messages` 口径，越界抛错）；**不替换、不重排、
    不删除既有条目**（断言＝追加 N 条后前 N-1 条逐字不变，相邻两次调用互为前缀延伸）。条目形态＝
    `{role, content}` 恰两键。**`system` 位（2026-10-17 H 批）只承载链首背景块**（每链恰一条；
    环节规章不入链——走 `call_model` 的 `system` 注入参）。
    """
    if role not in MESSAGE_ROLES:
        raise _reject("对话链角色（role）", role, MESSAGE_ROLES)
    state.messages.append({"role": role, "content": content})


def append_dialogue(state: RunState, *, role: str, content: str, origin: str) -> None:
    """对话层（`dialogue`）追加唯一入口（行为 9——钉 `pin-26` 的**写入面**）：`origin` 闭世界。

    来源闭世界＝`state.DIALOGUE_ORIGINS` 三值（越界即拒），并守**来源↔角色一致性不变量**
    （`state.DIALOGUE_ORIGIN_ROLES`）——**写入点即拒**（隔离优于过滤，张冠李戴同判失败）。

    **过程内容（任务书／指令／注记）不得经该入口**：三条合法来源都只标签自然对话，要写过程内容
    走 `note`（过程档案，有界摘要）。条目形态＝`{role, content, origin}` 恰三键。
    """
    if origin not in DIALOGUE_ORIGINS:
        raise _reject("对话层来源（origin）", origin, DIALOGUE_ORIGINS)
    expected_role = DIALOGUE_ORIGIN_ROLES[origin]
    if role != expected_role:
        raise ValueError(
            f"对话层来源↔角色不变量失配：origin={origin!r} 须配 role={expected_role!r}，"
            f"实为 {role!r}"
        )
    state.dialogue.append({"role": role, "content": content, "origin": origin})


def _bounded_digest(digest: str) -> str:
    """写入点截断（行为 10）：≤ 上限原样；超长 → 切至「上限 − 标记长」＋可见标记。

    **截断只在此处发生**（写入点是唯一边界），消费侧读到的 `digest` 恒 ≤ `NOTE_DIGEST_LIMIT`
    且截断**可见**（末字为 `TRUNCATION_MARK`）——不静默硬切片（现状 `digest[:200]` 无标记，
    `recon/B1` D-B1-16）。标记计入上限（输出 `len ≤ 上限`，同 `persistence.summary.clip` 口径）。
    """
    if len(digest) <= NOTE_DIGEST_LIMIT:
        return digest
    return digest[: NOTE_DIGEST_LIMIT - len(TRUNCATION_MARK)] + TRUNCATION_MARK


def note(state: RunState, *, phase: str, title: str, digest: str) -> None:
    """过程档案（`process_notes`）续写唯一入口（行为 10：写入点截断 `digest` ＋只追加）。

    条目形＝`{phase, title, digest}` 恰三键（现状锚＝`recon/B1` R-B1-24 与 `arch/P5b2`
    A-P5b2-03，旧码 `_note`）；`digest` 在**写入点**截断至 `NOTE_DIGEST_LIMIT`（上限真源＝
    `synth/S5` 的 `process_notes` 条目口径，本模块不复述数字）且截断可见（见 `_bounded_digest`）。

    **只追加、不改写既有条目**（同 `_notes_with` 纪律：旧列逐字不动、新条目链尾追加）——本函数
    不重排、不去重、不按任何语义过滤；`phase` 无闭世界（过程面相位标记由调用方如实给，本块**不猜**、
    不设词表——行为 18 零判断）。
    """
    state.process_notes.append(
        {"phase": phase, "title": title, "digest": _bounded_digest(digest)}
    )


def notice(
    state: RunState,
    *,
    type: str,
    gates: Sequence[str] = (),
    content: str,
) -> None:
    """通知（`notices`）追加唯一入口（行为 11：恰三键 `{type, gates, content}`＋只追加）。

    闭世界面（越界一律抛错＝fail-closed，不吞错、不静默降级、不落哨兵）：
    `type` ∈ `transport.NOTICE_TYPES`（二十九值——真源 `specs/transport.md`，本模块不复述取值）；
    `gates` ⊆ `state.LIMIT_KINDS`（`LimitHit.limit` 七限额键名——流水 52-B 裁；**逐项**把守，
    越界项全部列进报错文案）。**恰三键**由签名面即已闭合（`type`／`content` 必给、无第四参——
    缺键／多键在调用期即拒）。

    **只追加**：既有通知逐字不变；`gates` 落列时**拷贝**（调用方随后改自己的列表不影响已落条目）。
    参数顺序与语义取自 `state.check_limits` 的 `Convergence.notice`（`converge` 内部落地同形）。
    """
    if type not in NOTICE_TYPES:
        raise _reject("通知类型（type）", type, NOTICE_TYPES)
    outside = [gate for gate in gates if gate not in LIMIT_KINDS]
    if outside:
        raise _reject("触界闸名（gates）", outside, LIMIT_KINDS)
    state.notices.append({"type": type, "gates": list(gates), "content": content})


def set_intent(state: RunState, intent: str) -> None:
    """`next_intent` 的唯一写口（行为 6）：取值 ∈ `INTENT`（十值），越界即拒。

    **写字段 ≠ 做路由决策**：各相位经它给路由意图，收敛（行为 12）与直答旁路（行为 14）两处由
    本块内部写；「去哪」的决策仍在 `orchestration`（路由表读该字段并决定跳转）。空串（未设态）
    不在闭世界内——划线即拒。
    """
    if intent not in INTENT:
        raise _reject("路由意图（next_intent）", intent, INTENT)
    state.next_intent = intent


def append_contract(state: RunState, phase: str) -> None:
    """`contracts_appended` 的唯一写函数（行为 8——钉 `pin-24` 的**写入面**）：幂等、越界抛错。

    相位经它标记「合同已追加」；**已标记相位再标记＝幂等无操作**（不重复追加、不重复标记）——
    `append_message` 的调用方据此不重发合同文本（回炉轮不重发）。`phase` 越出合同追加相位闭世界
    （`decision`｜`clarify`｜`toolmatch`，见 `constants`）即抛错（fail-closed）。
    """
    if phase not in CONTRACT_PHASES:
        raise _reject("合同追加相位（phase）", phase, CONTRACT_PHASES)
    if phase in state.contracts_appended:
        return
    state.contracts_appended.append(phase)
