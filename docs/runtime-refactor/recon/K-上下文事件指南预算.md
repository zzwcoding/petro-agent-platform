# K·现状调研报告

- 锚定：commit e4b75f1（行号以此为准）——已核对：`git diff e4b75f1 HEAD --` 四文件为空，行号在锚定与当前 HEAD（085b294）一致
- 覆盖：context.py + events.py + guide.py + budget.py（全文件）
- def/class 清单（逐一全列）：

**appv2/runtime/context.py（119 行）**
| 符号 | 行号区间 |
| --- | --- |
| `TRUST_AGG` / `TRUST_LEDGER` / `TRUST_REPORT` | L19-L21 |
| `_KIND_TRUST` | L23-L34 |
| `_TRUST_RANK` | L35 |
| `DEFAULT_MAX_OBSERVATIONS` | L37 |
| `SYSTEM_PROMPT` | L39-L50 |
| `LEDGER_DICT_NOTE` | L54-L58 |
| `def trust_of` | L61-L64 |
| `def render_materials` | L72-L109 |
| `class ContextBuilder` | L113-L117 |

**appv2/runtime/events.py（107 行）**
| 符号 | 行号区间 |
| --- | --- |
| `EVENT_STEP` / `EVENT_TEXT` / `EVENT_TOOL` / `EVENT_OBSERVATION` / `EVENT_ASK` / `EVENT_VERDICT` / `EVENT_CITATION` / `EVENT_NOTICE` / `EVENT_BLACKBOX` | L23-L31 |
| `EVENT_KINDS` | L32-L44 |
| `class RunEvent` | L47-L54 |
| `RunEvent.__post_init__` | L55-L59 |
| `class EventBus` | L62-L63（类头＋docstring） |
| `EventBus.__init__` | L65-L68 |
| `EventBus.emit` | L70-L77 |
| `EventBus.close` | L79-L83 |
| `EventBus.closed` | L85-L87 |
| `EventBus.snapshot` | L89-L91 |
| `EventBus.stream` | L93-L107 |

**appv2/runtime/guide.py（149 行）**
| 符号 | 行号区间 |
| --- | --- |
| `DECISION_CONTRACT` | L24-L42 |
| `CLARIFY_CONTRACT` | L46-L97 |
| `TOOLMATCH_CONTRACT` | L99-L129 |
| `SUMMARY_CONTRACT` | L135-L142 |
| `class GuideProvider` | L145-L146 |
| `GuideProvider.guide` | L148 |

**appv2/runtime/budget.py（139 行）**
| 符号 | 行号区间 |
| --- | --- |
| `NO_MATERIAL_SHELL` | L22-L25 |
| `MAX_ROUNDS_CONTRACT` | L28 |
| `MAX_DISCOVERS_PER_ROUND_CONTRACT` | L29 |
| `MAX_EXECUTES_PER_ROUND_CONTRACT` | L30 |
| `TOTAL_SECONDS_CONTRACT` | L31 |
| `TOOL_TIMEOUT_SECONDS_CONTRACT` | L32 |
| `MAX_DISCOVERS_PER_RUN_CONTRACT` | L34 |
| `CLARIFY_ASK_CAP_CONTRACT` | L38 |
| `class Budget` | L41-L49 |
| `Budget.as_dict` | L51-L58 |
| `def now_monotonic` | L61-L63 |
| `def rounds_exhausted` | L66-L69 |
| `def time_exhausted` | L72-L74 |
| `def budget_gate_hit` | L77-L89 |
| `def unfinished_items` | L92-L105 |
| `def material_rows` | L108-L117 |
| `def unfinished_notice` | L120-L138 |

---

## context.py

### `TRUST_AGG`／`TRUST_LEDGER`／`TRUST_REPORT`（context.py L19-L21）｜信任级三档字符串常量
- 消费：`_KIND_TRUST` 的值（L23-L34）、`_TRUST_RANK` 的键（L35）。
- 装配：不涉（非上下文注入面）。
- 分支表（穷尽）：
  1. 无分支（纯常量定义） → 值为 `"authoritative"`／`"ledger"`／`"report"` → 供映射表与排序表引用。
- 副作用：无。
- 返回：字符串常量。
- 规则条目：
  - R-K-01 信任级为三档英文串，语义次序由 `_TRUST_RANK` 固定为 authoritative < ledger < report（数值越小越靠前）。
  - R-K-02 注释自述"骨架版确定性映射——细化批可调，语义不破：权威表最高"（L18）。
- 耦合：模块内 `_KIND_TRUST`、`_TRUST_RANK`。
- 疑点：
  - D-K-01 `_KIND_TRUST` 里出现的第四取值 `"notice"`（L33）不属于三档常量；含义与排序位在本模块无定义（见 D-K-02、D-K-05）。

### `_KIND_TRUST`（context.py L23-L34）｜观察 kind → 信任级映射表
- 消费：`TRUST_*` 三常量。
- 装配：不涉。
- **V2-125 文档同步**：生产实点＝`appv2/runtimev2/context/materials.py::_KIND_TRUST`，台账族第五键＝`family`（V2-105 改；真源 `appv2/knowledge/domain.py:28-32` `KIND_FAMILY="family"`）。本报告锚定的旧码 `appv2/runtime/context.py` 仍留旧键 `family_annotation`（V1 承载位，R5「旧码只作备份」）——下表按**生产实点**记 `family`。
- 分支表（穷尽，逐键）：
  1. `agg_row` → `TRUST_AGG`；
  2. `lineage` → `TRUST_AGG`；
  3. `metric` → `TRUST_LEDGER`；
  4. `term` → `TRUST_LEDGER`；
  5. `object` → `TRUST_LEDGER`；
  6. `relation` → `TRUST_LEDGER`；
  7. `family` → `TRUST_LEDGER`；
  8. `fragment` → `TRUST_REPORT`；
  9. `graph` → `TRUST_REPORT`；
  10. `notice` → 字符串 `"notice"`（非三档常量）；
  11. 未收录 kind → 由 `trust_of` 兜底落 `TRUST_REPORT`（本表不含兜底）。
- 副作用：无。
- 返回：`dict[str, str]`，10 键。
- 规则条目：
  - R-K-03 映射闭世界＝10 个 kind；权威表族 2 个（agg_row/lineage）、台账族 5 个（metric/term/object/relation/family）、检索族 2 个（fragment/graph）、notice 1 个。
  - R-K-04 `notice` 被映射为 `"notice"` 而非三档之一——该值不在 `_TRUST_RANK` 中。
- 耦合：`TRUST_AGG`／`TRUST_LEDGER`／`TRUST_REPORT`。
- 疑点：
  - D-K-02 模块 docstring（L8）称"notice 类观察不进模型面"，而映射表把 notice 也收进来——过滤发生在 `render_materials`（L78）而非映射层；若未来新增过滤白名单，此处 notice 取值语义与过滤表不同源。

### `_TRUST_RANK`（context.py L35）｜信任级排序位
- 消费：`TRUST_*` 三常量作键。
- 分支表（穷尽）：
  1. `TRUST_AGG` → 0；2. `TRUST_LEDGER` → 1；3. `TRUST_REPORT` → 2。
- 副作用：无。
- 返回：`dict[str, int]`，3 键。
- 规则条目：
  - R-K-05 排序位正向：0 最靠前（权威），2 最后（检索）。
  - R-K-06 缺键时的兜底值由消费点给定（`render_materials` L81 的排序键用 `9`），本表不含兜底。
- 耦合：`TRUST_AGG`／`TRUST_LEDGER`／`TRUST_REPORT`。
- 疑点：
  - D-K-01（同上）：`"notice"` 无 rank 位，一旦进入排序路径只能靠调用点的 9 兜底。

### `DEFAULT_MAX_OBSERVATIONS`（context.py L37）｜默认观察渲染上限
- 消费：`ContextBuilder.max_observations` 缺省值（L117）。
- 分支表：无。
- 副作用：无。
- 返回：整数 24。
- 规则条目：
  - R-K-07 默认上限 24 支——上限只作用于检索片段（report）族，见 R-K-12。
