"""核验相位本体（`verify`）：剥结构性残留 → 逐行断言级核验 → 改写／分列／归属审 → 判定卡＋机读信号。

真源＝`specs/verification.md`（已定稿）＋卡 `specs/modules.md` `## verification`（签名以卡为准：
`verify(state) -> Verdict`）。一句话：答案交付前**逐句核对有没有材料撑着**——**纯程序、零模型**
（防编造的机器底线）；没支撑的话**改写掉**，两来源对不上就**分开列**。

一次调用的固定序（行为 1–11；语义真源＝`recon/A2` R-A2-16…R-A2-28，承载位在 V2）：

1. **剥结构性残留**（行为 1）：整行即 JSON 对象／数组＝结构性残片，剥除且**不计改写**（发射围栏／
   裸发射令牌的剥离单点归 `answering`——答案面归属，进核验的草稿已过那道剥离）；**块头模式族段**
   同拍离场（2026-10-17 EB3 D2 起血缘五要素整段；2026-10-17 EB5c 扩为族判据：血缘族段整段入
   `lineage` 增补面、剥除面块型〔引用清单〕段整段离场——判据与段剥离单点＝`transport.blocks`，
   两相位同族同语义；单行口径说明（≤2 行、带 `[n]` 引标）保留在正文）；
2. **逐行断言级核验**（行为 1／2／7／8）：逐行判定（**不是整段判**）；判定面文本先过全角归一
   （行为 7），引标切辖域、数值取**边界记号**比对；被引观察的数值须在断言文本里复述，承载形式
   （`agg_row`／`lineage`／`fragment`）豁免「全数值复述」（任一数值重叠即支撑、零重叠照改）；
   空壳辖域整行重判（修一）；整行重判仍不过时**窗内对齐放行**（行为 8：零数值断言不放行——仍须
   有可解析引标支撑）。**2026-10-17 F1 件一**：数值断言的记号面**只收计量数值**（带单位／小数／
   千分位形）——标识符（`W-22`）与日期（`2026 年 11 月 1 日`）不算数值断言；**件二**：无引标数字行
   与**本轮窗内全观测**比对（`aligned_indices` 同款判据单点，2026-10-18 V2-103 由「同 draft 已
   cited 观察集」扩窗），命中即保留、按命中支回填 `cited` 且计有支撑（综述句重组已引事实不得删；
   窗内零命中＝真无据照删——数值记号全等不变）；**件四**：支撑过的行再过**行级油田归属闸**——被引材料自带
   油田名却**全不属题眼所辖油田**且行内无分源说明者**拒收**（同删句族留痕），机读面落 step payload
   `field_attribution_mismatch` 键；**2026-10-18 V2-94（定性句放行）**：承载片段断言辖域**零计量
   数值记号**时引标可解析即保留（step payload additive 键 `qualitative_kept` 如实计数），**有计量
   数值仍照旧记号比对、对不上照删**（防编造红线不动）；一行多引标时承载片段**任一支撑即保留**
   （引标须全可解析——行为 8；非承载辖域全须复述不变）；`rewrites`／`ok=False` 语义与
   `RewriteRecord.reason` 闭世界（两值）不变；
3. **无据 → 删句**（行为 3；2026-10-17 EB3 D3）：没支撑的句子**整行离场**（不贴「未找到」前缀，
   不留残句）＋ `RewriteRecord`（`reason="no_material"`）＋发 `notice`（`verdict.rewritten` 如实
   计数＝不静默）；**豁免两类线**原样保留（引擎披露行／组头行——只豁免删句，不改写、不放行支撑判）；
   无引标但有数值的行＝无据断言，照删（V2：关闭现状「无引标数字行经窗内放行」形——钉 `pin-10`
   「不得 `cited=[]` 且数字在场」）；无引标且无数值的行＝结构承载，原样保留且**不计有支撑数**
   （行为 8「不得自动判过」）；
4. **矛盾 → 分列**（行为 4）：被引观察同 subject（全角「：」前名）≥2 支且值不同 → 分开列明、各带
   出处、**不强调和**（`RewriteRecord.reason="conflict"`）＋发 `notice`；`Verdict.split`＝**组数**；
   **分列块不入 `state.draft`**——按原序入增补面（2026-10-17 EB3 D2）；
5. **归属审**（行为 5）：题眼锚＝问句实体词（`appv2.tools.anchors` 的闭世界解析单点，
   确定性零模型）；
   被引**检索片段**（`fragment`／`graph`）的出处名与内容均不含任何题眼锚＝跨源引用 →
   `attribution=False` ＋缺口留痕＋条入增补面（`attribution` 块，2026-10-17 EB3 D2）；无锚＝审静默
   （不误伤）；
6. **判定卡＋机读信号**（行为 6／10／11；「不降级与静默禁令」节）：`Verdict` 九键齐备（缺键＝判
   失败）＋ step payload 六计数键与行集对账两字段 ＋ `verdict`／`notice` 帧（**批次落定归
   `orchestration` 协调**，本块只保证自产部分就位）；行集对账差额>0 且答案面无行集声明 → 补如实
   注记（**不删改数值断言、不重试、不拦截**）。

**动作档位（2026-10-18 V2-116——配置单点 `VERIFY_ACTION`，真源 `specs/verification.md` 行为 14）**：
`off`／`observe`／`repair`／`delete` 四档，**缺省档＝`delete`**（保既有行为）；`off` 完全跳过
逐行核验（不检测、不改写）；`observe` 照常检测（判定逻辑零改）但**不删任何行**；`repair` 接
V2-115 回炉口（未落地时等同 `observe` 并记 `verify_mode="repair-fallback"`）。非 `delete` 档
交付面**逐字等于草稿**（零加工）；检出项入 step payload `intended_rewrites`（每条含原句 `line`
与 `reason`）＋ `verify_mode`（additive 键——`Verdict` 九键不动）；`rewrites` 计数＝**检出条数**
（非 `delete` 档下检出 ≠ 离场，故 notice／gap 文案按档诚实，不称「删去」）。档位闭世界越界＝
fail-fast（转 fail-closed，不静默回落）。

**写面纪律**：共享写面（步／通知／路由意图）一律经 `bookkeeping` 唯一写口（相位禁直写）；本块自有
字段（`state.draft`＝核验后答案面、`state.verdict`＝判定卡投影）直接落地——`answering` 收口以
`state.draft`／`state.verdict` 为消费面（真源 `specs/answering.md` 行为 7）。**增补面**（分源块／
归属块／血缘段）经注入的 `supplements` 列表交出（2026-10-17 EB3 D2——块不进正文，帧由编排层发射）。

**接缝**：`bus`（per-run 总线，编排块持有、注入各相位）为**必给**注入面——未注入＝调用方断线，
入口即 fail-closed 抛错（同 `answering.answer`／`understanding.interpret` 先例）；`supplements`
（增补面收集列表）为**选给**注入面（缺省＝本块自持一份丢弃——正文剥离面与列表无关）。

**合法降级路径＝无**：闭世界越界一律 fail-closed 抛错；核验器自身抛错**不判 `ok=True`**——
转 `Verdict.ok=False` ＋缺口（由 `orchestration` 承接），绝不静默放行。
"""

