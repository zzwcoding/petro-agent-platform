# FX-06b 收尾回报——well_overhaul 过滤复合键对齐（R1-06 补遗）

> 状态：✅ 完工 ｜ 分支：`debt/de02-wells-snapshot-filter`（FX-06 940ffbe 之上续提交）｜ 日期：2026-10-07
> 六闸全绿（原文摘要见 §3）；PG 实跑（TEST_DATABASE_URL 指 dev compose pg）wells 全目录＋
> midplatform 基础设施 75 例绿（FX-06 基线 73＋本票净增 2）。
> commit SHA：见 `git log -1 --format=%H`（本票单提交，FX-06 后第一笔）。

## 1. 产物清单（文件＋动作）

| 文件 | 动作 | 内容 |
|---|---|---|
| `app/domains/wells/store.py` | 修改 | ①新增 `_BUSINESS_KEYS` 闭世界常量——照抄 data-plane `app/data_plane/lake_store.py:76` 三行（well_info=(well_id)／well_overhaul=(well_id, overhaul_start, overhaul_end)／well_measures=(well_id)），注源注释「SSOT＝data-plane lake_store，扩表随其票同步，不发明第二套键定义」；②`_current_version_asof` 分区键从硬编码 `well_id` 等值改逐表查 `_BUSINESS_KEYS`——键列相关用 `IS NOT DISTINCT FROM`（＝窗口 PARTITION 的 NULL 同组语义：well_overhaul 起止列 001 DDL 无 NOT NULL，等值比较会让空值行因 NULL 失配整行丢失；max 半连接骨架＝FX-06 原样不推倒，RANK()=1 等价口径不变：同键同快照并列行全保留、跨批旧版不混用）；③模块 docstring 过滤段随动（「每业务键 well_id」→逐表业务键复合键） |
| `tests/domains/wells/test_wells_snapshot_filter_pg.py` | 修改 | ①既有检修 fixture O2 批扩修订行（同 O1 复合键 well_id+起止、批 2 重导——「被更新那条出最新版」入基线 fixture）；②DE-02「台账只出最新批」断言按新语义改写（测试改名 `test_chain_ledgers_only_latest_batch`→`test_chain_ledgers_latest_version_per_business_key`：检修出检泵＋洗井修订两行、洗井旧版被同键新版覆盖不出现；措施 well_id 键行为零变化断言保留）；③两个回落态断言随动（well_overhaul 账本清空→3 行全出含被覆盖旧版——回落态与过滤态首次可区分；drop 账本例 overhauls 计数 2→3；完工日同日并列行排序不稳定改 sorted 对账）；④FX-06b 新例 2 枚＋共用装载器 `_load_overhaul_scenario`（增量批例：批 1 两记录全量、批 2 只更新洗井一条——断言检泵（批 2 未含的旧批记录）仍可见、洗井修订出批 2、每复合键恰 1 行；RANK 并列例：单批同复合键同 _snapshot_id 两行（A/B 班）——断言两行全保留，照 lake_store scan「RANK 非 ROW_NUMBER」注记钉口径）；模块 docstring 断言段随动 |
| `tickets/phase3/FX-06b-overhaul复合键对齐.md` | 新增（自主仓复制） | 票面验收框勾选 |

编译 SQL 形态实录（well_overhaul；`_BUSINESS_KEYS` 驱动，其余两表同构减列）：

```sql
SELECT raw.well_overhaul.* FROM raw.well_overhaul
WHERE raw.well_overhaul._snapshot_id = (
    SELECT max(well_overhaul_1._snapshot_id) FROM raw.well_overhaul AS well_overhaul_1
    WHERE well_overhaul_1.well_id         IS NOT DISTINCT FROM raw.well_overhaul.well_id
      AND well_overhaul_1.overhaul_start  IS NOT DISTINCT FROM raw.well_overhaul.overhaul_start
      AND well_overhaul_1.overhaul_end    IS NOT DISTINCT FROM raw.well_overhaul.overhaul_end
      AND well_overhaul_1._snapshot_id <= 42)
```

## 2. 票面验收逐条

- [x] **复合键增量批 PG 例红先绿后（改前旧记录丢失可见红）**——红：store 未改
  跑 `test_incremental_overhaul_batch_keeps_other_records`＝FAILED，断言输出
  「Right contains one more item: 检泵…」——per-well_id 旧谓词下检泵（批 2
  未含的旧批其他检修记录）随井最新版整批消失，列表只剩洗井修订 1 行；
  绿：复合键化后全文件 9 例绿。红绿两轮输出在案（§4）。
- [x] **well_info/well_measures 既有回归零跌；RANK 并列口径有断言**——well_info
  五查询键列仍 (well_id)、well_measures 仍 (well_id)（`_BUSINESS_KEYS` 照抄
  湖真源，零语义变化），既有增量批井例／列表/档案/回落各例全绿；RANK 口径
  新例 `test_same_snapshot_tied_rows_all_kept` 钉死（同键同 _snapshot_id
  两行全保留）。
- [x] **全量闸全绿**——见 §3 原文摘要（六段，含通过数数字）。

