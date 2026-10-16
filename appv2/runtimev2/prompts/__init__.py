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
本票（-04a）落合同常量六族＋`assemble_task_book`＋`assemble_answer_prompt`；
`anchor_line`／决策轮首入包／决策轮增量条／台账常驻块渲染／分解发射样例渲染器
（`ASSEMBLY_FUNCTIONS` 内其余成员）的行为断言归 `RT-W2-04b-prompts.md`，元面与
边界·保留收口归 `RT-W2-04c-prompts.md`。
"""

from appv2.runtimev2.prompts.answer_round import assemble_answer_prompt
from appv2.runtimev2.prompts.constants import (
    ANSWER_DRAFT_CONTRACT,
    ANSWER_REQUIREMENTS,
    CLARIFY_EMISSION_CONTRACT,
    CONTRACT_CONSTANT_FAMILIES,
    SUMMARY_CONTRACT,
    TASK_BOOK_EXAMPLES,
    TASK_BOOK_OUTPUT_CONTRACT,
    TASK_BOOK_REDLINE,
    TASK_BOOK_SCENE,
    TASK_BOOK_TASK,
    TOOLMATCH_EMISSION_CONTRACT,
)
from appv2.runtimev2.prompts.task_book import (
    FAMILY_GLOSS,
    assemble_task_book,
    instruction_zone,
    question_segment,
    render_data_zone,
)

# ── 装配函数族名单闭世界（增删成员须同批对账四消费方规格——`specs/prompts.md` 接口定义节）──
# 签名（卡面两函数已落位；族内其余成员的形状随本清单落位，行为断言归 -04b）：
#   anchor_line(question, understanding) -> str
#   assemble_decision_package(state, *, phase, guide_text, ...) -> str
#   assemble_decision_increment(state, *, phase, done_text, ...) -> str
#   render_ledger_resident_block(state) -> str
#   render_decompose_example(metrics, *, today) -> str
ASSEMBLY_FUNCTIONS: tuple[str, ...] = (
    "assemble_task_book",
    "assemble_answer_prompt",
    "anchor_line",
    "assemble_decision_package",
    "assemble_decision_increment",
    "render_ledger_resident_block",
    "render_decompose_example",
)

__all__ = [
    "ANSWER_DRAFT_CONTRACT",
    "ANSWER_REQUIREMENTS",
    "ASSEMBLY_FUNCTIONS",
    "CLARIFY_EMISSION_CONTRACT",
    "CONTRACT_CONSTANT_FAMILIES",
    "FAMILY_GLOSS",
    "SUMMARY_CONTRACT",
    "TASK_BOOK_EXAMPLES",
    "TASK_BOOK_OUTPUT_CONTRACT",
    "TASK_BOOK_REDLINE",
    "TASK_BOOK_SCENE",
    "TASK_BOOK_TASK",
    "TOOLMATCH_EMISSION_CONTRACT",
    "assemble_answer_prompt",
    "assemble_task_book",
    "instruction_zone",
    "question_segment",
    "render_data_zone",
]
