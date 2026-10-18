"""作答相位本体（`answer`）：材料面显式 → 起草（真流式逐段推）→ 收口（引用块＋citation 帧＋链尾）。

真源＝`specs/answering.md`（已定稿）＋卡 `specs/modules.md` `## answering`（签名以卡为准：
`answer(state) -> AnswerDraft`）。一句话：把前面查到的**全部子问题结果**整理成**一份答案**
——**一段段推给页面（真流式）**、**每句带出处**、**缺口如实交代**。

一次调用的固定序（行为 1–11；语义不变、承载位在 V2）：

1. **材料面显式**（行为 4）：材料面 Manifest 经 `context.compile_manifest` 编译（**本块只消费、
   零自取**；作答轮零常驻来源行）；材料段经 `context.render_materials` 渲染（帽为注入参数、
   数值单点仍在 `context`）；指令文本经 `prompts.assemble_answer_prompt` 装配（材料段不在装配
   输出内——调用方追加于尾）。截断态**必披露**：`material_truncated` notice 在场（未截断零通知）；
   **引擎注记段**（行为 15 的「不静默」面）：`locator.kind == notice` 的观察（台账 no_hit 等降级／
   拦停注记——`context` 材料段整体排除）由本块以**原文**追加于材料段之后（不得静默丢弃）；
2. **起草**：作答指令**动态段**（题面件＋子问题结果清单）＋材料段（＋引擎注记段）一条 user 消息
   追加链尾（`bookkeeping.append_message`）→ 经 `bookkeeping.call_model` **单点发起**模型调用
   （本块不直引 `gateway_adapter`、不直引 `appv2.infra.llm_client`、不自建模型客户端——R7 ＋
   「无旁路」行为断言）；**2026-10-17 H 批（角色分家）**：作答**规章段**（动词钉死句／【答案要求】
   ＋清单全文／术语白话表／汇总合同／起草答案合同）不入链——经 `prompts.answer_system_contract`
   走 `call_model(system=…)` 的**调用级注入参**（只随本次请求走、不用即散）；
3. **发射剥离与块剥除**（行为 11，钉 `pin-04`；行为 13）：应答**先过输入侧提取**
   （2026-10-17 V2-82g 热修：整应答恰一枚 `{"action":"finalize","answer":…}` 发射 JSON 时，
   `emission.extract_finalize_answer` 取回交付字段作草稿原文——程序接管输入侧、合同零新增；
   提取属「恢复」非「放行」），再过 `strip_emission_fences`
   （`emission` 单点），发射 JSON 不进答案面（泄漏=0）；检出即发 `emission_strip` notice（机读面）；
   随后过 `strip_placeholders`（行为 13）：字面占位引标 `[n]` 整枚离场；再过**块剥除**
   （2026-10-17 EB5c，单点＝`transport.split_block_sections`）：模型自把程序块写进草稿者按
   **块头模式族**整段离场（加粗变体同族——真机帧形 `**引用**`），血缘族段原文入 `lineage` 增补面、
   其余剥除面块段原文零留存（程序机械再生）——**text 帧发出前**正文即已干净；剥离后才是
   答案面文本（分段／发帧／落 `state.draft` 三者同源）；
4. **分段与引标**（行为 1／2／3）：草稿按空行分**段**，逐段取本段 `citation_seqs`（`[n]` 序）；
   **引标必须真实存在于观察序列**——界外引标号由 `strip_dangling_citations` 在**分段之前**整枚
   剥除（2026-10-17 EB5b：剥除族第二形，同行为 13 占位符剥除；剥除列落起草步 payload 机读键
   `dangling_citation_seqs`，不静默），**不判失败**——该行失去引标即由 `verification` 按
   「无据断言」既有处置收口（删句／结构行原样），材料照常带引标交付（`completed`）；
5. **真流式推出**（行为 1）：逐段发 `text` 帧（一段一帧）——**不是收口时一次性推全量**；模型原话
   **只进过程档案**（`bookkeeping.note` 留痕——行为 8：模型原话不进对话层），草稿另落
   `state.draft` 供核验消费；答案面步落 `payload` 的 `citations`／`gaps` 机读字段（「不降级与
   静默禁令」节）＋**降级与引用簇七键**（`_delivery_face`：行为 6／12／14／15／16 的机读面——
   `echo_flag`／`engine_notes`／`contradiction_seqs`／`engine_rows`／`delivered_rows`／
   `ranking_seqs`／`ranking_order_ok`）＋**材料面 Manifest**（见下「步面接缝」）；
6. **结构化缺口**（行为 5）：被拒子问题→`Gap(kind="refused")`、其余失败／缺料→
   `Gap(kind="missing")`、零实质材料（无非 notice 观察）→`Gap(kind="unverified")`——三档齐由
   同一确定性分派产生，**不静默截断**；空稿（剥离后）→ **不推空答案**（零 text 帧、`state.draft`
   保持空），按缺口如实收口（行为 9）；
7. **收口**（行为 7，核验后重入面）：`verdict` 在场／直答态／已有起草标记＝**收口段**——引用块
   生成、`citation` 帧逐支发射、终稿一条 assistant 消息追加链尾，**同批落定**；正文与引用块之间
   依次接**「互不一致」分源块**（行为 6）与**分源列明归属块**（行为 17）——两块由 `degradation`
   以形态判据确定性装配（不靠模型自觉、逐支原文照抄、单源／无矛盾零追加、重入幂等；重入幂等判据
   2026-10-17 EB5c 起＝**同族块头在场**〔块头模式族单点 `transport.same_family_head_in`〕，
   加粗变体同族）。`verdict`
   帧本体是**消费方信号**（批次落定归 `orchestration`，行为 7 明写），本块不产。**交付面分层
   （2026-10-17 EB3 D2）**：上述三块（分源／归属／引用）**不进正文**——按原序入 `supplements`
   增补面，`state.answer` 与链尾只留模型稿（块帧由编排层发射）。

**步面接缝（登记呈主窗）**：模型调用步由 `bookkeeping.call_model` **单点记账**（用量与归因面＋
`token_count`），本块**不为同一调用再记模型调用步**；本块的答案面步（`起草答案`／`答案收口`）
承载**材料面 Manifest**（`context.compile_manifest` 产物）与 `citations`／`gaps` 机读字段——
`call_model` 的签名（`call_model(state, caller, messages)`）无 manifest 注入面，故材料面 Manifest
只能落本块步面；该接缝为**登记项**（跨块对账面＝`specs/agent-loop.md` 行 18「每个模型调用 step
落 Manifest」）。

**接缝纪律**：`bus`（per-run 总线，编排块持有、注入各相位）为**必给**注入面——未注入＝调用方断线，
入口即 fail-closed 抛错（同 `understanding.interpret` 先例）；`max_observations`（材料帽）为注入
参数（缺省引 `context.DEFAULT_MAX_OBSERVATIONS` 单点、无裸字面）；`supplements`（增补面收集列表）
为**选给**注入面（缺省＝本块自持一份丢弃——正文剥离面与列表无关）。

**合法降级路径＝无**：闭世界越界即抛错；起草原话不完整时走结构化缺口，**不改写事实**。
"""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping
from typing import Any

