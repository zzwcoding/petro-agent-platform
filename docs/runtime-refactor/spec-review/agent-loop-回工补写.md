- 日期：2026-10-15 ｜ 状态：**回工补写**（复审⑦ V1 发起面 doctrine 回改；本件为首建——此前本规格无回工补写记录）
- 本次只改 `specs/agent-loop.md`（234→235 行）＋本记录，其它文件未动；未 git commit（主窗统一提交）。

## V1 发起面回改（主窗裁 doctrine）——2026-10-15

- **依据**：复审⑦处置（`docs/runtime-refactor/00-决议与方法.md` 流水 27 第①裁）——相位调模型一律经 `bookkeeping.call_model`（其内部唯一出口 `appv2.runtimev2.gateway_adapter`）。
- **修改点**（行号指改后文件）：
  1. 「触及的模块」依赖表（:36）：`orchestration` 行后新增 `bookkeeping` 行（改动类型＝**新增依赖**；说明＝「模型调用发起面：经 bookkeeping.call_model（单点发起），本块不直引 gateway_adapter」）——与 `specs/modules.md` `## orchestration` 卡依赖行（已列 `bookkeeping`）对齐，本表此前漏列。
  2. 「框架与依赖红线」（:72）：「模型调用唯一出口＝`gateway_adapter`」改为「**模型调用发起面＝`bookkeeping.call_model`（单点发起）；其内部唯一出口＝`gateway_adapter`**：编排层与各相位不直引 `gateway_adapter` 发起模型调用、不自建模型客户端」；R7 括注补「发起面收敛为规格层 doctrine，不设闸——主窗 2026-10-15 裁」；「无旁路」行为断言保留。
  3. 「依赖与风险」依赖行（:211)：补 `bookkeeping`（模型调用发起面——`call_model` 单点发起）。
  4. 「与闸的挂钩表」（:226)：「模型调用只经 `gateway_adapter`」行改为「模型调用经 `bookkeeping.call_model` 发起（单点发起；其内部唯一出口 `gateway_adapter`）」；挂钩列注「出口面 R7；发起面为规格层 doctrine，不设闸」；现状列不变。
- **不加闸（裁定照录）**：importlinter 边界闸**不随本批加**——R7「只经出口」＋R8 语义不变，doctrine 是规格层不是闸层（主窗 2026-10-15 裁）。
- **契约字面核对（未改 toml）**：逐条实读 `tools/importlinter_v2.toml`——R7（forbidden＝`appv2.infra.llm_client`；source 含 `appv2.runtimev2.orchestration` 与 `appv2.runtimev2.bookkeeping`）与 R2（forbidden 含 `appv2.runtimev2.bookkeeping.*` 深层子模块、不含包根）均与新 doctrine **无字面冲突**。实现期注意：相位 import 只许 `appv2.runtimev2.bookkeeping` 包根（R2 面）。
- **验证**：`uv run python tools/check_specs.py` → **PASS（0 警告）**；`uv run python tools/ref_resolvable.py check` → **绿（20 份规格）**。均 exit 0（批次一改后实跑；批次三后全量复跑仍绿）。

---

## 流水 31 裁决落笔（裁决二＝同参重投闸落 execution，行为 3 表述回提）——2026-10-15

- **依据**：主窗流水 31②（2026-10-15）——「decision 出口同参重投闸保留」在 legacy 决策节点废弃（`synth/S4` 结构-1）后 V2 无落点（`parsing-评审.md` P-10），裁＝闸落 `execution`（dispatch 统一出口），本块只保留轮数闸／自旋收敛的预算面层。
- **修改点**（只改 `specs/agent-loop.md`，235→236 行）：行为 3（:119-120）「decision 出口同参重投闸保留，定位降为确定性兜底」改为「同参重投闸落 execution（dispatch 统一出口，流水 31②），本块保留轮数闸／自旋收敛的预算面层；定位降为确定性兜底」——其后括注（主力是过程摘要渲染——V2-79c；V2-79a 三层分离后原「消息历史簿记」承载面退役）不变。
- **验证**：`uv run python tools/check_specs.py` → **PASS（0 警告）**；`uv run python tools/ref_resolvable.py check` → **绿（21 份规格）**；`uv run lint-imports --config tools/importlinter_v2.toml` → **Contracts: 18 kept, 0 broken**。均 exit 0（改后实跑）。未 git commit（主窗统一提交）。

