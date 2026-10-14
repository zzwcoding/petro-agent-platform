# L1a·现状调研报告

- 锚定：commit e4b75f1（行号以此为准）
- 覆盖：appv2/runtime/subtask.py L1-L296
- 锚定核对：工作区文件与 e4b75f1 的该文件 git 内容 sha1 一致（298987e48a647c1a8b3bcb8cfdbfa0eb88842622）——行号可直接对读
- 本段内 import 只有标准库（json／dataclasses.dataclass、replace／typing.Any），零 appv2 内部依赖（L21-L25）

## 段内文件头声明（L1-L19，docstring，不可执行）

- L3-L4：声明本模块＝四相位两道 schema 收口，「LLM 出语义，本模块出结构判定——零 LLM 纯校验」
- L5-L8：相位①业务澄清发射（parse_question_group）为 discover｜decompose｜ask｜finalize 四动作闭世界；decompose 产出 QuestionGroup（subtasks[{id/question/ledger_notes/chain?/tool?}]）；子问题上限 ≤4（Owner 认可值）；ledger_notes 必填非空（从词典层注入块逐字转抄，前置条件机按注释过闸）
- L9-L13：相位②工具匹配发射（parse_tool_match）与问题组闭合世界对账；chain/tool 一致（data→data_query、knowledge→doc_retrieve）；data 链必带 plan、knowledge 链必带 retrieval_need；caliber_key 可选
- L15-L16：extract_plan_json 自 graph.py 迁入本模块（graph 侧 re-export 保持旧名可用）
- L18：拒因返回 str（回喂 LLM 重发射——无 repair，与 parse_decision 同款契约）

## def/class 清单（段内全列）

| 符号 | 行号区间 | 形 |
| --- | --- | --- |
| extract_plan_json | L61-L79 | 模块级函数 |
| json_syntax_feedback | L82-L110 | 模块级函数 |
| Subtask | L116-L136（as_payload L126-L136） | @dataclass(frozen=True, slots=True) |
| QuestionGroup | L139-L146（as_payload L145-L146） | @dataclass(frozen=True, slots=True) |
| ClarifyEmission | L149-L176（as_payload L161-L176） | @dataclass(frozen=True, slots=True) |
| _question_group_of | L179-L223 | 模块级私有函数 |
| parse_question_group | L226-L290 | 模块级函数 |

段界外（同文件、不属本段，未展开）：SubtaskMatch L296-L315、parse_tool_match L318-L379、repair_inner_quotes L381-L428。

---

### `extract_plan_json`（file L61-L79）｜从任意文本中取首个花括号平衡块并当 JSON 解析，失败给 None

- 消费：`content: str`（LLM 原话，裸产／围栏产／散文包裹产同路）
- 调用：`parse_question_group` L238、`parse_tool_match` L320（段外）、graph.py parse_decision L586、graph.py understand 降级形 L459；graph.py L122-L132 以 re-export 形式 import 旧名
- 分支表（穷尽）：
  1. `content.find("{") < 0` → 返回 None → 调用方转拒因
  2. 扫描自首个 `{` 起逐字符计数深度（`{` 加一、`}` 减一）；深度回到 0 的位置 → 取 `content[start:position+1]` 交 `json.loads`
     2a. 抛 `json.JSONDecodeError` → 返回 None → 调用方转拒因（不再找后续块）
     2b. 解析成功且顶层是 dict → 返回该 dict
     2c. 解析成功但顶层非 dict → 返回 None
  3. 扫到串尾深度未回到 0（括号不平衡）→ 返回 None
- 副作用：无
- 返回：`dict[str, Any] | None`
- 规则条目：
  - R-L1a-01 无左花括号 → 返回 None → 调用方（L240／L322／graph L588）出拒因
  - R-L1a-02 首个平衡块 JSON 语法坏 → 返回 None（不续扫后续块）
  - R-L1a-03 首个平衡块解析成功且为对象 → 返回该对象
  - R-L1a-04 首个平衡块解析成功但顶层非对象 → 返回 None（该支不可达，见 D-L1a-02）
  - R-L1a-05 括号始终不平衡 → 返回 None
