# V2 核验（verification）

状态: 已定稿
来源: `specs/modules.md` `## verification` 卡、`docs/runtime-refactor/walk/15-核验-核验收口.md`、`walk/裁决表.md` §15、`synth/S1`（M7）
版式: `docs/spec-format.md` ｜ 工序: `docs/spec-process.md`

## 目标

答案交付前**逐句核对有没有材料撑着**——**纯程序、零模型**（防编造的机器底线）；没支撑的话**改写掉**，两来源对不上就**分开列**。

## 不做什么

| 不做 | 由谁承担 | 锚点 |
|---|---|---|
| 起草答案、真流式推出 | `answering` | `specs/modules.md` `## answering` |
| 执行查询、产观察 | `execution` | `specs/modules.md` `## execution` |
| 材料段与 Manifest 的编译 | `context` | `specs/modules.md` `## context` |
| **任何模型调用**（核验是零模型铁律的落点） | **本块不调模型**；模型出口属 `gateway_adapter` | `specs/modules.md` `## gateway_adapter` |
| 拿语义模型判「这句话意思上能不能被材料支持」 | **不做**——本块只做**确定性断言级核验**（数值复述／引标可解析）；语义蕴含判定属「第三档」，见「依赖与风险」风险 3 | `walk/00-设计总纲.md` §二 |

## 触及的模块

| 模块 | 改动类型 | 说明 |
|---|---|---|
| verification | 新增 | 断言级核验 ＋ 无据改写 ＋ 矛盾分列 ＋ 归属审 ＋ verdict |
| state | 新增 | verdict／改写行／引用的状态形状；本 spec 只消费 |
| transport | 新增 | `verdict`／`notice` 帧的发射（本块只经其公开面）；**增补面块型闭世界 `SUPPLEMENT_BLOCKS` 与 `supplement` 帧**（2026-10-17 EB3 D2——本块只入收集列，帧由 `orchestration` 发） |
| bookkeeping | 新增依赖 | **写口面**——落 step 记录/notice 经 bookkeeping 唯一写口，只引函数、不引其内部 |

## 接口定义

```python
def verify(state: RunState) -> Verdict: ...
# 注入面（签名以卡为准的展开；关键词注入面）：verify(state, *, bus, supplements=None)——
# 2026-10-17 EB3 D2 增第二处选给注入面 `supplements`（编排块持有的增补面收集列表）：
# 分源块／归属块／血缘五要素整段按产出序入该列表（不进 `state.draft`），帧由 `orchestration` 发。

class Verdict:                           # 对外判定（**不是 answer 侧文本**）
    supported: int                       # 有支撑的句子数
    rewritten: int                       # 无据被改写的句子数
    split: int                           # 因矛盾被分列的组数
    cited: list[int]                     # 被引用的观察序号
    delivered_rows: int                  # 答案交付行数（行集对账——答案面实际交付的数据行数）
    obs_rows: int                        # 在窗数据行数（材料窗内数据链行集支数；与 delivered_rows 确定性对账）
    attribution: bool                    # 归属审是否通过（引的材料与被点名对象对得上）
    ok: bool                             # 是否仍有「无据断言」残留（Verdict.ok=False 才需回炉）
    gaps: list[Gap]                      # 结构化缺口（复用 answering 的 Gap 口径；核验侧产出 kind="unverified"）
class RewriteRecord:
    line: str                            # 被改写的原句
    reason: Literal["no_material", "conflict"]    # 闭世界：无材料／矛盾
class Gap:                               # 复用 answering 的 Gap 口径（字段与闭世界逐字同源）
    kind: Literal["refused", "missing", "unverified"]   # 闭世界
    subtask_id: str | None
    reason: str
```

- **`RewriteRecord.reason` 是闭世界**（`no_material`｜`conflict`）；越界值判失败。
- **`Gap` 复用 `answering` 的口径**（真源 `specs/answering.md`）：字段＝`kind`／`subtask_id`／`reason`，闭世界＝`refused`｜`missing`｜`unverified`；**核验侧产出的缺口 `kind="unverified"`**，越界值判失败。
- **两个维度、不强行映射**：`RewriteRecord.reason`（`no_material`｜`conflict`）回答「**为什么改写这句**」，`Gap` 回答「**哪个子问题有缺口**」——两者是不同维度，不做一一映射。
- **确定性**：同一输入两次运行，`Verdict` 的五个计数与 `ok` **完全一致**（零随机、零模型）。
- **动作档位与机读留痕（2026-10-18 V2-116）**：`verify` 的动作档位经环境变量 `VERIFY_ACTION` 配置（闭世界四值 `off`／`observe`／`repair`／`delete` ＋ **缺省 `delete`**，见行为 14）；step payload 增 **additive** 两键 `verify_mode`（如实档位）／`intended_rewrites`（检出项逐条含原句 `line` 与 `reason`）——`Verdict` 九键不动、`RewriteRecord.reason` 闭世界两值不动。
- **回炉接缝与兜底（2026-10-18 V2-115）**：公开面另增两件（零 LLM、零写面）——`detect_intended(state) -> list[RewriteRecord]`（回炉请求装配与复检的**程序检测单点**，复用 `_verify_lines`）与 `forced_gap_statement(state) -> str`（回炉零交付兜底的**程序确定性诚实说明**，同 V2-106 插入点）；step payload 另增 additive 布尔键 `repair_zero_delivery_fallback`（回炉后正文空 ⇒ 兜底已生效）。回炉环（LLM 改写＋复检＋留痕四键）归 `orchestration`（见行为 15；本块零 LLM 红线 R8 不破）。
- 错误契约：核验器自身抛错 → **不判 `Verdict.ok=True`**（fail-closed），转 `Verdict.ok=False` ＋ 缺口，由 `orchestration` 承接。
- 真源：`specs/modules.md` `## verification` 卡（签名以卡为准）。

## 框架与依赖红线

- **无点名框架**（本模块不引入任何框架）。
- **零 LLM 面（不调模型）**：本块零 LLM 面（R8），**不存在模型调用发起面**——不调模型，模型调用发起面（`bookkeeping.call_model`）不在本块作用面；本块的硬要求是**不调模型**。对应闸：`tools/importlinter_v2.toml` **R8 契约**（`forbidden`＝`appv2.runtimev2.gateway_adapter`；`preconditions`／`verification`／`execution` 禁引）——**真正覆盖本块的是 R8**；**R7**（`forbidden`＝`appv2.infra.llm_client`）只禁「直引 `appv2.infra.llm_client`」一面，对本块仅是「天然满足」（本块既不调模型、也不直引该出口）。验收写法：**AST 机检**（先例 `tests/domains/test_v2_four_phase.py:446`）＋「无旁路」断言。
- **不得直接 import `langgraph`／`langchain`**；对应闸：**R5b 契约**。
- **只经 `transport` 公开面**发帧（「只经包根」半面由 **R2 契约**覆盖）。
- **禁手写替代**：不得自建模型客户端、不得自建帧通路。对应闸：`tools/importlinter_v2.toml` **R8 契约**（`forbidden`＝`appv2.runtimev2.gateway_adapter`，本块禁引）。（**「自建帧通路」一面**：`transport` 的「只经包根」半面由 **R2 契约**覆盖，见「与闸的挂钩表」；另一半「不自行拼 wire 帧」无专属闸 → **人审**，理由：R1–R8 无「不许出现直连帧通路符号」一面；降维（AST 断言）需新增验收行，本批未授权，登记待补。）

