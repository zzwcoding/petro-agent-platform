# DE-13 reextract 面微清扫（E5＋E6——两小件一票）

> 状态：⬜ 可开工 ｜ 依赖：—

任务: 两个一行级卫生件同域同票清扫。交付物：
1. E5 审计 action 风格：reextract 审计 action「图谱重抽」改为点分风格（对齐既有
  「graph.extract_config.saved」族——新名建议 `graph.reextract.requested`，票内按既有 action
  清单定名，不发明第二套风格）。
2. E6 冗余 import：app/domains/derivatives/service.py:526 函数内
  `from app.domains.derivatives.domain import GraphParamError` 删除（顶部 `domain as d` 已可覆
  ——:795 即用 d.GraphParamError 先例）。
3. 核对面：审计 action 改名对消费方零影响核对（grep 旧 action 字符串全仓——无消费即安全改名，
  有消费则列出并处置）；审计历史行不改写（append-only 教义）。

先读:
- tickets/phase3/挂账清单-20261006.md §E5/§E6
- app/domains/derivatives/service.py:516-530（reextract_graph 审计写点＋函数内 import）、
  既有点分 action 清单（grep "audit" app/domains/ 点分命名先例）

验收:
- [ ] 全仓 grep 无函数内 GraphParamError import；新 action 点分且旧串无消费方（核对记录落回报）
- [ ] 全量闸全绿：`uv run ruff check app tests migrations tools && uv run mypy app && uv run pytest -q && uv run lint-imports && uv run python tools/contract_coverage.py check && uv run python tools/debt_markers.py check`（回报附输出原文含通过数）

回报: 写 tickets/phase3/reports/DE-13.收尾.md。git 纪律：master 拉 `debt/e56-reextract-cleanup`；
只 add 本票文件；严禁 `git add -A`。
框架红线: 零新依赖；审计历史行不迁移不改写。
边界红线: 只许触碰 app/domains/derivatives/service.py 两处＋测试位。
〔来源：挂账清单-20261006 §E5/§E6〕
