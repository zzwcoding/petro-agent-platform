# parsing 规格评审（独立评审代理用）

- 日期：2026-10-15 ｜ 状态：**框架已建，发现清单待填（本文件由起草方留空，评审代理填）**
- 被评对象：`specs/parsing.md`（起草稿——十节版式，真源 `docs/spec-format.md`）
- 评审工序：起草 → **独立评审** → 逐条处置（L0 必须清零）→ 修订 → 复审 → 定稿（真源 `docs/runtime-refactor/规划.md` §三 工序纪律六步）
- 评审人纪律：全新上下文、只产发现不改任何现存文件；每条发现带证据锚点＋建议处置；**L0 清零前 `specs/parsing.md` 不得定稿**。

## 评审基准（只读参考）

- 版式与三判据：`docs/spec-format.md` §二（十节硬要求）／§二之二（节标题逐字）／§三（可判真伪／数字单点／闸在前面）
- 块真源：`specs/modules.md` `## parsing` 卡（职责／公开接口两函数／依赖／Seam／测试计划「缺字段／超限／引号异常分支；同类行多次出现不静默覆盖」）；`docs/runtime-refactor/eng/00-阶段2-模块划分草案.md` §三 B
- 归责尺子：`docs/runtime-refactor/walk/判断归责表.md`——parsing 是**纯结构判定块**，**重点扫「解析滑成程序语义判断」与「语义判断误落本块」两侧**
- 行为真源抽查面（起草方实读并锚，供评审代理抽查）：
  - 解析现状：`docs/runtime-refactor/recon/A1-头部常量与解析校验.md`（R-A1-12…R-A1-36＋D-A1-01…D-A1-18）、`docs/runtime-refactor/recon/L1a-子任务前半.md`（R-L1a-01…R-L1a-41）、`docs/runtime-refactor/recon/L1b-子任务后半.md`（R-L1b-01…R-L1b-21）、`docs/runtime-refactor/recon/C-理解与legacy决策节点.md`（R-C-09／R-C-10／R-C-24）、`docs/runtime-refactor/recon/E1-澄清节点.md`（R-E1-10…R-E1-16）、`docs/runtime-refactor/recon/E2-工具匹配节点.md`（R-E2-04…R-E2-07）、`docs/runtime-refactor/recon/I2b-RunState全字段.md`（`executed_payloads`／`empty_probes` 字段面）
  - 决策面：`docs/runtime-refactor/walk/04-理解-读题步.md` §七（统一 JSON Owner 直令）、`docs/runtime-refactor/walk/05-理解-定路由.md` §七（解析严格、不取默认）、`docs/runtime-refactor/walk/09-澄清-分解问题.md` §七（子问题无依赖）、`docs/runtime-refactor/walk/11-匹配-工具阀.md` §七与末「补注」（参数枚举收紧）、`docs/runtime-refactor/walk/裁决表.md` §04-B／§07／§11＋项目级裁决 #12/#13
  - 治理票：`docs/runtime-refactor/arch/P4b-票堆V2-56至65.md`（A-P4b-10/11/12 拒因带定位；A-P4b-37/38/39 引号三层；A-P4b-13 回喂线）、`docs/runtime-refactor/arch/P6b-票堆V2-80系列后半.md`（A-P6b-05 机器拒因原文零改动；A-P6b-24/34 迁移文本不变）
  - 单元归属：`docs/runtime-refactor/synth/S1-重写单元与证据交叉矩阵.md`（H4 解析与载荷定型（主体＝A1 L392-665）＋H11 子任务与发射 schema（L1a/L1b 全部）；表 B：V2-37 指纹面→H4）、`docs/runtime-refactor/synth/S4-调用图.md`（节点→helper 面；结构-1 legacy decision 整体废弃）
  - 已定稿消费方对账：`specs/understanding.md`（接口定义／行为 5／7／错误契约）、`specs/clarification.md`（接口定义 `ClarifyOutcome`／行为 8）、`specs/tool_matching.md`（接口定义／「不做什么」行／风险 4——「闸件本体归 parsing（发射指纹）＋ state（限额）」）、`specs/answering.md`（行为 11／14——发射剥离与回声观测面）、`specs/state.md`（行为 10 限额键面）、`specs/execution.md`（行为 13 空手指纹闸）、`specs/agent-loop.md`（行为 3「decision 出口同参重投闸保留」）
  - 交叉核对（起草方实读，确认**零落点**）：`docs/runtime-refactor/walk/02-理解-词面安全阀.md`、`docs/runtime-refactor/walk/03-理解-禁用词闸.md`（两道闸族归 `gate`／模型侧，parsing 无落点——评审可复核该判定）
  - 逐字稿载体（V1 现行代码）：`appv2/runtime/subtask.py`（L48-L58 常量／L61-L110 提取与拒因带定位／L116-L176 载荷类／L179-L290 澄清面／L296-L375 匹配面／L381-L428 引号自修）
