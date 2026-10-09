"""runtime.guide —— ReAct 决策处理指南（Skill 处理指南的消费接口——V2-31 拍板⑦）。

拍板⑦：Skill 处理指南＝ontology 资产（V2-32 并行起草，本票消费其接口）。本模块
即被消费的接口缝：`GuideProvider` 协议（结构性——V2-32 的 ontology 资产件实现
同形即可注入 LoopDeps）＋`DefaultGuideProvider` 内置缺省实现（澄清分级＋决策
发射合同＋工具使用指引，指南正文＝本模块常量单点）。

V2-32 落地后：其 ontology 资产件实现 GuideProvider 协议注入 LoopDeps.guide——
graph 决策节点只经 `provider.guide()` 取文，不感知指南来源（接口不变，正文可
整替——骨架版内置文案随 V2-32 退役，不设双真源）。
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Protocol

# ---------- 决策发射合同（模型面的结构化发射契约——graph.parse_decision 同源） ----------

DECISION_CONTRACT = (
    "每轮只输出一个 JSON 对象（可围栏包裹，不要输出 JSON 之外的解释文字）。键：\n"
    '{"thought": "一句话理由（可省）", "action": "discover|execute|ask|finalize", ...}\n'
    '- action=discover（探查）：{"discovers": [{"tool": "semantic_query"|"table_schema", '
    '"args": {...}}]}——1~2 支。semantic_query 的 args 二选一：{"question": "..."} 或 '
    '{"element_name": "精确名"}；table_schema 的 args：{"area": "agg"|"sem"|"kb"} 可选＋'
    '{"table": "表名"} 可选（查不存在的表会如实告知不开放）。\n'
    "- action=execute（主执行）：{\"task_type\": \"data\"|\"knowledge\"|\"mixed\"}，"
    'data 带计划 {"plan": {"metric_slot": "...", "ranking": false, "window_start": '
    '"ISO 日期或 null", "window_end": "ISO 日期或 null", "limit": 50, "direction": '
    '"asc|desc", "external_tables": [...]}}；knowledge 带检索需要 {"retrieval_need": '
    '{"question": "...", "anchors": [...], "family_hints": [...]}}——family_hints '
    "只能省略或取 completion／monthly／dynamic／blank（族机器名，不要写中文名）；"
    "mixed＝plan 与 retrieval_need 都给（数证结合，一轮双执行）。\n"
    '- action=ask（澄清挂起）：{"ask": {"prompt": "问用户什么", "options": '
    '["选项1", "选项2"]}}——2~4 个选项。\n'
    "- action=finalize（定稿）：材料已足够回答——系统将按观察材料起草带引用的答案。\n"
    '可带 {"note": "给用户的注记"} 随任何 action 出场。'
)

# ---------- 澄清分级（拍板⑥——时间窗不问，目标/对象/口径才 ask） ----------

CLARIFY_GRADING = (
    "澄清分级（硬规则）：\n"
    "1) 时间窗歧义不许 ask——按默认窗自动取数：近 30 天（window_start={start}、"
    "window_end={end}，end 为不含端），plan 置 \"is_default\": true，并带 "
    "\"note\": \"未指明时间窗——已按近 30 天默认（{start} 起）\"；\n"
    "2) 问句目标/对象/口径歧义（用户补一句话即可解）→ action=ask；\n"
    "3) 计划涉及外部表（如井位台账 erp_well_register）→ 照常发 plan（data_query "
    "会走审批挂起，不要自行改道检索）。\n"
)

# ---------- ReAct 循环纪律（轮预算与观察回流） ----------

REACT_DISCIPLINE = (
    "循环纪律：最多 {max_rounds} 轮，每轮一个决策；轮内发现工具最多 {max_discovers} 支、"
    "主执行最多 {max_executes} 支。工具结果以带 [n] 序号的观察材料回流——读序号引用，"
    "不要凭空复述之前轮次的数字。材料足够就 finalize，不要为凑轮次重复执行。"
    "上下文携带完整对话历史：你此前的决策 JSON 与执行台账（「参数 → 结果：N 行／"
    "闸拒（拒因）」）都在历史消息里——已执行过的同参计划不要重复发射，带已有结果"
    "finalize 直答或改参后再发射；被闸拒过的路径读拒因，不要原样重试。"
)


class GuideProvider(Protocol):
    """处理指南接口缝（V2-32 ontology 资产件的注入形——结构性协议）。"""

    def guide(self) -> str: ...


class DefaultGuideProvider:
    """内置缺省指南（骨架版——V2-32 落地后整替注入，接口不变）。

    guide() 输出五段：角色与红线（ContextBuilder 系统提示的决策面补充）＋
    决策发射合同＋工具使用次序建议＋澄清分级＋循环纪律。今天锚点进指南
    （默认窗计算的确定性依据——时钟经 infra.clock 唯一出口）。
    """

    def __init__(self, *, today: date, max_rounds: int = 3, max_discovers: int = 2,
                 max_executes: int = 2) -> None:
        self._today = today
        self._max_rounds = max_rounds
        self._max_discovers = max_discovers
        self._max_executes = max_executes

    def guide(self) -> str:
        start = (self._today - timedelta(days=30)).isoformat()
        end = self._today.isoformat()
        contract = DECISION_CONTRACT
        grading = CLARIFY_GRADING.replace("{start}", start).replace("{end}", end)
        discipline = REACT_DISCIPLINE.replace("{max_rounds}", str(self._max_rounds))
        discipline = discipline.replace("{max_discovers}", str(self._max_discovers))
        discipline = discipline.replace("{max_executes}", str(self._max_executes))
        return (
            f"今天：{end}。\n{contract}\n路由判定（先分型再动手）：报告/文档事实"
            "（完井工程参数、月报统计、生产动态、术语解释）→execute(knowledge) 走"
            " doc_retrieve；指标数值→discover(semantic_query) 核口径存在与绑定态再"
            " execute(data)。台账查询回流 no_hit（未命中）＝该词不在指标台账——不要"
            "换词重复 discover，改走 execute(knowledge) 检索报告原文。"
            f"{grading}{discipline}"
        )
