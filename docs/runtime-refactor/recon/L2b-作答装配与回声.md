# L2b·现状调研报告

- 锚定：commit e4b75f1（行号以此为准）
- 覆盖：appv2/runtime/orientation.py L282-文末
- def/class 清单：逐一全列（含行号区间），不得省略

（行号核验：e4b75f1 版本文件 347 行，L282-347 与工作区逐行 diff 一致——已实测。）

## def/class 清单（全列）

appv2/runtime/orientation.py L282-文末（文件 L347 收尾）：
- 模块节注释：L280（「V2-62 轮次任务自足性（答案轮三件套/题意锚行/观察字段）」）
- 模块常量：`_ANSWER_REQUIREMENTS` L282-290（本段唯一模块级常量）
- `answer_turn_preamble` L293-300
- `assemble_answer_instruction` L303-317
- `anchor_line` L320-324
- `echo_signature_hit` L327-330
- `paste_ratio` L333-347
- class：无（本段无类定义）

接缝（向上多读 L205-280，不在覆盖范围、只为理解接缝）：上文收尾为 `render_decompose_example`（L205-232 区段）与 `assemble_understand_turn`（L235-277）——本段由 L280 节注释新开，与上文无互相调用。

---

### `_ANSWER_REQUIREMENTS`（orientation.py L282-290）｜答案要求逐字稿（模块级 str 常量，7 条以「；」分隔）
- 消费：无入参（模块导入时求值一次）。生产消费唯一＝`answer_turn_preamble`（L299）；测试直取：tests/domains/test_v2_v264_slice_origin.py:89、:104。
- 装配：不独立成段——经 `answer_turn_preamble` 以「【答案要求】」为前缀嵌进答案轮指令（L299）；常量内无换行符，故该段恒为单行。
- 分支表（穷尽）：
  1. 无分支（常量）→ 恒返回同一 str → `answer_turn_preamble`
- 副作用：无。
- 返回：str。
- 规则条目（一句话一条）：
  - R-L2b-01 单条 str 由 7 个相邻字符串字面隐式拼接（L283-289 断行仅为排版，不产生换行符）。
  - R-L2b-02 条款结构总览（7 条，分隔符「；」，顺序固定）：①逐条事实断言带 [n] 引标；②材料未覆盖部分不得断言、须如实说明未覆盖；③材料含多个来源（不同报告／油田／井）时逐个来源分别作答（不冲突也要分别列出、不以反问代替作答——V2-64 拓宽形）；④作答后仍有未覆盖来源或指代不明处，如实点名未覆盖来源（含检索窗注记的未进窗来源）并请用户补充检索或指明对象、不静默略过；⑤引擎的降级/未绑定/拦停注记必须如实转述进对应子问题条目、不得静默丢弃；⑥引用观察材料摘录必要短语并带引标、禁整段照搬原文充当回答；⑦「理解：／指标候选：」及任何动作 JSON 出现即废品。
  - R-L2b-03 逐字受测试看守：tests/domains/test_v2_v264_slice_origin.py:89-96（多来源拓宽形三处字面在场）与 :104-106（未覆盖来源给出路两句在场）。
- 耦合：本模块 `answer_turn_preamble`；跨文件同规则字面三处同步：appv2/runtime/graph.py `_ANSWER_INSTRUCTION`、`SYSTEM_PROMPT`（同测试文件三处并查）。
- 疑点（只列不判，不静默）：
  - D-L2b-01 同一答案规则以字面形式在 orientation `_ANSWER_REQUIREMENTS`／graph `_ANSWER_INSTRUCTION`／graph `SYSTEM_PROMPT` 三处并维护，无共享常量——防漂移仅靠三处字面在场断言（test_v2_v264_slice_origin.py:89-91）。

### `answer_turn_preamble`（orientation.py L293-300）｜写答案轮三件套置顶（题目锚/动词钉死/答案要求）
- 消费：`question: str`（位置参数）。docstring 注「V2-61 方案附 A 逐字」。
- 装配：拼装答案轮指令置顶三行，进答案轮发给模型的 user 消息（V2-80h 追加式：本串由调用方再拼材料段后整条追加对话链尾——graph.py:3868-3880）：
  1. 行1「用户问题：{question}」（题目锚；前缀固定「用户问题：」，全角冒号）
  2. 行2 动词钉死句：本步是写答案步、不再做任何决策、不再发射任何动作指令（明列 finalize/decompose 等动作出现即废品）
  3. 行3「【答案要求】」＋`_ANSWER_REQUIREMENTS` 全文
  - 返回串以 "\n" 收尾（供上层直接串接）。
- 分支表（穷尽）：
  1. 无分支 → 恒三行拼接（question 为空串也照拼，无校验）→ 返回 str → 去向：assembler 置顶（L312）或 graph 基线形（graph.py:3829）
