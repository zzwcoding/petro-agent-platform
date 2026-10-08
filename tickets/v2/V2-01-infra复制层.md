# V2-01 · infra 复制层

状态: 实现中（2026-10-08，P-001 已派发）
Touches modules: `infra`
阻塞: 无（V2 线首票）｜被阻塞: V2-02/03/04/05/06/07

## 任务

按 specs/infra.md 的"带/不带"清单，从 V1 `app/infra` 复制清理出 `appv2/infra/`：
config 装载/db 双路由只读会话/llm_client/gateway 域/clock/security——带纪律不带业务语义。

先读: specs/infra.md 全文；specs/modules.md `infra` 卡与「边界规则」节；docs/adr/0002-langgraph框架决策.md

框架红线: 无点名框架（litellm 为 V1 既有依赖，复制沿用；langgraph 不在本票）
边界红线: 只许建 `appv2/infra/**`；不得 import `app.**`（V1）；不得搬 V1 domains 任何代码

验收: 以下逐条对应 specs/infra.md「验收测试」表——
- specs/infra.md「验收测试」五条逐条实现为 `tests/infra/test_v2_infra.py`（llm_single_exit / no_v1_dependency / gateway_gate / readonly_guard / audit_single_writer）全绿
- 复制清单落实：带 4 项/不带 2 类逐条可指认（文件级 diff 审查）
- `uv run pytest tests/infra/test_v2_infra.py` 输出原文附回报
- 行为约定 1–4 逐条在代码中对位（B6 单点/只读守卫/audit 单写口/agent_v2.* 前缀注记）

回报: 完成后回总窗口："V2-01 完成，产物 appv2/infra/，偏差: 有/无，测试: pytest 输出摘要"
