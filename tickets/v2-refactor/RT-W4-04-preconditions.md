# RT-W4-04 · preconditions——V2 前置条件机

状态: **草案（待主窗 manifest 对账后派工）** ｜ 所属规格: `specs/preconditions.md`（状态「已定稿」——前置满足）
Touches modules: `preconditions`（本票只建 preconditions 本体；规格「触及的模块」表另声明 `tools`（**闸件本体在 `appv2/tools/precondition.py`**——ADR-0007 同时裁决 4）、`state`（判定结果与注记的状态形状）两关联侧归各自票承接）
波次: W4（`docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二 W4 行原文：「七个业务相位（understanding → clarification → tool_matching → preconditions → execution → answering → verification）」｜「互零依赖，**建议按业务链序施工**（便于走查 narrative 与测试网逐块加厚），不禁止并行」；本波出口判据「每相位配属规格十节版式定稿＋新规格钉绿＋触及相位的特征钉绿」；本块＝链序第 4 位（前位 tool_matching、后位 execution））
复审强度: 100%（eng/03 §五 流水 48 规则，质量关键块全复审；本块在 §五 表 W4 行质量关键列「preconditions／answering／verification」侧——该列分配理由整行原文「零 LLM 精度件＋P0 钉最重的交付面给 B」；§五 头注「**2026-10-16 更新：双队制废止**——改为单窗＋子代理 ≤3 并发、小票制，下表 A/B 分配**降级为「复审强度规则」保留**：B 列六块＝质量关键块施工后 100% 复审」——故本票复审强度＝100%）
前置: ① 规格定稿（`specs/preconditions.md` 已定稿——已满足）；② 波次前置：**W1–W3 全收波**（本票只依赖 `state` W1 与 `tools` 存量公开面——**零模型依赖**，W2／W3 的 gateway_adapter 替身**非本块前置**，本块不调模型）；③ 链序前置（eng/03 §二 W4 行「**建议**按业务链序施工」）：RT-W4-03-tool_matching 收票——该票产出的三类语义结论（「提及 vs 执行」结论／口径归一结果 `caliber_key`／时间窗结论）是本块判定序第 1／2／4 位的**被消费物**；**仅链序消费面，非 import 依赖**（R1 相位互不 import，消费只经 `state` 形状）
阻塞: RT-W4-03-tool_matching 收票（链序消费面；其结论字段载体＝该票「接口缺口」条，L0 未裁前本块判定序第 1／2 位无输入形状）；`state` 收波（`approved_ids`／判定结果与注记的形状面）｜被阻塞: W5 `orchestration`（判定序驱动、ask 帧发射与 resume 承接、拒因回喂）；`answering`（全拒 → 带拒因如实直答——消费本块「拒因齐备」的保证）；`transport`／`orchestration`（`AskReason.kind` → 帧 `frame.kind` 映射的对账依据＝本规格接口定义映射表）

## 任务

按 `specs/preconditions.md` 新建 `appv2/runtimev2/preconditions/`：每个子问题在**真去查之前**过一串**固定检查**，出**三态**之一——**放行／拒答／等用户**；**纯程序零 LLM**（语义判断已上移到匹配相位）；判定序固定＋命中即停，注记并入放行（不设第四态），任一非 `allow` 与任何带注记的 `allow` 都必须留痕；闸件不可用时 **fail-closed 转 `refuse`**，不静默放行。闸件本体在 `tools` 侧，本块**只经其公开面**。

> 逐字稿载体（AGENTS.md 6b）：本票「票面对象」「测试网钉」「织网义务」三节的每一行均为所引规格／eng 文档表行**原文照抄**（无改写、无增删、无换述）；施工子代理对逐字稿只许照抄，偏离即停报 L0，不自行裁量。

先读: （6 份，小票制上限）`specs/preconditions.md` 全文（十节版式，含「判定序明文表」8 行）；`specs/modules.md` `## preconditions` 卡（签名以卡为准）＋`## 边界规则`（R1／R2／R5b／R6／R8）；`specs/tools.md`（闸件本体 `appv2/tools/precondition.py` 公开面）；`docs/runtime-refactor/eng/04a-应钉行为清单.md`（pin-17 行 ＋ pin-14／pin-16／pin-31 行 ＋ 末「使用规则」行）；`docs/runtime-refactor/synth/S6-事件与帧目录.md`（notice 类型 ＋ 帧 `frame.kind` 闭世界——`AskReason.kind`→`frame.kind` 映射表的对账依据）；`docs/runtime-refactor/eng/04-测试网设计.md` §三（B2b 行）／§五／§六。AGENTS.md 硬纪律 6b 为常驻纪律（本票已逐字引在「逐字稿载体」条）。

