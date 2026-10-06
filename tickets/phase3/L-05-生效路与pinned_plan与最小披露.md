# L-05 生效路与 pinned_plan 与最小披露（生效＋钉入新缝＋披露同批——闸 B 交付）

> 状态：⬜ 可开工 ｜ 依赖：闸 A（Owner 看影子报告拍板过闸）＋L-04（golden 回归闸在位）。
> 开工前置：闸 A 过后影子批（L-01~L-04）合入 master，本票自 master 拉分支；影子批未合入
> ＝依赖未清，停工升级 Owner。

任务: 实现阶段 3 方案 v2.1 应用线 L-05——LLM#plan 从影子转生效＋pinned_plan 新缝＋最小
披露同批（D5 决策：披露与生效同批，本票不拆）。TDD 先红后绿（每件交付物先写测试见红→
实现转绿；前端 vitest 同纪律）。四件交付物：
1. 生效开关＋兜底生效路：配置布尔键（票内定案：挂 app/infra/config.py Settings 面，
   additive 一键，默认 false＝快路-only 现状；「B 关开关即回现状」回退纪律的载体）。
   开关 on∧触发谓词 True→LLM#plan 产物过 validator→通过则钉入 ctx.pinned_plan 进链，
   拒则走兜底路（照现状链路，零新合同形状，票内定案分派）：
   - ctx.clarify_available 有额度→既有澄清帧（candidates 澄清帧，build_candidate_clarify
     既有面）有界一次（澄清额度机制现状不动，第二次 409 合同值照旧）；
   - 无额度→现行降级解释链接续（_continue_with_retrieval，chains.py:1737，W-AUX③ 现状
     链路——如实标注不冒充审定口径）。
2. pinned_plan 新缝（机制 11；评审意见 6 在案：钉入/挂起携带/恢复消费全是新接线）：
   - ChainContext 增字段 `pinned_plan: QueryPlan | None = None`（domain.py:685；字段闭
     世界——只钉已验证 QueryPlan，不发明第二意图结构，守 D2）；
   - N7.1 消费（chains.py:1331 区）：有 pinned_plan→重跑 validator 只做确定性校验（依旧
     零模型），通过则直用钉入 plan（node 行如实标注「意图来源：LLM 精解析（已复验）」）；
     校验拒→按交付物 1 兜底路；快路（确定性信号齐）链路零改动、不钉 plan；
   - 持久化载体（票内定案，**本验收对象**）：chat_run 表新增 jsonb 列 plan_pinned
     （migrations/versions/ 新迁移一文件——编号顺延现版 0020 之后，日期以开工日为准；
     序列化＝QueryPlan dict 化/重建两向测试在案）。候选二（复用 verdict jsonb 内嵌键）
     否决理由：裁决与意图混载；若开工发现迁移惯例冲突，回退候选二并偏差记回报呈 Owner；
   - 审批挂起恢复重跑 validator（F7 幂等升级为「持久化意图的确定性重放」）：
     service._resume_approval（service.py:831 区——【注意】方案册引 823-829 为旧行号，
     现位已漂移）恢复时取持久化 plan→重跑 validator（不盲信挂起时载荷）→过则整节点重跑
     消费 pinned plan（不重调 LLM——D1 前提：批过的外表集与重跑后执行的一致）→拒则按
     兜底路。resume 语义已由 teach T-01 升级为正式行为规则注记（拍板记录开放问题 2 立场）
     ——开工核对 teach specs/api/A1-问一问.md 2026-10-05 变更行与本票行为一致，不一致＝
     缺陷回 teach 改，不在本仓私改语义。
3. 最小披露同批（D5；评审意见 2 在案——不落渲染＝没披露）：
   - verdict 帧 additive 意图来源键（票内定案键名 `intent_source`，值域
     deterministic｜llm_plan——与 teach T-01 已登记注记对齐；键名以 teach 册登记名为准，
     不一致＝缺陷回 teach 改）：快路恒 deterministic，LLM 生效路恒 llm_plan；
     _wire_verdict（service.py:1680）剥 `_` 前缀逻辑不动，非下划线键自然随行；
   - 血缘卡①口径行 LLM 路来源后缀：lineage_caliber_line（domain.py:1483）行内文字尾缀
     （票内定案文案：「——意图来源：LLM 精解析（经校验）」，仅 LLM 路追加；快路零变化）；
     **五要素键序不动**；
   - 前端一行渲染：web/src/landing/A1.jsx verdict 块（现 850-853 区——【注意】任务书引
     web/src/pages/A1.jsx 有误，实际文件在 web/src/landing/；方案册 A1.jsx:850-853 与
     现位一致）白名单渲染增来源键一行（现只取 chain/confidence/slots 三键）＋
     web/src/landing/A1.test.jsx 断言（渲染含 intent_source；无键时零变化）。
4. 闸 B 检查项落验收（拍板 3/5）：正确率达标（阈值呈 Owner——开放问题 4，Owner 看
   L-03/L-04 数后拍，本票不预设）＋每一问意图来源可见（LLM 路每问 verdict 或血缘卡必见
   来源标注——测试＋实跑各验一道）＋golden 回归绿（L-04 跑批脚本退出码 0）。

