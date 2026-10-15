# V2 解析与发射（parsing）

状态: 草稿
来源: `specs/modules.md` `## parsing` 卡、`docs/runtime-refactor/eng/00-阶段2-模块划分草案.md` §三 B、`docs/runtime-refactor/walk/判断归责表.md`、`docs/runtime-refactor/walk/04-理解-读题步.md`、`docs/runtime-refactor/walk/05-理解-定路由.md`、`docs/runtime-refactor/walk/09-澄清-分解问题.md`、`docs/runtime-refactor/walk/11-匹配-工具阀.md`、`docs/runtime-refactor/walk/裁决表.md`（§04／§07／§11＋项目级裁决 #12/#13）、`docs/runtime-refactor/recon/A1-头部常量与解析校验.md`、`docs/runtime-refactor/recon/L1a-子任务前半.md`、`docs/runtime-refactor/recon/L1b-子任务后半.md`、`docs/runtime-refactor/recon/C-理解与legacy决策节点.md`、`docs/runtime-refactor/recon/E1-澄清节点.md`、`docs/runtime-refactor/recon/E2-工具匹配节点.md`、`docs/runtime-refactor/recon/I2b-RunState全字段.md`、`docs/runtime-refactor/arch/P4b-票堆V2-56至65.md`（V2-56／57／60）、`docs/runtime-refactor/arch/P6a-票堆V2-80系列前半.md`、`docs/runtime-refactor/arch/P6b-票堆V2-80系列后半.md`（A-P6b-05／24／34）、`docs/runtime-refactor/synth/S1-重写单元与证据交叉矩阵.md`（H4／H11）、`docs/runtime-refactor/synth/S4-调用图.md`、`docs/runtime-refactor/eng/04a-应钉行为清单.md`、`specs/understanding.md`、`specs/clarification.md`、`specs/tool_matching.md`、`specs/answering.md`、`specs/state.md`、`specs/execution.md`、`specs/agent-loop.md`、`appv2/runtime/subtask.py`
版式: `docs/spec-format.md`（节标题按该文 §二之二 逐字命名） ｜ 工序: `docs/spec-process.md`
块性: 本块＝**纯结构判定块**（真源 `docs/runtime-refactor/walk/判断归责表.md`）——解析拒收（缺字段／超限／引号异常／闭世界对账）＝结构判可做；语义判断（语义词表判「提及 vs 执行」／要不要问／覆盖没覆盖）一律不落本块。

## 目标

把模型应答的外部文本变成**定型载荷**——理解／澄清／工具匹配三面应答的解析、发射 schema 结构校验、子任务与问题组载荷定型；**纯结构判定，零语义判断**（外部文本 → 定型载荷＝卡面 Seam）。

## 不做什么

| 不做 | 由谁承担 | 锚点 |
|---|---|---|
| 语义词表判（「提及 vs 执行」的判断） | 模型侧产出（`tool_matching` 发射面）；结论分派归 `preconditions` 判定序第 1 位 | `docs/runtime-refactor/walk/裁决表.md` #12 |
| 「能不能锚定窗／要不要问／覆盖没覆盖」的语义判断 | 模型侧产出；程序只按结论分派 | `docs/runtime-refactor/walk/裁决表.md` #13；`specs/clarification.md` 行为 9 |
| 直答结构核验（`route="direct"` 的数值／名录／结构卡闭世界判） | `understanding` | `specs/understanding.md` 行为 5 |
| 模型调用、限流退避、记账 | `gateway_adapter`（本块**零模型调用**，连该出口都不 import） | `specs/modules.md` `## gateway_adapter` |
| 拒因回喂、轮次记账、预算免轮 streak、步记录 | 调用方相位＋`bookkeeping`（唯一写口）／`orchestration`（轮与路由） | `specs/modules.md` `## bookkeeping`；`docs/runtime-refactor/recon/E1-澄清节点.md` R-E1-12 |
| 引号自修受理 notice 的发射与状态写入 | 调用方（事件面归 `transport`） | `docs/runtime-refactor/recon/A1-头部常量与解析校验.md` R-A1-14 |
| plan 深形字段白名单与其余必填键（`ranking` 等） | 工具层 args_schema（`bad_args` 同路回喂——两道闸一个去处） | `docs/runtime-refactor/recon/A1-头部常量与解析校验.md` R-A1-36 |
| 台账投影取得与注入块渲染（`ledger_notes` 逐字求得面） | `context`／`prompts` | `specs/clarification.md` 行为 8 |
| 起草应答的发射剥离（`strip_emission_fences`）与回声／粘贴观测 | `answering`（答案面归属） | `specs/answering.md` 行为 11／行为 14 |
| 提示词合同常量与各轮指令装配 | `prompts` | `specs/modules.md` `## prompts` |
| 工具执行与观察回流 | `execution` | `specs/modules.md` `## execution` |
| 同参重投闸的**触发与拦截／回喂** | 消费方（触发面归属登记件——见风险 4）＋`state`（指纹簿记字段） | `specs/tool_matching.md` 风险 4；`specs/execution.md` 行为 13 |
| legacy 决策发射解析（`parse_decision` 四动作＋repair 桶） | **不做**——随 legacy 决策节点整体废弃（决策语义并入澄清相位） | `docs/runtime-refactor/synth/S4-调用图.md`（结构-1） |