from appv2.runtimev2.answering.constants import (
    CITATION_BLOCK_HEAD,
    CITATION_EVENT,
    CITATION_PAYLOAD_INDEX,
    CITATION_PAYLOAD_SOURCE,
    CITATION_PAYLOAD_SOURCE_ID,
    CITATION_PAYLOAD_TRUST,
    DRAFT_KIND_DIRECT,
    DRAFT_NOTE_TITLE,
    DRAFT_STEP_KIND,
    DRAFT_STEP_TITLE,
    EMISSION_STRIP_CONTENT,
    EMISSION_STRIP_EMPTY_CONTENT,
    EMPTY_DRAFT_REASON,
    EXPLORE_FEEDBACK_TEMPLATE,
    EXPLORE_REJECT_BODY,
    EXPLORE_STEP_TITLE,
    FINALIZE_STEP_KIND,
    FINALIZE_STEP_TITLE,
    MATERIAL_TRUNCATED_CONTENT,
    MODEL_CALLER,
    NOTICE_EMISSION_STRIP,
    NOTICE_MATERIAL_TRUNCATED,
    PAYLOAD_CITATIONS_KEY,
    PAYLOAD_CONTRADICTION_SEQS_KEY,
    PAYLOAD_DANGLING_SEQS_KEY,
    PAYLOAD_ECHO_FLAG_KEY,
    PAYLOAD_ENGINE_NOTES_KEY,
    PAYLOAD_EXPLORE_KEY,
    PAYLOAD_GAP_KIND_KEY,
    PAYLOAD_GAP_REASON_KEY,
    PAYLOAD_GAP_SUBTASK_KEY,
    PAYLOAD_GAPS_KEY,
    PAYLOAD_PHASE_DRAFT,
    PAYLOAD_PHASE_FINALIZE,
    PAYLOAD_PHASE_KEY,
    PAYLOAD_RANKING_ORDER_OK_KEY,
    PAYLOAD_RANKING_SEQS_KEY,
    PHASE,
    ROLE_ASSISTANT,
    ROLE_USER,
    SUBTASK_MISSING_REASON,
    SUBTASK_STATUS_OK,
    SUBTASK_STATUS_REFUSED,
    TEXT_EVENT,
    TEXT_PAYLOAD_CONTENT,
    ZERO_MATERIAL_REASON,
)
from appv2.runtimev2.answering.degradation import (
    annotate_window_label,
    citation_seqs,
    contradiction_groups,
    contradiction_section,
    dangling_tail_closing,
    delivery_accounting,
    echo_flag,
    engine_notes,
    engine_notes_block,
    ranking_order_ok,
    rowset_seqs,
    source_id_of,
    source_of,
    source_section,
    strip_dangling_citations,
    strip_placeholders,
)
from appv2.runtimev2.answering.emission import (
    extract_finalize_answer,
    strip_emission_fences,
)
from appv2.runtimev2.answering.models import (
    GAP_MISSING,
    GAP_REFUSED,
    GAP_UNVERIFIED,
    AnswerDraft,
    AnswerSegment,
    Citation,
    Gap,
)
from appv2.runtimev2.bookkeeping import (
    append_message,
    call_model,
    note,
    notice,
    record_step,
    set_intent,
)
from appv2.runtimev2.context import (
    DEFAULT_MAX_OBSERVATIONS,
    compile_manifest,
    render_materials,
    trust_of,
)
from appv2.runtimev2.parsing import Explore, explore_schema_feedback, parse_explore
from appv2.runtimev2.persistence import STEP_STATUS_FAILED, STEP_STATUS_OK
from appv2.runtimev2.prompts import answer_system_contract, assemble_answer_prompt
from appv2.runtimev2.state import (
    INTENT_END,
    INTENT_EXPLORE,
    INTENT_VERIFY,
    Manifest,
    RunState,
)
from appv2.runtimev2.transport import (
    SUPPLEMENT_BLOCK_ATTRIBUTION,
    SUPPLEMENT_BLOCK_CITATIONS,
    SUPPLEMENT_BLOCK_LINEAGE,
    SUPPLEMENT_BLOCK_SPLIT,
    SUPPLEMENT_PAYLOAD_BLOCK_KEY,
    SUPPLEMENT_PAYLOAD_TEXT_KEY,
    EventBus,
    split_block_sections,
)
from appv2.tools import LINEAGE_WINDOW_LABEL_KEY, LOCATOR_PAYLOAD_KEY

_BUS_MISSING = (
    "作答相位总线未注入（per-run 总线由编排块持有并注入）——增量文本事件无出口，"
    "fail-closed：不静默丢弃（行为 1／2）"
)
_CITATION_BLOCK_LINE = "[{seq}] {source} · {source_id}（{trust}）"


