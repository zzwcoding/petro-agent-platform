# FX-08 收尾回报——rerank 播种 lifespan 接线测试（2026-10-07）

> 修复拍子代理（L2 编码，全新无历史实例）产出。工作树 `/Users/divh/Downloads/petro-wt/de10`，
> 分支 `debt/rerank-env-seeding`（DE-10 完工代码 6719604 上续提交，不拉新分支）。TDD 全闸绿后回报。
> 处置裁决依据：审查 R2 L0 裁决节（R2-02 修复＋R2-06 并入），只修被裁决条目。

---

## 一、验收结论

**达标可合。** R2-02（medium「非法值拒绝启动」未挡在启动路径——main lifespan 接线零测试执行）与
R2-06（low 合法域测试硬编码三档）两条裁决条目全部修复：新增 `TestLifespanWiring` 三例
（monkeypatch.setenv＋`with TestClient(app)` 真穿 `app/main.py` lifespan 播种段），合法域测试改遍历
`RERANK_TIERS` 常量。生产代码零改动（突变验证后 main.py 逐字恢复，`git diff` 零残留），零新依赖。

## 二、lifespan 测试策略定案（票内定案记录）

**播种点位置**：`app/main.py` 的 RERANK_TIER 播种段在 lifespan **偏后段**——
`verify_midplatform_route()`＋十二个 `ensure_*_tables`＋`seed_demo_if_empty`＋六域服务装配之后
（约 ：177-180）。按票面约束「不许为测试改生产代码顺序」，依赖链处理定案＝**其余全照生产代码跑，
只替两处真外部依赖**：

1. **`app.main.load_database_specs` → tmp_path sqlite 规格**（monkeypatch）——config/database.yaml
   真文件指向 localhost PG（5433），测试环境无 PG；sqlite 底座是 DE-10 既有惯例
   （tests/domains/retrieval/conftest.py 同款 DatabaseSpec 形态）。
2. **`ConnectionManager.verify_midplatform_route` → no-op**（monkeypatch 打类方法）——该中台只读
   校验在 sqlite 底座上**恒拒启动**（写探针 `CREATE TEMP TABLE` 在 sqlite 必然成功＝「未被拒」→
   MidplatformRouteError），对 sqlite 无真实语义可保；播种段在其后，替身不影响被测段。

其余链条全真：sqlite 上 `ensure_audit/gateway/outbox/semantics/kb/derivatives/faq/retrieval/chat/
wells/quality_tables`（逐一核过——列类型全带 `with_variant(JSON,"sqlite")`、PG 专属 DDL 全在
`dialect.name == "postgresql"` 守卫内）、`seed_demo_if_empty`（纯 DB 写种子，无 LLM）、各域服务与
`MinioObjectStorage`/`Neo4jGraphStore`/`LlmClient` 构造（全部懒建连，构造零网络）。

**三例断言设计**：

| 例 | 驱动 | 断言 |
| --- | --- | --- |
| ①非法值拒启动 | setenv RERANK_TIER=turbo＋`pytest.raises` 包 `with TestClient(app)` | 进入上下文（触发 lifespan）即抛 `RerankTierEnvError`（match "turbo"） |
| ②合法值落种子 | setenv RERANK_TIER=llm＋`with TestClient(app)` | with 体内 `app.state.retrieval` 装配完成（进入 yield＝启动全链走通）；退出后以独立 ConnectionManager 重开同一 sqlite 文件断言版本轴 `["v1"]`、`config["rerank"]=="llm"`、`via is None`（与首读种子同构——行格式零变化） |
| ③无 env 零变化 | delenv＋caplog（logger "main"） | 启动全程无 RERANK_TIER 日志记录；版本轴零写入（`[]`——现状：首读才种子） |

**收尾泄漏处置（测试内）**：①例 lifespan 中断在 `manager.dispose()` 之前（播种段后无清理路径），
池中 sqlite 连接的 aiosqlite 工作线程在 portal 事件循环关闭后抛未处理异常，被 pytest 线程异常钩子
记为 `PytestUnhandledThreadExceptionWarning`（基线 1 警告 → 带 2 警告）。处置＝该例断言后
`await app.state.db.dispose()` 显式收口（app.state.db 在播种点之前已装配，不触生产代码）；修后
`-W error::pytest.PytestUnhandledThreadExceptionWarning` 全量 957 过，警告回到基线的 1 个。

