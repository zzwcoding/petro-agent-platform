# RT-W4-03 · tool_matching——V2 工具匹配

状态: **草案（待主窗 manifest 对账后派工）** ｜ 所属规格: `specs/tool_matching.md`（状态「已定稿」——前置满足）
Touches modules: `tool_matching`（本票只建 tool_matching 本体；规格「触及的模块」表另声明 parsing／prompts／bookkeeping／gateway_adapter／state 五关联侧归各自票承接，`tools` 侧只做**工具描述文本写全**——本块唯一触及 runtimev2 之外的地方，改动限描述文本、不动公开接口签名）
波次: W4（`docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二 W4 行原文：「七个业务相位（understanding → clarification → tool_matching → preconditions → execution → answering → verification）」｜「互零依赖，**建议按业务链序施工**（便于走查 narrative 与测试网逐块加厚），不禁止并行」；本波出口判据「每相位配属规格十节版式定稿＋新规格钉绿＋触及该相位的特征钉绿」；本块＝链序第 3 位（前位 clarification、后位 preconditions））
复审强度: 50% 抽查（eng/03 §五 流水 48 规则：非质量关键块抽 50%；本块在 §五 表 W4 行非关键列「understanding／clarification／tool_matching／execution」侧）
前置: ① 规格定稿（`specs/tool_matching.md` 已定稿——已满足）；② 波次前置：**W1–W3 全收波**（本票依赖 `state` W1；`parsing`／`prompts`／`gateway_adapter` 替身 W2；`bookkeeping.call_model` 单点发起面 W3）；③ 链序前置（eng/03 §二 W4 行「**建议**按业务链序施工」）：前位 understanding／clarification 收票——**仅链序建议，非 import 依赖**（R1 相位互不 import；跨相位消费只经 `state` 形状）
阻塞: W3 收波（`bookkeeping` 单写口＝模型调用发起面）；链序前位 understanding／clarification 收票（建议序）｜被阻塞: RT-W4-04-preconditions（消费本块产出的「提及 vs 执行」结论／口径归一结果／时间窗结论——经 `state` 形状承载，见「接口缺口」条）；W5 `orchestration`（拒因回喂与相位路由的驱动方）

## 任务

按 `specs/tool_matching.md` 新建 `appv2/runtimev2/tool_matching/`：给每个子问题配上**恰好一个**工具／路线，并把参数校验到**可执行**——**模型提议，程序做闭世界对账**（程序只做存在性／一致性／枚举三类结构判定，不替模型选工具）；失败一律带**结构化拒因**回喂模型重配，不自动修补；本块与 `caliber_key` 同批产出「提及 vs 执行」结论，交 `preconditions` 判定序第 1 位做机械分派。

> 逐字稿载体（AGENTS.md 6b）：本票「票面对象」「测试网钉」「织网义务」三节的每一行均为所引规格／eng 文档表行**原文照抄**（无改写、无增删、无换述）；施工子代理对逐字稿只许照抄，偏离即停报 L0，不自行裁量。

先读: （6 份，小票制上限）`specs/tool_matching.md` 全文（十节版式）；`specs/modules.md` `## tool_matching` 卡（签名以卡为准）＋`## 边界规则`（R1／R2／R5b／R6／R7）；`specs/query.md`（`QueryPlan` **真源**——体字段只引不复述）；`specs/tools.md`（工具注册表公开面＋`ToolDescriptor.description` 三件套真源＝其行为 6）；`docs/runtime-refactor/eng/04a-应钉行为清单.md`（pin-31 行＋末「使用规则」行）；`docs/runtime-refactor/eng/04-测试网设计.md` §三／§五／§六（本块无明写行，见「织网义务」节归块注）。AGENTS.md 硬纪律 6b 为常驻纪律（本票已逐字引在「逐字稿载体」条）。

**小票制自检（流水 48）**：票面对象 15 行 ≤ 15 ✓；先读 6 份 ≤ 6 ✓；聚焦一个行为簇＝「提议→闭世界对账→结构化拒因」单链（本块单一入口 `match`）✓ → **本票不拆**（无 -A／-B 派生票）。eng/03 §二 的波序、§五 的复审强度已逐字引在票头，施工子代理**不必再读 eng/03**。