## 行为约定

1. **逐行断言级核验**：先把答案剥掉结构性残留（JSON／引标记号），再**逐行**判定；**不是整段判**。
2. **数值须复述（承载豁免）**：被引观察里的**数值须在断言文本里复述**才算有支撑——只凭"引用了一个数"不算；**但 `agg_row`（表格行）／`lineage`（血缘卡）／`fragment` 承载形式下豁免「全数值复述」**——任一数值重叠即支撑、零重叠照改（零重叠不回退；真源 `docs/runtime-refactor/recon/A2-核验规则与归属审.md` R-A2-11——carrier 字面以真源为准）。
3. **无据 → 删句**（2026-10-17 EB3 D3 修正）：没有支撑的句子**整行离场**（**删句，不贴前缀**——旧「改写成「未找到／材料未披露」＋`REWRITE_PREFIX`」前缀形**退役**），留痕三处不得静默：`RewriteRecord.reason="no_material"`（原句＋原因）、`Verdict.rewritten` **如实计数**、`notice`（`unsupported_claim`）——**verdict 计数如实＝不静默**（审计走 verdict 帧 supported／rewritten 计数＋过程档案，禁静默）。真源：`specs/answering.md` 行为 3（「无据的话不写进答案」）；逐字稿＝`docs/runtime-refactor/proposals/EB3-交付面分层与缺陷修复.md` D3。**2026-10-17 F1 件一（删句判据修精度）**：「有数值」的判据面收窄为**计量数值**（带单位／小数／千分位形——判据单点＝`rules.number_tokens`／`line_numbers_are_asserted`）——**标识符**（井号 `W-22`／修井机编号 `渤海 302`）与**日期**（`2026 年 11 月 1 日`）**不算数值断言**（行内只有标识符／日期＝结构承载，原样保留且不计有支撑数）；真机证据＝`eval/results/frames/EB4-D-诱12.json`（run-c6fd52c7：草稿「W-22 井教训侧重…／W-24 井教训侧重…」两行被整段删，交付答案断在裸标题）。**同年同日 F1 件二（跨行支撑比对）× 2026-10-18 V2-103（比对域扩到全窗）**：**无引标数字行**与**本轮窗内全观测**比对（判据单点＝`rules.aligned_indices`，与带引标行的窗内对齐分支同款——零第二份判据），命中即保留、按命中支回填 `cited`（引标落账面）且计有支撑——综述句重组**已引事实**不得删；**窗内零命中＝真无据照删**（数值记号**全等**要求不变——防蒙混），钉 `pin-10`「不得 `cited=[]` 且数字在场」不放宽。旧比对域「同 draft 已 cited 的观察内容集」在单句草稿下必空 ⇒ 权威观测在位仍被删致**零交付**（真机证据＝EB11 `数-排1`：`eval/suite-147/results/EB11-删句原句.jsonl` run-098e7ab2，`supported` 0／`rewritten` 1），故扩为全窗观测；真源＝`tickets/v2/V2-103-无引标数字行比对域扩窗.md`。**2026-10-18 V2-94（核验定性句放行）**：承载片段（`agg_row`／`lineage`／`fragment`）的支撑判据放宽一处——**断言辖域无计量数值记号时，引标可解析即保留**（step payload additive 键 `qualitative_kept` 如实计数）；**有计量数值仍照旧记号比对、对不上照删**（防编造红线不动）；一行引多来源时**承载片段任一支撑即保留**（引标须全可解析——行为 8；**非承载**辖域全须复述不变）。`rewrites`／`Verdict.ok=False` 语义与 `RewriteRecord.reason` 闭世界（两值）**不变**。真机证据＝`eval/results/EB9-判分.md` D-诱12 step13（`rewrites` 4 行全 `no_material`，含 W-24 定性断口检查句；帧 `eval/results/frames/EB9-D-诱12.json`）。**2026-10-18 V2-105（台账卡／口径卡不入数值断言面）**：台账／口径类观察（`locator.kind ∈ CALIBER_KINDS`＝**生产实点五 kind** `metric`／`term`／`object`／`relation`／`family`——真源 `appv2/knowledge/domain.py`（:28-32）；**非**信任级 `ledger`、**非** `_KIND_TRUST` 旧键 `family_annotation`）的记号面只取**口径数值**——册号／节号形（文档结构记号 `§` 紧邻的数，如「99 §2.12」的 `2.12`）不入列（判据单点＝`rules.caliber_numbers_only`；形态值集＋结构记号，**零 CJK 词表**）。真机证据＝EB11 `Q27`：唯一观察 `ledger｜sem_metric#201` 正文含「99 §2.12」⇒ 旧判据回 `('2.12',)` ⇒ 引用该卡的纯定性只读声明句被非承载「全须复述」误删（`supported` 0）；修后该句保留。**2026-10-18 V2-116**：本条的**删句**处置**只在 `delete` 档**成立——档位可配见行为 14（`off` 不检测、`observe`／`repair-fallback` 下检出项**不离场**、交付面＝草稿逐字）。
4. **矛盾 → 分列**：两个来源给的数对不上时**分开列、各带出处**（`reason="conflict"`），**不强调和**、不取其一。（2026-10-17 EB2 D3：分列块**段头去工程腔**——旧「多来源不一致——分源列明（禁止无出处调和）：」→「各来源说法如下，按来源分别列出：」；段头话术仍归本块常量单点，具体文本不落规格。）
5. **归属审**：引用的材料与问句点名的对象对不上号 → `attribution=False`，并把该情形写进缺口。（2026-10-17 EB2 D3：归属审块**段头去工程腔**——旧「跨源归属审——分源列明（题眼锚：{anchors}；禁止无出处调和）：」→「按来源归属如下（题眼：{anchors}）：」，`{anchors}` 占位保持；段内对齐／跨源两面子段头不动。）
6. **给出核对结果卡**：`Verdict` **各字段齐备**（五计数 supported／rewritten／split／cited／attribution ＋ `ok`／`gaps` ＋ 行集对账 `delivered_rows`／`obs_rows`）——**缺键＝判失败**。
7. **判据加严（治已知假阳／假阴）**：数值比对**先做边界记号化**（`52` 不得命中 `1520`）；**全角与半角标点先归一**再切分。**2026-10-18 V2-94**：边界记号化只在**断言辖域有计量数值**时适用；承载片段（`agg_row`／`lineage`／`fragment`）的断言辖域零计量数值记号时记号比对不适用——引标可解析即保留（行为 3 的定性句放行），**非承载**辖域不放宽（全须复述）。
8. **零数值断言不恒过**：断言里**没有任何数值**时，**不得自动判过**——仍须有可解析引标支撑，否则计入无据。**2026-10-18 V2-94（放宽面收窄声明）**：本不恒过条**仍成立**——放宽面仅限**承载片段**（`agg_row`／`lineage`／`fragment`）：其观察**有量值**而断言辖域零计量数值记号时，引标可解析即保留（`qualitative_kept`）；**非承载**（`metric`／`graph` 等）零数值断言仍须观察数值全复述，不自动判过。一行引多引标时承载片段**任一支撑即保留**，引标须全可解析。
9. **`Verdict.ok=False` 才回炉**：只要仍存在无据断言残留，`Verdict.ok=False`（供 `orchestration` 决定回炉）；`Verdict.ok=True` 时不得再改写。
10. **`verdict` 帧的批次落定由 `orchestration` 协调**；本块只保证自产部分（`Verdict`／`notice`）就位。
11. **行集对账（记账面、非拦截阀门）**：verify 面确定性对账**在窗数据行数 vs 答案交付行数**——`Verdict` 产出 `obs_rows`（在窗数据行数）／`delivered_rows`（答案交付行数）两机读字段并随 step payload 落账；**差额>0 且答案面无行集声明 → 补如实注记**；**不改写数值断言、不重试、不拦截**（真源 `docs/runtime-refactor/arch/P7a-交接包与挂账清单.md` A-P7a-38；钉 `pin-12`）。**2026-10-17 EB5c 扩面（缺行 ＋ 引标错位两面入机读对账）**：step payload 增 `rowset_missing`（缺行序号列——引擎行号未被交付者，升序）与 `rowset_aligned`（引标序对齐——交付的引擎行号列是否恰为引擎行号序前 L 项；跳号／整体偏移＝off-by-one 错位）两键，**与注记面三态解耦、恒定落账**（判据单点＝`rules.rowset_audit`，纯计数零语义）。**理由（真机帧 `eval/results/frames/EB3G-L04-22.json`，run-0fb0b64b）**：答案自述「以上共 86 口井已返回」而实际交付 84 行（缺第 24／46 号行）且引标整体错位一格——自述声明的真伪只能由对账事实判，故机读两面不因「答案面有声明」而缺位（注记面〔人读〕三态不变：无声明→注记、有声明→零注记）。注记文案同批携缺行序号列与引标序标记（同一事实的注记面与机读面同源）。**装配面已核实无病**：该 run 的答案面材料 87/87 全渲染（`material_truncated=false`——agg 行属权威族、不承检索帽），即**缺行与错位都在答案面**（模型自编行号 84 行、自述 86 行），不在装配帽／引擎出口面——故本条按 Owner 裁决②取**记账面扩面**（不新增阀门）；「答案面渲染行数＝引擎行数」的行为面仍由合同侧（`prompts` 的行集交付规矩句）与核验侧删句／如实注记共同把守。
12. **核验豁免两类线＋增补面（2026-10-17 EB3 D2／D3）**：
    - **豁免两类线（D3；只豁免「删句」一拍，不改写、不放行支撑判）**：(a) **引擎披露行**——行内含窗 ISO 区间或含披露标记（`封顶`／`截断`／`LIMIT`／`未覆盖`——闭世界四值，单点在 `constants`），**且与材料披露行事实一致**（行内数值记号皆出自血缘卡载荷／引擎注记观察的数值记号集）；(b) **组头行**——行尾落格「：」，或数据表头（含表格列记号 `|`）且**后邻行带引标**；
    - **真无据断言删句**（行为 3）——豁免之外的没支撑句仍整行离场；
    - **块头模式族段剥除**（D2 血缘五要素整段；**2026-10-17 EB5c 扩为族判据**）：判据与段剥离**单点＝`transport.split_block_sections`**（族取值／块头条判据／段界切分同源一处——块型闭世界的文本面随块闭世界落 `transport`；两相位同族同语义）——血缘族段（行内含 `② 来源表`／`⑤ 收口注记`）**整段**（空行界段落）剥出正文入增补面 `lineage`；**例外**＝该段 ≤2 行且带 `[n]` 引标（单行口径说明）保留在正文；**剥除面块型**（引用清单——`SUPPLEMENT_STRIPPABLE_BLOCKS` 成员）段同拍整段离场（程序机械再生产物，正文零留存）；**分源／归属族段不剥**（可能承载模型逐源作答正文；只作在场判据）；
    - **血缘统一走增补面（2026-10-17 EB5c）**：**数据链题血缘在场（`locator.kind="lineage"` 观察在场）⇒ 增补面必有 `lineage` 块**——不以「模型是否把五要素写进草稿」为断（EB2 D1 起材料面只渲染一行口径行，模型多数不再复写全文；EB3 实态＝supplement 携血缘仅 6/97 题、其余只在 `observation` 帧）；模型稿无该段时**原文照抄**观察自带五要素全文入列（入栈序、空行连接、零二次创作）——前端旁路取数统一从增补面取，不必回读观察帧；
    - **分源块／归属块不入 `state.draft`**（D2）：按产出序入编排块持有的增补面收集列（`supplements`）——帧由 `orchestration` 的增补面发射点发（`block="split"`／`"attribution"`）。
    断言：引擎披露行与组头行原样在场（不贴前缀、不被删）且 `rewritten` 不计它们；真无据行离场且 `rewritten` 如实计一；血缘整段入增补面（正文零五要素）＋口径说明留在正文；`state.draft` 不含分源／归属块头。
