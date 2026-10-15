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
