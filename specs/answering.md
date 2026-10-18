# V2 作答（answering）

状态: 已定稿
来源: `specs/modules.md` `## answering` 卡、`docs/runtime-refactor/walk/14-作答-汇总作答.md`、`walk/裁决表.md` §14、`synth/S1`（M6）
版式: `docs/spec-format.md` ｜ 工序: `docs/spec-process.md`

## 目标

把前面查到的**全部子问题结果**整理成**一份答案**——**一段段推给页面（真流式）**、**每句带出处**、**缺口如实交代**。

## 不做什么

| 不做 | 由谁承担 | 锚点 |
|---|---|---|
| 逐句核验「有没有材料撑着」 | `verification` | `specs/modules.md` `## verification` |
| 执行查询、产观察 | `execution` | `specs/modules.md` `## execution` |
| 大结果**原文**的落盘与引用载体 | `execution` 落、`persistence` 为载体（本块**只消费引用**） | `walk/裁决表.md` §14-B；评审 E-10 处置（`docs/runtime-refactor/spec-review/execution-评审.md` E-10） |
| 材料段与 Manifest 的编译 | `context` | `specs/modules.md` `## context` |
| 提示词合同文本与指令装配 | `prompts` | `specs/modules.md` `## prompts` |
| 模型调用出口 | `gateway_adapter` | `specs/modules.md` `## gateway_adapter` |
| 拿词表／正则猜「这句话答没答上原问题」 | 交模型与 `verification`；程序只做结构判据 | `walk/00-设计总纲.md` §二 |

## 触及的模块

| 模块 | 改动类型 | 说明 |
|---|---|---|
| answering | 新增 | 起草 ＋ 真流式推出 ＋ 引用落账 ＋ 结构化缺口 ＋ **作答第二出口 `explore`**（V2-96 D5：材料不足时出检索意图，不落答案、零 text 帧） |
| parsing | 新增依赖 | 第二出口解析单点（`parse_explore`／`explore_schema_feedback`——闭世界/条数/必填，拒因回喂；V2-96 D5） |
| context | 新增 | 材料段与 Manifest（本块只消费其编译出口） |
| prompts | 新增 | 答案轮指令装配文本（只出文本；材料段不在装配输出内——材料渲染归 `context`，本块材料渲染＝消费 `context` 编译产物、零自取，与 `specs/context.md` 定界互认）；**第二出口合同＋1 示例＋再探预算行**（V2-96 D5）；**子问题覆盖表段＋additive `coverage` 参**（V2-119——零支撑子问题提示行，落动态段清单后材料前） |
| bookkeeping | 新增依赖 | 模型调用发起面：经 bookkeeping.call_model（单点发起），本块不直引 gateway_adapter |
| gateway_adapter | 新增 | 模型出口（唯一出口仍归它）；本块不直引——经 bookkeeping.call_model 发起 |
| state | 新增 | 草稿／引用块／缺口的状态形状（本块只消费）；**再探独立计数与待执行意图三字段＋`INTENT_EXPLORE`**（V2-96 D5） |
| transport | 新增 | **`text` 帧的增量发射**（本块只经其公开面）；`citation` 帧同经其公开面；**增补面帧（`supplement`）的发射归 `orchestration`**（2026-10-17 EB3 D1／D2——本块只往收集列追加条目）；**再探新观察复用 `observation` 帧**（帧型零新增，V2-96 D5） |
| tools | 改动（additive 载荷键＋闭世界词表转出） | 血缘观察载荷兄弟键 `LINEAGE_WINDOW_LABEL_KEY`（V2-107——答案面日期标注的**唯一**只读取值口，值＝实际取数窗标签）；相对时间词两表 R6 桥接转出（真源 `query`） |
| query | 改动（additive 只读件） | 血缘③行读回单点 `lineage_filter_window_label`（V2-107——`TimeWindow.label` 的只读出口，与生产单点 `lineage_filter_line` 同文件同源）＋相对时间词闭世界两表（只识别不解析；解析算法零改） |

## 接口定义

```python
def answer(state: RunState) -> AnswerDraft: ...
# 注入面（签名以卡为准的展开；关键词注入面）：answer(state, *, bus, max_observations=…)——
# 2026-10-17 EB3 D2 增第三处选给注入面 `supplements`（编排块持有的增补面收集列表）：
# 收口段三块（分源／归属／引用）按原序入该列表，帧由 `orchestration` 的增补面发射点发。
# V2-96 D5 增第四处选给注入面 `forced_text`（缺省空串）：编排块硬停止（再探轮数到顶）时交来的
# 程序确定性缺口正文——模型仍发射 `explore` 形时以本正文兜底交付（不判 failed）。
# **V2-123 增第五处选给注入面 `execution_date`**（缺省空串）：执行日**时间量经注入参**（orchestration
# 下传；本块不读时钟——L0 裁定 D-g），透传 `context.render_materials` 渲染材料头「执行日」段与
# 期错位比对（报表期晚于执行日 → 期错位注记）；缺省空串＝材料头无执行日段（本批前逐字零漂移）。

class AnswerDraft:
    segments: list[AnswerSegment]     # **增量片段**（流式逐段；顺序即呈现顺序）
    citations: list[Citation]         # 引用块（引标 → 观察序号）
    gaps: list[Gap]                   # **结构化缺口**（被拒／缺失／未及核验）
class AnswerSegment:
    text: str
    citation_seqs: list[int]          # 本段引用的观察序号（[n]；与全局观察同一套序）
class Citation:
    seq: int                          # 引标编号（＝观察序号）
    locator: str                      # 可机读出处（台账行／片段→报告→库／表名）
class Gap:
    kind: Literal["refused", "missing", "unverified"]   # 闭世界
    subtask_id: str | None
    reason: str
```