---

## 流水 43 裁决落笔（裁决⑦c＝行为 2 改述＋挂钩表补 pin-24 行）——2026-10-16

- **依据**：主窗流水 43⑦（2026-10-16，真源 `docs/runtime-refactor/00-决议与方法.md` 流水 43）零散回提三项之三——①**行为 2 改述**：删 79a 形「Context Builder 确定性编译／[system]＋dialogue 截断＋当前轮／现拼现用用完即弃」旧文，改「每步在 `messages` 整链续写」（真源 `specs/state.md` 行为 4＋V2-80h 追加式；compile 已退役）；②**挂钩表补 pin-24 行**（落法照 `specs/context.md` 挂钩表：消费侧重发判定＝追加编排归 `orchestration`＋标记写入归 `bookkeeping.append_contract`）。销 `specs/context.md` 风险 7⑧（pin-24 行登记）／⑩（行为 2 两说，P-29）两条登记。
- **修改点**（行号指改后文件；236→241 行）：
  1. 行为 2（:102-118）整体改述：首句改「**每步在 `messages` 整链续写**（真源 `specs/state.md` 行为 4＋V2-80h 追加式——`tickets/v2/V2-80h-对话链追加式架构.md`；**compile 已退役**——流水 43⑦c 改述，删 79a 形「Context Builder 确定性编译／[system]＋dialogue 截断＋当前轮／现拼现用用完即弃」旧文）」；承接句＝「每个 LLM 调用发送**整条链**（＝上次链＋尾段），模型应答与过程记录以类型正确的消息**追加链尾**、任意相邻调用互为前缀延伸」；`dialogue`／`process_notes` 双字段面保留（真源锚改指 `specs/state.md` 行为 6＋A-P5b2-03；「本行为真源以方案为准」旧短语随 79a 形删除）；「历史增长带 token 预算/截断显式进 Manifest」改「历史增长的超窗压缩＝compaction（只压模型视图、`state.messages` 原史零覆盖——真源 `specs/context.md` 行为 9），披露账目显式进 Manifest」；词典层常驻注入段与 Manifest 产出句逐字保留。
  2. 「触及的模块」context 行（:38）：「Context Builder＋对话状态簿记……」改「追加内容渲染（compile 已退役——流水 43⑦c）＋对话状态簿记……」（Context Builder 为已退役名，随行为 2 改述同批收正）。
  3. 「与闸的挂钩表」pin-22 行（:237）后新增一行（:238）：硬要求＝「相位合同一次性（消费侧重发判定＝追加编排归 `orchestration`＋标记写入归 `bookkeeping.append_contract`——落法真源 `specs/context.md` 挂钩表）」｜挂钩＝钉 **`pin-24`**（P1）｜现状＝待织网（阶段 5）。
- **未随批改面（登记交主窗）**：①行为 3 末句「V2-79a 三层分离后原「消息历史簿记」承载面退役」保留（历史沿革注记，语义不冲突）；②验收表「run 内对话状态簿记（`dialogue`＋`process_notes` 双字段，第二轮调用携带首轮对话）」等 multi_turn 行未动（测试标识与双字段语义仍在——messages 整链下第二轮携带由链前缀延伸承载，测试网②改写时一并核对断言面）。
- **验证**：`uv run python tools/check_specs.py` → **PASS（0 警告）**；`uv run python tools/ref_resolvable.py check` → **绿（22 份规格）**。均 exit 0（改后实跑）。未 git commit（主窗统一提交）。

---

## 拆票期卡级修正（流水 50）——api 卡进口面——2026-10-16

> 本节记 **`specs/modules.md` `## api` 卡**的进口面修正（api 面属本规格侧：本规格「触及的模块」表 api 行＝`specs/agent-loop.md:41`；W5-02 票面对象行 1 引该行）。

