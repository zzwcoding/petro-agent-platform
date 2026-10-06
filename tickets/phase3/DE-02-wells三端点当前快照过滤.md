# DE-02 wells 三端点接当前快照过滤（E10 后半——M-02 读面缺陷收口）

> 状态：✅ 完工（2026-10-07，回报见 tickets/phase3/reports/DE-02.收尾.md）｜ 依赖：DE-01

任务: 把 DE-01 解析器接进 M-02 三个读端点，收口「多批重复行」。交付物：
1. 端点 1 GET /api/wells（列表）：查询加当前快照过滤——仅最新批次的行。
2. 端点 2 GET /api/wells/{well_id}（档案明细）：同款过滤。
3. 端点 3 GET /api/wells/{well_id}/chain（关系链）：同款过滤。
4. 多批 fixture 回归测试（tests/pg/ 或既有 wells 测试位）：造 well_info 两批次数据＋对应
   lake_snapshot 账本行——断言列表每井恰 1 行、档案/关系链只出最新批内容；账本无记录态回落
   全量（对齐 DE-01 三态语义）。

先读:
- tickets/phase3/DE-01-湖当前版快照解析器.md（解析器形状与注入缝）
- app/api/wells.py:44-130（三端点）、app/domains/wells/store.py（SQL 落点）
- tickets/phase3/挂账清单-20261006.md §E10（「合同读语义『当前版』未在 SQL 落地」定性）

验收:
- [x] 三端点多批 fixture 回归全绿（每井 1 行断言在案）
- [x] 合同形状零变化：响应模型/字段/状态码不动（A2-井档案.md v0.2 读语义本就是「当前版」，
  本票是把合同语义在 SQL 落地，不是合同变更——回报中引合同原文佐证）
- [x] 全量闸 `uv run ruff check app tests migrations tools && uv run mypy app && uv run pytest -q && uv run lint-imports && uv run python tools/contract_coverage.py check && uv run python tools/debt_markers.py check` 全绿（回报附输出原文）

回报: 写 tickets/phase3/reports/DE-02.收尾.md——产物清单＋SHA/闸门输出原文/偏差/疑点。git 纪律：
master 拉 `debt/de02-wells-snapshot-filter`；只 add 本票文件；严禁 `git add -A`。
框架红线: 零新依赖；响应 DTO 零变化。
边界红线: 只许触碰 app/domains/wells/、app/api/wells.py 内查询装配行与对应测试位。
〔来源：挂账清单-20261006 §E10；A2-井档案.md v0.2〕
