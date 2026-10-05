# DEP-01 关票结论（单窗口 L0 直收——部署准备批五件，T1 审查通过零高/中发现）

## 门禁结论（合并后 master 实跑）

- ruff：`uv run ruff check app tests migrations tools` → All checks passed!
- mypy：`uv run mypy app` → Success: no issues found in 76 source files
- pytest：`uv run pytest -q` → 881 passed, 83 skipped（master 基线恰 +5＝本票新测试；审查独立复跑同数）
- lint-imports：`uv run lint-imports` → Contracts: 5 kept, 0 broken
- 合同覆盖率闸：169 条；债务标记闸：绿（33 条）
- alembic：合并形态 19 步全链单头 0019＋双向干净（审查独立复跑——0010→0018→0011 链位手术实证修复全新库断链）
- 原型闸：`tools/prototype_guard.py` → GREEN（原型树 4 关键文件与清单一致）

## 产物

- 主仓分支 fix/dep-01-deploy-prep 单提交 `2b03fc0`（rebase 后 FF 合入为 `4c0e0bf`，9 文件 +717/−2）：0018_gateway_tables（链位 0010→0018→0011 修断链）＋docs/deploy/db-accounts-runbook.md（三账号 runbook＋环境变量表＋口令纪律＋MinIO 策略）＋tools/prototype_guard.py＋web/prototype-manifest.json＋双树冒烟常驻测试＋CI guard 步骤＋口令机制测试
- data-plane main 直落 `6a38f56`（2 文件 +238）：worker/gc.py（只列不删＋默认不注册＋人工入口）＋测试 8 条

## T1 审查结论（results/DEP-01.rev.md——七节全过无高/中发现）

0018 vs ORM 三表 31 列逐列对照全符（临时库实跑迁移建与 ensure 建 diff 为空；反证实锤——无补丁 master 全新库恰断于 0011）；原型闸合并后 GREEN＋七段演示（篡改 RED 点名/复原/合法同步批全流程）；冒烟断言强度成立（272+7=279）；口令机制两半边断言实跑；runbook 环境变量表逐键对账无漏键无幻键；gc delete 调用面不存在机证＋默认不注册双机证。

## 收尾裁决

- F1（dev 回报 hermetic skip 数 6 vs 实测 57）→ 采纳勘误登记（回报统计口径，不影响验收实质）
- F2/F3（data-plane 既有测试基建 wart：探针 DSN 硬编码/dim_date 探针不幂等）→ 采纳转票——归属：数据面测试基建小票（不阻本票）
- F4（runbook 建议补 SM4/LLM 密钥注记）→ 采纳登记——归属：部署批执行时随 runbook 补（密管交付物）
- F5/F6（极低登记）→ 采纳登记关闭
- F7 合并序 → 采纳（2b03fc0 直接合入 master——撞号已由 S-01 改号 0019 先合化解，审查实证合并形态全链单头＋全绿）
- 偏差①（0011 链位一行改）→ 追认（票面验收可达的前提手术，审查反证实锤）
- 偏差③（两处真实红非伪造 TDD）→ 追认（如实登记优于摆拍）

## 回写五样

- specs/票册：已回写——tickets/phase2/README.md DEP-01 标已合入
- modules/模块卡：无变更
- CONTEXT.md：无变更
- lessons/：施工日志——dev 回报（全新库断链反证实锤链）
- 架构投影：无变更

## 遗留登记

- 数据面测试基建小票（F2/F3）——归属：数据面仓
- SM4/LLM 密钥注记——归属：部署批执行
- MinIO 真删除策略与开关——归属：Owner 部署批拍板
- 本票无其他新增遗留项

## 提交锚

4c0e0bf（rebase 后 FF 合入，master HEAD）＋data-plane 6a38f56