## 触及的模块

| 模块 | 改动类型 | 说明 |
|---|---|---|
| parsing | 新增 | 本块本体：三面解析器族＋共用件族＋载荷定型类＋指纹器材（纯文本进出） |
| state | 已定稿 | 唯一模块依赖（R3）：限额单点常量（解析默认上限）＋指纹簿记字段的形状面；只消费、零写入 |

## 接口定义

```python
# ── 卡面两函数（逐字照录——真源 specs/modules.md `## parsing` 卡；参数名以卡为准）──
def parse_understanding(text: str) -> Understanding | Direct | None: ...
def parse_question_group(text: str) -> QuestionGroup | None: ...
# 注：卡面为阶段 2 初拟形；本块 V2 定案的返回形与 V1 现行签名见「行为约定」2／7——
#     两者差异＝卡级登记件（风险 7①，本规格不改卡，单写者纪律）。

# ── 族内其余成员（卡面职责「模型输出解析、发射 schema 校验、子任务与问题组载荷定型」
#    的展开，名单闭世界；逐成员带真源锚）──────────────────────────────────
# ① 发射面解析器：
#   parse_tool_match(content, group) -> tuple[SubtaskMatch, ...] | str
#       # 工具匹配发射解析＋闭合世界对账（matches ↔ 问题组一一对应）
#       # 真源 docs/runtime-refactor/recon/L1b-子任务后半.md R-L1b-05…R-L1b-21；
#       # 消费方 tool_matching（其规格「不做什么」行：模型输出的解析与 schema 校验→parsing）
# ② 共用件（三解析入口共用，单点）：
#   extract_plan_json(content) -> dict | None        # 首个花括号平衡块提取单点（R-L1a-01…R-L1a-05）
#   json_syntax_feedback(content, fallback) -> str   # 拒因带定位拼装（arch/P4b A-P4b-10/11/12）
#   repair_inner_quotes(text) -> str | None          # 确定性引号自修（arch/P4b A-P4b-37/38；V2-60 ③层）
# ③ 载荷定型类（子任务与问题组载荷——字段表＝「行为约定」11）：
#   Subtask／QuestionGroup／SubtaskMatch（＋V1 发射定形 ClarifyEmission）
#       # 真源 docs/runtime-refactor/recon/L1a-子任务前半.md 与同报告 L1b（字段与投影逐条）
# ④ 「同参重投闸」的指纹器材（闸件本体指纹面归本块——真源 specs/tool_matching.md
#    「不做什么」行＋风险 4；synth/S1 把 V2-37（指纹面）归 H4）：
#   payload_fingerprint(payload) -> str              # 键序归一紧凑 JSON（R-A1-24）
#   discover_fingerprint(tool_name, args) -> str     # 空手探查指纹（R-A1-25）
#   emission_fingerprints(plan, retrieval_need) -> tuple[str, ...]   # 按支拆算（R-A1-26）
#   is_same_param_replay(fingerprints, executed) -> bool             # 同参判定（R-A1-27/28）
# ⑤ 理解面（签名＝卡面两函数之第一式逐字；V2 定案＝统一 JSON 严格解析，见行为 1）：
#   合格 → Understanding｜Direct；不合格 → None（唯一转译出口＝调用方 understanding 抛
#   UnderstandingParseError——真源 specs/understanding.md 行为 7）
```

- **族名单是闭世界**：上列成员之外新增公开成员＝只许以「新增成员入名单＋同批对账消费方规格」方式进块；消费方在相位块内私建解析副本（自写提取循环／引号扫描／schema 校验）＝判失败。
- **返回三态闭世界（全体解析成员统一口径）**：①**定型载荷**（合格）；②**拒因正文**（`str`——发射面不合格的回喂形；机器拒因原文）；③**`None`**（不合格的无回喂形——理解面不合格／提取与自修的无病或失败形）。**越界行为**：任何不在这三态内的返回形态（半成品载荷、部分字段、哨兵值、裸抛业务异常）＝判失败。
- **错误契约**：本块不抛业务异常、不吞错——不合格一律走三态返回；**异常出口唯一**＝`understanding` 对 `None` 转 `UnderstandingParseError`（真源 `specs/understanding.md` 错误契约）。
- **入参纪律**：纯文本进出（外部文本 → 定型载荷）＋调用方注入的限额参数（`max_discovers`／`discover_budget_left`／`max_subtasks`）——**上限数值取自 `state` 限额单点**（行为 16），本块源码不写裸值。
- 真源：`specs/modules.md` `## parsing` 卡（卡面两函数签名以卡为准；卡面与 V2 定案差异见风险 7①）。

