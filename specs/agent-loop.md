# V2 问答主链路（agent loop）

状态: 已定稿
来源: docs/prd.md §③、specs/modules.md `runtime`/`api` 卡、ADR-0001/0002

## 目标

用户向 `/api/v2/chat/asks` 提一个问题，系统以**有界 agent loop** 推理作答：
理解→规划→工具→观察→核验→阐述，全程事件可见、答案带 fail-closed 引用、
中途可澄清/审批挂起并可恢复。替代 V1 十七站瀑布＋无状态 LLM 判断孤岛。

## 不做什么

不做 Memory/跨会话个性化；不做自进化；不做写操作；不做 V1 端点的任何改动；
核验不替代引擎侧 citation fail-closed 校验（那是确定性 Middleware，本 spec 之上叠加）。

## 触及的模块

| 模块 | 改动类型 | 说明 |
|---|---|---|
| runtime | 新增 | loop/计划状态机/Context Builder/Verifier/run 持久化（LangGraph 实现） |
| api | 新增 | 三端点＋SSE 事件桥 |
| tools | 新增 | loop 经 ToolRegistry 调四工具（本 spec 只消费其公开接口） |

## 接口定义

```python
# runtime 公开接口（真源在 modules.md runtime 卡，此处细化）
class AgentRuntime:
    async def ask(self, q: AskRequest) -> RunHandle: ...
    async def resume(self, run_id: str, choice: AskChoice) -> RunHandle: ...
# AskRequest = {question: str, actor: Actor}
# RunHandle = {run_id: str, stream: AsyncIterator[SseEvent]}
# 事件枚举: step/text/tool/observation/ask/verdict/citation/notice（V1 wire 形兼容）

POST /api/v2/chat/asks                 200 → text/event-stream（首帧 run_id）
POST /api/v2/chat/runs/{run_id}/resume 200 → text/event-stream
GET  /api/v2/chat/runs/{run_id}        200 → {status, steps, manifest_digest}
错误：400 参数非法｜401 身份缺失｜404 run 不存在｜409 run 非挂起态不可 resume
```

## 行为约定

1. 每问新建 run；step 类型只许 understand/plan/tool/observe/verify/answer 六种，每步落 step 记录（INV-5）。
2. 模型每次调用前经 Context Builder 确定性编译（过滤→排序→预算→引用化），调用产出 Manifest
   （source_type/source_id/version/trust_level/selected_reason/token_count/transform）随 step 存档（INV-5）。
3. 规划步产出 plan_draft（指标槽/时间窗/条数/排名），先经 tools.data_query 的确定性校验：
   校验不过→repair 一次→仍不过→need_clarify 转 ASK 帧。
4. 工具只经 ToolRegistry.call；返回 status=ask 时 run 转 waiting_ask 挂起，事件流发 ask 帧后正常收束；
   resume 带选择续跑（INV-2：全程只读）。
5. 核验步（verify）：逐条检查阐述草稿的断言有 Observation 支撑；无支撑断言改写为"未找到/材料未披露"
   并出 notice——禁止无据断言进答案（INV-1、INV-4）。
6. 多来源矛盾时答案必须分源列明（各标出处）或显式声明歧义；禁止无出处调和（INV-4）。
7. 预算三闸：max_steps 8／总时长 300s／单工具超时 30s；触界即收敛——交付已核实部分＋
   notice 明示未完成项，不得静默截断（有界终止）。
8. run 状态机：running→waiting_ask→（resume）→running→completed/failed；
   引擎事件外置持久化，断线凭游标续传，进程重启后可恢复 waiting_ask 态（resume 可达）。

## 验收测试

| 验收标准 | 对应测试 |
|---|---|
| 正常提问→事件流含六类 step 且按 understand→…→answer 次序 | `tests/api/test_v2_asks.py::loop_step_sequence` |
| 每个模型调用 step 落 Manifest（来源/版本/token） | `tests/api/test_v2_asks.py::manifest_present_each_call` |
| 计划校验失败→repair→clarify ASK 帧→resume 续跑出答案 | `tests/api/test_v2_asks.py::plan_repair_clarify_resume` |
| 工具返回 ask→run 挂起→GET 状态 waiting_ask→resume 完成 | `tests/api/test_v2_asks.py::ask_suspend_resume` |
| 断言无 Observation 支撑→verify 改写为"未找到"＋notice | `tests/domains/test_agent_verify.py::unsupported_claim_rewritten` |
| 矛盾两来源→答案分源列明各带 citation（INV-4） | `tests/domains/test_agent_verify.py::contradiction_split_source` |
| max_steps 触界→收敛答案＋未完成项 notice，无静默截断 | `tests/domains/test_agent_loop.py::budget_termination` |
| 断线游标重连→事件不重复不遗漏 | `tests/api/test_v2_asks.py::sse_cursor_resume` |
| run 挂起态跨进程恢复（checkpoint 落 PG） | `tests/domains/test_agent_loop.py::run_recover_after_restart` |
| resume 到不存在/非挂起 run→404/409 | `tests/api/test_v2_asks.py::resume_error_paths` |
| 全程无任何写操作落库（只读断言，INV-2） | `tests/domains/test_agent_loop.py::readonly_inv2` |

## 依赖与风险

- 依赖：`tools` 四工具接口先定稿（tools 层 spec 先行或同批）；infra 复制票（gateway completer/时钟/db）。
- 风险：LangGraph checkpointer 的 PG saver 与 V1 表共存（新表前缀 agent_v2_ 隔离）；
  剧本化 completer 需支持多轮 replay（不同 caller 不同应答）。
