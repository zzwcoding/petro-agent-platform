"""决策轮装配（锚行／相位首入包／每轮增量条）＋台账常驻块＋分解发射样例——只出文本、零判断。

真源＝`specs/prompts.md` 行为 6–10／16（本模块行为簇）；逐字稿载体（迁移照抄、承载位换、
文本不变——`arch/P6b` A-P6b-24/34「文本常量与渲染函数零变化、只换承载位」）：

- 题意锚行＝`appv2/runtime/orientation.py` `anchor_line`（L320-323）；
- 相位首入包（锚行→相位头行→相位合同→〔澄清轮〕分解样例／〔匹配轮〕合同内嵌样例→§A 指南段
  →〔匹配轮〕问题组 JSON→〔投影非空时〕台账常驻块尾附）＝`appv2/runtime/graph.py`
  `clarify_node`（instruction L2354-2373＋尾附 L2379-2384）／`toolmatch_node`（L2698-2729）；
- 每轮增量条（澄清轮五件：探查预算／回炉／用户补充／拒因回喂／已做段；匹配轮两件：拒因回喂／
  已做段）＝同两节点 `tail_parts` 段（clarify L2385-2421；toolmatch L2710-2731）；回炉行渲染＝
  嵌套 `_rework_line`（L2396-2404）；
- 台账常驻块＝同文件 `_resident_block`（L1337-1347）＋`_resident_sources`（L1308-1333）三块行渲染；
  BEGIN／END 标记与字典头注 V1 另载 `appv2/tools/ledger.py`（L151-152）／`appv2/runtime/context.py`
  （L54-59）——V2 定界＝「固定包裹文本＋逐字转抄渲染归本块」（`specs/context.md`「不做什么」表；
  `specs/prompts.md` 风险 3），故三标记在**本模块落单点**、不引 V1 载体（R3：本块只 import
  `state`）；
- 分解发射样例＝`appv2/runtime/orientation.py` `render_decompose_example`（L199-228）。

显式差异（V1→V2，逐条带真源）：
①分解样例改 `json.dumps` 现造——V1 字符串拼接无转义（D-L2a-13 病灶）产出的非法 JSON 不复现；
②样例空串时不留悬空空行（V1 D-E1-11「连续空行占位」不迁移——空串＝该段缺位、调用方跳过）；
③时间量只经 `today` 入参注入（V1 读 `deps.watermark()`／`deps.today`——本块零时钟接触，B14）；
④常驻块三块行渲染只读结构化投影值串（V1 `render_ledger_rows` 同款：零正则、零筛选、零改写）；
⑤分解样例区补**无台账命中形全样例行**（2026-10-17 补·分解样例补行）——V1 样例只有锚定指标形一条、
无命中形仅头行一句说明，模型知形而无整行可照抄；V2 追加第二条全样例行＋头行补句「三段照抄上形」
（逐字稿合法形真源 `specs/clarification.md` 行为 8①③；真机证据 `docs/runtime-refactor/ladder/L3/06`
run-b5b6b056：r1 段尾加解释→段数非三、r2 绑定态/窗段自造形越界，三轮烧光）。

入参纪律：装配＝`state` 投影＋调用方注入文本（`guide_text`／`done_text`／`today`／`max_subtasks`
／`shared_context`）；输出恒为 `str`——缺位走**空串段**（调用方跳过）或**占位文案**，不降级、
不截断、不编造、不静默。

**run 级共享上下文（§A 指南段＋台账常驻块）只注一次**（2026-10-17 补·真机消重批）：两段共享
上下文在**同一 run 的决策链里共出现一次**——挂第一次决策装配（澄清相位首入包），后续决策调用
（匹配轮首入包／回炉轮）不再重复注入：链是追加形（pin-22），模型从链首可见前文，语义零损失，
重复的两份＝纯重复 token（真机 `docs/runtime-refactor/ladder/L3/07` run-919ed881：末轮 answer
prompt 19359 tokens 里 §A 全文与台账全量块各两遍）。**注入与否的判定归编排**（`orchestration`
按 `state.contracts_appended` 判「本 run 是否已注」后经 `shared_context` 下传）——本模块只按该
标志拼／不拼两段文本，自身零判断（行为 15；「何时追加＝调用方义务」同款分工）。

**何时追加增量条整条＝调用方义务**（编排面，`specs/prompts.md` 行为 16）：本模块只供条文本与
条内自身条件（①仅非首入轮／②仅存在重跑档失败子问题〔`bad_args`／`retryable`〕／
③user_hint 非空／④decision_error 非空／⑤调用方传入文本原样在场）。

**2026-10-17 H 批（角色分家·system 承载位）**：决策轮原一条 user 包拆两路——**规章段**（相位头行＋
相位合同正文＋〔澄清轮〕finalize 交付面边界句）＝`clarify_system_contract`／
`toolmatch_system_contract`，
经 `bookkeeping.call_model(system=…)` **随本次请求走**（前置一条 system 条、不入链、回炉轮亦在场）；
**动态段**（锚行／分解样例／§A 指南段／台账常驻块／问题组 JSON）＝`assemble_decision_package`，
仍作 user 条入链（相位一次性 `pin-24` 不变）。文本零改、矩阵内相对序零改。
**共享上下文留链的判据**：§A 与台账常驻块是**run 级一次性**注入（2026-10-17 消重批"F1"）——其
一次性语义的前提是「链为追加形、模型从链首可见前文」；若改随规章走 per-call system 前缀，
则后续决策调用（§A 段与常驻块按判定整段缺席）将**再也看不见**这两段（语义净损失 + 每调用重付
token），故两段**留在 user 链**（与开票 §4② 的取件清单有意不同——见票面「共享上下文」注）。
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import date, datetime, timedelta
from typing import Any

from appv2.runtimev2.prompts.constants import (
    CLARIFY_EMISSION_CONTRACT,
    TOOLMATCH_EMISSION_CONTRACT,
)
from appv2.runtimev2.prompts.task_book import _projection, _rows
from appv2.runtimev2.state import MAX_DISCOVERS_PER_RUN, RunState

# ── 相位闭世界（值＝`state.contracts_appended` 的相位标记，同 V1 节点名——pin-24 记账面）──
PHASE_CLARIFY = "clarify"
PHASE_TOOLMATCH = "toolmatch"
DECISION_PHASES: frozenset[str] = frozenset({PHASE_CLARIFY, PHASE_TOOLMATCH})
_PHASES_TEXT = "／".join(sorted(DECISION_PHASES))

# ── 相位头行（逐字迁移——graph.py L2356-2358／L2700-2701；族②③常量本体不载此两行）──
# 相位合同＝头行＋合同正文（正文＝`constants` 族②／族③）；头行声明本相位动作闭世界
# （任务动词要素面——A-P4b-56「四要素制度」）。
CLARIFY_PHASE_HEAD = (
    "【相位①·业务澄清——本相位唯一有效发射合同（.action 只许 "
    "discover|decompose|ask|finalize；指南正文中出现的 execute 动作"
    "归后续相位，本相位发射它＝非法）】"
)
TOOLMATCH_PHASE_HEAD = "【相位②·工具匹配——本相位唯一有效发射合同（只许输出 matches JSON）】"

# ── §A 指南段消歧头（**两轮统一同一字面**——graph.py L2368-2370／L2703-2705 逐字；A-P4b-33）──
# 字面单点不变（行为 9：两轮装配头行同字面）；**落链次数**＝run 内一次（2026-10-17 补·真机
# 消重批——头行与其后 §A 正文同属 run 级共享上下文，随 `shared_context` 标志整段进出）。
GUIDE_REFERENCE_HEAD = (
    "【业务规则参考（ontology 指南 §A——窗词锚定/单井红线/"
    "三链路由；动作类措辞以上方合同为准）】"
)

# ── 澄清轮 finalize 交付面边界句（逐字迁移——graph.py L2368-2372；P-051b 真批修正面）──
CLARIFY_FINALIZE_BOUNDARY = (
    "【finalize 交付面边界——台账常驻注入不进交付面（不计入"
    "「材料足够」）：仅凭注入就能回答的术语/口径定义问，先 discover "
    "semantic_query 取条目卡再定稿；零探查观察时禁 finalize。】"
)

# ── 台账常驻块固定包裹文本（逐字迁移——tools/ledger.py L151-152＋runtime/context.py L54-59）──
RESIDENT_BLOCK_BEGIN = "〖台账全量·常驻注入（ledger_dump 族）〗"
RESIDENT_BLOCK_END = "〖/常驻注入〗"
LEDGER_DICT_NOTE = (
    "（台账全量是字典不是数据：本块只载指标/术语/对象的定义、粒度与绑定态，"
    "不载任何数值——「在台账」不等于「数值在手」；数值一律经检索执行取得，"
    "禁止仅凭本块 finalize 定稿。）"
)
# 三块标签（逐字迁移——graph.py `_resident_sources` L1308-1333 的 label 三件）。
_LEDGER_BLOCK_LABEL = "台账全量（指标/术语/对象/关系/族标注）"
_ALIAS_BLOCK_LABEL = "别名表"
_CARD_BLOCK_LABEL = "数据资产结构卡"

# ── 增量条文本（逐字迁移——clarify L2386-2419／toolmatch L2711-2719）────────────────
_BUDGET_LINE = "探查预算：全 run ≤{cap} 次，已用 {used} 次。"
_REWORK_HEAD = "回炉：只分解以下失败/缺失子问题（成功子问题结果已保留，禁止重复分解执行）："
_REWORK_LINE = "- [{id}] {question}——拒因：{reason}"
# 改道后缀（V2-56 回炉行路由动词——触发＝机器拒因原文的**闭世界子串校**（`arch/P6b` A-P6b-05：
# 机器拒因面零改动），属行为 15 豁免面「逐字子串校」，非语义词表）。
_REROUTE_SUFFIX = "→改走 knowledge 链（tool=doc_retrieve）"
_REROUTE_TRIGGERS: tuple[str, ...] = ("未绑定", "不在台账")
_HINT_LINE = "用户已补充：{hint}——请把它落进本轮分解。"
# 回喂壳两件（前缀／尾件）**本块单点**：拒因回喂行＝壳＋拒因＋壳尾。
# **2026-10-16 补（流水 66·叠字病灶）**：槽位对账拒因载荷**自带整套壳体**（真源
# `specs/clarification.md` 行为 8 与「接口定义」错误契约——头行「上次发射被拒：ledger_notes…」＋
# 尾行「——修正后重新输出 JSON。」，流水 64 裁），再套一次即叠字（真机 run-18e5d273：
# 「上次发射被拒：上次发射被拒：…」「——修正后重新输出 JSON。——修正后重新输出 JSON。」）。
# 故回喂行对**已自带壳者原样透传**（`_rejection_feedback_line`）——回喂文本壳恰一遍，
# 拒因载荷与模型所见同形（一本账）。
_REJECTION_HEAD = "上次发射被拒："
_REJECTION_TAIL = "——修正后重新输出 JSON。"
_REJECTION_LINE = _REJECTION_HEAD + "{reason}" + _REJECTION_TAIL
# 回炉条判据：**重跑面两档**（真源＝execution `subtask_results` 状态闭世界〔流水 59〕：
# `ok／refused／bad_args／retryable`——「失败子集回炉」语义真源＝execution 三档失败分类
# 〔`specs/execution.md:49／:62`〕＋澄清相位回炉行为）：`bad_args`（参数错——回炉「修参」）
# ／`retryable`（超时／上游抖动／限流——**只重跑此档**）两档重跑回炉；`ok` 成品不重跑、
# `refused`（前置闸拒／闸拒）**终局不回炉**。两值按 R1 在本常量点以字面承载（不引 execution
# 包），单点判据＝`_REWORK_STATUSES`。
_SUBTASK_STATUS_BAD_ARGS = "bad_args"
_SUBTASK_STATUS_RETRYABLE = "retryable"
_REWORK_STATUSES: frozenset[str] = frozenset(
    {_SUBTASK_STATUS_BAD_ARGS, _SUBTASK_STATUS_RETRYABLE}
)
# 问题组 JSON 段头（逐字迁移——graph.py L2706-2708）。
_QUESTION_GROUP_HEAD = "问题组："

# ── 分解发射样例（逐字迁移——orientation.py L199-228；运行时现造、**不进合同常量**）──
# 头行**2026-10-16 补（L0/L2 三病灶修复批②）**：窗词锚定说明句补模糊时间词一档——
# 真机实测首秀形于窗段无据可依（L2/r1 必拒）；合法形真源 `specs/clarification.md` 行为 8③。
# **2026-10-16 补（流水 66）**：头行再补「无台账行＝槽位写「无台账命中」」一档——报告内容题
# （如完井液密度）本就无台账行，旧教据只教「逐字转抄台账块」，模型无合法形可写、三拒烧光轮次
# （真机 run-18e5d273）；合法形真源 `specs/clarification.md` 行为 8①。
_DECOMPOSE_EXAMPLE_HEAD = (
    "填写样例（分解形——五键齐全，ledger_notes 逐字转抄台账全量块，窗为示意按窗词锚定表现算；"
    "模糊时间词（最近/近期）＝窗写 null~null，由引擎缺参反问兜底三选一——不要自己锚窗；"
    "子问题无台账行（报告内容题）＝槽位写「无台账命中」，不硬凑名"
    "——三段照抄上形：无台账命中｜未绑定｜窗未定（不加解释、不改写））："
)
# ── 无台账命中形全样例行（**2026-10-17 补·L3 阻塞修复批·分解样例补行**，逐字）────────────
# 病根：样例区只给了**锚定指标形**全样例行，无命中形仅头行一句说明、无整行可照抄——模型知形而凑不齐
# 三个闭世界段。真机 `run-b5b6b056`（`docs/runtime-refactor/ladder/L3/06`）三轮全拒：r1
# `无台账命中——完井液密度属于完井工程报告事实`（段尾加解释→段数非三）／r2
# `无台账命中｜无绑定｜检索式无窗`（绑定态／窗段自造形越界）／r3
# `无台账命中｜未绑定｜检索式无窗`（窗段自造形越界）。本行逐字＝闸收形的三段位（绑定态 ∈ 澄清对账
# 闭世界 `BINDING_STATES`／窗 ∈ `WINDOW_LITERALS`；合法形真源 `specs/clarification.md` 行为 8①③）。
_DECOMPOSE_EXAMPLE_NO_HIT = (
    '{"action": "decompose", "question_group": {"subtasks": [{"id": "s1", '
    '"question": "〈报告内容类问题〉", "ledger_notes": "无台账命中｜未绑定｜窗未定", '
    '"chain": "knowledge", "tool": "doc_retrieve"}]}}'
)
_UNBOUND_BINDING = "未绑定"
# 绑定态字面须 ∈ 澄清对账闭世界 `BINDING_STATES`（`已绑定`／`未绑定`）——样例教的即闸收的
# （2026-10-16 微批对齐：旧字面 `在册可出数` 是台账 V1 绑定态形，过不了三段槽位对账的绑定态段）。
_BOUND_BINDING = "已绑定"


def anchor_line(question: str, understanding: str = "") -> str:
    """题意锚行两形（行为 6）——插澄清轮／工具匹配轮指令最前（首行位）。

    理解真值 → 单行「用户原题：{question}｜题意：{understanding}」（前缀固定「用户原题：」、
    全角冒号、全角「｜」直连）；理解假值 → 单段「用户原题：{question}」（不输出空「题意：」段）。
    """
    if understanding:
        return f"用户原题：{question}｜题意：{understanding}"
    return f"用户原题：{question}"


def _ledger_rows(dump: Mapping[str, Any]) -> str:
    """台账行渲染（逐字迁移 V1 `render_ledger_rows`——值串直取、零改写、零筛选）。"""
    lines: list[str] = []
    for metric in _rows(dump.get("metrics")):
        lines.append(
            f"指标｜{metric.get('value', '')}（绑定态：{metric.get('binding_state', '')}）"
        )
    for term in _rows(dump.get("terms")):
        lines.append(f"术语｜{term.get('value', '')}（时效：{term.get('freshness', '')}）")
    for obj in _rows(dump.get("objects")):
        lines.append(f"对象｜{obj.get('value', '')}")
    for relation in _rows(dump.get("relations")):
        lines.append(f"关系｜{relation.get('value', '')}")
    for family in _rows(dump.get("families")):
        lines.append(f"族标注｜{family.get('value', '')}")
    return "\n".join(lines)


def _alias_rows(dump: Mapping[str, Any]) -> str:
    """别名表行渲染（逐字迁移 V1 `render_aliases`——「别名→规范名」行族、以「；」分隔）。"""
    aliases = dump.get("aliases")
    if not isinstance(aliases, Mapping):
        return ""
    return "；".join(f"{alias}→{canonical}" for alias, canonical in aliases.items())


def _card_rows(dump: Mapping[str, Any]) -> str:
    """结构卡行渲染（逐字迁移 V1 `render_cards`——逐卡一行「- {卡名}」）。"""
    cards = dump.get("cards")
    if not isinstance(cards, list):
        return ""
    return "\n".join(f"- {card}" for card in cards if isinstance(card, str))


def render_ledger_resident_block(state: RunState) -> str:
    """台账常驻块渲染（行为 7⑥／行为 8）——BEGIN＋字典说明行＋台账/别名/结构卡三块＋END。

    台词条目**逐字转抄**自 `state.ledger_dump` 投影（不改写、不摘要——`ledger_notes` **槽位段**
    逐字可求得的前提：对账口径＝段一逐字 ∈ 台账名录 ∪「无台账命中」（无台账行的报告内容题 —
    —自造名不算，`specs/clarification.md` 行为 8），非整块逐字子串）；**恰一份**（装配不另拼
    名录段——V2-59 三删纪律的装配面）。投影缺位／空投影（`None`
    或 `{}`）→ 返回**空串**（该段缺位、调用方跳过——行为 7「投影非空时」）。
    """
    dump = _projection(state)
    if not dump:
        return ""
    blocks = (
        f"【{_LEDGER_BLOCK_LABEL}】\n{_ledger_rows(dump)}",
        f"【{_ALIAS_BLOCK_LABEL}】\n{_alias_rows(dump)}",
        f"【{_CARD_BLOCK_LABEL}】\n{_card_rows(dump)}",
    )
    return (
        RESIDENT_BLOCK_BEGIN
        + "\n"
        + LEDGER_DICT_NOTE
        + "\n"
        + "\n\n".join(blocks)
        + "\n"
        + RESIDENT_BLOCK_END
    )


def _as_day(today: Any) -> date | None:
    """注入时间量归一（`date`／`datetime`／ISO 串／零参可调用→`date`；缺位→`None`）。

    时间量只经入参注入（本块零时钟接触，B14）：`None`＝缺位（不编造日期——上层落空串段）；
    形态越界（非日期形串）→ 抛参数错误、不吞错（先例 `specs/context.md` 错误契约）。
    """
    day = today() if callable(today) else today
    if day is None:
        return None
    if isinstance(day, datetime):
        return day.date()
    if isinstance(day, date):
        return day
    return date.fromisoformat(str(day))


def render_decompose_example(metrics: Any, *, today: Any) -> str:
    """分解发射样例渲染（行为 10）——**运行时现造、不进合同常量**（A-P4b-32 命名闸所迫）。

    三分支：取**首条未绑定指标** → knowledge 链（`tool=doc_retrieve`）形；无未绑定取**首条可出数**
    → data 链（`tool=data_query`）形；台账空投影（或时间量缺位）→ **空串**（调用方跳过）。
    样例窗＝「today−近 30 天 ~ today」示意（默认窗口径真源 `walk/08` §七 Q-B）；payload 两层嵌套、
    子问题条目五键齐全（id／question／ledger_notes／chain／tool）——**合法 JSON**（`json.dumps`
    现造，V1 拼接无转义病灶 D-L2a-13 不复现）。

    样例区**两条行**（2026-10-17 补·分解样例补行）：首行＝上述现造锚定指标形；次行＝
    `_DECOMPOSE_EXAMPLE_NO_HIT` 无台账命中形全样例行（逐字、静态——报告内容题整行可照抄，防模型
    只知形而凑不齐三段位；真机 `run-b5b6b056` 三轮全拒）。两行同属该段：投影空／时间量缺位 →
    整段空串（两行同缺，调用方跳过——行为 7「投影非空时」）。
    """
    rows = _rows(metrics)
    if not rows:
        return ""
    day = _as_day(today)
    if day is None:
        return ""
    ordered = sorted(rows, key=lambda metric: 0 if metric.get("binding_state") == "unbound" else 1)
    pick = ordered[0]
    slot = str(pick.get("slot", ""))
    unbound = pick.get("binding_state") == "unbound"
    window = f"{(day - timedelta(days=30)).isoformat()}~{day.isoformat()}"
    payload = json.dumps(
        {
            "action": "decompose",
            "question_group": {
                "subtasks": [
                    {
                        "id": "s1",
                        "question": f"{slot}是多少？",
                        "ledger_notes": f"{slot}｜{_UNBOUND_BINDING if unbound else _BOUND_BINDING}"
                        f"｜{window}",
                        "chain": "knowledge" if unbound else "data",
                        "tool": "doc_retrieve" if unbound else "data_query",
                    }
                ]
            },
        },
        ensure_ascii=False,
    )
    return _DECOMPOSE_EXAMPLE_HEAD + payload + "\n" + _DECOMPOSE_EXAMPLE_NO_HIT


def _question_group_json(state: RunState) -> str:
    """问题组 JSON 渲染（投影**原形直转**——顶层 `subtasks` 单键形，真源 R-E2-04／V1 L2706-2708）。

    投影缺位／空 → 空串（该段缺位、调用方跳过）。
    """
    group = state.question_group
    if not isinstance(group, Mapping) or not group:
        return ""
    return json.dumps(group, ensure_ascii=False)


def _with_resident_block(text: str, state: RunState) -> str:
    """常驻块尾附（投影非空时——行为 7⑥「常驻块包裹对恰一对」）。"""
    block = render_ledger_resident_block(state)
    return text + "\n\n" + block if block else text


def _clarify_contract(max_subtasks: Any) -> str:
    """澄清轮相位合同正文：族②常量替换声明槽 `{max_subtasks}`。

    槽值来源（-04a 常量注）：`{max_subtasks}`＝调用方注入（子问题上限，数值单点不在本块）。
    槽缺值＝装配不可完成 → 参数错误（fail-closed，不吞错、不留裸槽）。

    **2026-10-17 补（真机消重批·缺陷二）**：旧 `{discover_used}` 槽随「已用 N 次」冻值一并退场
    ——静态合同块内的槽值只在**相位首入**替换一次（首入时 `discover_used` 恒 0），一路带到 answer
    调用仍写「已用 0 次」，模型看不见自己烧了几支（真机 run-e1b6ff1e：8 次 decision、4 次
    discover 全 no_hit，烧到 `budget_converged`）。真实已用数只由**每轮动态条**①「探查预算：
    全 run ≤{上限} 次，已用 {已用} 次。」逐轮披露（行为 16①——机计数权威披露面；静态合同只留
    上限、不载计数，KV 字节稳定亦不破）。上限数值真源＝`state.MAX_DISCOVERS_PER_RUN`
    （R-K-75；增量条引该常量，本块不复述数值）。
    """
    if max_subtasks is None:
        raise ValueError(
            "澄清轮相位合同槽 {max_subtasks} 缺值（调用方必供——族②常量声明槽，"
            "specs/prompts.md 接口定义节）"
        )
    return CLARIFY_EMISSION_CONTRACT.replace("{max_subtasks}", str(max_subtasks))


def clarify_system_contract(max_subtasks: Any) -> str:
    """澄清环节**规章段**（system 承载位——2026-10-17 H 批）：相位头行＋相位合同正文＋
    finalize 交付面边界句。

    文本零新写（头行／族②合同／边界句均为既有常量）；`{max_subtasks}` 槽由调用方注入
    （单点仍在 `_clarify_contract`）。**不入链**——经 `bookkeeping.call_model(system=…)` 随本次
    请求走（回炉轮亦每轮在场：规章随请求、链只追加首入包，`pin-24` 的链面一次性不变）。
    """
    return (
        CLARIFY_PHASE_HEAD
        + "\n"
        + _clarify_contract(max_subtasks)
        + "\n\n"
        + CLARIFY_FINALIZE_BOUNDARY
    )


def toolmatch_system_contract() -> str:
    """工具匹配环节**规章段**（system 承载位——2026-10-17 H 批）：相位头行＋相位合同正文（内含
    合同内嵌定案样例）。

    文本零新写；不入链——经 `bookkeeping.call_model(system=…)` 随本次请求走。
    """
    return TOOLMATCH_PHASE_HEAD + "\n" + TOOLMATCH_EMISSION_CONTRACT


def assemble_decision_package(
    state: RunState,
    *,
    phase: str,
    guide_text: str = "",
    today: Any = None,
    max_subtasks: Any = None,
    shared_context: bool = True,
) -> str:
    """决策轮**首入包动态段**装配（行为 7 的 user 半面——2026-10-17 H 批）——相位一次性：
    回炉轮不重发（pin-24；追加编排归调用方）。

    构成逐件（澄清轮／工具匹配轮各按其件）：①题意锚行（首行位，行为 6）＋③产出样例（澄清轮＝
    分解发射样例；匹配轮＝合同内嵌样例，随合同常量走）＋④§A 指南段（**文本经入参注入**，装载面
    不归本块）＋⑤（匹配轮）问题组 JSON＋⑥（投影非空时）台账常驻块（包裹对恰一对）。
    **规章件**（相位头行＋相位合同＋finalize 边界句）**不在本函数输出内**——走
    `clarify_system_contract`／`toolmatch_system_contract` 的调用级 system 注入参、不入链
    （真源 `specs/prompts.md` 2026-10-17 H 批注）。

    `shared_context`＝**run 级共享上下文**（④§A 指南段＋⑥台账常驻块）本次是否注入（缺省 `True`
    ＝装配函数本体的行为 7 构成）：`True` 按上列注；`False`＝两段**整段缺席**（其余件照常——锚行、
    分解样例、问题组 JSON 皆不属共享上下文）。**判定归编排**（同一 run 只注一次，挂第一次决策
    装配；见模块头「run 级共享上下文」注）——本函数只按标志拼／不拼文本。
    **共享上下文留在 user 链**（不随规章改走 system）：run 级一次性的语义前提＝「链为追加形、
    模型从链首可见前文」（2026-10-17 消重批）——移出链即断该前提（后续决策调用看不见）。

    纯函数：只读 `state` 投影与注入文本，零 IO／零模型／零时钟／零随机；输出恒为 `str`。
    """
    if phase == PHASE_CLARIFY:
        return _clarify_package(
            state,
            guide_text=guide_text,
            today=today,
            max_subtasks=max_subtasks,
            shared_context=shared_context,
        )
    if phase == PHASE_TOOLMATCH:
        return _toolmatch_package(
            state, guide_text=guide_text, shared_context=shared_context
        )
    raise ValueError(f"决策轮相位越界（闭世界 DECISION_PHASES＝{_PHASES_TEXT}）：{phase!r}")


def _clarify_package(
    state: RunState,
    *,
    guide_text: str,
    today: Any,
    max_subtasks: Any,
    shared_context: bool = True,
) -> str:
    """澄清轮首入包**动态段**（逐字迁移 graph.py L2354-2384 的动态件）。

    `shared_context=False` → §A 指南段与台账常驻块整段缺席（run 级一次性的下传面）；锚行与分解
    样例照常（样例属相位装配件、不属共享上下文）。**规章件不在本段**（头行／合同／边界句走
    `clarify_system_contract`——H 批）；`max_subtasks` 仍作入参（转交规章段单点取件，本段不用它，
    保留签名以零改调用面）。
    """
    parts = [anchor_line(state.question, state.understanding)]
    example = render_decompose_example(_projection(state).get("metrics"), today=today)
    if example:
        parts.append(example)
    text = "\n\n".join(parts)
    if shared_context:
        text += "\n\n" + GUIDE_REFERENCE_HEAD + "\n" + guide_text
    return _with_resident_block(text, state) if shared_context else text


def _toolmatch_package(
    state: RunState, *, guide_text: str, shared_context: bool = True
) -> str:
    """工具匹配轮首入包**动态段**（逐字迁移 graph.py L2698-2729 的动态件）。

    `shared_context=False` → §A 指南段与台账常驻块整段缺席（run 级一次性的下传面——匹配轮是同一
    run 的第二次决策装配，共享上下文已挂澄清轮首入包）；锚行与问题组 JSON 照常。**规章件不在本段**
    （头行／合同走 `toolmatch_system_contract`——H 批）。
    """
    text = anchor_line(state.question, state.understanding)
    if shared_context:
        text += "\n\n" + GUIDE_REFERENCE_HEAD + "\n" + guide_text
    group_json = _question_group_json(state)
    if group_json:
        text += "\n\n" + _QUESTION_GROUP_HEAD + "\n" + group_json
    return _with_resident_block(text, state) if shared_context else text


def _rejection_feedback_line(reason: str) -> str:
    """拒因回喂行（行为 16④）：裸拒因套壳；**已自带整套壳体者原样透传**（壳恰一遍）。

    已带壳＝串首即 `_REJECTION_HEAD`（形态处理面「逐字子串校」——机器面文本的闭世界前缀校，
    先例 `_REROUTE_TRIGGERS` 同款；非语义词表）：槽位对账拒因载荷自带头／尾壳体
    （`specs/clarification.md` 错误契约，流水 64），套壳即叠字（流水 66 修——真机 run-18e5d273）。
    """
    if reason[: len(_REJECTION_HEAD)] == _REJECTION_HEAD:
        return reason
    return _REJECTION_LINE.format(reason=reason)


def _rework_line(row: Mapping[str, Any]) -> str:
    """回炉行逐条渲染（逐字迁移 V1 `_rework_line`——拒因词面→路由动词）。"""
    reason = str(row.get("reason") or "")
    shown = reason + _REROUTE_SUFFIX if any(t in reason for t in _REROUTE_TRIGGERS) else reason
    return _REWORK_LINE.format(id=row.get("id", ""), question=row.get("question", ""), reason=shown)


def _rework_block(state: RunState) -> str:
    """回炉条（仅当存在**重跑档**失败子问题——`bad_args`／`retryable` 两档；成功结果保留、
    禁重复分解执行；`refused` 终局不回炉）。"""
    rework_rows = [
        row
        for row in state.subtask_results
        if isinstance(row, Mapping) and row.get("status") in _REWORK_STATUSES
    ]
    if not rework_rows:
        return ""
    return _REWORK_HEAD + "\n" + "\n".join(_rework_line(row) for row in rework_rows)


def assemble_decision_increment(
    state: RunState, *, phase: str, done_text: str = ""
) -> str:
    """决策轮**每轮增量条**装配（行为 16）——单条 user 内各段以「\\n」连接；零段 → 空串。

    澄清轮五件：①探查预算条（**仅非首入轮**——判据＝相位标记已在 `state.contracts_appended`，
    同 V1 `contracts_flag`；首入包内槽值会陈旧，机计数权威披露双保险同向）②回炉条（仅当存在
    重跑档失败子问题——`bad_args`／`retryable`）③用户补充条（`user_hint` 非空）④拒因回喂条
    （`decision_error` 非空）⑤已做段（调用方传入文本**原样在场、零改写**——渲染归 `context`）。
    工具匹配轮两件：④拒因回喂条＋⑤已做段。

    **何时追加整条＝调用方义务**（编排面）：本函数只供条文本与条内自身条件；输出恒为 `str`。
    """
    if phase == PHASE_CLARIFY:
        parts: list[str] = []
        if PHASE_CLARIFY in state.contracts_appended:
            cap = MAX_DISCOVERS_PER_RUN
            parts.append(_BUDGET_LINE.format(cap=cap, used=int(state.discover_used)))
        rework = _rework_block(state)
        if rework:
            parts.append(rework)
        if state.user_hint:
            parts.append(_HINT_LINE.format(hint=state.user_hint))
        if state.decision_error:
            parts.append(_rejection_feedback_line(state.decision_error))
        if done_text:
            parts.append(done_text)
        return "\n".join(parts)
    if phase == PHASE_TOOLMATCH:
        parts = []
        if state.decision_error:
            parts.append(_rejection_feedback_line(state.decision_error))
        if done_text:
            parts.append(done_text)
        return "\n".join(parts)
    raise ValueError(f"决策轮相位越界（闭世界 DECISION_PHASES＝{_PHASES_TEXT}）：{phase!r}")