**小票制自检（流水 48）**：票面对象 14 行 ≤ 15 ✓；先读 6 份 ≤ 6 ✓；聚焦一个行为簇＝「逐子问题过固定判定位序 → 三态结论 → 留痕」单链（本块单一入口 `gate_all`）✓ → **本票不拆**（无 -A／-B 派生票）。eng/03 §二 的波序、§五 的复审强度已逐字引在票头，施工子代理**不必再读 eng/03**。

**施工前对账项（停报 L0，勿自造）**：① 判定序第 1／2 位消费的「提及 vs 执行」结论与时间窗结论，其**字段载体在 `tool_matching` 侧未定**（RT-W4-03「接口缺口」条）——未经 L0 裁并回写卡面，不得自造读入字段名；② 8 个判定位各自的**输入口径**（哪些字段来自 `state`、哪些来自 `tool_matching` 结论）以 `synth/S3` C-01 与各闸件公开面为准——规格不复制新值，遇缺即停报 L0，不发明判定位；③ **信号落地写口**——**已消化（流水 50）**：写口面＝`bookkeeping` 唯一写口，触及表 `specs/preconditions.md:30` 已列该写口行；行为 10「落 step 记录」与 notice 的**写入承接方**＝该写口（本块只产信号值，不直写状态——W3 `bookkeeping` 单写口的「相位不得直写」约束面；测试 `::verdict_signal_present` 经写口断言）。

框架红线: **无点名框架**（本模块不引入任何框架、**不调模型**）——对应闸 R5b 契约（source 覆盖 `preconditions`）＋ **零 LLM 铁律**（R7／R8，见边界红线①）
边界红线: ① **零 LLM 铁律**：不得 import 任何模型客户端——**不得引 `litellm`／`appv2.infra.llm_client`（R7 ＋ B6）**，**且不得引 `appv2.runtimev2.gateway_adapter`（R8「零 LLM 面」）**；对应闸＝`tools/importlinter_v2.toml` R7／R8 契约 ＋ 一条 AST 机检（先例 `tests/domains/test_v2_four_phase.py:446`）；② 不得直接 import `langgraph`／`langchain`（框架只许在 `orchestration`）——**R5b**；③ **只经 `tools` 公开面**接触世界（闸件本体在 tools 侧，不绕过 `tools` 直引引擎）——**R6**；④ 相位互不 import（R1）＋公共层块只经包根（R2）；⑤ **禁手写替代**：不得自建闸件旁路、不得绕过 `tools` 直引引擎；程序侧无词表／正则语义判断（AST 扫描，豁免面＝形态处理／集合成员判定）；⑥ 不引旧码 `appv2.runtime`（R5）

## 票面对象（specs/preconditions.md「验收测试」表逐行转抄，14 行）

〔来源：specs/preconditions.md「验收测试」表 :105–:118，逐行原文；「规格行」列＝该行 file:line 来源注，非规格原文〕