- 耦合：`json.loads`、`json.JSONDecodeError`
- 疑点（只列不判，不静默）：
  - D-L1a-01 只读首个平衡块；首块坏即 None——同一输出里第二个合法 JSON 不可达（提取单点为「首块即全信」语义）
  - D-L1a-02 L78 `loaded if isinstance(loaded, dict) else None` 的 else 支不可达（以平衡花括号围出的片段 loads 成功时必为 JSON 对象）——纯防御写法，与 R-L1a-04 同一事实

### `json_syntax_feedback`（file L82-L110）｜解析失败时重放同款扫描，把 json 异常定位与坏点邻域拼进拒因

- 消费：`content: str`（同一次失败的原话）、`fallback: str`（调用方的笼统拒因前缀）
- 调用：`parse_question_group` L240、`parse_tool_match` L322（段外）、graph.py parse_decision L588；三个调用点均以字面量 `json_syntax_feedback(content,` 形式出现，被 tests/domains/test_v2_v257_rejection_locus.py L212-L213 以源码计数钉住（subtask.py 恰 2、graph.py 恰 1）
- 分支表（穷尽）：
  1. `content.find("{") < 0` → 返回 `fallback + "——输出中没有任何以左花括号起始的 JSON 对象（检查是否漏了 JSON 外壳、只输出了围栏或解释文字）"`
  2. 重放平衡块扫描；深度回到 0 的片段交 `json.loads`
     2a. 抛 `json.JSONDecodeError` → 绝对坏点位置 `bad = start + exc.pos`（L102，exc.pos 是片段内相对位）→ 片段窗 `content[max(0, bad-40) : bad+40]` → 返回 `fallback + "——JSON 语法错误：{exc.msg}（约第 {bad} 字符）。常见原因：少写右括号或方括号、尾逗号、引号未闭合。你上次输出坏点附近原文：「{snippet}」——只修正语法错误，结构与其余内容照旧，重新输出一个 JSON。"`
     2b. `json.loads` 成功 → 不返回，循环继续走完
  3. 扫描走完（含 2b 与「括号从未平衡」两形）→ 返回裸 `fallback`（L110，无定位、无外壳提示）
- 副作用：无（零模型调用、零新依赖——L85 声明）
- 返回：`str`（回喂 LLM 的拒因正文）
- 规则条目：
  - R-L1a-06 无左花括号 → fallback 追加「没有任何以左花括号起始」＋「漏了 JSON 外壳」提示 → 回喂 LLM
  - R-L1a-07 平衡块内 JSON 语法坏 → fallback 追加 `exc.msg`＋绝对坏点字符序号＋坏点 ±40 字符原文＋「只修正语法错误」指令 → 回喂 LLM
  - R-L1a-08 括号始终不平衡（截断形）→ 仅返回 fallback 裸文（定位线索为零）
- 耦合：`json.loads`、`json.JSONDecodeError`、`exc.msg`／`exc.pos`
- 疑点（只列不判，不静默）：
  - D-L1a-03 L110 兜底注释自称「重放意外成功（防御性——理论不可达）」，但「花括号始终不平衡」的输入实际落此支（截断输出形；tests/domains/test_v2_v260_quote_rule.py L44 的坏例 `{"action": "decompose", "question_group": {` 即此形，测试只断言返回 str）；此支与 R-L1a-06 的「无花括号」支同为无定位裸 fallback，两种不同病征在拒因上不可区分

### `Subtask`（file L116-L136）｜子问题最小单元：id／问题原文／台账注释＋工具链提议

