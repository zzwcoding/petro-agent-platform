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