13. **油田归属对账（2026-10-17 F1 件四——核验增一维，**行级拒收**）**：支撑判定通过的行再过一道**行级归属闸**——被引材料**自带油田名**（名录面闭世界取词：`appv2.tools` 的实体锚解析单点 `entity_anchor_tokens` ＋ `FIELD_NAME_NOUN` 形态过滤；归一与闭世界匹配**引名录面单点、零新造词表字面**）却**全不属题眼所辖油田**、**且该油田名未在本行写明**（＝无分源说明）→ **该行拒收**（按行为 3 的删句族处置：`RewriteRecord.reason="no_material"` ＋ `rewritten` 如实计数 ＋ `unsupported_claim` notice——`RewriteRecord.reason` 闭世界两值不动），并把归属对不上的被引序号列落 step payload 机读键 `field_attribution_mismatch`（**升序去重**；判据单点＝`rules.field_attribution_mismatch`）。**题眼所辖油田**（`rules.aligned_field_names`）＝①题眼锚里自带的油田名（题眼点名油田）∪ ②窗内**非元信息**材料里承载题眼锚的油田名（题眼是井号时，正确油田的材料片段会把井号写在正文里）。四条收窄面（防误伤；均以真机帧取证）：①`field_scope` 空（无题眼锚或点不出油田）＝**审静默**（同行为 5）；②行内写明该油田名＝**分源说明**（`specs/answering.md` 行为 17 的分源列明）→ 不拒收；③本行被引里**只要有一支**落在题眼所辖油田＝**混引不拒**（`eval/results/frames/EB4-D-诱14.json`：一条口径补充行同引 34-5 与 34-8 两油田材料）——拒收只对「整行材料全来自另一油田且没写明」成立；④**元信息／披露类**观察（`lineage`／`notice`——血缘卡、引擎注记、检索窗声明）不入辖域（它们并列多油田名只是记账：`EB4-C-正5.json` 的「缺位名单」形）。真机证据＝`eval/results/frames/Q14M-NQ-M4.json`（NQ-M4：题眼井号体系为 Y 系〔渤中34-8〕，交付行却全引 `《B-渤中34-5油田躺井治理与检泵作业月报-202608》` 的 302／305／22.5 天——跨油田张冠李戴；`eval/results/EB4-终判.md`「新病灶」第 5 条；同期 49 帧真机抽检中本闸仅咬该形 3 行）。**2026-10-18 V2-106（件四全行拒收零交付兜底）**：件四拒收发生（`field_attribution_mismatch` 非空）且**零有支撑句**（`supported == 0`）——即**全行拒收**致实质零交付（`out_lines` 只剩标题；真机形＝`Q14M-NQ-M4.json`）——时，强制产出「本主体未覆盖＋已试什么」**正证据声明**：兜底文本（`ZERO_DELIVERY_FALLBACK`——题眼所辖油田／被拒材料自带油田／已试材料清单〔被引序号＋出处名〕，全为程序确定性渲染、零模型）**追加进正文**（`state.draft`，**非增补面**；插入点在收口 `text="\n".join(out_lines)` **之前**，否则进不了 draft）＋ `unsupported_claim` notice（`ZERO_DELIVERY_NOTICE`——不静默）＋ step payload **additive** 布尔键 `zero_delivery_fallback`（兜底已生效；`Verdict` 九键不动）；**只对 `delete` 档**（`off` 不检测、`observe`／`repair` 检出项不离场＝交付面草稿逐字，见行为 14）；**不放松本条的件四判据**（跨油田混写照拒、行级拒收照旧、`rewritten` 如实计数、`RewriteRecord.reason` 闭世界两值不动）。真源＝`tickets/v2/V2-106-件四零交付兜底.md`。
    **2026-10-18 V2-117（件四**主体归属扩面**——判据面从「油田归属」扩到「题面主体」）**：支撑判定通过、油田归属闸不咬的行再过一道**行级主体归属闸**——被引来源的**主体反思判值**（`state.subject_reflection`：逐来源「属／不属／未知」，材料到手后由编排落——判据单点＝`appv2.runtimev2.orchestration.subjects.reflect_subjects`，本块只读）为「**不属**」（该来源四面上无题面主体命中、却自带**同类**其它主体 token——题面主体是井号时只认「另一口井」，题面主体是油田名时只认「另一油田名」；类＝`well`／`entity` 两值，取词单点 `tools.anchors`）→ **该行拒收**（同删句族处置：`RewriteRecord.reason="no_material"` ＋ `rewritten` 如实计数 ＋ `unsupported_claim` notice），并把序号列落 step payload 机读键 `subject_attribution_mismatch`（**升序去重**；判据单点＝`rules.subject_attribution_mismatch`）——与 `field_attribution_mismatch` **分列**（两维度各有独立值源、可分别判读）。**辖域＝归属审承载族**（`locator.kind ∈ ATTRIBUTION_CARRIER_KINDS`——检索片段／图谱边，与行为 5 归属审同辖域）：判据面是「来源的**报告名**／油田标签／井号」，只对**文档材料来源**成立——权威表行（`agg_row`）／台账行／血缘卡的来源＝表名或账 id，其主体归属由上游闸（单井槽位闸等）管，本闸**不入辖域**（不误伤数据行）。三条收窄面（防误伤）：①`state.subject_reflection` 空／判值全「未知」／无「不属」⇒ **审静默**（不误伤无主体题与泛制度类来源）；②**混引不误伤**——本行被引里**只要有一支**判「属」⇒ 不拒收（跨主体对照题红线：C-正3 两油田四井并列、D-诱14 分源列明）；③**分源说明**——行内写明该来源**身份面**（出处名／报告名／油田标签）的主体类 token（井号／油田名——取词单点 `entity_anchor_tokens`）⇒ 不拒收。**零交付兜底复用**：两维度拒收取并集作 V2-106 兜底判据（`field_attribution_mismatch ∪ subject_attribution_mismatch` 非空 ∧ `supported == 0`）；兜底声明的题眼所辖显示形在油田名面为空时回落到 `state.subjects`（题眼是井号时点得出主体——NQ-M8 形）。真源＝`tickets/v2/V2-117-主体反思与下游加权.md` 任务 2 第三处加权（含「Kimi 评审修正」3：件四拒收后由 V2-106 兜底，本票不重复兜底）。