**接口缺口（施工前须 L0 裁，勿自造）**：① 规格「接口定义」节 `specs/tool_matching.md:73` 原文「**本块亦产出「提及 vs 执行」的结论**（废弃词闸的判断；Owner 裁决 #12）——**与 `caliber_key` 同批产出**，交 `preconditions` 判定序第 1 位做机械分派」＋「测试网钉」节所引挂钩表 **pin-31 行** `specs/tool_matching.md:164` 原文「产出「提及 vs 执行」结论（废弃词闸的判断；与 `caliber_key` 同批产出）｜钉 **`pin-31`**｜待织网（阶段 5）」——两处要求本块产出「提及 vs 执行」结论、pin-31／pin-14 要求 `preconditions` 消费其**时间窗结论**，但 `specs/modules.md` `## tool_matching` 卡与规格「接口定义」的 `SubtaskMatch` **未列「时间窗结论」的字段**（名字／类型／承载物未定）；② 规格 `class MatchReason:` 拒因枚举的**字段面与成员名**（原正文为 `...`）。施工子代理**不得自造字段名**——遇此停报 L0，待主窗裁后回写卡面再施工（本项与 RT-W4-04 的消费面同批裁）。
（**勘误与现状注 2026-10-16（流水 50／51，逐字对照见 `docs/runtime-refactor/spec-review/tool_matching-回工补写.md` 末节）**：原票面本行①误指「**规格行为 11 行**要求本块产出「提及 vs 执行」结论」——实读不符：行为 11（`specs/tool_matching.md:112`）是「解析拒文→结构化拒因的转换归本块」，与「提及 vs 执行」无关；真实落点＝上引「接口定义」节 `:73` ＋ pin-31 行 `:164`，本行已按落点改写。**字段面现状**：①的「提及 vs 执行」字段载体 `mention_mode` 已随流水 50 回写（卡 `specs/modules.md:178-179`／规格 `:56`／`:75`）——**仅剩**pin-14 的**时间窗结论**字段未定；②已随流水 50／51 落（`specs/tool_matching.md:65-67` 给 `kind`／`reason`，枚举**六类**＝五类＋第六类 `malformed_matches`），其卡面同批同改。）

框架红线: **无点名框架**（本模块不引入任何框架）——对应闸 R5b 契约（specs/tool_matching.md「框架与依赖红线」首条）
边界红线: ① **不直引模型出口**：模型调用发起面＝`bookkeeping.call_model`（单点发起；import 落点＝`appv2.runtimev2.bookkeeping` **包根**——R2 禁深层子模块），本块**不直引** `gateway_adapter`、不直引 `appv2.infra.llm_client`——**R7**；② 不得直接 import `langgraph`／`langchain`——**R5b**；③ 只经 `tools` 公开面接触世界（不直引 knowledge／query／retrieval 引擎）——**R6**；④ 相位互不 import（R1）＋公共层块只经包根（R2）；⑤ **禁手写替代**：不得自建模型客户端／自建工具目录、不得绕过 `call_model` 直发模型调用——验收写法＝「无旁路」行为断言（R7＋R6）；⑥ **不直写状态**：本块只产信号值（拒因字段／notice 类型），step payload 与 notice 的**写入**归 W3 `bookkeeping` 单写口（其行为 1「相位不得直写」＋测试 `::no_direct_state_write_in_phases`）——本块测试经写口断言（`::rejection_signal_present`）；⑦ 不引旧码 `appv2.runtime`（R5）

## 票面对象（specs/tool_matching.md「验收测试」表逐行转抄，15 行）

〔来源：specs/tool_matching.md「验收测试」表 :124–:137（前 14 行，逐行原文）＋ :138（第 15 行，本批补抄——见行尾注）；「规格行」列＝该行 file:line 来源注，非规格原文。**行号回填 2026-10-16**：原 :107–:120，随流水 50／51 两次改批漂移后为 :124–:137（各行 +17）。〕

