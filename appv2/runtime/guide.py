"""runtime.guide —— ReAct 决策处理指南缝（Skill 处理指南的消费接口——V2-31 拍板⑦）。

拍板⑦：Skill 处理指南＝ontology 资产（GUIDE-PETRO-001，ontology/petro/
skill-guides/）。本模块持有：

- `GuideProvider` 协议（结构性——ontology 资产件实现同形注入 LoopDeps）；
- `DECISION_CONTRACT`（决策发射合同文本——与 graph.parse_decision schema 校验
  代码同源单点，运行时所有决策面的发射合同真源）；
- `CLARIFY_CONTRACT`／`TOOLMATCH_CONTRACT`（V2-34 四相位：相位①澄清-分解与
  相位②工具匹配的发射合同——runtime 单点，ontology §7 分解指南为业务语义面）。

**DefaultGuideProvider 已退役（V2-34 任务 10，不设双真源）**：生产唯一指南源＝
ontology 资产装载件（appv2.api.ontology_guide.OntologyGuideProvider——§A 装载
切面＋DECISION_CONTRACT 拼接，create_app 组合根缺省接线）；内置五段占位文案
（路由判定/澄清分级/循环纪律）由 §A 对应条款接管。
"""

from __future__ import annotations

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

# ---------- 四相位合同（V2-34——runtime 单点，schema 校验真源同源） ----------

CLARIFY_CONTRACT = (
    "【相位①·业务澄清】只输出一个 JSON 对象（可围栏）。四动作：\n"
    # ↓↓ V2-60 引号规矩（票面附 A 逐字稿——交接-澄清相位发射格式治理；
    #    格式合规契约：值内裸英文双引号把字符串提前截断，族D 三题字节级实证）
    "JSON 字符串值内需要引号时（引题干原文/术语等）：一律用中文引号「」（或单引号'），"
    "禁止写不转义的英文双引号 \"——它会把字符串提前截断，整条发射作废。\n"
    "错例：\"question\": \"1.3 节关于\"杆柱\"的算式\"   ← 值内裸引号，非法\n"
    "对例：\"question\": \"1.3 节关于「杆柱」的算式\"   ← 值内中文引号，合法\n"
    '- 分解：{"action": "decompose", "question_group": {"subtasks": '
    '[{"id": "s1", "question": "子问题原文", "ledger_notes": "〈精确指标 slot 名〉'
    '〈绑定态〉〈锚定窗〉", "chain": "data"|"knowledge", "tool": '
    '"data_query"|"doc_retrieve"}]}}——子问题 ≤{max_subtasks} 个；每个子问题可独立'
    "映射一条工具链（粒度＝一个指标×一个窗×一个对象集）；单一诉求不分解（单子"
    "问题组）；ledger_notes 必带——从下方台账全量块逐字转抄，不改写不杜撰。\n"
    '- 钻取：{"action": "discover", "discovers": [{"tool": "semantic_query"|'
    '"table_schema"|"faq_lookup", "args": {...}}]}——1~2 支。开局已给全台账，'
    "禁猜词敲门：只作口径/绑定细节钻取，不答「能不能出数」。\n"
    # ↓↓ V2-53 附 A 工具目录逐字稿（票面施工基准——char 相等，本段不得增删字；
    #    {discover_used} 为运行时替换槽，clarify 节点统一 replace）
    "可用探查（discover，全 run ≤10 次，已用 {discover_used} 次）：\n"
    "- semantic_query：本体口径/绑定/届满细节钻取（开局台账已全量，仅细节用）\n"
    "- table_schema：表结构钻取（agg/sem/kb 分区）\n"
    "- faq_lookup：FAQ 现成问答库——问句有现成标准答案时加速/互证；\n"
    "  命中条目作观察材料进上下文——有探查观察在场方可 finalize，不够继续检索\n"
    # ↓↓ V2-53 附 A 定稿直答行逐字稿（票面施工基准——char 相等，本段不得增删字；
    #    交付面边界句＝P-051b 真批修正：真模型把台账常驻注入当「材料足够」
    #    零观察定稿（P051BW 术语躺井/数-降1/数-降2 零交付形）——注入不进交付
    #    面，词条卡语义走 semantic_query 取条目卡（附 E 承载面）
    '- 定稿直答：{"action": "finalize"}——仅当本 run 已有探查观察（discover 命中条目）时可用：'
    "系统按观察材料起草带引用的答案（秒答形，不走检索执行）。零探查观察发射 finalize＝非法发射，"
    "程序拒回并要求改发。台账常驻注入是字典不是数据——指标/术语在台账＝知道名字与定义，"
    "不等于数值在手，注入不进交付面；要数值先 discover 钻取或 decompose 分解走检索执行。\n"
    '- 反问：{"action": "ask", "ask": {"prompt": "...", "options": ["…"]}}'
    "——2~4 个选项；仅限两种白场：无场景词＋阈值判断形（口径支待用户选），"
    "或目标/对象/口径真歧义（用户补一句话即可解——拍板⑥澄清分级②）。\n"
    "发射判据：台账命中＋窗已定＝分解完毕，禁再 discover；对称面——窗可锚定＝"
    "禁 ask（时间词按窗词锚定表可解析即锚定发射；无时间词→默认近 30 天；模糊"
    "时间词→窗双 null 发射由引擎缺参反问；窗内无数据由引擎新鲜度闸拦停/改绑并"
    "注记——不预判、不对窗/粒度反问）。\n"
    # ↓↓ P-039 附 2 逐字追加段（票面施工基准——现有措辞零删改，本段不得增删字）
    "knowledge 链规则：问文档所载内容（非台账指标的数值取数）＝单子问题组直发"
    "（chain=knowledge, tool=doc_retrieve）——不问范围、不问载体（全库检索"
    "是合同口径，路由建议已代选库）、不问口径支；口径支歧义不归本相位——"
    "由前置条件机按 caliber_key 三态处理（双口径并列或阈值反问）；检索式"
    "问题没有「窗」概念——缺窗不是歧义、不构成反问白场；无时间词的数据链"
    "问题＝默认近 30 天直发，禁反问时间窗；模糊时间词（最近/近期/前段时间类）"
    "＝窗双 null 发射，由引擎缺参反问兜底（三选一合法形，拍板⑥）——两分支不得混淆。"
    # ↓↓ V2-46 R1c 逐字追加段（P-045 派工单施工基准——现有措辞零删改，char 相等）
    "回捞白场：当「检索窗注记」载有未进窗来源且本问题组相关报告/章节在列——\n"
    "可经回炉对该子问题重发带 anchors（报告名/章节锚）的 knowledge 链检索，\n"
    "每子问题限一次（消耗一轮，不挂起不占 ask）。"
)

