# V2-143 call_model 异步化（消桥 #1：每相位模型调用不再堵事件循环）

状态: 待开工（票面已补，未施工；**前置＝Owner 批准签名级变更并记 ADR**——方案件 `design/统筹方案-阻塞桥异步化-20261019.md` 即 ADR 草案）
日期: 2026-10-19 ｜ 依据：`bookkeeping/closing.py:283` 的 `pool.submit(lambda: asyncio.run(aw)).result()` 在**服务器环线程**同步等待，而 `call_model` 是**每个相位的每次模型调用**（秒级 × 每 run 5–8 次）⇒ 3 并发跑批时点击对话被阻塞 4–11s（CPU 0%）。规格本就登记：`specs/gateway_adapter.md:83` 行为 4「`async` 是硬要求……不得在事件循环内同步阻塞调用」＋`:129` 风险 2。调研件＝`research/阻塞桥-调用面调研-20261019.md`／`-副作用评估-20261019.md`

## 任务：

1. `appv2/runtimev2/bookkeeping/closing.py`：`call_model` 去桥、改 async（**逐字稿**）：
   ```python
   # 旧（同步签名 + 桥）
   def call_model(state, caller, messages, *, system=None) -> str:
       ...
       reply = _run_sync(_complete(...))          # ← :221 经 _run_sync → :283 .result()
       ...
   # 新（async 直 await；本函数不再触 _run_sync）
   async def call_model(state, caller, messages, *, system=None) -> str:
       ...
       reply = await _complete(...)
       ...
   ```
   （`_run_sync` 若本文件内已无消费方则同批删除；`closing` 的记账/落步语义逐字不动。）
2. 五相位调用点 `await` 化（**逐字稿**，每处同形）：
   ```python
   # 旧： raw = call_model(state, MODEL_CALLER, list(state.messages), system=...)
   # 新： raw = await call_model(state, MODEL_CALLER, list(state.messages), system=...)
   ```
   落点：`appv2/runtimev2/understanding/interpret.py:216`、`appv2/runtimev2/clarification/core.py:179`、`appv2/runtimev2/tool_matching/matching.py:140`、`appv2/runtimev2/answering/core.py:551`（explore 回喂 `:583`）、`appv2/runtimev2/orchestration/repair.py:126,172`。**这些相位函数及其内部调用链由 sync 改 async**（同批；调用它们的 graph 节点已是 async，只加 `await`）。
3. `appv2/runtimev2/orchestration/graph.py`：五个节点对相位函数的调用加 `await`（**逐字稿**：`interpret(state)` → `await interpret(state)` 同形五处）。
4. `specs/bookkeeping.md:78-79` 接口定义行 sync→async（**逐字稿**：`def call_model(...) -> str` → `async def call_model(...) -> str`）；`specs/gateway_adapter.md:129` 风险 2 补收口注（本票落地该风险的对策）。
5. 测试改判（逐条列名）：`tests/domains/test_v2_bookkeeping.py:862-895`（`inspect.signature` 参数面）、`:1170-1195`／`:1255-1263`（同步直调 `call_model` → async 化）、各相位测试中同步直调相位函数者。

## 先读：

- `appv2/runtimev2/bookkeeping/closing.py:25,193-230,272-284`（`call_model` 与 `_run_sync`）
- 五相位调用点（上列 file:line）与 `orchestration/graph.py:340,407,569,658,710`（节点）
- `specs/bookkeeping.md:78-79`、`specs/gateway_adapter.md:83,129`、`specs/modules.md:605`
- `docs/runtime-refactor/design/统筹方案-阻塞桥异步化-20261019.md` §三/§四

## 验收：以下 5 条全绿算收票（逐条机检）。

1. **心跳不阻塞**：新增 `tests/infra/test_v2_bridge_nonblocking.py::test_call_model_does_not_block_loop`——5ms 心跳协程 + 慢 completer 替身（`sleep 0.1`），断言 `ticks >= 10`；**反向判据**：回退 `_run_sync` 形 ⇒ `ticks <= 1` ⇒ 红（回报附红→绿输出）。
2. `call_model` 与五相位均为 `async def`（AST 断言）；全仓 `call_model(` 调用点无同步直调（grep 零命中）。
3. `specs/bookkeeping.md` 接口行与源码签名逐字一致（`check_specs` 绿）。
4. 语义零漂移：`tests/infra/test_v2_db_loop_scope.py` 两例＋门两件＋hot_reload 六例恒绿；`call_model` 记账/步记录断言（`test_call_model_keeps_accounting`）改判后仍绿。
5. 全量 `pytest -q`／`ruff`／`mypy app appv2`／`lint-imports` 两配置／`check_specs`／`ref_resolvable` 全绿。

## 回报：

改动文件＋测试名＋红→绿（含反向判据输出）＋心跳 ticks 前后＋五相位 async 证据＋specs diff＋改判清单＋各闸输出＋偏离点。

框架红线: 禁 langgraph/langchain（R5b）；禁直引 `appv2.infra.llm_client`（R7）——`call_model` 仍经既有 completer 缝。
边界红线: 只许动 `appv2/runtimev2/bookkeeping/closing.py`、五相位文件（`understanding/interpret.py`／`clarification/core.py`／`tool_matching/matching.py`／`answering/core.py`／`orchestration/repair.py`）、`appv2/runtimev2/orchestration/graph.py`（仅调用点 `await`）、`specs/{bookkeeping,gateway_adapter}.md`、对应 tests 与新增 `tests/infra/test_v2_bridge_nonblocking.py`；**不动** `execution/core.py`（V2-144 面）、`query/*`／`knowledge/*`（V2-145 面）、`persistence/*`、`api/*`、`web/`。
