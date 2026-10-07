# DE-11 reextract 防重入覆盖入库路径（E3）

> 状态：✅ 完工（2026-10-07，回报 tickets/phase3/reports/DE-11.收尾.md）｜ 依赖：—

任务: reextract 防重入（app/domains/derivatives/service.py:516-528）只防 reextract-vs-reextract；
入库触发的图谱支路运行中调 reextract 不拦——双跑同报告图 upsert 幂等未证，blocked-edges 可能
双记。本票把防护改成「报告级」：**该报告任何图谱支路在跑（入库触发或手动重抽），新图谱写入
一律拒**。交付物：
1. 在跑登记面统一：入库触发与 reextract 共用同一登记（按 report_id；登记点票内定位——入库
   图谱支路启动处与 reextract_graph 入口处），登记生命周期与支路生命周期同生共死（含异常路径
   清理，防泄漏假阳性）。
2. reextract_graph 入口查登记：同报告在跑→现 400 语义保持（归一归 DE-12），报错文案点名
  「入库支路在跑」/「重抽在跑」两态可辨。
3. 测试：入库支路运行中（替身占登记）→reextract 拒；reextract 运行中→第二次拒（既有回归）；
   异常中断后登记清理解除（可再入）。

先读:
- tickets/phase3/挂账清单-20261006.md §E3
- app/domains/derivatives/service.py:516-528（现防重入与 GraphParamError 抛点）
- 入库图谱支路启动处（app/domains/kb/service.py 图谱支路/branch 装配——grep 图谱/extract 定位）

验收:
- [x] 三态测试绿（互斥两向＋异常清理）；既有 reextract 测试零跌
- [x] 登记无泄漏：异常路径清理有测试断言
- [x] 全量闸全绿：`uv run ruff check app tests migrations tools && uv run mypy app && uv run pytest -q && uv run lint-imports && uv run python tools/contract_coverage.py check && uv run python tools/debt_markers.py check`（回报附输出原文含通过数）

回报: 写 tickets/phase3/reports/DE-11.收尾.md。git 纪律：master 拉 `debt/e3-ingest-reentry-guard`；
只 add 本票文件；严禁 `git add -A`。
框架红线: 零新依赖；不改图谱 upsert 本体语义（防护是登记面，不是幂等化——幂等未证的事实照旧
如实登记，不因加了锁就宣称安全）。
边界红线: 只许触碰 app/domains/derivatives/service.py 防重入段＋kb 图谱支路登记点＋测试位。
〔来源：挂账清单-20261006 §E3〕
