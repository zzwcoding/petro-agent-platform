"""过程档案有界摘要段（行为 8——逐字迁移＋显式改动两处）。

真源：`specs/context.md` 接口定义节 `render_process_notes` 签名＋行为 8；逐字迁移载体＝
`appv2/runtime/graph.py` `_render_process_notes`（头注字面、条目行形、预算起算与披露行）；
显式改动＝①去下划线前缀；②`budget` 转显式注入参（**无缺省裸字面**——值＝常量
`PROCESS_NOTES_BUDGET`）；数值真源＝`docs/runtime-refactor/recon/B2-档案渲染与安全闸族.md`
`_PROCESS_NOTES_BUDGET`／`_PROCESS_NOTES_HEADER`。

**段永不作对话轮**：本函数只产文本片段，由调用方拼接（`specs/prompts.md` 行为 16⑤ 只接其
渲染产物入参）；`process_notes` 写入面归 `bookkeeping.note`，本块零写（行为 8／红线）。
"""

from __future__ import annotations

from appv2.runtimev2.state import RunState

# 过程档案预算单点（数值真源 recon/B2 `_PROCESS_NOTES_BUDGET`——数值不落规格，行为 8）。
PROCESS_NOTES_BUDGET = 400

# 头注逐字（真源 recon/B2 `_PROCESS_NOTES_HEADER`；迁移照抄）。
_PROCESS_NOTES_HEADER = "【本 run 已做（过程档案摘要——防重参考，不是作答材料）】"


def render_process_notes(state: RunState, *, budget: int) -> str:
    """`state.process_notes`→有界摘要段（零档案＝零段——调用方跳过，首轮零噪声）。

    头注逐字起；条目行形 `- [{phase}] {title}｜{digest}`（`phase` 缺失＝`?`、
    `title`／`digest` 缺失＝空串——现状缺省回落，迁移照抄）；预算含头注起算、逐条累加、
    超即止（披露行免预算复检——现状固有，源疑点 D-B2-07 如实登记）——超预算追加披露行
    （条数前后账，逐字）并停止。预算＝注入参数 `budget`（数值单点＝`PROCESS_NOTES_BUDGET`）。
    """
    if not state.process_notes:
        return ""
    lines: list[str] = []
    total = len(_PROCESS_NOTES_HEADER)
    for note in state.process_notes:
        line = (
            f"- [{note.get('phase', '?')}] {note.get('title', '')}"
            f"｜{note.get('digest', '')}"
        )
        if total + len(line) + 1 > budget:
            lines.append(
                f"-（过程档案摘要有界截断——已渲染 {len(lines)}/"
                f"{len(state.process_notes)} 条）"
            )
            break
        lines.append(line)
        total += len(line) + 1
    return _PROCESS_NOTES_HEADER + "\n" + "\n".join(lines)
