# V2-72 · context 题检索深度（no_hit 后强制兜底钻取）

状态: 待施工 ｜ 优先级: P1 ｜ 来源: 场景对照报告瑕疵④（context 题实锤）

## 背景与根因

场景对照 context 题（那口井最近有递减风险吗——追问续会话）：指代解析成功（ADR-0006
生效）后仅 2 次钻取（faq_lookup no_hit、semantic_query no_hit）即「材料足够——直答收口」，
实际零实质材料，答案为两条 no_hit 如实转答。根因：澄清相位发射判据允许「no_hit 后定稿」
——零探查/零实质材料时收口过早（graph.py 有「零探查观察禁定稿」拒（freshness/lith 题
出现 r0 被拒），但 no_hit 观察在场上未被视作「零实质」）。

## 改动面

`_make_clarify` 发射校验：观察面全为 no_hit/notice 形（无 rows/empty 实质材料）时
**禁定稿**——同「零探查观察禁定稿」语义扩族：拒因回喂重决策，强制下一轮 discover
改用未用过的工具面（semantic_query no_hit 后引导 doc_retrieve 全文检索）。轮预算照旧
约束（≤3 轮兜底，不会无限钻）。

## 验收（场景覆盖：context）

- `test_v2_four_phase.py` 增钉：全 no_hit 观察面 → 定稿被拒（拒因回喂）；随后
  doc_retrieve 命中 → 正常收口；
- 轮预算触界收敛语义不回归（3 轮尽仍收敛直答——budget_converged 面）；
- context 题重放：指代解析成功＋递减分析材料可达（或如实「未找到」——不再是 no_hit 直答）。

## 边界红线

- 「材料足够——直答收口」在**有实质材料**时语义零变化（faq 快答面不受影响）；
- discover 预算 ≤10 不动。

## 依赖与分工

无前置。与 V2-70 同相位不同面。