- **`Gap.kind` 是闭世界**（`refused`｜`missing`｜`unverified`）；越界值判失败。
- **`citation_seqs` 里的每个序号必须真实存在于观察序列**；**界外引标号由 `strip_dangling_citations` 在分段之前整枚剥除**（2026-10-17 EB5b 改判：剥除族第二形，同行为 13 占位符剥除——**不判失败、不收 `run_failed`**；剥除序号列落起草步 payload 机读键 `dangling_citation_seqs`〔不静默〕，该行失去引标即由 `verification` 按无据断言既有处置收口〔删句／结构行原样〕，材料照常带引标交付、run 终态 `completed`）。
- **大结果引用经 `seq → observation.ref`（`MaterialRef`）可达**：`Citation` 不另设 `handle` 字段，与 `specs/execution.md` 的字段口径显式对齐（真源 `walk/裁决表.md` §14-B）。
- 错误契约：起草失败（模型不可用／空稿超限）→ **不返回半成品**；由 `orchestration` 承接（挂起或如实收口），**不静默推空答案**。
- 真源：`specs/modules.md` `## answering` 卡（签名以卡为准）。

## 框架与依赖红线

- **无点名框架**（本模块不引入任何框架）。
- **模型调用发起面＝`bookkeeping.call_model`（单点发起）；其内部唯一出口＝`gateway_adapter`**：本块不直引 `gateway_adapter`（import 落点＝`appv2.runtimev2.bookkeeping` 包根——R2 禁深层子模块）。验收写法：模型调用发起点只出现在 `bookkeeping.call_model` ＋ 调用行为测试绿。对应闸：`tools/importlinter_v2.toml` 的 **R7 契约**（禁直引 `appv2.infra.llm_client`——模型出口仍唯一归 `gateway_adapter`；**B6 只管 litellm 出 `infra`，不含「绕过 `gateway_adapter` 直引」这一面**）＋ 一条「无旁路」行为断言（写法照 `specs/tool_matching.md` 同款；发起面收敛为规格层 doctrine，不设闸——主窗 2026-10-15 裁）。
- **不得直接 import `langgraph`／`langchain`**（框架只许在 `orchestration`）；对应闸：**R5b 契约**。
- **只经 `transport` 公开面**发帧（不自行拼 wire 帧、不直接接触 SSE 通道）。
- **禁手写替代**：不得自建模型客户端、不得自建帧通路。对应闸：`tools/importlinter_v2.toml` **R7 契约**（模型出口唯一归 `gateway_adapter`——发起经 `bookkeeping.call_model`）；验收写法：「无旁路」行为断言（模型调用发起点只出现在 `bookkeeping.call_model`，无自建旁路）。（**「自建帧通路」一面**：`transport` 的「只经包根」半面由 **R2 契约**覆盖，见「与闸的挂钩表」；另一半无闸。）

## 行为约定