- 耦合：`ContextBuilder`。
- 疑点：无。

### `SYSTEM_PROMPT`（context.py L39-L50）｜常量，L39-L50
- 内容概述：定性系统为"查询与解读"（执行类诉求不在系统内，引导线下流程），并列三条红线——①每条事实断言必须带 [n] 引标；②材料含多来源时逐来源分别作答且不得无出处调和，并限定该纪律只适用于材料确已覆盖所问内容的情形；③只依据给定观察作答，未覆盖部分如实说明未找到。
- 规则条目：
  - R-K-08 红线①：事实断言必须带 [n] 引标指向给定观察，无据不断言。
  - R-K-09 红线②：多来源同理逐源列出，且明确"不得只取其一""不以反问代替作答"；作答后未覆盖来源须点名。
  - R-K-10 红线②作用域句：材料未覆盖所问内容时只简短说明未找到＋缺什么＋下一步，不逐源转述无关材料；用户点名主体而材料未覆盖时只说明未找到并请用户确认（可给最相近候选名）。
  - R-K-11 红线③：只依据给定观察回答。
  - R-K-12 定位句：执行类诉求（写入/修改/删除/发送/订阅提醒）不在系统内。
- 耦合：`appv2.runtime.executor`（executor.py L34 import）、`tests/domains/test_v2_v258_understand_orientation.py`（逐字子串钉）。
- 疑点：无（文本被测试逐字钉住）。

### `LEDGER_DICT_NOTE`（context.py L54-L58）｜常量，L54-L58
- 内容概述：台账全量块头注——"台账全量是字典不是数据"，只载定义/粒度/绑定态、不载数值，"在台账"不等于"数值在手"，数值须经检索取得，禁止仅凭本块 finalize。
- 规则条目：
  - R-K-13 头注位置：常驻块 BEGIN 标记后首行、位于 BEGIN/END 之间（由拼接方 `_resident_block` 保证，graph.py L1343-L1348）。
  - R-K-14 V2-79a 起当前轮不入史，块随当轮渲染、无收窄面（注释 L52-L53）。
- 耦合：`appv2.runtime.graph._resident_block`（graph.py L1345 逐字拼接）；`tests/domains/test_v2_v253_zero_probe_gate.py` L277 以 `RESIDENT_BLOCK_BEGIN + "\n" + LEDGER_DICT_NOTE + "\n"` 前缀断言。
- 疑点：
  - D-K-03 "头注位置在 BEGIN/END 之间"由 graph 侧拼接保证，本模块只有文本——两处规则（位置＋文本）分属两个文件，无本模块级校验。

### `trust_of`（context.py L61-L64）｜观察信任级判定单点
- 消费：`observation["locator"]["kind"]`（两级 `get`，均带空兜底）；`_KIND_TRUST`。
- 装配：不涉（被排序/标注消费：graph.py L3308、L3569 写 `entry["trust"]`；`render_materials` 内部调用）。
- 分支表（穷尽）：
  1. `locator` 缺失或为 None → 取 `""` → 未命中映射 → 返回 `TRUST_REPORT`；
  2. `locator` 存在但 `kind` 缺失 → 同上 → 返回 `TRUST_REPORT`；
  3. `kind` 命中映射 → 返回对应信任级（含 `"notice"`）；
  4. `kind` 非空但未收录 → `_KIND_TRUST.get` 未命中 → 返回 `TRUST_REPORT`。
- 副作用：无。
- 返回：`str`（信任级字符串，可能为 `"notice"`）。
- 规则条目：
  - R-K-15 判定路径唯一：只读 `locator.kind`，不读其它字段。
  - R-K-16 一切异常输入（缺 locator／缺 kind／未知 kind）统一落 `TRUST_REPORT`，不抛错。
  - R-K-17 `kind` 值强制 `str()` 转换后查表（非字符串 kind 也会被字面化再查表）。
- 耦合：`_KIND_TRUST`、`TRUST_REPORT`；graph.py L3308/L3569 消费点。
- 疑点：
  - D-K-04 未知 kind 静默降级为检索族——降级后该观察在 `render_materials` 中会参与截断与"检索片段"披露计数（L84-L85、L98-L99），权威内容可能被误截且无告警。
  - D-K-05 降级路径无日志/notice，调用方无从分辨"真 report"与"未知 kind 兜底 report"。

### `render_materials`（context.py L72-L109）｜材料段渲染唯一入口（compile 退役后）
- 消费：`observations: list[dict]`、关键字参数 `max_observations: int`；每条观察的 `locator.kind`、`index`、`source`、`well`、`content`。
- 装配：返回值 `text` 由调用方拼成一条 **user** 消息追加链尾——graph.py L3876-L3883（作答相位；每次作答一次，核验/收口不重发；最终答案由收口单点追加）。函数本身不写链。
- 分支表（穷尽）：
  1. `locator.kind == "notice"` → 从材料集排除（不进模型面） → 不渲染、不计入任何计数；
  2. 排序：`sorted(enumerate(material), key=rank_or_9)` → 稳定排序，同 rank 保持入栈原序；
  3. `trust_of != TRUST_REPORT` → 归入 `authority`（含 `"notice"` 等非 report 值）→ 全量渲染；
  4. `trust_of == TRUST_REPORT` → 归入 `reports`；
  5. `len(reports) > max_observations` → `truncated=True` → 只渲染 `reports[:max]` 并追加披露句；
  6. `len(reports) <= max_observations` → `truncated=False` → 无披露句；
  7. 渲染块为空（材料集为空） → 正文写 `"（无）"`；
  8. 单块 `trust`/`origin`/`well` 三段全空 → label 为空串 → 输出空括号 `"（）"`（`"｜".join` 的固有行为，非显式分支）。
- 副作用：emit 无；持久化写无（截断 notice 由调用方 graph.py L3884-L3898 发 `"notice"`／`type="material_truncated"`）。
- 返回：`tuple[str, dict]`——文本＋元数据 `{"material_truncated": bool, "material_rendered": int, "material_total": int}`。
- 规则条目：
  - R-K-18 引标 `[n]` 取观察自带 `index`（全局观察序号），不是渲染位次——模型面与答案引用同一套序号。
  - R-K-19 块的 label 形为 `信任级｜来源｜井`，空段跳过（`"｜"` 连接）。
  - R-K-20 块正文形为 `[index]（label）content`；`content` 缺失时补空串（`.get` 默认 `''`）。
  - R-K-21 `authority` 族无数量上限、恒全量渲染；上限只作用于 `reports` 族。
  - R-K-22 截断披露句含两个数：检索片段总数 `len(reports)` 与实际渲染数 `min(len(reports), max_observations)`。
  - R-K-23 披露句同时声明"未渲染片段不得对其断言"与"权威行集与台账卡已全量渲染"。
  - R-K-24 `material_rendered` ＝ authority ＋ 实渲 reports 的支数（＝`len(ordered)`）；`material_total` ＝ 排除 notice 后的观察总数。
  - R-K-25 文本以 `"\n观察材料：\n"` 起头，块间以换行连接。
  - R-K-26 排序键兜底值 9 只影响未在 `_TRUST_RANK` 登记的信任级（现状＝`"notice"`，但 notice 已在第 1 步被排除）。