> **V2 定案差异点（对 V1 显式声明——迁移照抄之外的改动全在此列，供逐字比对）**：①**理解面＝统一 JSON 严格解析**（两行式「理解：／指标候选：」、冒号回退、降级子串提取、`parse_direct_reply` 全部退场——Owner 直令，真源 `docs/runtime-refactor/walk/裁决表.md` §04-B）；②**本块不裸抛业务异常**（V1 两处裸抛收口为三态返回——`args` 非对象＝拒，对齐同族 R-A1-31 口径；`action` 不可哈希形＝拒；登记件，风险 7⑦）；③解析默认上限**取自 `state` 限额单点**（迁移对账件，风险 7⑤）；④预算拒因文本内嵌数值**保留 V1 字面**（「迁移照抄」与「数字单点插值」两解**待裁**——风险 7②）；⑤`parse_decision` 随 legacy 节点退场、不在本块名单（见「不做什么」）。

## 框架与依赖红线

- **无点名框架**（纯解析零框架依赖；只用标准库 `json`／`dataclasses`）。验收写法：依赖锁文件不出现框架包＋行为测试绿。对应闸：**R5b 契约**。
- **只许 import `state`**（纯解析块）：本块不感知运行状态机、不引任何其他 runtimev2 块、不直引 `appv2.runtime.*`（旧码；该面承 **R5** 契约全包覆盖）。对应闸：**R3 契约**——**诚实声明覆盖面**：R3 的 forbidden 只列七个业务相位（`tools/importlinter_v2.toml` 亲读属实），**「禁引公共层其余块」（bookkeeping／context／transport／persistence／gateway_adapter／orchestration／gate）这半面无闸**；降维＝AST import 扫描测试（`::imports_state_only`），余面人审（见挂钩表）。
- **消费方向（R2）**：consume 本块的三个业务相位只许经包根 `appv2.runtimev2.parsing`（深层子模块私有）。对应闸：**R2 契约**（forbidden 含 `appv2.runtimev2.parsing.*`）。
- **不引引擎**（knowledge/query/retrieval）＝**R6 契约**；**不直引 `appv2.infra.llm_client`**＝**R7 契约**。**零模型调用**——本块连 `gateway_adapter` 都不 import（纯解析块）；该面由 `::parsing_pure_deterministic`（AST）承载，R1–R8 无此专属闸（R8 只列三个零 LLM 相位）。
- **禁手写替代（解析单点）**：提取件／拒因带定位件／引号自修件在 runtimev2 面内各恰一处定义，禁在相位块另存副本（V1 病灶：`extract_plan_json` 曾自 `appv2/runtime/graph.py` 迁入 `appv2/runtime/subtask.py` 并以 re-export 保留旧名——真源 `docs/runtime-refactor/recon/L1a-子任务前半.md` 段头声明）。验收写法：runtimev2 面内唯一定义点断言（`::shared_helpers_single_source`）。

## 行为约定