- 副作用：无。
- 返回：str。
- 规则条目（一句话一条）：
  - R-L2b-04 三件套顺序固定：题目锚 → 动词钉死 → 答案要求；「【答案要求】」行内嵌 `_ANSWER_REQUIREMENTS` 全文。
  - R-L2b-05 无分支无校验：任何 question 字面照拼，无空值/类型防护。
  - R-L2b-06 消费两处：本模块 `assemble_answer_instruction`（L312，问题组形）；appv2/runtime/graph.py:3829（无问题组基线形，后接 `_ANSWER_INSTRUCTION`，追问轮再追 `_FOLLOWUP_HISTORY_ANSWER_CLAUSE`）。
- 耦合：本模块 `_ANSWER_REQUIREMENTS`；graph.py:93 直连 import（不在 runtime `__init__` 导出面）；测试 tests/domains/test_v2_v262_turn_selfsufficiency.py:38-41（T2）。
- 疑点（只列不判，不静默）：
  - D-L2b-02 同一题干存在两种前缀措辞：本函数「用户问题：」与 `anchor_line`「用户原题：」——决策轮/作答轮各用一词，是否统一属重构议题。
  - D-L2b-03 动词钉死句点名 finalize/decompose 等动作出现即废品，但起草面机检只覆盖 JSON 残留剥离（graph.py:3903 strip_emission_fences）与回声/粘贴观测（只记不拦）——无动作词机检面（事实登记）。

### `assemble_answer_instruction`（orientation.py L303-317）｜答案轮指令装配（三件套置顶＋既有字面依次居中/垫底）
- 消费：四个关键字参数（`*` 强制）：`question`、`summary_contract`、`subtask_list`、`answer_instruction`；`question` 仅透传给 `answer_turn_preamble`。
- 装配：答案轮指令一条串接（进答案轮 user 消息），段序：
  1. `answer_turn_preamble(question)` 三行（末字符为 "\n"）
  2. 空行（衔接用 "+ \n"）
  3. `summary_contract`（相位④汇总合同，调用方传 graph 常量 `SUMMARY_CONTRACT`）
  4. 「子问题结果清单：」标题行＋`subtask_list`（调用方逐子问题行拼装）
  5. 空行（"\n\n"）＋`answer_instruction`（调用方传 graph 常量 `_ANSWER_INSTRUCTION`）
  - 调用方再在尾部拼材料段成完整 user 消息（graph.py:3879-3880），追加对话链尾、不重发历史。
- 分支表（穷尽）：
  1. 无分支 → 恒五段拼接 → 返回 str → graph.py:3868-3880（仅 state.question_group 非空时改走本函数）
- 副作用：无。
- 返回：str。
- 规则条目（一句话一条）：
  - R-L2b-07 段序硬编码为「preamble → 空行 → 汇总合同 → 子问题结果清单 → 起草答案合同」；既有字面零删改（测试 T1 位置断言）。
  - R-L2b-08 入参全为关键字参数（L303-309），无位置参数；本函数不改任何入参内容。
  - R-L2b-09 调用点 graph.py:3828-3873：question_group 非空才用本函数覆盖基线形（L3829 的 preamble＋`_ANSWER_INSTRUCTION`）；追问条款（`_FOLLOWUP_HISTORY_ANSWER_CLAUSE`）由调用方追加、不在本函数。
- 耦合：本模块 `answer_turn_preamble`；appv2/runtime/graph.py（`SUMMARY_CONTRACT`、`_ANSWER_INSTRUCTION` 常量与调用点 L3868-3873）；tests/domains/test_v2_v262_turn_selfsufficiency.py:21-35（T1 三条位置断言）。
- 疑点（只列不判，不静默）：
  - D-L2b-04 答案轮指令有两条生产路径并存（问题组形走本函数；追问/基线形在 graph.py:3829 手拼 preamble＋instruction），装配逻辑部分散在调用点——重构归一议题。

### `anchor_line`（orientation.py L320-324）｜题意锚行（决策轮标准装配件——原题与理解置于当轮）
- 消费：`question: str`；`understanding: str = ""`（缺省空串）。
- 装配：单行文本，进决策轮 user 指令首行（后接对应相位合同）：
  - 形1（understanding 真值）：「用户原题：{question}｜题意：{understanding}」——前缀固定「用户原题：」、全角冒号，理解段以全角「｜」直接连接、无空格
  - 形2（understanding 假值）：「用户原题：{question}」
- 分支表（穷尽）：
  1. `if understanding`（真值）→ 拼「｜题意：{understanding}」→ 返回形1 → 相位①/②指令首行
  2. `if understanding` 为假（""、None 等）→ 单段形2 → 同上