14. **动作档位可配（2026-10-18 V2-116——配置单点，环境变量 `VERIFY_ACTION`）**：核验动作**四档**，取值闭世界＝`off`／`observe`／`repair`／`delete`（常量单点＝`constants.VERIFY_MODES`／`VERIFY_ACTION_ENV`；**缺省档＝`delete`**——保既有行为，`observe` 档用例显式指定 env）：
    - **`off`**：**完全跳过逐行核验**（不检测、不改写）——`Verdict.supported`／`rewritten`／`cited` 皆空值，交付面＝草稿逐字；
    - **`observe`**：**照常检测（判定逻辑零改）但不删任何行**——检出项入 verify step payload 的 `intended_rewrites`（**每条含原句 `line` 与 `reason`**）＋ `verify_mode`；交付面**逐字等于草稿**；
    - **`repair`**：接 V2-115 回炉口（**已落地**）——检出即**只标红不删**（交付面＝草稿逐字），意图转 `INTENT_REPAIR` 交编排侧回炉环；回炉改写后**复检重入本块**（见行为 15）。回炉面不可用时（如单点回置）等同 `observe`，并记 `verify_mode="repair-fallback"`（如实标注降级档位）；
    - **`delete`**：保留旧行为（无据断言整行离场——行为 3 的删句族），**仅供既有单测显式指定**（缺省保既有行为）。
    计数语义随档标注：step payload 增 `verify_mode`（如实档位）与 `intended_rewrites`（**检出条数**面——非 `delete` 档下检出项**不离场**）；`Verdict.rewritten`／`rewrites` 计数＝**检出条数**（非 `delete` 档下检出 ≠ 离场，故 `unsupported_claim` notice 与 `gaps` 文案按档诚实，不称「删去」）。`Verdict` 九键与 `RewriteRecord.reason` 闭世界（两值）**不变**。档位取值闭世界越界＝**fail-fast 抛错**（不静默回落；经错误契约转 `Verdict.ok=False`＋缺口）。真源＝`tickets/v2/V2-116-校对员三档开关.md`（含末尾「Kimi 评审修正」：默认档 `delete`、conftest env-pin 新建、回归敞口 ~34 例）。

