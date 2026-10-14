# L1b·现状调研报告

- 锚定：commit e4b75f1（行号以此为准）
- 覆盖：appv2/runtime/subtask.py L297-文末（L428）
- 锚定核对：工作区 subtask.py 与 e4b75f1 git 内容 sha1 一致（298987e48a647c1a8b3bcb8cfdbfa0eb88842622）——行号可直接对读；本报告引用的 graph.py／guide.py／anchors.py／precondition.py／tests 三件与本 commit 零 diff（`git diff e4b75f1` 空）
- 段内常量：无模块级常量定义（文件全部常量在 L30-L58，属 L1a 段；本段引用段外常量 CHAIN_DATA L33／CHAIN_KINDS L35／_CHAIN_TOOL L40-L43）

## def/class 清单（段内全列）

| 符号 | 行号区间 | 形 |
| --- | --- | --- |
| SubtaskMatch | L296-L315（装饰器 L296、class L297、字段 L300-L305、as_payload L307-L315） | @dataclass(frozen=True, slots=True) |
| parse_tool_match | L318-L375（docstring L319；L378 为 V2-60 节界注释、非代码） | 模块级函数 |
| repair_inner_quotes | L381-L428（docstring L382-L387、扫描循环 L391-L420、终检 L421-L428） | 模块级函数 |

段界说明：SubtaskMatch 的 @dataclass 装饰器在 L296（L1a 已按界外列出 L296-L315）；本段从 L297 class 行起算，整块成节。

---

### `SubtaskMatch`（file L296-L315）｜工具匹配定案单元：子问题 id＋链＋工具＋计划/检索需求/口径支 key

- 消费：`parse_tool_match` L366-L371 逐支构造；graph.py L2766-L2776 对 retrieval_need 非 None 的支做 `replace(match, retrieval_need=inject_retrieval_anchors(...))`（锚注入后重绑新实例）；tests/domains/test_v2_four_phase.py L1466-L1485 断言 caliber_key 字段
- 调用：`as_payload` 被 graph.py L2801（step record 的 emission 摘要）与 L2831（写 `state.tool_matches`）消费；下游读取该 dict 序列的面：graph.py L2865（前置条件机节点）、L2946（前置条件节点）、L3243（批量执行）、L3842（汇总）
- 字段（L300-L305）：`id: str`／`chain: str`／`tool: str`（三者必填）；`plan: dict | None = None`；`retrieval_need: dict | None = None`；`caliber_key: str = ""`（注释 L305 自述 B5：场景词落定的口径支 key，可空）
- 分支表（穷尽，as_payload L307-L315）：
  1. 无条件下 → 底座 `{"id": self.id, "chain": self.chain, "tool": self.tool}` 三键（L308）
  2. `self.plan is not None` → payload 加 `"plan" = dict(self.plan)`（浅拷，L309-L310）
  3. `self.retrieval_need is not None` → payload 加 `"retrieval_need" = dict(self.retrieval_need)`（浅拷，L311-L312）
  4. `self.caliber_key` 真值 → payload 加 `"caliber_key"`（L313-L314）；假值（空串）→ 该键整体不出现
- 副作用：无（frozen＋slots，不可变；投影不发事件不写 store）
- 返回：`as_payload` 返回 `dict[str, Any]`
- 规则条目：
  - R-L1b-01 投影恒带 id／chain／tool 三键（无条件）
  - R-L1b-02 plan 非 None → 投影带 "plan"（dict 浅拷）；None → 键不出现
  - R-L1b-03 retrieval_need 非 None → 投影带 "retrieval_need"（dict 浅拷）；None → 键不出现
  - R-L1b-04 caliber_key 真值 → 投影带 "caliber_key"；空串 → 键不出现（对读：graph 定案合并 L2799 恒写该键——两投影面缺省语义不同，见 D-L1b-07）
- 耦合：`dataclasses.dataclass`（L296 装饰器）；`inject_retrieval_anchors`（appv2/tools/anchors.py L107，graph L2776 对字段做 replace）；`state.tool_matches: list[dict[str, Any]]`（state.py L164——as_payload 投影落该字段，字段注释自述「与 question_group 双面同源」）
- 疑点（只列不判，不静默）：
  - D-L1b-01 as_payload 空 caliber_key 不带键（L313），graph 定案合并恒写 "caliber_key" 键（graph L2789-L2799 item.update，含空串）——同一次定案的 question_group 投影与 tool_matches 投影（L2831 走 as_payload）该键缺省语义不同（事实列举）
  - D-L1b-02 frozen 只挡字段重绑：plan／retrieval_need 为浅拷贝 dict 字段（构造面 L356／L363 浅拷，投影面 L310／L312 再浅拷）——持有方可原地修改内容，frozen 不深冻