- 钉清单：`docs/runtime-refactor/eng/04a-应钉行为清单.md`（**起草方核实结论：pin-04／pin-13 均不落本块**——见「重点核对项」5）
- 双闸＋边界闸（评审人本地复跑，命令与期望输出见起草方留档）：
  - `uv run python tools/check_specs.py`（期望 PASS 0 警告）
  - `uv run python tools/ref_resolvable.py check`（期望绿）
  - `uv run lint-imports --config tools/importlinter_v2.toml`（期望 Contracts: 18 kept, 0 broken）

## 重点核对项（起草方自评风险，供优先看）

1. **卡与规格分叉（返回形＋成员展开＋载荷类定义点）**：卡面公开接口为两函数且 `parse_question_group` 为**初拟返回形**（问题组容器单件），本规格按 V1 逐字迁移形（四动作定形＋拒因正文）展开族名单（`parse_tool_match`／共用件三件／载荷四类／指纹器材四件），并宣告载荷定型类**物理定义点在 parsing**（依据＝卡面 `parse_understanding` 已在本块引用 `Understanding | Direct` ＋R3 禁 parsing 引 understanding 的组合推论）。请评审判：①族成员展开是否属卡面职责（「模型输出解析、发射 schema 校验、子任务与问题组载荷定型」）的具体化（判例参照 `docs/runtime-refactor/spec-review/prompts-评审.md` P-08「非新公开类型」）还是构成卡缺公开成员（判例参照 `docs/runtime-refactor/spec-review/state-评审.md` S-2）；②`parse_question_group` 返回形差异「以卡为准」还是「以迁移照抄为准」；③载荷类定义点宣告是否越出本块单写者权限（登记件是否足够）。
2. **迁移照抄 vs 数字单点两处相抵**：行为 7 断言拒因正文「逐字迁移、零改动」（A-P6b-05），但 V1 预算拒文内嵌数值（载体 L258-L261）与 V1 缺省裸字面（D-L1a-12）在「数字单点」判据下是病灶；行为 16 声明「待裁」。请评审：该双轨（照抄＋差异点登记）是否有自相矛盾处、行为 4／7／16 三处是否口径一致；另核「V2 定案差异点②」（V1 两处裸抛收口为拒因）是否属未授权改形。
3. **与消费方交接面三处未定案**：①拒因正文（`str`）↔ `clarification` 的 `ClarifyRejection`／`tool_matching` 的 `ToolMatchRejection` 转换点归属（风险 5）；②理解面 `None`→`UnderstandingParseError` 的分工（本块不抛 vs understanding 抛，风险 6）；③同参重投闸的触发面与拦截落点（本块只锁指纹器材纯函数面——`specs/tool_matching.md` 风险 4／`specs/execution.md` 行为 13／`specs/agent-loop.md` 行为 3 三处对读，风险 4）。请评审逐条判「两头都认／两头都不认／一头认得住」。
4. **闸半覆盖与降维诚实性**：**亲读 `tools/importlinter_v2.toml` 核实**——R2（forbidden 含 `appv2.runtimev2.parsing.*`）／R3（source 含 `appv2.runtimev2.parsing`，forbidden 恰七个业务相位）／R5b／R6／R7 的编号与覆盖面是否与规格挂钩表逐行相符；「R3 半覆盖」声明与「零模型面无专属闸（R8 只列三相位）」声明是否属实；「禁手写替代（共用件单点）」无闸、只靠 `::shared_helpers_single_source` 测试的降维是否充分。注意：`appv2/runtimev2/parsing/` 现仅有占位 `__init__.py`——边界闸对本块是**契约空过**（同 prompts 评审先例）。
5. **pin-04／pin-13 核实结论自曝（起草方逐条核实：两钉均不落本块）**：pin-04「发射 JSON 不得进答案面（emission_strip 确定性剥离）」——落点在 `specs/answering.md` 行为 11＋其挂钩表（已定稿在册，测试 `::emission_strip_zero_leak`），剥离动作属答案面（起草／收口相位），**不落 parsing**；pin-13「起草回声=0（`echo_flag` 恒 0）」——两侧已落：合同侧 `specs/prompts.md` 行为 13（动词钉死句＋答案要求⑦），观测面 `specs/answering.md` 行为 14（测试 `::echo_flag_zero`），**parsing 无第三面缺口，本块不挂**（防一头两认）。请评审复读 `docs/runtime-refactor/eng/04a-应钉行为清单.md` :13／:22 两行原文与上述两侧登记，判「不落本块」是否成立（漏挂／错挂两向）。
6. **真源缺口（起草时未决——评审可直接查红/黄）**：①预算拒因内嵌数值是否可插槽化（无裁决文本；`docs/runtime-refactor/arch/P6b-票堆V2-80系列后半.md` A-P6b-05 只说「机器拒因原文零改动」）；②JSON 重复键形（解析后取后者）无真源裁决——卡面测试计划「同类行多次出现不静默覆盖」的 V2 对应面（风险 7⑥）；③`docs/runtime-refactor/synth/S1-重写单元与证据交叉矩阵.md` H4「载荷指纹」与行为 13 器材名单的粒度（`is_same_param_replay` 是否属「器材」）无反证文本；④子问题条数上限（`MAX_SUBTASKS_CONTRACT` 的 V2 承载位）——`specs/state.md` 行为 10 键面读数与 `docs/runtime-refactor/walk/裁决表.md` §06-A 五项均未含它，行为 16「取自 state 限额单点」的落点待落定。