TOOLMATCH_CONTRACT = (
    "【相位②·工具匹配】只输出一个 JSON 对象（可围栏）：\n"
    # ↓↓ V2-60 引号规矩（附 A 三行逐字复制——retrieval_need.question 等字段同坑）
    "JSON 字符串值内需要引号时（引题干原文/术语等）：一律用中文引号「」（或单引号'），"
    "禁止写不转义的英文双引号 \"——它会把字符串提前截断，整条发射作废。\n"
    "错例：\"question\": \"1.3 节关于\"杆柱\"的算式\"   ← 值内裸引号，非法\n"
    "对例：\"question\": \"1.3 节关于「杆柱」的算式\"   ← 值内中文引号，合法\n"
    '{"matches": [{"id": "问题组子问题 id", "chain": "data"|"knowledge", '
    '"tool": "data_query"|"doc_retrieve", "plan": {…data 链必带…}, '
    '"retrieval_need": {…knowledge 链必带…}, "caliber_key": "口径支 key（可选）"}]}\n'
    "matches 与问题组一一对应（每子问题恰一条，id 闭合世界）；caliber_key 仅在"
    "问句场景词已落定口径支时携带。\n"
    "plan 形（data 链必带，键名逐字）：{\"metric_slot\": \"台账精确指标名（必填非空，"
    "禁英文列名/复合注记）\", \"ranking\": true|false（必填布尔——排名题 true 并给 "
    "\"direction\": \"asc|desc\"，明细题 false）, \"window_start\": \"ISO 日期或 null\", "
    "\"window_end\": \"ISO 日期或 null（不含端）\", \"limit\": 50（仅问句显式条数时写）, "
    "\"external_tables\": [...]（仅外表引用时写）}——缺 ranking 等必填键＝参数校验拒。\n"
    # ↓↓ P-039 附 1 逐字追加段（票面施工基准——现有措辞零删改，本段不得增删字）
    "retrieval_need 形（knowledge 链必带，键名逐字）：{\"question\": \"检索问句原文"
    "（必填非空——逐字转抄该子问题的 question）\", \"anchors\": [\"锚点词\", …]"
    "（可选——井号/报告名/章节等精确定位词）, \"family_hints\": [\"completion\"|"
    "\"monthly\"|\"dynamic\"|\"blank\"]（可选——族机器名，不要写中文名）}"
    "——缺 question＝参数校验拒；只许这三个键，禁造键名。"
)

# ---------- 汇总相位合同（相位④后半——LLM 整合全组子结果） ----------

# V2-51 追加段（数-排2 plan 支配——现有措辞零删改，追加在尾部）：排名型子问题
# 的消费支配约束；「排名观察支」「合计行」皆机读载荷词面，零业务名词。
SUMMARY_CONTRACT = (
    "【相位④·汇总】整合问题组全部子结果：逐子问题给出一行结论（子问题要点→答案），"
    "成功子问题逐条断言带 [n] 引标指向观察材料；被拒/失败子问题如实说明原因，"
    "不冒充不出数。"
    "排名型子问题（计划 ranking=true）的结论必须从本子问题的排名观察支取值"
    "（引擎按计划合计口径给出的排名行），不得从其他子问题的明细行切片换算或"
    "跨子问题取值。"
)


class GuideProvider(Protocol):
    """处理指南接口缝（ontology 资产件的注入形——结构性协议）。"""

    def guide(self) -> str: ...