### `parse_tool_match`（file L318-L375）｜相位②发射解析＋闭合世界对账（matches ↔ 问题组一一对应）——工具匹配 schema 机检单点

- 消费：`content: str`（模型原话）、`group: QuestionGroup`（相位①定案，L326 取 `st.id` 全集）
- 调用：唯一生产调用点 graph.py L2736-L2738（toolmatch_node 内 `_parse_with_quote_repair(lambda c: parse_tool_match(c, group), content)`——先引号自修再解析）；再导出面 appv2/runtime/__init__.py L146／__all__ L234；tests/domains/test_v2_four_phase.py L47 import、L247-L278 单测、L1459-L1485 caliber_key 透传；tests/domains/test_v2_v257_rejection_locus.py L208-L214 以源码计数钉住 `json_syntax_feedback(content,` 在 subtask.py 恰 2 处（澄清＋本函数）
- 调用（下游）：返回 tuple 后 graph 侧 L2766-L2776 逐支注入检索锚、L2783-L2808 按 id 并入 question_group、L2831 以 as_payload 落 state.tool_matches；拒因 str 由 graph L2762-L2768 落 STEP_DECISION「工具匹配 r{rnd} 被拒」并回喂自环（不占新轮、轮照耗）
- 分支表（穷尽，按执行顺序；一处不过即返 str，fail-fast 不续扫）：
  1. `extract_plan_json(content)` 返 None → `json_syntax_feedback(content, "工具匹配不可解析——只输出一个 JSON")` → 返回 str（L320-L322）
  2. `payload.get("matches")` 非 list **或** 空 list → `"缺 matches（非空数组——组内每个子问题恰一条）"` → 返回 str（L323-L325；两形同一文案）
  3. 逐支（按发射顺序）：
     3a. 支非 dict → `"matches 支须为对象（{id/chain/tool/plan|retrieval_need}）"` → 返回 str（L331-L332）
     3b. `id = str(raw.get("id") or "").strip()` 为空 → `"matches 支缺 id"` → 返回 str（L333-L335）
     3c. id 不在组 id 集 → `f"matches id {match_id!r} 不在问题组内（闭合世界：{group_ids}）"` → 返回 str（L336-L337）
     3d. id 已在 seen → `f"matches id 重复：{match_id!r}（每子问题恰一条匹配）"` → 返回 str（L338-L339）
     3e. `chain` 归一后 ∉ CHAIN_KINDS → `f"matches {id} chain 越界（data/knowledge）：{chain!r}"` → 返回 str（L340-L342）
     3f. `tool` 归一后为空 → `f"matches {id} 缺 tool"` → 返回 str（L343-L345）
     3g. `tool != _CHAIN_TOOL[chain]` → `f"matches {id} chain/tool 不一致（{chain} 链须配 {_CHAIN_TOOL[chain]}）"` → 返回 str（L346-L347）
     3h. chain == "data"：`raw.get("plan")` 非 dict → `f"matches {id} data 链缺 plan（data_query 计划草案对象）"`；dict 但 `metric_slot` 归一后空 → `f"matches {id} plan 缺 metric_slot（必填非空）"`；全过 → `plan = dict(raw_plan)` 浅拷（L350-L356）
     3i. 否则（chain == "knowledge"）：`raw.get("retrieval_need")` 非 dict → `f"matches {id} knowledge 链缺 retrieval_need（参数对象）"`；dict 但 `question` 归一后空 → `f"matches {id} retrieval_need 缺 question（必填非空）"`；全过 → `need = dict(raw_need)` 浅拷（L357-L363）
     3j. `caliber_key = str(raw.get("caliber_key") or "").strip()`——零校验装载（L364）
     3k. seen.add(match_id)＋追加 SubtaskMatch（L365-L371）
  4. 组内存在未见 id → `f"matches 覆盖缺口（组内子问题缺匹配：{missing}）——每子问题恰一条"` → 返回 str（L372-L374）
  5. 组内 id 全见 → `tuple(matches)`（L375）
