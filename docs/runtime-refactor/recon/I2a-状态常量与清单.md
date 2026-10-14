# I2a·现状调研报告

- 锚定：commit e4b75f1（行号以此为准）
- 覆盖：appv2/runtime/state.py L1-L101
- 取证口径：消费方＝锚定 commit 上 `git grep` 取证（行号即该 commit 行号）；注释可读处直引，不臆测。
- def/class 清单：逐一全列（含行号区间），不得省略
  1. `Manifest`（L70-L98：装饰器 L70、class 行 L71、docstring L72、字段 L74-84、方法 L86-98）——本段唯一 class（模板标注 L71-L100；L99-L100 为空行）
  2. `Manifest.as_dict`（L86-L98）——本段唯一 def（方法；段内无模块级函数）
  - 段内其它行：文件头 docstring L1-L22、imports L24-L31、常量族 L33-L67、边界行 L101（AskRequest 的 @dataclass 装饰器行；`class AskRequest` 主体 L102 起出段）
  - 头 docstring 点名的 RunState／AskRequest／AskChoice／RunHandle 四符号主体均在段外（L102 起）。

---

## 一、常量清单（全量逐条）

三块注释分组：L33 step 族、L45 run 族、L55＋L63-64 路由意图族；共 22 条。

| 常量名 | 值 | 注释语义 | 消费方（注释或本文件可见则写） |
|---|---|---|---|
| STEP_DECISION | "decision" | L33 组注「step 类型六值闭世界（ReAct 周期——wire 演进后只许六种）」；docstring L8-10 轮＝LLM 决策周期 | graph.py L112 导入；步记录 20+ 处（L1422、L1506、L1541、L1624、L1740、L1777、L1811、L1934、L2017、L2453、L2493、L2531、L2551、L2579、L2748、L2804、L2999 等）；__init__ 转出 L126/186 |
| STEP_DISCOVER | "discover" | 同 L33 组注；docstring L10 discover/execute＝固定代码执行的工具步 | graph.py L113 导入、L2198 步记录、L2109（kind==STEP_DISCOVER 判意图）；__init__ L127/187 |
| STEP_EXECUTE | "execute" | 同 L33 组注（工具步） | graph.py L114 导入、L2261、L3332/L3335；__init__ L128/188 |
| STEP_OBSERVE | "observe" | 同 L33 组注 | graph.py L115 导入、L3495/L3497、L3573/L3596；__init__ L130/190 |
| STEP_VERIFY | "verify" | 同 L33 组注；docstring L10 verify 保留零 LLM | graph.py L116 导入、L3681、L3726；__init__ L131/191 |
| STEP_ANSWER | "answer" | 同 L33 组注 | graph.py L111 导入、L3768/L3797、L3961/L3976；__init__ L125/185 |
| STEP_KINDS | frozenset{六值} | 六值闭世界全量集（L41-43） | 仅 __init__ L129/189 转出；仓内无校验消费点（grep——见 D-I2a-03） |
| RUN_RUNNING | "running" | L45 组注「run 状态机（行为约定 8：running→waiting_ask→（resume）→终态）」 | 本文件 L146（RunState.status 默认）；executor.py L41/L382；__init__ L122/182 |
| RUN_WAITING_ASK | "waiting_ask" | 同 L45 组注（挂起态） | executor.py L42/L214/L431；__init__ L124/184；api/chat.py L310 用裸字面量（见 D-I2a-04） |
| RUN_COMPLETED | "completed" | 同 L45 组注（终态） | executor.py L39/L283（追问前轮须 completed）/L456；__init__ L120/180 |
| RUN_FAILED | "failed" | 同 L45 组注（终态） | executor.py L40/L441/L473；__init__ L121/181 |
| RUN_STATUS_KINDS | frozenset{四值} | 四态闭世界全量集（L51-53） | 仅 __init__ L123/183 转出；无消费点（grep——D-I2a-03；store 自建把守见 D-I2a-04） |
| INTENT_DECISION | "decision" | L55「节点间显式路由意图（next_intent 闭世界——条件边唯一判据）」；L63-64 clarify 沿用本值承载 | graph.py L103 导入；产者 20+ 处（L1649、L1758、L1808、L1880、L1910、L1994、L2083、L2100、L2163、L2249、L2474、L2547、L2600、L2671、L2697、L2854、L3124、L3130、L3241、L3514、L3538、L3545、L3604）；路由表 L3994/L3999/L4008/L4015/L4022 与 L4075；未入 __init__ 导出（D-I2a-05） |
| INTENT_DISCOVER | "discover" | 同 L55 | graph.py L104 导入；产者 L1842/L2567/L3600；路由表 L4000/L4007/L4020/L4079 |
| INTENT_EXECUTE | "execute" | 同 L55 | graph.py L106 导入；产者 L1852/L1996/L3602；路由表 L4001/L4014/L4021 |
| INTENT_OBSERVE | "observe" | 同 L55 | graph.py L107 导入；产者 L2072；路由表 L4006/L4013 |
| INTENT_VERIFY | "verify" | 同 L55 | graph.py L110 导入；产者 L3979/L3983；路由表 L4028 |
| INTENT_ANSWER | "answer" | 同 L55 | graph.py L101 导入；产者 L1088/L1207/L1883/L2626/L3145/L3547/L3728；路由表 L3995/L4002/L4009/L4016/L4023/L4026/L4029/L4086/L4092/L4098/L4103；缺省回退 L4036（`_route`：`state.next_intent or INTENT_ANSWER`） |
| INTENT_END | "end" | 同 L55（收敛路由终点） | graph.py L105 导入；产者 L3799/L3808；路由表 L3996/L4003/L4010/L4017/L4024/L4026/L4030/L4087/L4093/L4099/L4104 |
| INTENT_TOOLMATCH | "toolmatch" | L63-64「V2-34 四相位路由意图（clarify 经既有 INTENT_DECISION 值承载……三相新意图随本票加入闭世界）」 | __init__ L119/173；graph.py L109 导入；产者 L2515/L2767；路由表 L4080/L4090 |
| INTENT_PRECONDITION | "precondition" | 同 L63-64（相位③） | __init__ L118/172；graph.py L108 导入；产者 L1965/L2838；路由表 L4085/L4091 |
| INTENT_BATCH | "batch" | 同 L63-64（相位④） | __init__ L117/171；graph.py L102 导入；产者 L3104/L3147；路由表 L4096 |