- **缺口描述**：`tickets/v2-refactor/RT-W5-02-api-v2端点与SSE桥.md` 票注①②③ 原文（逐字）：「① **进口面落点四处无卡面落点**——`api` 卡依赖行只列 `orchestration`＋`infra`（行 8 原文），而实件面需四类进口：受理三形状（卡面签名 `AgentRuntime.ask(q: AskRequest) -> RunHandle`——`specs/modules.md:309–:311`）、帧类型（`SseEvent`——真源行 11／12）、读面（行 5／6 两读口的 `status/steps/manifest_digest/pending_ask`）、装配面（`app.py` 现进口 `Budget`／`PgCheckpointer`／`Completer`／`CALLER_PREFIX` 一族）……② **两读口归属**：行 5／6 数据来源在 V2 落到 `persistence` 读面（`specs/persistence.md` 公开面 `run`／`steps`／`blackbox`），而卡面依赖行不含 `persistence`……③ **组合根装配面**……在卡面无落点」。
- **裁口径（主窗 L0，2026-10-16）**：「**api 经 orchestration 包根 re-export 受理三形状（AskRequest/AskChoice/RunHandle）与装配面；帧类型与读口行投影直引 transport/persistence 的公开面**——`modules.md` `## api` 卡依赖行同批改并注「类型/常量面只引形状」（守 bookkeeping 先例句式）」。
- **改动位置**（行号指改后文件；`specs/modules.md` 635→640 行）：`specs/modules.md:603`——`## api` 卡依赖行改为：`- 模块: \`orchestration\`（业务面只许走其公开接口；**受理三形状 AskRequest／AskChoice／RunHandle 与组合根装配面经其包根 re-export**；组合根 create_app 例外——装配执行器/检查点/网关模型，V2-07 按组合缝采纳）、\`transport\`、\`persistence\`（**帧类型与读口行投影面**——SseEvent 帧类型、两读口（run 行／步记录）行投影；**类型/常量面只引形状**，不许引其行为：不自建帧通路、不落盘）、\`infra\``。
- **依据引文（逐字）**：① `specs/modules.md` 边界规则 api 行（原 `:622`→现 `:627`）「\| `api` 引用 `orchestration` 以外模块 \| （无） \| 端点薄层，编排语义全在运行时 \|」；② `specs/transport.md:32`「\| api \| 新增 \| 帧→SSE 的渲染与断线游标的接缝（本块只出帧与游标语义） \|」；③ `specs/modules.md` `## bookkeeping` 卡依赖行先例句式「`tools`、`persistence`、`transport`（**类型与常量形状面**——ToolContext 类型、StepRecord 形状、NOTICE_TYPES 常量；只引形状，不许引其行为：不调工具、不落盘、不发帧）」。
- **机器闸交互（踩坑记录，务必留痕）**：初稿把 `AskRequest`／`AskChoice`／`RunHandle`／`SseEvent` **加反引号**写进 `- 模块:` 行 → `uv run python tools/check_specs.py` **报 4 处 FAIL**（`模块 \`api\` 依赖 \`AskRequest\`，后者未声明`…）。原因：`tools/check_specs.py` 的 `parse_modules` 把该行**所有反引号 token 当依赖模块名**去做「已声明卡」校验与成环检查。**故卡依赖行只许给模块名加反引号**（类型/常量名裸写）——与 `## bookkeeping` 卡先例写法一致；改后 spec gate PASS。
- **未随批改面 / 张力登记（呈主窗，本批不代改）**：
  1. **边界规则行与新增直引面字面张力**：边界规则 api 行（`:627`）仍写「api 引用 `orchestration` 以外模块｜（无）」，而本次卡面已列 `transport`／`persistence` 直引面（票注① 原文即要求「后者须同批改 `specs/modules.md:622` 边界行」）——**本批只授权卡依赖行**，未改该边界行；建议主窗随批收词（人审面，无专属闸：`R1–R8` 契约 `source_modules` 均不含 `appv2.api`，票注② 原文「无专属闸 → 人审」）。
  2. **对侧落点缺口**：`orchestration` 卡公开接口（改后 `:312–:317`；`AgentRuntime.ask`／`resume` 两行 `:315–:316`）只列两签名，**未列受理三形状的包根 re-export 面**——「两处不许脱节」意义上的对侧未落；且 `RT-W5-01a/b/c` 三票「先读／边界红线」节均无 re-export 字样（亲读 grep 无命中），呈主窗（是否在 orchestration 卡／其票同批补注，须主窗裁）。
  3. **`state` 未入卡依赖行**：三形状经 orchestration re-export 后本层不直引 `state`——若主窗改判为「api 直引 `state` 包根」，须同步改边界规则行（同上）。