1. **真流式**：答案**一段段推**（`text` 帧随增量发射），**不是收口时一次性推全量**。**免起草旁路例外（2026-10-16 补（L0/L2 三病灶修复批③））**：`draft_kind="direct"`（`route="direct"` 直答／拒答／闸拒／收敛转答——`bookkeeping.direct_answer` 三键与 `converge` 同落该值）**不发起草段**，其交付正文帧由**编排面**在收口后补发一帧（本块零帧：帧面归 `orchestration`，真源 `specs/agent-loop.md` 行为 8——真机证据 `docs/runtime-refactor/ladder/L0/01` 零 `text` 帧＝用户端空白）；本块**起草路径**的帧面与判据不变（判据只认 `draft_kind="direct"`，保留面不回归）。**2026-10-17 H 批注（角色分家·system 承载位）**：本相位**规章段**（动词钉死句／【答案要求】＋族⑥清单全文／术语白话表／族④汇总合同／族⑤起草答案合同）经 `prompts.answer_system_contract` 走 `bookkeeping.call_model(system=…)` 的**调用级注入参**（前置进本次请求、不入链）；**动态段**（题面件＋子问题结果清单）＋材料段（调用方追加于尾）仍作 user 条入链。
2. **引标与增量同步**：每段自带 `citation_seqs`；**引标编号＝观察序号**（全局同一套），段与引用不脱节。
3. **逐句可核**：每个事实断言都带引标；**无据的话不写进答案**（无据由 `verification` **删句**，本块不产出无据句——2026-10-17 EB3 D3：删句不贴前缀）。
4. **材料进上下文必须显式（本块只消费 `context` 的编译出口、只断言不实现）**：每次模型调用**必须有 Manifest 在场**（缺失＝判失败；Manifest 的编译归 `context`）；**大结果只以引用形式进窗口**（正文落 `persistence`，见 `execution`），本块不重复落。
5. **结构化缺口**：被拒／缺失／未及核验的部分，除文字外必须给出 `Gap`（哪个子问题、哪一类、为什么、还差什么）；**不静默截断**。
6. **多来源矛盾分开列**：矛盾数据**分源列明、不强调和**；并在 `Gap`／引用块里标出「互不一致」（对应最佳实践的 `refuted_by` 取向）。**2026-10-17 EB3 D2（交付面分层）**：分源块**不进正文**——按产出序入增补面（`supplement` 帧，`block="split"`），**块入增补面＝交付完成**，正文只留模型稿；本块收口段的确定性装配判据与逐支原文照抄纪律零改。
7. **链尾同步**：收口时引用块、`citation` 帧、`verdict` 帧、对话链尾**同批落定**，不得只落其一；其中 **`verdict` 帧的批次落定由 `orchestration` 协调**，本块只保证自产部分（引用块／`citation` 帧）就位。**2026-10-17 EB3 D2**：引用块与分源／归属块同属增补面（`block="citations"`／`"split"`／`"attribution"`），本块按原序入编排块持有的收集列（`supplements`），**帧由 `orchestration` 的增补面发射点一地发**；`citation` 帧与链尾仍在收口批内。
8. **模型原话不进对话层**：模型的中间原话只进过程档案与留痕。
9. **空稿不推**：若起草得到空稿或全部无据，**不推空答案**——按结构化缺口如实收口。
10. **答案要求以 `prompts` 的合同文本为唯一真源**：本规格不复制该清单（避免两处漂移）；条数现状真源＝`docs/runtime-refactor/recon/L2b-作答装配与回声.md`（`_ANSWER_REQUIREMENTS`，现 **8 条**——2026-10-17 EB2 D2 追加第八条「核验元数据不进答案正文」，条数真源随本合同走），**V2 条数以 `prompts` 合同定稿为准**。
11. **发射剥离**：模型应答在进答案面（`AnswerDraft` 片段与其 `text` 帧增量）之前经**发射围栏／JSON 形确定性剥离**——发射 JSON 不得进答案面（泄漏=0）。真源：`eval/results/Q15-对账报告.md`（:38——Q14 6 题→0，V2-48 发射围栏确定性剥离＋通道隔离兑现）；旧码真源 `docs/runtime-refactor/recon/L2b-作答装配与回声.md`（:58 `strip_emission_fences`／:101 剥离后草稿才进答案装配）。
12. **行集题交付与落引用界线**（与 `specs/execution.md` 行为 4 同一规则、逐字一致）：行集题（明细行集类：问句要求明细／排名／列举全行集）全量交付为默认——引擎返回的全部数据行逐行交付、丢行＝0；非行集大结果超阈才落引用（窗口只留摘要＋稳定引用＋行数），截断与落引用必披露。阈值数值阶段 5 待定（随真机数据定），行为归属与披露义务即此定死：行集题不得因落引用而丢行。真源：`tickets/v2/V2-61-材料承载分形渲染.md`（:5——24 支一刀切截断废除、改分承载体渲染）。**2026-10-17 EB3 D2**：行集交付的**程序追加面**（分源块／归属块／引用清单）同走增补面——**块入增补面＝交付完成**，正文只留模型稿（数据行逐行交付的义务落在正文，判据面不变）。
13. **占位符与界外引标不进答案面**：答案面不得出现字面占位引标 `[n]`（确无可引序号时一个引用记号都不写）；含 `[n]` 字面的行不得以占位符形式交付。**2026-10-17 EB5b（剥除族第二形）**：**界外引标号**（引标号不存在于观察序列）同族整枚剥除——`strip_dangling_citations` 在**分段之前**离场（正文其余字面零改），剥除序号列落起草步 payload `dangling_citation_seqs`（不静默）；**不判失败、不收 `run_failed`**——剥后该行失去引标即由核验面按无据断言既有处置收口，材料照常带引标交付（`completed`）。**2026-10-17 EB5c（块剥除）**：模型自把**程序块**写进草稿者按**块头模式族**整段离场（判据与段剥离单点＝`transport.split_block_sections`，族与变体同族判据见 `specs/transport.md` 行为 17）——血缘族段原文入 `lineage` 增补面、其余剥除面块型（引用清单）段原文零留存（程序机械再生），**text 帧发出前**正文即已干净（收口剥除不再是唯一防线）。真源：`eval/results/Q16-判分报告-G3.md`（:56——数字在场而 cited=[] 的 D-诱15 形）；`tickets/v2/V2-69-坏引标修复.md`（占位符串台根因＋「禁止占位符 [n] 进答案」指令纪律）。
14. **起草回声＝0**：草稿首行不得以「理解：」开头、草稿前 100 字不得含「指标候选」（`echo_flag` 恒 0——观测字段只记不拦）。真源：`docs/runtime-refactor/arch/P4b-票堆V2-56至65.md`（A-P4b-61——`echo_flag` 形态判据定义）；`eval/results/Q16-对账报告.md`（:61——echo_flag 全批 0，回声形态自 V2-62 后零再现）。
15. **台账 no_hit 降级交付三段形**：台账 no_hit（agg 未落列 notice 在场）时的降级交付必须**三段齐**——①油田级邻近可得量**带引用**交付；②逐井明细**逐井「未找到」明示**；③**指路**（替代出路指引）；且**零逐井数值冒充**（无逐井数据不得以油田级值充当逐井值）。真源：`eval/results/Q16-判分报告-G1.md`（:39 数-降2 判语——「油田级 8.10 万吨邻近可得引用＋逐井明细未找到明示＋指路，零逐井数值——轴第 4 条满分形」）；`eval/README.md`（「判分轴统一登记」第 4 条——引擎降级解释＋如实标注＝✅ 满分，诚实转述也是正确交付，数-降1/数-降2 跷跷板就此封尺）。
16. **排名型子问题强制消费排名观察支**：排名型子问题（问句求排名／排序序）的答案必须从**排名观察支**取值——交付的排名序对（对象↔名次／值）须与排名观察支的序信息一致，**不得弃排名支、以他支拼排名**（数-排2 形——帧证 obs[52]/[53] 曾弃即病形）。真源：`docs/runtime-refactor/arch/P4a2-票堆V2-51至55.md`（A-P4a2-04——「排名型子问题答案强制消费排名观察支（数-排2 形，帧证 obs[52]/[53] 曾弃）」）。
17. **跨油田题分源列明油田归属**：交付面涉**多油田**（或跨区块／跨层系）的题，答案必须**分源列明每条结论的归属**（油田名↔数值／结论配对），**不得框成「某区块／小范围结算序列」等含糊归属**（C-正6 形禁现）；**无据归属不得进答案面**（与行为 3「无据的话不写进答案」同族；`eng/04a` 族面＝pin-02「无据差值/无据口径框架」）。合同侧承接＝`prompts` 答案要求③（多来源逐个来源分别作答，不冲突也要分别列出）。可写成 assert：多油田 fixture 下答案面归属配对在场＋「某区块」形零命中。真源：`eval/results/Q16-判分报告-G3.md`（:32——C-正6 判语逐字：「34-8 侧 −42.6 被无据框成"某区块/小范围结算序列"、不认列渤中34-8 油田归属——跨套混写不分油田档＋无据调和」）；`eval/results/Q15-对账报告.md`（:167——族 C 跨报告归属校验：attribution_split 分源列明块帧证）；`docs/runtime-refactor/eng/04a-应钉行为清单.md`（pin-03——「跨油田题交付必须分源列明油田归属，不得框成『某区块』不认归属」，golden，P0）。**2026-10-17 EB3 D2**：归属块同样**不进正文**——入增补面（`block="attribution"`）；「归属配对在场」的判据面＝增补面（帧／run 行 `supplements`），正文只留模型稿。
18. **交付面分层：四类块不进正文（2026-10-17 EB3 D1／D2）**：程序追加内容（分源块／跨源归属块／引用清单／血缘五要素全文）**不进正文**——正文＝LLM回复原文（模型稿）；四类块经**增补面**（`supplement` 帧，载荷 `{block, text}`，`block` ∈ `split`／`attribution`／`citations`／`lineage`）交付，并由编排块随 run 行落库（`supplements` 列）；**评分面＝正文＋增补面合并判**（Owner 2026-10-17 裁决）。断言：收口后 `state.answer` 与链尾不含四类块的任何段头；增补面条目按产出序在场（原序）。
19. **残尾护栏（2026-10-17 F1 件三——定稿前的悬空结构检测与诚实收口）**：正文进终稿前先过**悬空结构**检测（判据单点＝`degradation.dangling_tail_closing`，纯形态、零语义）：①末行以全角「：」收尾（悬空引导句）；②末段连续表格行（含表格列记号 `|`）≤ 表头行上限（有表头无数据行）；③末段为**裸标题**（整行加粗，或独立短行——≤ 24 字、无引标、无 ASCII 数字、无句读收尾，且正文 ≥2 行）。命中即程序**补一句诚实收口短句**（白话、具名常量：`TAIL_CLOSE_LEAD_IN`／`TAIL_CLOSE_TABLE_HEADER`／`TAIL_CLOSE_BARE_HEADING`，随收口段追加为末段），**正文其余字面零改**——不改写、不重试、不拦截；重入幂等（该短句已在场＝零追加）。这是**兜底**：删句误伤本体由 `verification` 侧 F1 件一／件二修掉（真机证据＝`eval/results/frames/EB4-D-诱12.json`，run-c6fd52c7：交付答案断在裸标题「**两口井教训的差异**」）。
20. **作答第二出口 `explore`（V2-96 D5——材料不足时的有界再探意图）**：起草段模型应答整枚为 `{"action":"explore","reason":…,"requests":[…]}` 且合闭世界（`tool ∈ {doc_retrieve,fetch_section,fetch_report}`；`requests` 1..2 条；`reason` 非空；`doc_retrieve.query` 非空；`fetch_*` 的 `report_id` 非空——判据单点＝`parsing.parse_explore`）时：**不落答案、零 `text` 帧、零草稿标记**，落 `state.pending_explore`（意图投影：`reason`／`requests`／`raw`）＋ `next_intent="explore"`（路由交编排执行，见 `specs/agent-loop.md` 行为 12），起草步 payload 携 `explore` 面（requests 原文）。**拒因回喂恰一次**：explore 尝试但不合 schema（`parsing.explore_schema_feedback` 非空）→ 向链尾追加拒因载荷（`EXPLORE_FEEDBACK_TEMPLATE`）→ 同相位再读一次；**仍不合＝强制作答**（`EXPLORE_REJECT_BODY` 程序确定性缺口正文，**不判 failed**、不收 `run_failed`）。**硬停止兜底**：编排块轮数到顶后交来 `forced_text` 时，模型仍发射 explore 形＝以该正文交付（含「已试 N 次检索、仍缺 X」）。非 explore 形（正常答案／散文／非 JSON）＝零影响，照现有剥离／起草／核验管线（行为 11／13 不变）。真源：`docs/runtime-refactor/接手-召回全链路最终决议与运行流程-20261018.md` §五·5.1／5.2／5.3。

