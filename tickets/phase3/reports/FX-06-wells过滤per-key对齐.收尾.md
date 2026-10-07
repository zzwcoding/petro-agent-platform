# FX-06 收尾回报——wells 当前版过滤改 per-key as-of 对齐（R1-01）

> 状态：✅ 完工 ｜ 分支：`debt/de02-wells-snapshot-filter`（DE-01 24d7206、DE-02 7380fc4、FX-01 708be2e 之上续提交）｜ 日期：2026-10-07
> 六闸全绿（原文摘要见 §3）；PG 实跑（TEST_DATABASE_URL 指 dev compose pg）wells 全目录＋midplatform 基础设施 73 例绿（含增量批新例）。
> commit SHA：见 `git log -1 --format=%H`（本票单提交，FX-01 后第二笔）。

## 1. 产物清单（文件＋动作）

| 文件 | 动作 | 内容 |
|---|---|---|
| `app/domains/wells/store.py` | 修改 | ①新增 `_current_version_asof(table, snapshot_id)` helper——per-key 最新版半连接谓词：相关子查询取该 well_id 窗口内 `max(_snapshot_id) WHERE _snapshot_id <= N`，外行 `_snapshot_id` 与之相等即当前版（与 data-plane lake_store.scan 的 RANK()=1 等价：同批并列行全保留、跨批旧版被新版覆盖不混用；SQL 形态票内定案取相关子查询——外查询列/排序/形状零变化）；②五查询（list_wells/get_well/get_well_unfiltered/list_measures/list_overhauls）的 `_snapshot_id = 全局最新批` 等值过滤统一换装该谓词；③模块 docstring 与 list_wells docstring 的谓词描述随动（「``_snapshot_id = 键``」→ per-key as-of） |
| `app/domains/wells/snapshot.py` | 修改 | 消费示例注释一行随动（DE-02 注释引用的旧谓词形状「``_snapshot_id == face.snapshot_id``」已不实——改为 per-key as-of 描述，face.snapshot_id 语义＝as-of 上界 N）。零逻辑改动 |
| `tests/domains/wells/test_wells_snapshot_filter_pg.py` | 修改 | 增量批回归 1 例新增（原 7 例零改动）：fixture 增 `_FIXTURE_INCREMENTAL`（批 1 两井全量导出＋批 2 增量只含 N-02 的更新）＋装载器 `_load_incremental_scenario`（只动两 fixture 井与 DE02-I 前缀账本行，插入序 I1→I2 保证 snapshot_id 递增＝最新批判据）——断言列表每井恰 1 行、N-02 出批 2 数据、N-06 仍以批 1 数据可见、档案端点 N-06 不 404 |
| `tickets/phase3/FX-06-wells过滤per-key对齐.md` | 新增（自主仓复制） | 票面验收框勾选 |

编译 SQL 形态实录（list_wells；其余四查询同构）：

```sql
SELECT raw.well_info.well_id, ... FROM raw.well_info
WHERE raw.well_info._snapshot_id = (
    SELECT max(well_info_1._snapshot_id) FROM raw.well_info AS well_info_1
    WHERE well_info_1.well_id = raw.well_info.well_id
      AND well_info_1._snapshot_id <= 42)
ORDER BY raw.well_info.well_id ASC
```

## 2. 票面验收逐条

- [x] **对应发现条目的修复断言测试红先绿后**——红：五查询未改前跑
  `test_incremental_batch_keeps_old_batch_wells`＝FAILED，断言输出
  `well_ids == ['N-02']`（N-06 计数 0＝旧批井静默消失，与 R1-01 风险原文逐字
  对上）；绿：五查询换装 per-key 半连接后 wells 全目录 66 例绿（含新例与
  DE-02 全部既有回归）。红绿两轮输出在案（§4）。
- [x] **既有测试零跌**——pytest 959 过 95 跳＝FX-01 后基线 959 过 94 跳＋本票
  新增 PG 门控 skip 1（无 TEST_DATABASE_URL 按仓约定 skip），逐数对账吻合；
  既有全量批场景（DE-02 五例含「关系链台账只出最新批」「回落两态」）零跌。
- [x] **全量闸全绿**——见 §3 原文摘要（六段，含通过数数字）。

红线遵守：零新依赖（pyproject 零改动）；响应 DTO 零变化（app/api/wells.py 零
触碰）；service.py 零触碰（键解析语义不变——face.snapshot_id 照传，只是谓词
消费端从等值改 as-of 上界）；不动 web/、migrations/、data-plane 仓。data-plane
交付物验证期临时符号链接主仓检出（前票先例），验证后删除链接再提交。

## 3. 闸门实跑输出原文摘要

