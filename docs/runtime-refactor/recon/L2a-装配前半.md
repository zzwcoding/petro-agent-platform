# L2a·现状调研报告

- 锚定：commit e4b75f1（行号以此为准；已核对该 commit 的 orientation.py 与工作区逐字节一致，graph.py/__init__.py 引用行号亦同）
- 覆盖：appv2/runtime/orientation.py L1-L281
- 模块职责（docstring L1-L10 概述）：LLM 触点信息装配；四要素制度（任务动词／题意锚／产出样例／失败反馈）；首轮 user 消息＝静态骨架（场景/任务/样例/红线）＋动态环境（族/水位/指标名录/术语表/本体速览）；装配规格引 tickets/v2/V2-58-理解步信息面治理.md 附 A/B

- def/class 清单（逐一全列）：
  1. `render_metric_lines` L90-L101
  2. `render_term_lines` L104-L128
  3. `render_relation_lines` L131-L140
  4. `thin_object_lines` L143-L150
  5. `iso_day` L153-L162
  6. `build_understand_instruction` L165-L196
  7. `render_decompose_example` L199-L232
  8. `assemble_understand_turn` L235-L277
  （class：0 个。附加常量：_ORIENT_SCENE L20-L26、_ORIENT_TASK L28-L44、_ORIENT_EXAMPLES L46-L74、_ORIENT_REDLINE L76-L78、FAMILY_GLOSS L81-L85。L280 注释为下段 V2-62 分节线，段内容不在本次覆盖。）

### 常量块（逐字稿）L18-L85｜结构概述（不抄正文）
- `_ORIENT_SCENE`（L20-L26）：常量——【场景】段：本环节角色（读题，管线第一环）＋后续环节序列描述＋本环节三不做。
- `_ORIENT_TASK`（L28-L44）：常量——【你的输出与它的消费方式】段：两行输出格式与各消费方（题意锚／指标白名单）＋要求行＋唯一例外（纯寒暄直答的单行形与触发条件）。
- `_ORIENT_EXAMPLES`（L46-L74）：常量——【样例】段：三个样例（多部分题／口语映射题／判断纠错题），各含问题、输出、"要点"括注行。
- `_ORIENT_REDLINE`（L76-L78）：常量——【红线】段：两句输出面约束。
- `FAMILY_GLOSS`（L81-L85）：常量——库族机器名→中文名映射字典，3 键（completion／monthly／dynamic）。

### `render_metric_lines`（file L90-L101）｜指标名录行渲染：每条指标一行「名｜单位｜状态」
- 消费：`metrics: list[dict]`，逐条读 `m["value"]`（内嵌「单位 X｜」字面）、`m["binding_state"]`、`m["slot"]`。
- 装配：产出指标行列表→由 assemble_understand_turn 包进【环境】「台账指标名录」块（每行前置两空格）。单行形「slot｜unit｜state」或省略单位段的「slot｜state」。
- 分支表（穷尽）：
  1. `value` 匹配正则 `单位 ([^｜]+)｜` → unit＝捕获组 strip → 行含单位段。
  2. 无匹配 → unit="" → 行省略单位段。
  3. `binding_state == "bound"` → state＝「可出数」。
  4. 其余一切值（unbound／None／未知） → state＝「未绑定（台账无数值——数值走报告检索）」。
  5. unit 非空 → `slot｜unit｜state`；unit 空 → `slot｜state`。
- 副作用：无
- 返回：`list[str]`
- 规则条目（一句话一条）：
  - R-L2a-01 指标行格式「slot｜单位｜状态」，单位段缺失时省略为「slot｜状态」。
  - R-L2a-02 仅 `binding_state=="bound"` 显示「可出数」，其余一切值显示「未绑定（台账无数值——数值走报告检索）」。
  - R-L2a-03 单位从 `value` 字面中正则 `单位 ([^｜]+)｜` 提取，捕获组 strip；无匹配静默留空。
- 耦合：标准库 re（L14 import）。
- 疑点（只列不判，不静默）：
  - D-L2a-01 单位提取依赖 `value` 内「单位 X｜」字面格式，格式漂移时单位静默丢失（无占位、无告警）。
  - D-L2a-02 非 bound 一切值（含 None／未知态）统一归「未绑定」文案——二值化，状态缺失与真未绑定不可区分。
  - D-L2a-03 `slot` 键缺失时 `str("")` 产出「｜单位｜状态」形空首段行，无占位文案。