15. **核验失败动作＝回炉修复（2026-10-18 V2-115——程序只检测、模型改写）**：核验的失败动作不再只有「删句」——`repair` 档下，程序**只标红**（沿用行为 1／2／8／13 既有判据：引标可解析、数值记号全等、油田归属闸），把问题行交**编排侧回炉环**（`appv2/runtimev2/orchestration/repair.py`＋`INTENT_REPAIR`，镜像 V2-96 explore 环）由**模型重写**该行（改引标／改写成「本轮材料未覆盖」／删除该行），复检**重入本块**——判据单点仍是 `_verify_lines`（**禁第二份判据**）。四段：
    - **检测（程序，零语义）**：本块新增公开检测口 `detect_intended(state) -> list[RewriteRecord]`（零 LLM、零写面；复用 `_verify_lines`），供回炉请求装配与复检两处消费；
    - **回炉（LLM，语义）**：归编排侧（**本块零 LLM 红线 R8 不破**——本块不调模型、不引 `gateway_adapter`）；回炉请求＝问题行逐条原句 ＋ 本轮窗内材料，应答只许重写这些行、不得新增窗内无据的数值；
    - **复检（程序）**：回炉应用后重入本块核验（同一 `_verify_lines`）；改写轮数到顶（`state.repair_rounds` ≥ `MAX_REPAIR_ROUNDS`）仍不过 ⇒ 编排侧令模型输出**缺位说明**（**不许程序删成空白**）；
    - **零交付兜底（同 V2-106 形）**：回炉后**最终无内容**（无实质行）⇒ 本块在收口 `text="\n".join(out_lines)` **之前**强制追加「已试什么＋仍缺什么」**诚实说明**（程序确定性、零模型——`forced_gap_statement`／`REPAIR_ZERO_DELIVERY_FALLBACK`，占位＝`state.repair_rounds` ＋ 题眼锚）＋ `unsupported_claim` notice ＋ step payload **additive** 布尔键 `repair_zero_delivery_fallback`；判据＝`repair` 档 ∧ 回炉口落地 ∧ 回炉已发生（`repair_rounds > 0`）∧ 无实质行（`_substantive_lines` 零命中，纯形态）。
    **留痕（机读面）**：回炉请求／模型返回／复检结果全落**回炉步** payload（`kind=verify`，标题「核验回炉」——**帧面零新增**：SSE step 帧恰三键不动）四 additive 键 `repair_rounds`／`repair_request`（`{mode, lines, prompt}`——`lines`＝标红原句逐条）／`repair_response`（`{raw, parsed, applied}`——模型原话）／`recheck`（应用后剩余标红行逐条 `{line, reason}`）；本块核验步 payload 的 `verify_mode`／`intended_rewrites`（行为 14）不变。**反编造红线保留**：数值记号全等检测不变（窗内无该数值 ⇒ 模型改写仍保留该数值者复检照咬、不得进交付面）。`RewriteRecord.reason` 闭世界**仍两值**（回炉不新增第 4 值——标红与复检复用既有 `no_material`）。真源＝`tickets/v2/V2-115-核验失败动作回炉修复.md`（含末尾「Kimi 评审修正」）＋`docs/runtime-refactor/design/统筹方案-核验澄清评测.md` §2.2。

## 不降级与静默禁令

- **合法降级路径：无**（本模块不降级；核验器不可用时按 fail-closed 取 `ok=False`）。
- 改写、分列、归属失败**都必须产生机读信号**：`verdict`／`notice` 事件（类型取自 `synth/S6-事件与帧目录.md`）＋ step payload 的 `supported`／`rewritten`／`split`／`cited`／`delivered_rows`／`obs_rows` 字段。**2026-10-17 EB3 D3**：无据断言的处置由「改写」改「**删句**」——**如实计数即不静默**（`verdict.rewritten` ＋ `RewriteRecord` 原句＋ `notice` 三处齐）；正文不再出现前缀残句。**2026-10-18 V2-116**：非 `delete` 档（`observe`／`repair-fallback`）下**未删行**——信号三处齐不变，但 `notice`／`gaps` 文案按档诚实（称「检出／只记录不删」，不称「删去」；检出项逐条落 step payload `intended_rewrites`）。**2026-10-18 V2-115**：`repair` 档的回炉步留痕四键（`repair_rounds`／`repair_request`／`repair_response`／`recheck`）＋ 回炉零交付兜底 notice（`unsupported_claim`）＋ payload `repair_zero_delivery_fallback`——回炉请求／模型返回／复检结果三面齐，不静默。
- 改写**不得静默**：被改写的原句与原因必须留痕（`RewriteRecord`）；红线原文 `arch/P7a-交接包与挂账清单.md`（A-P7a-37）「不许静默」。

## 验收测试