from __future__ import annotations

import os
from collections.abc import Collection, Mapping, Sequence
from typing import Any

from appv2.runtimev2.bookkeeping import notice, record_step, set_intent
from appv2.runtimev2.state import INTENT_ANSWER, STEP_VERIFY, RunState
from appv2.runtimev2.transport import (
    SUPPLEMENT_BLOCK_ATTRIBUTION,
    SUPPLEMENT_BLOCK_LINEAGE,
    SUPPLEMENT_BLOCK_SPLIT,
    SUPPLEMENT_PAYLOAD_BLOCK_KEY,
    SUPPLEMENT_PAYLOAD_TEXT_KEY,
    EventBus,
)
from appv2.runtimev2.verification.constants import (
    CARRIER_KINDS,
    EVENT_NOTICE,
    EVENT_VERDICT,
    GAP_ATTRIBUTION_REASON,
    GAP_FAIL_CLOSED_REASON,
    GAP_REWRITE_REASON,
    GAP_REWRITE_REASON_RECORD_ONLY,
    NOTICE_ATTRIBUTION_CONTENT,
    NOTICE_ATTRIBUTION_SPLIT,
    NOTICE_CONTRADICTION_CONTENT,
    NOTICE_CONTRADICTION_SPLIT,
    NOTICE_UNSUPPORTED_CLAIM,
    NOTICE_UNSUPPORTED_CONTENT,
    NOTICE_UNSUPPORTED_CONTENT_RECORD_ONLY,
    PAYLOAD_ATTRIBUTION_KEY,
    PAYLOAD_CITED_KEY,
    PAYLOAD_DELIVERED_ROWS_KEY,
    PAYLOAD_FIELD_MISMATCH_KEY,
    PAYLOAD_GAP_KIND_KEY,
    PAYLOAD_GAP_REASON_KEY,
    PAYLOAD_GAP_SUBTASK_KEY,
    PAYLOAD_GAPS_KEY,
    PAYLOAD_INTENDED_REWRITES_KEY,
    PAYLOAD_OBS_ROWS_KEY,
    PAYLOAD_OK_KEY,
    PAYLOAD_PHASE_KEY,
    PAYLOAD_REWRITE_LINE_KEY,
    PAYLOAD_REWRITE_REASON_KEY,
    PAYLOAD_REWRITES_KEY,
    PAYLOAD_REWRITTEN_KEY,
    PAYLOAD_ROW_NOTE_KEY,
    PAYLOAD_ROWSET_ALIGNED_KEY,
    PAYLOAD_ROWSET_MISSING_KEY,
    PAYLOAD_SPLIT_KEY,
    PAYLOAD_SUPPORTED_KEY,
    PAYLOAD_VERIFY_MODE_KEY,
    PHASE,
    REWRITE_CONFLICT,
    REWRITE_NO_MATERIAL,
    ROW_NOTE_MISSING_NONE,
    ROW_NOTE_ORDER_ALIGNED,
    ROW_NOTE_ORDER_MISALIGNED,
    ROW_NOTE_TEMPLATE,
    ROWSET_OBSERVATION_KINDS,
    SPLIT_NO,
    SPLIT_YES,
    STEP_TITLE_TEMPLATE,
    VERIFY_ACTION_ENV,
    VERIFY_MODE_DEFAULT,
    VERIFY_MODE_DELETE,
    VERIFY_MODE_OBSERVE,
    VERIFY_MODE_OFF,
    VERIFY_MODE_REPAIR,
    VERIFY_MODE_REPAIR_FALLBACK,
    VERIFY_MODES,
)
from appv2.runtimev2.verification.models import GAP_UNVERIFIED, Gap, RewriteRecord, Verdict
from appv2.runtimev2.verification.rules import (
    aligned_field_names,
    aligned_indices,
    attribution_block,
    attribution_split,
    citation_chunks,
    contradiction_groups,
    engine_disclosure_line,
    field_attribution_mismatch,
    group_header_line,
    line_numbers_are_asserted,
    lineage_observation_text,
    locator_kind,
    normalize_for_match,
    number_tokens,
    observation_supported,
    qualitative_release,
    question_anchors,
    resolvable,
    rowset_audit,
    scope_usable,
    split_block,
    split_block_sections,
    structural_line,
    uncited_aligned,
    without_markers,
)