def answer(
    state: RunState,
    *,
    bus: EventBus | None = None,
    max_observations: int = DEFAULT_MAX_OBSERVATIONS,
    supplements: list[dict[str, Any]] | None = None,
    forced_text: str = "",
    execution_date: str = "",
) -> AnswerDraft:
    """作答一步：起草（真流式逐段推）或收口（引用块＋citation 帧＋链尾同批）。

    两段式入口（同 V1 answer 节点的两拍）：**未起草** → 起草段（模型调用、剥离、分段引标、
    逐段发 `text` 帧、落 `state.draft`，意图转 `verify` 交核验）；**已起草**（`verdict` 在场／
    直答态／起草标记在场）→ 收口段（引用块＋`citation` 帧＋终稿链尾，意图收 `end`）。
    灌进模型的是整条对话链（`state.messages` 只追加——钉 `pin-22`）；过程态一律经 `bookkeeping`
    唯一写口落（步／链／过程档案／通知／意图），本块零直写共享写面字段。

    `supplements`（2026-10-17 EB3 D2）＝编排块持有的**增补面收集列表**——收口段的引用块／
    「互不一致」分源块／分源归属块**不再写进正文**（`state.answer` 只留模型稿），改按原序入该
    列表（帧由编排层发射）；未注入＝本块自持一份丢弃（正文剥离面与列表无关）。

    `forced_text`（V2-96 D5）＝编排块在**硬停止**（再探轮数到顶）时交来的程序确定性缺口正文：
    模型若仍发射 `explore` 形，以本正文兜底交付（不判 failed）；模型正常作答则本参不用。
    缺省空串＝无硬停止（本批前行为零漂移）。

    `execution_date`（V2-123，L0 裁定 D-g）＝**执行日时间量的注入参**（orchestration 下传；
    本块不读时钟、不自取）——透传 `context.render_materials` 渲染材料头「执行日」段与期错位
    比对（报表期晚于执行日 → 期错位注记）；缺省空串＝材料头无「执行日」段（本批前逐字零漂移）。

    **作答第二出口 `explore`**（V2-96 D5，真源 §五·5.1）：起草应答整枚为
    `{"action":"explore","reason":…,"requests":[…]}` 且合闭世界时，**不落答案、零 text 帧**，
    落 `state.pending_explore` ＋ `next_intent="explore"` 交编排执行；不合 schema 的 explore
    尝试回喂拒因恰一次，仍不合＝强制作答（`EXPLORE_REJECT_BODY`，不判 failed）。
    """
    channel = _require_bus(bus)
    collected: list[dict[str, Any]] = [] if supplements is None else supplements
    if _drafted(state):
        return _finalize(state, channel, collected)
    return _draft(
        state,
        channel,
        max_observations=max_observations,
        supplements=collected,
        forced_text=forced_text,
        execution_date=execution_date,
    )


def _require_bus(bus: EventBus | None) -> EventBus:
    """总线把守（fail-closed）：未注入即抛错——不做「无出口静默跳过」的降级。"""
    if bus is None:
        raise RuntimeError(_BUS_MISSING)
    return bus


def _supplement(supplements: list[dict[str, Any]], block: str, text: str) -> None:
    """增补面条目入列（载荷形＝`{block, text}`——键名与块型闭世界真源均在 `transport`）。

    条目按**产出序**入列（＝原正文序：分源块 → 归属块 → 引用块）——帧由编排层按列发；
    空文本零入列（不产空块）。**块文本原样**（字面零改——正文剥离面同一份文本）。
    """
    if not text:
        return
    supplements.append(
        {SUPPLEMENT_PAYLOAD_BLOCK_KEY: block, SUPPLEMENT_PAYLOAD_TEXT_KEY: str(text)}
    )


# 题面数字串锚点的形态字符集（纯字符扫描——非语义词表；
# 先例 `understanding.closure.numeric_form_hit`）。
_ASCII_DIGITS = "0123456789"
_NUMERIC_JOINERS = ".,"  # 小数位／千分位连接符（**仅当其后接数字**才留串内）
_ANCHOR_TOKEN_LIMIT = 12  # 锚席位预算上界（V2-93 D8：8→12——题面数值全收，再多也不膨胀）


def _numeric_anchor_tokens(text: str) -> tuple[str, ...]:
    """题面数字串锚点（`render_materials` 的 `anchors` 来源之一——V2-86 行为 4）。

    **纯字符扫描**（禁 `re`——形态处理，先例 `understanding.closure.numeric_form_hit`）：
    取连续阿拉伯数字串，小数位／千分位**保形**留在串内（`12.5`／`1,000`，全角数字经 NFKC
    归一后取 ASCII 字）；百分号作形态分隔符（数字字面即锚——`12.5%` 与 `12.5` 的写法差异
    不丢召回）；汉字数字不取（无阿拉伯数字位即零 token）。去重保序、至多 `_ANCHOR_TOKEN_LIMIT`
    个。本函数零语义判断：只做字符集判定与字符拼接（规格行为 13 形态处理豁免面）。
    """
    tokens: list[str] = []
    seen: set[str] = set()
    buffer: list[str] = []

    def _flush() -> None:
        if not buffer:
            return
        token = "".join(buffer)
        buffer.clear()
        if token not in seen and len(tokens) < _ANCHOR_TOKEN_LIMIT:
            seen.add(token)
            tokens.append(token)

    for position, char in enumerate(text):
        folded = unicodedata.normalize("NFKC", char)
        if folded in _ASCII_DIGITS:
            buffer.append(folded)
        elif (
            buffer
            and folded in _NUMERIC_JOINERS
            and position + 1 < len(text)
            and unicodedata.normalize("NFKC", text[position + 1]) in _ASCII_DIGITS
        ):
            buffer.append(folded)
        else:
            _flush()
    _flush()
    return tuple(tokens)


