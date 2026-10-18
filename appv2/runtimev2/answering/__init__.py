"""作答：起草（指令装配＋材料渲染）、真流式收口、引用落账

模块卡见 `specs/modules.md` 的 `## answering` 一节；规格见 `specs/answering.md`（形状与行为真源）；
架构图见 docs/architecture-v3.html。包根即公开面（R2：消费方只经 `appv2.runtimev2.answering` 消费，
深层子模块私有）：

- 相位单入口：`answer(state, *, bus, max_observations=…, supplements=None)`（卡面签名
  `answer(state) -> AnswerDraft`；三处关键词注入面见 `core` 模块注：`bus`＝编排块持有的 per-run
  总线、`max_observations`＝材料帽、`supplements`＝增补面收集列表〔2026-10-17 EB3 D2：收口三块
  不进正文，按原序入该列表由编排层发射〕）；
- 五形状（规格接口定义节 :37–:60 逐字）：`AnswerDraft`／`AnswerSegment`／`Citation`／`Gap`
  （形状单点在 `models`）＋缺口三档闭世界常量 `GAP_KINDS`（`GAP_REFUSED`／`GAP_MISSING`／
  `GAP_UNVERIFIED`）；
- 坏引标剥除单点（2026-10-17 EB5b）：`strip_dangling_citations`（界外引标号整枚离场——同
  `strip_placeholders` 一族；**不判失败**，该行失去引标即由 `verification` 按无据断言处置）；
- 发射剥离单点：`strip_emission_fences`（钉 `pin-04`，P0；`specs/parsing.md` :24 的答案面归属）＋
  发射动作闭世界 `EMISSION_ACTIONS`；**输入侧提取**（2026-10-17 V2-82g 热修）＝
  `extract_finalize_answer`（整应答恰一枚 finalize 发射 JSON 时取回交付字段作草稿原文——
  剥离之前跑，提取属「恢复」非「放行」，合同零新增）；
- 降级与引用簇单点（`RT-W4-06b`）：`degradation` 模块（行为 6／12／13／14／15／16／17 的形态层
  ——矛盾分源／占位符剥离／回声签名／引擎注记／行集交付对账／排名支序；**零语义判断**，豁免面＝
  形态处理／集合成员判定）＋其机读面七键（`PAYLOAD_ECHO_FLAG_KEY`／`PAYLOAD_ENGINE_NOTES_KEY`／
  `PAYLOAD_CONTRADICTION_SEQS_KEY`／`PAYLOAD_ENGINE_ROWS_KEY`／`PAYLOAD_DELIVERED_ROWS_KEY`／
  `PAYLOAD_RANKING_SEQS_KEY`／`PAYLOAD_RANKING_ORDER_OK_KEY`）；**残尾护栏**（2026-10-17 F1 件三＝
  行为 19）：`dangling_tail_closing`＋三处收口短句常量（`TAIL_CLOSE_*`——定稿前悬空结构检测，
  命中即补一句诚实收口，正文其余字面零改）；
- 接线与机读面常量：`MODEL_CALLER`／`PHASE`／`TEXT_EVENT`／`CITATION_EVENT`／`PAYLOAD_*` 键名
  （真源逐条注在 `constants`）；
- 子问题覆盖信号（2026-10-18 V2-119）：`subtask_coverage(subtasks, window, *, subjects, terms)`
  ——逐子问题三 kind 分层形态判据（锚／术语／数值记号是否在渲染窗内出现），零支撑者由
  `prompts` 侧 `assemble_answer_prompt(coverage=…)` 在作答上下文追加提示行（只提示、不替模型
  决定），覆盖表落起草步 payload 键 `subtask_coverage`（additive）。

一句话：把前面查到的**全部子问题结果**整理成**一份答案**——**一段段推给页面（真流式）**、
**每句带出处**、**缺口如实交代**。**语义判断交模型，程序只做结构判据**（引标可解析、分段、
表分派；「答没答上原问题」交模型与 `verification`）。

**边界**（规格「框架与依赖红线」＋卡「依赖」）：无点名框架（R5b）；模型调用经
`bookkeeping.call_model` 单点发起、本块不直引 `gateway_adapter`（R7——import 落点＝
`appv2.runtimev2.bookkeeping` 包根）；只经 `transport` 公开面发帧；材料面只消费 `context` 编译
出口（**零自取**：材料段／Manifest 编译归 `context`，指令文本归 `prompts`）；不直引引擎（R6）；
不引旧码 `appv2.runtime`（R5）；不 import 其它相位（R1）；**相位不直写共享写面**（写面全经
`bookkeeping` 唯一写口）；模型调用步与用量记账由 `call_model` 单点统一记账（本块不为同一调用
重复记模型调用步——本块的答案面步只承载材料面 Manifest 与 `citations`／`gaps` 机读字段，
登记见 `core` 模块注）。**合法降级路径＝无**：闭世界越界一律 fail-closed 抛错。
"""