1. **理解面＝统一 JSON 严格解析（V2 定案，Owner 直令）**：合格 → `Understanding`（`route="full"`）｜`Direct`（`route="direct"`）两形互斥；`route` 越界／缺必填字段／类型不符 → `None`（本块不合格信号——**不猜、不取默认、不做降级提取**）；两行式形（行首「理解：／指标候选：」）与「直接回答：」行通道（`parse_direct_reply`）**不再受理**。断言：合法 JSON 两形落对；缺 `route`／越界 `route`／缺 `text` → `None`；两行式样本 → `None`（不落降级提取，旧降级通道零可达）（真源 `docs/runtime-refactor/walk/裁决表.md` §04-B；`specs/understanding.md` 行为 7）。
2. **澄清面＝四动作闭世界＋分派**：`action` 合法值闭世界恰四——`discover`｜`decompose`｜`ask`｜`finalize`（V1 字面 `CLARIFY_ACTIONS`，载体 `appv2/runtime/subtask.py` L48-L54）；越界或缺失 → 拒因正文（回喂）；四支各自校验见行为 3–5；`thought`／`note` 经字符串归一随定形携带（四动作通吃）；**payload 无键白名单**——动作之外的未知键静默忽略（V1 事实面，登记件风险 7①同族）。断言：四动作各示例落对；`action` 越界／缺失 → 拒因正文；未知键不影响受理（如实记录）。
3. **问题组载荷校验（`decompose` 支）**：`question_group` 须对象；`subtasks` 须非空数组；支条数超上限 → 拒（上限取 `state` 限额单点）；逐支按序过闸：支须对象／`id` 归一后非空且组内唯一／`question` 归一后非空／`ledger_notes` 归一后非空（台账注释必带——本块是其唯一机检点）／`chain` 非空时 ∈ 闭世界 `data`｜`knowledge`／`tool` 非空时 ∈ 闭世界 `data_query`｜`doc_retrieve`；三键经「去空白归一」判空与落值同源；支内未知键静默丢弃（V1 事实）。**本层不做**链-工具一致性／链-载荷配套校验（归行为 6；真源 R-L1a-26）。断言：各违例逐条落拒因原文（比对件见行为 7）；支条数边界（上限／上限加一）落对（真源 `docs/runtime-refactor/recon/L1a-子任务前半.md` R-L1a-16…R-L1a-27）。
4. **发现支校验＋预算闸**：`discovers` 须非空数组；支数超单次上限 → 拒；`discover_budget_left` 非 None 且支数超剩余 → **预算拒**——拒文以机读前缀「发现预算」（V1 字面 `BUDGET_REJECT_MARK`，载体 L58）开头；支须对象且含 `tool`（`tool` 值本层不做闭世界校验——V1 事实面）；通过 → 逐支归一为 `{"tool": …, "args": …}` 形（`args` 缺省／假值归一空对象；**`args` 非对象＝拒**——V2 定案差异点②）。断言：四型拒各自落对；预算拒以「发现预算」开头（机读前缀恰一值）；支数＝剩余放行、剩余加一拒（真源 `docs/runtime-refactor/recon/L1a-子任务前半.md` R-L1a-30…R-L1a-34）。
5. **`ask` 支校验**：`ask` 须对象；`prompt` 归一后非空；`options` 逐项字符串化去空白、空白项丢弃（不去重）；个数不在「2~4」→ 拒——拒文逐字「ask 缺 options 或个数越界（2~4 个选项）」（载体 `appv2/runtime/subtask.py` L288-L289）。断言：`prompt` 空／`ask` 缺失／个数越界（低于下限／高于上限）→ 拒；重复选项照样过（V1 事实面）（真源 `docs/runtime-refactor/recon/L1a-子任务前半.md` R-L1a-38…R-L1a-41）。
6. **工具匹配面＝闭合世界对账（恰一一对应）**：`matches` 须非空数组；逐支按序 fail-fast：支须对象／`id` 归一后非空／`id` 须在问题组 id 集内（不在＝拒且拒文列组 id 全量）／`id` 组内不重复／`chain` 归一后 ∈ `data`｜`knowledge`／`tool` 非空且＝该链唯一工具（`data`→`data_query`、`knowledge`→`doc_retrieve`）／`data` 链 `plan` 须对象且 `metric_slot` 非空／`knowledge` 链 `retrieval_need` 须对象且 `question` 非空／`caliber_key` 零校验装载（非空串原样，合法口径三态在下游前置条件机）；组内存在未见 `id` → 覆盖缺口拒（拒文列缺失 id 全量）。**plan／retrieval_need 深形白名单不在本层**（R-A1-36；D-L1b-03 事实面）。返回顺序＝发射顺序（不回排组序）。断言：全配 → tuple；缺／多／未知／重复 id 各拒；chain／tool 不一致拒；按链必填各拒（真源 `docs/runtime-refactor/recon/L1b-子任务后半.md` R-L1b-05…R-L1b-21）。
7. **拒因正文＝机器拒因原文（迁移照抄，零改动）**：全部分支的拒因文本**逐字迁移、承载位换文本不变**（真源 `docs/runtime-refactor/arch/P6b-票堆V2-80系列后半.md` A-P6b-05「机器拒因原文零改动」＋A-P6b-24／A-P6b-34）；**逐字稿载体＝迁移前现行代码 `appv2/runtime/subtask.py`（L179-L290 澄清面／L318-L375 匹配面）**，条目真源＝`docs/runtime-refactor/recon/L1a-子任务前半.md` R-L1a-16…R-L1a-41 与 `docs/runtime-refactor/recon/L1b-子任务后半.md` R-L1b-05…R-L1b-21（**要点形，不作逐字稿**）；施工以迁移前代码字面为逐字稿照抄，偏离即停。机读甄别面恰一值：前缀「发现预算」（载体 L58）。断言：各拒因分支返回文本与迁移前快照逐字相等（golden 比对件）；预算拒前缀在场（真源 `docs/runtime-refactor/recon/L1a-子任务前半.md` R-L1a-28／R-L1a-32）。
8. **拒因带定位（V2-57）**：提取失败 → 拒因经带定位件拼装——无左花括号形含逐字提示「输出中没有任何以左花括号起始的 JSON 对象（检查是否漏了 JSON 外壳、只输出了围栏或解释文字）」（载体 `appv2/runtime/subtask.py` L88-L89）；语法坏点形含异常消息＋绝对坏点字符序（「（约第 {bad} 字符）」形）＋坏点前后窗原文（窗宽真源＝R-L1a-07）＋逐字修复指令「只修正语法错误，结构与其余内容照旧，重新输出一个 JSON。」（载体 L104-L108）；**括号始终不平衡形退裸 fallback（零定位）**——V1 事实面（D-L1a-03）；「括号失衡也给定位」需另裁，本块不自行裁量。断言：三形样本各落对；坏点窗与字符序在场；截断形退 fallback（真源 `docs/runtime-refactor/arch/P4b-票堆V2-56至65.md` A-P4b-10／A-P4b-11）。
9. **提取单点＝首个花括号平衡块**：只读首块、首块坏即 `None`（不续扫后续块——V1 事实面 D-L1a-01）；深度归零处切片交 JSON 解析；成功且顶层为对象 → 返回该对象；无左花括号／括号未平衡／顶层非对象 → `None`。两发射面共用同一件（单点）。断言：多块文本只取首块；首块坏＋次块好 → `None`；顶层数组 → `None`（真源 `docs/runtime-refactor/recon/L1a-子任务前半.md` R-L1a-01…R-L1a-05）。
10. **引号自修＝确定性纯字符处理（V2-60 ③层）**：逐字符在串／不在串态扫描；串内反斜杠连带后一字符原样带过（转义序列不误伤）；串内遇 `"` 且其后（跳空白）首字符 ∉ `,` `}` `]` `:` 结构集 → 认定值内裸引号，替换为「／」（该串内按出现次序开闭交替）、串态保持；∈ 结构集 → 结构引号原样；扫描后与原文相同（无病不修）→ `None`；有替换且**全文** JSON 可解析 → 返回修复文本；仍失败 → `None`（两形 `None` 不可区分——V1 事实面 D-L1b-11）。零模型零语义；受理 notice 由调用方发、归其事件面（本块零事件）。断言：四形单测（合法转义原样／值内引号修复受理／无病不修 `None`／修后仍失败 `None`）＋修后全文可解析（真源 `docs/runtime-refactor/arch/P4b-票堆V2-56至65.md` A-P4b-37／A-P4b-38）。
11. **载荷定型类＝V1 字段表逐字迁移**：`Subtask{id, question, ledger_notes, chain="", tool=""}`／`QuestionGroup{subtasks: 元组}`／`SubtaskMatch{id, chain, tool, plan=None, retrieval_need=None, caliber_key=""}`（＋V1 发射定形 `ClarifyEmission{kind, group=None, discovers=(), ask_prompt="", ask_options=(), thought="", note=""}`）；全 `frozen=True, slots=True`（载体 `appv2/runtime/subtask.py` L116-L176／L296-L315）。投影规则（`as_payload`）逐字：Subtask 恒带三键、`chain`／`tool` 真值才出键；QuestionGroup 恒单键形（`subtasks` 数组）；SubtaskMatch 恒 id／chain／tool＋`plan`／`retrieval_need` 非 None 才出键＋`caliber_key` 真值才出；ClarifyEmission 恒 `action`＋thought／note 真值才出＋group 非 None 才出＋discovers 非空才出＋**`ask` 段以 `ask_prompt` 真假单点开闸**（`ask_options` 单有值静默消失——V1 事实面 D-L1a-04）。断言：字段集逐类对照迁移前字段表；空值键不出现；`ask` 段开闸单点（真源 `docs/runtime-refactor/recon/L1a-子任务前半.md` R-L1a-09…R-L1a-15；`docs/runtime-refactor/recon/L1b-子任务后半.md` R-L1b-01…R-L1b-04）。
12. **理解面两载荷形状不重定义**：`Understanding`／`Direct` 的字段集以 `specs/understanding.md` 接口定义为**消费面视图**（`text`／`metric_candidates`／`route`）；本块产出实例形状与之相等（同物一套形状，禁第二套含义）；**物理定义点＝本块**——依据＝卡面签名已在本块引用两类型＋R3 禁本块引 `understanding` 的组合推论（登记件，风险 7③）。断言：本块产出实例字段集与 `understanding` 规格所列集合相等；本块无第二处两类型形状定义（AST／集合比较）。
13. **指纹器材（同参重投闸指纹面）**：载荷规范指纹＝键序归一（排序键）＋紧凑分隔符＋不转义非 ASCII 的 JSON 串（R-A1-24）；发现调用指纹＝`{"tool": 名, "args": 参}` 键序归一 JSON（R-A1-25；与前者归一规范不同——V1 事实面 D-A1-13，两规范各自保留、不跨面比较）；按支拆算＝单支单形（`plan` 支在前；两皆空 → 空元组；两支皆在 → 两值——R-A1-26）；同参判定＝空元组 → 放行；全部支都在实录 → 拦；任一支为新参 → 放行（R-A1-27／R-A1-28）。**触发点与拦截／回喂归消费方**（本块只产纯函数器材——真源 `specs/tool_matching.md` 风险 4；`specs/agent-loop.md` 行为 3）。断言：指纹两跑同串（确定性）；两支形与单支形不等（整形与实录对齐面）；同参判定三支落对。
14. **纯结构判定**：本块全部判定＝存在性／类型／闭世界成员／计数／字符串归一／字符扫描——**零词表零正则语义判定**；豁免面＝形态处理（闭世界成员判定、逐字子串校、数字／ASCII 形判定——先例 `specs/tool_matching.md` 行为 4）。断言：`::no_lexicon_or_regex_in_parsing` 绿＋判定清单逐条可指真源条目（真源 `docs/runtime-refactor/walk/判断归责表.md`）。
15. **确定性纯函数**：同入参两次调用输出逐字相等；零 IO、零模型调用、零时钟、零随机、零事件发射、零状态写入（唯一 `state` 接触＝限额常量与指纹簿记字段的形状）。断言：两跑逐字相等＋AST 扫描零命中。
16. **数字与上限单点**：解析默认上限（`max_discovers`／`max_subtasks` 缺省）**取自 `state` 限额单点**（真源 `specs/state.md` 行为 10——数值不落本规格）；V1 缺省裸字面（D-L1a-12 病灶）与合同常量的定义点随迁移对账（风险 7⑤）；预算拒因文本内嵌数值（行为 4）是否插槽化＝**待裁**（风险 7②）。断言：默认参数取值＝`state` 常量（签名／AST 断言）；本块源码无裸上限字面（扫描）。
17. **同类条目多次出现不静默覆盖**：重复 `id`（问题组支／匹配支）逐条拒（拒因原文逐字，载体 L199／L339）；**JSON 重复键**形（同键出现多次、解析后取后者）＝真源未裁落点（卡面测试计划「同类行多次出现不静默覆盖」的 V2 对应面）——登记疑点（风险 7⑥），本块不自行加严。断言：重复 `id` 各面拒因在场；JSON 重复键样本行为＝如实记录（待裁）。
18. **共用件单点、消费方零副本**：三解析入口的提取件／拒因带定位件／引号自修件在 runtimev2 面内各恰一处定义；相位块内出现同形字面副本（提取循环／引号扫描）＝判失败。断言：`::shared_helpers_single_source`（各件特征子串在 `understanding`／`clarification`／`tool_matching` 块源码零命中）。