- 副作用：无（纯函数；不发事件、不写 store、不调模型——事件/落档全在 graph 调用点）
- 返回：`tuple[SubtaskMatch, ...]`（合法发射）或 `str`（拒因正文，回喂 LLM 重发射、无 repair 契约）
- 规则条目（一句话一条：条件＋动作＋去向）：
  - R-L1b-05 提取失败 → json_syntax_feedback 拼「工具匹配不可解析——只输出一个 JSON」→ 返回 str 回喂
  - R-L1b-06 matches 缺失/非 list/空 list → 同一拒因「缺 matches（非空数组）」→ 返回 str
  - R-L1b-07 任一支非对象 → 拒 → 返回 str
  - R-L1b-08 支 id 归一后为空 → 拒 → 返回 str
  - R-L1b-09 支 id 不在组 id 集 → 拒（拒因内列 group_ids 全量）→ 返回 str
  - R-L1b-10 支 id 归一后与已见重复 → 拒 → 返回 str
  - R-L1b-11 支 chain 归一后 ∉ {data, knowledge} → 拒 → 返回 str
  - R-L1b-12 支 tool 归一后为空 → 拒 → 返回 str
  - R-L1b-13 支 tool ≠ 该链唯一工具（data→data_query／knowledge→doc_retrieve）→ 拒 → 返回 str
  - R-L1b-14 chain=data 且 plan 非 dict → 拒 → 返回 str
  - R-L1b-15 chain=data 且 metric_slot 归一后为空 → 拒 → 返回 str；非空过闸但不做值域校验
  - R-L1b-16 chain=knowledge 且 retrieval_need 非 dict → 拒 → 返回 str
  - R-L1b-17 chain=knowledge 且 question 归一后为空 → 拒 → 返回 str
  - R-L1b-18 caliber_key 经 `str() or ""` 归一（缺失/None→空串）装载 SubtaskMatch——本函数零值域校验（合法口径三态在下游前置条件机）
  - R-L1b-19 支全过 → seen 记入归一 id、按发射顺序追加 SubtaskMatch（plan/retrieval_need 浅拷、caliber_key 原样）
  - R-L1b-20 组内某 id 未在 seen → 覆盖缺口拒（列出全部缺失 id）→ 返回 str；「未知 id 拒＋重复拒＋缺失拒」三刀合成恰一一对应（无多余、无重复、无遗漏）
  - R-L1b-21 全部过闸 → 返回 tuple(matches)（顺序＝发射顺序，不回排组序）
- 耦合：`extract_plan_json`（L320，本文件 L61）、`json_syntax_feedback`（L322，本文件 L82）、`CHAIN_KINDS`／`CHAIN_DATA`（L33-L35）、`_CHAIN_TOOL`（L40-L43）、`SubtaskMatch`（L297）、`QuestionGroup.subtasks[].id`（本文件 L143／L150-L177、构造在 `_question_group_of` L193 同款 str+strip 归一）；下游 `inject_retrieval_anchors`（graph L2776）；合同同源面 guide.py TOOLMATCH_CONTRACT（L99-L124，本 commit 无 diff）
- 疑点（只列不判，不静默）：
  - D-L1b-03 合同-机检落差：guide.py TOOLMATCH_CONTRACT（L110-L124）声明 plan「缺 ranking 等必填键＝参数校验拒」、retrieval_need「只许这三个键，禁造键名」；本函数只机检 metric_slot（L354）／question（L361）非空，两 dict 整体浅拷贝照单全收（L356／L363）——键白名单与其余必填键不在本函数校验面（下游是否补检＝段外，本段未证）
  - D-L1b-04 caliber_key 零校验：任何非空串装载（L364）；合法口径校验按模块 docstring（L12-L13）自述在前置条件机（precondition.py L424-L489 为其消费点）
  - D-L1b-05 chain 先 `str()` 归一（L340）：raw 里数字/布尔/列表型 chain 不抛异常、统一字符串化后走「越界」拒；L346 `_CHAIN_TOOL[chain]` 查表仅在 chain ∈ CHAIN_KINDS 判定之后执行（L33-L43 键集与 CHAIN_KINDS 同源，无 KeyError 面）
  - D-L1b-06 id 双侧归一依赖：本函数对 id `str()+strip`（L333）后对账，组 id 在 `_question_group_of` L193 同款归一——两侧同款是闭合对账前提；返回的 SubtaskMatch.id 是归一后值
  - D-L1b-07 返回 tuple 保发射顺序（L366 追加序）不回排组序；下游以 by_id 映射合并（graph L2783-L2787）消化顺序无关
  - D-L1b-08 拒因全为中文自然语言 str，无类型化错误码；fail-fast 首拒即返——同一次发射里的多类错误只回喂最靠前一条

### `repair_inner_quotes`（file L381-L428）｜值内裸英文双引号确定性修复（纯字符处理，零语义零模型）——修后过 json.loads 才受理