from appv2.runtimev2.answering.constants import (
    CITATION_BLOCK_HEAD,
    CITATION_EVENT,
    CONTRADICTION_SECTION_HEAD,
    DRAFT_KIND_DIRECT,
    DRAFT_NOTE_TITLE,
    ECHO_CANDIDATE_MARK,
    ECHO_HEAD,
    EMISSION_ACTIONS,
    EMPTY_DRAFT_REASON,
    EXPLORE_REJECT_BODY,
    EXPLORE_STEP_TITLE,
    MODEL_CALLER,
    NOTICE_EMISSION_STRIP,
    NOTICE_MATERIAL_TRUNCATED,
    PAYLOAD_CONTRADICTION_SEQS_KEY,
    PAYLOAD_DANGLING_SEQS_KEY,
    PAYLOAD_DELIVERED_ROWS_KEY,
    PAYLOAD_ECHO_FLAG_KEY,
    PAYLOAD_ENGINE_NOTES_KEY,
    PAYLOAD_ENGINE_ROWS_KEY,
    PAYLOAD_EXPLORE_KEY,
    PAYLOAD_RANKING_ORDER_OK_KEY,
    PAYLOAD_RANKING_SEQS_KEY,
    PAYLOAD_SUBTASK_COVERAGE_KEY,
    ROWSET_OBSERVATION_KINDS,
    SOURCE_SECTION_HEAD,
    TAIL_CLOSE_BARE_HEADING,
    TAIL_CLOSE_LEAD_IN,
    TAIL_CLOSE_TABLE_HEADER,
)
from appv2.runtimev2.answering.core import answer, answer_anchors, subtask_coverage
from appv2.runtimev2.answering.degradation import (
    annotate_window_label,
    dangling_tail_closing,
    echo_flag,
    relative_time_word,
    strip_dangling_citations,
    strip_placeholders,
)
from appv2.runtimev2.answering.emission import extract_finalize_answer, strip_emission_fences
from appv2.runtimev2.answering.models import (
    GAP_KINDS,
    GAP_MISSING,
    GAP_REFUSED,
    GAP_UNVERIFIED,
    AnswerDraft,
    AnswerSegment,
    Citation,
    Gap,
)

__all__ = [
    "CITATION_BLOCK_HEAD",
    "CITATION_EVENT",
    "CONTRADICTION_SECTION_HEAD",
    "DRAFT_KIND_DIRECT",
    "DRAFT_NOTE_TITLE",
    "ECHO_CANDIDATE_MARK",
    "ECHO_HEAD",
    "EMISSION_ACTIONS",
    "EMPTY_DRAFT_REASON",
    "EXPLORE_REJECT_BODY",
    "EXPLORE_STEP_TITLE",
    "GAP_KINDS",
    "GAP_MISSING",
    "GAP_REFUSED",
    "GAP_UNVERIFIED",
    "MODEL_CALLER",
    "NOTICE_EMISSION_STRIP",
    "NOTICE_MATERIAL_TRUNCATED",
    "PAYLOAD_CONTRADICTION_SEQS_KEY",
    "PAYLOAD_DANGLING_SEQS_KEY",
    "PAYLOAD_DELIVERED_ROWS_KEY",
    "PAYLOAD_ECHO_FLAG_KEY",
    "PAYLOAD_ENGINE_NOTES_KEY",
    "PAYLOAD_ENGINE_ROWS_KEY",
    "PAYLOAD_EXPLORE_KEY",
    "PAYLOAD_RANKING_ORDER_OK_KEY",
    "PAYLOAD_RANKING_SEQS_KEY",
    "PAYLOAD_SUBTASK_COVERAGE_KEY",
    "ROWSET_OBSERVATION_KINDS",
    "SOURCE_SECTION_HEAD",
    "TAIL_CLOSE_BARE_HEADING",
    "TAIL_CLOSE_LEAD_IN",
    "TAIL_CLOSE_TABLE_HEADER",
    "AnswerDraft",
    "AnswerSegment",
    "Citation",
    "Gap",
    "annotate_window_label",
    "answer",
    "answer_anchors",
    "dangling_tail_closing",
    "echo_flag",
    "extract_finalize_answer",
    "relative_time_word",
    "strip_dangling_citations",
    "strip_emission_fences",
    "strip_placeholders",
    "subtask_coverage",
]