- **行号漂移（供票面回填）**：`specs/modules.md` 原 `:179` 起 **+5**（tool_matching 卡级注所致）——原 `## api` `:578`→`:583`；原 api 依赖行 `:598`→`:603`；原卡 Seam 行 `:602`→`:607`；原测试计划行 `:604`→`:609`；原边界规则 api 行 `:622`→`:627`；文件 **635→640 行**。
- **验证**：`uv run python tools/check_specs.py` → **PASS（0 警告）**；`uv run python tools/ref_resolvable.py check` → **绿（22 份规格）**；`uv run lint-imports --config tools/importlinter_v2.toml` → **Contracts: 18 kept, 0 broken**；`uv run lint-imports`（默认配置）→ **6 kept, 0 broken**。均 exit 0（改后实跑）。未 git commit。

---

## 2026-10-16 拆票期卡级修正②（流水 51）——R6／R7／R8 indirect 豁免 ＋ api 卡边界行对齐

- **范围**：`tools/importlinter_v2.toml`（R6／R7／R8 加 `allow_indirect_imports = true` ＋ 语义注）＋ `specs/modules.md`（api 卡边界规则行改口、orchestration 卡公开接口节补注）＋ 本记录。其它契约未动（**R2 未动**，见 §三）。未 git commit（主窗统一提交）。

### 一、R6／R7／R8 语义口径（`tools/importlinter_v2.toml`）

- **缺口（前探针实测，逐字闸输出）**：按各卡面形态实现时三契约必红——`forbidden` 默认连**间接链**一起禁，而三契约措辞是「不**直**引」「只许**直**引」：
  - R6 红链：`appv2.runtimev2.execution -> appv2.tools (l.7)` ／ `appv2.tools -> appv2.tools.handlers (l.42)` ／ `appv2.tools.handlers -> appv2.retrieval (l.52, l.58)`；
  - R7 红链：`appv2.runtimev2.execution -> appv2.tools (l.7)` ／ `appv2.tools -> appv2.tools.registry (l.91)` ／ `appv2.tools.registry -> appv2.infra.llm_client (l.23)`；
  - R8 红链：`appv2.runtimev2.verification -> appv2.runtimev2.bookkeeping` ／ `appv2.runtimev2.bookkeeping -> appv2.runtimev2.gateway_adapter`（写口/模型桥——`bookkeeping.call_model` 内部出口）。
- **裁口径（主窗 L0，2026-10-16，流水 51；Owner 可否决）**：三契约语义＝禁**直引**；间接经批准桥接（`bookkeeping` 模型桥／`tools` 类型面）不违——故三契约各置 `allow_indirect_imports = true`，并在**每条契约上方**加语义注。
- **改动位置**（行号指改后文件）：`tools/importlinter_v2.toml` R6 语义注 `:107–:108`、flag `:114`；R7 语义注 `:116–:117`、flag `:123`；R8 语义注 `:125–:126`、flag `:132`。注释逐字要点：R6「tools 包装引擎＝设计路径，相位 → `appv2.tools` → 引擎 传递链非触界」｜R7「模型出口唯一桥＝`bookkeeping.call_model` → `gateway_adapter`（＋ tools 侧异常类型面）」｜R8「写口面 `bookkeeping` 内部承载模型桥（verification → bookkeeping → gateway_adapter ＝写口链，非本块发起面）」；三条 flag 行均注「只咬直接引用」。
- **探针证据（同批实跑；跑完 `git checkout --` 回退，零残留——`git status appv2` 干净）**：探针＝三处骨架占位文件临时 import（`appv2/runtimev2/execution/__init__.py` → `appv2.tools`；`appv2/runtimev2/bookkeeping/__init__.py` → `gateway_adapter`；`appv2/runtimev2/verification/__init__.py` → `bookkeeping`），改前配置＝`git show HEAD:tools/importlinter_v2.toml` 落临时件——**改前 14 kept, 4 broken（R2／R6／R7／R8）；改后 18 kept, 0 broken**（探针在位态 1 broken＝R2，见 §三）。