| 验收标准 | 对应测试 |
|---|---|
| 逐行核验（多句答案逐句判定，非整段判） | `tests/domains/test_v2_verification.py::per_line_check` |
| 数值未在断言里复述 → 判无据并**删句** | `tests/domains/test_v2_verification.py::cited_value_must_be_restated` |
| 无据句**删句**（整行离场）＋ notice 在场＋ `rewritten` 计数如实 | `tests/domains/test_v2_verification.py::unsupported_rewritten_with_notice` |
| 豁免两类线（引擎披露行／组头行）不被删句——只豁免删句、不改写 | `tests/domains/test_v2_verification.py::rewrite_exempt_disclosure_and_group_head` |
| 真无据句被删且 verdict 计数在位（不静默） | `tests/domains/test_v2_verification.py::unsupported_deleted_with_verdict_count` |
| 组引标不被改（组头行组引标 `[m]–[n]` 原样在场） | `tests/domains/test_v2_verification.py::group_citation_marker_untouched` |
| 血缘五要素整段入增补面（正文零五要素；口径说明例外保留） | `tests/domains/test_v2_verification.py::lineage_paragraph_stripped_to_supplement` |
| 血缘统一走增补面：数据链题血缘在场 ⇒ 增补面必有 `lineage` 块（模型稿无该段时原文照抄观察全文；2026-10-17 EB5c） | `tests/domains/test_v2_agent_verify.py::test_unsupported_claim_rewritten`／`::test_contradiction_split_source` |
| 分源块／归属块不入 `state.draft`（入增补面，正文＝模型稿） | `tests/domains/test_v2_verification.py::conflict_split_not_merged`／`::attribution_mismatch` |
| 矛盾来源分列、各带出处、不调和 | `tests/domains/test_v2_verification.py::conflict_split_not_merged` |
| 归属对不上 → `attribution=False` ＋ 缺口 | `tests/domains/test_v2_verification.py::attribution_mismatch` |
| `Verdict` 各字段齐备；缺字段判失败 | `tests/domains/test_v2_verification.py::verdict_all_keys` |
| 边界记号化：`52` 不命中 `1520` | `tests/domains/test_v2_verification.py::token_boundary_no_substring_false_positive` |
| 全角／半角标点先归一后切分 | `tests/domains/test_v2_verification.py::fullwidth_normalized_before_split` |
| 零数值断言不自动判过 | `tests/domains/test_v2_verification.py::no_number_assertion_not_auto_pass` |
| 不确定性：同输入两次运行 verdict 完全一致 | `tests/domains/test_v2_verification.py::deterministic_repeatable` |
| `RewriteRecord.reason` 越界取值 → 判失败 | `tests/domains/test_v2_verification.py::rewrite_reason_closed_world` |
| 核验器抛错 → fail-closed 取 `ok=False`（不静默放行） | `tests/domains/test_v2_verification.py::verifier_error_fail_closed` |
| 本模块零 LLM（AST＋import 双证） | `tests/domains/test_v2_verification.py::no_model_call_in_verification` |
| 程序侧无词表／正则语义判断（AST 扫描；豁免面＝形态处理／集合成员判定） | `tests/domains/test_v2_verification.py::no_lexicon_or_regex_in_verification` |
| 机读信号在场（verdict／notice ＋ step payload） | `tests/domains/test_v2_verification.py::verification_signal_present` |
| 行集对账：`delivered_rows`／`obs_rows` 入 `Verdict` 与 step payload；差额>0 且答案面无行集声明 → 补如实注记（不改写、不拦截） | `tests/domains/test_v2_verification.py::row_reconciliation_bookkeeping` |
| 行集对账扩面（2026-10-17 EB5c）：`rowset_missing`（缺行序号列）／`rowset_aligned`（引标序对齐）两键恒落账——自述声明不改其在场；正文零改、不拦截、不产通知 | `tests/domains/test_v2_verification.py::rowset_audit_l0422_offset_caught` |
| 【边界集】单句答案／零材料答案／双源矛盾／全角数字 → 各自落到对应分支 | `tests/domains/test_v2_verification.py::boundary_single_zero_material_conflict_fullwidth` |
| 【保留集】无矛盾、有支撑的普通答案：各字段取值与 `ok=True` 行为不变 | `tests/domains/test_v2_verification.py::retention_clean_answer_unchanged` |
| 数值断言只认**计量数值**：标识符（井号／修井机编号）与日期不算数值断言（行原样保留）；量值行照删（2026-10-17 F1 件一；2026-10-18 V2-103：**窗内零命中**的量值行照删——窗内命中者保留并回填 `cited`） | `tests/domains/test_v2_verification.py::identifier_and_date_not_numeric_assertion` |
| 无引标数字行 × **本轮窗内全观测**比对：命中即保留并计有支撑（按命中支回填 `cited`，文本零改）；**窗内零命中**照删（2026-10-17 F1 件二；2026-10-18 V2-103 比对域扩窗） | `tests/domains/test_v2_verification.py::uncited_line_reconciled_with_draft_cited` |
| `数-排1` 形离线复现：权威观测在窗 ⇒ 无引标数字行**不再零交付**（保留＋回填 `cited`；2026-10-18 V2-103） | `tests/domains/test_v2_verification.py::uncited_numeric_line_aligned_with_window_observation` |
| 真无据仍删：窗内确无该记号 ⇒ 照删；数值记号**全等**（`52` 不命中 `1520`）（2026-10-18 V2-103） | `tests/domains/test_v2_verification.py::uncited_numeric_line_without_window_hit_still_deleted` |
| 油田归属对账：整行材料全属另一油田且无分源说明 → 行拒收＋机读键 `field_attribution_mismatch`；分源说明／同油田／混引／无题眼锚 → 不拒收（2026-10-17 F1 件四；2026-10-18 V2-106 起全行拒收同步断言零交付兜底正证据） | `tests/domains/test_v2_verification.py::cross_field_line_rejected_without_split_note` |
| 件四**全行拒收**零交付兜底：正文追加「本主体未覆盖＋已试什么」正证据（`state.draft` 非空）＋ `unsupported_claim` notice ＋ payload `zero_delivery_fallback`（2026-10-18 V2-106） | `tests/domains/test_v2_verification.py::test_zero_delivery_field_mismatch_fallback_positive_evidence` |
| 件四**主体归属扩面**（V2-117）：来源反思判「不属」且行内无分源说明 → 行拒收＋机读键 `subject_attribution_mismatch`；判「属」混引／分源说明／反思空 ⇒ 不拒收（NQ-M8 形离线复现含零交付兜底） | `tests/domains/test_v2_v117_subject_reflection.py::test_nq_m8_shape_cross_subject_line_rejected_with_fallback`／`::test_subject_attribution_mismatch_field_scope_still_independent` |
| 跨主体对照题不受损（V2-117）：C-正3（未点名主体）／D-诱14（点名 34-5 分源列明）／两油田四井并列 ⇒ 分源列明逐字保留、零拒收 | `tests/domains/test_v2_v117_subject_reflection.py::test_cross_subject_c_zheng3_no_named_subject_silent`／`::test_cross_subject_d_you14_named_field_sources_aligned`／`::test_cross_subject_two_fields_four_wells_both_aligned` |
| 零交付兜底不越红线：跨油田混写行仍拒；有支撑行在场或非件四零交付 ⇒ 不兜底（2026-10-18 V2-106） | `tests/domains/test_v2_verification.py::test_zero_delivery_fallback_requires_field_mismatch_and_empty_support` |
| 零交付兜底只在 `delete` 档：`observe` 交付＝草稿逐字、兜底不触发（2026-10-18 V2-106） | `tests/domains/test_v2_verification.py::test_zero_delivery_fallback_not_in_observe_mode` |
| 承载片段定性句放行：断言辖域零计量数值记号 ＋ 引标可解析 → 保留并计 `qualitative_kept`（2026-10-18 V2-94） | `tests/domains/test_v2_verification.py::qualitative_fragment_claim_kept` |
| 有计量数值的承载断言仍照旧记号比对、对不上照删（防编造红线不动；2026-10-18 V2-94） | `tests/domains/test_v2_verification.py::numeric_claim_still_deleted` |
| 一行多引标：承载片段任一支撑即保留（引标须全可解析；2026-10-18 V2-94） | `tests/domains/test_v2_verification.py::multi_citation_any_support` |
| 删行后正文无半句残渣（整行离场、不贴前缀；2026-10-18 V2-94） | `tests/domains/test_v2_verification.py::deleted_line_leaves_no_residue` |
| EB9 D-诱12 形复现：4 行不再全删（至少 W-24 定性断口检查句保留；2026-10-18 V2-94） | `tests/domains/test_v2_verification.py::eb9_d12_shape_qualitative_line_kept` |
| 判据值域＝**生产实点五 kind**（非信任级 `ledger`、非旧键 `family_annotation`；2026-10-18 V2-105） | `tests/domains/test_v2_verification.py::test_caliber_kinds_production_five_match` |
| 台账／口径卡（五 kind 各一）记号面只取口径数值：册号／节号（`§` 紧邻的数）不入面——纯定性句不再被删（2026-10-18 V2-105） | `tests/domains/test_v2_verification.py::test_caliber_kind_section_number_not_deleted` |
| 口径数值仍可核：口径卡计量数值照旧须复述、对不上照删（2026-10-18 V2-105） | `tests/domains/test_v2_verification.py::test_caliber_value_still_checkable` |
| EB11 `Q27` 形离线复现：只读声明句保留、`supported` 0→≥1（2026-10-18 V2-105） | `tests/domains/test_v2_verification.py::test_q27_shape_readonly_declaration_kept` |
| 动作档位缺省＝`delete` 且 env-pin 机制在场（conftest autouse 夹具；2026-10-18 V2-116） | `tests/domains/test_v2_verification.py::verify_action_env_pinned_delete_by_conftest` |
| 缺省档（env 未设）＝`delete`：删句＋留痕＋`verify_mode` 标注（2026-10-18 V2-116） | `tests/domains/test_v2_verification.py::verify_mode_default_delete_when_env_unset` |
| `delete` 显式档行为与现 HEAD 一致（2026-10-18 V2-116） | `tests/domains/test_v2_verification.py::verify_mode_delete_explicit_matches_head` |
| `observe`：交付＝草稿逐字＋检出项入 `intended_rewrites`（原句＋reason）＋`verify_mode`（2026-10-18 V2-116） | `tests/domains/test_v2_verification.py::verify_mode_observe_delivery_verbatim_and_records` |
| `observe` 下矛盾检出只记不删（`reason="conflict"` 原句入 `intended_rewrites`；2026-10-18 V2-116） | `tests/domains/test_v2_verification.py::verify_mode_observe_conflict_detected_not_deleted` |
| `off`：完全跳过逐行核验——交付＝草稿逐字、零检出（2026-10-18 V2-116） | `tests/domains/test_v2_verification.py::verify_mode_off_skips_check_delivery_verbatim` |
| `repair`：V2-115 未落地 → 等同 `observe` 并记 `verify_mode="repair-fallback"`（2026-10-18 V2-116） | `tests/domains/test_v2_verification.py::verify_mode_repair_fallback_equals_observe` |
| 档位闭世界越界 → fail-fast（转 `ok=False`＋缺口，不静默回落；2026-10-18 V2-116） | `tests/domains/test_v2_verification.py::verify_mode_invalid_value_fail_closed` |
| `observe` 辖域＝逐行核验输入：块剥除照常、仅「无据删句」停（2026-10-18 V2-116） | `tests/domains/test_v2_verification.py::verify_mode_observe_block_strip_still_applies` |
| 回炉检测口＝程序单点（复用 `_verify_lines`）：只报标红行、零写面（2026-10-18 V2-115） | `tests/domains/test_v2_v2115_repair.py::test_detect_intended_is_program_detection_single_point` |
| `repair` 档落地：检出即标红（不删）＋ `verify_mode="repair"` ＋ `next_intent="repair"`（2026-10-18 V2-115） | `tests/domains/test_v2_verification.py::test_verify_mode_repair_landed_flags_and_routes_repair` |
| `repair` 且回炉口不可用 → `repair-fallback` 等同 `observe`（如实降级标注；2026-10-18 V2-115／V2-116） | `tests/domains/test_v2_verification.py::test_verify_mode_repair_fallback_equals_observe` |
| 回炉四形：①引标可修正（改引标）／②真无据（改写成缺位）／③零交付（强制诚实说明）／④反编造（窗内无该数值不得保留）（2026-10-18 V2-115） | `tests/domains/test_v2_v2115_repair.py::test_repair_citation_fixable_rewrites_citation`／`::test_repair_truly_unsupported_rewritten_as_gap`／`::test_repair_zero_delivery_forces_honest_statement`／`::test_repair_anti_fabrication_number_not_kept` |
| 缺位说明自身仍无据 ⇒ 交程序确定性诚实说明（防「模型缺位说明」成新编造面）（2026-10-18 V2-115） | `tests/domains/test_v2_v2115_repair.py::test_repair_gap_statement_dirty_falls_back_to_program_statement` |
| 回炉留痕：回炉请求／模型返回／复检结果全落回炉步 payload（含逐行原句）（2026-10-18 V2-115） | `tests/domains/test_v2_v2115_repair.py::test_repair_citation_fixable_rewrites_citation` |
| 端到端（脚本化 completer）：`数-排1` 形不再零交付；`D-诱1` 形 415 不再被删（2026-10-18 V2-115） | `tests/domains/test_v2_v2115_repair.py::test_repair_mode_shupai1_shape_no_zero_delivery`／`::test_repair_mode_dy1_shape_415_kept` |
| 端到端（四相位图＋脚本化 completer）：编造行回炉重写 → 交付携正确数值、编造数值零残留（2026-10-18 V2-115） | `tests/domains/test_v2_v2115_repair.py::test_repair_end_to_end_graph_rewrites_unsupported_line`／`::test_repair_end_to_end_graph_zero_delivery_fallback` |