- 耦合：`_TRUST_RANK`、`_KIND_TRUST`、`trust_of`、`TRUST_REPORT`；消费方 `appv2.runtime.graph`（L3876-L3883）与 `ContextBuilder.max_observations`。
- 疑点：
  - D-K-04（同上，未知 kind 被误当 report 截断）。
  - D-K-06 `int(obs["index"])` 为硬取（L89）——`index` 缺失抛 KeyError、非数字抛 ValueError，无兜底分支。
  - D-K-07 authority／台账族无上限：材料段长度只受 report 帽约束，若权威行集或台账卡数量暴涨，材料段可无限增长（注释只保证"截断显式披露"）。
  - D-K-08 排序键对未登记信任级回退 9，但 authority/report 分组用的是 `!= TRUST_REPORT` 判定——若将来新增一种信任级（如第四档），它会自动落 authority 分支（全量渲染、不计入披露），与排序兜底 9（排到最末）语义互相矛盾。
  - D-K-09 披露句文案写死"权威行集与台账卡已全量渲染"——句中的"台账卡"对应 kind 集合由 `_KIND_TRUST` 隐式定义，改映射表不会同步改文案，无测试锚（本文件无非 notice/片段类字面校验）。
  - D-K-10 `min(len(reports), max_observations)` 在披露句中使用：`max_observations` 为负或 0 时不报错，只渲染 0 支并报"渲染前 0 支"（无参数校验）。

### `ContextBuilder`（context.py L113-L117）｜材料渲染配置面
- 消费：`DEFAULT_MAX_OBSERVATIONS`（缺省）。
- 装配：不涉（`compile` 已退役——docstring L115 明示只余 `max_observations` 消费缝）。
- 分支表（穷尽）：
  1. 构造不传参 → `max_observations=24`；
  2. 传参 → 用传入值（无上下界校验）。
- 副作用：无。
- 返回：dataclass 实例；`max_observations` 字段。
- 规则条目：
  - R-K-27 `@dataclass(slots=True)`，唯一字段 `max_observations: int`，非 frozen。
  - R-K-28 无任何方法——纯配置载体（`hasattr(ContextBuilder(), "compile")` 为假，测试 tests/domains/test_v2_v258_understand_orientation.py L276 钉住）。
- 耦合：`appv2.runtime.graph` L3877（`deps.builder.max_observations`）；`appv2.runtime.executor` L34/L352（构造后注入 LoopDeps）；`appv2.runtime.__init__` L55 公开导出 `ContextBuilder`。
- 疑点：
  - D-K-11 非 frozen 且 slots 无保护——运行期可写 `builder.max_observations`（`Budget` 同类对象为 frozen，两者一致性策略不同）。
  - D-K-12 `max_observations` 无类型/范围校验（可为负数、0、非 int），下游直接用于切片与 `min()`。

---

## events.py

### `EVENT_STEP`…`EVENT_BLACKBOX`（events.py L23-L31）｜事件名闭世界九常量
- 内容：`step`/`text`/`tool`/`observation`/`ask`/`verdict`/`citation`/`notice`/`blackbox` 九个字符串常量。
- 分支表：无。
- 副作用：无。
- 返回：字符串常量。
- 规则条目：
  - R-K-29 事件名为九类字符串常量，字面值即 wire 面 `event` 字段值。
  - R-K-30 注释 L21 自称"事件八类闭世界"但实际常量九个（blackbox 为 V2-54 追加）。
- 耦合：`EVENT_KINDS`；`appv2.runtime.__init__` L63-L74 公开导出（不含 `EVENT_BLACKBOX`，见 D-K-14）。
- 疑点：
  - D-K-13 注释/文案与实际数量不符：L21、L49（`RunEvent` docstring）、L58（报错文案"八类闭世界"）三处写"八类"，实际 `EVENT_KINDS` 九元。
  - D-K-14 `EVENT_BLACKBOX` 未被 `appv2.runtime.__init__` 导出（L63-L74 导出清单里无它），仅 `executor.py` L35 直接 import——公开面与闭世界成员不一致。

### `EVENT_KINDS`（events.py L32-L44）｜闭世界判据
- 消费：九个 `EVENT_*` 常量。
- 分支表（穷尽）：
  1. 成员在内 → 合法；2. 不在 → 由 `RunEvent.__post_init__` 抛 ValueError。
- 副作用：无。
- 返回：`frozenset[str]`，9 元。
- 规则条目：
  - R-K-31 闭世界唯一判据＝该 frozenset（不可变，运行期不可增删）。
  - R-K-32 类型标注显式 `frozenset[str]`。
- 耦合：九个 `EVENT_*`；`RunEvent.__post_init__`；`appv2.runtime.__init__` L66。
- 疑点：
  - D-K-13（同上，文案"八类"）。
  - D-K-15 闭世界与 wire 面下游映射（`appv2/api/wire.py` L28-L36 挑选导出）无机器闸比对——新增事件类需人工在 api 面补映射。

### `RunEvent`（events.py L47-L54）｜事件帧
- 消费：调用方传入 `seq`／`event`／`data`。
- 装配：不涉。
- 分支表（穷尽）：
  1. 构造 → 交 `__post_init__` 校验（仅一条分支）。
- 副作用：无。
- 返回：frozen 实例，字段 `seq: int`、`event: str`、`data: dict[str, Any]`。
- 规则条目：
  - R-K-33 `@dataclass(frozen=True, slots=True)`——帧不可变，无字段校验（除事件名）。
  - R-K-34 `seq` 语义＝断线游标（docstring L49）。
  - R-K-35 `data` 为任意字典，无 schema 约束（键形由发帧方各自决定）。
- 耦合：`EVENT_KINDS`；`appv2.runtime.state`（state.py L31 import）、`appv2.api.bridge` L36、`appv2.runtime.__init__` L73。
- 疑点：
  - D-K-16 `data` 无键校验且不同事件类载荷异构（如 notice 带 `type/gates/content`、ask 带 `frame/run_id`）——载荷契约不在本模块，本文件内无闭世界。

### `RunEvent.__post_init__`（events.py L55-L59）｜事件名越界拦截
- 分支表（穷尽）：
  1. `self.event not in EVENT_KINDS` → `raise ValueError`（文案内嵌排序后的闭世界集合）；
  2. 命中 → 无操作。
- 副作用：无。
- 返回：None。
- 规则条目：
  - R-K-36 闭世界校验在构造期，fail-closed（越界即炸，不静默）。
  - R-K-37 报错文案动态插入 `sorted(EVENT_KINDS)`——文案随闭世界变化自动更新（与 D-K-13 的"八类"前缀不同源）。
- 耦合：`EVENT_KINDS`。
- 疑点：
  - D-K-17 异常类型为内置 `ValueError`，无自定义异常子类——调用方无法按类型区分"事件名写错"与其它 ValueError。

### `EventBus.__init__`（events.py L65-L68）｜事件流三态构造
- 消费：无。
- 分支表：无。
- 副作用：无。
- 返回：实例，三内部状态：`_events: list[RunEvent]`、`_queue: asyncio.Queue[RunEvent | None]`、`_closed: bool = False`。
- 规则条目：
  - R-K-38 双通道：列表保存全部历史（游标回看面），队列承载等待唤醒（实时消费面）。
  - R-K-39 队列元素类型含 `None` 哨兵——终止信号。
  - R-K-40 队列在 `__init__` 中同步构造（`asyncio.Queue()` 不要求运行中的事件循环）。
- 耦合：`asyncio.Queue`；`RunEvent`。
- 疑点：
  - D-K-18 队列无容量上限——事件产生速度超过消费速度时全量积压在内存（与 `_events` 列表重复持有同一引用）。
  - D-K-19 `asyncio.Queue` 在无事件循环的线程构造/使用行为未在代码中约束（现代 asyncio 允许构造，但 `put_nowait`/`get` 需读线程上下文）——本文件无说明。

### `EventBus.emit`（events.py L70-L77）｜发帧
- 消费：`event: str`、`data: dict[str, Any]`。
- 装配：不涉。
- 分支表（穷尽）：
  1. `self._closed` 为真 → `raise RuntimeError`（"close 后不得再发射"，拒收）；
  2. 未关闭 → `seq = len(self._events)`、`RunEvent(...)` 构造（闭世界校验在此触发）、追加 `_events`、`put_nowait`、返回该帧。
