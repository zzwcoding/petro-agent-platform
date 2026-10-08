# V2-07 · api v2 端点＋SSE

状态: open
Touches modules: `api`
阻塞: V2-06｜被阻塞: 无（V2 线收口票）

## 任务

实现 `appv2/api/`：三端点（asks/resume/runs）＋SSE 事件桥；
事件形 V1 wire 兼容（id:/event:/data:）＋新增 step/observation 事件；
断线游标续传；错误码 400/401/404/409。

先读: specs/agent-loop.md「接口定义」节；specs/modules.md `api` 卡与「页面映射」节；
tests/api/test_chat_sse.py（V1 wire 形参照）

框架红线: 无点名框架
边界红线: 只许建 `appv2/api/**`；依赖 `appv2.runtime`（公开接口）＋`appv2.infra`；
不得 import `app.**` 及 engines/tools；SSE 帧不得携带 langgraph 类型

验收: 以下逐条对应 specs/agent-loop.md「验收测试」表 API 侧条目——
- API 侧六条全绿：loop_step_sequence / manifest_present_each_call /
  ask_suspend_resume / sse_cursor_resume / resume_error_paths / plan_repair_clarify_resume
- TestClient 接口级测试（不起真实端口）
- V1 前端旧事件形兼容断言在场（web/ 零改动可连）

回报: 完成后回总窗口："V2-07 完成，产物 appv2/api/，偏差: 有/无，测试: pytest 输出摘要"