- 消费：`_question_group_of` L217-L222 构造；graph.py `_group_of` L2293-L2310 从 `state.question_group` 载荷重建（恢复段读面）
- 字段（L120-L124）：`id: str`、`question: str`、`ledger_notes: str`（三者必填）；`chain: str = ""`、`tool: str = ""`（提议，可空——相位②收口定案）
- 分支表（穷尽，as_payload L126-L136）：
  1. 恒带 `id`／`question`／`ledger_notes` 三键
  2. `self.chain` 真值 → payload 加 `"chain"`
  3. `self.tool` 真值 → payload 加 `"tool"`
- 副作用：无（frozen＋slots，不可变）
- 返回：`as_payload` 返回 `dict[str, Any]`
- 规则条目：
  - R-L1a-09 chain 非空 → 投影带 "chain"（空则整个键不出现——反向对读：graph `_group_of` L2303 以 `or ""` 兜缺键，round-trip 相容）
  - R-L1a-10 tool 非空 → 投影带 "tool"
- 耦合：无（本段内零外部调用；投影键名与 state.py L160-L162 注释、graph.py L2288-L2310 读面同源）
- 疑点（只列不判，不静默）：无

### `QuestionGroup`（file L139-L146）｜问题组容器：带台账注释的子任务序列

- 消费：`_question_group_of` L223 构造；graph.py `_group_of` L2298-L2310 重建；graph.py L2491 读 `emission.group.subtasks` 计数
- 字段（L143）：`subtasks: tuple[Subtask, ...]`
- 分支表（穷尽，as_payload L145-L146）：无分支，恒返回 `{"subtasks": [每支 as_payload()]}`
- 副作用：无
- 返回：`as_payload` 返回 `dict[str, Any]`
- 规则条目：
  - R-L1a-11 恒以 `{"subtasks": [...]}` 单键形落盘／入 step payload（图侧消费点：graph L2508 落 `state.question_group`；state.py L160-L162 声明该字段）
- 耦合：state.py `RunState.question_group: dict[str, Any] | None`（L162）；blackbox.py L28／L57 蒸馏白名单收录键名 `"question_group"`
- 疑点（只列不判，不静默）：无

### `ClarifyEmission`（file L149-L176）｜相位①发射定型形（四动作合一出口）

- 消费：`parse_question_group` L246-L250 构造，L267／L272／L290 以 `replace` 补载荷（L274 finalize 原样返回、不 replace）；tests 直接断言字段
- 字段（L153-L159）：`kind: str`（discover|decompose|ask|finalize）；`group: QuestionGroup | None = None`；`discovers: tuple[dict[str, Any], ...] = ()`；`ask_prompt: str = ""`；`ask_options: tuple[str, ...] = ()`；`thought: str = ""`；`note: str = ""`
- 分支表（穷尽，as_payload L161-L176）：
  1. 恒带 `"action": self.kind`
  2. `self.thought` 真值 → 带 `"thought"`
  3. `self.note` 真值 → 带 `"note"`
  4. `self.group is not None` → 带 `"question_group": group.as_payload()`
  5. `self.discovers` 非空 → 带 `"discovers": [dict(item) for item in ...]`（逐支浅拷）
  6. `self.ask_prompt` 真值 → 带 `"ask": {"prompt": ask_prompt, "options": list(ask_options)}`
  7. `self.ask_prompt` 空 → 不输出 `"ask"`（即使 ask_options 非空，一并丢弃）
- 副作用：无
- 返回：`as_payload` 返回 `dict[str, Any]`
- 规则条目：
  - R-L1a-12 thought/note 非空 → 随投影带出（值源自 payload 原样 `str()` 归一，见 R-L1a-23）
  - R-L1a-13 kind=decompose → 投影带 question_group 段
  - R-L1a-14 kind=discover → 投影带 discovers 段（浅拷，args 嵌套对象未深拷）
  - R-L1a-15 kind=ask → 投影带 ask 段（prompt＋options），且该段的存在判据只看 prompt