---

## 二、Manifest 类

### `Manifest`（L71-L100）｜模型调用 Manifest：随模型调用步存档的过程态簿记（docstring L72「行为约定 2」）

- 范围注：本段无其它 class/def，R-/D- 编号在本节承载全段（L1-L101，含常量族）条目。

- 字段表（10 字段，穷尽）：

| 字段名 | 类型/默认值 | 语义 |
|---|---|---|
| source_type | list[str]＝field(default_factory=list) | 合同七字段之一（specs/agent-loop.md 行为约定 2 合同形；本文件无逐字注释，键名即义） |
| source_id | list[str]＝field(default_factory=list) | 同上 |
| version | list[str \| None]＝field(default_factory=list) | 同上（元素可为 None 表无版本） |
| trust_level | list[str]＝field(default_factory=list) | 同上 |
| selected_reason | str＝"" | 同上 |
| token_count | int＝0 | 同上 |
| transform | str＝"filter→rank→budget→cite" | 同上（默认值＝四段变换链字面量，无注释展开） |
| material_total | int＝0（L82 行注） | 渲染候选总数（非 notice；零材料步＝0）——V2-61 材料承载分形记账三机检字段之一 |
| material_rendered | int＝0（L83 行注） | 实渲染支数（权威全量＋检索帽内） |
| material_truncated | bool＝False（L84 行注） | 检索片段帽触发（截断态＝True） |

- 分支表（as_dict 等，穷尽）：
  1. 无条件（L87-98 唯一 return）→ 返回 10 键 dict（键名与字段同名）：前四列表键经 `list()` 拷贝，后六键直引 → 去向：调用方序列化（现存预期唯一消费点 graph.py `_step_record` L1063 的 `manifest` 键；生产实参恒 None——见 D-I2a-02）
  - 除 as_dict 外本类无其它方法（无 `__post_init__`／校验／工厂）。

- 规则条目：
  - R-I2a-01 step 类型六值闭世界（L33）：合法值＝decision／discover／execute／observe／verify／answer 六种，STEP_KINDS 即全量集；「wire 演进后只许六种」。
  - R-I2a-02 run 状态四态闭世界（L45 组注，行为约定 8）：running→waiting_ask→（resume）→终态；RUN_STATUS_KINDS 即全量集（running／waiting_ask／completed／failed）。
  - R-I2a-03 路由意图十值闭世界（L55）：INTENT_* 十值＝next_intent 合法域，条件边唯一判据。
  - R-I2a-04 clarify 复用 decision 值（L63-64，V2-34）：四相位不新增 clarify 意图——沿用 INTENT_DECISION，图装配按 four_phase 把该值重定向 clarify 节点；toolmatch／precondition／batch 三值随本票入闭世界。
  - R-I2a-05 Manifest 无参可构造：七合同字段全带缺省（列表 default_factory=list；selected_reason ""；token_count 0；transform "filter→rank→budget→cite"）——`Manifest()` 合法（tests/domains/test_v2_v61_material_rendering.py L146 实证）。
  - R-I2a-06 材料三机检字段默认零（L81-84，V2-61）：material_total＝0、material_rendered＝0、material_truncated＝False；口径「零材料步＝0」「截断态＝True」。
  - R-I2a-07 as_dict 全键恒出：10 键＝10 字段同名投影，列表字段 `list()` 拷贝、标量直引，无裁剪分支（L87-98 唯一 return）。
  - R-I2a-08 冻结＋JSON 原语投影（L70 frozen/slots；docstring L21）：字段值全部 JSON 原语可投影，checkpointer 序列化面最简；零框架依赖。