- 副作用：emit 自身无事件副作用；写入内部 `_events` 与 `_queue`（进程内状态，非持久化）。所有事件类（step/text/tool/observation/ask/verdict/citation/notice/blackbox）的产生均经此单点。
- 返回：`RunEvent`（同一引用已入列表与队列）。
- 规则条目：
  - R-K-41 `seq` 由历史长度唯一决定（单调、0 起、无跳号，前提是不删除历史）。
  - R-K-42 关闭后发射＝缺陷，显式抛错而非静默丢弃。
  - R-K-43 发射顺序＝列表顺序＝队列顺序（`put_nowait` 同步入队）。
- 耦合：`RunEvent`、`EVENT_KINDS`（间接）；消费方 `appv2.runtime.graph`（73 处 `deps.bus.emit` 调用点）、`appv2.runtime.executor`（L508-L511）。
- 疑点：
  - D-K-20 `emit` 的 `event` 参数无本地校验，闭世界校验完全依赖 `RunEvent.__post_init__`——参数类型（如 None）会以 ValueError 形式抛出，错误信息指向 "RunEvent.event 越界" 而非调用点。
  - D-K-21 `seq = len(self._events)` 与 `snapshot()`/`stream()` 的历史列表强耦合——一旦将来出现删除/裁剪历史的优化，seq 会重复，stream 的去重逻辑（见 `stream`）会静默丢帧。

### `EventBus.close`（events.py L79-L83）｜收束
- 分支表（穷尽）：
  1. `_closed` 为假 → 置 True ＋ `put_nowait(None)`；
  2. `_closed` 为真 → 幂等无操作（不重复投哨兵）。
- 副作用：向队列投一次 `None`。
- 返回：None。
- 规则条目：
  - R-K-44 幂等：重复 close 不重复投哨兵。
  - R-K-45 收束语义＝投递终止信号，不阻止历史回看（`snapshot` 仍可读，`stream(cursor)` 对已发射历史仍可取）。
- 耦合：调用点 `appv2.runtime.executor` L511（`bus.close()`）；`appv2/api/bridge` 的 `RunStream.closed` 属性（bridge.py L55）为另一层的关闭标志，非本方法。
- 疑点：
  - D-K-22 哨兵为单发：多个消费者（`stream` 多次调用）中只有一个能取到 `None` 而正常收束，其余见 D-K-23。

### `EventBus.closed`（events.py L85-L87）｜只读属性
- 分支表：无。
- 副作用：无。
- 返回：`bool`（内部 `_closed`）。
- 规则条目：
  - R-K-46 只读视图，无 setter；外部据此判发射是否仍合法（与 `emit` 的拒收条件同源）。
- 耦合：无外部调用点（本仓未发现消费）。
- 疑点：
  - D-K-23 `closed` 无本仓消费者（grep 无结果）；关闭态判定在 api 层由 `RunStream.closed`（bridge.py L55）另行维护——两处"关闭"语义不同源。

### `EventBus.snapshot`（events.py L89-L91）｜历史快照
- 分支表：无（单一返回路径）。
- 副作用：无。
- 返回：`list[RunEvent]`——`self._events` 的浅拷贝（元素为同一帧对象；帧本身 frozen）。
- 规则条目：
  - R-K-47 快照是副本，调用方增删不影响内部历史。
  - R-K-48 用途：游标回看的进程内面（V2-07 断线续传）。
- 耦合：`RunEvent`（frozen 保证浅拷贝安全）。
- 疑点：
  - D-K-24 无本仓调用点（api 层用 `handle.stream` 单点排空，bridge.py L95）——该 API 目前只被测试或外部消费者使用，实际入口归属不明。

### `EventBus.stream`（events.py L93-L107）｜按游标消费
- 消费：`cursor: int = 0`。
- 分支表（穷尽）：
  1. `index < len(self._events)` → `yield self._events[index]`、`index += 1`、`continue`（优先补偿历史）；
  2. 否则 `await self._queue.get()`；
  3. 取出 `None` → `return`（流收束）；
  4. 取出帧且 `item.seq < index` → `continue`（排队期间已被历史分支消费，跳过防重复）；
  5. 取出帧且 `item.seq >= index` → `yield item`、`index = item.seq + 1`。
- 副作用：无（消费队列，吞吐内部状态）。
- 返回：`AsyncIterator[RunEvent]`（异步生成器；`return` 即 StopAsyncIteration）。
- 规则条目：
  - R-K-49 `cursor` 语义＝断线前已收到的最大 `seq` ＋ 1；保证不重复不遗漏（注释 L94）。
  - R-K-50 历史优先：已落列表的帧先从列表读，队列只用于等待新帧——列表与队列双投递靠 `item.seq < index` 去重。
  - R-K-51 收束由 `None` 哨兵驱动；`_closed` 标志在本方法内不参与判定。
  - R-K-52 生成器按调用时的 `cursor` 惰性推进，可从中途接入。
- 耦合：`RunEvent`、`asyncio.Queue`；消费方 `appv2.runtime.executor` L209/L260（`RunHandle(stream=bus.stream())`）、`appv2/api/bridge` L95（api 层唯一排空点）。
- 疑点：
  - D-K-25 多消费者隐患：`None` 哨兵是一次性的——消费者 A 取走后队列为空，消费者 B 若 `cursor >= len(_events)` 将永久 `await`（挂死），本方法无"已关闭且无新历史即返回"的短路。
  - D-K-26 越界游标（`cursor > len(_events)`，如重放已攒满历史的流）同样落队列分支；若此时流已关闭且哨兵已被取走，行为同上（永久阻塞）；本方法不校验游标范围。
  - D-K-27 已关闭后新接入的消费者：若 `cursor == 0` 且历史非空，可正常读完历史，但读完后仍会 `await queue.get()`——因哨兵可能已在 close 时被首个消费者取走，此时不会收到终止信号（挂死），需要消费者自行依据 `closed` 属性退出（本方法未用该属性）。

---

## guide.py

### `DECISION_CONTRACT`（guide.py L24-L42）｜常量，L24-L42
- 内容概述：决策相位发射合同——每轮只输出一个 JSON 对象（可围栏）；键 `thought`（可省）＋`action`（四值闭世界 discover/execute/ask/finalize）；逐 action 规定键形：discover 给 `discovers`（1~2 支，工具 semantic_query/table_schema 及各自 args 二选一形）、execute 给 `task_type`（data/knowledge/mixed）＋按类型给 `plan`／`retrieval_need`（family_hints 只许 completion/monthly/dynamic/blank 四个机器名）、ask 给 `ask`（prompt＋2~4 选项）、finalize 表示材料足够（系统起草带引用答案）；`note` 可随任意 action 出场。
- 规则条目：
  - R-K-53 合同含四 action 闭世界与逐 action 键形约束（含 1~2 支 discover、ask 2~4 选项）。
  - R-K-54 `family_hints` 允许值＝四个机器名常量，且在文本中明示"不要写中文名"。
  - R-K-55 `note` 键可随任意 action 出场。
- 耦合：`appv2/api/ontology_guide.py` L27 导入、L124 与 ontology §A 切面拼接为 `f"{section}\n\n{DECISION_CONTRACT}"`（生产指南源）；`appv2.runtime.__init__` L99/L157 公开导出。
- 疑点：
  - D-K-28 模块 docstring（L7-L8）称本常量"与 graph.parse_decision schema 校验代码同源单点，运行时所有决策面的发射合同真源"，但 `appv2/runtime/graph.py` **不 import 本常量**（其 guide 导入清单仅 CLARIFY/SUMMARY/TOOLMATCH/GuideProvider，graph.py L84-L89）——"同源"靠人工文本一致维护，无本模块级机器闸。
  - D-K-29 与 `CLARIFY_CONTRACT` 存在语义交叠（action 词表：DECISION 有 execute、CLARIFY 只有 discover/decompose/ask/finalize）——交叠边界由消费点文案消歧（graph.py L2350-L2356 声明"指南正文中出现的 execute 动作归后续相位"），不在本文件。