## 三、红先绿后（突变验证）

修复物是测试缺口（R2-02 原文「实现本身正确，纯测试缺口」），红先绿后以**突变验证**兑现：
临时把 `app/main.py` 播种段改成 `if False and (...)`（模拟接线被删）→
`test_invalid_env_rejects_startup` 与 `test_legal_env_seeds_row_at_startup` **真红**（2 failed），
③零变化例如期保持绿（其职责即钉「无行为」不变量）→ 逐字恢复后 13/13 绿，`git diff app/main.py`
零残留。两正向例确证真穿 lifespan 接线段，非域层单点自证。

**R2-06 修复**：`test_all_contract_tiers_pass` 改 `for tier in RERANK_TIERS`（常量遍历——合同枚举
扩档即自动覆盖），`rerank_seed_config_dict` 断言同扩为逐档；删硬编码三档。

## 四、全量闸输出摘要（原文数字）

| 闸 | 结果 |
| --- | --- |
| `ruff check app tests migrations tools` | All checks passed!（首跑 1 处新导入块排序 I001，`--fix` 后复跑绿） |
| `mypy app` | Success: no issues found in 76 source files |
| `pytest -q` | **957 passed, 83 skipped**, 1 warning in 29.54s（基线 954＋新增 3，零跌） |
| `pytest -q -W error::PytestUnhandledThreadExceptionWarning`（附加核验） | 957 passed, 83 skipped, 1 warning——线程收尾泄漏确认清零 |
| `lint-imports` | Contracts: **5 kept, 0 broken** |
| `tools/contract_coverage.py check` | 合同覆盖率闸绿：**170** 条合同端点双向对账通过 |
| `tools/debt_markers.py check` | 债务标记闸绿：web 源码债务短语全部携可解析 DEBT 标签（盘点 **33** 条） |

## 五、产物清单（git 工作树文件 SHA-256 前 16 位）

| 文件 | SHA-256（前 16 位） | 改动 |
| --- | --- | --- |
| `tests/domains/retrieval/test_rerank_env_seeding.py` | 766ee22a3d6b2e66 | +105/-7（+3 例 TestLifespanWiring＋R2-06 遍历＋docstring 修正） |
| `tickets/phase3/FX-08-rerank播种lifespan测试.md` | （本票勾选版） | 新增（主仓票面复制勾选） |
| `tickets/phase3/reports/FX-08-rerank播种lifespan测试.收尾.md` | （本回报） | 新增 |

**生产代码零改动**：`app/main.py` 突变验证后逐字恢复（diff 空）；其余 app/migrations/tools/deploy
零触碰。**git 纪律**：de10 分支续提交，只 add 上表文件，未 `git add -A`，未合入未 push。

## 六、偏差与疑点

1. **回报文件名**：修复票回报行写「FX-08-rerank播种lifespan测试.收尾.md」，派工指令写「FX-08.收尾.md」
   ——从票面（且对齐 FX-01/FX-06 收尾报告命名惯例带主题词），主窗口对账时请按本名收。
2. **docstring 修正**：原测试文件 docstring「装配接线由该单点保证」的论证被 R2-02 点名为不成立
   （域层单点保证不了接线存在性），已改写为「域层单点＋lifespan 接线级两层」——属被裁决条目的
   直接改正，非超界。
3. **测试底座形态更正一处旧表述**：conftest 的 sqlite 夹具是 tmp_path **文件**库（非内存态），原
   docstring「内存形态存储」表述顺手订正（同段改写内，不另开改动）。
4. **无 env 零变化例对「接线删除」不敏感（突变下仍绿）**：该例职责是钉「env 缺省时启动零行为」
   不变量（防播种段误扩为无条件执行），与①②例正交——三例合起来才完整覆盖裁决要求的三态。
5. **①例的显式 dispose**：测试内资源收尾（app.state.db 在播种点前已装配），非对生产行为的断言
   弱化——拒启动语义（异常上抛、版本轴零残留）照常钉死。