| # | 验收标准（原文） | 对应测试（原文标识） | 规格行 |
|---|---|---|---|
| 1 | 子问题恰配一条；漏配 → 判失败带结构化拒因 | `tests/domains/test_v2_tool_matching.py::exactly_one_match_per_subtask` | specs/tool_matching.md:124 |
| 2 | 多配／编号对不上 → 判失败 | `tests/domains/test_v2_tool_matching.py::duplicate_or_unknown_id_rejected` | specs/tool_matching.md:125 |
| 3 | 工具名不在注册表名单 → 判失败（闭世界） | `tests/domains/test_v2_tool_matching.py::tool_name_closed_world` | specs/tool_matching.md:126 |
| 4 | `chain="data"` 缺 `plan` ／ `chain="knowledge"` 缺 `retrieval_need` → 判失败 | `tests/domains/test_v2_tool_matching.py::required_by_chain` | specs/tool_matching.md:127 |
| 5 | `metric_slot` 为空，或呈英文列名**形态**（形态判定；判定形＝ASCII 标识符形——首字符 `[A-Za-z]`、其余仅 `[A-Za-z0-9_]`，大小写都咬；Owner 2026-10-15 拍板 B 案，判定形见行为 4）→ 判失败 | `tests/domains/test_v2_tool_matching.py::metric_slot_not_english_column` | specs/tool_matching.md:128 |
| 6 | `ranking` 与 `direction` 同现约束 | `tests/domains/test_v2_tool_matching.py::ranking_direction_paired` | specs/tool_matching.md:129 |
| 7 | 旧名经账本归一后才出数（出数只认现行口径） | `tests/domains/test_v2_tool_matching.py::legacy_name_normalized_before_query` | specs/tool_matching.md:130 |
| 8 | 解析拒文（parsing `str`）→ `ToolMatchRejection` 结构化转换归本块（消费方）：机械适配（str 逐字进 `reason` 字段＋映射拒因枚举）、零语义判断（行为 11） | `tests/domains/test_v2_tool_matching.py::parse_rejection_str_to_tool_match_rejection_consumer_side` | specs/tool_matching.md:131 |
| 9 | 每个工具描述含「何时用／不能做什么／参数示例」三项（**经 tools seam 测**；本块只消费其公开面） | `tests/domains/test_v2_tool_matching.py::descriptor_covers_three_parts` | specs/tool_matching.md:132 |
| 10 | 程序只对账、不替模型选工具（AST 扫描本模块；**豁免面＝结构归一／形态处理**，如去装饰符号、token 包含匹配，**不算语义词表**） | `tests/domains/test_v2_tool_matching.py::no_lexicon_or_regex_in_tool_matching` | specs/tool_matching.md:133 |
| 11 | 失败与拒因的机读信号在场（step payload ＋ notice） | `tests/domains/test_v2_tool_matching.py::rejection_signal_present` | specs/tool_matching.md:134 |
| 12 | 【边界集】`chain`／`direction` 越界取值 → 判失败 | `tests/domains/test_v2_tool_matching.py::boundary_enum_out_of_range` | specs/tool_matching.md:135 |
| 13 | 【保留集】名归一闸行为不变（本块） | `tests/domains/test_v2_tool_matching.py::retention_normalize` | specs/tool_matching.md:136 |
| 14 | 【保留集】聚合下推行为不变（归属 `execution`） | `tests/domains/test_v2_tool_matching.py::retention_pushdown` | specs/tool_matching.md:137 |
| 15 | `SubtaskMatch.mention_mode` 取值闭世界（`executed`／`mentioned_only`）越界即拒 | `tests/domains/test_v2_tool_matching.py::mention_mode_closed_world` | specs/tool_matching.md:138 |