21. **核验失败回炉后的作答收口（2026-10-18 V2-115）**：`repair` 档下核验只标红不删（`specs/verification.md` 行为 14／15），回炉环（`appv2/runtimev2/orchestration/repair.py`）由模型**只重写标红行**后**复检重入核验**；本块**收口段**消费的 `state.draft` 即回炉后的定稿（`_finalize` 取 `state.draft or state.answer`——本块零改：回炉不新增作答相位调用面、不改收口判据）。回炉请求／模型返回／复检结果三面留痕落**回炉步** payload（`kind=verify`，标题「核验回炉」——四键 `repair_rounds`／`repair_request`／`repair_response`／`recheck`），**帧面零新增**（`text` 帧仍只在起草段发：回炉改写不改「一段一帧」的真流式判据，回炉后交付面以收口终稿为准）。回炉零交付兜底（正文空 ⇒ 程序诚实说明）由 `verification` 落 `state.draft`，本块照常收口（非空稿即交付）。真源＝`tickets/v2/V2-115-核验失败动作回炉修复.md`（含末尾「Kimi 评审修正」）。

22. **答案日期标注＝实际取数窗（2026-10-18 V2-107 降级版——只落一条不变量）**：答案里出现的**日期标注**必须＝**实际取数窗**，**不许沿用用户原词**（形如「昨天（2026-08-30）」＝把改绑日标成用户词，EB11 `Q10`／`Q14` 病灶）。单点真源＝`appv2/query/domain.py` 的 `TimeWindow.label`——本块**只读引用**（经血缘观察载荷键 `LINEAGE_WINDOW_LABEL_KEY` 取值，**不另算窗、不解析观察正文文本串**；该键的生产单点＝`tools` 血缘装配，读回单点＝`query.lineage_filter_window_label`）。起草段在**分段之前**做一次确定性形态归一（判据单点＝`degradation.annotate_window_label`，零语义、零正则）：定位「相对时间词［尾缀 ≤2 字符］（纯日期表达式）」形，且该词与问句内用户原词**同族**（族判据＝闭世界词表 `RELATIVE_TIME_WORDS`／`RECENT_TIME_WORDS`——真源在 `appv2/query/domain.py` 的「相对时间词闭世界」节，经 `appv2/tools/__init__.py` 包根只读转出（R6 桥接），本块零第二份字面；「近N天」形由形态扫描归近族），整枚替换为 `ANSWER_WINDOW_ANNOTATION_TEMPLATE`（＝`实际取数窗：{实际窗标签}（你问的「{原词}」）`——**保留原问法作对照说明**），**正文其余字面零改**；替换在分段前跑，故 `state.draft`／`text` 帧／片段三者同源（交付面零旧形）。**零改面（不猜）**：无用户原词／实际窗标签缺位或空串／两者相等／多窗不可归属（不同标签 ≥2 种）／异族词／括注非纯日期表达式（含量值或说明）⇒ 原样交付。**不做**冻结日/水位机制（《逻辑层清单》§三 L1 已裁「略过」——归测试环境）；**不改**时间解析算法（`parse_time_window` 逐字不动）。真源＝`tickets/v2/V2-107-相对窗标注即实际窗.md`、`docs/runtime-refactor/design/统筹方案-供给窗口.md`（§二 V2-107 节）。