> **测试文件归属（与既有 `tests/domains/test_v2_agent_verify.py` 的关系）**：本块验收测试绑**新建**的 `tests/domains/test_v2_verification.py`——`verification` 是 V2 十七块的新模块（`appv2/runtimev2/verification/`，公开接口 `verify(...) -> Verdict`），与既有 `test_v2_agent_verify.py`（现状 agent-loop 核验步：`verify_draft` 直测／表格·血缘卡·fragment 承载豁免现状行为）所测形状不同；故本块落新文件，既有文件继续覆盖现状核验步、本批不改。

## 依赖与风险

- 依赖：`state`（状态形状）、`transport`（`verdict`／`notice` 帧）、`tools`（**只引 `entity_anchor_tokens`／`normalize_anchor_text` 公开面**——行为 5 题眼锚，流水 56-W4 登记；**行为 13 的油田名取词同一单点**＋`FIELD_NAME_NOUN` 形态过滤，2026-10-17 F1 件四）。
- 风险与对策：
  1. **召回／误杀从未与人工标注度量过**（本块最大空白，Owner 裁决 Q-B「要补」）→ 对策：**用人工标注样本算核验的精确率／召回率**（拦错的 vs 放过的），**进测试网**（不是本块实现的运行时能力）；检测手段＝测试网的人工标注对照。
  2. **子串假阳／假阴**（历史病例：`52` 命中 `1520`；全角「：」切分错）→ 对策：边界记号化 ＋ 全角归一；检测手段＝`token_boundary_no_substring_false_positive`／`fullwidth_normalized_before_split`。
  3. **「第三档」语义蕴含判定**（用更强模型提准确率）→ **不做**：本块零模型是机器底线；若将来要引第三档，须先裁「是否允许破零模型」并记 ADR（真源 `research/最佳实践-节点-核验.md` 的第三档主张）。
  4. **溯源粒度**（行＋引标 vs 文档+段落+版本）→ 按 Owner 裁决 Q-C **保持「行＋引标」**（只读问答、单租户够用）。
  5. **核验对增量引标（承接真流式）**：答案真流式后，核验要能对上**增量**里的引标；本块现状行为 1 只覆盖「剥结构性残留→逐行判定」，对**增量的引标对齐尚未落点**——登记为**跨块待办**，随 `answering` 真流式协同定稿（真源 `walk/裁决表.md` §14-A）。