- 字段消费（下游谁读，事实）：graph.py clarify 节点按 `emission.kind` 三分派（`CLARIFY_DECOMPOSE` L2489、`CLARIFY_DISCOVER` L2517、`CLARIFY_FINALIZE` L2569，其余即 ask 路 L2631-L2668）；读 `emission.group` L2491/L2508、`emission.discovers` L2520/L2549/L2560、`emission.note` L2499/L2614、`emission.ask_prompt` L2651/L2657/L2668、`emission.ask_options` L2652；`emission.thought` 除本类 as_payload 外图侧零读取（只随 step payload 落档）
- 耦合：graph.py L495-L526 `DecisionEmission`（字段与 as_payload 逐段同形——两处并列，无共享基类）；graph.py L121-L133 从本模块 import 12 名（含 `QuestionGroup`／`Subtask`／`MAX_SUBTASKS_CONTRACT`／`BUDGET_REJECT_MARK`／三个 CLARIFY_* 动作常量——不含 `ClarifyEmission` 本身，图侧只经 `parse_question_group` 返回值使用）；appv2/runtime/__init__.py L140-L146 再导出 `ClarifyEmission`／`QuestionGroup`／`Subtask`／`MAX_SUBTASKS_CONTRACT`
- 疑点（只列不判，不静默）：
  - D-L1a-04 ask 段以 `ask_prompt` 真假单点开闸（L171）——`ask_options` 单有值的构造态在投影中静默消失（校验层产不出该态：ask 成功路径 prompt 必非空）
  - D-L1a-05 `ClarifyEmission`（L149-L159）与 graph.py `DecisionEmission`（L495-L508）字段面／投影面高度重复（ask 段、discovers 段、thought/note 段逐行同款），两处无共享定义

### `_question_group_of`（file L179-L223）｜question_group 载荷校验（澄清发射 schema 的机检面）

- 消费：`raw: Any`＝`payload.get("question_group")`（L269 传入）；`max_subtasks: int`（关键字参数，无默认值）
- 调用：`parse_question_group` L269（唯一调用点；私有，仓内零外部引用）
- 分支表（穷尽）：
  1. `not isinstance(raw, dict)` → 返回 `"decompose 缺 question_group 对象"`
  2. `raw.get("subtasks")` 非 list 或为空列表 → 返回 `"question_group 缺 subtasks（非空数组）"`
  3. `len(raw_subtasks) > max_subtasks` → 返回 `f"subtasks 超出上限（≤{max_subtasks} 个——Owner 认可值）"`
  4. 逐支（L190-L222），每支按序过闸：
     4a. 支非 dict → `"subtasks 支须为对象（{id/question/ledger_notes/...}）"`
     4b. `id/question/ledger_notes` 各经 `str(x or "").strip()` 归一（L193-L195）；id 归一后空 → `"subtasks 支缺 id（组内唯一标识）"`
     4c. id 已在 `seen` 集 → `f"subtasks id 重复：{id!r}"`
     4d. question 归一后空 → `f"subtasks {id} 缺 question（子问题原文）"`
     4e. ledger_notes 归一后空 → `f"subtasks {id} 缺 ledger_notes（台账注释必带——从词典层逐字转抄：〈精确指标 slot 名〉〈绑定态〉〈锚定窗〉）"`
     4f. chain 非空且 `not in CHAIN_KINDS` → `f"subtasks {id} chain 越界（data/knowledge）：{chain!r}"`
     4g. tool 非空且 `not in set(_CHAIN_TOOL.values())` → `f"subtasks {id} tool 越界（data_query/doc_retrieve）：{tool!r}"`
     4h. 全过 → `seen.add(id)`；`Subtask(id, question, ledger_notes, chain, tool)` 入列（支内未知键静默丢弃，不报错不保留）
  5. 全部支过 → 返回 `QuestionGroup(subtasks=tuple(subtasks))`
