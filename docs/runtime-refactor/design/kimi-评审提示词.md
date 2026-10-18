# Kimi 独立评审任务书（统筹 25 票实施方案）

> 你是**独立评审员**。仓库：`/Users/divh/Downloads/petro-agent-platform`。**只读**：不得修改任何代码/测试/规格/票面；只输出评审报告到 stdout。

## 一、必读材料（逐份读，不要跳）

**被评方案（主）**
1. `docs/runtime-refactor/design/统筹方案-L0裁定与实施总方案.md`（总方案＋D-a..D-l 裁定＋10 波顺序）
2. `docs/runtime-refactor/design/统筹方案-供给窗口.md`（设计一，275 行）
3. `docs/runtime-refactor/design/统筹方案-作答提示词.md`（设计二，233 行）
4. `docs/runtime-refactor/design/统筹方案-核验澄清评测.md`（设计三，300 行）

**已有评审（你要复核它们，可推翻）**
5. `docs/runtime-refactor/design/统筹方案-评审-最佳实践.md`（54 项合规：22 符合/24 偏离/8 风险；20 条必须修正）
6. `docs/runtime-refactor/design/统筹方案-评审-副作用与节序.md`（24 对相互作用；~40 例将破用例；10 波顺序）

**设计真源与背景**
7. `docs/runtime-refactor/接手-召回全链路最终决议与运行流程-20261018.md`（四层 L0–L3＋D1–D13）
8. `docs/runtime-refactor/接手-逻辑层方案与统筹清单-20261018.md`（六条逻辑决定＋25 票清单）
9. `docs/runtime-refactor/接手-EB11全量147题修复方案-20261018.md`（P0–P3 原始方案）

**证据面（EB11 全量 147 题实测）**
10. `eval/suite-147/results/EB11-归因.md`（主因矩阵 C1 23/C2 19/C3 8/C4 20/C5 13/C6 1）
11. `eval/suite-147/results/EB11-核实.md`（对抗式核实，已推翻若干判分结论）
12. `eval/suite-147/results/EB11-臆造上下文归因.md`（E1/E2/E7 诱因＋S1–S9 结构性改法）
13. `eval/suite-147/README.md` 与 `eval/suite-147/scoring.md`（147 题册与判分总则）

**仓纪律与票面**
14. `AGENTS.md`（硬纪律：合同驱动、四层 B1–B16、统一出口、每票一提交、6b 票面逐字稿、业务事实零发明、两道机器闸）
15. `tickets/v2/` 下的 `V2-100..V2-124`（有多少读多少；注意评审称 14 张缺票面）

## 二、评审任务（逐项给结论＋file:line 证据）

1. **复核 L0 裁定 D-a～D-l**：逐条判「成立／存疑／不成立」。
   - **重点 D-a**：V2-100 要把「题眼锚/边界/数字记号」判定下沉 L1，但 L3 判据在 `appv2/runtimev2/context/materials.py`，而 `tools/importlinter_v2.toml` R6 禁 runtimev2 直引 retrieval、且 `appv2/tools/__init__.py` 已 import handlers→retrieval（循环风险）。裁定取「新建依赖自由模块 `appv2/text_tokens.py`」。请独立核：**该模块放哪一层才不破 B1–B16／R1–R6？有没有更优解（判据归 retrieval 经 tools 包根 re-export／把 L3 判定上收／其他）？**给推荐与理由。
   - **D-b**：V2-113 取「不改 SSE step 帧、runner 取 `GET /chat/runs/{id}` 详情落档」——核 `synth/S6` 与 `api/chat.py` 的帧键闭世界是否支持该结论。
   - **D-c**：V2-116 默认档设 `delete`＋conftest pin——核是否真能保住既有 ~55 例、`observe` 另立新测是否够。
   - **D-d**：V2-105 判据值域改 `locator.kind ∈ {metric,term,object,relation,family_annotation}`——核实点。
   - **D-e**：V2-124 定义等式判据改「NFKC 后判 ASCII `=`」——核是否能过零词表 AST 闸（`test_v2_verification.py` 相关用例）。
2. **装配上下文最佳实践**：链只追加不改写、环节规章随请求（`call_model(system=…)`）不入链、user 位只动态段、首入包一次性、单点真源、KV 前缀稳定、token 预算与截断披露——逐条核三份设计是否合规。
3. **副作用与回归**：两份评审的「~40 例将破用例」「24 对相互作用」是否可信、有无遗漏；`over_budget`／披露行／三机检字段／`selected_reason`／`RewriteRecord.reason` 两值／帧闭世界／state 字段矩阵等冻结面是否被触碰。
4. **节序**：四条流水线（L1 供给／L3 渲染／作答调用／核验／澄清）的顺序是否与设计意图和代码现状一致；指出所有不一致。
5. **与 EB11 证据自洽**：这些裁定是否真能治 C1 23／C2 19／C3 8／C4 20／C5 13？哪些题**治不到**（给题号）？
6. **两份评审漏掉的点**：你自己发现的（≤5 条），须给证据。

## 三、输出格式（markdown，≤300 行）

```
## 一、总裁定（成立 N／存疑 N／不成立 N）
## 二、D-a～D-l 逐条复核表（裁定｜判定｜证据 file:line｜修正建议）
## 三、装配上下文最佳实践（逐条 合规/偏离/风险）
## 四、副作用与回归（含两份评审的漏项）
## 五、节序核验
## 六、与 EB11 证据自洽（含治不到的题号）
## 七、必须修正清单（严重/中/轻）
## 八、你认为两份评审漏掉的点
## 九、给 Owner 的 3 条最关键结论
```

纪律：只读、可定位（file:line 或题号）、不编造；不确定写「证据不足」；与既有评审冲突处写「既有评审称 X／我核为 Y」。