> 第 15 行系**本批补抄**（2026-10-16，流水 51 收尾一致）：来源＝`specs/tool_matching.md:138`——该规格「验收测试」表末行原文照转（其原注「增行＝流水 51 收尾一致」），随规格行为 5「枚举闭世界」补 `mention_mode` 成员（`2026-10-16 补（流水 51）`）同批增；**票面对象 15 行 ＝ 小票制上限，仍 ≤ 15 ✓**。
> 测试文件归属（spec 未另附节尾原注，按规格「验收测试」表首列原标识照抄）：本块验收测试绑**新建** `tests/domains/test_v2_tool_matching.py`（15 行测试标识同文件、同模块名）；旧码测试本批不改。第 14 行「【保留集】聚合下推行为不变」的**归属 `execution`**——本块只按规格原文登记该行，其实现落点在 `execution` 票（施工时若该用例不在本文件可落，停报 L0 由主窗切分）。
> 第 9 行跨 `tools` seam：`::descriptor_covers_three_parts` 与 `specs/tools.md` 行为 6 为同一判据的两侧（本块只消费公开面；`tools` 侧描述文本改动的对账归 RT-W2 之外的 tools 票／阶段 7 体检，见「依赖与风险」2）。

## 测试网钉（specs/tool_matching.md「与闸的挂钩表」pin 行逐行转抄，1 行）

〔来源：specs/tool_matching.md「与闸的挂钩表」:164（原 :144，随流水 50／51 两次改批漂移 +20），逐行原文〕

1. **pin-31（P1，判半边的产出面）**｜产出「提及 vs 执行」结论（废弃词闸的判断；与 `caliber_key` 同批产出）｜钉 **`pin-31`**｜现状：待织网（阶段 5）

- 本规格「与闸的挂钩表」共 11 行，**仅上列 1 行为 pin 行**（其余为 spec gate／边界闸 R5b／R6／R7／测试／人审行——见「验收」节逐条）。
- pin-31 是**双落点钉**：**判断产出面**＝本块（模型在配工具那次调用产出「提及 vs 执行」结论，`eng/04a` pin-31 原文「提及 vs 执行由**模型**在配工具那次调用产出」）；**机械分派面**＝`preconditions` 判定序第 1 位（RT-W4-04「测试网钉」第 1 行）。本块只承担**判断产出面**，不重复挂分派面。
- pin-31 的字段载体＝**`SubtaskMatch.mention_mode`**（取值闭世界 `executed`／`mentioned_only`）——已随流水 50 回写卡与规格「接口定义」节（`specs/modules.md:178-179`；`specs/tool_matching.md:56`＋`:75`），**字段名不再属接口缺口**；「任务」节「接口缺口」①的**未清项只剩 pin-14 的时间窗结论字段**（见该节 2026-10-16 现状注）。

## 施工要点（specs/tool_matching.md「行为约定」节骨架——file:line 锚＋一句话）