- 副作用：无（局部 `seen`／`subtasks` 不上抛；不改 `raw`）
- 返回：`QuestionGroup | str`（str＝拒因原文，由调用方原样上抛回喂）
- 规则条目：
  - R-L1a-16 raw 非 dict → 拒「decompose 缺 question_group 对象」→ parse_question_group 原样返回 str
  - R-L1a-17 subtasks 非 list 或空 → 拒「question_group 缺 subtasks（非空数组）」
  - R-L1a-18 支数 > max_subtasks（默认 4）→ 拒「subtasks 超出上限」
  - R-L1a-19 支非 dict → 拒「subtasks 支须为对象」
  - R-L1a-20 id 归一后空 → 拒；同支内重复 → 拒（组内唯一）
  - R-L1a-21 question 归一后空 → 拒「缺 question（子问题原文）」
  - R-L1a-22 ledger_notes 归一后空 → 拒「缺 ledger_notes」（台账注释必带纪律的唯一机检点）
  - R-L1a-23 id／question／ledger_notes 三键经 `str(值 or "").strip()` 归一：null／缺失→空串、数字→十进制字符串、前后空白剥除（判空与落值用同一归一结果）
  - R-L1a-24 chain 非空且越界（闭世界仅 data／knowledge）→ 拒——空串合法（提议可缺，定案归相位②）
  - R-L1a-25 tool 非空且越界（闭世界仅 data_query／doc_retrieve）→ 拒——空串合法
  - R-L1a-26 chain／tool 本层不做「链-工具一致」校验（data 配 doc_retrieve 在此通过；一致性闸在相位② parse_tool_match L346，段外）；本层也不校验 data 链是否带 plan／knowledge 链是否带 retrieval_need
  - R-L1a-27 支全过 → 构造 frozen `Subtask` 列成 `QuestionGroup` → 返回（去向：parse_question_group replace 进 ClarifyEmission.group → graph L2508 落 `state.question_group`）
- 耦合：`CHAIN_KINDS`（L35）、`_CHAIN_TOOL`（L40-L43）仅本模块使用；下游读面 graph.py L2288-L2310、state.py L160-L162
- 疑点（只列不判，不静默）：
  - D-L1a-06 闸序：id 重复检查（L198）先于 question（L200）／ledger_notes（L202）必填检查——同支既重复又缺字段时只出重复拒因（缺字段病因被遮蔽，模型只见其一）
  - D-L1a-07 本层对 `raw` 只白名单读 6 个键（id/question/ledger_notes/chain/tool＋容器 subtasks），支内／容器内未知键与多余键零反馈（静默丢弃/忽略）
  - D-L1a-08 链-工具一致性与链-载荷配套（plan／retrieval_need）校验不在本层（L318 起相位②负责）：本层对「chain=data 且 tool=doc_retrieve」等组合全部放行——阶段分工事实，归属待确认

### `parse_question_group`（file L226-L290）｜相位①发射解析＋schema 校验（拒因回喂，无 repair）