def answer_anchors(state: RunState) -> tuple[tuple[str, str], ...]:
    """本轮材料面的锚席位来源（V2-90 单点）——**同一组**喂给 Manifest 与材料段两出口。

    题名对象（强锚）／术语（弱锚）＋题面数字串（数字锚，纯字符扫描、去重保序）；锚＝
    `(kind, text)` 分层对。V2-96：编排块的再探增量渲染（L3 选席）同引本件——**禁第二份锚装配**。
    """
    return (
        tuple(("subject", subject) for subject in state.subjects)
        + tuple(("term", term) for term in state.terms)
        + tuple(
            ("number", number)
            for number in _numeric_anchor_tokens(str(state.question or ""))
        )
    )


def _answer_window_label(observations: list[dict[str, Any]]) -> str:
    """本轮**实际取数窗**标签（V2-107 只读取值口——`TimeWindow.label` 原文）。

    取值＝血缘观察载荷 `LINEAGE_WINDOW_LABEL_KEY`（生产单点＝`query.lineage_filter_line`，
    读回单点＝`query.lineage_filter_window_label`——本块**不另算窗、不解析正文文本串**）。
    多窗不可归属（不同标签 ≥2 种）／缺位／空串 ⇒ 空串（如实不标注——不猜哪一窗是这一句的）。
    """
    labels: list[str] = []
    for observation in observations:
        locator = observation.get("locator")
        if not isinstance(locator, Mapping):
            continue
        payload = locator.get(LOCATOR_PAYLOAD_KEY)
        if not isinstance(payload, Mapping):
            continue
        label = payload.get(LINEAGE_WINDOW_LABEL_KEY)
        if isinstance(label, str) and label and label not in labels:
            labels.append(label)
    return labels[0] if len(labels) == 1 else ""


def _drafted(state: RunState) -> bool:
    """起草是否已发生（本块自立的机读判据）：直答态／`verdict` 在场／过程档案起草标记在场。

    起草标记＝过程档案里的一条标题条目（先例＝`understanding.assembly` 的「任务书已装配」标记
    ——任务书与草稿都是不能再算的活体文本，故不以文本相等为判据）。
    """
    if state.draft_kind == DRAFT_KIND_DIRECT or state.verdict is not None:
        return True
    return any(
        isinstance(entry, Mapping) and entry.get("title") == DRAFT_NOTE_TITLE
        for entry in state.process_notes
    )


# ── 起草段（行为 1／2／3／4／5／8／9／11）─────────────────────────────────────