### `CLARIFY_CONTRACT`（guide.py L46-L97）｜常量，L46-L97
- 内容概述：相位①业务澄清发射合同——引号规矩（值内一律中文引号「」或单引号，禁裸英文双引号，附错例/对例）；四动作 decompose（子问题组，子问题 ≤`{max_subtasks}` 个、ledger_notes 必带）、discover（1~2 支，工具三选：semantic_query/table_schema/faq_lookup，禁猜词敲门）、finalize（仅当本 run 已有探查观察，零观察禁 finalize，台账常驻注入不进交付面）、ask（2~4 选项，仅限两种白场）；工具目录（含 `{discover_used}` 替换槽）；发射判据（台账命中＋窗已定＝分解；窗可锚定＝禁 ask，含默认近 30 天与模糊时间词双 null 两分支）；knowledge 链规则（单子问题组直发、不问范围/载体/口径支）；回捞白场（每子问题限一次，消耗一轮不挂起不占 ask）。
- 规则条目：
  - R-K-56 两处运行时替换槽：`{max_subtasks}` 与 `{discover_used}`，由 clarify 节点统一 `replace`（graph.py L2334-L2337：前者 ← `MAX_SUBTASKS_CONTRACT`，后者 ← `state.discover_used`）。
  - R-K-57 引号规矩段落为 V2-60 票面逐字稿（实证依据：族 D 三题字节级）。
  - R-K-58 工具目录段落与定稿直答行为 P-051b 修正段均标注为"票面施工基准——char 相等，不得增删字"。
  - R-K-59 合同内声明的探查预算数值"全 run ≤10 次"为文本字面（L65），非引用常量。
- 耦合：`appv2.runtime.graph` L85/L2334（clarify 节点装配）；`MAX_SUBTASKS_CONTRACT`（`appv2.runtime.subtask`）；`appv2.runtime.__init__` L153 导出；`tests/domains/test_v2_v259_clarify_assembly.py`、`test_v2_p039_contract_and_name_gate.py`、`test_v2_v260_quote_rule.py`、`test_v2_p039b_f2c_two_branch_wording.py`、`test_v2_r1c_window_recall.py` 等逐字/子串钉。
- 疑点：
  - D-K-30 预算数值双源：文本写"全 run ≤10 次"（L65）而常量 `MAX_DISCOVERS_PER_RUN_CONTRACT = 10`（budget.py L34）——不引用，改值需人工同步（本文件无校验）。
  - D-K-31 `{discover_used}`、`{max_subtasks}` 是无类型占位符裸串；若替换被跳过（eg. 新消费点忘记 replace），模型面会看到字面 `{max_subtasks}`——本文件无断言或兜底。
  - D-K-32 合同文本内自述"开局已给全台账"（L61-L62）——该前提由消费点保证（常驻块注入），两文件规则耦合且本文件无机器检查。
  - D-K-33 引号规矩段落在 `CLARIFY_CONTRACT` 与 `TOOLMATCH_CONTRACT` 各写一遍（L48-L53 与 L101-L105 文本近乎相同，注释各自标注"逐字来自不同票"）——同一规则双份文本，改一处需改两处。

### `TOOLMATCH_CONTRACT`（guide.py L99-L129）｜常量，L99-L129
- 内容概述：相位②工具匹配合同——引号规矩（与相位①同款三行）；输出 `{"matches": [...]}`，每子问题恰一条（id 闭合世界）；逐键说明：`plan` 形（metric_slot 必填非空禁英文列名、ranking 必填布尔＋direction、aggregate 缺省 false 用于求和/合计类整窗 SUM、window_start/window_end（不含端）ISO 或 null、limit 仅问句显式条数时写、external_tables 仅外表引用时写；缺 ranking 等必填键＝参数校验拒）、`retrieval_need` 形（question 必填非空须逐字转抄、anchors 可选、family_hints 四机器名可选；只许三键，禁造键名）、`caliber_key` 可选（仅问句场景词已落定口径支时携带）；末尾附填写样例（单匹配 knowledge 形）。
- 规则条目：
  - R-K-60 无运行时替换槽（纯静态文本）。
  - R-K-61 `matches` 与问题组一一对应、id 闭世界，由本文本声明。
  - R-K-62 `retrieval_need` 只许三键（question/anchors/family_hints），禁造键名。
  - R-K-63 样例段落为 V2-62 票面逐字稿，示例词"杆柱"过 P-039 命名闸（非台账词）。
- 耦合：`appv2.runtime.graph` L87/L2702（匹配相位装配）；`appv2.runtime.__init__` L194 导出；多个四相位测试（tests/domains/test_v2_four_phase.py、test_v2_v262_turn_selfsufficiency.py 等）。
- 疑点：
  - D-K-33（同上，引号规矩重复文本）。
  - D-K-34 合同声明"缺 ranking 等必填键＝参数校验拒"——实际拒因产生在 `graph.parse_decision`／匹配校验侧，本文件不含校验实现，两处同步靠人工。

### `SUMMARY_CONTRACT`（guide.py L135-L142）｜常量，L135-L142
- 内容概述：相位④汇总合同——整合问题组全部子结果，逐子问题一行结论（子问题要点→答案），成功子问题逐条断言带 [n] 引标，被拒/失败子问题如实说明原因不冒充不出数；追加排名支配约束——排名型子问题（plan ranking=true）的结论必须取本子问题的排名观察支（引擎按计划合计口径给出的排名行），不得从其他子问题的明细行切片换算或跨子问题取值。
- 规则条目：
  - R-K-64 汇总合同只在 answer 指令装配点注入（`assemble_answer_instruction(summary_contract=...)`，graph.py L3870）。
  - R-K-65 排名支配句为 V2-51 追加段，追加在尾部（注释 L133-L134 明示"现有措辞零删改"）。
  - R-K-66 文案所用"排名观察支""合计行"为机读载荷词面，零业务名词（注释 L134）。
- 耦合：`appv2.runtime.graph` L86/L3870；`appv2.runtime.__init__` L192；`tests/domains/test_v2_v251_domain_fuzzy_dominance.py` L449-L453（钉"排名型子问题""排名观察支"子串）、`tests/domains/test_v2_p039_contract_and_name_gate.py` L37/L121。
- 疑点：
  - D-K-35 SUMMARY_CONTRACT 只在作答（汇总）装配点消费；`graph.py` L337 注释称"汇总相位复用 answer 节点"，即汇总与普通作答共用同一常量——两语义（普通作答指令 vs 汇总指令）由 `assemble_answer_instruction`（orientation 模块）分叉，本文件不体现该分叉输入（subtask_list 是否为"（无）"）。

### `GuideProvider`（guide.py L145-L148）｜协议
- 声明方法：`def guide(self) -> str: ...`（L148）。
- 分支表（穷尽）：
  1. 实现方返回非空指南文本 → 消费点拼接（graph.py L1699／L2367／L2705）；
  2. 返回空串 → 拼接处仍加前后分隔（无校验）。
- 副作用：无（协议无实现）。
- 返回：`str`。
- 规则条目：
  - R-K-67 结构性协议（`typing.Protocol`，未标 `runtime_checkable`）——只约束形状，无运行期校验。
  - R-K-68 唯一方法 `guide()` 无参数、返回 `str`。
  - R-K-69 生产唯一实现＝`appv2.api.ontology_guide.OntologyGuideProvider`；占位 `DefaultGuideProvider` 已退役（V2-34 任务 10，"不设双真源"——注释 L12-L15）。