```
$ uv run ruff check app tests migrations tools
All checks passed!

$ uv run mypy app
Success: no issues found in 77 source files

$ uv run pytest -q
959 passed, 95 skipped, 1 warning in 24.01s
（FX-01 后基线 959 过 94 跳——本票净增 1 个 PG 门控测试，无环境时 skip，对账吻合）

$ uv run lint-imports
Contracts: 5 kept, 0 broken.

$ uv run python tools/contract_coverage.py check
合同覆盖率闸绿：170 条合同端点双向对账通过。

$ uv run python tools/debt_markers.py check
债务标记闸绿：web 源码债务短语全部携可解析 DEBT 标签（盘点 33 条见 report）。

—— 附加（票面闸外，本地实跑 PG 集成，DE-02 同口径联跑）：
$ TEST_DATABASE_URL=postgresql+asyncpg://petro:petro@localhost:5433/petro \
  uv run pytest tests/domains/wells/ tests/infra/test_db_midplatform_pg.py -q
73 passed, 1 warning in 23.60s
（wells 全目录 66＋midplatform 基础设施 7＝73；含本票增量批新例 1——DE-02 同口径
  联跑 68 例＋FX-01 drop 表例 1＋本票新例 1＋其余 wells 单测，零跌）
```

## 4. 红先绿后实录（要点）

- 红（五查询未改，增量批例首跑）：
  `FAILED ... assert (1 == 1 and 0 == 1)`——`well_ids == ['N-02']`，N-06 从列表
  静默消失（旧过滤＝全局最新批 DE02-I2 等值，N-06 无批 2 行即无行）。
- 绿（per-key 半连接换装后）：`tests/domains/wells/` 全目录 `66 passed`
  （新例＋DE-02 既有回归＋FX-01 drop 表例全绿）。

## 5. 偏差逐条（现象→原因→处置）

1. **well_overhaul 的 per-key 键与湖 `_BUSINESS_KEYS` 的偏差**（现象：票面定案
   「每 well_id 取其自身最大 _snapshot_id」，而 data-plane lake_store.py:76-85
   对 well_overhaul 的业务键是复合键 `(well_id, overhaul_start, overhaul_end)`
   ——严格按湖 scan 语义，增量批下「批 2 只含某井一条新检修记录」时该井批 1 的
   **不同起止**检修记录仍应可见；现按票面 per-well_id 落地则随井最新版整批消失）——
   原因：票面原文两处均钉 well_id（「每 well_id 取其自身最大 _snapshot_id 的
   行」＋派单注记「per-key 键＝各表业务键（well_id）」），且 DE-02 既有回归
   「关系链台账只出最新批」（O1 洗井/O2 检泵 两批各一行断言只出检泵）只有
   per-well_id 语义能保绿；well_info/well_measures 两表湖业务键本就是
   `(well_id,)`（lake_store.py:77/81——measures 注记「措施次列未供给→退化
   井号」），零偏差。处置：实现照票面 per-well_id（三表统一），此偏差列疑点 1
   交 L0/Owner 裁决（若判「检修台账应对齐复合键」，是一行 helper 改动——
   分区键扩三列——加一例增量回归即可）。
2. **snapshot.py 消费示例注释一行随动**（现象：票面边界红线「只许触碰对应发现
   涉及的文件与测试位」，snapshot.py 不在 R1-01 证据文件内）——原因：该注释
   逐字引用被本票替换的旧谓词形状（「``_snapshot_id == face.snapshot_id``」），
   不随动即留下对已删代码的错误描述。处置：仅注释一行、零逻辑；派单注记
   「FX-01 与 FX-06 都动 snapshot.py/store.py」预期内；报备。
3. **增量批场景用独立 fixture/loader 不动既有两批 fixture**（现象：票面「PG 回归
   fixture 增增量批场景」——若把既有 B2 改成增量会跌 DE-02 三个既有断言）——
   原因：既有 fixture 的 B1/B2 是「每批全量导出」形态，回落态测试依赖「每井两
   行」；增量场景是另一前提（只导变化井），须独立造数。处置：新 loader 先清
   后插只动本票造数自留地（两 fixture 井＋DE02-I 前缀账本行），与既有测试
   共存纪律一致；既有全量批场景回归零跌（票面要求兑现）。

## 6. 疑点（列 L0 不动手）

1. **well_overhaul 复合键对齐问题**（偏差 1 详述）——湖业务键＝well_id+起止，
   per-well_id 在增量批下会淹没该井旧批的不同检修记录。查 teach 合同册端点 3
   未见「台账每批全量导出」级不变式；属业务语义裁决，交 Owner（修法一行：
   `_current_version_asof` 分区键扩列）。well_measures 无此问题（湖键本就是
   井号退化）。
2. **service.py 类 docstring 的谓词短语未随动**（现象：`WellsService` docstring
   仍写「按 ``_snapshot_id = 湖当前版`` 过滤」）——原因：service.py 不在本票
   边界（R1-01 证据与派单注记均未列），其描述的键解析/传参行为本票零改动，
   仅短语与 store 谓词新形状有措辞差。处置：不动，登记——归 wells 域下次
   触碰该文件的票顺带对齐（一句话改动）。
