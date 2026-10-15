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
| transport | 新增 | `verdict`／`notice` 帧的发射（本块只经其公开面） |
| bookkeeping | 新增依赖 | **写口面**——落 step 记录/notice 经 bookkeeping 唯一写口，只引函数、不引其内部 |

## 接口定义

```python
def verify(state: RunState) -> Verdict: ...

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
3. **无据 → 改写**：没有支撑的句子**改写成「未找到／材料未披露」**（`RewriteRecord.reason="no_material"`），并发 `notice`。
4. **矛盾 → 分列**：两个来源给的数对不上时**分开列、各带出处**（`reason="conflict"`），**不强调和**、不取其一。
5. **归属审**：引用的材料与问句点名的对象对不上号 → `attribution=False`，并把该情形写进缺口。
6. **给出核对结果卡**：`Verdict` **各字段齐备**（五计数 supported／rewritten／split／cited／attribution ＋ `ok`／`gaps` ＋ 行集对账 `delivered_rows`／`obs_rows`）——**缺键＝判失败**。
7. **判据加严（治已知假阳／假阴）**：数值比对**先做边界记号化**（`52` 不得命中 `1520`）；**全角与半角标点先归一**再切分。
8. **零数值断言不恒过**：断言里**没有任何数值**时，**不得自动判过**——仍须有可解析引标支撑，否则计入无据。
9. **`Verdict.ok=False` 才回炉**：只要仍存在无据断言残留，`Verdict.ok=False`（供 `orchestration` 决定回炉）；`Verdict.ok=True` 时不得再改写。
10. **`verdict` 帧的批次落定由 `orchestration` 协调**；本块只保证自产部分（`Verdict`／`notice`）就位。
11. **行集对账（记账面、非拦截阀门）**：verify 面确定性对账**在窗数据行数 vs 答案交付行数**——`Verdict` 产出 `obs_rows`（在窗数据行数）／`delivered_rows`（答案交付行数）两机读字段并随 step payload 落账；**差额>0 且答案面无行集声明 → 补如实注记**；**不改写数值断言、不重试、不拦截**（真源 `docs/runtime-refactor/arch/P7a-交接包与挂账清单.md` A-P7a-38；钉 `pin-12`）。

## 不降级与静默禁令

- **合法降级路径：无**（本模块不降级；核验器不可用时按 fail-closed 取 `ok=False`）。
- 改写、分列、归属失败**都必须产生机读信号**：`verdict`／`notice` 事件（类型取自 `synth/S6-事件与帧目录.md`）＋ step payload 的 `supported`／`rewritten`／`split`／`cited`／`delivered_rows`／`obs_rows` 字段。
- 改写**不得静默**：被改写的原句与原因必须留痕（`RewriteRecord`）；红线原文 `arch/P7a-交接包与挂账清单.md`（A-P7a-37）「不许静默」。

## 验收测试

| 验收标准 | 对应测试 |
|---|---|
| 逐行核验（多句答案逐句判定，非整段判） | `tests/domains/test_v2_verification.py::per_line_check` |
| 数值未在断言里复述 → 判无据并改写 | `tests/domains/test_v2_verification.py::cited_value_must_be_restated` |
| 无据句改写成「未找到」＋ notice 在场 | `tests/domains/test_v2_verification.py::unsupported_rewritten_with_notice` |
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
| 【边界集】单句答案／零材料答案／双源矛盾／全角数字 → 各自落到对应分支 | `tests/domains/test_v2_verification.py::boundary_single_zero_material_conflict_fullwidth` |
| 【保留集】无矛盾、有支撑的普通答案：各字段取值与 `ok=True` 行为不变 | `tests/domains/test_v2_verification.py::retention_clean_answer_unchanged` |

> **测试文件归属（与既有 `tests/domains/test_v2_agent_verify.py` 的关系）**：本块验收测试绑**新建**的 `tests/domains/test_v2_verification.py`——`verification` 是 V2 十七块的新模块（`appv2/runtimev2/verification/`，公开接口 `verify(...) -> Verdict`），与既有 `test_v2_agent_verify.py`（现状 agent-loop 核验步：`verify_draft` 直测／表格·血缘卡·fragment 承载豁免现状行为）所测形状不同；故本块落新文件，既有文件继续覆盖现状核验步、本批不改。

## 依赖与风险

- 依赖：`state`（状态形状）、`transport`（`verdict`／`notice` 帧）。
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
| INV-1 前缀规则（「未找到（材料未披露）：」只挂无据行，行内有引标/观察对齐即放行，理想残余=0） | 钉 **`pin-11`**（落点＝行为 3 无据改写——前缀只随 `RewriteRecord.reason="no_material"` 落，有据行不粘前缀；真源 `eval/results/Q16-对账报告.md` §五 第 3 条（:59）＋ `tickets/v2/V2-54-核验辖域治理.md` 修法三层） | 待织网（阶段 5） |
| verify 对账机读字段（delivered_rows／obs_rows）入 step payload | 钉 **`pin-12`**（落点＝接口 `Verdict` 两字段 ＋ 行为 11 行集对账；真源 `arch/P7a-交接包与挂账清单.md` A-P7a-38） | 待织网（阶段 5） |
| 跨油田题交付分源列明油田归属（C-正6 形禁现） | 钉 **`pin-03`**（本块无独立落点——verify 侧仅行为 5 归属审触发面；答案交付面的分源列明属 prompts 合同「7 条③引用链承接」，prompts 规格落盘后承接，登记备查不落本块验收） | 待织网（阶段 5） |
| 「不做什么」的纯范围排除（不起草／不执行查询等） | **人审** | 接不上闸的原因：纯范围排除没有形状／存在性／退出码判据；能降维的部分（相位互不 import、零 LLM 面）已由边界闸 R1／R8 覆盖 |