_BUS_MISSING = (
    "核验相位总线未注入（per-run 总线由编排块持有并注入）——裁决／通知事件无出口，"
    "fail-closed：不静默丢弃（行为 6／10）"
)
_INDEX_SEPARATOR = "、"
# 定性句放行计数键（2026-10-18 V2-94——票面边界红线只许动 `rules.py`／`core.py`／本块测试／
# `specs/verification.md`，故键字面落本块 core 单点，不扩 `constants.py`；additive 键）。
PAYLOAD_QUALITATIVE_KEPT_KEY = "qualitative_kept"
# V2-115 回炉口落地标志（2026-10-18 V2-116 `repair` 档的前置）：V2-115（编排侧 `orchestration/
# repair.py` ＋ `INTENT_REPAIR`，见其票面「Kimi 评审修正」1——回炉归编排，本块零 LLM 不动）
# **未落地** ⇒ `repair` 档等同 `observe` 并记 `verify_mode="repair-fallback"`。V2-115 落地时
# 改此单点即可（本块不预建回炉面——「合法降级路径＝无」不变）。
_REPAIR_PORT_LANDED = False


def _verify_mode() -> str:
    """核验动作档位读点（**唯一 env 读点**，先例 `gateway_adapter.eval_clock.frozen_date`）。

    未设／空串 → 缺省档（`delete`——评审修正 1：保既有行为）；闭世界外取值 → **fail-fast 抛错**
    （不静默回落；`verify()` 的错误契约把其转成 `ok=False`＋缺口，不静默放行）。
    """
    raw = os.environ.get(VERIFY_ACTION_ENV)
    if raw is None or raw == "":
        return VERIFY_MODE_DEFAULT
    if raw not in VERIFY_MODES:
        raise ValueError(
            f"{VERIFY_ACTION_ENV} 非法值 {raw!r}（闭世界 {sorted(VERIFY_MODES)}）"
            "——fail-fast 不静默回落"
        )
    return raw


def verify(
    state: RunState,
    *,
    bus: EventBus | None = None,
    supplements: list[dict[str, Any]] | None = None,
) -> Verdict:
    """核验入口（卡面签名 `verify(state) -> Verdict`；`bus` 为编排块注入的帧出口）。

    返回判定卡 `Verdict`（对外判定，**不是 answer 侧文本**）；同时把核验后的答案面落回
    `state.draft`、判定卡投影落 `state.verdict`、步／通知／意图经 `bookkeeping` 唯一写口落账。
    `supplements`（2026-10-17 EB3 D2）＝编排块持有的**增补面收集列表**——分源块／归属块／血缘
    五要素整段**不再写进 `state.draft`**，改按产出序入该列表（帧由编排层发射）；未注入＝本块
    自持一份丢弃（不落正文）。**核验器自身抛错 → 不判 `ok=True`**（fail-closed：`ok=False`
    ＋缺口，不静默放行）。
    """
    channel = _require_bus(bus)
    collected: list[dict[str, Any]] = [] if supplements is None else supplements
    try:
        return _verify(state, channel, collected)
    except Exception as exc:  # 错误契约：核验器自身抛错＝fail-closed 取 ok=False
        return _fail_closed(state, exc)


def _require_bus(bus: EventBus | None) -> EventBus:
    """总线把守（fail-closed）：未注入即抛错——不做「无出口静默跳过」的降级。"""
    if bus is None:
        raise RuntimeError(_BUS_MISSING)
    return bus


def _fail_closed(state: RunState, exc: BaseException) -> Verdict:
    """fail-closed 判定卡：`ok=False` ＋缺口（行为 9／错误契约）——不静默放行、不返回哨兵。"""
    reason = GAP_FAIL_CLOSED_REASON.format(error=f"{type(exc).__name__}: {exc}")
    verdict = Verdict(
        supported=0,
        rewritten=0,
        split=0,
        cited=[],
        delivered_rows=0,
        obs_rows=0,
        attribution=False,
        ok=False,
        gaps=[Gap(kind=GAP_UNVERIFIED, subtask_id=None, reason=reason)],
    )
    state.verdict = verdict.as_dict()
    return verdict