- 副作用：无。
- 返回：str。
- 规则条目（一句话一条）：
  - R-L2b-10 两形由 `understanding` 真假值分流；假值不输出空「题意：」段。
  - R-L2b-11 前缀「用户原题：」与分隔符「｜」为固定字面（逐字受测试 test_v2_v262_turn_selfsufficiency.py:47-49 看守）。
  - R-L2b-12 去向＝决策轮指令首行两处：graph.py:2355（相位①·业务澄清）、graph.py:2700（相位②·工具匹配）；作用＝当轮自带原题与理解，免长历史考古。
- 耦合：appv2/runtime/graph.py:92 直连 import、调用点 L2355/L2700；tests/domains/test_v2_v262_turn_selfsufficiency.py:47-49。
- 疑点（只列不判，不静默）：
  - D-L2b-05 `understanding` 类型标注 str 但分支按真假值判——传 None 亦落单段形，无反 None 处理（事实登记）。
  - D-L2b-02 见上（「用户原题：」与「用户问题：」并存的两种前缀措辞）。

### `echo_signature_hit`（orientation.py L327-330）｜回声签名检测（只记不拦——模板头即过程废品特征）
- 消费：`draft: str`；graph 侧传入的是剥离后草稿（graph.py:3899 模型应答 → :3903 `.strip()`＋`strip_emission_fences` → :3949 传入）。
- 装配：不拼文本；产 bool 观测位。
- 分支表（穷尽）：
  1. `first = draft.split("\n", 1)[0].strip()`（首行、两侧空白剥除）后 `first.startswith("理解：")` → True
  2. 否则 `"指标候选" in draft[:100]`（草稿原始前 100 字符内含该子串，起始索引 ≤96）→ True
  3. 两条均不中 → False
- 副作用：无（纯函数，无 emit/日志/持久化）。
- 返回：bool。
- 规则条目（一句话一条）：
  - R-L2b-13 判定口径仅两条：首行以「理解：」开头，或草稿前 100 原始字符含「指标候选」（票面同款：tickets/v2/V2-62-轮次任务自足性治理.md:50-51）。
  - R-L2b-14 两判据范围不对称——「理解：」只认首行行首（strip 后、全角冒号）；「指标候选」认前 100 字符内任意位置（不限行、不需冒号、不受 strip 影响，draft 总长 <100 时即全稿）。
  - R-L2b-15 边界实测：空串 False；以换行开头（首行为空）且前 100 字无「指标候选」时 False——第 2 行行首「理解：」不救；前导空白＋「理解：」True（strip 后命中）；「指标候选」起始索引 101 False。
  - R-L2b-16 只记不拦（V2-62 零约束闸）：不拦停、不重试、不替换草稿——v1 回声检测闸已被 Owner 否决（V2-62 票 L13）。
  - R-L2b-17 消费去向：graph.py:3949 `echo_flag` 入 step_payload（:3947-3953）→ :3970-3972 process_notes 摘要（「echo=…」）＋ :3974-3977 step 记录 payload 落 `state.steps`；Q16 拿分布定阈值（graph.py:3946 注释）。
- 耦合：appv2/runtime/graph.py:96 直连 import、调用点 L3949；appv2/runtime/__init__.py `__all__` L226（幽灵导出，未 import）；tests/domains/test_v2_v262_turn_selfsufficiency.py:64-67（T5 两态）。
- 疑点（只列不判，不静默）：
  - D-L2b-06 首行判定与 100 字窗判定不对称：典型回声「理解：」若出现在第 2 行行首而前 100 字无「指标候选」，整条不命中——覆盖面是否够属阈值标定议题（只列）。
  - D-L2b-07 本函数与 `paste_ratio` 在 appv2/runtime/__init__.py `__all__`（L226/L235）内但未在该文件 import——幽灵导出（与 L3 报告 D-L3-19 为同一事实，此处挂本段符号名下）。

### `paste_ratio`（orientation.py L333-347）｜粘贴重合占比（只记不拦——观察 content 的 60 字窗逐字重合占比）
- 消费：`draft: str`（同上传剥离后草稿）；`observations: list[dict[str, Any]]`——仅读 `obs.get("content", "")` 并 `str()` 强转；graph 侧传 **未过滤全量** `list(state.observations or [])`（含 kind=notice 条目，graph.py:3950-3952）。
- 装配：不拼文本；产 float 观测位。
- 分支表（穷尽）：
  1. `not draft`（空串）→ L336-337 立即 0.0 → 返回
  2. 某观察 `len(content) < 60` → continue 跳过该观察 → 下一观察（全部跳过 → best=0 → 0.0）
  3. 某观察某对齐窗 `content[i:i+60] in draft` → best=max(best,60)、break 该观察窗循环 → 继续遍历下一观察（命中不早退观察循环；后续命中不改变数值）
  4. 全部观察无窗命中 → best=0 → 0.0
  5. 任一命中收尾 → `round(min(60/len(draft), 1.0), 4)` → 返回（命中蕴含 len(draft)≥60，min 为防御性恒等）
