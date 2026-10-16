"""tool_matching 单入口：模型提议 → 程序闭世界对账 → `ToolPlan`｜`ToolMatchRejection`。

真源＝`specs/tool_matching.md`（已定稿）行为 1–5／11 与「不降级与静默禁令」节；卡
`specs/modules.md` `## tool_matching`（单入口 `match`）。分工一句话：**模型只提议，程序只对账**
（存在性／一致性／枚举三类结构判定），**绝不替模型选工具**（行 10 的 AST 机检面）。

一次 `match` 的固定序（与 V1 节点同构，承载位换、语义不变）：

1. **取问题组**（`state.question_group`——上游澄清相位产物）：缺组＝上游契约违例 → fail-closed 抛错
   （不猜、不静默跳过）；逐支 id 只作闭合世界比对面，`parse_tool_match` 只用 id；
2. **装配本轮指令**（文本单点在 `prompts`）：首入＝`assemble_decision_package`（相位包），
   回炉＝`assemble_decision_increment`（拒因回喂行＋已做段）；经唯一写口 `append_message`
   **链尾追加**（pin-22：只追加、不改写、相邻调用互为前缀延伸），首入并 `append_contract`
   标记相位合同（pin-24：回炉轮不重发）。§A 指南段与常驻台账段的文本经 `prompts` 的**注入面**
   传入——该注入面不在本块签名上（`match(state)`），本块按契约以**缺位形**装配（段缺位、
   不降级），注入归属见本票回报登记；
3. **调模型**：`bookkeeping.call_model(state, "decision", messages)`——**单点发起面**，本块不直引
   `gateway_adapter`、不建客户端（「无旁路」）；模型调用步记录由 `call_model` **统一记账**，
   本块不为同一调用重复记步；
4. **解析＋对账**：`parsing.parse_tool_match`（schema 收口单点）→ 不合格＝拒因正文（`str`）→
   `_rejection_from_parse` **机械适配**（`str` 逐字进 `reason` ＋映射 `kind`；行为 11）；
   合格 → 追加密集级校验（`mention_mode` 闭世界／`metric_slot` 英文列名形／`ranking` 与
   `direction` 同现与取值／`anchors` 形态）；
5. **定案**：`retrieval_need` **原样透传**（`question`／`anchors`／`family_hints` 全键——键形照
   `RetrievalNeed` 消费面）＋按 V2-50 族 C ① 注入**确定性锚**（`tools.inject_retrieval_anchors`：
   模型已填锚不被覆盖、缺锚按题面实体补）；注入随定案载荷承载（成功路径**零补记步**——
   留痕面＝`ToolPlan.matches[].retrieval_need`，同 `caliber_key` 承载口径）；
6. **失败**：落**机读信号**（step payload 拒因字段 ＋ notice——「不降级」节）后返回
   `ToolMatchRejection` 交 `orchestration` 回喂重配（**不自动修补**）。

**合法降级路径＝无**；本块零状态直写（写面全经 `bookkeeping` 唯一写口）、零事件发射（发帧归
`transport`／批次协调归 `orchestration`）、零引擎接触（只经 `tools` 公开面——锚注入件
`inject_retrieval_anchors` 即该公开面一件：锚解析单点在 `appv2/tools/anchors.py`，本块不自立
第二套词面／正则）。

**行为 9（熔断暂不加）**：拒因回喂自环靠**轮数闸**兜底——本块**不计数、不判轮、不写字面限额**；
限额数值只引**真源双指** `docs/runtime-refactor/recon/K-上下文事件指南预算.md` R-K-72…R-K-78
＋`docs/runtime-refactor/walk/裁决表.md` §06-A（判定与计数归 `state`／`orchestration`）。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from appv2.runtimev2.bookkeeping import (
    append_contract,
    append_message,
    call_model,
    notice,
    record_step,
)
from appv2.runtimev2.parsing import (
    QuestionGroup,
    Subtask,
    extract_plan_json,
    parse_tool_match,
)
from appv2.runtimev2.parsing import SubtaskMatch as ParsedMatch
from appv2.runtimev2.persistence import STEP_STATUS_FAILED
from appv2.runtimev2.prompts import assemble_decision_increment, assemble_decision_package
from appv2.runtimev2.state import STEP_DECISION, RunState
from appv2.runtimev2.tool_matching.constants import (
    DATA_CHAIN,
    DIRECTIONS,
    KIND_ENUM_OUT_OF_RANGE,
    KIND_MISSING_REQUIRED,
    MENTION_MODES,
    MODEL_CALLER,
    NOTICE_DECISION_REJECTED,
    PAYLOAD_KIND_KEY,
    PAYLOAD_PHASE_KEY,
    PAYLOAD_REASON_KEY,
    PAYLOAD_REJECTION_KEY,
    PHASE,
    REJECTION_KIND_BY_MARK,
    ROLE_ASSISTANT,
    ROLE_USER,
)
from appv2.runtimev2.tool_matching.models import (
    MatchReason,
    SubtaskMatch,
    ToolMatchRejection,
    ToolPlan,
)
from appv2.tools import inject_retrieval_anchors


def match(
    state: RunState, *, guide_text: str = "", shared_context: bool = True
) -> ToolPlan | ToolMatchRejection:
    """工具匹配相位单入口（签名真源＝卡 `## tool_matching`）。

    返回**两态互斥**：`ToolPlan`（恰配一条全部合格）｜`ToolMatchRejection`（结构化拒因，非终局）。
    无半成品、无「疑似」形；上游缺组等契约违例＝抛错（fail-closed），不返回哨兵。

    `guide_text`＝§A 指南段**文本注入参**（流水 63——additive 注入，编排面按启动快照注入全文；
    缺省空串＝空段头，回归面同形）。装载面归 `api` 组合根（`OntologyGuideProvider`
    启动取一次快照，同 `watermark` 先例），本块只下传、不读文件。

    `shared_context`＝**run 级共享上下文**（§A 指南段＋台账常驻块）本次是否注入（缺省 `True`＝
    函数本体行为）：判定归 `orchestration`（同一 run 只注一次，挂澄清轮首入包——本相位是同一 run
    的第二次决策装配，故编排面通常下传 `False`），本块只下传、不自行判定。
    """
    group = _question_group_of(state)
    _append_round_instruction(
        state, guide_text=guide_text, shared_context=shared_context
    )
    content = call_model(state, MODEL_CALLER, list(state.messages))
    append_message(state, role=ROLE_ASSISTANT, content=content)

    parsed = parse_tool_match(content, group)
    if isinstance(parsed, str):
        return _reject(state, _rejection_from_parse(parsed))

    reconciled = _reconcile(content, parsed)
    if isinstance(reconciled, ToolMatchRejection):
        return _reject(state, reconciled)
    return ToolPlan(matches=list(reconciled))


# ── 问题组（上游产物面）───────────────────────────────────────────────────────


def _question_group_of(state: RunState) -> QuestionGroup:
    """从状态投影取问题组（上游澄清相位产物）；缺组／缺 id ＝上游契约违例 → 抛错。

    本块**不产子问题**（归 `clarification`）：这里只把状态投影定形成解析面所需的组，逐支 id 是
    闭合世界比对面；`question`／`ledger_notes` 原样随形（本块零改写、零补齐）。
    """
    payload = state.question_group
    raw_subtasks = payload.get("subtasks") if isinstance(payload, Mapping) else None
    if not isinstance(raw_subtasks, list) or not raw_subtasks:
        raise ValueError(
            "工具匹配缺问题组（state.question_group 无 subtasks——上游澄清相位未产组）："
            "fail-closed，不猜、不跳过子问题"
        )
    subtasks: list[Subtask] = []
    for item in raw_subtasks:
        if not isinstance(item, Mapping):
            raise ValueError(f"问题组支须为对象（state.question_group.subtasks）：{item!r}")
        subtask_id = str(item.get("id") or "").strip()
        if not subtask_id:
            raise ValueError("问题组支缺 id（闭合世界比对面必填）")
        subtasks.append(
            Subtask(
                id=subtask_id,
                question=str(item.get("question") or ""),
                ledger_notes=str(item.get("ledger_notes") or ""),
            )
        )
    return QuestionGroup(subtasks=tuple(subtasks))


# ── 本轮指令装配（文本单点在 prompts；链尾追加与合同标记经唯一写口）────────────


def _append_round_instruction(
    state: RunState, *, guide_text: str = "", shared_context: bool = True
) -> None:
    """首入＝相位包（一次性，pin-24）／回炉＝增量条（拒因回喂行＋已做段）；链尾追加（pin-22）。

    `guide_text` 只对首入包有意义（增量条无 §A 段）——装载面归 `api` 组合根，本块只下传。
    `shared_context`＝run 级共享上下文（§A 指南段＋台账常驻块）本次是否注入——判定归编排
    （同一 run 只注一次），本块只下传（缺省 `True`＝函数本体行为）。
    """
    first_entry = PHASE not in state.contracts_appended
    instruction = (
        assemble_decision_package(
            state, phase=PHASE, guide_text=guide_text, shared_context=shared_context
        )
        if first_entry
        else assemble_decision_increment(state, phase=PHASE)
    )
    if instruction:
        append_message(state, role=ROLE_USER, content=instruction)
    if first_entry:
        append_contract(state, PHASE)


# ── 解析拒文 → 结构化拒因（消费方；行为 11）───────────────────────────────────


def _rejection_from_parse(reason: str) -> ToolMatchRejection:
    """解析面 `str` 拒文 → 结构化拒因：**机械适配，零语义判断**（行为 11）。

    `str` **逐字**进 `reason` 字段；`kind` 由 `REJECTION_KIND_BY_MARK`（逐字拒文子串表）机械映射。
    映射表未覆盖＝解析面拒文集合漂移 → fail-closed 抛错（不猜 kind、不静默归兜底）。
    """
    for mark, kind in REJECTION_KIND_BY_MARK.items():
        if mark in reason:
            return ToolMatchRejection(reasons=[MatchReason(kind=kind, reason=reason)])
    raise ValueError(f"解析面拒文未在拒因映射表内（映射面须随解析面拒文集合同步）：{reason!r}")


# ── 加密集对账（本块追加面）──────────────────────────────────────────────────


def _reconcile(
    content: str, parsed: Sequence[ParsedMatch]
) -> tuple[SubtaskMatch, ...] | ToolMatchRejection:
    """解析面已受（逐支合格）后的**闭世界一致性判定**：按 id 逐支复核并定型。

    解析面管 schema 与支内必填；本处只补规格点名的加密集面（`mention_mode` 闭世界、
    `metric_slot` 英文列名形、`ranking`／`direction` 同现与取值、`anchors` 形态）——
    判据全是结构判定（存在性／类型／闭世界成员），**零词表零语义**。
    """
    payload = extract_plan_json(content)
    raw_matches = payload.get("matches") if isinstance(payload, Mapping) else None
    if not isinstance(raw_matches, list):
        raise ValueError("对账失序：解析面已受支，原始载荷却取不到 matches 列表")
    raw_by_id: dict[str, Mapping[str, Any]] = {}
    for item in raw_matches:
        if isinstance(item, Mapping):
            raw_by_id[str(item.get("id") or "").strip()] = item

    matches: list[SubtaskMatch] = []
    for item in parsed:
        raw = raw_by_id.get(item.id)
        if raw is None:
            raise ValueError(f"对账失序：解析面支 {item.id!r} 在原始载荷中缺失")
        violation = _violation_of(item, raw)
        if violation is not None:
            return ToolMatchRejection(reasons=[violation])
        matches.append(_build_match(item, raw))
    return tuple(matches)


def _violation_of(item: ParsedMatch, raw: Mapping[str, Any]) -> MatchReason | None:
    """逐支加密集校验：首违即返（fail-fast——V1 同款；一条拒因足够回喂重配）。"""
    mention = raw.get("mention_mode")
    mention_text = mention.strip() if isinstance(mention, str) else ""
    if not mention_text:
        return MatchReason(
            kind=KIND_MISSING_REQUIRED,
            reason=(
                f"matches {item.id} 缺 mention_mode"
                "（「提及 vs 执行」结论——须给 executed／mentioned_only）"
            ),
        )
    if mention_text not in MENTION_MODES:
        return MatchReason(
            kind=KIND_ENUM_OUT_OF_RANGE,
            reason=(
                f"matches {item.id} mention_mode 越界（executed/mentioned_only）：{mention_text!r}"
            ),
        )

    if item.chain == DATA_CHAIN:
        plan = item.plan or {}
        slot = str(plan.get("metric_slot") or "").strip()
        if _is_ascii_identifier_form(slot):
            return MatchReason(
                kind=KIND_MISSING_REQUIRED,
                reason=(
                    f"matches {item.id} plan metric_slot 呈英文列名形（须写现行口径名）：{slot!r}"
                ),
            )
        ranking = plan.get("ranking")
        if not isinstance(ranking, bool):
            return MatchReason(
                kind=KIND_MISSING_REQUIRED,
                reason=f"matches {item.id} plan 缺 ranking（必填布尔）：{ranking!r}",
            )
        direction = plan.get("direction")
        if ranking and direction is None:
            return MatchReason(
                kind=KIND_MISSING_REQUIRED,
                reason=(
                    f"matches {item.id} plan ranking/direction 同现缺"
                    "（排名题 true 须同时给 direction）"
                ),
            )
        if direction is not None:
            direction_text = direction.strip() if isinstance(direction, str) else str(direction)
            if direction_text not in DIRECTIONS:
                return MatchReason(
                    kind=KIND_ENUM_OUT_OF_RANGE,
                    reason=(
                        f"matches {item.id} plan direction 越界（asc/desc）：{direction_text!r}"
                    ),
                )
        return None

    raw_need = item.retrieval_need or {}
    anchors = raw_need.get("anchors")
    if anchors is None:
        return None
    if not isinstance(anchors, list) or not all(isinstance(anchor, str) for anchor in anchors):
        return MatchReason(
            kind=KIND_MISSING_REQUIRED,
            reason=f"matches {item.id} retrieval_need anchors 须为字符串数组：{anchors!r}",
        )
    return None


def _build_match(item: ParsedMatch, raw: Mapping[str, Any]) -> SubtaskMatch:
    """按链定型：`plan` 与 `retrieval_need` **逐字段原样透传**（「出数只认现行口径」＋「检索参数
    不缩水」的结构约束落点）。

    形态单点归位（P-05）：`SubtaskMatch` 形状＝`parsing`（`plan`／`retrieval_need` 以映射承载、
    `caliber_key` 空串形）；本处只把模型原话的两个结论（`mention_mode`／`caliber_key`）定型填入，
    闭世界把守见 `_violation_of`（消费面拒因面）。

    `retrieval_need` 逐键原样透传（`question`／`anchors`／`family_hints`——键形照
    `appv2/retrieval/domain.py` 的 `RetrievalNeed` 消费面，不改键名、不裁键）——**旧实现只重建
    `question`／`anchors` 两键，模型发的 `family_hints` 被丢弃**（L3-02 病灶 A：族配额退化成每族
    1 席、gold 章被裁；`docs/runtime-refactor/ladder/L3/02-完井液在二开钻进段与三开-*`）。透传后
    并接 V2-50 族 C ① **确定性锚注入**（模型已填锚不覆盖、缺锚按题面实体补；注入项随定案载荷
    承载——**成功路径零补记步**：留痕面＝返回值 `ToolPlan.matches[].retrieval_need`，落
    `state.tool_matches` 后与批量执行输入面同源零漂移）。
    """
    mention = raw.get("mention_mode")
    plan: dict[str, Any] | None = None
    need: dict[str, Any] | None = None
    if item.chain == DATA_CHAIN:
        plan = dict(item.plan or {})
    else:
        # 原样透传（整 dict 副本，不改键名、不裁键）＋确定性锚注入（返回副本）。
        need = inject_retrieval_anchors(dict(item.retrieval_need or {}))
    return SubtaskMatch(
        id=item.id,
        tool=item.tool,
        chain=item.chain,
        plan=plan,
        retrieval_need=need,
        caliber_key=item.caliber_key,
        mention_mode=str(mention).strip(),
    )


def _is_ascii_identifier_form(value: str) -> bool:
    """「英文列名形」判定（形态判定，只判形状不判语义——行为 4，Owner 2026-10-15 拍板 B 案）。

    判定形＝值整体呈 ASCII 标识符形：首字符 `[A-Za-z]`、其余仅 `[A-Za-z0-9_]`，**大小写都咬**；
    禁例 `oil_pressure`／`WELL_NAME`。fail-closed：宁可误拒重提议，不可漏放列名形。
    空值不归本判定（空＝必填缺，归解析面拒文）。
    """
    if not value:
        return False
    first = value[0]
    if not (("A" <= first <= "Z") or ("a" <= first <= "z")):
        return False
    for char in value[1:]:
        if char == "_" or ("0" <= char <= "9") or ("A" <= char <= "Z") or ("a" <= char <= "z"):
            continue
        return False
    return True


# ── 机读信号（「不降级与静默禁令」节：step payload 拒因字段 ＋ notice）──────────


def _reject(state: RunState, rejection: ToolMatchRejection) -> ToolMatchRejection:
    """失败落地机读信号后原样返回拒因（非终局——回喂重配归 `orchestration`）。"""
    for reason in rejection.reasons:
        record_step(
            state,
            kind=STEP_DECISION,
            title=f"工具匹配被拒（{reason.kind}）",
            status=STEP_STATUS_FAILED,
            payload={
                PAYLOAD_PHASE_KEY: PHASE,
                PAYLOAD_REJECTION_KEY: {
                    PAYLOAD_KIND_KEY: reason.kind,
                    PAYLOAD_REASON_KEY: reason.reason,
                },
            },
        )
        notice(
            state,
            type=NOTICE_DECISION_REJECTED,
            content=f"工具匹配发射被拒（{reason.kind}）：{reason.reason}——修正后重新输出 JSON。",
        )
    return rejection
