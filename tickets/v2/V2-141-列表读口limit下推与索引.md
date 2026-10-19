# V2-141 列表读口 limit 下推与 created_at 索引

状态: 待开工（票面已补，未施工；**前置 V2-135＋V2-136 合入**——两票占同文件）
日期: 2026-10-19 ｜ 依据：`appv2/api/chat.py:189-222 list_runs` 对 `registry.run_ids()` **全量** `store.run()` 才 `[:limit]`；V2-136 拟落形（`scan_all`＋内存排序＋`[:limit]`）**limit 仍一次读都不省**（2055 行样本实测 7.49ms；理想下推 0.07ms）；`agent_v2_run.created_at` **无索引**（0022 仅建 `ix_agent_v2_step_run_id`）。调研件＝`research/列表慢-后端读口调研-20261019.md`。

> **推荐：本票折进尚未开工的 V2-136 同批**（同文件、避免先落「全表读」再返工）；若不折，须**排在 V2-136 之后**。

## 任务：

1. 端口侧 limit 下推（**逐字稿**签名）：
   ```python
   # appv2/runtimev2/persistence/tables.py
   class Tables(Protocol):
       def scan_recent(self, limit: int) -> list[RunRow]: ...   # created_at DESC，取前 limit
   ```
   - `PgTables.scan_recent`：`SELECT ... FROM agent_v2_run ORDER BY created_at DESC LIMIT $1`（真件 SQL 落在 persistence 块内，api 侧不自造 SQL）；
   - `MemoryTables.scan_recent`：内存按 `created_at` 降序后切片；
   - `RunStore` 转出同名（**逐字稿**）：`def scan_recent(self, limit: int) -> list[RunRow]: ...`；
   - `appv2/api/chat.py::list_runs` 改为「先 `scan_recent(wanted)` 再投影」（不再全量读＋Python 排序）。
2. 迁移 `migrations/0029_agent_v2_run_created_at_index.py`：`CREATE INDEX ix_agent_v2_run_created_at ON agent_v2_run (created_at DESC)`（含 downgrade drop）。
3. specs 同批（**逐字稿**）：
   - `specs/persistence.md` 风险 5 的「分页/上限归 api 侧」措辞按新端口改写；`RunStore` 接口节补 `scan_recent`；
   - `specs/agent-loop.md:78` 读口行注明「limit 由端口侧下推」。
4. tests：`tests/domains/test_v2_persistence.py`（协议替身 `_ProbeTables`／`_FailingTables` 补新口；`test_public_surface_complete` 签名同步）；`tests/api/test_v2_runs_list.py` 新增 `test_list_applies_limit_at_read_port`（直插 `limit+5` 行 → 响应恰 `limit` 条且 `created_at` 降序前 `limit`；若走端口侧 LIMIT，则 monkeypatch 全量扫描抛错仍绿；越界仍静默夹取 1..100）。

## 先读：

- `appv2/api/chat.py:189-222`（`list_runs` 现状与行投影）
- `appv2/runtimev2/persistence/{store,tables,pg_tables}.py`（`Tables` 协议、`MemoryTables`、`PgTables`）
- `migrations/0022_*`（`ix_agent_v2_step_run_id` 先例）与 `agent_v2_run` 列定义
- `specs/persistence.md`（`RunStore` 接口节、风险 5）、`specs/agent-loop.md:77-78`
- `docs/runtime-refactor/research/列表慢-后端读口调研-20261019.md`

## 验收：以下 4 条全绿算收票（逐条机检）。

1. 读口**只读 limit 条**：`test_list_applies_limit_at_read_port` 绿（含「全量扫描被 monkeypatch 抛错仍绿」的下推反证）。
2. 2055 行样本耗时对照：下推后 `limit=20` 读口耗时 <1ms（现状 7.49ms），给前后数字。
3. 迁移 0029 可 up/down；`created_at` 索引在场（`EXPLAIN` 或 schema 断言）。
4. 全量 `pytest -q`／`ruff`／`mypy app appv2`／`lint-imports` 两配置／`check_specs`／`contract_coverage` 全绿。

## 回报：

改动文件＋测试名＋红→绿＋耗时前后对照＋索引证据＋specs diff＋各闸输出＋偏离点。

框架红线: 禁 langgraph/langchain（R5b）；**api 侧不得自造 SQL、不得直引 `appv2.infra.db`**（B3）。
边界红线: 只许动 `appv2/runtimev2/persistence/{store,tables,pg_tables}.py`、`migrations/0029_*.py`、`appv2/api/chat.py::list_runs`（**调用点一处**；若 V2-136 已改则只改调用）、`specs/{persistence,agent-loop}.md`、`tests/domains/test_v2_persistence.py`、`tests/api/test_v2_runs_list.py`；**不动** `api/app.py`／`bridge.py`／两个启动器（V2-136 面）、`web/`、`RunListItem`/`RunView` 形状（V2-142 面）。
