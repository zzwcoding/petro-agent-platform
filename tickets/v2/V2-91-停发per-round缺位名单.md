# V2-91 停发 per-round 缺位名单（消除与实投窗自相矛盾）

状态: done（2026-10-18 收票，验收全勾）
日期: 2026-10-18 ｜ 依据：EB8 A-正6 的「检索窗注记（缺位名单）」称《Y-21 井完井工程报告》未纳入，而同窗实有 6 支 Y-21 材料；C-反1 两轮窗不同但名单逐字相同（`接手-EB7vsEB8送窗差异` 取不到③/建议）

## 任务：

停发 `doc_retrieve` 产出的「检索窗注记（缺位名单）」观察——该名单按**单轮检索**算，与实际**多子问题并集＋材料选择**后的送窗不一致，模型会照着它说「某来源未纳入」而该来源实际在窗内。保留：①`window_note` 主段（recalled/sent 计数）②材料渲染披露行（`material_truncated`，按实投窗算）③审计面（ToolResult metadata／日志里可留名单，不再进 `state.observations`）。「按实投窗重算的缺位名单」登记为后续能力（不在本票恢复）。

## 先读：

- `appv2/tools/handlers.py`（`_missing_sources_segment` 与其观察装配点；`doc_retrieve` 返回前）
- `appv2/retrieval/engine.py`（`build_window_note` 的 missing 来源）
- `appv2/runtimev2/context/materials.py`（渲染披露行——本票不动）
- `specs/tools.md`／`specs/retrieval.md`（缺位名单相关行为，若有）
- `docs/runtime-refactor/research/接手-EB7vsEB8送窗差异-20261018.md`（A-正6 证据）

## 施工基准：

- 在 `doc_retrieve` 观察装配处：**不再**把 `_missing_sources_segment(window_note)` 作为独立观察（`检索窗注记（缺位名单）`）追加到 `state.observations`；`window_note` 主段与其余观察零改。
- 名单仍留在工具调用结果/日志的机读面（如 `ToolResult.meta["missing_sources"]`，若现无此键则落日志即可），供审计；**不进模型材料、不进引擎注记**。
- 逐字文案零改（不新造话术）。

## 测试：

1. `::no_missing_sources_observation`：桩检索返回带 missing 的 window_note → observations 里**无**「检索窗注记（缺位名单）」观察；主段计数观察仍在。
2. `::window_note_counts_unchanged`：recalled/sent 主段逐字不变（含差额段）。
3. `::missing_sources_kept_in_audit`：missing 名单仍可在 ToolResult/日志机读面取到（审计不丢）。
4. 既有 retrieval/handlers 测试按新行为改判（判据意图保留：计数如实、缺位不静默——改为审计面不静默）。

## 验收：以下 4 条全绿算收票（逐条机检）。

1. 上述 3 测绿；既有测试零回退（按新形改判处逐条列出）。
2. 全量 `pytest -q` 全绿；ruff 全树过。
3. `specs/tools.md`／`specs/retrieval.md` 相关行为注同步（停发理由＋后续「按实投窗重算」登记）。
4. 主窗复跑 EB9：答案中不再出现「某来源未纳入」而该来源在窗内的自相矛盾（A-正6 重点核）。

## 回报：

改动文件＋测试名＋全量数字＋A-正6 形离线/真机对照。

框架红线: 无点名框架。
边界红线: 只许动 `appv2/tools/handlers.py`（停发点＋审计面）、对应测试、`specs/tools.md`／`specs/retrieval.md` 注；**不碰** `retrieval/engine.py` 的名单计算、`context/materials.py` 披露行、transport 帧面。

## 收票回写（2026-10-18）

- 施工：`handlers._bundle_to_result` 不再追加 `locator.kind=window_miss` 观察；notice 正文摘除缺位段（主段计数逐字保留）；名单落模块日志作审计面；`specs/tools.md`／`specs/retrieval.md` 同步注。
- 测试：新增 `test_v2_v291_missing_sources_stop.py` 5 例；`test_v2_r1c_window_recall.py` 9 例按新行为改判（逐条清单见回报）；全量 **2393 passed / 0 failed**；ruff／import-linter 绿。
- 偏离/登记：①notice 正文摘除缺位段（否则经 engine_notes 仍进模型面）；②**V2-46 缺位回捞门随之失效**（`graph.py` 只认 window_miss 观察，停发后恒不开；边界禁动，改判测试并登记——回捞能力待「按实投窗重算」后重做）；③审计面走模块日志（`ToolResult` 无 meta 键）。
- 未做：A-正6 真机对照由主窗/跑批子代理执行（EB9）。