23. **子问题覆盖信号（2026-10-18 V2-119——程序确定性检测 → 作答上下文显式提示）**：起草段在**渲染材料段之后、模型调用之前**逐子问题核「其锚／术语／数值记号是否在**渲染窗**（本轮材料段产物）内出现」（判据单点＝`subtask_coverage`——三 kind 分层形态判据：`subject`／`term`／`number`，同 `answer_anchors` 的装配序；**首个非空 kind 定论**：强锚在场时只认强锚——`NQ-M8` 形的数字 `41` 在错源窗 `W-41` 上全等命中，若「任一层命中即算支撑」则误判「有支撑」；零记号可判〔题面既无主体／术语命中又无数字串〕＝**有支撑**——零误报面）。零支撑子问题经 `prompts.assemble_answer_prompt(coverage=…)` 在 **user 动态段**追加提示行（`prompts.answer_round.ANSWER_COVERAGE_LINE` 逐字模板——落「子问题结果清单」之后、材料段之前；全有支撑＝整段零追加），覆盖表落起草步／再探意图步 payload 机读键 `subtask_coverage`（additive：`{子问题 id: 有支撑}`）。**只做检测与提示**：不替模型决定是否 `explore`、不自动改材料（票面任务 4）；模型自决面——零支撑在场时模型给正常作答仍走 `verify`、给 `explore` 形照既有第二出口（行为 20）走。判据面单点：锚面＝`appv2.text_tokens.boundary_hit`（边界优先）＋`appv2.tools.normalize_anchor_text`（跨形包含——核验归属审同规），术语面＝跨形包含，数字面＝`appv2.text_tokens.num_token_hit`（V2-100 D-a 判据单点，依赖自由）；题面数字串取词单点＝`_numeric_anchor_tokens`（既有锚席单点 V2-86／V2-90——本票**不新造第二份记号化**）。**与 `verification.rules.number_tokens` 的关系（Kimi 评审修正 2 的单点结论）**：核验面 `number_tokens` 是**材料侧量值记号**（小数／千分位／带单位／表格行裸数字——判「断言数值是否被材料复述」）；本票数值面＝**题面数字串锚点取词**（`_numeric_anchor_tokens`）＋**全等判定**（`text_tokens.num_token_hit`）——两者非同物、互不替换，本票**不新增任何记号化实现**（取词与判定全引既有单点，无第二真源）。**过渡期与收口条件**：本票登记为「带票号过渡（V2-119）」；若后续票把「题面数字串取词」下沉为共享单点（`appv2/text_tokens` 增件），本票 `_subtask_anchors` 改为直引该新单点即收口（调用面唯一、一处改动），在此之前 `verification` 面零改。真源＝`tickets/v2/V2-119-子问题覆盖信号.md`（含「Kimi 评审修正」节）。