## 与闸的挂钩表

| 本规格的硬要求 | 挂钩 | 现状 |
|---|---|---|
| 触及模块名已声明 | spec gate | 已进 CI |
| 验收测试逐行有标识 | spec gate | 已进 CI |
| 零 LLM 面（不调模型、不存在发起面） | 边界闸 **R8** ＋ AST 机检 `::no_model_call_in_verification` | R8 已真跑；AST 测试待实现 |
| 不直接 import `langgraph`／`langchain` | 边界闸 **R5b** | 已真跑 |
| 只经 `transport` 公开面发帧（只经包根半面） | 边界闸 **R2** | 已真跑 |
| 不自行拼 wire 帧／不直连 SSE 通道（另一半） | **无专属闸** → **人审** | 原因：R1–R8 无「不许出现直连帧通路符号」一面；降维（AST 断言）需新增验收行，本批未授权，登记待补 |
| 程序不判语义 | 测试 `::no_lexicon_or_regex_in_verification` | 待实现（阶段 5） |
| 判据加严（边界记号化／全角归一） | 测试 `::token_boundary_no_substring_false_positive`／`::fullwidth_normalized_before_split` | 待实现 |
| 质量度量（精确率／召回率） | **测试网**（人工标注对照，非运行时闸） | 待织网（阶段 5） |
| 题眼锚定归属审（答案引用的报告≠题干点名报告即失败） | 钉 **`pin-01`**（落点＝行为 5 归属审 → `attribution=False` ＋缺口留痕） | 待织网（阶段 5） |
| 答案面禁现无据差值／无据口径框架（「252 天」型：全文零出现的数值不得充当答案） | 钉 **`pin-02`**（落点＝行为 2 数值须复述 ＋ 行为 3 无据改写） | 待织网（阶段 5） |
| citation 落账（引标对应窗内切片；不得 `cited=[]` 且数字在场） | 钉 **`pin-10`**（落点＝行为 8 零数值断言不恒过 ＋ `Verdict.cited`） | 待织网（阶段 5） |
| INV-1 前缀规则（「未找到（材料未披露）：」只挂无据行，行内有引标/观察对齐即放行，理想残余=0）——**2026-10-17 EB3 D3 已退役**：无据断言改**删句**（前缀不再落正文），留痕面＝`RewriteRecord`＋`Verdict.rewritten` 计数＋`notice`；豁免两类线见行为 12 | 钉 **`pin-11`**（**判据平移**：行为 3 的删句与如实计数即其落点；真源 `eval/results/Q16-对账报告.md` §五 第 3 条（:59）＋ `tickets/v2/V2-54-核验辖域治理.md` 修法三层） | 待织网（阶段 5） |
| verify 对账机读字段（delivered_rows／obs_rows）入 step payload | 钉 **`pin-12`**（落点＝接口 `Verdict` 两字段 ＋ 行为 11 行集对账；真源 `arch/P7a-交接包与挂账清单.md` A-P7a-38） | 待织网（阶段 5） |
| 对账缺行／错位两面机读落账（`rowset_missing`／`rowset_aligned`，2026-10-17 EB5c） | 测试 `::rowset_audit_l0422_offset_caught`（L04-22 真机帧形） | 已实现 |
| 血缘统一走增补面（数据链题血缘在场 ⇒ `lineage` 块必在场；2026-10-17 EB5c） | 测试 `::test_unsupported_claim_rewritten`／`::test_contradiction_split_source` | 已实现 |
| 跨油田题交付分源列明油田归属（C-正6 形禁现） | 钉 **`pin-03`**（**2026-10-17 F1 件四起本块有独立落点**：行为 13 油田归属对账——被引材料归属另一油田且行内无分源说明 ⇒ 行拒收＋机读键 `field_attribution_mismatch`，测试 `::cross_field_line_rejected_without_split_note`；答案交付面的分源列明仍属 prompts 合同「7 条③引用链承接」，两处互补） | 部分织网（核验侧已实现；答案面合同侧随 prompts 规格） |
| 「不做什么」的纯范围排除（不起草／不执行查询等） | **人审** | 接不上闸的原因：纯范围排除没有形状／存在性／退出码判据；能降维的部分（相位互不 import、零 LLM 面）已由边界闸 R1／R8 覆盖 |
