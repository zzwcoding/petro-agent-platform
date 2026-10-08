# DEP-01 审查拍（T1 关票前审查——只产发现清单，零修复动作）

任务：对 DEP-01 双仓产物做独立关票前审查——主仓 `fix/dep-01-deploy-prep` 单 commit `2b03fc0`（9 文件 +717/−2：0018 迁移＋链位手术＋runbook＋原型闸＋冒烟常驻＋CI 步骤）＋data-plane `6a38f56`（worker gc 函数默认不注册，2 文件 +238）〔来源：票面 DEP-01 审查节点节"T1——重点专查 0018 与 ORM 一致性、原型闸误报面"〕。

审查七节：

1. **diff 双仓嗅探**：主仓 9 文件逐块定性（0018/0011 链位改/runbook/guard/manifest/冒烟/CI/config 测试）；data-plane 2 文件（gc＋测试）零夹带；业务域 app/ 零触碰复核。
2. **0018 vs ORM 逐列对照（主查）**：迁移 DDL 与 `app/domains/gateway/store.py` ORM 声明逐表逐列（表名/列名/类型/PK/索引/CHECK）；链位手术复核——0010→0018→0011 的 down_revision 指向正确（0011 原指 0010 改指 0018），纯 Alembic 全新库全链不再断；既有库幂等（ensure 并存）。
3. **原型闸误报面（票面点名专查）**：guard 对当前态 GREEN 的判据（manifest 首版 vs W-LAND 还原后原型树）；合法场景误报面盘点——未来合法同步批（teach 定稿→快照同步）会 RED，manifest 再生流程是否在 runbook/工具用法中写明；guard 对非同步页（landing/ 流转）零误伤。
4. **双树冒烟常驻化**：7 例改造为常驻 vitest 的断言强度（stub fetch 零调用断言/真端点 URL 断言）；对 vitest 套整体的影响（266→279 增量合理）。
5. **口令机制测试**：`${VAR:-默认}` 覆盖/回落两半边断言独立复跑；runbook 环境变量清单与 config 实际键逐一对照（无漏键/无幻键）。
6. **MinIO gc 安全性**：gc_orphans 只列不删（delete 面不存在的替身机证）；默认不注册作业机判；人工入口用法与误删风险面（列出的对象判定口径——超期定义）。

先读：dev 回报 `dispatch/results/DEP-01.dev.md`；DP-04.dev.md（gateway 缺口发现原文）；W-LAND.rev.md（原型还原 blob-hash——guard manifest 判据）；`git show 2b03fc0`＋data-plane `git show 6a38f56`；`app/domains/gateway/store.py` ORM。

框架红线：无。

边界红线：全程只读＋独立复跑（alembic 双向用临时库；guard 演示篡改复原；两仓零写入），零修复动作；全新实例。

验收：以下全达才算过。
1. 七节结论逐项（通过/发现）；0018 vs ORM 逐表对照表在回报。
2. 发现清单每条带 file:line＋影响评级＋建议处置（含 0018 撞号 S-01 的合并序建议）。
3. 独立复跑数字（alembic 双向/两仓闸门）附回报。
4. "零修复动作已执行"声明在末节。

回报：按 PROTOCOL 写 `dispatch/results/DEP-01.rev.md`。