## 不降级与静默禁令

- **合法降级路径：无**（本模块不自降级；起草原话不完整时走结构化缺口，不改写事实）。
- 流式增量、缺口、截断披露、收口都必须产生机读信号：本块自产的 `text`／`citation` 事件（类型取自 `synth/S6-事件与帧目录.md`）＋ 材料截断的 `material_truncated` notice（真源 `tickets/v2/V2-61-材料承载分形渲染.md` 附 D）＋ step payload 的 `citations`／`gaps` 字段；`verdict` 事件为**消费方信号**——其批次落定由 `orchestration` 协调（见行为 7），本块只保证自产帧。
- 红线原文：`arch/P7a-交接包与挂账清单.md`（A-P7a-37）「**不许静默**——若任何相位仍发生截断，模型面必须随材料段带明示……收口注记面同步披露」。
- **用户可见文案白话化（2026-10-17 EB4b）**：notice 内容（`MATERIAL_TRUNCATED_CONTENT`／`EMISSION_STRIP_CONTENT`）与增补面段头（`CONTRADICTION_SECTION_HEAD`／`SOURCE_SECTION_HEAD`／`CITATION_BLOCK_HEAD`——增补面属交付面，评分面＝正文＋增补面合并判）白话化（依据＝`docs/runtime-refactor/research/最佳实践-3a-白话化与受众适配.md` 第三节 3.2）；**判定面语义零改**（披露义务、逐支原文照抄、逐源配对判据不变）；**回喂／机读面零改动**——`ENGINE_NOTES_HEAD`（进模型窗的材料段头）与四条 `*_REASON`（`Gap.reason` 机读缺口面）逐字不动（A-P6b-05）。

## 验收测试