- 签名（L226-L232）：`parse_question_group(content: str, *, max_discovers: int = 2, discover_budget_left: int | None = None, max_subtasks: int = MAX_SUBTASKS_CONTRACT) -> ClarifyEmission | str`
- 消费：`content: str`（LLM 原话）；`max_discovers`（单次发现支数上限）；`discover_budget_left`（本 run 剩余发现预算；非 None 时启用确定性预算闸）；`max_subtasks`（转发给 `_question_group_of`）
- 调用：graph.py L2426-L2434（clarify 节点唯一生产调用，经 `_parse_with_quote_repair` 包一层引号自修：graph.py L392-L409——首解为 str 时用 `repair_inner_quotes` 修一次再解析，修好则发 `emission_quote_repair` notice，修不好原拒因原样返回）；tests 多处直接调用
- 分支表（穷尽）：
  1. `extract_plan_json(content)` 为 None → 返回 `json_syntax_feedback(content, "澄清发射不可解析——只输出一个 JSON")`
  2. `payload.get("action")` 不在 `CLARIFY_ACTIONS` → 返回 `f"action 缺失或越界（{sorted 四值斜杠连}）：{action!r}"`
  3. `kind == "discover"`：
     3a. `payload.get("discovers")` 非 list 或空 → 返回 `"action=discover 缺 discovers（非空数组）"`
     3b. 支数 > `max_discovers` → 返回 `f"discovers 超出单次上限（≤{max_discovers} 支）"`
     3c. `discover_budget_left is not None` 且支数 > 剩余 → 返回 `f"{BUDGET_REJECT_MARK}已尽（全 run ≤10，剩余 {discover_budget_left} 支）——台账全量已在上下文，禁止继续敲门：产出 decompose 问题组或 ask 反问"`
     3d. 支非 dict 或缺 `"tool"` 键 → 返回 `"discovers 支缺 tool（{'tool': 名, 'args': {...}}）"`
     3e. 全过 → 逐支归一为 `{"tool": str(raw["tool"]), "args": dict(raw.get("args") or {})}` → `replace(emission, discovers=tuple(items))`
  4. `kind == "decompose"`：
     4a. `_question_group_of(payload.get("question_group"), max_subtasks=max_subtasks)` 返回 str → 原样返回该 str
     4b. 返回 QuestionGroup → `replace(emission, group=group)`
  5. `kind == "finalize"` → 原样返回 `emission`（L274，定稿直答无载荷；thought/note 基形已携）
  6. 其余（即 `"ask"`）：
     6a. `payload.get("ask")` 非 dict → 返回 `"action=ask 缺 ask 对象（{'prompt': …, 'options': […]}）"`
     6b. `prompt = str(raw_ask.get("prompt") or "").strip()` 为空 → 返回 `"ask 缺 prompt（问用户什么必填）"`
     6c. options 归一：`raw_options` 是 list 则 `[str(item).strip() for item in raw_options if str(item).strip()]`（元素逐项 str 归一、空白项静默丢弃），否则空列表；个数不在 2..4 → 返回 `"ask 缺 options 或个数越界（2~4 个选项）"`
     6d. 全过 → `replace(emission, ask_prompt=prompt, ask_options=tuple(options))`
- 副作用：无（不发事件、不写 store、不调模型——L3-L4 声明的「零 LLM 纯校验」；拒因仅回传，落档由 graph 侧做：graph L2447-L2460 落 STEP_DECISION「澄清 r{rnd} 被拒」）
- 返回：`ClarifyEmission`（合法发射）或 `str`（拒因正文，含预算拒因；回喂 LLM 重发射、无 repair）
- 规则条目：
  - R-L1a-28 提取失败 → 走 json_syntax_feedback 拼拒因（fallback 固定为「澄清发射不可解析——只输出一个 JSON」）
  - R-L1a-29 action 越界／缺失 → 一次拒因即回（不做任何动作分支）；`thought`／`note` 经 `str(payload.get(...) or "")` 归一入 emission（本行早于动作分派，四动作通吃）
  - R-L1a-30 kind=discover 且 discovers 不是非空数组 → 拒
  - R-L1a-31 kind=discover 且单次支数超 `max_discovers` → 拒（graph 传 `int(state.budget.get("max_discovers_per_round", MAX_DISCOVERS_PER_ROUND_CONTRACT))`，兜底常量 budget.py L29=2）
  - R-L1a-32 kind=discover 且 `discover_budget_left` 非 None 且支数超剩余 → 拒因以 `BUDGET_REJECT_MARK`（"发现预算"）开头 → graph L2445 以 `startswith` 识别为「预算免轮」拒（首次不计轮、连续第 2 次起占轮：graph L2446-L2453 streak 公式）
  - R-L1a-33 kind=discover 且支非 dict 或缺 tool 键 → 拒；tool 值不做闭世界校验（任意名 str 化通过）
  - R-L1a-34 kind=discover 通过 → discovers 逐支 `{tool, args}` 归一（args 缺省或假值→空 dict）
  - R-L1a-35 kind=decompose 且 `_question_group_of` 拒 → 该拒因原文上抛（不二次包装）
  - R-L1a-36 kind=decompose 通过 → group 装入 emission 返回
  - R-L1a-37 kind=finalize → 不读任何载荷直接返回（`sufficiency` 判定在模型侧；代码零干预——L45-L47 声明）
  - R-L1a-38 kind=ask 且 ask 非对象 → 拒
  - R-L1a-39 kind=ask 且 prompt 归一后空 → 拒（拒前已算出 options，但 prompt 判据先出）
  - R-L1a-40 kind=ask 且 options 过滤空白后个数不在 2..4 → 拒（去重不做：重复选项照样过）
  - R-L1a-41 kind=ask 通过 → prompt／options（tuple）装入 emission 返回