def _verify(state: RunState, bus: EventBus, supplements: list[dict[str, Any]]) -> Verdict:
    # 档位读点最先（2026-10-18 V2-116）：闭世界越界＝fail-fast，交付面零加工即转 fail-closed。
    mode = _verify_mode()
    verify_mode = mode
    if mode == VERIFY_MODE_REPAIR and not _REPAIR_PORT_LANDED:
        # repair 前置未落地（V2-115）⇒ 等同 observe，并**如实标注**降级档位。
        verify_mode = VERIFY_MODE_REPAIR_FALLBACK
    anchors = question_anchors(state.question)
    observations = list(state.observations)
    by_index = {int(obs["index"]): obs for obs in observations}
    # 题眼所辖油田名集（2026-10-17 F1 件四——油田归属对账的比对面；空集＝审静默）
    field_scope = aligned_field_names(anchors, observations)

    # 块剥除（2026-10-17 EB3 D2 血缘五要素整段；2026-10-17 EB5c 扩块头模式族——引用清单段同拍
    # 离场，分源／归属族只作在场判据不剥）：血缘族段整段入 `lineage` 增补面，单行口径说明留正文。
    kept_lines, lineage_text = split_block_sections(str(state.draft or ""))
    # 血缘统一走增补面（2026-10-17 EB5c）：**数据链题血缘在场（`locator.kind="lineage"` 观察）⇒
    # 增补面必有 `lineage` 块**——不以「模型是否把五要素写进草稿」为断（EB2 D1 起材料面只渲染
    # 一行口径行，模型多数不再复写全文，EB3 实态＝supplement 携血缘仅 6/97 题、其余只在
    # `observation` 帧）；模型稿无该段时**原文照抄**观察自带五要素全文（入栈序、空行连接、
    # 零二次创作）——前端旁路取数统一从增补面取，不必回读观察帧。
    lineage_text = lineage_text or lineage_observation_text(observations)
    if lineage_text:
        _supplement(supplements, SUPPLEMENT_BLOCK_LINEAGE, lineage_text)

    if mode == VERIFY_MODE_OFF:
        # `off`：**完全跳过逐行核验**（不检测、不改写）——交付＝草稿逐字（票面任务 1 逐字）。
        out_lines = list(kept_lines)
        rewrites: list[RewriteRecord] = []
        cited: set[int] = set()
        cited_lines: list[tuple[str, tuple[int, ...]]] = []
        supported = 0
        field_mismatched: tuple[int, ...] = ()
        qualitative_kept = 0
    else:
        (
            detected_lines,
            rewrites,
            cited,
            cited_lines,
            supported,
            field_mismatched,
            qualitative_kept,
        ) = _verify_lines(kept_lines, observations, by_index, field_scope)
        if mode in (VERIFY_MODE_OBSERVE, VERIFY_MODE_REPAIR):
            # `observe`／`repair`（含 repair-fallback）：判定逻辑零改，但**不删任何行**——
            # 检出项只入 `intended_rewrites`（交付面＝草稿逐字，票面任务 2）。
            out_lines = list(kept_lines)
        else:
            out_lines = detected_lines  # `delete`：旧行为（无据断言整行离场）
    text = "\n".join(out_lines)

    ordered_cited = sorted(cited)
    groups = contradiction_groups(ordered_cited, observations)
    if groups:
        # 分源块不再写进 `state.draft`（EB3 D2）：按原序入增补面，帧由编排层发射。
        _supplement(supplements, SUPPLEMENT_BLOCK_SPLIT, split_block(groups))
        for group in groups:
            members = {int(obs["index"]) for obs in group}
            matched_lines = [
                source for source, seqs in cited_lines if members.intersection(seqs)
            ]
            if matched_lines:
                for source in dict.fromkeys(matched_lines):
                    rewrites.append(RewriteRecord(line=source, reason=REWRITE_CONFLICT))
            else:
                rewrites.append(
                    RewriteRecord(
                        line=str(group[0].get("content", "")), reason=REWRITE_CONFLICT
                    )
                )

    aligned, crossed = attribution_split(anchors, ordered_cited, observations)
    if crossed:
        pending = uncited_aligned(anchors, ordered_cited, observations)
        # 同款：归属块入增补面（原序：分源 → 归属），不进正文。
        _supplement(
            supplements,
            SUPPLEMENT_BLOCK_ATTRIBUTION,
            attribution_block(anchors, aligned, pending, crossed),
        )

    engine_row_seqs = [
        int(obs["index"]) for obs in observations if locator_kind(obs) in ROWSET_OBSERVATION_KINDS
    ]
    obs_rows = len(engine_row_seqs)
    delivered_rows = sum(1 for seq in engine_row_seqs if seq in cited)
    delta = obs_rows - delivered_rows
    # 行数对账（行为 11；2026-10-17 EB5c 扩面）：**机读面恒在场**——`rowset_missing`（缺行序号列：
    # 渲染行数≠引擎行数的逐号面）＋ `rowset_aligned`（引标序对齐：交付的引擎行号列是否恰为引擎
    # 行号序前 L 项——跳号／整体偏移即 off-by-one 错位）。两键**不受「答案面有无声明」影响**：
    # L04-22 实态＝自述「以上共 86 口井已返回」而实际交付 84 行（缺第 24／46 号）＋引标整体错位
    # 一格——自述声明的真伪只能由对账事实判，故机读面恒落账（对账面可复算）。
    # 注记面（`row_note`，人读）三态不变（附 D 钉：无声明→注记、有声明→零注记）；**不改写数值
    # 断言、不重试、不拦截**（Owner 裁决②：对账只作诚实记账面）。
    rows_missing, rows_aligned = rowset_audit(engine_row_seqs, cited)
    row_note: str | None = None
    if delta > 0 and delivered_rows == 0:
        row_note = ROW_NOTE_TEMPLATE.format(
            obs_rows=obs_rows,
            delivered_rows=delivered_rows,
            delta=delta,
            missing=(_index_text(list(rows_missing)) if rows_missing else ROW_NOTE_MISSING_NONE),
            order=ROW_NOTE_ORDER_ALIGNED if rows_aligned else ROW_NOTE_ORDER_MISALIGNED,
        )

    # `rewritten`＝**无据**被改写的句子数（分列改写不计——`split` 另计组数；两维度不强行映射）
    rewritten = sum(1 for record in rewrites if record.reason == REWRITE_NO_MATERIAL)
    gaps: list[Gap] = []
    if rewritten:
        gaps.append(
            Gap(
                kind=GAP_UNVERIFIED,
                subtask_id=None,
                reason=(
                    GAP_REWRITE_REASON.format(rewritten=rewritten)
                    if mode == VERIFY_MODE_DELETE
                    else GAP_REWRITE_REASON_RECORD_ONLY.format(
                        rewritten=rewritten, mode=verify_mode
                    )
                ),
            )
        )
    if crossed:
        gaps.append(
            Gap(
                kind=GAP_UNVERIFIED,
                subtask_id=None,
                reason=GAP_ATTRIBUTION_REASON.format(
                    indices=_index_text([int(obs["index"]) for obs in crossed]),
                    anchors=_anchor_text(anchors),
                ),
            )
        )
    verdict = Verdict(
        supported=supported,
        rewritten=rewritten,
        split=len(groups),
        cited=ordered_cited,
        delivered_rows=delivered_rows,
        obs_rows=obs_rows,
        attribution=not crossed,
        ok=rewritten == 0,
        gaps=gaps,
    )

    _emit_signals(
        state,
        bus,
        verdict,
        rewrites,
        anchors,
        crossed,
        row_note,
        rows_missing,
        rows_aligned,
        field_mismatched,
        qualitative_kept,
        verify_mode,
    )
    state.draft = text
    state.verdict = verdict.as_dict()
    set_intent(state, INTENT_ANSWER)
    return verdict