def _draft(
    state: RunState,
    bus: EventBus,
    *,
    max_observations: int,
    supplements: list[dict[str, Any]],
    forced_text: str = "",
    execution_date: str = "",
) -> AnswerDraft:
    """起草段：材料面显式 → 单点发起模型调用 → 剥离 → 块剥除 → 分段引标 → 逐段推帧。"""
    # V2-90 锚席位来源（**同一组**喂给 Manifest 与材料段——两出口必须同源同序）：题名对象
    # （强锚）／术语（弱锚）＋ 题面数字串（数字锚，纯字符扫描、去重保序）；锚＝`(kind, text)`
    # 分层对——席位选择按「强锚→弱锚→数字锚」逐锚各保一席；additive 参，缺省空元组即本批前行为。
    # V2-96：装配单点抽为 `answer_anchors`（编排块再探增量渲染同引本件）。
    anchors = answer_anchors(state)
    manifest = compile_manifest(
        state.observations,
        step=PHASE,
        max_observations=max_observations,
        anchors=anchors,
    )
    materials_text, meta = render_materials(
        state.observations,
        max_observations=max_observations,
        anchors=anchors,
        # V2-123：执行日时间量经注入参下传（本块零时钟接触——L0 裁定 D-g）。
        execution_date=execution_date,
    )
    # V2-93：本轮渲染窗选席实录（`context.render_materials` 元数据 additive 键——本块只读、
    # 零自取；答案步 payload 原样落 `window_materials`）。
    window_face = meta[PAYLOAD_WINDOW_MATERIALS_KEY]
    # V2-123：逐支报表期实录（元数据 additive 键——本块只读、零自取；答案步 payload 同名落键）。
    material_periods = meta[MATERIAL_PERIODS_KEY]
    if meta[MATERIAL_TRUNCATED_KEY]:
        notice(
            state,
            type=NOTICE_MATERIAL_TRUNCATED,
            content=MATERIAL_TRUNCATED_CONTENT.format(
                rendered=meta[MATERIAL_RENDERED_KEY], total=meta[MATERIAL_TOTAL_KEY]
            ),
        )
    append_message(
        state,
        role=ROLE_USER,
        content=(
            assemble_answer_prompt(state)
            + materials_text
            + engine_notes_block(engine_notes(state.observations))
        ),
    )
    raw = call_model(
        state, MODEL_CALLER, list(state.messages), system=answer_system_contract()
    )
    # V2-96 D5：作答第二出口 `explore`（真源 §五·5.1）——整枚 explore JSON 且合闭世界 ⇒
    # **不落答案、零 text 帧**，落 `pending_explore` ＋ 意图 `explore` 交编排执行；不合 schema 的
    # explore 尝试回喂拒因恰一次，仍不合＝强制作答（程序确定性缺口正文，不判 failed）。
    # 硬停止轮（`forced_text` 非空，编排交来）：模型仍出 explore 形 ⇒ 以兜底正文交付。
    exp: Explore | None = None
    extracted: str | None = None
    source_text = raw
    use_forced = False
    if forced_text:
        extracted = extract_finalize_answer(raw)
        probe = raw if extracted is None else extracted
        source_text = probe
        use_forced = parse_explore(probe) is not None
    else:
        # 输入侧提取（2026-10-17 V2-82g 热修，真机 run-9d1c5267）：模型沿袭澄清相位发射形、整应答恰
        # 一枚 `{"action":"finalize","answer":…}` 时，先取回交付字段作草稿原文（程序接管输入侧），
        # 再走整条剥除管线；非整枚 finalize JSON／交付字段空 → 零提取，照旧走剥离。提取属「恢复」非
        # 「放行」：`state.draft` 落提取后文本，机读痕迹走同一条 `emission_strip` notice（发射 JSON
        # 外壳零进答案面）；`note` 的 digest 仍留**模型原话**（含发射 JSON——行为 8 的可回溯面）。
        extracted = extract_finalize_answer(raw)
        probe = raw if extracted is None else extracted
        exp = parse_explore(probe)
        if exp is None:
            feedback = explore_schema_feedback(probe)
            if feedback:
                # 回喂拒因恰一次（真源 §五·5.1）：追加拒因载荷 → 同相位再读一次。
                append_message(
                    state,
                    role=ROLE_USER,
                    content=EXPLORE_FEEDBACK_TEMPLATE.format(reason=feedback),
                )
                raw = call_model(
                    state,
                    MODEL_CALLER,
                    list(state.messages),
                    system=answer_system_contract(),
                )
                extracted = extract_finalize_answer(raw)
                probe = raw if extracted is None else extracted
                exp = parse_explore(probe)
                if exp is None:
                    # 仍不合 ⇒ 强制作答（不判 failed）——程序确定性缺口正文。
                    forced_text = EXPLORE_REJECT_BODY.format(reason=feedback)
                    use_forced = True
        if exp is not None:
            state.pending_explore = exp.as_payload()
            record_step(
                state,
                kind=DRAFT_STEP_KIND,
                title=EXPLORE_STEP_TITLE,
                payload={
                    **_citations_gaps_payload(PAYLOAD_PHASE_DRAFT, [], []),
                    PAYLOAD_EXPLORE_KEY: exp.as_payload(),
                },
            )
            set_intent(state, INTENT_EXPLORE)
            return AnswerDraft(segments=[], citations=[], gaps=[])
        source_text = raw if extracted is None else extracted
    if use_forced:
        draft_text, leaked = forced_text, False
    else:
        draft_text, leaked = strip_emission_fences(source_text)
    strip_hit = leaked or extracted is not None  # 剥离/提取命中（原判据不动；通知发点后移）
    # 占位符不进答案面（行为 13）：字面占位引标 `[n]` 整枚离场——剥离后才是答案面文本
    # （分段／发帧／落 `state.draft` 三者同源；剥后成空的行由空段跳过自然丢弃）。
    draft_text = strip_placeholders(draft_text)
    # 块剥除（2026-10-17 EB5c——行为 13 的块面）：模型自把程序块写进草稿（真机帧形＝引用清单的
    # markdown 加粗变体 `**引用**`，`eval/results/frames/EB3-NQ-M7.json`）按**块头模式族**整段
    # 离场，故 **text 帧发出前**正文即已干净（收口剥除不再是唯一防线）；血缘族段原文入 `lineage`
    # 增补面（整段照抄——血缘在场必在增补面可达），其余剥除面块段原文零留存（程序机械再生）。
    draft_text, draft_lineage = split_block_sections(draft_text)
    _supplement(supplements, SUPPLEMENT_BLOCK_LINEAGE, draft_lineage)
    # 模型原话只进过程档案与留痕（行为 8；对话层零写入）——本条同时是「已起草」机读标记。
    note(state, phase=PHASE, title=DRAFT_NOTE_TITLE, digest=raw)
    by_index = _observation_index(state)
    # 坏引标剥除（2026-10-17 EB5b——行为 13 剥除族第二形）：界外引标号整枚离场，正文其余字面
    # 零改；剥后该行失去引标＝按核验面「无据断言」既有处置收口（删句／结构行原样）。剥除列落
    # 起草步 payload 机读键（`dangling_citation_seqs`——不静默）；**不再判失败**——材料照常交付，
    # 由核验面确定性处置（旧「坏引标抛错 → 编排收 run_failed」已销账）。
    draft_text, dangling = strip_dangling_citations(draft_text, tuple(by_index))
    # 实际取数窗标注（2026-10-18 V2-107 降级版）：答案里的日期标注必须＝实际取数窗
    # （单点真源 `TimeWindow.label`——经血缘载荷只读引用），不许沿用用户原词
    # （「昨天（2026-08-30）」式）；用户原词作对照说明保留。零语义、零正则形态替换——
    # 在**分段之前**跑，故 `state.draft`／text 帧／片段三者同源（交付面零旧形）。
    draft_text = annotate_window_label(
        draft_text,
        label=_answer_window_label(state.observations),
        question=str(state.question or ""),
    )
    if strip_hit:
        # V2-85（A2③）：notice 文案按**终稿态**分支——剥成空稿时不得再称「答案不受影响」
        # （旧文案与实际相反：答案恰被剥没）。非空稿分支保留原文案（确实不影响答案）。
        notice(
            state,
            type=NOTICE_EMISSION_STRIP,
            content=(
                EMISSION_STRIP_CONTENT
                if draft_text.strip()
                else EMISSION_STRIP_EMPTY_CONTENT
            ),
        )
    segments = _draft_segments(draft_text)
    gaps = _draft_gaps(state, manifest=manifest, draft_text=draft_text)
    record_step(
        state,
        kind=DRAFT_STEP_KIND,
        title=DRAFT_STEP_TITLE,
        status=STEP_STATUS_OK if draft_text.strip() else STEP_STATUS_FAILED,
        payload={
            **_citations_gaps_payload(PAYLOAD_PHASE_DRAFT, segments, gaps),
            **_delivery_face(state, by_index, segments, draft_text),
            PAYLOAD_DANGLING_SEQS_KEY: list(dangling),
            # V2-93 additive：渲染窗选席实录（四键——selected/cap/rendered/total）
            PAYLOAD_WINDOW_MATERIALS_KEY: window_face,
            # V2-123 additive：逐支报表期实录（index → 报表期；缺期材料不入键＝如实缺行）
            MATERIAL_PERIODS_KEY: material_periods,
        },
        manifest=manifest,
    )
    if not draft_text.strip():
        # 空稿不推（行为 9）：零 text 帧、`state.draft` 保持空——按结构化缺口如实收口。
        set_intent(state, INTENT_END)
        return AnswerDraft(segments=[], citations=[], gaps=gaps)
    state.draft = draft_text
    set_intent(state, INTENT_VERIFY)
    for segment in segments:
        bus.emit(TEXT_EVENT, {TEXT_PAYLOAD_CONTENT: segment.text})  # 一段一帧（真流式）
    return AnswerDraft(
        segments=segments, citations=_citations_of(segments, by_index), gaps=gaps
    )