| # | 验收标准（原文） | 对应测试（原文标识） | 规格行 |
|---|---|---|---|
| 1 | 每子问题恰一条 verdict；`subtask_id` 对不上 → 判失败 | `tests/domains/test_v2_preconditions.py::exactly_one_verdict_per_subtask` | specs/preconditions.md:105 |
| 2 | `decision` 越界取值 → 判失败（三态闭世界） | `tests/domains/test_v2_preconditions.py::decision_enum_closed_world` | specs/preconditions.md:106 |
| 3 | 判定序固定＋命中即停（打在序 3 上不进序 4） | `tests/domains/test_v2_preconditions.py::fixed_order_short_circuit` | specs/preconditions.md:107 |
| 4 | 带注记的判定位 → `allow` ＋ `notes` 非空（**不设第四态**） | `tests/domains/test_v2_preconditions.py::note_merges_into_allow` | specs/preconditions.md:108 |
| 5 | 外表越集（申报面）→ `ask`（kind=external_table_approval） | `tests/domains/test_v2_preconditions.py::declared_external_table_asks` | specs/preconditions.md:109 |
| 6 | 恢复后消费 `approved_ids` 重判放行 | `tests/domains/test_v2_preconditions.py::resume_reconsume_approved_ids` | specs/preconditions.md:110 |
| 7 | 换链回炉只允许一次；二次触发 → `refuse` | `tests/domains/test_v2_preconditions.py::rewire_once_then_refuse` | specs/preconditions.md:111 |
| 8 | 非 `allow` 必带 `hit_rule` ＋ 人话；口径类拒答必带替代项 | `tests/domains/test_v2_preconditions.py::refusal_has_rule_text_alternatives` | specs/preconditions.md:112 |
| 9 | 闸件抛错 → fail-closed 转 `refuse`（**不静默放行**） | `tests/domains/test_v2_preconditions.py::gate_error_fail_closed` | specs/preconditions.md:113 |
| 10 | 本模块与闸件零 LLM（AST＋import 双证） | `tests/domains/test_v2_preconditions.py::no_model_call_in_preconditions` | specs/preconditions.md:114 |
| 11 | 程序侧无词表／正则语义判断（AST 扫描本模块；**豁免面＝形态处理／集合成员判定**——不算语义词表／正则） | `tests/domains/test_v2_preconditions.py::no_lexicon_or_regex_in_preconditions` | specs/preconditions.md:115 |
| 12 | 判定结果的机读信号在场（step payload ＋ notice） | `tests/domains/test_v2_preconditions.py::verdict_signal_present` | specs/preconditions.md:116 |
| 13 | 【边界集】空窗／越界水位／未绑定指标／单井不支持 → 各自命中对应判定位 | `tests/domains/test_v2_preconditions.py::boundary_each_rule_hits` | specs/preconditions.md:117 |
| 14 | 【保留集】`allow` 的普通子问题行为不变（无注记、无额外信号） | `tests/domains/test_v2_preconditions.py::retention_plain_allow_unchanged` | specs/preconditions.md:118 |

> 测试文件归属（spec 未另附节尾原注，按规格「验收测试」表首列原标识照抄）：本块验收测试绑**新建** `tests/domains/test_v2_preconditions.py`（14 行测试标识同文件、同模块名）；旧码测试本批不改。
> 第 5／6 行跨相位面：`::declared_external_table_asks` 的 `ask` 帧发射与 `::resume_reconsume_approved_ids` 的 resume 承接在 `orchestration`／`transport`（本块只出 `SubtaskVerdict` 与 `approved_ids` 重判语义）；第 12 行 notice 类型取自 `synth/S6-事件与帧目录.md`。
> 第 10 行的「闸件」侧＝`appv2/tools/precondition.py`：本块测试须**同时**覆盖本模块 AST 与 import 双证（`specs/preconditions.md` 挂钩表 R8 行）。

## 测试网钉（specs/preconditions.md「与闸的挂钩表」pin 行逐行转抄，4 行）

〔来源：specs/preconditions.md「与闸的挂钩表」:140–:143，逐行原文〕