- 疑点：
  - D-I2a-01 头 docstring L18-19 仍称「Manifest 七字段」，类体 V2-61 后实为十字段（L81-84 增三机检字段）——头清单未随票更新；是否刻意保留「合同七字段」表述未注。
  - D-I2a-02 Manifest 生产面零构造零消费：全仓 `Manifest(` 仅 tests/domains/test_v2_v61_material_rendering.py L146 与 V2-61 票面文档命中；graph.py `_step_record`（L1051-1065）26 处调用点第 4 实参逐点核证全部传 None——「manifest」键在生产 step 记录恒 null，as_dict 生产路径不可达；该类是否为退役面未标注。
  - D-I2a-03 两个 frozenset 常量无消费点：STEP_KINDS／RUN_STATUS_KINDS 全仓仅 __init__ L129/189、L123/183 转出；tests 用自建 HAPPY_STEP_KINDS 列表（tests/api/test_v2_asks.py L83、tests/domains/test_v2_agent_loop.py L89），未复用本常量（grep 取证）。
  - D-I2a-04 闭世界校验与实际把守不同源：store.py 自建 `_TERMINABLE = frozenset({"waiting_ask", "completed", "failed"})`（L34），转移把守用裸字面量（L176-177、L200-204）；api/chat.py L310 亦用裸字面量 "waiting_ask"（chat.py 未 import RUN_*，L41 只 import AskChoice/AskRequest）——同一取值多处写法，未统一到 state 常量。
  - D-I2a-05 导出面缺口：INTENT_* 七值（decision／discover／execute／observe／verify／answer／end）未入 runtime/__init__ 的 __all__（L171-173 只三相位意图），而 graph.py 直接 `from appv2.runtime.state import` 取用（L100-110）——是否有意收敛未注。
  - D-I2a-06 同名同值异构面：STEP_×6 与 INTENT_×6 值一一重复（decision／discover／execute／observe／verify／answer 各两份定义）；INTENT 族多 end／toolmatch／precondition／batch 四值、STEP 族无对应——两族是否须同步演进无注释约束。
  - D-I2a-07 as_dict 拷贝语义无注释：前四列表键 `list()` 浅拷贝、后六键（str/int/bool，不可变）直引——拷贝是防调用方改原列表还是无意义写法，未注。

---

## 覆盖自检

- 常量总数：22（表内 22 条，逐条对账一致）：STEP_×6＋STEP_KINDS×1；RUN_×4＋RUN_STATUS_KINDS×1；INTENT_×10（ReAct 六＋END＋三相三）
- 规则数：8（R-I2a-01..08）；疑点数：7（D-I2a-01..07）
- def/class：class 1（Manifest L70-L98）＋def 1（as_dict L86-L98）；段内无模块级 def、无其它 class
- 引用的外部符号全集（本文件内定义的除外）：
  - import 面：AsyncIterator（collections.abc，L26）、dataclass／field（dataclasses，L27）、Any（typing，L28）、Actor（appv2.infra.security，L30）、RunEvent（appv2.runtime.events，L31）——Actor／RunEvent 在本段内未被使用（服务于段外 L102+ 类）
  - 内建／字面量：frozenset（L41/L51 注解）、list／dict／str／int／bool（字段与返回类型）、字符串字面量 "filter→rank→budget→cite"（L80）
  - 文档引用（非代码符号）：ADR-0002（L1）、specs/agent-loop.md 行为约定 2／行为约定 8／接口定义节（L15、L19、L45）、票号 V2-31（L8）／V2-34（L63）／V2-61（L81）
- 消费方取证涉及的外部文件（仅证据来源，非本段引用）：appv2/runtime/__init__.py、appv2/runtime/graph.py、appv2/runtime/executor.py、appv2/runtime/store.py、appv2/api/chat.py、tests/domains/test_v2_v61_material_rendering.py
