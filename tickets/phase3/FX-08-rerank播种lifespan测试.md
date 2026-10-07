# FX-08 rerank 播种 lifespan 接线测试（R2-02）

> 状态：⬜ 可开工 ｜ 依赖：R2 裁决
> 来源：审查 R2（reports/审查R2-批34-20261007.md）L0 裁决——审查-修复链修复拍。

任务:
1. 补 lifespan 级测试（monkeypatch.setenv＋`with TestClient(app)`）：①RERANK_TIER=非法值→启动抛
   RerankTierEnvError（TestClient 进入上下文即触发 lifespan）；②合法值→启动完成且种子行落库（替身/
   内存存储或既有测试库惯例）；③无 env→现状零变化（无播种日志）。三例都真穿 main lifespan 接线段。
2. 顺带（R2-06）：合法域测试改遍历 RERANK_TIERS 常量，不硬编码三档。

先读:
- tickets/phase3/reports/审查R2-批34-20261007.md R2-02 条＋L0 裁决节
- tickets/phase3/reports/DE-10.收尾.md、app/main.py:177-180（de10 分支接线段）、
  tests/domains/retrieval/test_rerank_env_seeding.py、tests/test_smoke.py（TestClient 模块级实例化惯例）

验收:
- [x] 对应发现条目的修复断言测试红先绿后（突变验证：临时摘除 main.py 接线段→非法值/合法值两例真红，
      无 env 零变化例如期保持绿——其职责即钉「无行为」不变量；恢复后 13/13 绿。回报附记录）
- [x] 既有测试零跌（所在分支基线：954 过 83 跳 → 修后 957 过 83 跳＝+3 全为新例，零跌）
- [x] 全量闸：`uv run ruff check app tests migrations tools && uv run mypy app && uv run pytest -q && uv run lint-imports && uv run python tools/contract_coverage.py check && uv run python tools/debt_markers.py check` 全绿（回报附输出原文含通过数数字）

回报: 写 tickets/phase3/reports/FX-08-rerank播种lifespan测试.收尾.md。git 纪律：在既有票分支上续提交（不拉新分支），
只 add 本修复票文件（含复制进工作树的票面勾选版），严禁 git add -A。

框架红线: 零新依赖；修复范围严格限于裁决条目。
边界红线: 只许触碰对应发现涉及的文件与测试位。
〔来源：审查R2-批34-20261007 L0 裁决节〕