def _chunks_supported(
    chunks: Sequence[tuple[int, str]], by_index: Mapping[int, Mapping[str, Any]]
) -> bool:
    """逐引标辖域支撑判定（引标须可解析——行为 8「仍须有可解析引标支撑」）。

    **2026-10-18 V2-94**（票面任务段逐字：「一行引多来源时，**承载片段**按「任一支撑即保留」」；
    「非承载：全须复述（不变）」）：

    - **引标须全可解析**：任一引标不可解析 → 本分支不过（行为 8；落回空壳重判／窗内对齐两支）；
    - **承载片段**（`fragment`／`agg_row`／`lineage`）辖域：**任一**支撑即过（V2-94 放宽面；
      定性句放行分支见 `rules.observation_supported`／`rules.qualitative_release`）；
    - **非承载**辖域：**全须复述**（逐辖域 `observation_supported`——语义零改；防编造红线不动）。
    """
    carrier_supported = False
    has_carrier = False
    for seq, chunk in chunks:
        if not resolvable(seq, by_index):
            return False
        obs = by_index[seq]
        if locator_kind(obs) in CARRIER_KINDS:
            has_carrier = True
            if observation_supported(obs, chunk):
                carrier_supported = True
            continue
        if not observation_supported(obs, chunk):
            return False
    return carrier_supported if has_carrier else True


def _supplement(
    supplements: list[dict[str, Any]], block: str, text: str
) -> None:
    """增补面条目入列（载荷形＝`{block, text}`——键名与块型闭世界真源均在 `transport`）。

    条目按**产出序**入列（＝原正文序：血缘段 → 分源块 → 归属块）——帧由编排层按列发。
    空文本零入列（不产空块）。
    """
    if not text:
        return
    supplements.append(
        {SUPPLEMENT_PAYLOAD_BLOCK_KEY: block, SUPPLEMENT_PAYLOAD_TEXT_KEY: str(text)}
    )