# ── 收口段（行为 7）─────────────────────────────────────────────────────────


def _finalize(
    state: RunState, bus: EventBus, supplements: list[dict[str, Any]]
) -> AnswerDraft:
    """收口段：引用块＋`citation` 帧＋终稿链尾**同批落定**（`verdict` 帧归编排协调，本块不产）。

    终稿文本＝核验后的草稿（`state.draft`）或直答/收敛正文（`state.answer`）；引用块与 `citation`
    帧取**同一序集**（答案面实际携带的合法引标 ∪ 核验支撑集）——两处同源不脱节（行为 2／7）。
    无稿可收口（空稿路径重入／直答空文本）→ **不推空答案**，按结构化缺口如实收口（行为 9）。

    **降级与引用簇**（`RT-W4-06b`，收口段两处确定性装配——**不靠模型自觉**，逐支原文照抄、
    零二次创作、零语义裁决）：「互不一致」分源块（行为 6——被引支同 subject 异值即分源列明，
    标「互不一致」，不调和）与分源列明归属块（行为 17——被引集跨 ≥2 出处即逐源配对「来源名↔
    数值／结论」）。两块的触发都是**形态判据**（见 `degradation`），单源／无矛盾＝零追加（保留集：
    普通答案的分源行为不变），收口重入面幂等（同块头在场＝不重复落）。

    **交付面分层（2026-10-17 EB3 D2）**：正文之后依次接的三块（分源块／归属块／引用块）**不再进
    正文**——按原序（split → attribution → citations）入 `supplements` 增补面，`state.answer` 与
    链尾只留模型稿（`docs/runtime-refactor/proposals/EB3-交付面分层与缺陷修复.md` D2）。

    **残尾护栏（2026-10-17 F1 件三）**：正文进终稿前先过**悬空结构**检测（悬空引导句／光表头／
    裸标题——`degradation.dangling_tail_closing`），命中即补一句诚实收口短句（白话、具名常量）；
    这是兜底（删句误伤已由 `verification` 侧 F1 件一／件二修掉），正文其余字面零改、零拦截。
    """
    by_index = _observation_index(state)
    text = state.draft or state.answer
    if not text.strip():
        gaps = [Gap(GAP_MISSING, None, EMPTY_DRAFT_REASON)]
        record_step(
            state,
            kind=FINALIZE_STEP_KIND,
            title=FINALIZE_STEP_TITLE,
            status=STEP_STATUS_FAILED,
            payload=_citations_gaps_payload(PAYLOAD_PHASE_FINALIZE, [], gaps),
        )
        set_intent(state, INTENT_END)
        return AnswerDraft(segments=[], citations=[], gaps=gaps)
    # 残尾护栏（2026-10-17 F1 件三）：定稿前检测**悬空结构**（悬空引导句／光表头／裸标题）——命中
    # 即程序补一句诚实收口（白话、具名常量，判据单点＝`degradation.dangling_tail_closing`）；正文
    # 其余字面零改。重入幂等：该短句已在场时零追加（同收口段三块的幂等口径）。
    closing = dangling_tail_closing(text)
    if closing and closing not in text:
        text = text + "\n\n" + closing
    segments = _final_segments(text, by_index)
    cited = _cited_seqs(state, text, by_index)
    citations = [Citation(seq=seq, locator=_locator_of(by_index[seq])) for seq in cited]
    groups = contradiction_groups(cited, by_index)
    _supplement(
        supplements, SUPPLEMENT_BLOCK_SPLIT, contradiction_section(groups, by_index, text)
    )
    _supplement(
        supplements, SUPPLEMENT_BLOCK_ATTRIBUTION, source_section(cited, by_index, text)
    )
    _supplement(
        supplements, SUPPLEMENT_BLOCK_CITATIONS, _citation_block(cited, by_index)
    )
    final_text = text  # 正文只留模型稿（四类块走增补面——EB3 D2）
    for seq in cited:
        bus.emit(CITATION_EVENT, _citation_payload(seq, by_index[seq]))
    append_message(state, role=ROLE_ASSISTANT, content=final_text)  # 链尾（同批）
    state.answer = final_text
    record_step(
        state,
        kind=FINALIZE_STEP_KIND,
        title=FINALIZE_STEP_TITLE,
        payload={
            **_citations_gaps_payload(PAYLOAD_PHASE_FINALIZE, segments, []),
            PAYLOAD_CONTRADICTION_SEQS_KEY: [
                seq for group in groups for seq in group
            ],
        },
    )
    set_intent(state, INTENT_END)
    return AnswerDraft(segments=segments, citations=citations, gaps=[])


# ── 分段与引标（行为 1／2／3）────────────────────────────────────────────────


def _split_segments(text: str) -> list[str]:
    """草稿分段（空行分段、逐段 `strip`、空段跳过）——一段一帧的呈现单元。"""
    return [part.strip() for part in text.split("\n\n") if part.strip()]