## 不降级与静默禁令

- **合法降级路径：无**——解析不降级：不合格＝三态返回（拒因正文／`None`），**不半成品、不静默丢字段、不改写模型原文**；固定 fallback 话只作拒因前缀（回喂面）而非交付面替代。
- **机读信号（本块承诺面两处）**：①拒因正文恒非空（无空返回——所有拒分支返回 `str`）；②预算拒前缀「发现预算」在场。**事件面信号**（`emission_quote_repair` 等 notice）＝调用方义务，本块零事件（不冒充覆盖）。
- **本块零截断**：不改写／截断拒因与载荷内容；拒因带定位的坏点前后窗＝V2-57 设计内明文摘录（非静默截断——真源 `docs/runtime-refactor/arch/P4b-票堆V2-56至65.md` A-P4b-10）。
- 卡面测试计划四项映射：缺字段／超限＝行为 3–6；引号异常分支＝行为 8／10；同类条目多次出现不静默覆盖＝行为 17。
- 红线原文：`docs/runtime-refactor/arch/P7a-交接包与挂账清单.md`（A-P7a-37）「**不许静默**——若任何相位仍发生截断，模型面必须随材料段带明示……收口注记面同步披露」。

## 验收测试

| 验收标准 | 对应测试 |
|---|---|
| 理解面：合法 JSON 两形（`route="full"`／`route="direct"`）落对，互斥单出口 | `tests/domains/test_v2_parsing.py::understanding_json_two_forms` |
| 理解面：缺必填字段／类型不符／`route` 越界 → `None`（不猜、不取默认、不降级） | `tests/domains/test_v2_parsing.py::understanding_malformed_none_no_fallback` |
| 理解面：两行式与「直接回答：」通道样本不再受理（旧降级提取零可达） | `tests/domains/test_v2_parsing.py::understanding_two_line_retired` |
| 澄清面：四动作闭世界各形落对 | `tests/domains/test_v2_parsing.py::clarify_actions_closed_world` |
| 澄清面：`action` 越界／缺失 → 拒因正文（原文逐字） | `tests/domains/test_v2_parsing.py::clarify_action_out_of_range_rejected` |
| 问题组：上限（取 `state` 限额单点）／支非对象／缺 `question`／`id` 重复 → 逐条拒 | `tests/domains/test_v2_parsing.py::question_group_schema_rejections` |
| 问题组：缺 `ledger_notes` → 拒（台账注释必带机检点） | `tests/domains/test_v2_parsing.py::ledger_notes_required` |
| 问题组：`chain`／`tool` 非空越界 → 拒；本层不做链-工具一致性 | `tests/domains/test_v2_parsing.py::question_group_chain_tool_closed_world` |
| 发现支：非空数组／单次上限／全 run 预算（前缀「发现预算」）／支缺 `tool`／`args` 非对象 → 逐条拒 | `tests/domains/test_v2_parsing.py::discover_shape_and_budget_rejections` |
| `ask` 支：缺 `ask` 对象／`prompt` 空／`options` 个数越界 → 拒；重复选项照样过 | `tests/domains/test_v2_parsing.py::ask_shape_rejections` |
| `finalize` 支：零载荷直通（不读载荷） | `tests/domains/test_v2_parsing.py::finalize_passthrough` |
| 匹配面：恰配一条全过 → tuple（顺序＝发射顺序）；缺／多／未知／重复 id → 逐条拒 | `tests/domains/test_v2_parsing.py::matches_exactly_one_per_subtask` |
| 匹配面：`chain` 闭世界／chain-tool 一致性／按链必填（`plan.metric_slot`／`retrieval_need.question`）→ 逐条拒 | `tests/domains/test_v2_parsing.py::matches_chain_tool_consistency` |
| 拒因原文逐字迁移（golden＝迁移前 `appv2/runtime/subtask.py` 快照逐字比对；预算前缀「发现预算」在场） | `tests/domains/test_v2_parsing.py::rejection_texts_verbatim_from_v1` |
| 拒因带定位：坏点字符序＋前后窗在场；无花括号专门提示；括号失衡形退裸 fallback | `tests/domains/test_v2_parsing.py::rejection_feedback_locus` |
| 提取单点：首平衡块／首块坏不续扫／顶层非对象 → `None` | `tests/domains/test_v2_parsing.py::extract_first_balanced_block` |
| 引号自修四形（转义不误伤／值内引号受理／无病不修／修后仍失败）＋修后全文可解析 | `tests/domains/test_v2_parsing.py::quote_repair_four_forms` |
| 载荷定型类：字段集与投影键形（`as_payload`）逐字；空值键不出现；`ask` 段开闸单点 | `tests/domains/test_v2_parsing.py::payload_types_field_tables` |
| 理解面两载荷形状与消费面视图相等；本块无第二处形状定义 | `tests/domains/test_v2_parsing.py::understanding_payload_shape_single_source` |
| 指纹器材：两跑同串（确定性）；按支拆算单支单形／两支两值 | `tests/domains/test_v2_parsing.py::fingerprints_deterministic_per_branch` |
| 同参判定三支（全在→拦／新参→放行／零支→放行） | `tests/domains/test_v2_parsing.py::same_param_replay_three_cases` |
| 共用件单点：三件特征子串在三个消费方块源码零命中（零副本） | `tests/domains/test_v2_parsing.py::shared_helpers_single_source` |
| 数字单点：默认上限取自 `state` 常量；本块源码无裸上限字面 | `tests/domains/test_v2_parsing.py::limits_from_state_constants` |
| 程序侧无词表／正则语义判断（AST；豁免面＝形态处理） | `tests/domains/test_v2_parsing.py::no_lexicon_or_regex_in_parsing` |
| 确定性纯函数：两跑逐字相等；零 IO／模型／时钟／随机／事件／状态写（AST） | `tests/domains/test_v2_parsing.py::parsing_pure_deterministic` |
| import 面只许 `state`（AST 扫描——R3 半覆盖面的降维补位） | `tests/domains/test_v2_parsing.py::imports_state_only` |
| 【边界集】缺字段／超限／引号异常／重复 `id`／括号失衡截断 → 各落拒因正文或 `None` | `tests/domains/test_v2_parsing.py::boundary_missing_overlimit_quote_duplicate` |
| 【保留集】常规三面文本解析不受边界分支影响；消费方既有 schema 断言不因迁移改形回归 | `tests/domains/test_v2_parsing.py::retention_normal_parses_unchanged` |

