# V2-144 execution.execute 异步化（消桥 #2：工具派遣不再堵事件循环）

状态: 待开工（票面已补，未施工；**前置＝V2-143 落定**（同形范式先落）＋Owner 批准签名级变更）
日期: 2026-10-19 ｜ 依据：`execution/core.py:474` 的 `pool.submit(lambda: asyncio.run(aw)).result()`（调用点 `:412 _run_sync(_gather(...))`）在服务器环同步等待**每次工具派遣**（`data_query`／`doc_retrieve`／`semantic_query`）；且 `execute` 路径内含 `bus.emit`（`core.py:1211,1237,1343`）与 `RunState` 写入——**异步化后这些留在主环**（对比 A 案 offload 会把帧/状态拖进工作线程 ⇒ SSE 丢帧）。调研件＝`research/阻塞桥-副作用评估-20261019.md` §最危险副作用 1/3

## 任务：

1. `appv2/runtimev2/execution/core.py`：`execute` 去桥改 async（**逐字稿**）：
   ```python
   # 旧
   def execute(state: RunState) -> ExecutionOutcome:
       ...
       return _run_sync(_gather(registry, context, calls, limit))     # :412 → :474 .result()
   # 新（async 直 await；本模块不再触 _run_sync）
   async def execute(state: RunState) -> ExecutionOutcome:
       ...
       return await _gather(registry, context, calls, limit)
   ```
   `_dispatch`／`_run_batch`／`_run_discovers`／`_retry_retryable` 等同批由 sync 改 async（同文件内连锁）；`_run_sync` 本文件内无消费方则删除。
2. `appv2/runtimev2/orchestration/graph.py:547`（`_make_discover`）与 `:617`（`_make_batch`）：`execute(state)` → `await execute(state)`（**逐字稿**）。
3. `specs/execution.md:36` 接口定义行 sync→async（**逐字稿**：`def execute(state) -> ExecutionOutcome` → `async def execute(state) -> ExecutionOutcome`）。
4. 测试改判（逐条列名）：`tests/domains/test_v2_execution.py:815-830`（AST 钉同步 `FunctionDef` → `AsyncFunctionDef`）、同文件 9 个 async 测试经 `_run` helper（`:252-260`）的调用形、以及 `tests/domains/test_v2_four_phase.py` 等经 graph 调 `execute` 的集成测试。

## 先读：

- `appv2/runtimev2/execution/core.py:332,404-420,461-475,561,638,1211,1237,1343`
- `appv2/runtimev2/orchestration/graph.py:540-560,610-625`
- `specs/execution.md:36`、`specs/gateway_adapter.md:83,129`
- `docs/runtime-refactor/design/统筹方案-阻塞桥异步化-20261019.md` §二/§三/§四

## 验收：以下 5 条全绿算收票（逐条机检）。

1. **心跳不阻塞**：`tests/infra/test_v2_bridge_nonblocking.py::test_execute_does_not_block_loop`——5ms 心跳 + 慢工具替身（`sleep 0.1`），断言 `ticks >= 10`；**反向判据**：回退 `_run_sync` ⇒ `ticks <= 1` ⇒ 红。
2. `execute` 为 `async def`（AST 断言）；全仓 `execute(` 的同步直调零命中。
3. **帧在主环**：`::test_frames_delivered_during_execute`——`execute` 在途时下一帧 ≤50ms（钉「异步化后帧/状态仍归主环」）。
4. 语义零漂移：`test_v2_db_loop_scope.py` 两例＋门两件恒绿；`ExecutionOutcome` 六形断言改判后仍绿。
5. 全量 `pytest -q`／`ruff`／`mypy app appv2`／`lint-imports` 两配置／`check_specs`／`ref_resolvable` 全绿。

## 回报：

改动文件＋测试名＋红→绿（含反向判据输出）＋心跳 ticks 前后＋帧延迟证据＋specs diff＋改判清单＋各闸输出＋偏离点。

框架红线: 禁 langgraph/langchain（R5b）；工具仍经 registry 公开面派遣（不直引引擎）。
边界红线: 只许动 `appv2/runtimev2/execution/core.py`、`appv2/runtimev2/orchestration/graph.py`（仅两节点 `await`）、`specs/execution.md`、对应 tests 与新增心跳用例；**不动** `bookkeeping/closing.py`（V2-143 面）、`query/*`／`knowledge/*`（V2-145 面）、`persistence/*`、`api/*`、`web/`。
