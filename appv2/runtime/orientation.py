"""runtime.orientation —— LLM 触点信息装配（V2-58 理解步首轮＋V2-62 轮次任务自足性）。

设计宪法「语义归模型，程序管装配」；**四要素制度（V2-62 起）**：每条发模型的轮次
自带「任务动词／题意锚／产出样例／失败反馈」——新触点按此审查，缺件即装配欠账。

首轮 user 消息＝静态骨架（场景/任务/样例/红线——本模块常量，Owner 逐轮审定，
改格式须过票）＋动态环境（库族/水位/指标名录/术语表/本体速览——渲染器从与程序闸
同源的活体投影现提取，台账改一天这里跟着变）。题干置末、紧邻生成点。
装配规格：tickets/v2/V2-58-理解步信息面治理.md 附 A/B。
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

# ---------- 静态骨架（Owner 2026-10-12 审定逐字——票面附 A 施工基准） ----------

_ORIENT_SCENE = (
    "【场景】你是油田数据问答系统的读题环节（整个管线的第一环）。用户会提出油田生产相关"
    "的问题：有的要查台账数值，有的要查报告里的事实，有的是判断、纠错、解释类。你之后系统"
    "将依次经过：澄清拆解（按题意拆子问题）→ 定案（为每个子问题选查数链或报告检索链）→ "
    "检索执行 → 答案起草 → 逐条核验（引标与数值对材料）→ 交付。你本环节不回答问题、不选"
    "工具、不执行任何检索——只把题读准。"
)

_ORIENT_TASK = (
    "【你的输出与它的消费方式】输出固定两行，格式强制：\n"
    "第一行「理解：〈一句话〉」——它是后续所有环节的题意锚：澄清按它拆子问题，核验按它"
    "判断是否答全，交付按它对题。要求：忠实复述题干要求；题干分①②③的照数保留，不添加"
    "题干没有的要求，不遗漏列举项。\n"
    "第二行「指标候选：〈逗号分隔〉」——它是后续取数的指标白名单：定案环节填报的指标名"
    "必须逐字出自本行，不在本行里的指标会被程序闸直接拦下。要求：只从下方《台账指标名录》"
    "里选；题干用口语或别名的，换成术语表指向的正名；题干不涉及数值取数（判断／解释／"
    "纠错类）写「指标候选：无」。\n"
    "唯一例外（纯寒暄直答）：你的判断只有一个——这句话是否可能与油田数据业务有关"
    "（业务范围见下方【本系统】）。只要可能有关——哪怕只有一点关联、哪怕问得含糊、"
    "哪怕你拿不准——就照常输出两行，把题意读准：是否需要向用户澄清、走哪条链取数，"
    "都由后续环节判断。\n"
    "只有确定与业务毫无关系的话（寒暄、道谢、道别，或与油田数据毫无关系的闲聊），"
    "才输出一行「直接回答：〈以油田数据问答助手的身份友好回应，并自然引导到油田数据"
    "话题〉」；此时上面两行都不输出。"
)

_ORIENT_EXAMPLES = (
    "【样例】（格式与取舍以这三个为准）\n"
    "样例一（多部分题）：\n"
    "问题：第一章载明本月抽油机时率 95.0% 及其损失构成。请：①逐项列出五项时率损失各占的"
    "百分点数；②第一章构成中的\"计划性检泵 0.6 个百分点\"与第二章说明三里哪两口井直接对应？"
    "这两口井的作业在\"当月躺井井次\"与\"检泵作业井次\"两个统计中各计不计入？③辨析：第一章中"
    "\"0.6 个百分点\"一共在两处出现（环比提高 0.6 个百分点／计划性检泵占 0.6 个百分点），两者"
    "含义是否相同？\n"
    "输出：理解：问①逐项列出本月抽油机时率 95.0% 的五项损失构成各占的百分点数；②第一章"
    "\"计划性检泵 0.6 个百分点\"对应第二章说明三的哪两口井，及这两口井的作业在\"当月躺井井次\""
    "与\"检泵作业井次\"统计中各计不计入；③辨析第一章两处\"0.6 个百分点\"（环比提高／计划性"
    "检泵占比）含义是否相同。\n"
    "指标候选：抽油机时率\n"
    "（要点：①②③逐项保留不合并；只有①涉及台账取数——候选只收它；②③是报告事实，"
    "不进候选行。）\n"
    "样例二（口语映射题）：\n"
    "问题：上月躺井的那几口井，日产油和时率怎么样？\n"
    "输出：理解：问上月停产待检泵（躺井）井的日产油量与抽油机时率。\n"
    "指标候选：日产油量,抽油机时率\n"
    "（要点：躺井按术语表转正名写进理解行，但「停产待检泵井次」是报告统计不是台账指标，"
    "不进候选；日产油、时率按名录与术语表转正名后进候选。）\n"
    "样例三（判断纠错题）：\n"
    "问题：判断并纠正这句话：\"Y-41 井本月抽油杆在第 41 根处断裂躺井，并于当月完成了螺旋"
    "气锚加装。\"这句话有哪几处与报告不符？逐一纠正，并给出 Y-41 井在报告中的真实状态"
    "（所属清单、预警类型、首次发现时间、当前安排），以及本月真正实施气锚加装的井号。\n"
    "输出：理解：判断并纠正关于 Y-41 井抽油杆断裂躺井及螺旋气锚加装的陈述，列出其与报告"
    "不符之处，并给出 Y-41 井的真实状态及本月真正实施气锚加装的井号。\n"
    "指标候选：无"
)

_ORIENT_REDLINE = (
    "【红线】只输出上述两行，不回答问题本身；指标候选不得出现名录里没有的名字。"
)

# 库族机器名 → 中文名（族名由库面动态给出，中文语义是系统固定约定）。
FAMILY_GLOSS: dict[str, str] = {
    "completion": "完井工程报告",
    "monthly": "月报",
    "dynamic": "生产动态",
}


# ---------- 动态渲染器（源＝与程序闸同源的活体投影） ----------

def render_metric_lines(metrics: list[dict[str, Any]]) -> list[str]:
    """指标名录行（Owner 定稿措辞）：slot｜单位｜状态——bound 可出数；
    unbound「未绑定（台账无数值——数值走报告检索）」。"""
    lines: list[str] = []
    for m in metrics:
        unit_m = re.search(r"单位 ([^｜]+)｜", str(m.get("value", "")))
        unit = unit_m.group(1).strip() if unit_m else ""
        state = ("可出数" if m.get("binding_state") == "bound"
                 else "未绑定（台账无数值——数值走报告检索）")
        slot = str(m.get("slot", ""))
        lines.append(f"{slot}｜{unit}｜{state}" if unit else f"{slot}｜{state}")
    return lines


def render_term_lines(terms: list[dict[str, Any]]) -> list[str]:
    """术语表行（每条自足）：禁用词给替代名＋定义；别名给映射；纯定义型给一句式定义
    （定义取 value「）：」后、「（时效」前）。"""
    lines: list[str] = []
    for t in terms:
        value = str(t.get("value", ""))
        parts = value.split("）：", 1)
        definition = parts[1].rsplit("（时效", 1)[0].strip("；。 ") if len(parts) > 1 else ""
        term = str(t.get("term", ""))
        if t.get("banned"):
            alt_m = re.search(r"替代：([^）]+)", value)
            alt = alt_m.group(1).strip() if alt_m else "?"
            lines.append(
                f"{term}＝禁用词！正确名「{alt}」（{definition}）" if definition
                else f"{term}＝禁用词！正确名「{alt}」"
            )
            continue
        arrow = re.search(r"→\s*([^·）]+)", value)
        if arrow:
            lines.append(f"{term}＝{arrow.group(1).strip()}")
        elif definition:
            lines.append(f"{term}＝{definition}")
        else:
            lines.append(term)
    return lines


def render_relation_lines(relations: list[dict[str, Any]]) -> list[str]:
    """关系行：「链路（人话注解）」——value 按「——」切前后。"""
    lines: list[str] = []
    for r in relations:
        value = str(r.get("value", ""))
        parts = value.split("——", 1)
        chain = parts[0].replace(" ", "")
        gloss = f"（{parts[1].strip()}）" if len(parts) > 1 else ""
        lines.append(chain + gloss)
    return lines


def thin_object_lines(objects: list[dict[str, Any]]) -> list[str]:
    """对象薄行（回退形——组合根未注入本体摘要时用台账 dump.objects 草案行）。"""
    lines: list[str] = []
    for o in objects:
        obj = str(o.get("obj", ""))
        attrs = str(o.get("value", "")).split("：", 1)[-1].strip()
        lines.append(f"{obj}：{attrs}" if attrs and "未列属性" not in attrs else obj)
    return lines


def iso_day(value: Any) -> str:
    """水位日统一呈 ISO 日串（date→isoformat；callable 求值；其余 str）。"""
    if value is None:
        return ""
    if callable(value):
        value = value()
    if value is None:
        return ""
    iso = getattr(value, "isoformat", None)
    return iso() if iso is not None else str(value)


def build_understand_instruction(
    *,
    question: str,
    dump: dict[str, Any] | None,
    object_lines: list[str] | None,
    watermark_date: Any,
    today: Any,
) -> str:
    """节点侧装配入口（graph.understand 消费——缝缺省全部就地兜底零漂移）。

    dump 缺省＝空投影；object_lines None＝台账 dump.objects 薄形回退
    （组合根注入本体摘要时传实摘要行）；水位缝缺省回退 deps.today。
    """
    dump = dump or {}
    lines = (
        object_lines if object_lines is not None
        else thin_object_lines(list(dump.get("objects") or []))
    )
    families = sorted({
        f
        for tags in (dump.get("families_map") or {}).values()
        for f in tags
    })
    return assemble_understand_turn(
        question=question,
        families=families,
        watermark=iso_day(watermark_date) or iso_day(today),
        metric_lines=render_metric_lines(list(dump.get("metrics") or [])),
        term_lines=render_term_lines(list(dump.get("terms") or [])),
        object_lines=lines,
        relation_lines=render_relation_lines(list(dump.get("relations") or [])),
    )


def render_decompose_example(metrics: list[dict[str, Any]], *, today: Any) -> str:
    """分解发射填写样例（V2-59 一补——运行时动态装配，不进合同）。

    P-039 命名闸（合同零业务名词——井号形/数字段/台账真源汉字连串）使「填真名
    样例」结构性不能进合同常量；本渲染器在澄清节点拼指令时从活体台账现造：
    取首条未绑定指标（演示 knowledge 链路由——与 V2-56 回炉路由动词一致），
    无未绑定取首条可出数（data 链形）。窗＝today−30 天 ~ today（默认近 30 天示意）。
    台账空投影返回空串（调用方跳过—— degraded 面不造空样例）。
    """
    ordered = sorted(
        metrics, key=lambda m: 0 if m.get("binding_state") == "unbound" else 1
    )
    if not ordered:
        return ""
    pick = ordered[0]
    slot = str(pick.get("slot", ""))
    unbound = pick.get("binding_state") == "unbound"
    binding = "未绑定" if unbound else "在册可出数"
    chain = "knowledge" if unbound else "data"
    tool = "doc_retrieve" if unbound else "data_query"
    day = today() if callable(today) else today
    if not hasattr(day, "year"):
        day = date.fromisoformat(str(day))
    window = f"{(day - timedelta(days=30)).isoformat()}~{day.isoformat()}"
    payload = (
        '{"action": "decompose", "question_group": {"subtasks": [{"id": "s1", '
        '"question": "' + slot + '是多少？", "ledger_notes": '
        '"' + slot + "｜" + binding + "｜" + window + '", "chain": "' + chain + '", '
        '"tool": "' + tool + '"}]}}'
    )
    return (
        "填写样例（分解形——五键齐全，ledger_notes 逐字转抄台账全量块，"
        f"窗为示意按窗词锚定表现算）：{payload}"
    )


def assemble_understand_turn(
    *,
    question: str,
    families: list[str],
    watermark: str,
    metric_lines: list[str],
    term_lines: list[str],
    object_lines: list[str],
    relation_lines: list[str],
) -> str:
    """首轮 user 消息装配（附 B 装配顺序）：场景→任务→样例→环境→红线→题干（末尾）。"""
    fam_line = "、".join(f"{f}（{FAMILY_GLOSS.get(f, '?')}）" for f in families) or "（暂无族标注）"
    metric_block = "\n".join("  " + line for line in metric_lines) or "  （空）"
    term_block = "\n".join("  " + line for line in term_lines) or "  （空）"
    object_block = "\n".join("  " + line for line in object_lines) or "  （空）"
    relation_block = "\n".join("  关系：" + line for line in relation_lines) or "  关系：（空）"
    environment = (
        "【环境】（以下由系统按当前数据现状动态装配）\n"
        "【本系统】（事实描述——业务相关性的判断依据）\n"
        "本系统是油田生产与管理数据的问答系统：围绕油田、井、区块的生产与管理数据，"
        "以及完井工程、生产动态、月报等报告中的事实，做查询、检索与解读。\n"
        "台账指标、术语与本体对象的具体清单见下方——它们是后续环节取数的依据；"
        "你判断相关性只看领域是否沾边。\n"
        "数据止于下方水位日。\n"
        f"- 资料库族：{fam_line}——报告事实（完井参数／月报统计／生产动态／治理事件）都在这里。\n"
        f"- 数据水位：{watermark or '（水位未取得）'}——题干中「本月／去年」等时间词以该日为锚。\n"
        f" - 台账指标名录（{len(metric_lines)} 条——名字｜单位｜状态，可出数＝数值在台账；"
        "未绑定＝有名字暂无数值）：\n"
        f"{metric_block}\n"
        f" - 术语表（{len(term_lines)} 条——口语／别名 → 正名；纯定义型给一句式定义）：\n"
        f"{term_block}\n"
        f" - 本体速览（解构用户问题的依据——用户说的名词对到对象，动作对到关系，取数对到指标）：\n"
        f"  对象：\n{object_block}\n{relation_block}"
    )
    return "\n\n".join([
        _ORIENT_SCENE,
        _ORIENT_TASK,
        _ORIENT_EXAMPLES,
        environment,
        _ORIENT_REDLINE,
        f"【待解构的题干】\n{question}\n（先判与业务的相关性：可能有关＝两行式；"
        "确定无关的寒暄闲聊＝直答。现在输出。）",
    ])


# ---------- V2-62 轮次任务自足性（答案轮三件套/题意锚行/观察字段） ----------

_ANSWER_REQUIREMENTS = (
    "逐条事实断言带 [n] 引标（n＝观察材料序号）；材料未覆盖的部分不得断言、如实说明"
    "未覆盖；材料含多个来源（不同报告／油田／井）时逐个来源分别作答（不冲突也要分别"
    "列出，不以反问代替作答）；作答后仍有未覆盖的来源或指代不明处，如实点名未覆盖"
    "来源（含检索窗注记的未进窗来源）并请用户补充检索或指明对象，不静默略过；引擎的"
    "降级/未绑定/拦停注记必须如实转述进对应子问题"
    "条目（不得静默丢弃）；引用观察材料请摘录必要短语并带引标，禁整段照搬原文充当回答；"
    "「理解：／指标候选：」及任何动作 JSON 是过程产物，出现在答案中即废品。"
)


def answer_turn_preamble(question: str) -> str:
    """写答案轮三件套置顶（题目锚/动词钉死/答案要求——V2-61 方案附 A 逐字）。"""
    return (
        f"用户问题：{question}\n"
        "现在：写最终答案交付用户。本步是写答案步——不再做任何决策、不再发射任何"
        "动作指令（finalize/decompose 等动作出现即废品）。\n"
        f"【答案要求】{_ANSWER_REQUIREMENTS}\n"
    )


def assemble_answer_instruction(
    *,
    question: str,
    summary_contract: str,
    subtask_list: str,
    answer_instruction: str,
) -> str:
    """写答案轮指令装配（四相位消费——三件套置顶，既有字面依次居中/垫底）。"""
    return (
        answer_turn_preamble(question)
        + "\n"
        + summary_contract
        + "\n子问题结果清单：\n" + subtask_list
        + "\n\n" + answer_instruction
    )


def anchor_line(question: str, understanding: str = "") -> str:
    """题意锚行（决策轮标准装配件——原题与理解置于当轮，免长历史考古）。"""
    if understanding:
        return f"用户原题：{question}｜题意：{understanding}"
    return f"用户原题：{question}"


def echo_signature_hit(draft: str) -> bool:
    """回声签名（只记不拦——V2-58 方案附 D）：模板头即过程废品特征。"""
    first = draft.split("\n", 1)[0].strip()
    return first.startswith("理解：") or ("指标候选" in draft[:100])


def paste_ratio(draft: str, observations: list[dict[str, Any]]) -> float:
    """粘贴重合占比（只记不拦）：草稿与任一观察 content 的 60 字窗口逐字重合
    最大长度 ÷ 草稿长度（窗口步进 40；零观察/空草稿＝0.0）。"""
    if not draft:
        return 0.0
    best = 0
    for obs in observations:
        content = str(obs.get("content", ""))
        if len(content) < 60:
            continue
        for i in range(0, len(content) - 59, 40):
            if content[i:i + 60] in draft:
                best = max(best, 60)
                break
    return round(min(best / len(draft), 1.0), 4)