| 锚 | 条目 | 一句话 |
|---|---|---|
| specs/tool_matching.md:102 | 行为 1 模型只提议 | 子问题 → 工具 ＋ 参数由模型给；程序做**闭世界对账**，不替模型选工具 |
| specs/tool_matching.md:103 | 行为 2 恰配一条 | 每个子问题**恰好一条**匹配；**漏配／多配／编号对不上**任一 → 判失败 |
| specs/tool_matching.md:104 | 行为 3 拒因回喂、不自动修补 | 失败一律带**结构化拒因**回喂模型重配；程序不补齐、不猜 |
| specs/tool_matching.md:105 | 行为 4 参数强校验（含判定形，Owner 拍板项） | `chain="data"`→`plan` 必填；`chain="knowledge"`→`retrieval_need` 必填；`metric_slot` 必填非空且不得为英文列名形（**判定形**＝值整体呈 ASCII 标识符形——首字符 `[A-Za-z]`、其余仅 `[A-Za-z0-9_]`，大小写都咬；Owner 2026-10-15 拍板 B 案 fail-closed：宁可误拒重提议，不可漏放列名形；禁例 `oil_pressure`／`WELL_NAME`）；`ranking` 必填布尔且与 `direction` 同现；`caliber_key` **由本块产出** |
| specs/tool_matching.md:106 | 行为 5 枚举闭世界 | `chain`（`data`｜`knowledge`）、`direction`（`asc`｜`desc`）、`tool`（注册表名单）、`mention_mode`（`executed`｜`mentioned_only`——**2026-10-16 补（流水 51）**）——越界值判失败 |
| specs/tool_matching.md:107 | 行为 6 工具描述写全 | 载体＝`ToolDescriptor.description`，必须含**何时用／不能做什么／参数示例**三项——选得准的**第一因**，**不加额外选型规则** |
| specs/tool_matching.md:108 | 行为 7 出数只认现行口径 | `metric_slot` 到查询引擎前只认现行名；**模型产出归一后的名字**，账本只提供 alias↔canonical 的**「结构映射」**（不替模型做语义判断） |
| specs/tool_matching.md:109 | 行为 8 不做主动发现 | 不引入检索式选工具／工具主动发现设施（工具集小） |
| specs/tool_matching.md:110 | 行为 9 熔断暂不加 | 拒因回喂自环靠**轮数闸**兜底；轮数等限额**引限额真源双指**（`walk/裁决表.md` §06-A ＋ `recon/K-上下文事件指南预算.md` R-K-72…R-K-78，轮数＝R-K-72）——**本规格不写字面值** |
| specs/tool_matching.md:111 | 行为 10 名归一闸保留 | 精确键未命中时按名归一扫描（真源 `walk/11-匹配-工具阀.md` §一） |
| specs/tool_matching.md:112 | 行为 11 解析拒文→结构化拒因（消费方） | parsing 的 `str` 拒文 → `ToolMatchRejection` 机械适配（`str` 逐字进 `reason` ＋映射拒因枚举）、零语义判断；parsing 不感知本块类型（R3） |

结构锚（**行号回填 2026-10-16**：原 :41–73／:75–81／:97–101，随流水 50／51 两次改批漂移后如下；:13–27／:29–39 两段未漂移）：specs/tool_matching.md:13–27 「不做什么」表（10 行纯范围排除——不查数／不主动发现等走**人审**，锚＝其挂钩表末行）；:29–39 触及的模块（`tools` 侧＝**工具描述写全**，本块唯一触及 runtimev2 之外的地方）；:41–90 接口定义（`match`／`ToolPlan`／`SubtaskMatch`／`RetrievalNeed`／`ToolMatchRejection`／`MatchReason`；`QueryPlan` 真源＝`specs/query.md`，本块只引不复述；`tool` 与 `chain` 双闭世界、越界判失败；`SubtaskMatch.mention_mode` 闭世界两值（`:56` 字段＋`:75` 说明）；错误契约＝拒因枚举**六类**（五类＋第六类 `malformed_matches`＝支形状失败，逐字拒文表 `:78-85`，2026-10-16 归位（流水 51））→ `ToolMatchRejection`）；:92–98 框架与依赖红线（R5b／R7／R6 与非死闸的发起面 doctrine）；:114–118 不降级与静默禁令（**合法降级路径＝无**；失败与拒因必须有**机读信号**：step payload 拒因字段 ＋ notice（类型取自 `synth/S6-事件与帧目录.md`）；**不得静默丢子问题**——漏配即判失败，不许「当作已配」或跳过该子问题，红线原文 `arch/P7a-交接包与挂账清单.md` A-P7a-37）。

## 织网义务（eng/04-测试网设计.md §三 归本块行＋关联行）

〔来源：eng/04-测试网设计.md §三 盲区补钉清单 :29–:37〕

> | B4 | N1 禁用词闸族（仅 1 个豁免族被间接测到） | 专属钉（对应 `gate`） | 中 |
> | B5 | 帧协议级时序（step/text/ask/verdict/done/error 序与 data 形） | 从 `eval/results/frames/` 真帧流转离线 golden 回放钉 | 中 |
> | B3 | H8 预算四限额边界（现只钉了 CLARIFY_ASK_CAP=6） | 每限额上限/触顶收敛行为钉（数值只引预算表） | 中 |