- 耦合：`appv2.runtime.graph` L88/L363/L376（`LoopDeps.guide: GuideProvider`）、调用点 L1699（决策包尾部）、L2367（澄清相位包尾部）、L2705（匹配相位包尾部）；`appv2.api.ontology_guide`、`appv2.api/app.py` L197（组合根缺省接线）；`appv2.runtime.__init__` L208 导出。
- 疑点：
  - D-K-36 "不设双真源"纪律无机器闸：`GuideProvider` 为普通 Protocol，任意对象（含测试剧本）在静态检查缺失时即可注入；`executor.py` L150 侧就写作 `guide: Any = None`（注释"防环不直接 import 类型"），协议在两处形参上仅一处生效。
  - D-K-37 协议无 `guide()` 返回值非空约束；三处消费点直接字面拼接，空串/超长串无防护。

---

## budget.py

### `NO_MATERIAL_SHELL`（budget.py L22-L25）｜常量，L22-L25
- 内容概述：未找到/未取得材料时给用户的唯一人话壳——"没能查到能回答这个问题的材料——可以换个问法，或告诉我更多背景（哪口井、哪个时间段），我再帮您查。"
- 规则条目：
  - R-K-70 单源：注释 L20-L21 声明"五装配点消费；追问版人话壳 V2-77 独立不动"。
  - R-K-71 用途分叉：既作收敛 notice 的 tail（L131），又作零材料直达答复（graph.py L1080、L1217、L3658）。
- 耦合：`appv2.runtime.graph` L73/L1080/L1217/L3658、L76 由 `unfinished_notice` 复用；`appv2.runtime.__init__` 未导出（graph 直接 import）。
- 疑点：
  - D-K-38 注释称"五装配点"，本仓 grep 到的消费点为 4 处（graph.py L1080、L1217、L3658 ＋ budget.py L131）——计数与现状需 Owner 对账；第 5 处是否在 web 面或测试面未核实。

### 预算合同常量组（budget.py L28-L38）｜逐个列值
| 常量 | 行号 | 值 |
| --- | --- | --- |
| `MAX_ROUNDS_CONTRACT` | L28 | 3 |
| `MAX_DISCOVERS_PER_ROUND_CONTRACT` | L29 | 2 |
| `MAX_EXECUTES_PER_ROUND_CONTRACT` | L30 | 2 |
| `TOTAL_SECONDS_CONTRACT` | L31 | 300.0 |
| `TOOL_TIMEOUT_SECONDS_CONTRACT` | L32 | 30.0 |
| `MAX_DISCOVERS_PER_RUN_CONTRACT` | L34 | 10 |
| `CLARIFY_ASK_CAP_CONTRACT` | L38 | 6 |
- 分支表：无。
- 副作用：无。
- 返回：数值常量。
- 规则条目：
  - R-K-72 轮数上限＝3（轮＝LLM 决策周期）。
  - R-K-73 轮内双上限：发现 ≤2、主执行 ≤2（注释 L3-L5 指明执法点在决策发射 schema 校验 `graph.parse_decision`，超限＝拒因回喂重决策）。
  - R-K-74 单段总时长＝300.0 秒；单工具超时＝30.0 秒。
  - R-K-75 澄清相位发现预算：全 run ≤10 次（V2-34，Owner 2026-10-09 拍板放宽原 3-4）。
  - R-K-76 连续 ask 截断上限＝6（V2-70 b 案，Owner 2026-10-13 两次拍板 2→3→6）。
  - R-K-77 防环语义：run 生命期计数任何路径不清零（注释 L37 记载 run-69517e02 实测封环面）。
  - R-K-78 注释 L27 声明"测试可收窄，合同值本身不因测试改动"。
- 耦合：`Budget` 缺省值（L45-L49）；`appv2.runtime.__init__` L45-L52 导出六个（不含 `CLARIFY_ASK_CAP_CONTRACT`）；`appv2.runtime.graph` L68-L72 导入四个（CLARIFY_ASK_CAP／MAX_DISCOVERS_PER_ROUND／MAX_DISCOVERS_PER_RUN／MAX_EXECUTES_PER_ROUND／MAX_ROUNDS）用于节点内嵌文案与判据；`tests/domains/test_v2_react_loop.py` L723 钉 `CLARIFY_ASK_CAP_CONTRACT == 6`、L734 monkeypatch 收窄为 3。
- 疑点：
  - D-K-39 双源数值：`MAX_DISCOVERS_PER_RUN_CONTRACT = 10` 与 `CLARIFY_CONTRACT` 文本内"全 run ≤10 次"（guide.py L65）各自硬编码，非同源引用。
  - D-K-40 `TOOL_TIMEOUT_SECONDS_CONTRACT` 的执法点在 graph（`state.budget.get("tool_timeout_seconds", 30.0)`，graph.py L2146／L2168／L2251／L3298）——四处均硬编码兜底 30.0，与本常量字面重复。
  - D-K-41 `CLARIFY_ASK_CAP_CONTRACT` 未进 `appv2.runtime.__init__` 公开导出（L45-L52 清单无它），但 graph.py L68 直接导入并用于多处文案与判据（L1859、L2631、L3108、L3522）——公开面与事实消费面不一致。
  - D-K-42 注释 L27 称"合同值不因测试改动"，但 monkeypatch 收窄全程可行（无 frozen/只读保护），纪律靠约定（与 D-K-11 同类）。

### `Budget`（budget.py L41-L49）｜冻结合同形参数对象
- 消费：五个合同常量作字段缺省。
- 装配：`as_dict()` 结果进 `RunState.budget` 随 checkpoint 走（模块 docstring L10-L11：跨进程恢复后判据仍生效）。
- 分支表（穷尽）：
  1. 字段全缺省 → 取五合同常量；
  2. 任一侧收窄（测试传入） → 用传入值。
- 副作用：无。
- 返回：frozen dataclass 实例；字段 `max_rounds: int`、`max_discovers_per_round: int`、`max_executes_per_round: int`、`total_seconds: float`、`tool_timeout_seconds: float`。
- 规则条目：
  - R-K-79 `@dataclass(frozen=True, slots=True)`——实例化后不可改。
  - R-K-80 字段顺序即 `as_dict` 键序（五键）。
  - R-K-81 无校验（如负数轮数、零时长均不拦）。
- 耦合：五合同常量；`appv2.runtime.executor` L33（`Budget` 构造）、L246（`deadline_monotonic = now_monotonic() + self._budget.total_seconds`）；`appv2.runtime.__init__` 导出 `Budget`；`tests/domains/test_v2_runtime_wiring.py` 等。
- 疑点：
  - D-K-43 `max_discovers_per_round`／`max_executes_per_round` 只经 `as_dict` 出值，判据在被 graph 读取——字段名与判据在 graph 侧的键名需逐字一致（`state.budget.get("max_executes_per_round", ...)`，graph.py L1690-L1693），无本模块级保障。

### `Budget.as_dict`（budget.py L51-L58）｜进 checkpoint 的序列化形
- 分支表（穷尽）：
  1. 单一返回路径：三个 int 字段转 `float()`，两个 float 字段原样返回。
- 副作用：无。
- 返回：`dict[str, float]`，键＝`max_rounds`／`max_discovers_per_round`／`max_executes_per_round`／`total_seconds`／`tool_timeout_seconds`（五键，全 float 值）。
- 规则条目：
  - R-K-82 全值 float 化（类型统一）。
  - R-K-83 键名与字段名逐字相同（读回侧按同名 get）。
- 耦合：`RunState.budget`（graph 侧 `state.budget.get(...)` 多处）；checkpoint 持久化面。
- 疑点：
  - D-K-44 int→float 再 `int()` 回转（`rounds_exhausted` L68）——类型往返无注释说明是否刻意（JSON 序列化兼容性推测，未在代码注明）。

### `now_monotonic`（budget.py L61-L63）｜预算面时钟
- 消费：`time.monotonic`。
- 分支表：无。
- 副作用：无。
- 返回：float（单调秒）。
- 规则条目：
  - R-K-84 docstring 自述为"B14 时钟纪律的预算面——墙上时钟不进判据"。
  - R-K-85 唯一实现＝`time.monotonic`（直连 stdlib，不经 `appv2.infra.clock`）。