### `render_term_lines`（file L104-L128）｜术语表行渲染：每条自足一行（禁用词／别名映射／纯定义）
- 消费：`terms: list[dict]`，逐条读 `t["value"]`、`t["term"]`、`t["banned"]`。
- 装配：产出术语行列表→由 assemble_understand_turn 包进【环境】「术语表」块（每行前置两空格）。定义从 `value` 的「）：」与「（时效」两标记间截取。
- 分支表（穷尽）：
  1. `banned` 为真（truthy） → 正则 `替代：([^）]+)` 取 alt（无匹配填「?」）；definition 非空 → `term＝禁用词！正确名「alt」（definition）`；空 → `term＝禁用词！正确名「alt」`；continue（不再走后续分支）。
  2. 非 banned 且 `value` 匹配 `→\s*([^·）]+)` → `term＝箭头名`。
  3. 非 banned、无箭头、definition 非空 → `term＝definition`。
  4. 全无 → 仅输出 `term`。
  5. definition 判定：`value.split("）：",1)` 后段存在 → 再 `rsplit("（时效",1)[0].strip("；。 ")`；否则 definition=""。
- 副作用：无
- 返回：`list[str]`
- 规则条目（一句话一条）：
  - R-L2a-04 禁用词固定「term＝禁用词！正确名「alt」」形；alt 取「替代：([^）]+)」，取不到填「?」；有定义时括号追加定义，无定义不追加。
  - R-L2a-05 非禁用词优先级：箭头映射（正名排除「·」「）」二字符）＞纯定义＞仅词条名。
  - R-L2a-06 定义＝`value` 在「）：」之后、「（时效」之前的片段，剥离「；。 」与空白。
- 耦合：标准库 re（L14 import）。
- 疑点（只列不判，不静默）：
  - D-L2a-04 替代名取不到时输出字面「?」——有损但不静默。
  - D-L2a-05 箭头正则排除字符表「·」「）」——正名含此二字符时截断，无告警。
  - D-L2a-06 定义提取三处失配（无「）：」／无「（时效」截断标记／两标记缺一）均静默降级（定义丢失或残文当定义），无占位。

### `render_relation_lines`（file L131-L140）｜关系行渲染：「链路（人话注解）」
- 消费：`relations: list[dict]`，逐条读 `r["value"]`。
- 装配：产出关系行列表→由 assemble_understand_turn 包进【环境】「本体速览」关系块（每行前缀「  关系：」）。value 按第一个「——」切前后：前＝链路（`replace(" ","")` 去空格），后＝括号注解。
- 分支表（穷尽）：
  1. value 含「——」 → `链路（注解）`。
  2. 不含「——」 → 仅链路（整串去空格）。
- 副作用：无
- 返回：`list[str]`
- 规则条目（一句话一条）：
  - R-L2a-07 关系行「链路（注解）」：链路名内空格剔除；无「——」时只输出链路名，注解缺失。
- 耦合：无外部符号（纯内置 str 操作）。
- 疑点（只列不判，不静默）：
  - D-L2a-07 无「——」时注解静默丢失（整串被当链路名进消息），无占位或告警。

### `thin_object_lines`（file L143-L150）｜对象薄行（回退形）：组合根未注入本体摘要时用台账 dump.objects 草案行
- 消费：`objects: list[dict]`，逐条读 `o["obj"]`、`o["value"]`（按「：」切取末段并 strip）。
- 装配：产出对象行列表→由 assemble_understand_turn 包进「本体速览」对象块（每行前置两空格）。单行形「obj：attrs」或裸 `obj`。
- 分支表（穷尽）：
  1. attrs 非空且不含子串「未列属性」 → `obj：attrs`。
  2. attrs 为空或含「未列属性」 → 仅 `obj`。
- 副作用：无
- 返回：`list[str]`
- 规则条目（一句话一条）：
  - R-L2a-08 对象行「obj：attrs」，attrs＝value 末个「：」后段；空或含「未列属性」时降为裸对象名。
- 耦合：无外部符号（纯内置 str/list 操作）。
- 疑点（只列不判，不静默）：
  - D-L2a-08 「未列属性」以子串探测 `value` 内容作语义判定——值中巧合含该串会误降裸名。