1. **pin-31（分派半边）**｜废弃词结论的**分派**（判定序第 1 位，机械分派；判断在 `tool_matching`）｜钉 **`pin-31`**（模型判「提及 vs 执行」／机械分派在 `preconditions` 判定序第 1 位／出数只认现行口径）｜现状：待织网（阶段 5）
2. **pin-14**｜模糊时间词＋plan 非空 → 确定性改判走 clarify 三选一反问帧｜钉 **`pin-14`**（落点＝判定序第 2 位闸1b——消费 `tool_matching` 时间窗结论 → `ask` 反问）｜现状：待织网（阶段 5）
3. **pin-16**｜软失败域闸：data/semantic 成功返回但域错 → 换链回炉恰 1 次为界｜钉 **`pin-16`**（落点＝行为 7 换链回炉一次为界）｜现状：待织网（阶段 5）
4. **pin-17（P0）**｜前置条件机**三态**语义一字不动（放行／拒答／等用户，注记并入放行）＋判定固定序命中即停＋零 LLM 面＋扩口未批不得直答终局｜钉 **`pin-17`**（落点＝行为 2／3／5 ＋ 判定序明文表 ＋ 零 LLM 红线；真源 `walk/裁决表.md` §12-B/C）｜现状：待织网（阶段 5）

- 本规格「与闸的挂钩表」共 12 行，**上列 4 行为 pin 行**（其余为 spec gate／边界闸 R8／R6／R5b／测试／人审行——见「验收」节逐条）。
- pin-31 是**双落点钉**：分派面＝本块判定序第 1 位（本行）；**判断产出面**＝`tool_matching`（RT-W4-03「测试网钉」1 行）。本块只承担分派面。
- pin-17 为 **P0 承重钉**（`eng/04a` 头注 P0 十三条含 pin-17），三态语义一字不动＝本票第一红线。

## 施工要点（specs/preconditions.md「行为约定」节骨架——file:line 锚＋一句话）

| 锚 | 条目 | 一句话 |
|---|---|---|
| specs/preconditions.md:71 | 行为 1 逐子问题判定 | 对每个子问题**恰好一条** `SubtaskVerdict`；`subtask_id` 必须对上某子问题（对不上＝判失败） |
| specs/preconditions.md:72 | 行为 2 判定序固定＋命中即停 | 同一处明文表（见下）；**不得乱序、不得并行判定同一子问题** |
| specs/preconditions.md:73 | 行为 3 条数与次序以真源为准 | 现为 `synth/S3` C-01 所记的 **8 个判定位（6 主闸号 ＋ 2 子闸）**——本规格不复制该数字以外的新值、不新增判定位 |
| specs/preconditions.md:74 | 行为 4 闸内只做结构校验与机械分派 | 语义类结论（禁用词「提及 vs 执行」／口径归一／**时间窗能否确定**）**一律由 `tool_matching` 的模型产出**（Owner 裁决 #12／#13）；本块只接收结论并机械分派，不判语义 |
| specs/preconditions.md:75 | 行为 5 注记并入放行 | 命中带注记的判定位时，`decision="allow"` 且把注记写进 `notes`；**不设第四态** |
| specs/preconditions.md:76 | 行为 6 外表审批（申报面） | 闸 2 **只做申报面判定**（计划里声明的外表 → `ask`／审批）；**「执行前再扫」归引擎执行面**（`tools`／`query`，真源 `arch/P3b-票堆V2-35至45.md` V2-44）；恢复后本块**消费 `approved_ids` 重判** |
| specs/preconditions.md:77 | 行为 7 换链回炉一次为界 | 同一子问题因换链回炉**只允许一次**（真源 V2-43 ／ `walk/06-过程图-循环挂起判断.md` 循环表）；再触发同支 → 转 `refuse`（不给第三次） |
| specs/preconditions.md:78 | 行为 8 可解释性 | 任一非 `allow` 的结论必须带 `hit_rule` ＋ 人话原因（`human_text`）；口径类拒答还必须带**替代项**（`alternatives`）——缺项＝判失败 |
| specs/preconditions.md:79 | 行为 9 全拒的处理不属本块 | 本块只逐子问题出结论；「全拒 → 带拒因如实直答」由 `answering` 承接（本块只保证拒因齐备） |
| specs/preconditions.md:80 | 行为 10 判定结果全部留痕 | 每个 `SubtaskVerdict` 落 step 记录（含 `hit_rule`）；**静默放行是已知失败模式**，故 `allow` 且带 `notes` 时注记必须落在 step payload 里 |