- 耦合：`time.monotonic`；`appv2.runtime.executor` L33/L246/L371；`unfinished_notice` 不消费（由 `time_exhausted` 间接用）。
- 疑点：
  - D-K-45 `appv2/infra/clock.py` 只提供墙上时钟（`now`／`iso_now`／`display_now`／`freeze`／`set_clock`，无 monotonic 对应）——故本函数直连 stdlib 与 AGENTS.md"时间一律 infra.clock"的关系需确认（是否属允许的预算面例外，代码注释只提 B14 未给例外条款）。

### `rounds_exhausted`（budget.py L66-L69）｜轮数闸判据
- 消费：`state.budget`（字典 `.get("max_rounds", MAX_ROUNDS_CONTRACT)`）、`state.rounds`（`getattr(..., 0)`）。
- 分支表（穷尽）：
  1. `state.budget` 缺 `max_rounds` 键 → 用合同常量 3；
  2. `state` 无 `rounds` 属性 → 用 0；
  3. `int(rounds) >= int(max_rounds)` → True；否则 False。
- 副作用：无。
- 返回：`bool`。
- 规则条目：
  - R-K-86 判据恰为 `rounds >= max_rounds`（达到上限即触界，非越界）。
  - R-K-87 形参 `state: Any`——不 import `RunState`（注释"防环不 import"），靠鸭子类型属性契约。
- 耦合：`RunState.budget`／`RunState.rounds`；`budget_gate_hit`；合同常量 `MAX_ROUNDS_CONTRACT`。
- 疑点：
  - D-K-46 字段缺失的静默兜底（`getattr(state, "rounds", 0)`）会把"结构错误"读成"未消耗轮次"（不触界）——与 `time_exhausted` 的硬取策略不对称（见 D-K-47）。
  - D-K-47 `state.budget` 为 None 或非 dict 时 `.get` 直接 AttributeError（无兜底）——与上一行的宽容策略混搭。

### `time_exhausted`（budget.py L72-L74）｜时长闸判据
- 消费：`now_monotonic()`、`state.deadline_monotonic`（硬取属性）。
- 分支表（穷尽）：
  1. `now_monotonic() >= state.deadline_monotonic` → True；
  2. 否则 False（含相等边界归为 True）。
- 副作用：无。
- 返回：`bool`（外层 `bool()` 显式包裹）。
- 规则条目：
  - R-K-88 判据＝单调钟越 deadline；墙上时钟不参与。
  - R-K-89 挂起恢复后 deadline 按段重算（docstring：executor 刷新）。
- 耦合：`now_monotonic`；`RunState.deadline_monotonic`（写点 `appv2.runtime.executor` L246）；`budget_gate_hit`。
- 疑点：
  - D-K-47 属性缺失/为 None 时抛 AttributeError/TypeError（无 getattr 兜底、无 None 检查）——与 `rounds_exhausted` 的兜底风格不一致（D-K-46 对称面）。

### `budget_gate_hit`（budget.py L77-L89）｜入口闸检查
- 消费：`state`、关键字参数 `include_rounds: bool = True`。
- 分支表（穷尽）：
  1. `include_rounds and rounds_exhausted(state)` → 追加 `"max_rounds"`（否则不追加）；
  2. `time_exhausted(state)` → 追加 `"total_seconds"`（否则不追加）；
  3. 两闸都不命中 → 空列表（未触界）。
- 副作用：无。
- 返回：`list[str]`——闸名列表，顺序固定（轮数在前、时长在后）。
- 规则条目：
  - R-K-90 `include_rounds=False` 时轮数闸不参与——docstring：轮数闸只守 decision 入口，轮内 execute/observe 与定稿后 answer/verify 不受轮数闸拦（否则 finalize 会被自家预算吞掉）。
  - R-K-91 时长闸全节点守（无开关）。
  - R-K-92 返回闸名即机读判据，随 notice 载荷走（下游 `unfinished_notice(gates=...)`）。
  - R-K-93 闸名字面值＝`"max_rounds"`／`"total_seconds"`（与 `Budget.as_dict` 键名同名，但非同一常量引用）。
- 耦合：`rounds_exhausted`、`time_exhausted`；`appv2.runtime.graph` L74/L1105（`_gate_or_none` 装配点，`include_rounds=rounds_gate`）。
- 疑点：
  - D-K-48 闸名字符串散落多处 literal（graph.py L136 `'、'.join(gates)`、L1539 取 `("type","gates","content")`）——无闭世界常量（对比 `EVENT_KINDS` 的 frozenset 纪律）。
  - D-K-49 `include_rounds` 默认 True，但实际两侧语义由调用点显式传（graph.py L1105、L2328 等），默认值是否被任一调用点使用未核实（本仓 grep 未发现省略该参数的调用）。

### `unfinished_items`（budget.py L92-L105）｜未完成项清单
- 消费：`state.understanding`、`state.rounds`、`state.last_result`、`state.observations`、`state.verdict`、`state.draft`、`state.answer`。
- 分支表（穷尽，五条互相独立，按序 append）：
  1. `not state.understanding` → 追加 `"理解（understand）未执行"`；
  2. `state.rounds < 1` → 追加 `"决策（decision）未执行"`；
  3. `state.last_result is None and not state.observations` → 追加 `"工具（discover/execute）未执行或未取得观察"`；
  4. `not state.observations` → 追加 `"观察（observe）未入栈"`；
  5. `not state.verdict and not state.draft and not state.answer` → 追加 `"核验（verify）/阐述（answer）未执行"`。
- 副作用：无。
- 返回：`list[str]`（顺序固定：理解→决策→工具→观察→核验/阐述；全满足时为空列表）。
- 规则条目：
  - R-K-94 五条判据互不排斥，可多条并存（第 3、4 条在零观察时必然同时命中）。
  - R-K-95 新增节点须同步新增判据——穷尽性靠人工（本函数只列举五类）。
  - R-K-96 判据读的是"是否存在"而非"是否触界"，与预算闸无直接关系（供触界收敛文案用）。
- 耦合：`RunState` 七个字段（鸭子类型，无 import）；唯一调用方 `unfinished_notice`（L126）。
- 疑点：
  - D-K-50 第 3、4 条并出时文案重复表达"无工具结果/无观察"（两条同时出现于同一 notice），是否为预期未标注。
  - D-K-51 本函数未被 `unfinished_notice` 之外任何人调用，也未在 `appv2.runtime` 公开面导出——"五类未完成项"是收敛文案的唯一真源但无测试直钉（tests 面 grep 无 `unfinished_items` 引用）。
  - D-K-52 `state.rounds < 1` 与 `rounds_exhausted` 读同一字段但判据方向相反（"未执行" vs "已触界"），两处语义靠命名区分，无共享常量。

### `material_rows`（budget.py L108-L117）｜材料面单源
- 消费：`state.observations`、`state.last_result`（读 `["observations"]` 子键，缺省空列表）。
- 分支表（穷尽）：
  1. `state.last_result is not None` → 返回 `observations` ＋ `last_result.get("observations") or []` 的拼接新列表；
  2. `state.last_result is None` → 返回 `observations` 的浅拷贝。
- 副作用：无。
- 返回：`list[dict[str, Any]]`（新列表；元素为原观察字典引用）。
- 规则条目：
  - R-K-97 材料面单源：docstring 声明 `graph._converge` 的交付正文与 `unfinished_notice` 的文案分叉同判此处——"notice 与答案永不漂移"。
  - R-K-98 材料 ＝ 已入栈观察 ＋ 末次工具结果自带观察（两者相加，不去重）。
  - R-K-99 返回浅拷贝，调用方增删不影响 `state`。
- 耦合：`RunState.observations`／`RunState.last_result`；`appv2.runtime.graph` L75/L1075/L1213（交付正文与零材料分叉点）；`unfinished_notice` L128。
- 疑点：
  - D-K-53 无去重：若同一观察既已入栈又出现在 `last_result["observations"]`，将重复计入"有材料"判定（对布尔判定无碍，但调用方 graph.py L1075 直接拿 `raw` 当交付正文用，重复会进入用户可见文本）——是否可能重复取决于入栈侧（graph），本文件不设防。

