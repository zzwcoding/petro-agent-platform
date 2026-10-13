# V2-72 · context 题检索深度（no_hit 后强制兜底钻取）

状态: 已完工（2026-10-13 Owner 拍 b 案——旁路保留＋零材料未找到形态）｜ 优先级: P1 ｜ 来源: 场景对照报告瑕疵④（context 题实锤）

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

## 施工发现（2026-10-13——施工中止，待 Owner 裁决）

取证结论：context 题过早定稿的根因＝`_zero_probe_block` 的**追问续跑旁路**
（graph.py：`if state.followup_of: return False`——追问形态跳过零探查闸）。但该旁路是
已验收行为的承重墙：`test_v2_multi_turn_context.py::test_followup_context_carries_prior_qa_history`
钉死「追问零探查直答」（前轮答案已可答时不再探查——会话线程承接语义）。移除旁路＝
改已验收行为＋该测试重写。候选案（呈 Owner）：
a) 移除旁路——追问也必须先探查（历史直答能力消失，测试重写）；
b) 折中——旁路保留，但零实质材料定稿时答案强制改写为「未找到」形态＋notice
   （不再以 no_hit 文本冒充答案面，直答能力保留）；
c) 收窄——仅当前轮答案含实质数值材料时允许零探查直答（机判面复杂，不推荐）。

## 拍案与实施（2026-10-13——b 案完工）

Owner 拍 **b 案**（旁路保留＋零实质材料收口改「未找到」形态）。实施：
- verify 节点零实质材料分支新增追问特判（`followup_of` 且 draft 空）：
  答案＝「未找到（材料未披露）：追问与前轮材料均未覆盖本题——未取得可交付
  观察材料，如实回报，不编造。」＋decision_note 机读 notice 随行；
- 旁路与直答能力零改动（`_zero_probe_block` 旁路原样；draft 面照走原支——
  历史直答保留）；有实质材料的追问零漂移（既有追问钉测全绿）；
- 新钉 `test_followup_zero_material_finalizes_as_not_found`（零探查追问→
  未找到面＋notice）；全量 1708 过零跌，ruff/mypy/lint-imports 绿。