| 验收标准 | 对应测试 |
|---|---|
| 答案**一段段推**（多段 `text` 帧），非一次性推全量 | `tests/domains/test_v2_answering.py::streaming_segments` |
| 每段自带 `citation_seqs`，且序号**真实存在于观察序列** | `tests/domains/test_v2_answering.py::segment_citations_resolve` |
| 出现不存在的引标号 → **剥除该记号**（坏引标；2026-10-17 EB5b 改判：不判失败、留痕 `dangling_citation_seqs`） | `tests/domains/test_v2_answering.py::dangling_citation_rejected` |
| 每次模型调用都有 Manifest；大结果只以引用进窗口 | `tests/domains/test_v2_answering.py::manifest_and_ref_only` |
| 被拒／缺失／未及核验 → 产出结构化 `Gap`（三档闭世界） | `tests/domains/test_v2_answering.py::structured_gaps_all_kinds` |
| `Gap.kind` 越界取值 → 判失败 | `tests/domains/test_v2_answering.py::gap_kind_closed_world` |
| 矛盾来源分列且标「互不一致」，不调和 | `tests/domains/test_v2_answering.py::contradiction_split_not_merged` |
| 收口同批落定（引用块＋citation 帧＋verdict 帧＋链尾） | `tests/domains/test_v2_answering.py::finalize_atomic` |
| 空稿／全无据 → 不推空答案，按缺口如实收口 | `tests/domains/test_v2_answering.py::empty_draft_not_pushed` |
| 模型原话不进对话层 | `tests/domains/test_v2_answering.py::raw_not_in_dialogue` |
| 发射 JSON 不进答案面（发射围栏／JSON 形确定性剥离，泄漏=0） | `tests/domains/test_v2_answering.py::emission_strip_zero_leak` |
| 明细行集题交付行数＝引擎返回行数（50 行全交付，丢行=0） | `tests/domains/test_v2_answering.py::rowset_full_delivery` |
| 材料截断必披露：`material_truncated` notice＋「没用上的部分不作答」声明在场（未截断零 notice；逐字＝2026-10-17 EB4b 白话化后文案，旧「未渲染部分不作答」） | `tests/domains/test_v2_answering.py::truncation_disclosed` |
| 答案面无字面占位符 `[n]`（含 `[n]` 行不以占位符交付） | `tests/domains/test_v2_answering.py::placeholder_marker_not_in_answer` |
| 起草回声=0：首行不以「理解：」开头／前 100 字不含「指标候选」（echo_flag 恒 0） | `tests/domains/test_v2_answering.py::echo_flag_zero` |
| 台账 no_hit → 降级交付三段形（油田级邻近可得引用＋逐井「未找到」明示＋指路）且零逐井数值冒充 | `tests/domains/test_v2_answering.py::no_hit_degraded_delivery_three_part` |
| 排名型子问题答案消费排名观察支（排名序对与排名支序信息一致，不弃支他拼） | `tests/domains/test_v2_answering.py::ranking_answer_consumes_ranking_obs` |
| 多油田题答案面分源列明归属配对（油田名↔数值／结论）在场＋「某区块」含糊归属形零命中 | `tests/domains/test_v2_answering.py::cross_oilfield_attribution_paired` |
| 交付面分层：四类块不进正文（正文＝模型稿）＋条目按产出序入增补面（`block` 闭世界四值） | `tests/domains/test_v2_answering.py::supplements_carry_blocks_out_of_body` |
| 程序侧无词表／正则语义判断（AST 扫描；豁免面＝形态处理／集合成员判定） | `tests/domains/test_v2_answering.py::no_lexicon_or_regex_in_answering` |
| 流式、缺口、截断披露的机读信号在场（text／citation 帧＋material_truncated notice＋step payload；verdict 为消费方信号，批次落定归 orchestration） | `tests/domains/test_v2_answering.py::answering_signal_present` |
| 起草面块剥除：模型自写程序块（`**引用**` 等族变体）段整段离场、text 帧发出前正文即已干净（2026-10-17 EB5c） | `tests/domains/test_v2_answering.py::supplements_carry_blocks_out_of_body`＋`tests/domains/test_v2_transport.py::eb5c_nq_m7_reference_variant_block_stripped` |
| 【边界集】单段答案／零材料／矛盾双源／坏引标 → 各自落到对应分支 | `tests/domains/test_v2_answering.py::boundary_single_seg_zero_material_conflict_bad_cite` |
| 【保留集】无矛盾、无缺口的普通答案：引标与分源行为不变 | `tests/domains/test_v2_answering.py::retention_plain_answer_unchanged` |
| 残尾护栏：悬空引导句／光表头／裸标题三形命中 → 定稿补诚实收口短句（正文其余字面零改、重入幂等）；完整正文字零追加（2026-10-17 F1 件三） | `tests/domains/test_v2_answering.py::dangling_tail_guard_closes_honestly` |
| 作答第二出口：命中 `explore` → 不落答案、零 `text` 帧、`next_intent="explore"`＋`pending_explore` 在场（V2-96 D5——落点＝行为 20） | `tests/domains/test_v2_v296_explore.py::test_answer_explore_does_not_emit_draft` |
| 第二出口解析闭世界（`tool` 三值／每轮 1..2 条／必填／越界即拒＋拒因面非空；非 explore 形零拒因）（V2-96 D5） | `tests/domains/test_v2_v296_explore.py::test_parse_explore_valid_and_invalid` |
| 执行日注入参透传材料头（V2-123：`answer(execution_date=…)` → 材料段「报表期／执行日」两段＋期错位注记＋答案步 payload 机读键 `material_periods`；缺省空串＝零漂移） | `tests/domains/test_v2_v123_material_period.py::test_answer_injects_execution_date_into_material_head` ／ `::test_q07_shape_future_period_material_is_marked_not_current` |
| explore 尝试不合 schema → 回喂拒因恰一次（恰 2 次模型调用）；仍不合 → 强制作答正文落草稿（不判 failed）（V2-96 D5） | `tests/domains/test_v2_v296_explore.py::test_explore_schema_feedback_retry_once_then_force` |
| 核验失败回炉后的作答收口：回炉定稿进收口（`state.draft` 被回炉改写后照常 finalize；四键留痕落回炉步、帧面零新增）（2026-10-18 V2-115） | `tests/domains/test_v2_v2115_repair.py::test_repair_end_to_end_graph_rewrites_unsupported_line`／`::test_repair_end_to_end_graph_zero_delivery_fallback` |
| 答案日期标注＝实际取数窗：`Q10`／`Q14` 形正文零「用户词（日期）」形（`昨天（2026-08-30）`）、改为 `实际取数窗：{TimeWindow.label}`＋原问法对照；起草面即改写（`state.draft` 与片段同源）且改写行过核验不删（2026-10-18 V2-107） | `tests/domains/test_v2_v107_window_label.py::test_q10_shape_no_user_word_date_form`／`::test_q14_shape_window_tail_is_exclusive_end`／`::test_draft_face_rewritten_end_to_end`／`::test_rewritten_annotation_survives_verification` |
| 日期标注单点真源＝`TimeWindow.label`：血缘③行读回往返相等＋载荷键 `LINEAGE_WINDOW_LABEL_KEY` 全仓恰一处定义／装配／读取＋标注模板 runtimev2 面内恰一处定义与消费（2026-10-18 V2-107） | `tests/domains/test_v2_v107_window_label.py::test_lineage_filter_label_round_trip`／`::test_window_label_payload_key_additive_single_write`／`::test_window_annotation_single_point` |
| 日期标注零改面（不猜）：标注词＝实际窗标签／无用户原词／无实际窗／多窗不可归属／异族词／括注非纯日期表达式 ⇒ 原样交付；时间解析算法零改（2026-10-18 V2-107） | `tests/domains/test_v2_v107_window_label.py::test_no_rewrite_when_label_equals_user_word`／`::test_no_rewrite_without_user_time_word_or_label`／`::test_no_rewrite_for_other_window_words`／`::test_no_rewrite_when_paren_is_not_a_window`／`::test_multiple_distinct_labels_not_attributed`／`::test_parse_time_window_algorithm_unchanged` |
| 子问题覆盖信号（2026-10-18 V2-119——落点＝行为 23）：零支撑子问题在作答上下文出现提示行＋作答步 payload 有 `subtask_coverage`（`B-正6`／`NQ-M8` 形离线复现）；材料充分题零提示（零误报）；提示行不改材料、不改 explore 决策（模型自决）；分层判据（强锚在场时数字记号不顶替）；覆盖信号随窗重算（非冻结）＋additive 键恒在场 | `tests/domains/test_v2_v119_subtask_coverage.py::test_subtask_coverage_nq_m8_shape_zero_support`／`::test_subtask_coverage_b_zheng6_shape_zero_support`／`::test_answer_nq_m8_shape_prompt_line_and_payload`／`::test_answer_b_zheng6_shape_prompt_line_and_payload`／`::test_answer_sufficient_material_no_line`／`::test_answer_coverage_section_placement_before_materials`／`::test_answer_coverage_does_not_change_materials_or_explore_decision`／`::test_answer_coverage_recomputed_after_window_grows`／`::test_answer_coverage_payload_present_without_subtasks`／`::test_answer_coverage_payload_key_single_source` |