### `unfinished_notice`（budget.py L120-L138）｜触界收敛 notice 装配
- 消费：`state`、`gates: list[str]`；内部调 `unfinished_items(state)`（L126）、`material_rows(state)`（L128）。
- 分支表（穷尽）：
  1. `items` 非空 → `body = "；".join(items)`；`items` 为空 → `body = "已到执行边界——按已取得材料收敛"`；
  2. `material_rows(state)` 真值非空 → `tail = "已交付已取得部分，不静默截断。"`；否则 → `tail = NO_MATERIAL_SHELL`；
  3. `gates` 直接 `'、'.join(gates)` 内插文案（空列表时产生空括号，无短路）。
- 副作用：emit 无（发帧由调用方 `deps.bus.emit("notice", dict(notice))`，graph.py L1081／L1419／L1503／L1539 等）；持久化写无。
- 返回：`dict[str, Any]`，恰三键：`{"type": "budget_converged", "gates": gates, "content": <文案>}`。
- 规则条目：
  - R-K-100 `type` 字面量＝`"budget_converged"`（机读判据）。
  - R-K-101 `gates` 原样透传（不拷贝、不改序）——与 `budget_gate_hit` 的返回同一对象引用。
  - R-K-102 `content` 形＝`"预算触界收敛（闸名顿号连接）——未完成项：{body}。{tail}"`。
  - R-K-103 零材料/有材料两态文案分叉（docstring 标注 P-006b·R2）：零材料 tail 用 `NO_MATERIAL_SHELL`，与答案侧同口径"不冒充已交付"。
  - R-K-104 `items` 全空时给中性收敛语，不出现"未完成项："后接空串的畸形（body 兜底为具体句子）。
- 耦合：`unfinished_items`、`material_rows`、`NO_MATERIAL_SHELL`；`appv2.runtime.graph` L76/L1074（并 L1081 发帧）；`appv2.runtime.__init__` 未导出 `unfinished_notice`（graph 直接 import）。
- 疑点：
  - D-K-54 `gates` 为空且 `items` 为空时仍会产出"预算触界收敛（）——未完成项：已到执行边界——按已取得材料收敛。…"的畸形组合（空括号＋空 items 兜底），本函数不校验 `gates` 非空、也不校验"未触界不应调用"——是否由调用方保证（`_gate_or_none`）未在本文件注明。
  - D-K-55 `gates` 参数按引用透传进返回字典（若调用方之后 mutate `gates`，notice 载荷随之变化）；`RunEvent` 为 frozen 但 `data` 字典可变——本文件无拷贝防护。
  - D-K-56 `type` 字面量 `"budget_converged"` 无闭世界常量（对比 `EVENT_KINDS`）——notice 的 `type` 值集合（如 `material_truncated`、本值）散在各处。
  - D-K-57 docstring 只描述两态分叉（P-006b·R2），未说明 `items` 空/非空与材料有无的四象限组合；实际分支矩阵为本文件四个组合（items×materials），文案全集只在代码里。

---

## 覆盖自检

### def/class 清单差集
无。四文件全部 `def`／`class`（含 dunder 与协议方法）已逐一成条目：
- context.py：`trust_of`、`render_materials`、`ContextBuilder`（＋常量组 6 个）。
- events.py：`RunEvent`、`RunEvent.__post_init__`、`EventBus`、`__init__`、`emit`、`close`、`closed`、`snapshot`、`stream`（＋常量组 2 个）。
- guide.py：`GuideProvider`、`GuideProvider.guide`（＋合同常量 4 个）。
- budget.py：`Budget`、`Budget.as_dict`、`now_monotonic`、`rounds_exhausted`、`time_exhausted`、`budget_gate_hit`、`unfinished_items`、`material_rows`、`unfinished_notice`（＋常量组 8 个）。
无省略；`LoopDeps` 等不在本四文件，未列。

### 四文件引用的外部符号全集（本四文件内定义的除外）

**代码引用（import 与属性访问）**
- `__future__.annotations`（四文件同）
- `dataclasses.dataclass`（context.py L15、events.py L18、budget.py L17）
- `typing.Any`（context.py L16、events.py L19、budget.py L18）
- `typing.Protocol`（guide.py L20）
- `asyncio.Queue`（events.py L16 导入、L67 构造）
- `collections.abc.AsyncIterator`（events.py L17、L93 返回标注）
- `time.monotonic`（budget.py L16、L63）
- 鸭子类型外部对象属性（`state: Any`，无 import）：`RunState.budget`、`.rounds`、`.deadline_monotonic`、`.understanding`、`.last_result`、`.observations`、`.verdict`、`.draft`、`.answer`（budget.py L68-L121）

**仓内反向消费方（本四文件被引用处）**
- context.py：`appv2.runtime.graph`（L79-L81 → `LEDGER_DICT_NOTE`／`render_materials`／`trust_of`）、`appv2.runtime.executor`（L34 → `SYSTEM_PROMPT`／`ContextBuilder`）、`appv2.runtime.__init__`（L55 → `ContextBuilder`）
- events.py：`appv2.runtime.graph`（L83、73 处 `deps.bus.emit`）、`appv2.runtime.executor`（L35 → `EVENT_BLACKBOX`／`EventBus`，L177/L209/L260/L511）、`appv2.runtime.state`（L31 → `RunEvent`）、`appv2.api.bridge`（L36、L145 → `EVENT_VERDICT`／`RunEvent`）、`appv2.api.wire`（L27-L36 → 8 个 `EVENT_*`）、`appv2.runtime.__init__`（L63-L74、L162-L170）
- guide.py：`appv2.runtime.graph`（L84-L89 → `CLARIFY_CONTRACT`／`SUMMARY_CONTRACT`／`TOOLMATCH_CONTRACT`／`GuideProvider`，消费点 L1699／L2334-L2367／L2702-L2705／L3870）、`appv2.api.ontology_guide`（L27 → `DECISION_CONTRACT`，L124 拼接）、`appv2.runtime.__init__`（L97-L102、L153-L208）
- budget.py：`appv2.runtime.graph`（L67-L76 → 五常量＋`budget_gate_hit`／`material_rows`／`unfinished_notice`／`NO_MATERIAL_SHELL`，消费点 L1080／L1105／L1217／L1690-L1693／L1859／L2146／L2335／L2431／L2631／L3108／L3522／L3658）、`appv2.runtime.executor`（L33 → `Budget`／`now_monotonic`，L246／L371）、`appv2.runtime.__init__`（L45-L52、L175）

**docstring 提及但无代码引用（供重构参照）**
- `RunHandle.stream`（events.py L9）、`specs/modules.md`、`specs/agent-loop.md`（行为约定 4／7）、`ADR-0002` 红线①、`V2-07`、`V2-54`／`V2-55`、`agent_v2_blackbox` 表
- `graph.parse_decision`（guide.py L7、budget.py L5）、`graph._converge`（budget.py L111）
- `appv2.api.ontology_guide.OntologyGuideProvider`、`GUIDE-PETRO-001`、`ontology/petro/skill-guides/`、`LoopDeps`（guide.py L6／L12-L15）、`MAX_SUBTASKS_CONTRACT`（本仓实际在 `appv2/runtime/subtask.py`，被 graph 消费）
- `infra.clock` B14（budget.py L62）、`DEFAULT_MAX_OBSERVATIONS=24` 的 V2-61 真源说明（tests/domains/test_v2_v61_material_rendering.py L3）

### 计数
- 条目数：35（context.py 9＋events.py 10＋guide.py 5＋budget.py 11）
- 规则条数：R-K-01…R-K-104（共 104 条）
- 疑点数：D-K-01…D-K-57（共 57 条）