- 耦合：`extract_plan_json`（L238）、`json_syntax_feedback`（L240）、`CLARIFY_ACTIONS`（L242）、`ClarifyEmission`（L246）、`replace`（dataclasses.replace，L267/L272/L290）、`BUDGET_REJECT_MARK`（L259）、`_question_group_of`（L269）、`MAX_SUBTASKS_CONTRACT`（L231 默认值）
- 疑点（只列不判，不静默）：
  - D-L1a-09 `action = payload.get("action")`（L241）未经 str 归一即入 `action not in CLARIFY_ACTIONS`（L242）——action 为对象／数组等不可哈希值时抛 `TypeError: unhashable type`，不经拒因通道返回 str（对比 L247 `kind=str(action)` 才归一；同形写法见 graph.py L589-L590 parse_decision）
  - D-L1a-10 discover 支 tool 名不做闭世界校验（与链-工具对表 `_CHAIN_TOOL.values()` 零对账——L262-L266 任何字符串入 items）；args 不做形状校验且 `dict(raw.get("args") or {})` 在 args 为非空非映射值（字符串／数字／列表）时抛 `ValueError`／`TypeError` 而非返回拒因
  - D-L1a-11 ask options 归一：非 list（缺失／None／标量）→ 空列表（随后被 2..4 闸拒，拒因文案只说「缺 options 或个数越界」，不区分「类型错」与「个数错」）；元素经 `str()` 且纯空白项静默丢弃；重复选项不去重不拒
  - D-L1a-12 默认 `max_discovers=2`（L229）与 budget.py L29 `MAX_DISCOVERS_PER_ROUND_CONTRACT = 2` 两处同值不同源；生产唯一调用点（graph.py L2426-L2434）显式传参，默认值只在测试调用面生效（如 tests/domains/test_v2_four_phase.py L183 起零传参调用）
  - D-L1a-13 `discover_budget_left=None`（默认）＝预算闸关闭态；graph 侧恒传 `MAX_DISCOVERS_PER_RUN_CONTRACT - int(state.discover_used)`（budget.py L34=10），关闭态仅在测试面出现（事实：L257 判据为 `is not None`）
  - D-L1a-14 `payload` 无键白名单：未知键静默忽略（四动作分支各自只取自己需要的键）；`kind` 由 `str(action)` 生成，闭世界已在上游 L242 卡死，但 dataclass 本身（L153）无值域约束
  - D-L1a-15 拒因全为中文自然语言 str，唯一被机读的只有 `BUDGET_REJECT_MARK` 前缀（graph L2445）；其余拒因（含 ask／decompose 各类）全靠文本原样回喂，无类型化错误码（本段只列事实）

---

## 覆盖自检