- 副作用：无（纯函数，无 emit/日志/持久化）。
- 返回：float——结果面等价二值：0.0 或 min(60/草稿字符数, 1.0)（四位小数）。
- 规则条目（一句话一条）：
  - R-L2b-18 窗口参数硬编码：窗宽恒 60、起点步进 40（i=0,40,80,…，`range(0, len(content)-59, 40)` 保证窗不越界；相邻窗重叠 20 字）。
  - R-L2b-19 逐观察独立扫描；`len(content)<60` 的观察直接跳过（不可能含 60 字窗）；缺 content 键取 ""（同被跳过）；非字符串 content 先 `str()` 强转再计长。
  - R-L2b-20 命中判据＝某整窗在草稿内逐字出现（子串包含）；命中即记 60（不测实际最长重合长度——连续 200 字照搬在 300 字草稿上仍记 60/300）。
  - R-L2b-21 归一化分母＝草稿字符数（非观察长度、非实际重合长度）；跨观察取 max（非累加/平均）；任一观察命中即同一数值。
  - R-L2b-22 漏检面实测（对齐效应）：任一 ≥99 字的连续逐字重合必被检出（必含一整对齐窗）；60-98 字的连续重合是否检出取决于起点对齐——offset 41 起的 60 字整段重合实测 0.0，98 字在 offset 1 实测 0.0。
  - R-L2b-23 零观察/空草稿 → 0.0（票面同款：V2-62 票 L52-53「窗口步进 40」、**只记账**、Q16 定阈值后另票议闸）。
  - R-L2b-24 消费去向：graph.py:3950-3952 入 step_payload → :3970-3972 process_notes 摘要（「paste=…」两位小数）＋ :3974-3977 step 记录 payload 落 `state.steps`。
- 耦合：`typing.Any`（L16 import、L333 注解）；appv2/runtime/graph.py:97 直连 import、调用点 L3950-3952；appv2/runtime/__init__.py `__all__` L235（幽灵导出）；tests/domains/test_v2_v262_turn_selfsufficiency.py:70-75（T6 态：60 字重合在场 >0、无重合 0.0、空草稿 0.0）。
- 疑点（只列不判，不静默）：
  - D-L2b-08 docstring「逐字重合最大长度 ÷ 草稿长度」与实现语义差：实现命中即记 60，不测真实最长重合长度——占比被系统性低估（连续 200 字重合在 300 字草稿报 0.2，非 0.67 量级）（事实登记，Q16 阈值标定前需知晓口径）。
  - D-L2b-09 对齐窗步进 40 的漏检面：60-98 字的未对齐连续重合可能不计（≥99 必检出，实测）——「只记不拦」前提下属观测噪声来源（只列）。
  - D-L2b-10 观察元素非 dict 时 `obs.get` 抛 AttributeError（注解声明 dict、运行期无防护）；另 notice 类观察未过滤即参与比对（短 notice 多被 <60 跳过，无保证）（事实登记）。

---

## 覆盖自检

- def/class 清单差集：无。L282-文末 5 函数＋1 模块常量全列入上表；本段无 class、无嵌套 def。
- 引用的外部符号全集（本文件内定义的除外）：`typing.Any`（L16 import，L333 注解消费）——本段代码体不引用任何其他外部模块符号。
- 本段符号的跨文件消费面（补充，供重构影响面用）：
  - 生产消费（appv2/runtime/graph.py，:92-98 直连 import）：`anchor_line` L2355/L2700；`answer_turn_preamble` L3829；`assemble_answer_instruction` L3868-3873；`echo_signature_hit` L3949；`paste_ratio` L3950-3952。
  - 导出面：appv2/runtime/__init__.py 仅 import `anchor_line`/`assemble_answer_instruction`（L105-115）并列入 `__all__`（L222/L223）；`echo_signature_hit`/`paste_ratio` 只在 `__all__`（L226/L235）无 import（幽灵导出，见 D-L2b-07）；`answer_turn_preamble` 未出导出面。
  - 测试：tests/domains/test_v2_v262_turn_selfsufficiency.py（T1/T2/T3/T5/T6 五用例）；tests/domains/test_v2_v264_slice_origin.py:89-96、:104-106（`_ANSWER_REQUIREMENTS` 字面）。
  - 票面：tickets/v2/V2-61-材料承载分形渲染.md（preamble docstring 注「V2-61 方案附 A 逐字」）；tickets/v2/V2-62-轮次任务自足性治理.md（L13 只记不拦／L50-53 观察字段定义／L79-87 验收）。
