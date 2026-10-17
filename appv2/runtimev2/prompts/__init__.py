"""指令与提示词：各相位提示词合同常量与各轮指令装配（只出文本，不做判断）

模块卡见 specs/modules.md 的 `## prompts` 一节；规格见 `specs/prompts.md`（形状真源）。
包根即公开面（`specs/modules.md` `## prompts` 卡「公开接口」节＋`specs/prompts.md` 接口定义节）：
合同常量六族（`constants`，名单闭世界）＋装配函数族（卡面两函数逐字照录，族内其余成员
名单闭世界见 `ASSEMBLY_FUNCTIONS`）。四业务相位（理解／澄清／工具匹配／作答）**只经本包根
引用**（R2）——深层子模块私有。

本块只出文本、不做判断：装配＝合同常量与 `state` 投影的确定性拼接（行为 14／15）；
入参只读 `state` 投影＋调用方注入的文本（水位等时间量——本块零时钟接触，B14）；
输出恒为 `str`，缺位走占位文案或空串段两形，不降级、不截断、不编造。

族成员分工（同包不并行——形状真源在本包根，-04b／-04c 只填行为、不另立第二套形状）：
-04a 落合同常量六族＋`assemble_task_book`＋`assemble_answer_prompt`；-04b 落
`anchor_line`／决策轮首入包／决策轮增量条／台账常驻块渲染／分解发射样例渲染器
（`ASSEMBLY_FUNCTIONS` 内其余成员）；-04c 收口元面与边界·保留断言。

**2026-10-17 H 批（角色分家·system 承载位）**：新增四个**规章取件函数**（`ASSEMBLY_FUNCTIONS`
内）——`understand_system_contract`／`clarify_system_contract`／`toolmatch_system_contract`／
`answer_system_contract`：各环节的规章段（文本全部引既有常量、零新写）经
`bookkeeping.call_model(system=…)` 前置进**本次请求**（不入链）；user 位只留动态段。常量族加第七族
`system_background`（`SYSTEM_BACKGROUND`＝链首背景块逐字稿）。真源＝`specs/prompts.md`
2026-10-17 H 批注。
"""

from appv2.runtimev2.prompts.answer_round import (
    answer_system_contract,
    assemble_answer_prompt,
)
from appv2.runtimev2.prompts.constants import (
    ANSWER_DRAFT_CONTRACT,
    ANSWER_REQUIREMENTS,
    CLARIFY_EMISSION_CONTRACT,
    CONTRACT_CONSTANT_FAMILIES,
    JARGON_PLAIN_GLOSSARY,
    SUMMARY_CONTRACT,
    SYSTEM_BACKGROUND,
    TASK_BOOK_EXAMPLES,
    TASK_BOOK_OUTPUT_CONTRACT,
    TASK_BOOK_REDLINE,
    TASK_BOOK_SCENE,
    TASK_BOOK_TASK,
    TOOLMATCH_EMISSION_CONTRACT,
)
from appv2.runtimev2.prompts.decision_round import (
    CLARIFY_FINALIZE_BOUNDARY,
    CLARIFY_PHASE_HEAD,
    DECISION_PHASES,
    GUIDE_REFERENCE_HEAD,
    LEDGER_DICT_NOTE,
    PHASE_CLARIFY,
    PHASE_TOOLMATCH,
    RESIDENT_BLOCK_BEGIN,
    RESIDENT_BLOCK_END,
    TOOLMATCH_PHASE_HEAD,
    anchor_line,
    assemble_decision_increment,
    assemble_decision_package,
    clarify_system_contract,
    render_decompose_example,
    render_ledger_resident_block,
    toolmatch_system_contract,
)
from appv2.runtimev2.prompts.task_book import (
    FAMILY_GLOSS,
    RECOMMENDATION_TEMPLATE,
    assemble_task_book,
    instruction_zone,
    question_segment,
    render_data_zone,
    understand_system_contract,
)

# ── 装配函数族名单闭世界（增删成员须同批对账四消费方规格——`specs/prompts.md` 接口定义节）──
# 签名（卡面两函数已落位；-04b 落族内其余成员，形状不再改——改形状＝回 -04a 或回设计仓）：
#   相位闭世界值（`state.contracts_appended` 标记／相位头行）：`PHASE_CLARIFY`／`PHASE_TOOLMATCH`
#   anchor_line(question, understanding) -> str
#   assemble_decision_package(state, *, phase, guide_text="", today=None, max_subtasks=None,
#                             shared_context=True) -> str
#                                 # 澄清轮必供 max_subtasks（族②合同声明槽）；today＝水位日注入
#                                 # shared_context＝run 级共享上下文（§A 指南段＋台账常驻块）
#                                 # 本次是否注入——判定归编排（同 run 只注一次；2026-10-17 消重批）
#   assemble_decision_increment(state, *, phase, done_text="") -> str
#   render_ledger_resident_block(state) -> str
#   render_decompose_example(metrics, *, today) -> str
#   ── H 批新增（2026-10-17·角色分家）规章取件函数族（system 承载位）──
#   understand_system_contract() -> str          # 指令区＋输出契约区
#   clarify_system_contract(max_subtasks) -> str # 相位①头行＋合同＋finalize 边界句
#   toolmatch_system_contract() -> str           # 相位②头行＋合同
#   answer_system_contract() -> str              # 动词钉死＋【答案要求】＋白话表＋汇总＋起草合同
ASSEMBLY_FUNCTIONS: tuple[str, ...] = (
    "assemble_task_book",
    "assemble_answer_prompt",
    "anchor_line",
    "assemble_decision_package",
    "assemble_decision_increment",
    "render_ledger_resident_block",
    "render_decompose_example",
    "understand_system_contract",
    "clarify_system_contract",
    "toolmatch_system_contract",
    "answer_system_contract",
)

__all__ = [
    "ANSWER_DRAFT_CONTRACT",
    "ANSWER_REQUIREMENTS",
    "ASSEMBLY_FUNCTIONS",
    "CLARIFY_EMISSION_CONTRACT",
    "CLARIFY_FINALIZE_BOUNDARY",
    "CLARIFY_PHASE_HEAD",
    "CONTRACT_CONSTANT_FAMILIES",
    "DECISION_PHASES",
    "FAMILY_GLOSS",
    "GUIDE_REFERENCE_HEAD",
    "JARGON_PLAIN_GLOSSARY",
    "LEDGER_DICT_NOTE",
    "PHASE_CLARIFY",
    "PHASE_TOOLMATCH",
    "RECOMMENDATION_TEMPLATE",
    "RESIDENT_BLOCK_BEGIN",
    "RESIDENT_BLOCK_END",
    "SUMMARY_CONTRACT",
    "SYSTEM_BACKGROUND",
    "TASK_BOOK_EXAMPLES",
    "TASK_BOOK_OUTPUT_CONTRACT",
    "TASK_BOOK_REDLINE",
    "TASK_BOOK_SCENE",
    "TASK_BOOK_TASK",
    "TOOLMATCH_EMISSION_CONTRACT",
    "TOOLMATCH_PHASE_HEAD",
    "anchor_line",
    "answer_system_contract",
    "assemble_answer_prompt",
    "assemble_decision_increment",
    "assemble_decision_package",
    "assemble_task_book",
    "clarify_system_contract",
    "instruction_zone",
    "question_segment",
    "render_data_zone",
    "render_decompose_example",
    "render_ledger_resident_block",
    "toolmatch_system_contract",
    "understand_system_contract",
]