### 二、api 卡边界行对齐（销 流水 50「未随批改面」①②）

- **缺口（流水 50 原文登记）**：①边界规则 api 行（原 `:627`）逐字「| `api` 引用 `orchestration` 以外模块 | （无） | 端点薄层，编排语义全在运行时 |」与同批卡依赖行（`:603`→`:605`）字面冲突（卡依赖行已列 `transport`／`persistence` 直引面）；②`## orchestration` 卡公开接口节未列受理三形状的包根 re-export 面（「两处不许脱节」意义上的对侧未落）。
- **裁口径**：边界行例外列改口为类型/常量形状面白名单（`transport`／`persistence`／`state`），理由列保留原文；orchestration 卡补公开面注。
- **改动位置**（行号指改后文件；`specs/modules.md` 640→642 行）：
  1. `specs/modules.md:629`（原 `:627`）——边界规则 api 行改为：`` | `api` 引用 `orchestration` 以外模块 | `transport`／`persistence`／`state`——**只许类型/常量形状面**（帧类型 SseEvent、读口行投影、Budget 装配形状），行为只经 orchestration | 端点薄层，编排语义全在运行时 | ``。
  2. `specs/modules.md:319`（orchestration 卡「### 公开接口」码块后新增一行）——「> **公开面注（流水 51 卡级修正）**：受理三形状（AskRequest/AskChoice/RunHandle）与装配面经包根 re-export 供 api 消费（2026-10-16，流水 51）。」
  - **行号漂移（供票面回填）**：自 `:318` 起 **+2**——原 api 卡依赖行 `:603`→`:605`（本批未改）、原边界规则 api 行 `:627`→`:629`。
- **未随批改面（呈主窗）**：边界行例外列现含 `state`（Budget 装配形状），而 `## api` 卡依赖行（`:605`）未列 `state`——若实现期 api 直引 `state` 包根，须同批补卡依赖行（人审面；`R1–R8` 契约 `source_modules` 均不含 `appv2.api`，无专属闸）。

### 三、呈主窗：R2 **报红**（间接链与「直引包根」两态皆红；按指令未改 toml）

- **契约原文**（`tools/importlinter_v2.toml:73–:78`，逐字）：`name = "R2 runtimev2 业务相位只经公共层包根（禁深层子模块）"`；`type = "forbidden"`；`source_modules`＝七个业务相位；`forbidden_modules = ["appv2.runtimev2.state.*", "appv2.runtimev2.orchestration.*", "appv2.runtimev2.bookkeeping.*", "appv2.runtimev2.prompts.*", "appv2.runtimev2.parsing.*", "appv2.runtimev2.context.*", "appv2.runtimev2.transport.*", "appv2.runtimev2.persistence.*", "appv2.runtimev2.gateway_adapter.*"]`；`allow_indirect_imports = false`。
- **红链**（逐字闸输出，改后配置＋探针在位态）：
  ```
  R2 runtimev2 业务相位只经公共层包根（禁深层子模块）
  appv2.runtimev2.verification is not allowed to import appv2.runtimev2.gateway_adapter.fake:
  -   appv2.runtimev2.verification -> appv2.runtimev2.bookkeeping (l.7)
      appv2.runtimev2.bookkeeping -> appv2.runtimev2.gateway_adapter (l.7)
      appv2.runtimev2.gateway_adapter -> appv2.runtimev2.gateway_adapter.fake (l.10)
  ```
  末跳出处＝**已在库代码**（`appv2/runtimev2/gateway_adapter/__init__.py:10`：`from appv2.runtimev2.gateway_adapter.fake import ModelReply, ScriptedCompleter`），非探针引入；前两跳＝施工形态（`bookkeeping` 包根→`gateway_adapter` 包根＝卡面已定稿依赖，`specs/modules.md:350` `call_model` 注「调 gateway_adapter.complete」＋`:358` 依赖行「`gateway_adapter`（**运行逻辑**）」）。