## 依赖与风险

- 依赖：`context`（材料与 Manifest）、`prompts`（答案轮指令）、`bookkeeping`（模型调用发起面——`call_model` 单点发起）、`gateway_adapter`（模型出口——经 `call_model` 的内部唯一出口，本块不直引）、`state`（状态形状）、`transport`（`text` 帧）。
- 风险与对策：
  1. **「真流式」退化成「收口一次推全量」**（本块最大缺口、易复发）→ 对策：验收以「多段 `text` 帧」为判据；检测手段＝`streaming_segments`。
  2. **引标与增量脱节**（段出了、引用没跟上）→ 对策：每段自带 `citation_seqs` 且必须可解析；检测手段＝`segment_citations_resolve`／`dangling_citation_rejected`。
  3. **缺口只写文字、不给结构化**（回到旧形态）→ 对策：`Gap` 为必填产物；检测手段＝`structured_gaps_all_kinds`。
  4. **答案要求清单两处漂移**（规格复制一份 vs `prompts` 合同）→ 对策：本规格**只引不复述**；检测手段＝人审（阶段 7 接口契约对账）。**登记（W4 对账批，2026-10-16）——V2 发射动作全量枚举无单点真源**：`parsing.CLARIFY_ACTIONS`（澄清面四动作：`discover`／`decompose`／`ask`／`finalize`）与本块 `EMISSION_ACTIONS`（`discover`／`execute`／`ask`／`finalize`——行为 11 剥离的域内判据，V1 `graph.ACTION_KINDS` 字面迁移）**非同族**；**扩域＝规格变更**（须同批对账两处并回设计仓），本批只登记、不扩、不新立第二闭世界。

## 与闸的挂钩表

| 本规格的硬要求 | 挂钩 | 现状 |
|---|---|---|
| 触及模块名已声明 | spec gate | 已进 CI |
| 验收测试逐行有标识 | spec gate | 已进 CI |
| 模型调用经 `bookkeeping.call_model` 发起（单点发起；其内部唯一出口 `gateway_adapter`） | 边界闸 **R7**（出口面：禁直引 `appv2.infra.llm_client`；B6 只管 litellm 出 `infra`。发起面为规格层 doctrine，不设闸） | 已真跑 |
| 不直接 import `langgraph`／`langchain` | 边界闸 **R5b** | 已真跑 |
| 只经 `transport` 公开面发帧（**只经包根**半面） | 边界闸 **R2**（业务相位禁引公共层块的**深层子模块**；`forbidden` 含 `appv2.runtimev2.transport.*`） | 已真跑 |
| 不自行拼 wire 帧／不直连 SSE 通道（另一半） | **无专属闸** → **人审** | 原因：R1–R8 无「不许出现直连帧通路符号」一面；降维（AST 断言）需新增验收行，本批未授权，登记待补 |
| 真流式（多段 `text` 帧） | 测试 `::streaming_segments` | 待实现（阶段 5） |
| 引标可解析 | 测试 `::segment_citations_resolve`／`::dangling_citation_rejected` | 待实现 |
| 结构化缺口（三档闭世界） | 测试 `::structured_gaps_all_kinds`／`::gap_kind_closed_world` | 待实现 |
| 程序不判语义 | 测试 `::no_lexicon_or_regex_in_answering` | 待实现 |
| 发射 JSON 不进答案面（确定性剥离，泄漏=0） | 钉 **`pin-04`**（P0） | 待织网（阶段 5） |
| 明细行集题全量交付（交付行数＝引擎返回行数，丢行=0；与 execution 行为 4 同一界线） | 钉 **`pin-08`**（P0） | 待织网（阶段 5） |
| 材料截断必披露（`material_truncated` notice＋「没用上的部分不作答」声明；逐字＝2026-10-17 EB4b 白话化后文案） | 钉 **`pin-09`**（P1） | 待织网（阶段 5） |
| 起草回声=0（`echo_flag` 恒 0） | 钉 **`pin-13`**（P1） | 待织网（阶段 5） |
| 台账 no_hit 降级交付三段形（油田级邻近可得引用＋逐井「未找到」明示＋指路，零逐井数值冒充——轴④封尺满分形）——落点＝行为 15 | 钉 **`pin-20`**（P1） | 待织网（阶段 5） |
| 排名型子问题强制消费排名观察支（排名序对与排名支序信息一致，不弃支他拼）——落点＝行为 16 | 钉 **`pin-19`**（P1） | 待织网（阶段 5） |
| 跨油田题分源列明油田归属（油田名↔数值／结论配对；「某区块」含糊归属形禁现——C-正6 形）——落点＝行为 17 | 钉 **`pin-03`**（P0） | 待织网（阶段 5） |
| 交付面分层（四类块不进正文；块入增补面＝交付完成） | 测试 `::supplements_carry_blocks_out_of_body`；帧形面挂 `specs/transport.md` 行为 16 | 待实现 |
| 残尾护栏（悬空引导句／光表头／裸标题 → 诚实收口短句；正文其余字面零改）——落点＝行为 19 | 测试 `::dangling_tail_guard_closes_honestly`（判据单点 `degradation.dangling_tail_closing`） | 已实现（2026-10-17 F1 件三） |
| 「不做什么」的纯范围排除（不执行查询／不核验等） | **人审** | 接不上闸的原因：纯范围排除没有形状／存在性／退出码判据；能降维的部分（相位互不 import）已由边界闸 R1 覆盖 |