def _citation_seqs(text: str) -> list[int]:
    """文本内的引标序号列（`[n]`，ASCII 数字形；出现序、含重复）——**形态扫描，零语义**。

    单点在 `degradation.citation_seqs`（同族还有占位符记号剥离——同一方括号扫描面，禁第二份）。
    """
    return citation_seqs(text)


def _draft_segments(text: str) -> list[AnswerSegment]:
    """起草段分段：逐段取 `citation_seqs`（剥离后的草稿——引标已全在界：坏引标由
    `strip_dangling_citations` 在分段前剥除，故此处零判定）。"""
    return [
        AnswerSegment(text=part, citation_seqs=_citation_seqs(part))
        for part in _split_segments(text)
    ]


def _final_segments(text: str, by_index: Mapping[int, Mapping[str, Any]]) -> list[AnswerSegment]:
    """收口段分段：域内引标逐段保留（核验后的终稿——越界引标由核验面收口，此处零判定）。"""
    segments: list[AnswerSegment] = []
    for part in _split_segments(text):
        seqs = [seq for seq in _citation_seqs(part) if seq in by_index]
        segments.append(AnswerSegment(text=part, citation_seqs=seqs))
    return segments


def _citations_of(
    segments: list[AnswerSegment], by_index: Mapping[int, Mapping[str, Any]]
) -> list[Citation]:
    """引用块条目（起草面）：全段引标去重升序 → `Citation(seq, locator)`。"""
    seqs = sorted({seq for segment in segments for seq in segment.citation_seqs})
    return [Citation(seq=seq, locator=_locator_of(by_index[seq])) for seq in seqs]


def _cited_seqs(
    state: RunState, text: str, by_index: Mapping[int, Mapping[str, Any]]
) -> list[int]:
    """收口序集＝终稿文本携带的合法引标 ∪ 核验支撑集（`verdict.cited`；两处同源在界者）。"""
    seqs = {seq for seq in _citation_seqs(text) if seq in by_index}
    for seq in _verdict_cited(state.verdict):
        if seq in by_index:
            seqs.add(seq)
    return sorted(seqs)


def _verdict_cited(verdict: dict[str, Any] | None) -> tuple[int, ...]:
    """核验支撑集（`Verdict.cited`）的读取面：只认整数形成员（形态判定，非语义）。"""
    if not isinstance(verdict, Mapping):
        return ()
    cited = verdict.get("cited")
    if not isinstance(cited, (list, tuple)):
        return ()
    values: list[int] = []
    for item in cited:
        try:
            values.append(int(item))
        except (TypeError, ValueError):
            continue
    return tuple(values)


def _observation_index(state: RunState) -> dict[int, Mapping[str, Any]]:
    """观察序列索引（`index` → 观察行）——引标解析与引用块的查表面。"""
    index: dict[int, Mapping[str, Any]] = {}
    for observation in state.observations:
        if not isinstance(observation, Mapping):
            continue
        try:
            seq = int(observation["index"])
        except (KeyError, TypeError, ValueError):
            continue
        index[seq] = observation
    return index


# ── 降级与引用簇机读面（`RT-W4-06b`：行为 6／12／14／15／16）─────────────────────


def _has_ranking_subtask(state: RunState) -> bool:
    """是否存在排名型子问题（形态读取：`state.tool_matches` 的 `plan.ranking` 布尔真——零语义）。

    取值真源＝`specs/tool_matching.md` 匹配计划的必填布尔 `ranking`（`prompts` 汇总合同的排名
    支配句同源判定）；本函数只读布尔形，不判「这句问句要不要排名」（语义面归模型）。
    """
    for match in state.tool_matches:
        if not isinstance(match, Mapping):
            continue
        plan = match.get("plan")
        if isinstance(plan, Mapping) and plan.get("ranking") is True:
            return True
    return False


def _delivery_face(
    state: RunState,
    by_index: Mapping[int, Mapping[str, Any]],
    segments: list[AnswerSegment],
    draft_text: str,
) -> dict[str, Any]:
    """降级与引用簇的**交付面机读字段**（起草步 payload 单点，-B 七键）。

    - `echo_flag`（行为 14）：起草回声签名真值——**观测字段只记不拦**（不拦交付、不改写）；
    - `engine_notes`（行为 15）：引擎注记原文列（台账 no_hit 等——不静默丢弃）；
    - `contradiction_seqs`（行为 6）：被引支里的矛盾池成员序号（分源列明面）；
    - `engine_rows`／`delivered_rows`（行为 12 交付侧）：行集题交付行数＝引擎返回行数（丢行=0）
      的机检形——**只记账、不拦截**（拦截／如实注记归 `verification` 行为 11，同一界线）；
    - `ranking_seqs`／`ranking_order_ok`（行为 16）：排名观察支序号（有排名型子问题才在册）＋
      交付序与支序一致性（**序信息**面；数值复述面归 `verification`）。

    **判据代理登记（呈主窗对账）**：状态面**无「子问题 → 观察」归属链**（`RunState.subtask_results`
    只记 `obs_count`／`ref`，观察行不带子问题号），故「排名观察支」以**窗口行集族行**为形态代理
    （引擎按计划序返回的数据行——`specs/execution.md` 行为 4）；「跨油田归属」以**出处名差异**
    为形态代理（见 `degradation.source_section`）。
    """
    cited = sorted({seq for segment in segments for seq in segment.citation_seqs})
    ranking = _has_ranking_subtask(state)
    branch = rowset_seqs(by_index)
    return {
        PAYLOAD_ECHO_FLAG_KEY: echo_flag(draft_text),
        PAYLOAD_ENGINE_NOTES_KEY: engine_notes(state.observations),
        PAYLOAD_CONTRADICTION_SEQS_KEY: [
            seq for group in contradiction_groups(cited, by_index) for seq in group
        ],
        **delivery_accounting(by_index, cited),
        PAYLOAD_RANKING_SEQS_KEY: branch if ranking else [],
        PAYLOAD_RANKING_ORDER_OK_KEY: (not ranking) or ranking_order_ok(draft_text, branch),
    }


