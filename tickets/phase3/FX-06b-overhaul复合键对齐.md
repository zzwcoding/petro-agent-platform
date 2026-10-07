# FX-06b well_overhaul 过滤复合键对齐（R1-06 补遗——FX-06 实施裁决）

> 状态：✅ 完工 ｜ 依赖：FX-06（同分支在其后）
> 来源：FX-06 收尾疑点 1 的 L0 裁决。湖底座 `_BUSINESS_KEYS`（data-plane lake_store.py:76）实证：
> well_overhaul＝(well_id, overhaul_start, overhaul_end) 复合键；well_info/well_measures＝(well_id)
> 单键（measures 措施次列未供给退化井号）。FX-06 按票面统一 per-well_id 落地——对 well_overhaul
> 而言，增量批下该井旧批的**其他检修记录**会随井最新版整批消失，正是 R1-01 要消灭的静默丢失形态。

任务:
1. wells store 三台账查询的 as-of 半连接分区键改为**逐表闭世界常量**（新常量照抄
   data-plane/app/data_plane/lake_store.py:76 `_BUSINESS_KEYS` 的 well_info/well_overhaul/
   well_measures 三行，注源注释「SSOT＝data-plane lake_store，扩表随其票同步」）：well_info
   (well_id)、well_overhaul (well_id, overhaul_start, overhaul_end)、well_measures (well_id)。
2. 对齐湖 scan 的 RANK 语义细节：同键并列行（同 _snapshot_id 多行）全保留（照 lake_store.py:168
   RANK 非 ROW_NUMBER 注记）——实现与测试都要钉这个口径。
3. 回归修正：DE-02 既有「台账只出最新批」断言按新语义改写（well_overhaul 增量批下：旧批的其他
   检修记录仍可见、被更新的那条记录出最新版）；well_info/well_measures 行为零变化回归保留。
4. PG 增量批 fixture 扩一例：well_overhaul 第二批只更新某井一条检修记录——断言该井其余旧批记录
   仍在、更新条出批 2。

先读:
- tickets/phase3/reports/FX-06-wells过滤per-key对齐.收尾.md（疑点 1 原文）
- data-plane/app/data_plane/lake_store.py:76-90（_BUSINESS_KEYS）、:152-185（scan as-of RANK 语义）
- app/domains/wells/store.py（FX-06 后的 _current_version_asof 谓词）、app/domains/wells/snapshot.py

验收:
- [x] 复合键增量批 PG 例红先绿后（改前旧记录丢失可见红）
- [x] well_info/well_measures 既有回归零跌；RANK 并列口径有断言
- [x] 全量闸：`uv run ruff check app tests migrations tools && uv run mypy app && uv run pytest -q && uv run lint-imports && uv run python tools/contract_coverage.py check && uv run python tools/debt_markers.py check` 全绿（回报附输出原文含通过数数字）

回报: 写 tickets/phase3/reports/FX-06b.收尾.md。git 纪律：debt/de02-wells-snapshot-filter 分支续
提交（不拉新分支），只 add 本票文件，严禁 git add -A。

框架红线: 零新依赖；分区键常量闭世界照抄 data-plane 真源，不发明第二套键定义。
边界红线: 只许触碰 app/domains/wells/（store/snapshot 常量与谓词）与测试位。
〔来源：审查R1-批12 L0 裁决节 FX-06 条；FX-06 收尾疑点 1；湖底座 _BUSINESS_KEYS 实证〕
