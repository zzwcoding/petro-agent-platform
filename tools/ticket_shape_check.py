#!/usr/bin/env python3
"""sdd-flow ticket-shape 闸：派发前机检派工单/票面形状。

来源：sdd-flow skill 的 references/ticket-shape-check.py
用法：复制到目标仓库 tools/ticket_shape_check.py；
      CI 派发步骤前或 L0 自检时 `python3 tools/ticket_shape_check.py <票文件.md>`。
契约：sdd-flow references/ticket-gates.md「闸一」。

判定边界（只判形状，不判语义）：
- 必备字段节（任务/先读/验收/回报）缺一 FAIL
- 红线字段（框架红线/边界红线）缺一 FAIL（"无点名框架/按默认边界规则"是合法显式值）
- 验收节空/无判据关键词黑名单 FAIL
- 全文含"拍板/裁决/已定"类词却无任何引用形（来源标注/引号原文块）FAIL
- 方案决策授权词（视情况/自行设计/自己决定…）FAIL——方案决策属拆票（L0 策略亲征），不许下放
- 施工基准：含"逐字/措辞/替换为/追加段/行为定义"类施工指令却无逐字稿载体
  （引用块/>/```代码块/「原文」引号）FAIL——意图级票面逼子代理自行设计措辞
  （Owner 2026-10-10 固化：票面即交接，交接必须自足）
退出码：0=绿；1=红（FAIL 明细打印到 stdout）。
"""
import re
import sys
from pathlib import Path

FAILS: list[str] = []

REQUIRED_FIELDS = {
    "任务": re.compile(r"^#*\s*任务[:：]?\s*\S", re.M),
    "先读": re.compile(r"先读[:：]", re.M),
    "验收": re.compile(r"验收[:：]", re.M),
    "回报": re.compile(r"回报[:：]", re.M),
}
REDLINE_FIELDS = {
    "框架红线": re.compile(r"框架红线[:：]", re.M),
    "边界红线": re.compile(r"边界红线[:：]", re.M),
}
EMPTY_ACCEPTANCE = re.compile(r"验收[:：]\s*(回报|见上|$)", re.M)
NO_CRITERIA = re.compile(r"完成后汇报即可|完成后说明|随意|看着办")
DECISION_WORDING = re.compile(r"拍板|裁决|已定|Owner\s*确认", re.I)
CITATION = re.compile(r"〔来源[:：][^〕]+〕|「[^」]{6,}」")
SCHEME_HANDOFF = re.compile(r"视情况|自行设计|自己决定|自行(选择|判断)|按需(设计|决定)")
CROSS_DOMAIN = re.compile(r"跨域|多个模块|多模块|大改|架构级|大规模重构")
MID_REVIEW_DECLARED = re.compile(r"中途审查|审查拍")
# 施工指令词（排除验收常用语：逐字段/逐字可查/逐字落字/措辞不如实类缺陷描述）
VERBATIM_NEED = re.compile(r"逐字(?!段|落|可|查|比对|一致|在场)|措辞(?!不|如|随|同步)|替换为|追加段|行为定义")
# 逐字稿载体：引用块/代码块/「原文」引号/票面附节指针
VERBATIM_BLOCK = re.compile(r"^> ?\S|^＞ ?\S|```|「[^」]{6,}」|见票面附\s*[0-9０-９]|附\s*[1-9０-９][：:]", re.M)


def check(text: str, name: str) -> None:
    for label, rx in REQUIRED_FIELDS.items():
        if not rx.search(text):
            FAILS.append(f"{name}: 缺必备字段「{label}」")
    for label, rx in REDLINE_FIELDS.items():
        if not rx.search(text):
            FAILS.append(f"{name}: 缺红线字段「{label}」（写显式'无'也是合法值，缺字段不是）")
    acc = re.search(r"验收[:：](.+?)(?:\n\s*\S|$)", text, re.S)
    if EMPTY_ACCEPTANCE.search(text) or (acc and NO_CRITERIA.search(acc.group(1))):
        FAILS.append(f"{name}: 验收节为空或无判据句")
    if DECISION_WORDING.search(text) and not CITATION.search(text):
        FAILS.append(f"{name}: 含拍板/裁决表述却无任何来源引用形（子代理被迫考古）")
    for m in SCHEME_HANDOFF.finditer(text):
        FAILS.append(f"{name}: 含方案决策授权词「{m.group(0)}」——方案决策属拆票（L0），不许下放")
    if CROSS_DOMAIN.search(text) and not MID_REVIEW_DECLARED.search(text):
        FAILS.append(
            f"{name}: 声明跨域/大改却未预挂「中途审查拍」"
            "（T3 触发线，ticket-gates.md 闸三）"
        )
    task_seg = re.split(r"先读[:：]", text, maxsplit=1)[0]  # 只查任务段——验收节的
    # 「逐字可查/逐字比对」类判据不算施工指令
    if VERBATIM_NEED.search(task_seg) and not VERBATIM_BLOCK.search(task_seg):
        FAILS.append(
            f"{name}: 任务段含施工指令（逐字稿/措辞定稿/替换/追加段/行为定义）却无"
            "逐字稿载体（引用块/代码块/「原文」引号/票面附节指针）"
            "——意图级票面逼子代理自行设计（Owner 2026-10-10 固化）"
        )


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    for arg in sys.argv[1:]:
        path = Path(arg)
        if not path.is_file():
            FAILS.append(f"{arg}: 文件不存在")
            continue
        check(path.read_text(encoding="utf-8"), path.name)
    for f in FAILS:
        print(f"FAIL {f}")
    print(f"ticket-shape: {'GREEN' if not FAILS else f'{len(FAILS)} FAIL'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