# ── 缺口（行为 5）───────────────────────────────────────────────────────────


def _draft_gaps(
    state: RunState, *, manifest: Manifest, draft_text: str
) -> list[Gap]:
    """结构化缺口三档齐的确定性分派（行为 5：被拒／缺失／未及核验——不静默截断）。

    - 子问题结果态 `refused`（前置闸拒／闸拒终局）→ `refused`（拒因原文）；
    - 其余非 `ok` 态（失败／重试耗尽／修参）→ `missing`（缺料，拒因原文）；
    - 零实质材料（材料面 Manifest 的 `material_total`＝0，notice 不计）→ `unverified`；
    - 空稿（剥离后）→ `missing`（起草未产出——「不推空答案，按缺口如实收口」）。
    """
    gaps: list[Gap] = []
    for result in state.subtask_results:
        if not isinstance(result, Mapping):
            continue
        status = str(result.get("status", ""))
        if status in ("", SUBTASK_STATUS_OK):
            continue
        subtask_id = str(result.get("id", "")) or None
        reason = str(result.get("reason") or "") or SUBTASK_MISSING_REASON
        kind = GAP_REFUSED if status == SUBTASK_STATUS_REFUSED else GAP_MISSING
        gaps.append(Gap(kind=kind, subtask_id=subtask_id, reason=reason))
    if manifest.material_total == 0:
        gaps.append(Gap(kind=GAP_UNVERIFIED, subtask_id=None, reason=ZERO_MATERIAL_REASON))
    if not draft_text.strip():
        gaps.append(Gap(kind=GAP_MISSING, subtask_id=None, reason=EMPTY_DRAFT_REASON))
    return gaps


# ── 引用块与帧载荷（行为 2／7；帧载荷键真源 `synth/S6` §一）────────────────────────


def _locator_of(observation: Mapping[str, Any]) -> str:
    """可机读出处（台账行／片段→报告→库／表名）：观察自带 `locator` 的键值形，回退 `source`。"""
    locator = observation.get("locator")
    if isinstance(locator, Mapping):
        parts = [
            f"{key}={locator[key]}"
            for key in sorted(locator, key=str)
            if _scalar(locator[key])
        ]
        if parts:
            return "；".join(parts)
    source = observation.get("source")
    return source.strip() if isinstance(source, str) else ""


def _scalar(value: Any) -> bool:
    """JSON 原语形且非空（引用出处的逐字段可取面——集合／空值不作数）。"""
    if isinstance(value, (str, int, float, bool)):
        return str(value).strip() != ""
    return False


def _source_of(observation: Mapping[str, Any]) -> str:
    """出处名读取（单点在 `degradation.source_of`——引用块／帧载荷／分源块同源，禁第二份）。"""
    return source_of(observation)


def _source_id_of(observation: Mapping[str, Any]) -> str:
    """出处标识读取（单点在 `degradation.source_id_of`——同源纪律同上）。"""
    return source_id_of(observation)


def _trust_of(observation: Mapping[str, Any]) -> str:
    trust = observation.get("trust")
    if isinstance(trust, str) and trust:
        return trust
    return trust_of(dict(observation))


def _citation_payload(seq: int, observation: Mapping[str, Any]) -> dict[str, Any]:
    """`citation` 帧载荷（真源 `synth/S6` §一 citation 行四键）。"""
    return {
        CITATION_PAYLOAD_INDEX: seq,
        CITATION_PAYLOAD_SOURCE: _source_of(observation),
        CITATION_PAYLOAD_SOURCE_ID: _source_id_of(observation),
        CITATION_PAYLOAD_TRUST: _trust_of(observation),
    }


def _citation_block(cited: list[int], by_index: Mapping[int, Mapping[str, Any]]) -> str:
    """引用块（迁移照抄 V1 `_finalize` 形：段头「引用：」＋逐支「[n] 出处 · id（信任）」）。"""
    if not cited:
        return ""
    lines = [
        _CITATION_BLOCK_LINE.format(
            seq=seq,
            source=_source_of(by_index[seq]),
            source_id=_source_id_of(by_index[seq]),
            trust=_trust_of(by_index[seq]),
        )
        for seq in cited
    ]
    return CITATION_BLOCK_HEAD + "\n".join(lines)


def _citations_gaps_payload(
    phase: str, segments: list[AnswerSegment], gaps: list[Gap]
) -> dict[str, Any]:
    """答案面步 payload：`phase` ＋ `citations`（去重升序）＋ `gaps`（逐条三键）机读字段。"""
    return {
        PAYLOAD_PHASE_KEY: phase,
        PAYLOAD_CITATIONS_KEY: sorted(
            {seq for segment in segments for seq in segment.citation_seqs}
        ),
        PAYLOAD_GAPS_KEY: [
            {
                PAYLOAD_GAP_KIND_KEY: gap.kind,
                PAYLOAD_GAP_SUBTASK_KEY: gap.subtask_id,
                PAYLOAD_GAP_REASON_KEY: gap.reason,
            }
            for gap in gaps
        ],
    }


# `context.render_materials` 元数据键（真源 `specs/context.md` 行为 5／6——本块只读三键指针）。
MATERIAL_TRUNCATED_KEY = "material_truncated"
MATERIAL_RENDERED_KEY = "material_rendered"
MATERIAL_TOTAL_KEY = "material_total"
# V2-93：渲染窗选席实录键（`context.render_materials` 元数据 additive 键——答案步 payload 同名落键，
# 键名单点在本行，消费方零第二份字面）。
PAYLOAD_WINDOW_MATERIALS_KEY = "window_materials"
# V2-123：材料期实录键（`context.render_materials` 元数据 additive 键 `material_periods`——
# 答案步 payload 同名落键：逐支 `index → 报表期`，缺期材料不入键＝如实缺行）。
MATERIAL_PERIODS_KEY = "material_periods"