- def/class 清单差集：无。L1-L296 内的 7 个符号（extract_plan_json／json_syntax_feedback／Subtask／QuestionGroup／ClarifyEmission／_question_group_of／parse_question_group）全部逐一成节；差集为空。段界外符号（SubtaskMatch L296-L315、parse_tool_match L318-L379、repair_inner_quotes L381-L428）已在清单中明示为下段，未展开
- 本段常量清单（逐名与值）：
  - `MAX_SUBTASKS_CONTRACT = 4`（L30）
  - `CHAIN_DATA = "data"`（L33）
  - `CHAIN_KNOWLEDGE = "knowledge"`（L34）
  - `CHAIN_KINDS = frozenset({"data", "knowledge"})`（L35）
  - `TOOL_DATA_QUERY = "data_query"`（L38）
  - `TOOL_DOC_RETRIEVE = "doc_retrieve"`（L39）
  - `_CHAIN_TOOL = {"data": "data_query", "knowledge": "doc_retrieve"}`（L40-L43）
  - `CLARIFY_DISCOVER = "discover"`（L48）
  - `CLARIFY_DECOMPOSE = "decompose"`（L49）
  - `CLARIFY_ASK = "ask"`（L50）——本段定义、段内零直接引用（frozenset 内联用常量）；graph.py 也未 import 该名
  - `CLARIFY_FINALIZE = "finalize"`（L51）
  - `CLARIFY_ACTIONS = frozenset({"discover", "decompose", "ask", "finalize"})`（L52-L54）
  - `BUDGET_REJECT_MARK = "发现预算"`（L58）
  - 常量外部消费面：`MAX_SUBTASKS_CONTRACT`（graph.py L126 import／L2335 填合同模板 `{max_subtasks}`；appv2/runtime/__init__.py L140 再导出；tests/domains/test_v2_four_phase.py L45）、`CLARIFY_DISCOVER`／`CLARIFY_DECOMPOSE`／`CLARIFY_FINALIZE`（graph.py L123-L125）、`BUDGET_REJECT_MARK`（graph.py L122、唯一读取点 L2445）、`Subtask`／`QuestionGroup`（graph.py L127-L128、runtime/__init__.py）
- 引用的外部符号全集（本文件内定义的除外）：
  - `json.loads`、`json.JSONDecodeError`（L74-L77、L100-L101）
  - `dataclasses.dataclass`、`dataclasses.replace`（L24、L267／L272／L290）
  - `typing.Any`（L25）
  - 另：本段内经函数调用引用到的同文件段外符号 `parse_tool_match`／`SubtaskMatch`／`repair_inner_quotes` 不计入本节（本段正文零引用；仅耦合节以消费方角度点名）
  - 反向面（外部引用本段，实证清单）：appv2/runtime/graph.py L121-L133 import 12 个名（BUDGET_REJECT_MARK／CLARIFY_DECOMPOSE／CLARIFY_DISCOVER／CLARIFY_FINALIZE／MAX_SUBTASKS_CONTRACT／QuestionGroup／Subtask／extract_plan_json／json_syntax_feedback／parse_question_group／parse_tool_match／repair_inner_quotes）；appv2/runtime/__init__.py L140-L146 与 __all__ L178-L233 再导出；tests/domains/test_v2_four_phase.py（L179-L246 schema 单测、L446-L460 零 LLM 闭包扫描种子——本文件在种子集 L460）、tests/domains/test_v2_v257_rejection_locus.py（L208-L213 源码计数钉）、tests/domains/test_v2_v260_quote_rule.py（L12 import、L19-L56 引号自修面）、tests/domains/test_v2_p039_contract_and_name_gate.py（L145-L154）、tests/domains/test_v2_v252_five_station.py（L42）、tests/domains/test_v2_v256_shallow_probe_gate.py（L39）
  - 契约／提示面耦合（同源重复，非 import）：appv2/runtime/guide.py L54-L59（decompose 合同样板与 ledger_notes 必带纪律）、appv2/runtime/orientation.py L224-L230（分解样例五键齐全）、appv2/runtime/state.py L160-L162（question_group 字段声明）、appv2/runtime/blackbox.py L28／L57（键名白名单）