### `iso_day`（file L153-L162）｜任意水位值统一呈 ISO 日串
- 消费：`value: Any`（None／callable／date 类对象／str／其他）。
- 装配：返回 ISO 日串；被 build_understand_instruction 用于水位（L191）。
- 分支表（穷尽）：
  1. value is None → 返回 ""。
  2. callable → 调用一次；结果再 None → 返回 ""。
  3. 有 `isoformat` 属性 → 调 `iso()`。
  4. 其余 → `str(value)`。
- 副作用：callable 值会被调用（求值时机＝渲染时）。
- 返回：`str`
- 规则条目（一句话一条）：
  - R-L2a-09 None→空串；callable 先求值；有 isoformat 用之（date→ISO 日串）；其余 str。
- 耦合：无 import 依赖（对 datetime.date 属 duck-typing：只探 isoformat 属性）。
- 疑点（只列不判，不静默）：
  - D-L2a-09 callable 求值与 isoformat 调用均无异常保护——异常向上冒泡（函数自身无 try/except）。

### `build_understand_instruction`（file L165-L196）｜节点侧装配入口：从活体投影 dump 提取七路素材转交 assemble
- 消费：关键字参数 `question: str`、`dump: dict|None`、`object_lines: list|None`、`watermark_date: Any`、`today: Any`。dump 键：`objects`、`families_map`、`metrics`、`terms`、`relations`。
- 装配：不直接拼消息文本；把七路素材归一后调 `assemble_understand_turn`（L188-L196）——families＝families_map 全值的 tags 去重 sorted；watermark＝`iso_day(watermark_date) or iso_day(today)`；metric/term/relation 行＝对应渲染器；object_lines 直传或薄形回退。产物在 graph.understand 节点作为首轮 user 消息文本（graph.py L1599-L1605，经代码外部确认）。
- 分支表（穷尽）：
  1. `dump` 为 None → `{}`（空投影）。
  2. `object_lines is not None` → 用注入行（组合根本体摘要实摘要行）。
  3. `object_lines is None` → `thin_object_lines(list(dump.get("objects") or []))` 薄形回退。
  4. `families_map` 缺省/空 → families=[]（下游 assembler 落「（暂无族标注）」）。
  5. `metrics`/`terms`/`relations` 键缺省 → 空 list → 对应渲染器返回空 → 空块占位。
  6. 水位：`iso_day(watermark_date)` 非空用它；为空 → `iso_day(today)`（today 再由 assembler 的 `or` 兜底）。
- 副作用：无（纯装配；经 iso_day 可能触发 callable 求值）。
- 返回：`str`（assemble_understand_turn 的整段首轮 user 消息文本）。
- 规则条目（一句话一条）：
  - R-L2a-10 缝缺省就地兜底零漂移：dump None→空投影；object_lines None→薄形回退；水位缺省回退 today。
  - R-L2a-11 families＝families_map 全部 value（tags）并集去重后 sorted（set 推导两重 for）。
  - R-L2a-12 watermark＝iso_day(watermark_date) or iso_day(today)——两来源短路二选一。
- 耦合：本文件 render_metric_lines／render_term_lines／render_relation_lines／thin_object_lines／iso_day／assemble_understand_turn；消费方 appv2/runtime/graph.py L95（import）、L1599（understand 节点调用，传 deps.object_digests()/deps.today）；经 appv2/runtime/__init__.py L109/L225 再导出。
- 疑点（只列不判，不静默）：
  - D-L2a-10 `families_map` 的 value 假定为可迭代 tags 集合（对 None 元素或字符串 tags 无类型校验——字符串会逐字符展开）。
  - D-L2a-11 families 排序是机器名字典序（completion→dynamic→monthly），非业务序。
  - D-L2a-12 watermark_date 求值为空串时静默回退 today——两来源在产出文本中不可区分。

