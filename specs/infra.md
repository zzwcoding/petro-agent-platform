# V2 infra 复制层

状态: 已定稿
来源: specs/modules.md `infra` 卡、ADR-0002/0003、V1 app/infra 现状

## 目标

从 V1 复制运行基础设施到 `appv2/infra/`，**带纪律不带业务语义**：
B6 单出口、只读 DB、时钟、审计、配置装载原样；V1 业务域语义（装配器/链/服务）一律不进复制层。

## 不做什么

不复制 V1 domains 任何业务逻辑（chat/kb/semantics 的 service/domain 不搬）；
不新造配置键（沿用 config/database.yaml 与环境变量机制）；不改 V1 文件。

## 触及的模块

| 模块 | 改动类型 | 说明 |
|---|---|---|
| infra | 新增 | 复制＋清理后的基础设施层 |

## 接口定义

与 V1 `app/infra` 同形（签名一致，模块路径 `appv2.infra.*`）：
`config.load_*`（database.yaml 装载含 chat 运行开关）、`db.session(spec)`（primary/midplatform 双路由只读）、
`llm_client.LlmClient.complete/embeddings`、`clock.now`、`security.resolve_actor`、`security.audit`。

### 复制清单（带/不带）

| 带 | 不带 |
|---|---|
| config 装载（database.yaml/chat 开关） | 任何 domains 导入 |
| db 会话/DatabaseSpec/driver registry | 业务表 ORM（kb_*/sem_*/chat_* 模型不搬——各引擎自建只读视图） |
| llm_client（litellm 单点＋空闲超时）＋gateway 域（别名路由/重试/预算/动态闸） | chat 域的 caller 常量与业务 prompt |
| clock / ids / 审计写口 | faq/kb/graph 的业务调用点 |

## 行为约定

1. B6 纪律：appv2 内 litellm 唯一出现点＝`appv2/infra/llm_client.py`；调用全走 gateway.complete 带 caller 归因（ADR-0002 红线②的落点）。
2. midplatform 路由只读（readonly 守卫＋账号级 SELECT-only 语义同 V1）。
3. 审计唯一写口 security.audit（INV-5）；appv2 新 action 前缀 `agent_v2.*`。
4. 新增 run 态表（agent_v2_run/agent_v2_step）由 runtime 建，DDL 走独立迁移文件，前缀与 V1 表隔离。

## 验收测试

| 验收标准 | 对应测试 |
|---|---|
| 全仓扫描：litellm 只出现在 appv2/infra/llm_client.py | `tests/infra/test_v2_infra.py::llm_single_exit` |
| 复制层无任何 app/（V1）import | `tests/infra/test_v2_infra.py::no_v1_dependency` |
| gateway 动态闸＋预算熔断行为与 V1 一致（并发上限生效） | `tests/infra/test_v2_infra.py::gateway_gate` |
| midplatform 会话只读：写操作抛守卫异常（INV-2） | `tests/infra/test_v2_infra.py::readonly_guard` |
| 审计写口唯一：appv2 其他模块直写 audit 表被禁（代码扫描） | `tests/infra/test_v2_infra.py::audit_single_writer` |

## 依赖与风险

- 依赖：无（最底层）；config/database.yaml 共享读取（V1 文件，只读不改）。
- 风险：复制变克隆——"不带"清单逐条过 import 扫描闸；gateway 域复制时剥离 V1 业务 caller 需小心引用残留。