**判定序明文表（specs/preconditions.md:84–:93 逐字引用——次序＝执行序，命中即停；施工子代理照抄，不得增删判定位/改序）**：

> | 序 | 判定位 | 判什么 | 性质 |
> |---|---|---|---|
> | 1 | 闸1 禁用词 | 旧叫法／合法提及 | **结构分派（消费模型结论）**——判断在 `tool_matching`（Owner 裁决 #12） |
> | 2 | 闸1b 模糊时间词门 | 时间窗能否确定／是否需反问 | **结构分派（消费模型结论）**——判断在 `tool_matching`（Owner 裁决 #13；**不设「确定性词面门」**） |
> | 3 | 闸2 外表越集 | 计划**声明**用到平台外的表 → `ask`（申报面判定；**「执行前再扫」归引擎执行面**，见行为 6） | 结构 |
> | 4 | 闸3 合法口径（＋前置台账闭世界） | 口径合法性（语义部分**已上移**）／指标在不在台账 | 结构 |
> | 5 | 闸4 在册绑定态 | 指标绑没绑汇总表 | 结构 |
> | 6 | 闸4b 软失败域闸 | 题眼域↔链路域一致 | 结构 |
> | 7 | 闸5 新鲜度窗 | 时间范围 vs 数据水位 | 结构 |
> | 8 | 闸6 单井支持 | 单井查得了吗 | 结构 |

结构锚：specs/preconditions.md:11–21 「不做什么」表（7 行——语义判断归 `tool_matching`、产出子问题归 `clarification`、执行归 `execution`、解析本体归 `parsing`、**本模块不调模型**、入口安全闸归 `gate`；纯范围排除走**人审**＝其挂钩表末行）；:23–29 触及的模块（`tools` 侧＝**闸件本体 `appv2/tools/precondition.py`**，语义类判定位上移后闸内只留结构校验）；:32–59 接口定义（`gate_all`／`SubtaskVerdict`／`RefusalReason`／`AskReason`；**`AskReason.kind` → 帧 `frame.kind` 唯一映射表**＝`external_table_approval`→`external_table_approval`、`caliber_clarify`→`clarify`（帧侧闭世界真源 `synth/S6`；发帧与映射由 `orchestration`／`transport` 承接，两处取值不得各说各话）；`decision` 三态闭世界、越界判失败；**唯一确定性来源＝不做任何模型调用**；错误契约＝判定器抛错 → **不着 `allow`**（fail-closed）转 `refuse` 带拒因；三态与 ADR／`synth/S1` 旧记「四态」的差异已由裁决覆盖、ADR／S1 修订**已兑现**）；:61–67 框架与依赖红线（R5b／R7／R8／R6＋AST 先例）；:95–99 不降级与静默禁令（**合法降级路径＝无**；任何非 `allow` 与任何带注记的 `allow` 必须产**机读信号**：step payload 的 `hit_rule`／`decision`／`notes` ＋ notice（类型取自 `synth/S6`）；红线原文 `arch/P7a-交接包与挂账清单.md` A-P7a-37）。

## 织网义务（eng/04-测试网设计.md §三 归本块行＋关联行）

〔来源：eng/04-测试网设计.md §三 盲区补钉清单 :29–:37〕

> | B2b | `test_precondition_four_states_reachable` 旧测仍断言**四态**闭世界（`SUBTASK_STATES=={pass,blocked_ask,blocked_refuse,note}`，test_v2_four_phase.py:284）——行为已被裁决 §12-B 改为三态 | 织网②**退役四态断言、织三态版** `test_precondition_three_states_reachable`（agent-loop 验收行已挂此名，悬空虚引）；同 pin-18 类目：按裁决改的行为，钉新不钉旧 | 高 |