> **测试文件归属**：本块验收测试绑**新建** `tests/domains/test_v2_parsing.py`（`parsing` 是阶段 2 新划的公共层块，与同层 `state`／`prompts` 规格同款归属；`ls tests/domains/` 实测无同名文件，无冲突）；fixture＝**文本 fixture 集**（卡面 Adapter）。全部测试标识＝**待织网（阶段 5）**。

## 依赖与风险

- 依赖：`state`（唯一模块依赖——R3；限额单点＋指纹簿记字段形状，只读）；消费方＝`understanding`／`clarification`／`tool_matching`（经 R2 包根），指纹器材的消费对账面＝`execution`／`agent-loop`；真源＝`specs/modules.md` `## parsing` 卡。
- 风险与对策（每条带检测手段）：
  1. **卡与规格分叉（返回形＋成员展开）**：卡面 `parse_question_group` 为初拟返回形（问题组容器单件），本块按 V1 逐字迁移形（含四动作定形＋拒因）并把族成员展开成名单。**登记件**（卡级，只登记不改卡）；检测手段＝**人审**（评审工序；卡级登记见风险 7①）。
  2. **迁移照抄 vs 数字单点相抵**（预算拒因文本内嵌数值：保字面 vs 插槽化）——**待裁差异点**。检测手段＝golden 比对件＋**人审**（主窗裁定；见风险 7②）。
  3. **载荷定型类物理定义点宣告**（本块）与三份已定稿消费方规格的「消费面视图」措辞——若主窗裁定另置＝须回阶段 2 改卡／改规格。检测手段＝**人审**（阶段 7 接口契约对账；风险 7③）。
  4. **同参重投闸的触发面与拦截落点未定案**（本块只锁指纹器材纯函数面；触发点在 V2 何面、拦截与回喂归谁两面无裁决文本）。检测手段＝**人审**（与 `specs/tool_matching.md` 风险 4／`specs/execution.md` 行为 13／`specs/agent-loop.md` 行为 3 对账）。
  5. **拒因正文（`str`）与消费方结构化拒因**（`clarification` 的 `ClarifyRejection`／`tool_matching` 的 `ToolMatchRejection`）**转换点归属未定案**。检测手段＝**人审**（阶段 7 接口契约对账）。
  6. **理解面异常面分工**：本块只产 `None`、`UnderstandingParseError` 由 `understanding` 抛——两规格分工须对读一致。检测手段＝`specs/understanding.md` 行为 7／错误契约＋本规格行为 1 对读＋`::understanding_malformed_none_no_fallback`。
  7. **跨规格债与卡级登记清单（本批只登记、不代办——单写者纪律，交主窗统一回提）**：①`specs/modules.md` `## parsing` 卡：返回形勘正＋族名单承载（建议补「族名单以 parsing 规格接口定义为准（闭世界）」注记）；②预算拒因内嵌数值待裁；③载荷类物理定义点宣告（建议三消费方规格／卡对齐）；④拒因转换点归属；⑤合同常量定义点迁移（子问题条数上限等的 `state` 承载面——`specs/state.md` 行为 10 键面读数与 `docs/runtime-refactor/walk/裁决表.md` §06-A 五项均未含该上限，须落定）；⑥JSON 重复键形（卡面测试计划的「不静默覆盖」落点）；⑦V1 裸抛收口差异点（D-L1a-09／D-L1a-10）。检测手段＝**人审**（主窗回提＋阶段 7 接口契约对账）。