def _verify_lines(
    lines: Sequence[str],
    observations: Sequence[Mapping[str, Any]],
    by_index: Mapping[int, Mapping[str, Any]],
    field_scope: Collection[str] = frozenset(),
) -> tuple[
    list[str],
    list[RewriteRecord],
    set[int],
    list[tuple[str, tuple[int, ...]]],
    int,
    tuple[int, ...],
    int,
]:
    """逐行断言级核验（行为 1／2／3／7／8；EB3 D3：真无据断言**删句**＋豁免两类线）。

    返回（保留行，改写留痕，被引序号集，有据行面，有支撑句数，**油田归属对不上**的被引序号列，
    **定性句放行行数**）。逐行判定、**不是整段判**；无据行**整行离场**（删句，不贴前缀）；豁免
    两类线（引擎披露行／组头行）原样保留且不计改写。**2026-10-17 F1**两处精度面：

    - **件一（删句判据修精度）**：无引标数字行的判据面＝**计量数值**（`line_numbers_are_asserted`
      ——标识符／日期不算数值断言），井号代码行不再被误判删句；
    - **件二（跨行支撑比对）× V2-103（比对域扩窗）**：无引标数字行与**本轮窗内全观测**比对
      （`aligned_indices`——与带引标行的 matched 分支同一判据单点，零第二份判据），命中即保留、
      按命中支回填 `cited` 且计有支撑（综述句重组已引事实不得删）；**窗内零命中＝真无据照删**
      （数值记号全等要求不变——防蒙混）。旧域「同 draft 已 cited 观察集」在单句草稿下必空 ⇒
      权威观测在位仍被删致零交付（真机证据＝EB11 `数-排1`），故扩为全窗观测；
    - **件四（油田归属对账）**：支撑判定通过的行再过**行级归属闸**——被引材料自带油田名却全不属
      题眼所辖油田、且行内无分源说明者**拒收**（按既有删句族处置，判据单点＝
      `rules.field_attribution_mismatch`；题眼所辖面与四条收窄面见该件注）。
    """
    out_lines: list[str] = []
    rewrites: list[RewriteRecord] = []
    cited: set[int] = set()
    cited_lines: list[tuple[str, tuple[int, ...]]] = []
    supported = 0
    qualitative_kept = 0
    field_mismatched: list[int] = []
    total = len(lines)
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            out_lines.append(line)
            continue
        if structural_line(stripped):
            continue  # 结构性残片：剥除不计改写（行为 1）
        next_line = lines[index + 1] if index + 1 < total else None
        normalized = normalize_for_match(line)
        chunks = citation_chunks(normalized)
        kept = _kept_citations(chunks, normalized, by_index, observations)
        if kept is not None:
            seqs, record_line, qualitative = kept
            mismatch = field_attribution_mismatch(line, seqs, by_index, field_scope)
            if mismatch:
                # 件四：行数据归属另一油田且无分源说明 → 该行拒收（同删句族留痕＋如实计数）
                field_mismatched.extend(mismatch)
                rewrites.append(RewriteRecord(line=line, reason=REWRITE_NO_MATERIAL))
                continue
            cited.update(seqs)
            if record_line:
                cited_lines.append((line, seqs))
            supported += 1
            if qualitative:  # V2-94：定性句放行计数（保留面，additive）
                qualitative_kept += 1
            out_lines.append(line)
            continue
        if chunks:
            if _rewrite_exempt(line, next_line, observations):
                # 豁免两类线（EB3 D3）：引擎披露行／组头行原样保留（不贴前缀、不删句）
                out_lines.append(line)
                continue
            rewrites.append(RewriteRecord(line=line, reason=REWRITE_NO_MATERIAL))
            continue
        if line_numbers_are_asserted(normalized):
            # 无引标但有**计量数值**＝无据断言（行为 8 后半；钉 pin-10：不得 `cited=[]` 且数字在场）
            # 比对域＝**本轮窗内全观测**（2026-10-18 V2-103——旧域「同 draft 已 cited 观察集」在单句
            # 草稿下必空 ⇒ 权威观测在位仍被删致零交付；判据单点 `aligned_indices` 零改，只换域）；
            # 命中即保留并按命中支回填 `cited`（pin-10 落账面）、**文本零改（不插引标）**；数值记号
            # 全等要求不变（窗内零命中＝真无据照删——防蒙混）。
            matched = aligned_indices(
                number_tokens(without_markers(normalized)), observations
            )
            if matched:  # V2-103：与**窗内全观测**比对——命中即保留（跨行支撑）
                cited.update(matched)
                supported += 1
                out_lines.append(line)
                continue
            if _rewrite_exempt(line, next_line, observations):
                out_lines.append(line)
                continue
            rewrites.append(RewriteRecord(line=line, reason=REWRITE_NO_MATERIAL))
            continue
        out_lines.append(line)  # 结构承载（标题／表头／分隔线）——不计有支撑数
    return (
        out_lines,
        rewrites,
        cited,
        cited_lines,
        supported,
        tuple(field_mismatched),
        qualitative_kept,
    )


def _kept_citations(
    chunks: Sequence[tuple[int, str]],
    normalized: str,
    by_index: Mapping[int, Mapping[str, Any]],
    observations: Sequence[Mapping[str, Any]],
) -> tuple[tuple[int, ...], bool, bool] | None:
    """带的引标行支撑判定（返回（被引序号列，是否入「有据行面」，是否定性句放行）；判不过＝`None`）。

    三分支同既有语义（逐辖域支撑 → 空壳辖域整行重判 → 窗内对齐放行）；`record_line`＝前两分支
    真（其行面供矛盾分列回填改写留痕），第三分支（对齐放行）不入行面——同既有行为。**2026-10-18
    V2-94**：第三返回值＝本行是否靠**定性句放行**保留（判据单点＝`_qualitative_release`，供
    `_verify_lines` 累计 `qualitative_kept`）。
    """
    if not chunks:
        return None
    seqs = tuple(seq for seq, _ in chunks)
    bare = without_markers(normalized)
    qualitative = _qualitative_release(chunks, bare, by_index)
    if _chunks_supported(chunks, by_index):
        return seqs, True, qualitative
    if any(not scope_usable(chunk) for _, chunk in chunks) and _whole_supported(
        chunks, bare, by_index
    ):
        return seqs, True, qualitative
    matched = aligned_indices(number_tokens(bare), observations)
    if matched:
        return matched, False, False
    return None