### `render_decompose_example`（file L199-L232）｜澄清相位分解发射填写样例（运行时现造，不进合同）
- 消费：`metrics: list[dict]`、关键字 `today: Any`（callable／date 类／str）。
- 装配：产出单串「填写样例（分解形——…）：{payload}」；payload 为手工拼接的 JSON 五键（action／question_group.subtasks[0]：id／question／ledger_notes／chain／tool）。在澄清节点拼指令时消费（graph.py L98 import、L2361 调用：锚行＋合同＋本样例＋§A＋边界句序列中）。
- 分支表（穷尽）：
  1. metrics 空 → 返回 ""（调用方跳过——degraded 面不造空样例）。
  2. 排序：`binding_state=="unbound"` 的排前（稳定排序，组内保持原序）；取 ordered[0]。
  3. 选中未绑定 → binding＝「未绑定」、chain＝"knowledge"、tool＝"doc_retrieve"。
  4. 选中非未绑定 → binding＝「在册可出数」、chain＝"data"、tool＝"data_query"。
  5. `today` callable → 调用一次。
  6. 求值后对象无 `year` 属性（str 形） → `date.fromisoformat(str(day))`。
  7. 正常 date → 窗＝`(day−30天).isoformat() ~ day.isoformat()`；payload 内 ledger_notes＝「slot｜binding｜窗」，question＝「{slot}是多少？」。
- 副作用：无（today callable 会被调用）。
- 返回：`str`（样例串；metrics 空时为 ""）。
- 规则条目（一句话一条）：
  - R-L2a-13 指标挑选：未绑定优先（稳定排序取首条）；全部非未绑定时即原序首条；空集返回空串。
  - R-L2a-14 选择未绑定 → knowledge／doc_retrieve（对应 V2-56 回炉路由动词）；否则 data／data_query。
  - R-L2a-15 payload 五键齐全：action=decompose、subtasks 单条（id=s1、question、ledger_notes、chain、tool）；ledger_notes＝「slot｜binding｜窗」；窗＝today−30 天~today。
  - R-L2a-16 today 为 callable 先求值；无 year 属性者经 `date.fromisoformat(str(day))` 转换。
- 耦合：`date`、`timedelta`（L15 from datetime import date, timedelta）；消费方 appv2/runtime/graph.py L98（import）、L2361（澄清相位指令拼接）；未进 runtime/__init__ 再导出（graph 直连）。
- 疑点（只列不判，不静默）：
  - D-L2a-13 payload 用字符串拼接拼 JSON，无转义——slot 含引号/反斜杠/换行时产出非法 JSON。
  - D-L2a-14 today 为字符串且非 ISO 形时 `date.fromisoformat` 抛 ValueError（无兜底）。
  - D-L2a-15 排序键把 `binding_state` 缺失视为非 unbound——静默走 data 链形。
  - D-L2a-16 窗固定 today−30 天（docstring 声明「近 30 天示意」）——题面真实窗词与该样例窗不一致的示范风险，靠「按窗词锚定表现算」字样提示模型，属文字约束非结构约束。

### `assemble_understand_turn`（file L235-L277）｜首轮 user 消息装配主路径：六段模板＋动态环境就地构造
- 消费：关键字参数 question／families／watermark／metric_lines／term_lines／object_lines／relation_lines（均为上游渲染产物或直量）。
- 装配：返回 `"\n\n".join([...])` 六段，顺序固定（docstring 声明＝附 B 装配顺序）：
  1. `_ORIENT_SCENE`（L20-L26，常量直引）。
  2. `_ORIENT_TASK`（L28-L44，常量直引）。
  3. `_ORIENT_EXAMPLES`（L46-L74，常量直引）。
  4. `environment`（L251-L268 就地构造）——内部顺序：①「【环境】（以下由系统按当前数据现状动态装配）」表头；②「【本系统】（事实描述——业务相关性的判断依据）」＋本系统定义与相关性口径正文（L254-L257，静态内联）；③「数据止于下方水位日。」（L258）；④「- 资料库族：{fam_line}——…」（fam_line＝`"、".join(f"{f}（{FAMILY_GLOSS.get(f,'?')}）") or "（暂无族标注）"`）；⑤「- 数据水位：{watermark or '（水位未取得）'}——…」（题面时间词锚）；⑥「 - 台账指标名录（N 条…）：」＋metric_block（每行前两空格，空则「  （空）」）；⑦「 - 术语表（N 条…）：」＋term_block（同上）；⑧「 - 本体速览（…）：」＋「  对象：」＋object_block（每行前两空格）＋relation_block（每行前缀「  关系：」，空则「  关系：（空）」）。
  5. `_ORIENT_REDLINE`（L76-L78，常量直引）。
  6. 题干段（L275-L276）：`【待解构的题干】\n{question}\n（先判与业务的相关性：可能有关＝两行式；确定无关的寒暄闲聊＝直答。现在输出。）`——题干置末、紧邻生成点。