## 与闸的挂钩表

| 本规格的硬要求 | 挂钩 | 现状 |
|---|---|---|
| 触及模块名已声明 | spec gate | 已进 CI |
| 验收测试逐行有标识 | spec gate | 已进 CI |
| 只 import `state`（禁引七业务相位半面） | 边界闸 **R3** | 已真跑（`tools/importlinter_v2.toml` R3 契约） |
| 只 import `state`（禁引公共层其余块半面） | 测试 `::imports_state_only` ＋ **人审** | 待实现（阶段 5）；人审原因：R3 的 forbidden 只列七个业务相位，公共层半面无闸、AST 补位是测试非闸 |
| 消费方只经包根（深层子模块私有） | 边界闸 **R2**（`forbidden` 含 `appv2.runtimev2.parsing.*`） | 已真跑 |
| 不引框架 | 边界闸 **R5b** | 已真跑 |
| 不引引擎 | 边界闸 **R6** | 已真跑 |
| 不直引 `appv2.infra.llm_client` | 边界闸 **R7** | 已真跑 |
| 零模型调用（连 `gateway_adapter` 都不 import） | 测试 `::parsing_pure_deterministic`（AST 零模型面） | 待实现（阶段 5）；R1–R8 无「禁引 `gateway_adapter` 于 parsing」专属闸（R8 只列三个零 LLM 相位） |
| 拒因正文＝机器拒因原文（逐字稿载体＝迁移前代码字面） | 测试 `::rejection_texts_verbatim_from_v1` | 待实现（阶段 5） |
| 引号自修确定性（V2-60 ③层；零模型零语义） | 测试 `::quote_repair_four_forms` | 待实现（阶段 5） |
| 同参重投闸指纹面（闸件本体归本块——真源 `specs/tool_matching.md` 风险 4） | 测试 `::fingerprints_deterministic_per_branch`／`::same_param_replay_three_cases`；触发面归属＝**人审**（风险 4） | 待实现（阶段 5） |
| 共用件单点（消费方零字面副本） | 测试 `::shared_helpers_single_source` | 待实现（阶段 5） |
| 数字单点（默认上限只引 `state` 单点） | 测试 `::limits_from_state_constants` ＋ `state` 侧常量单点测试 | 待实现（阶段 5） |
| 程序不判语义（无词表／正则） | 测试 `::no_lexicon_or_regex_in_parsing` | 待实现（阶段 5） |
| 理解面不合格信号唯一转译出口（`None`→`UnderstandingParseError`） | 测试 `::understanding_malformed_none_no_fallback` ＋ **人审**（与 `specs/understanding.md` 对读，风险 6） | 待实现（阶段 5） |
| pin-04／pin-13 经逐条核实**不落本块**（防一头两认） | 钉落点对读：`pin-04`（发射 JSON 不进答案面）已落 `specs/answering.md` 行为 11＋其挂钩表；`pin-13`（起草回声=0）已落 `specs/prompts.md` 行为 13（合同侧）＋`specs/answering.md` 行为 14（观测面）——parsing 无第三面缺口 | 已核实（本批起草时逐条对读） |
| 真源引用可解析（本规格全部引用行） | 真源引用闸（`tools/ref_resolvable.py` 的 check 子命令） | 交稿前本地实跑 |
| 「不做什么」的纯范围排除（不调模型／不判语义／不回喂等） | **人审** | 接不上闸的原因：纯范围排除没有形状／存在性／退出码判据；能降维的部分（只引 `state`、零模型、零引擎）已由 R3／R6／R7＋AST 测试覆盖 |
