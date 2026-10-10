# AGENTS.md —— petro-agent-platform 仓协作说明

## 这个仓是什么

Petro-Agent 主平台的**真实实现仓**（后端+前端），与 teach-petro-agent（设计/教学双轨仓）、petro-ontology（本体资产仓）、tpa-data-plane（数据面仓）鼎立。本仓只放实现代码，**合同/架构/ADR 真源在 teach-petro-agent，禁止把合同正文复制进本仓**（引用路径即可）。

## 硬纪律

0. **本体已并入本仓，数据面独立**：`ontology/`＝平台仓普通目录（2026-09-30 子树合并，全部历史随合并提交 8643eb9 可溯，改动直接提交本仓、**提交前跑 `bash ontology/ci.sh` 语义闸**——all-agent 纪律不变）；`data-plane/`＝嵌套独立 git 仓（.gitignore 排除，独立服务独立提交节奏，守其 ADR 链）。**原型快照同步节奏**（2026-10-01 Owner 拍板）：页面讨论与改版只动 teach 原型真源（`teach-petro-agent/prototype/app`），本仓 `web/src/pages|flows|data` 快照**平时不追同步**，阶段开始时一次性同步定稿页面。
1. **合同驱动**：每个端点实现前先引用合同册（`teach-petro-agent/specs/api/<页>.md` 端点号）；字段名/语义/错误码与合同不一致＝缺陷，改合同回设计仓改，不在本仓私改语义。
2. **四层 + B1–B16**：层间依赖单向向下；边界规则进 import-linter，CI 红即不过。新增 import 前先看 pyproject 的 import-linter contracts。
3. **统一出口**：DB 只经 `infra.db`（B3）、LLM/embedding 供应商接触单点 `infra.llm_client`（B6）——complete 面唯一出口 `gateway.complete`、embedding 面唯一出口 `llm_client.embeddings`；审计唯一写口 `security.audit`（B12）、时间一律 `infra.clock`（B14）。
4. **身份桩**：开发期 `X-Dev-User` 头即身份；不许在代码里硬编码用户；OAuth2.0 替换只动 `security.resolve_actor` 实现。
5. **每票一提交**：tickets/ 一票一分支一提交，验收（票面对象全勾）过才合。
6. **子代理一律全新**：派子代理只许新开无历史记录实例，提示词自带完整上下文。
6b. **票面施工基准逐字稿（2026-10-10 固化进 shape 闸）**：票面即交接、交接必须自足——凡合同措辞/替换文本/行为定义/追加段类改动，任务段必须带**逐字稿载体**（引用块/代码块/「原文」引号/票面附节指针）；意图级描述＝逼零上下文子代理自行设计，shape 闸机检 FAIL。验收节的"逐字可查/逐字比对"类判据不触发。子代理对逐字稿**只许照抄，偏离即停报 L0**，不自行裁量。
7. **业务事实零发明**：业务语义疑问查 teach-petro-agent/docs/business-setting.md 与合同册，查不到就问 Owner，不许编造。
8. **合同覆盖率闸与债务标记闸（2026-10-02 端点 3 事故固化）**：两道机器闸绿是交付闸（pytest 看守＋CI 步骤双挂）——①`tools/contract_coverage.py check`：「实现有/清单无」必须为 0；「清单有/实现无」每条必须带 owner 归属（注记在 `config/contract_endpoints.json`：票号/挂账行/阶段标注）；合同册变更后重跑 `export` 并提交（owner 注记自动保留）。②`tools/debt_markers.py check`：web 源码中的债务短语（挂后续批/未接线/随其票/接线预留/产品化批族）必须携 `DEBT(去向)` 标签且去向可解析（票号存在于 tickets/ 或 阶段\d/Owner）——**代码注释与 UI 降级文案不算登记**，只是镜子和指针；app/tests 侧裸短语进 `report` 盘点，阶段收官 triage。**拆票纪律**：涉及某合同册时对该册端点闭世界全量分派，不许留白；**两道工序约定**：拆票后派分派对账子代理（manifest × 票面清单逐条对账，报告清零才开工）；阶段收官派全量对齐子代理（跑两闸＋原型/落地交互对照＋债务 triage，产物落票面验收节）——子代理产物须 L0 核对＋闸复跑才算数。

## 与教学仓的关系

teach-petro-agent 的"不建 app/ scripts/"纪律**不约束本仓**（那是教学轨纪律——ADR-0005）；本仓也不要改教学轨任何文件。