- 分支表（穷尽）：
  1. families 为空 → fam_line＝「（暂无族标注）」。
  2. 族名不在 FAMILY_GLOSS → 中文名位落「?」。
  3. metric_lines 空 → metric_block＝「  （空）」且块头计数为 0。
  4. term_lines 空 → term_block＝「  （空）」。
  5. object_lines 空 → object_block＝「  （空）」。
  6. relation_lines 空 → relation_block＝「  关系：（空）」。
  7. watermark 为空串或 None（falsy） → 「（水位未取得）」。
- 副作用：无
- 返回：`str`（六段整文本＝首轮 user 消息）。
- 规则条目（一句话一条）：
  - R-L2a-17 段序固定：场景→任务→样例→环境→红线→题干（题干置末），段间以「\n\n」连接。
  - R-L2a-18 环境段块序：表头→本系统定义→清单指引（含"数据止于下方水位日"）→资料库族→数据水位→指标名录→术语表→本体速览（对象＋关系）。
  - R-L2a-19 空块占位文案：族「（暂无族标注）」；指标／术语／对象「  （空）」；关系「  关系：（空）」；水位「（水位未取得）」。
  - R-L2a-20 族名显示形「机器名（中文释义）」，FAMILY_GLOSS 缺键落「?」。
  - R-L2a-21 动态行缩进：指标／术语／对象行前置两空格；关系行前缀「  关系：」；指标名录与术语表块头内置条数计数。
  - R-L2a-22 题干段末尾附收束句（相关性判定口径＋"现在输出"）。
- 耦合：本文件 FAMILY_GLOSS、_ORIENT_SCENE／_ORIENT_TASK／_ORIENT_EXAMPLES／_ORIENT_REDLINE；被 build_understand_instruction（L188）消费；经 appv2/runtime/__init__.py L108/L224 再导出。
- 疑点（只列不判，不静默）：
  - D-L2a-17 FAMILY_GLOSS 三键固定，新增族机器名落「?」——静默降级，无告警通道。
  - D-L2a-18 环境段静态文字（【环境】表头、【本系统】正文、清单指引、"数据止于下方水位日"句）内联函数体，不在常量块——模块 docstring 声明的「静态骨架＝本模块常量」边界不含它们，改措辞需动函数体。
  - D-L2a-19 块前导不一致：资料库族／数据水位行「- 」无前导空格，指标名录／术语表／本体速览行「 - 」有前导空格——同一环境段两种缩进风格。
  - D-L2a-20 例外/直答口径在两处文本面重复（`_ORIENT_TASK` 的「唯一例外」段与题干段收束句）——改一侧需同步另一侧，现无机器闸看守此一致性。
  - D-L2a-21 watermark 参数签名声明为 str，但调用链上游 iso_day 对 None 返回空串——「（水位未取得）」兜底依赖 `or` 短路而非类型约束。

## 覆盖自检
- def/class 清单差集：无。L1-L281 内 def 共 8 个（L90／L104／L131／L143／L153／L165／L199／L235），class 0 个，全部逐一覆盖；模块 docstring L1-L10、import L12-L16、常量区 L18-L85、分节注释 L88／L280 均已说明。L282 起的 `_ANSWER_REQUIREMENTS` 属 V2-62 下段，不在本次覆盖。
- 引用的外部符号全集（本文件内定义的除外）：
  - 代码引用（import 级）：`re.search`（L14）；`date.fromisoformat`、`timedelta`（L15）；`Any`（L16）。
  - 代码引用（内置，无 import）：sorted、len、str、list、dict、callable、getattr、hasattr。
  - 仓内消费方（锚定 commit 行号）：appv2/runtime/graph.py L95（import build_understand_instruction）、L98（import render_decompose_example）、L1599-L1605（build_understand_instruction 调用——understand 节点首轮消息，入参含 deps.object_digests()/deps.today）；appv2/runtime/__init__.py L108-L114（import 再导出，含 assemble_understand_turn／build_understand_instruction／iso_day／render_metric_lines／render_relation_lines／render_term_lines／thin_object_lines；**不含 render_decompose_example**）、L224／L225／L230／L236／L237／L238／L241（__all__ 条目）。FAMILY_GLOSS 无本文件外引用（已全仓 grep 确认）。
  - 文档字符串提及（非代码引用，列明防误判依赖）：deps.today、deps.object_digests（组合根注入）、graph.understand、tickets/v2/V2-58-理解步信息面治理.md 附 A/B。