## 待填：评审发现清单

| 编号 | 严重度 | 发现 | 证据锚点 | 建议处置 |
|---|---|---|---|---|
| P-01 | （L0·高·中·低） |  |  |  |
|  |  |  |  |  |

> 说明（起草方）：表体留空——编号自 P-01 起；严重度取值＝L0／高／中／低；每条发现须带证据锚点（`文件:行` 或条目号）与建议处置（采纳分支写清落法）。卡级问题只登记不裁决（单写者纪律）；已定稿文件侧的问题写「登记交主窗」，不得直改已定稿文件。

## 起草方留档：三闸实跑记录（2026-10-15）

```
$ uv run python tools/check_specs.py
spec gate: PASS（0 警告）                                     # exit 0

$ uv run python tools/ref_resolvable.py check
真源引用可解析闸绿：20 份规格的真源引用与边界规则编号均可解析。   # exit 0

$ uv run lint-imports --config tools/importlinter_v2.toml
R2 runtimev2 业务相位只经公共层包根（禁深层子模块） KEPT
R3 runtimev2 parsing/prompts 只许依赖 state KEPT
R5b ADR-0002 红线① 扩展：框架只许在 runtimev2.orchestration（其余 16 块禁引） KEPT
R6 runtimev2 各块只经 tools 接触引擎 KEPT
R7 runtimev2 各块只经 gateway_adapter 调模型 KEPT
R8 runtimev2 零 LLM 面：preconditions/verification/execution 不得引 gateway_adapter KEPT
Contracts: 18 kept, 0 broken.                                # exit 0
```

辅助取证：`ls tests/domains/` 实测无 `test_v2_parsing.py`（新建归属无冲突）；`ls appv2/runtimev2/parsing/` 仅 `__init__.py`（占位空包——边界闸为契约空过）。

### 未验证清单（交评审代理）

1. `tests/domains/test_v2_parsing.py` 不存在、`appv2/runtimev2/parsing/` 仅占位 `__init__.py`——验收行只能核标识形态，实现层合规待阶段 5。
2. 「V2 定案差异点」五点中的②③④（裸抛收口／常量迁移／内嵌数值待裁）**无既有裁决文本**——起草方按迁移纪律＋总纪律组合推出，属**待主窗过目件**（评审可判其对错，但处置归 L0／主窗）。
3. 行为 12 的「物理定义点＝本块」为组合推论（卡面签名＋R3），**无直接真源文本**——见重点核对项 1③。