def _qualitative_release(
    chunks: Sequence[tuple[int, str]],
    bare: str,
    by_index: Mapping[int, Mapping[str, Any]],
) -> bool:
    """本行是否靠「定性句放行」保留（2026-10-18 V2-94——`qualitative_kept` 的计数判据面）。

    行级判据＝**断言面零计量数值记号**（`bare`＝剥引标后整行，`number_tokens` 空）且**至少一支
    可解析承载片段有量值**（判据单点＝`rules.qualitative_release`）。断言面有量值者走记号比对
    （修前照删面）——不入本计数（票面「有数字照旧记号比对」的计数面）。
    """
    if number_tokens(bare):
        return False
    return any(
        resolvable(seq, by_index) and qualitative_release(by_index[seq], chunk)
        for seq, chunk in chunks
    )


def _rewrite_exempt(
    line: str, next_line: str | None, observations: Sequence[Mapping[str, Any]]
) -> bool:
    """核验豁免两类线（EB3 D3 逐字）：引擎披露行／组头行——只豁免删句，不改写、不放行支撑判。"""
    return engine_disclosure_line(line, observations) or group_header_line(line, next_line)


def _whole_supported(
    chunks: Sequence[tuple[int, str]],
    bare: str,
    by_index: Mapping[int, Mapping[str, Any]],
) -> bool:
    """空壳辖域修一：剥引标后以**整行文本**对各引标逐一重判（引标序号自身不作数——防自证）。"""
    return all(
        resolvable(seq, by_index) and observation_supported(by_index[seq], bare)
        for seq, _ in chunks
    )


def _index_text(indices: Sequence[int]) -> str:
    return _INDEX_SEPARATOR.join(f"[{index}]" for index in indices)


def _anchor_text(anchors: Sequence[str]) -> str:
    return _INDEX_SEPARATOR.join(str(anchor) for anchor in anchors)


def _emit_signals(
    state: RunState,
    bus: EventBus,
    verdict: Verdict,
    rewrites: Sequence[RewriteRecord],
    anchors: Sequence[str],
    crossed: Sequence[Any],
    row_note: str | None,
    rowset_missing: Sequence[int],
    rowset_aligned: bool,
    field_mismatched: Sequence[int] = (),
    qualitative_kept: int = 0,
    verify_mode: str = VERIFY_MODE_DELETE,
) -> None:
    """机读信号（「不降级与静默禁令」节）：step payload ＋ `notice`／`verdict` 帧 ＋ 通知落账。

    三类事件的帧面与状态落账同批：改写／分列／归属失败**都必产信号**（不许静默），step payload
    携六计数键与行集对账两字段（行为 6／11）；`verdict` 帧的**批次落定**由 `orchestration` 协调，
    本块只保证自产部分就位（行为 10）。**2026-10-17 F1 件四**：油田归属对账的机读面＝step payload
    键 `field_attribution_mismatch`（拒收行的被引序号列）——拒收本身走既有删句族信号（`rewritten`
    计数 ＋ `rewrites` 留痕 ＋ `unsupported_claim` notice），维度面另有本键可复算。
    **2026-10-18 V2-94**：定性句放行计数键 `qualitative_kept`（additive——`Verdict` 九键不动）。
    **2026-10-18 V2-116**：`verify_mode`＝如实档位标注（payload 键）；非 `delete` 档下**未删行**，
    故 `unsupported_claim` notice 取**档位诚实**文案（「只记录不删」——检出 ≠ 离场）。
    """
    title = STEP_TITLE_TEMPLATE.format(
        supported=verdict.supported,
        rewritten=verdict.rewritten,
        split=SPLIT_YES if verdict.split else SPLIT_NO,
    )
    record_step(
        state,
        kind=STEP_VERIFY,
        title=title,
        payload=_step_payload(
            verdict,
            rewrites,
            row_note,
            rowset_missing,
            rowset_aligned,
            field_mismatched,
            qualitative_kept,
            verify_mode,
        ),
    )
    if verdict.rewritten:
        _notify(
            state,
            bus,
            NOTICE_UNSUPPORTED_CLAIM,
            (
                NOTICE_UNSUPPORTED_CONTENT.format(rewritten=verdict.rewritten)
                if verify_mode == VERIFY_MODE_DELETE
                else NOTICE_UNSUPPORTED_CONTENT_RECORD_ONLY.format(
                    rewritten=verdict.rewritten, mode=verify_mode
                )
            ),
        )
    if verdict.split:
        _notify(state, bus, NOTICE_CONTRADICTION_SPLIT, NOTICE_CONTRADICTION_CONTENT)
    if not verdict.attribution:
        _notify(
            state,
            bus,
            NOTICE_ATTRIBUTION_SPLIT,
            NOTICE_ATTRIBUTION_CONTENT.format(
                indices=_index_text([int(obs["index"]) for obs in crossed]),
                anchors=_anchor_text(anchors),
            ),
        )
    # `verdict` 帧载荷键集＝`synth/S6-事件与帧目录.md` §一 verdict 行的 `verify` 形
    # （`subtype` 由 `transport` 注入，本模块不写）；行集对账两字段**不入帧**——其落点＝
    # `Verdict` 两字段 ＋ step payload（行为 11／钉 pin-12）。
    bus.emit(
        EVENT_VERDICT,
        {
            PAYLOAD_SUPPORTED_KEY: verdict.supported,
            PAYLOAD_REWRITTEN_KEY: verdict.rewritten,
            PAYLOAD_SPLIT_KEY: verdict.split,
            PAYLOAD_CITED_KEY: list(verdict.cited),
            PAYLOAD_ATTRIBUTION_KEY: verdict.attribution,
        },
    )