- 消费：`text: str`（整段模型原话——唯一调用点 graph.py L402 传 `content` 全文，非提取后的 JSON 片段）
- 调用（caller）：graph.py `_parse_with_quote_repair`（L392-L408）唯一生产调用点；该包装被 graph L1728（understand/decision 面）、L2425（clarify）、L2736（toolmatch）三处使用；tests/domains/test_v2_v260_quote_rule.py L12 import、L21-L26 四形单测、L29-L56 包装面测试
- 扫描/替换规则（逐字符，L391-L420）：
  - 态变量：`in_string`（在串/不在串）、`inner_open`（本串内已出开引号未出闭）
  - 不在串：遇 `"` → 进入串态且 inner_open 复位 False（L395-L397）；字符一律原样 append（L398）
  - 在串且字符 `\`：连同其后 1 字符（`text[i:i+2]`）整体原样拷贝、不参与引号判定（L401-L403）——`\"` 不误伤；文本末尾孤立 `\` 时切片只得 1 字符，i 越界循环自然结束
  - 在串且非 `"`：原样 append、i+1（L405-L408）
  - 在串且 `"`：先看其后（i+1 起跳过空格/`\t`/`\r`/`\n`，可为空窗）的首个非空白字符 nxt：
    - nxt ∈ `,` `}` `]` `:`（L413）→ 认定「结构引号＝串的合法闭合」：in_string=False、inner_open 复位 False、字符原样 append
    - 否则（含 nxt = "" 文末形，L412 兜空串）→ 认定「值内裸引号」：替换为 `「`（该串内首处）或 `」`（其后交替——inner_open 取反），in_string 保持 True（该引号不当闭合用）（L417-L419）
  - 替换不区分引号对语义、不找配对；串外引号（开串那一个）永不改写
  - 值内引号判定的边界：nxt 只在「跳空白后」取值，故 `"x" ,` 是结构引号、`"x""y"` 中第一个引号因 nxt=`"` 被判值内引号
- 返回路径（L421-L428）：拼出 repaired 后——`repaired == text`（无任何替换＝无值内引号）→ None（无病不修）；有替换 → 对**全文** `json.loads(repaired)`：抛 `json.JSONDecodeError` → None；成功 → 返回 repaired
- 分支表（穷尽，按执行顺序）：
  1. 扫描中 `not in_string` 且 ch 任意 → 原样 append；ch == `"` 时额外开串＋inner_open=False（L394-L400）
  2. `in_string` 且 ch == `\` → 拷 2 字符、i+=2（L401-L403）
  3. `in_string` 且 ch != `"` → 原样、i+=1（L405-L408）
  4. `in_string` 且 ch == `"`：跳空白取 nxt
     4a. nxt ∈ {`,`, `}`, `]`, `:`} → 闭串＋inner_open 复位、原样（L413-L416）
     4b. 否则 → 替换 `「`/`」`（交替）、串态保持（L417-L419）
  5. `repaired == text` → 返回 None（L422-L423）
  6. `json.loads(repaired)` 抛 JSONDecodeError → 返回 None（L424-L427）
  7. 成功 → 返回 repaired（L428；验收只查语法，不查顶层类型）
- 副作用：无（零模型调用、零新依赖；不发事件——修复受理 notice 由 graph L2740-L2742／L2437-L2438／L1730-L1731 发）
- 返回：`str | None`——str＝修复后全文（唯一受理出口＝全文可解析）；None＝无病可修或修后仍解析失败（两形不可区分）
- 规则条目（一句话一条：条件＋动作＋去向）：
  - R-L1b-22 不在串态 → 字符原样；遇 `"` 开串且 inner_open 复位 → 扫描继续
  - R-L1b-23 在串遇 `\` → 连同后 1 字符原样拷贝、不判引号 → 扫描继续
  - R-L1b-24 在串遇非 `"` → 原样拷贝 → 扫描继续
  - R-L1b-25 在串遇 `"` 且跳空白后首字符 ∈ {`,`, `}`, `]`, `:`} → 认定结构引号：闭串＋inner_open 复位＋原样 → 扫描继续
  - R-L1b-26 在串遇 `"` 且跳空白后首字符 ∉ 结构集（含文末空串）→ 认定值内裸引号：替换为 「/」（按该串内出现次序交替）、串态保持 → 扫描继续
  - R-L1b-27 扫描完 replaced 与原文相同（无值内引号）→ 返回 None（无病不修）→ 调用方走原拒因
  - R-L1b-28 有替换且全文 json.loads 成功 → 返回 repaired（受理）→ graph 侧复解析＋发 emission_quote_repair notice；json.loads 失败 → None → 调用方走既有 V2-57 定位回喂