先读:
- tickets/phase3/方案-LLM问数演进-20261005.md §2.1（钉入新缝/N7.1 消费/披露行）、§2.2
  （路径 2 兜底）、§2.3 D1/D2/D5、§3 机制 2/10/11/13、§4（B 生效＋披露→闸 B）、§5 拆票
  表第 6 行、§6 开放问题 2/4、§8 意见 2/6
- tickets/phase3/拍板记录-20261005.md 第 2/3/4/5 条
- tickets/phase3/L-01、L-02、L-04 票面（影子件/接线/golden 闸——本票消费面）
- app/domains/chat/domain.py:685-708（ChainContext 全字段——增字段位）、1107（QueryPlan）、
  1483-1493（lineage_caliber_line——血缘①行文消费面）
- app/domains/chat/chains.py:1331-1387（N7.1——【注意】方案册引 1037-1110 为旧行号）、
  1737（_continue_with_retrieval 降级接续）、1581 区（lineage_caliber_line 链内消费）
- app/domains/chat/service.py:831-884（_resume_approval——恢复重推导现状）、404/436
  （resume_preflight/resume）、1680-1682（_wire_verdict）、1291-1342（确定性信号——旧行
  号 1295-1301 已漂移）
- app/domains/chat/store.py:86-120（ChatRunRow——verdict/pending_interrupt jsonb 先例，
  plan_pinned 落位）、app/infra/config.py:43（Settings——生效开关落位）
- app/domains/gateway/service.py:87（complete——B6 出口，本票生效路调用面）
- web/src/landing/A1.jsx:848-855（verdict 渲染三键现状）、web/src/landing/A1.test.jsx
  （前端测试惯例）

验收:
- [ ] 生效开关默认 false＝现网行为零变化（既有 pytest 全绿无断言改动）；开→关往返回归
  测试在案（回退纪律可演练）
- [ ] 兜底路 TDD：validator 拒→有澄清额度走澄清帧（有界一次）/无额度走降级解释链，两支
  帧形状与现状合同零差异（断言帧序列）
- [ ] pinned_plan TDD：ChainContext 新字段缺省 None 零影响；N7.1 有钉→复验通过直用/
  复验拒走兜底；快路不钉；plan_pinned 列迁移 up/down 可逆、QueryPlan dict 两向重建等值
- [ ] 恢复重放 TDD：审批挂起→恢复取持久化 plan→重跑 validator（篡改持久化载荷的拒例
  在案——不盲信）；全程零 LLM 重调（替身断言）
- [ ] 披露 TDD：LLM 路 verdict 带 intent_source=llm_plan、快路 deterministic；血缘①
  LLM 路尾缀在案且五要素键序断言不变；前端渲染测试绿（`cd web && npx vitest run`）
- [ ] golden 回归绿：L-04 跑批脚本对 golden 全量退出码 0（附实跑输出）；每一问意图来源
  可见抽查记录在回报
- [ ] `cd web && npx vitest run` 全绿（回报附输出原文）
- [ ] `uv run ruff check app tests migrations tools && uv run mypy app && uv run pytest -q && uv run lint-imports && uv run python tools/contract_coverage.py check && uv run python tools/debt_markers.py check` 全绿（回报附输出原文含通过数数字）

回报: 写 tickets/phase3/reports/L-05.收尾.md——产物清单（文件＋迁移号＋commit SHA）/
闸门实跑输出原文（pytest＋vitest 两段）/闸 B 检查项逐条核验记录（正确率数字＋Owner 拍板
阈值引文）/偏差逐条（现象→原因→处置）/疑点列 L0 不动手。git 纪律：master 拉
`l-plan/L-05-effective-path`（前置：影子批已合入）；只 add 本票明确改动文件，提交前
git status 核对暂存区仅含本票文件，严禁 git add -A/git add .。

框架红线: 零新依赖；LLM 调用面只许经 gateway.complete（B6——L-02 接线复用，本票零新
调用面）；不改 19 类事件帧（intent_source＝帧内 additive 键，teach 册已登记）、17 链
枚举、血缘五要素键序（①口径行只加行内尾缀）；SQL 唯一出口＝装配器；F7 幂等前提不破
——恢复重放全程确定性（重跑 validator，不重调模型）。

边界红线: 只许触碰 app/domains/chat/（domain.py/chains.py/service.py/store.py）、
migrations/versions/（仅本票新迁移一文件）、app/infra/config.py（仅 additive 一生效
开关键）、web/src/landing/A1.jsx＋A1.test.jsx、tests/；不许 import retrieval/semantics/
faq/kb/gateway 内部实现（零共享库纪律）；不动 app/api/（SSE 下发面既有）。

〔来源：方案-LLM问数演进-20261005 §2.1/2.2/2.3(D1/D2/D5)/3(机制11/13)/4(B→闸B)/
5(第6行)/6(开放问题2/4)/8(意见2/6)；拍板记录-20261005 第 2/3/4/5 条；
票册总表-统一开票-20261007 乙节〕
