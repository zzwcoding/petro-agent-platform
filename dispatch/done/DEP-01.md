# DEP-01 开发票：部署准备批——上线前五件（runbook/迁移补建/口令机制/原型保护闸/清理策略）

任务：部署前必办五件收口〔来源：阶段 2 移交清单＋W-LAND.rev F5＋DP-04/0016 全新库实跑发现；单窗口 L0 裁决 2026-10-05〕：

1. **三账号建号 runbook（纯文档）**：`docs/deploy/db-accounts-runbook.md`——三账号（midplatform 只读/agg_writer 限写三表/quality_writer 限写＋rule 只读）在**生产实例**的逐步建号流程（模板位置/`<SET_ME>` 替换/口令密管注入/GRANT 验证三分法）；环境变量清单表（DATABASE_URL/AGG_DATABASE_URL/QUALITY_DATABASE_URL/MIDPLATFORM_PG_*/MINIO_*——每个变量：用途/示例/缺省行为）；dev 容器已执行的授权动作与生产差异说明。
2. **gateway 表迁移补建（0018）**：gateway 表族（ORM ensure 建表、不在迁移链——0016 全新库实跑发现的缺口）补 Alembic `0018_gateway_tables.py`——表结构照 ORM 声明；**双向验证**：全新库全链 0001→0018 upgrade head 成功＋downgrade 逐步干净；既有库 upgrade 幂等（ensure 与迁移并存现状不破坏）；迁移头注释登记来源（0011 docstring 双轨前提的收敛）。
3. **口令环境注入机制验证＋登记**：`config/database.yaml` 的 `${VAR:-默认}` 机制补测试（tests/infra/test_config.py——环境量在位时覆盖默认、缺省回落默认）；runbook 增「生产口令经环境注入，禁止默认口令上生产」一节。
4. **原型树保护闸＋双树冒烟常驻化**：①`tools/prototype_guard.py`——对原型树关键文件（pages/E2·A2·B4 等同步页）计算 hash 与清单（`web/prototype-manifest.json`，由本票生成首版）比对，不一致退出码非零并打印漂移文件；②冒烟常驻化——W-LAND 的双树渲染冒烟 7 例改造为常驻 vitest 测试（stub fetch 断言：落地三页真端点消费×原型三页零 api 调用）进 web 测试套；③CI 接线——前端 job 增 guard 步骤（照 P0-06 CI 前端 job 现状）。
5. **MinIO 清理策略（安全优先）**：策略文档入 runbook（保留期建议：隔离/拒收批文件保留 ≥90 天，清理须先列后删两步制）＋worker 增 `gc_orphans` 函数（**默认不注册作业**；列出超期对象清单仅日志，不删除——真删除策略与开关归 Owner 部署批拍板）；测试：gc 列表逻辑（fixture 桶）。

先读：DP-04.dev.md（0016 全新库实跑与 gateway 缺口发现）；DP-05/DP-06 交付；W-LAND.dev.md＋rev（冒烟 7 例与原型树教训）；P0-06 CI 前端 job 现状；`app/domains/gateway/`（gateway 表 ORM 真源）；`config/database.yaml`＋`tests/infra/test_config.py`。

框架红线：无点名框架（APScheduler 既有）。

边界红线：主仓动 `migrations/`（0018）＋`tools/prototype_guard.py`＋`docs/deploy/`＋`web/prototype-manifest.json`＋`web/`（冒烟测试文件）＋CI 配置（原型闸步骤）＋`tests/infra/test_config.py`；data-plane 仓动 worker（gc 函数，默认不注册）＋runbook 引用；**不碰 app/ 业务域一行**；分支主仓 `fix/dep-01-deploy-prep`、data-plane 单提交；禁止 `git add -A/.`，显式路径 add；Owner 私产不碰。

验收：以下全达才算过。
1. 0018 双向实跑：全新库 0001→0018 upgrade head 成功＋downgrade 干净；既有库幂等——输出附回报。
2. 原型闸：对本仓当前态跑出 GREEN（原型树与 3c2d63a/04f9606 同步点一致——W-LAND 已还原）；人为篡改一文件→RED→复原（演示输出附回报）。
3. 冒烟常驻：vitest 套含双树冒烟例并全绿。
4. runbook 文档在位（三账号＋环境变量表＋口令纪律）；MinIO gc 函数＋策略文档在位（默认不删除）。
5. 两仓提交各一（主仓/数据面）；全量四门禁＋两闸绿（主仓）；data-plane ci.sh 绿。

审查节点：关票前审查拍（T1）——重点专查 0018 与 ORM 一致性、原型闸误报面（合法接线提交会不会误红）。

回报：按 PROTOCOL 写 `dispatch/results/DEP-01.dev.md`（主仓与 data-plane 两 SHA 分列）。
