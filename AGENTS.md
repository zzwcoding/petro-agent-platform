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
7. **业务事实零发明**：业务语义疑问查 teach-petro-agent/docs/business-setting.md 与合同册，查不到就问 Owner，不许编造。

## 与教学仓的关系

teach-petro-agent 的"不建 app/ scripts/"纪律**不约束本仓**（那是教学轨纪律——ADR-0005）；本仓也不要改教学轨任何文件。