def _notify(state: RunState, bus: EventBus, notice_type: str, content: str) -> None:
    """通知双落（状态写口 ＋ `notice` 帧——恰三键 `{type, gates, content}`）。"""
    notice(state, type=notice_type, content=content)
    bus.emit(EVENT_NOTICE, {"type": notice_type, "gates": [], "content": content})


def _step_payload(
    verdict: Verdict,
    rewrites: Sequence[RewriteRecord],
    row_note: str | None,
    rowset_missing: Sequence[int] = (),
    rowset_aligned: bool = True,
    field_mismatched: Sequence[int] = (),
    qualitative_kept: int = 0,
    verify_mode: str = VERIFY_MODE_DELETE,
) -> dict[str, Any]:
    """步 payload（六计数键 ＋ 行集对账四字段 ＋ 改写／缺口留痕 ＋ 行集注记 ＋ 油田归属维度键）。

    行集对账四字段（2026-10-17 EB5c）：`delivered_rows`／`obs_rows` 两计数 ＋ `rowset_missing`
    （缺行序号列）／`rowset_aligned`（引标序对齐）两判据——同一事实的机读面与注记面（`row_note`）
    同批落账（判据单点＝`rules.rowset_audit`，本件只投影）。**2026-10-17 F1 件四**：`field_mismatch`
    键＝油田归属对账拒收行的被引序号列（**升序去重**——判据单点＝`rules.field_attribution_mismatch`）。
    **2026-10-18 V2-94**：`qualitative_kept` 键＝定性句放行行数（承载片段断言零量值记号即保留；
    additive 键——`Verdict` 九键不动，计数判据单点＝`_qualitative_release`）。
    **2026-10-18 V2-116**：`verify_mode`（如实档位）＋ `intended_rewrites`（检出项逐条原句＋原因）
    两 additive 键——非 `delete` 档下检出项**不离场**，交付面＝草稿逐字。
    """
    return {
        PAYLOAD_PHASE_KEY: PHASE,
        PAYLOAD_VERIFY_MODE_KEY: verify_mode,
        PAYLOAD_SUPPORTED_KEY: verdict.supported,
        PAYLOAD_REWRITTEN_KEY: verdict.rewritten,
        PAYLOAD_SPLIT_KEY: verdict.split,
        PAYLOAD_CITED_KEY: list(verdict.cited),
        PAYLOAD_DELIVERED_ROWS_KEY: verdict.delivered_rows,
        PAYLOAD_OBS_ROWS_KEY: verdict.obs_rows,
        PAYLOAD_ROWSET_MISSING_KEY: list(rowset_missing),
        PAYLOAD_ROWSET_ALIGNED_KEY: rowset_aligned,
        PAYLOAD_FIELD_MISMATCH_KEY: sorted(set(field_mismatched)),
        PAYLOAD_QUALITATIVE_KEPT_KEY: qualitative_kept,
        PAYLOAD_ATTRIBUTION_KEY: verdict.attribution,
        PAYLOAD_OK_KEY: verdict.ok,
        PAYLOAD_REWRITES_KEY: _rewrite_entries(rewrites),
        PAYLOAD_INTENDED_REWRITES_KEY: _rewrite_entries(rewrites),
        PAYLOAD_GAPS_KEY: [
            {
                PAYLOAD_GAP_KIND_KEY: gap.kind,
                PAYLOAD_GAP_SUBTASK_KEY: gap.subtask_id,
                PAYLOAD_GAP_REASON_KEY: gap.reason,
            }
            for gap in verdict.gaps
        ],
        PAYLOAD_ROW_NOTE_KEY: row_note,
    }


def _rewrite_entries(rewrites: Sequence[RewriteRecord]) -> list[dict[str, Any]]:
    """改写留痕投影（原句＋原因——`rewrites` 与 `intended_rewrites` 同源，零第二份判据）。"""
    return [
        {
            PAYLOAD_REWRITE_LINE_KEY: record.line,
            PAYLOAD_REWRITE_REASON_KEY: record.reason,
        }
        for record in rewrites
    ]