- **更强证据：相位**直引包根**也红（红链不需 `bookkeeping` 中转）**——探针 `appv2/runtimev2/preconditions/__init__.py` 加一行 `from appv2.runtimev2.gateway_adapter import ScriptedCompleter`（＝R2 措辞**要求**的「公共面只经包根」形态），逐字闸输出：
  ```
  appv2.runtimev2.preconditions is not allowed to import appv2.runtimev2.gateway_adapter.fake:
  -   appv2.runtimev2.preconditions -> appv2.runtimev2.gateway_adapter (l.7)
      appv2.runtimev2.gateway_adapter -> appv2.runtimev2.gateway_adapter.fake (l.10)
  ```
  即 R2 现状与「只经包根」口径在 `gateway_adapter` 一块上**自相矛盾**：合规写法（引包根）必红，除非相位永不可达该块（而 R8 前提要求 `verification` 经写口链达它）。
- **直接引用的咬合面完好（同批反证，R6／R7／R8 未被豁免写坏）**：探针 `preconditions/__init__.py` 直引 `appv2.knowledge`／`appv2.infra.llm_client`／`appv2.runtimev2.gateway_adapter` → **14 kept, 4 broken**（R6／R7／R8 皆红＋R2 如上）；回退后 **18 kept, 0 broken**。全部探针 `git checkout --` 回退，`git status appv2/` 干净（零残留）。
- **分析**：①R2 咬合点＝**公共层包根自身经「自 re-export 边」引自身深层子模块**——包根节点（`bookkeeping`／`gateway_adapter`）不匹配 `.../*`，把链带进 `gateway_adapter.fake` 的是包根内部那条自边。故凡相位**传递触达 `gateway_adapter` 包根**即红，而 R8 语义（`verification → bookkeeping → gateway_adapter` 为写口/模型桥）使该触达**设计必现**——与 R6／R7／R8 同因：`allow_indirect_imports = false` ＋ 契约措辞只讲「相位自身 import 形态」。②本红链**不经 `tools`**：仅 `execution → appv2.tools` 探针在位时 R2 实跑仍 **KEPT**（证据：该态 18 kept, 0 broken）——R2 的 `forbidden_modules` 不含 `appv2.tools`／引擎／`infra.llm_client`，故候选「收紧 `tools` 公开面」对本红链**无效**。③结构性：施工期任一公共层块若在包根 re-export 自身深层子模块（今日仅 `gateway_adapter` 一例），同形红链即复现。
- **两个候选修法（交主窗裁）**：
  1. **R2 加 `allow_indirect_imports = true`**（与 R6／R7／R8 同款裁法）——语义对口径：R2 措辞主语＝「业务相位 **import** 九个公共层块的深层子模块」＝相位**自身 import 形态**，间接经包根 re-export 不违。代价＝R2 失去「经他块间接触达深层」的咬合面（该面非措辞所辖）；相位直引深层子模块仍必红。
  2. **保 R2 严格性、只豁免「公共层包根 → 自身深层子模块」自边**：给 R2 加 `ignore_imports = ["appv2.runtimev2.gateway_adapter -> appv2.runtimev2.gateway_adapter.fake"]`（其余八块施工期若现同形自边，逐条登记）。语义＝「深层实现属私有」指**相位不得绕过包根**，不含公共层内部结构；R2 咬合面精确化为「相位经公共层内部结构触达深层」（如 `verification → persistence → persistence.store`）仍红。
  3. （备选·结构性，代价高）把 `gateway_adapter` 替身并入包根文件、不自 re-export —— 牵动已定稿 `## gateway_adapter` 卡（「本包根此刻只导出替身与其回执类型」）与 `docs/runtime-refactor/eng/04-测试网设计.md` §五落点，且治不了同形新链。

### 四、闸记录（无探针态，全量实跑）

- `uv run python tools/check_specs.py` → **PASS（0 警告）**；`uv run python tools/ref_resolvable.py check` → **绿（22 份规格）**；`uv run lint-imports --config tools/importlinter_v2.toml` → **18 kept, 0 broken**；`.venv/bin/lint-imports`（默认配置）→ **6 kept, 0 broken**；`.venv/bin/python -m pytest tests/infra/test_v2_infra.py tests/tools/ -q` → **100 passed**。均 exit 0（`.venv/bin/` 与 `uv run` 两路同值，实跑）。