- **归块注（本行即本块，行文未写「对应 runtimev2」字样）**：B2b 行主体＝前置条件机旧测四态断言退役、织三态版 `test_precondition_three_states_reachable`（`test_v2_four_phase.py:284`）——即本块（三态闸，pin-17）。§三 另两处明写归属（B1「对应 runtimev2 `bookkeeping`」／B2「对应 `orchestration`」）皆非本块；**B2b 的「对应 runtimev2 `preconditions`」归属注记由主窗对账确认**（本票按行为主体归本块）。
- **关联行①（B6 的越集审批半条）**：B6「挂起恢复多场景（clarify 二级／越集审批／跨实例）」中**越集审批**半条＝本块行为 6（恢复后消费 `approved_ids` 重判，测试 `::resume_reconsume_approved_ids`）；帧侧挂起／resume 承接归 `orchestration`／`transport`，「跨实例条保持门控」。本块不新写 B6 专属钉。
- **关联行②（B5 的 verdict 面）**：B5「帧协议级时序（step/text/ask/verdict/done/error 序与 data 形）」中本块是 `verdict`／`ask` 的**产出方半边**（`SubtaskVerdict` → step payload ＋ notice；`AskReason.kind` → `frame.kind` 映射表为对账依据）；回放钉本体归 B5（`eval/results/frames/` 离线 golden），本块只保证信号形状可机检（`::verdict_signal_present`）。
- **关联行③（B3 的换链计数面）**：B3「每限额上限」的计数与数值面归 `state`（预算表／限额判定）；本块行为 7 的「换链回炉一次为界」＝消费该计数做**机械分派**（pin-16），不复制数值、不新增限额。
- 本票织网义务＝① B2b 织网②动作（退役四态断言、三态版新钉在场且绿——`::decision_enum_closed_world` ＋ pin-17 用例为其实体）；②「测试网钉」4 行对应用例落网；③ L2 新规格钉随本票施工按 TDD 生长（eng/04 §五原文：**「L2 新规格钉不入门——它随各块施工按 TDD 生长，是网的使用者不是织网判据」**）——本票验收测试即 L2 钉源。

验收: 以下判据逐条全绿为过——
- 「票面对象」14 行逐行实现为 `tests/domains/test_v2_preconditions.py` 用例并全绿，测试标识与规格列逐字一致（含【边界集】／【保留集】两行）；
- 「测试网钉」4 行对应用例在场且绿（**pin-17 为 P0 承重钉**——三态语义一字不动）；
- B2b 织网②动作完成：旧四态闭世界断言退役、三态版新钉在场且绿（`test_precondition_three_states_reachable` 名实相符、非悬空虚引）；
- 零 LLM 双证绿：R7／R8 import 契约 ＋ AST 机检 `::no_model_call_in_preconditions`；`::no_lexicon_or_regex_in_preconditions` 绿；
- 边界闸 R5b／R6／R8（＋R1／R2）在 `lint-imports` 双配置下绿（V2 侧 18 KEPT 基线不红）；
- 判定位条数＝8（6 主闸号＋2 子闸）且次序与「判定序明文表」逐行一致（`::fixed_order_short_circuit`）；
- 「任务」节所列施工前对账项**三项**：①／② 待施工前由 L0 裁（未裁则停报 L0，不落实现）；③ 信号落地写口**已消化（流水 50）**——写口面＝`bookkeeping` 唯一写口，触及表 `specs/preconditions.md:30` 已列；
- 回报附 pytest 全量输出与 lint-imports 输出原文。

回报: 完成后回主窗——「RT-W4-04 完成，产物 `appv2/runtimev2/preconditions/`，偏差: 有/无（有则逐条列），测试: pytest 摘要＋lint-imports 摘要」。对逐字稿任何一行偏离即停码停报 L0，不落实现；三态语义、判定序明文表、零 LLM 面（R8）任一偏离即停报 L0，不落实现。