- 耦合：`json.loads`／`json.JSONDecodeError`（L425-L426）；唯一 caller graph.py `_parse_with_quote_repair` L392-L408（L399-L407：修好→复解析，二次解析仍 str→仍返 (原拒因, False)；复解析走 extract_plan_json 首平衡块，与 L425 全文判据不同面）；合同同源面 guide.py TOOLMATCH_CONTRACT L100-L103（「值内裸引号将字符串提前截断」逐字规矩）
- 疑点（只列不判，不静默）：
  - D-L1b-09 扫描自文本首字符起、无「先定位 JSON 块」步骤；输入是整段模型原话（graph L402 传全文）——围栏/散文里的引号同样参与在串/不在串状态推进；误替换由 L424-L427 挡回，但验收判据只有「全文可解析」一条：偶然拼成合法 JSON 的误替换同样会被受理（fence 反引号本身不含 `"`，常见围栏形不受影响；本段只列事实）
  - D-L1b-10 受理判据 L425 是**全文** json.loads，非 extract_plan_json 平衡块提取——含围栏/前导散文的输出修后仍解析失败 → 恒 None（修复通道实际只在「整段文本本身＝单个合法 JSON 文档」时可能受理）；而 caller 复解析走 extract_plan_json（graph L399-L407）——两判据面不同（全文文档 vs 首平衡块）
  - D-L1b-11 「无病不修」（L422-L423）与「修后仍失败」（L426-L427）两形同为 None，调用方不可区分（graph L403-L404 两形同路 → (原拒因, False)）
  - D-L1b-12 文末引号判定：`"` 后无字符时 nxt=""（L412）∉ 结构集 → 被判值内引号替换、串态不复位——`{"a": "x"` 这类截断形修复后仍非法（tests/domains/test_v2_v260_quote_rule.py L31 断言 None 即此形）
  - D-L1b-13 替换为「/」按「每串内出现次序交替」（inner_open 在开串 L397 与结构闭串 L415 两处复位）——不做引号配对语义；某串内值内引号个数为奇数时修后串不闭合（引号修不了结构伤，收尾由 json.loads 拒）；同为结构合法的情形也可能因 nxt 判定被改（如 `"x""y"` 相邻两串形中前者闭引号被判值内）
  - D-L1b-14 验收不查顶层类型（L425-L428）：json.loads 成功即返回 repaired——顶层数组/标量同样受理，与 extract_plan_json 的 dict 要求（L74-L78）不同；下游 caller 复解析时再受 dict 约束（graph L399-L407，超出即原拒因）
  - D-L1b-15 替换为全量替换＋一次性终检（无逐处试错/回退）：任何一处替换导致全文非法即整体 None——不返回部分修复结果

---

## 覆盖自检

- def/class 清单差集：无。L297-文末（L428）内的 3 个符号（SubtaskMatch／parse_tool_match／repair_inner_quotes）全部逐一成节；段内无模块级常量定义（常量全在 L30-L58，L1a 已列），段内无嵌套 def/class
- 引用的外部符号全集（本文件内定义的除外）：
  - `json.loads`、`json.JSONDecodeError`（L425-L426）
  - `dataclasses.dataclass`（L296 装饰器；本段不用 replace）
  - `typing.Any`（L303-L304 注解）
  - 同文件段外符号：`extract_plan_json`（L61，被 L320 调）、`json_syntax_feedback`（L82，被 L322 调）、`QuestionGroup`（L139，L318 入参注解、L326 读 subtasks）、`CHAIN_DATA`（L33）、`CHAIN_KINDS`（L35）、`_CHAIN_TOOL`（L40-L43）
  - 外部文件的说明性引用（本次核对，均与锚定 commit 零 diff）：graph.py L392-L408（_parse_with_quote_repair）、L1728／L2425／L2736（三调用点）、L2766-L2808／L2831（定案注入与落 state）；appv2/tools/anchors.py L107（inject_retrieval_anchors）；appv2/tools/precondition.py L424-L489（caliber 消费面）；appv2/runtime/state.py L164（tool_matches 字段）；appv2/runtime/guide.py L99-L124（TOOLMATCH_CONTRACT）；tests/domains/test_v2_four_phase.py L247-L278／L1459-L1485、tests/domains/test_v2_v260_quote_rule.py L19-L56、tests/domains/test_v2_v257_rejection_locus.py L208-L214