（上列三行为**关联行**——归块注与分工见下）

- **归块注（§三 无明写本块的行）**：§三 表内两处明写归属的是 B1「（对应 runtimev2 `bookkeeping`）」与 B2「（对应 `orchestration`）」——**tool_matching 在 §三 无明写行**。本块织网义务＝①②③（下），不加专属盲区钉；若主窗对账认为图面缺本块盲区钉，属新增项、不在本票。
- **关联行①（B4 的判断面）**：B4 行原文归属注记「专属钉（对应 `gate`）」已被 `walk/裁决表.md` §12 覆盖（gate 卡「H12 全量」作废、`eng/04a` pin-18 改写；`specs/modules.md` `## gate` 注「废弃词闸已移出本模块——判断归 `tool_matching` 的模型产出、分派归 `preconditions` 判定序第 1 位」）——故「禁用词闸族」的**判断产出面**落本块，钉面＝pin-31 判半边（本票「测试网钉」1 行）；**分派面**落 `preconditions`（RT-W4-04）。本块不新写「禁用词闸族」专属钉。
- **关联行②（B5 的 data 形面）**：本块拒因的机读信号（step payload 拒因字段 ＋ notice）是帧 `data` 形的**发射方半边**；帧序与回放钉本体归 B5（`eval/results/frames/` 离线 golden），本块只保证「payload 形状＋notice 类型」按规格可被机检（`::rejection_signal_present`）。
- **关联行③（B3 的限额面）**：B3「每限额上限」的**数值与计数面**归 `state`（预算表／`check_limits`）——本块按行为 9 **只引限额真源双指、不写字面值**（挂钩表「限额数值不复制…」行）；拒因回喂自环的**熔断不加**（行为 9），轮数兜底归 `state` 判定 ＋ `orchestration` 终止。
- 本票织网义务＝① 关联行①③的**消费面**（不新写专属钉）；②「测试网钉」1 行对应的 pin-31 判半边用例落网；③ L2 新规格钉随本票施工按 TDD 生长（eng/04 §五原文：**「L2 新规格钉不入门——它随各块施工按 TDD 生长，是网的使用者不是织网判据」**）——本票验收测试即 L2 钉源。

验收: 以下判据逐条全绿为过——
- 「票面对象」15 行逐行实现为 `tests/domains/test_v2_tool_matching.py` 用例并全绿，测试标识与规格列逐字一致（含【边界集】／【保留集】三行；第 15 行 `::mention_mode_closed_world` 系 2026-10-16 流水 51 补抄行，来源＝`specs/tool_matching.md:138`）；
- 「测试网钉」1 行（pin-31 判半边）对应用例在场且绿；pin-31 分派半边不在本票（挂 RT-W4-04）；
- 边界闸 R5b／R6／R7（＋R1／R2）在 `lint-imports` 双配置下绿（V2 侧 18 KEPT 基线不红）；「无旁路」行为断言在场（不经 `bookkeeping.call_model` 之外直发模型调用＝零命中）；
- 限额数值零字面量：本块源码不含限额字面值，只引 `recon/K-上下文事件指南预算.md` R-K-72…R-K-78 ＋ `walk/裁决表.md` §06-A；
- `tools` 侧工具描述改动限**描述文本**，`specs/tools.md` 公开接口签名零改动（`::descriptor_covers_three_parts` 经 tools seam 绿）；
- 「任务」节所列**接口缺口**两项已在施工前由 L0 裁并回写卡面（未裁则停报 L0，不落实现）；
- 回报附 pytest 全量输出与 lint-imports 输出原文。

回报: 完成后回主窗——「RT-W4-03 完成，产物 `appv2/runtimev2/tool_matching/`（＋`tools` 侧描述文本改动清单），偏差: 有/无（有则逐条列），测试: pytest 摘要＋lint-imports 摘要」。对逐字稿任何一行偏离即停码停报 L0，不落实现；接口缺口（「提及 vs 执行」结论字段／时间窗结论字段／`MatchReason` 字段面）未裁即停报 L0。