红线遵守：零新依赖（pyproject 零改动）；响应 DTO 零变化（app/api/wells.py 零
触碰）；service.py 零触碰（键解析语义不变——face.snapshot_id 照传作 as-of 上
界；其 docstring 旧短语遗留＝FX-06 疑点 2 原样登记，归 wells 域下次触碰该文件
的票）；snapshot.py 零触碰（本票无需改动）；不动 web/、migrations/、data-plane
仓。data-plane 交付物验证期临时符号链接主仓检出（前票先例），验证后删除链接
再提交。

## 3. 闸门实跑输出原文摘要

```
$ uv run ruff check app tests migrations tools
All checks passed!

$ uv run mypy app
Success: no issues found in 77 source files

$ uv run pytest -q
959 passed, 97 skipped, 1 warning in 23.84s
（FX-06 后基线 959 过 95 跳——本票净增 2 个 PG 门控测试，无环境时 skip，
对账吻合：97＝95＋2；过数零变化＝非 PG 例零触碰）

$ uv run lint-imports
Contracts: 5 kept, 0 broken.（Analyzed 115 files, 546 dependencies.）

$ uv run python tools/contract_coverage.py check
合同覆盖率闸绿：170 条合同端点双向对账通过。

$ uv run python tools/debt_markers.py check
债务标记闸绿：web 源码债务短语全部携可解析 DEBT 标签（盘点 33 条见 report）。

—— 附加（票面闸外，本地实跑 PG 集成，前票同口径联跑）：
$ TEST_DATABASE_URL=postgresql+asyncpg://petro:petro@localhost:5433/petro \
  uv run pytest tests/domains/wells/ tests/infra/test_db_midplatform_pg.py -q
75 passed, 1 warning in 19.78s
（wells 全目录 68＋midplatform 基础设施 7＝75；FX-06 同口径联跑 73＋本票
  新例 2，零跌）
```

## 4. 红先绿后实录（要点）

- 红（store 未改，per-well_id 旧谓词）：`test_incremental_overhaul_batch_keeps_other_records`
  FAILED——`AssertionError: assert [...] == [...]`，实际 overhauls 仅
  `洗井（批 2 修订）` 1 行，`Right contains one more item: 检泵`（批 1 独有
  键整条消失＝R1-01 同款静默丢失形态，与票面风险原文逐字对上）。
- 绿（复合键化后）：`tests/domains/wells/test_wells_snapshot_filter_pg.py`
  全文件 `9 passed`（新例 2＋改写断言＋既有 6 例零跌）。

## 5. 偏差逐条（现象→原因→处置）

1. **键列相关用 IS NOT DISTINCT FROM 而非等值**（现象：票面任务 1 只说「分区
   键改逐表闭世界常量」，未规定比较符；FX-06 原实现对 well_id 用 `==`）——
   原因：well_overhaul 起止列在 data-plane 001 DDL 无 NOT NULL（检修未完工
   ＝overhaul_end 空是真实形态，list_overhauls 排序本就 `nulls_last`）；窗口
   PARTITION 的 NULL 同组语义下，等值相关会让空值键行因 `NULL=NULL` 失配取
   不到 max 而**整行消失**——与 RANK()=1 不等价。处置：键列统一
   `IS NOT DISTINCT FROM`（PG 原生，语义＝「窗口分组的同组」），实现与湖
   scan RANK 严格等价；base fixture 未造空值行（真实空值批到货前无机判例，
   语义由比较符本身承载），登记疑点 2。
2. **DE-02「台账只出最新批」测试改名**（现象：`test_chain_ledgers_only_latest_batch`
   →`test_chain_ledgers_latest_version_per_business_key`）——原因：检修台账
   新语义下不再「只出最新批」（旧批不同复合键记录仍可见），原名与断言矛盾。
   处置：同名槽位断言改写＋改名，回报报备。
3. **基线检修 fixture O2 批扩修订行**（现象：既有两批 fixture 改了一行造数）
   ——原因：DE-02 旧断言依赖「O1/O2 异复合键＋只出最新批」；新语义下若
   fixture 不含同键跨批对，回落态与过滤态输出相同、回落测试失去区分度。
   处置：O2 批增洗井修订行（同 O1 复合键）——过滤态＝检泵＋修订 2 行、
   回落态＝3 行（含被覆盖旧版），两态首次可区分；per-well_id 旧语义下该
   fixture 两行恰都在最新批，故改写后断言在旧代码下也绿——复合键行为的
   红先绿后机判由增量批专例承载（票面验收 1 口径），两例分工在案。

## 6. 疑点（列 L0 不动手）

1. **well_overhaul 空值复合键无机判例**（偏差 1 关联）——`IS NOT DISTINCT
   FROM` 已承载 NULL 同组语义，但仓内 fixture 尚无「起止含空」的检修行到货
   场景例；真实湖数据出现空起止行时的读面行为本票未造数验证。修法：fixture
   增空值行例（同键空起止并列/跨批覆盖两断言），归 wells 域下次触碰该测试
   文件的票顺带补。
2. **service.py 类 docstring 谓词旧短语**（FX-06 疑点 2 原样沿用）——
   `WellsService` docstring 仍写「按 ``_snapshot_id = 湖当前版`` 过滤」，本票
   边界红线未列 service.py，不动；归 wells 域下次触碰该文件的票顺带对齐。
