# V2 存储归档（persistence）

状态: 已定稿
来源: `specs/modules.md` `## persistence` 卡、`docs/runtime-refactor/walk/16-收尾-归档.md`、`walk/裁决表.md` §16、`synth/S5` §三（持久化面）、`recon/J-存储留痕与网关缝.md`、`recon/I1b-执行器后半.md`（三终态与审计事件）、`arch/P4a2-票堆V2-51至55.md`（V2-54 黑匣子／V2-55 防膨胀）、`specs/agent-loop.md` 行为 8、`specs/execution.md`（窗口侧材料条目口径）、`CONTEXT.md`（INV-2）
版式: `docs/spec-format.md`（节标题按该文 §二之二 逐字命名） ｜ 工序: `docs/spec-process.md`

## 目标

一次运行的**落盘与读回真源**：运行记录、检查点、黑匣子（只追加）、审计留痕、大结果原文的引用载体——**业务数据零写入**（INV-2），簿记表是唯一写面。

## 不做什么

| 不做 | 由谁承担 | 锚点 |
|---|---|---|
| 编排逻辑、状态迁移决策、图驱动 | `orchestration` | `specs/agent-loop.md` 行为 8；`specs/modules.md` `## orchestration` |
| **LangGraph 的检查点 saver 实现**（框架类型只许活在编排块内） | `orchestration`（组合本块的框架无关入口） | `specs/modules.md` `## persistence` 卡注；边界闸 **R5b** |
| 状态形状、限额判定、受理载荷定义 | `state` | `specs/state.md` |
| 事件与帧的发射（含黑匣子瘦指针帧） | `transport` | `specs/modules.md` `## transport` |
| 模型调用与调用记账（calllog） | `gateway_adapter`（记账出口在 `infra`） | `specs/modules.md` `## gateway_adapter` |
| 落引用的**决策**（何时落、阈值） | `execution` | `specs/execution.md` 行为 4 |
| 业务数据（油田数据）的任何写入 | **不做**（INV-2 全程只读） | `CONTEXT.md`（INV-2 词条：只读边界——全部工具只读、SQL 只读账号＋白名单 Schema） |
| 用程序替模型做语义判断（本块只存储／读回，零判断） | **不做** | `docs/runtime-refactor/walk/判断归责表.md` |

## 触及的模块

| 模块 | 改动类型 | 说明 |
|---|---|---|
| persistence | 新增 | 本块本体：落盘入口 ＋ 读回入口 ＋ 审计写口 ＋ 引用载体 |
| state | 新增 | `RunState` 形状（`load` 返回；本块只消费） |
| execution | 新增 | 大结果落引用的消费侧（本块提供可寻址载体） |
| orchestration | 新增 | 检查点 saver 实现与三态落库的调用侧（本块只出入口） |

## 接口定义

```python
class RunStore:
    def save(self, record: RunRecord | StepRecord | BlackBox) -> None: ...
    def load(self, run_id: str) -> RunState: ...              # 检查点恢复（跨进程重放）
    def run(self, run_id: str) -> RunRecord | None: ...
    def steps(self, run_id: str) -> list[StepRecord]: ...      # seq 升序
    def scan_recent(self, limit: int) -> list[RunRecord]: ...  # created_at 降序取前 limit（V2-141 列表读口 limit 下推）
    def blackbox(self, run_id: str) -> BlackBox | None: ...
    def put_ref(self, blob: bytes) -> BlobRef: ...             # 大结果原文的引用载体（可寻址 handle）
    def read_ref(self, handle: str) -> bytes: ...
    def ensure_tables(self) -> None: ...                       # 幂等建表

# 检查点三表的框架无关行级读写口（编排块的 LangGraph saver 组合它，不直连表）
def put_checkpoint_rows(rows: Sequence[CheckpointRow | CheckpointBlobRow | CheckpointWriteRow]) -> None: ...
def checkpoint_rows(thread_id: str) -> list[CheckpointRow]: ...
def checkpoint_blobs(thread_id: str, checkpoint_id: str) -> list[CheckpointBlobRow]: ...
def checkpoint_writes(thread_id: str, checkpoint_id: str) -> list[CheckpointWriteRow]: ...
def delete_thread(thread_id: str) -> None: ...

class RunRecord:                     # agent_v2_run 行的投影
    run_id: str
    question: str
    actor: str                       # 行级身份（字符串投影——见 specs/state.md 行为/风险）
    status: str                      # 闭世界＝state 的 RUN_STATUS_KINDS（四值）
    answer: str | None
    error: str | None
    manifest_digest: str | None
    followup_of: str                 # 空串＝链根
    created_at: datetime
    updated_at: datetime
class StepRecord:                    # agent_v2_step 行的投影
    run_id: str
    seq: int
    step: str                        # 闭世界＝state 的 STEP_KINDS（六值）
    status: str                      # 闭世界："ok"｜"failed"｜"refused"
    title: str
    manifest: dict[str, Any] | None
    payload: dict[str, Any] | None   # 原样保真（不裁剪——见行为 8）
    created_at: datetime             # 该记录末次落盘时间（现状列如实投影——recon/J `AgentV2Step`；语义定死＝末次落盘，首写时间不可回溯——见风险 4）
class BlackBox:                      # agent_v2_blackbox 的投影
    run_id: str
    record: dict[str, Any]           # 键白名单闭世界（真源 recon/J 蒸馏白名单）
    created_at: datetime
class BlobRef:                       # 大结果原文的引用载体（可寻址 handle）
    handle: str                      # 不透明标识——**与 execution.MaterialRef.handle 同源同值**（见下）
    bytes: int
    sha256: str
class CheckpointRow:                 # agent_v2_checkpoint 行的投影（框架无关；列名映射：ns↔checkpoint_ns、kind↔type、metadata↔metadata_json——投影改名不换列，真源 recon/J 表事实）
    thread_id: str
    ns: str
    checkpoint_id: str
    parent_checkpoint_id: str | None
    kind: str
    checkpoint: bytes
    metadata: bytes
class CheckpointBlobRow:             # agent_v2_checkpoint_blob 行的投影
    thread_id: str
    ns: str
    channel: str
    version: str
    kind: str
    blob: bytes
class CheckpointWriteRow:            # agent_v2_checkpoint_write 行的投影
    thread_id: str
    ns: str
    checkpoint_id: str
    task_id: str
    idx: int
    channel: str
    kind: str
    blob: bytes
class AuditRecord:                   # 审计留痕（四要素——Owner 裁决见 walk/16 §七 Q-C）
    run_id: str                      # 范围键（四类记录同源可聚合——见行为 9）
    who: str                         # 主体
    scope: str                       # 范围（会话线程／子问题域）
    action: str                      # 意图（闭世界七值，恒 agent_v2.* 前缀）
    authorization: str               # 授权（角色／审批单号；无则 ""）
    facts: str                       # 执行事实（摘要，截断必可见）
    evidence: dict[str, Any]         # 结果与证据（引用／摘要／单号）
def audit(record: AuditRecord) -> None: ...   # 唯一写口＝security.audit（B12）
```

- **闭世界一：`RunRecord.status`** ＝ `state.RUN_STATUS_KINDS`（四值，真源 `specs/state.md`）——**本块不复述取值**。
- **闭世界二：`StepRecord.step`** ＝ `state.STEP_KINDS`（六值，真源 `specs/state.md`）；`StepRecord.status` ＝ `ok`｜`failed`｜`refused`（真源＝`specs/bookkeeping.md` 已定口径——`status` 是显式关键词参，闭世界三值、缺省 `ok`、由调用方如实给）。
- **闭世界三：`AuditRecord.action`** ＝ 七值、恒 `agent_v2.*` 前缀（真源 `recon/J-存储留痕与网关缝.md` R-J-05）。
- **闭世界四：`BlackBox.record` 的键白名单**（真源 `recon/J-存储留痕与网关缝.md` R-J-02／R-J-03）：**新增状态键须显式入列**，未入列键不进黑匣子。
- **`BlobRef.handle` 与 `execution.MaterialRef.handle` 是同一标识（同源同值）**：`execution` 产的是**窗口侧材料条目**（`{handle, summary, row_count}`——已定稿真源 `specs/execution.md`，`answering` 已按它对齐），`persistence` 产的是**载体回执**（把 handle 解析回原文的凭据）。两处键名**统一为 `handle`**、本块**不另起 `ref` 之类的第二个名字**（治「同名类型两套字段」）。断言：`execution` 产出的 `handle` 直接喂给 `read_ref` 能取回原文。
- **检查点三表的行级读写口是本块公开面的一部分**（框架无关）：编排块的 LangGraph saver **组合它、不直连表**（表主人是本块）。断言：saver 路径上出现的写操作全经这五个函数（AST／行为双证）。
- **列表读口的 limit 由端口侧下推**（V2-141）：`RunStore.scan_recent(limit)` 转出端口口 `Tables.scan_recent(limit)`——`created_at` 降序**只读前 `limit` 行**（`MemoryTables` 内存排序后切片），`api` 侧不再全量读＋Python 排序、不自造 SQL。**PG 真件口 `PgTables.scan_recent`（`ORDER BY created_at DESC LIMIT $1`）随 V2-135 同批补**（`persistence/pg_tables.py` 本票未落——**形状契约登记于此，V2-135 落地时须同批补该口，禁静默漏**）；支撑索引＝迁移 `0029` `ix_agent_v2_run_created_at`（`agent_v2_run (created_at DESC)`）。断言：`tests/api/test_v2_runs_list.py::test_list_applies_limit_at_read_port`（含「全量扫描被 monkeypatch 抛错仍绿」的下推反证）。
- **错误契约**：`save` 的 `status`／`step` 越界、归档重复、`run` 不存在、`read_ref` 的 `handle` 不可解析 → **抛错（fail-closed）**，**不静默丢弃、不返回哨兵**；错误码映射归调用方（`api`／`orchestration`）。
- **`load` 的返回面**：`RunState`（真源 `specs/state.md`）；旧版本检查点按 `schema_version` 如实读入（行为 12）。
- **实现载体待定项**：`BlobRef` 的原文存放载体（簿记表／对象存储）**阶段 5 定**；本规格只写**可寻址语义**（行为 10）。
- 真源：`specs/modules.md` `## persistence` 卡（签名以卡为准）。

## 框架与依赖红线

- **LangGraph／LangChain 框架类型零出现**：检查点 saver（`BaseCheckpointSaver` 一族，需框架类型）归 `orchestration`；本块只出**框架无关**的表与读写入口。对应闸：**R5b 契约**（framework 只许在 `appv2.runtimev2.orchestration`）。
- **模型出口零接触**：本块不含模型调用。对应闸：**R7 契约**（不直引 `appv2.infra.llm_client`）。
- **不直引引擎**（`knowledge`／`query`／`retrieval`）。对应闸：**R6 契约**。
- **DB 只经 `infra.db`**，时间只经 `infra.clock`，审计只经 `security.audit`。对应闸：**无专属闸 → 人审**（原因：V1／V2 两侧契约表里没有「DB 会话唯一出口」「时间唯一出口」「审计唯一写口」这三条的面）；**可降维面＝AST 断言**「本块不出现裸 `sqlalchemy` 会话构造、不出现 `datetime.now`、不出现直连 `audit_log` 的写路径」（登记待补）。
- **不引包内其它块**（本块只依赖 `state`；引 `orchestration` 即成环）。对应闸：**无专属闸 → 人审**（原因：R1–R8 里没有「persistence 白名单」一面；可降维面＝AST 断言「本块 import 只出现 `state`／`infra`」）。
- **业务数据零写入**（INV-2）：簿记表前缀 `agent_v2_*` 是唯一写面。对应闸：测试 `::no_business_table_write`。

## 行为约定

1. **落盘的三种语义，逐类定死**（Owner 裁决 `walk/16` §七 Q-B「只追加、不原地改」）：①**运行记录**＝按状态机**更新**（同一 run 一行）；②**步记录**＝**同键幂等**（`(run_id, seq)` 重复落盘不产生第二行、且内容等价才允许覆盖）；③**黑匣子与审计**＝**只追加**（既成行不得改写、不得删除）。断言：三类各按其规则；对黑匣子／审计行做改写或删除的路径**不存在**（AST＋行为双证）。
2. **状态机把守在本块（结构约束，非迁移决策）**：`RunRecord.status` 写入值必须 ∈ `RUN_STATUS_KINDS`（四值）；**`waiting_ask → running` 是唯一合法的「恢复」迁移方向**——这是**结构约束**（现状先例＝`recon/J-存储留痕与网关缝.md` R-J-17「唯一合法转移 waiting_ask→running」），**「该不该迁移」的决策仍在 `orchestration`**（见「不做什么」row 1）。断言：越界取值抛错；`waiting_ask → running` 成功、反向抛错。
3. **恢复可重放**：同一 run 两次 `load` 得**等价** `RunState`；`load` 不得产生副作用（不写盘）。断言：两次 `load` 逐字段相等 ＋ 落盘计数不变。
4. **黑匣子只追加、首写为准**：每个 run 的归档**至多一次**；重复归档**不覆盖**并**如实记账**（幂等跳过 ＋ 机读信号）。**跳过记账的落点**＝该次归档调用的**返回值／错误面**（`save` 对该 run 已有归档 → 抛既定异常「已归档」；调用方据该异常记一条 notice，发帧由 `orchestration` 协调）。断言：二次归档后 `blackbox(run_id)` 内容与首次逐字相同，且「已归档」异常被抛出、调用方一次跳过记账在场。
5. **审计四要素齐备**（四项＝Owner 裁决 `walk/16` §七 Q-C「审计按四要素补齐字段」，枚举同 `walk/裁决表.md` §16-C——**主体／意图／事实／结果**）：每条 `AuditRecord` 必须给出**主体**（`who`；`scope` 是主体的范围细化——会话线程／子问题域，并入本项、不另立要素）／**意图**（`action`；`authorization` 是其授权依据——角色／审批单号，无则空串，并入本项、不另立要素）／**事实**（`facts`）／**结果**（`evidence`）——**缺项判失败**。断言：构造缺 `scope` 或 `evidence` 的记录 → 抛错。
6. **审计 action 闭世界（计数只有一个口径）**：取值 ∈ **七值闭世界**（真源 `recon/J-存储留痕与网关缝.md` R-J-05），恒 `agent_v2.*` 前缀；越界抛错。**计数口径以「action 七值」为唯一真源**——分组说法（谁把它叫成几类事件）**不产生第二个数字**，本规格不写类数。对账：`specs/agent-loop.md` 行为 8 原写「四事件」，那是**现状陈旧口径**（漏 `ban_exempt` 禁用词豁免留痕），**已就地改述为「action 闭世界七值」**（与 `walk/16-收尾-归档.md` 口径一致——该处「六类」是方法粒度分组，同样不再当计数真源）。
7. **业务数据零写入**（INV-2）：本块对业务表零写；所有写入落在 `agent_v2_*` 簿记表。断言：测试注入探针——任何对业务表的写入尝试被判失败；表名清单与簿记前缀一致。
8. **步记录 payload 原样保真**：`payload` **不做裁剪、不做假值归一**（空 `{}` 与「无 payload」是两件事，读回必须可区分）；核验对账等机读字段**必须能被读面机检**（字段真源＝`specs/verification.md` 行为 11 ＋ `arch/P7a-交接包与挂账清单.md` A-P7a-38；本块只负责**原样落盘、原样读回**，不复述字段清单）。断言：落盘再读回 `payload` 逐字段相等，空结构与缺失各归各位（钉 `pin-12` 的**落盘面**）。
9. **`run_id` 全盖章（落盘面）**：run／步／黑匣子／审计四类记录**都携 `run_id`**，读回可按 `run_id` 聚合到同一 run；逐题账集合与落盘记录**等值可对账**——对账数据源＝逐题 `ledger_run_ids` 集合与跑批 jsonl（eval/results 下各题记录）的 `run_id` **集合等值**（真源 `eval/results/Q15-对账报告.md`（:207——逐题 `ledger_run_ids` 与 jsonl `run_id` 集合等值））。断言：按 `run_id` 聚合四类记录无遗漏、无外键错挂（钉 `pin-28` 的**落盘面**）。
10. **引用载体可寻址**：`put_ref(blob)` 返回 `BlobRef`；`read_ref(handle)` 返回**逐字节相同**的原文；`handle` 不可解析 → 抛错。断言：往返等价 ＋ 坏 handle 抛错。载体实现（簿记表／对象存储）阶段 5 定，**语义不随载体变**。
11. **黑匣子键白名单闭世界**：`BlackBox.record` 的键 ⊆ 白名单（真源 `recon/J-存储留痕与网关缝.md` R-J-02）；**新增状态键必须同批入列**（禁"白名单外偷偷进"）。断言：越界键判失败；白名单变更必须同步改该表与测试。
12. **旧检查点／旧黑匣子如实读入**（钉 `pin-30` 的**回放面**）：v1／v2 旧黑匣子／旧检查点**回放**不抛错；旧 run 的对话通道**如实空显**（不得伪造补写）。断言：回放 v1 fixture → 不抛错、对话通道如实空显。（**分工**：状态字段的读入不炸与 `schema_version` 如实由 `specs/state.md` 行为 8 断言；本块只断言**回放读口**这一面。）
13. **截断必可见**：审计 `facts` 摘要与黑匣子转写文本的截断**必须留可见标记**（不得静默截断）——摘要截断长度真源＝`recon/J-存储留痕与网关缝.md` R-J-06（审计）、转写文本截断长度真源＝同文件 R-J-60／R-J-62（单行摘要／各分面截断）。断言：超长输入 → 输出带截断标记且**长度受控**（判据＝真源值：审计 `facts` 摘要 ≤120 字符（R-J-06 `SUMMARY_LIMIT=120`）；黑匣子单行摘要 ≤96 字符、换行替换后按字符数计（R-J-60）；分面截断 title 30／60、digest 80、source 40（R-J-62））。
14. **落盘失败 fail-closed**：写失败上抛、不吞错、不半写（同一记录要么落要么不落）；**不留无声缺口**（红线 `arch/P7a-交接包与挂账清单.md` A-P7a-37）。**发帧的实施口是 `transport`、批次协调归 `orchestration`**（本块只负责把错误如实抛出，不产帧）。断言：注入写失败 → 抛错且无部分行。
15. **本块零判断**：无词表／正则语义判定、无模型调用。断言：AST 扫描本块源码（`no_lexicon_or_regex_in_persistence`／`no_model_call_in_persistence`）。

## 不降级与静默禁令

- **合法降级路径：无**（存储不可用时按行为 14 **fail-closed 上抛**，不产出残缺记录、不静默丢弃）。
- **截断必留可见标记**（行为 13）；**归档跳过必留记账**（行为 4）；**写失败必上抛**（行为 14）——三者都配机读信号与断言。
- **不许自述完成**：完成判定（三态收口）由 `orchestration` 决定，本块只**如实落盘**它给的终态；本块**不判断**运行是否完成。
- **审计不可改写**：既成审计行不得 UPDATE／DELETE（Owner 裁决 `walk/16` §七 Q-C「原始事实不可改写」）——本块不提供任何改写入口。

## 验收测试

| 验收标准 | 对应测试 |
|---|---|
| 三类落盘语义各按其规则（更新／幂等／只追加） | `tests/domains/test_v2_persistence.py::three_write_semantics` |
| 黑匣子与审计行无改写／删除路径（AST＋行为双证） | `tests/domains/test_v2_persistence.py::append_only_no_mutation_path` |
| `status` 取值闭世界；`waiting_ask→running` 唯一合法方向 | `tests/domains/test_v2_persistence.py::status_machine_guarded` |
| 两次 `load` 等价且无副作用 | `tests/domains/test_v2_persistence.py::load_replayable_idempotent` |
| 黑匣子重复归档不覆盖＋跳过记账在场 | `tests/domains/test_v2_persistence.py::blackbox_first_write_wins` |
| 审计四要素缺项判失败 | `tests/domains/test_v2_persistence.py::audit_four_elements_required` |
| 审计 action 七值闭世界＋`agent_v2.` 前缀 | `tests/domains/test_v2_persistence.py::audit_action_closed_world` |
| 业务表零写（探针注入判失败） | `tests/domains/test_v2_persistence.py::no_business_table_write` |
| 步记录 payload 原样保真（空结构与缺失可区分） | `tests/domains/test_v2_persistence.py::step_payload_faithful` |
| 核验对账机读字段可被读面机检（`pin-12` 落盘面） | `tests/domains/test_v2_persistence.py::verify_fields_readable_in_step` |
| `run_id` 全盖章：四类记录可按 run 聚合对账 | `tests/domains/test_v2_persistence.py::run_id_stamped_across_records` |
| 引用载体往返逐字节相同；坏 `handle` 抛错 | `tests/domains/test_v2_persistence.py::material_ref_roundtrip_and_bad_ref` |
| 检查点三表的写操作全经五个行级口（编排块 saver 不直连表） | `tests/domains/test_v2_persistence.py::saver_writes_only_via_port_functions` |
| 黑匣子键白名单闭世界（越界键判失败） | `tests/domains/test_v2_persistence.py::blackbox_keys_closed_world` |
| 旧检查点／旧黑匣子如实读入（对话通道空显） | `tests/domains/test_v2_persistence.py::legacy_read_honest` |
| 截断必带可见标记 | `tests/domains/test_v2_persistence.py::truncation_visible` |
| 写失败 fail-closed：抛错且无部分行、无静默缺口 | `tests/domains/test_v2_persistence.py::write_failure_fail_closed` |
| 本块零判断零模型（AST 扫描） | `tests/domains/test_v2_persistence.py::no_judgement_or_model_in_persistence` |
| 【边界集】空 payload／超长事实／坏 ref／旧版本记录 → 各落对应分支 | `tests/domains/test_v2_persistence.py::boundary_empty_huge_badref_legacy` |
| 【保留集】常规落盘读回与未触发边界时的行为不变 | `tests/domains/test_v2_persistence.py::retention_normal_roundtrip_unchanged` |

> **测试文件归属**：本块验收测试绑**新建** `tests/domains/test_v2_persistence.py`（本块是阶段 2 新划的公共层块 `appv2/runtimev2/persistence/`，与现状 `appv2/runtime/{store,checkpointer,blackbox,audit}.py` 的旧码测试形状不同）；旧码测试本批不改。

## 依赖与风险

- 依赖：`state`（`RunState`／状态与步类型闭世界）｜`infra`（DB 会话／时钟／审计出口）｜`synth/S5` §三 的持久化面口径（该表列**5 盘**——其标题「三条盘」为陈旧标注，本规格只引该节不复述盘数）｜`recon/J` 的黑匣子与审计常量真源。
- 风险与对策（每条带检测手段）：
  1. **框架类型越界进本块**（检查点 saver 需要 `langgraph.checkpoint.base` 一族）→ 对策＝saver 实现归 `orchestration`，本块只出框架无关入口（卡级澄清已记流水）。检测＝**R5b 契约** ＋ `::no_model_call_in_persistence` 同族 AST 面（人审补）。
  2. **黑匣子语义从 upsert 改「只追加」**（现状 `merge` 覆盖，Owner 裁决改追加）→ 检测＝`::blackbox_first_write_wins`；历史行处理＝**不回溯改写**（旧行照旧可读，登记为迁移事实）。
  3. **步记录 payload 假值归 NULL 造成语义丢失**（现状 `or None`）→ 对策＝行为 8 保真（空结构与缺失可区分）。检测＝`::step_payload_faithful`。
  4. **`created_at` 语义漂移**（现状步记录时间戳＝**末次投影时间**，首次落库时间不可回溯）→ 对策＝列语义在规格内定死为「该记录末次落盘时间」；若要首写时间，须新增列（**登记为阶段 5 可选项**）。本批已按此对策在 `StepRecord` 投影**补 `created_at` 列**（末次落盘时间——见接口定义）。检测＝人审 ＋ 读面断言。
  5. **长 run 全量读无分页**（现状 `list_steps` 无 limit）→ 对策＝**列表读口的 limit 由端口侧下推**（V2-141：`RunStore.scan_recent(limit)` → `Tables.scan_recent(limit)`，`created_at` 降序只读前 `limit` 行——api 侧不再全量读＋Python 排序；PG 真件口 `PgTables.scan_recent` 随 V2-135 同批补，索引 `ix_agent_v2_run_created_at` 见迁移 0029）；**步记录读口（`steps(run_id)`）仍无 limit**——该面上限归 `api` 侧；检测＝`tests/api/test_v2_runs_list.py::test_list_applies_limit_at_read_port`（下推反证：全量扫描口被 monkeypatch 抛错仍绿）＋**人审**。
  6. **建表双轨**（幂等建表 vs 迁移脚本）→ 对策＝`ensure_tables()` 幂等、与迁移脚本同形；检测＝**人审**（无机器闸看守「两处同形」，登记）。
  7. **审计字段从四列扩到四要素**（Owner 裁决）→ 对既有“六类方法／七 action 值”的映射口径必须单点；检测＝`::audit_four_elements_required` ＋ `::audit_action_closed_world`。
  8. **D 类疑点残留**（`recon/J` 记录的黑匣子白名单两处不一致、指针对账缺口）：本批**不逐条 triage**（Owner 令「不结旧账」）——重写按行为 11 的**白名单闭世界**收口，历史疑点只作现状证据。
  9. **引用载体的实现载体未定**（簿记表 vs 对象存储）→ 检测＝`::material_ref_roundtrip_and_bad_ref`（语义不随载体变）＋ 阶段 5 定载体时**人审**。
  10. **「DB／时间／审计唯一出口」三条无专属闸**（V1／V2 契约表都没有这三面）→ 检测＝AST 降维断言（登记待补）＋ **人审**。

## 与闸的挂钩表

| 本规格的硬要求 | 挂钩 | 现状 |
|---|---|---|
| 验收测试逐行有标识 ／ 触及模块名已声明 | spec gate（**该闸只校这两项**——十节标题不在其作用面） | 已进 CI |
| 十节标题齐备、逐字、有序 | **人审** | 原因：`tools/check_specs.py` 不校标题名／顺序，仓内无标题闸（登记：可降维为一条标题机检，本批未授权） |
| 真源引用可解析（路径／边界规则编号／被引卡片在册） | 真源引用闸 `tools/ref_resolvable.py` | 已进 CI |
| 框架类型零出现（检查点 saver 归编排块） | 边界闸 **R5b** | 已真跑 |
| 不直引模型出口 | 边界闸 **R7** | 已真跑 |
| 不直引引擎 | 边界闸 **R6** | 已真跑 |
| DB 只经 `infra.db`／时间只经 `infra.clock`／审计只经 `security.audit` | **无专属闸 → 人审**（降维 AST 断言登记待补） | 原因：V1／V2 契约表无这三面；红了没救的闸不做 |
| 不引包内其它块（只依赖 `state`） | **无专属闸 → 人审**（降维 AST 断言：import 白名单） | 原因：R1–R8 无 persistence 的边界条 |
| 业务表零写（INV-2） | 测试 `::no_business_table_write` | 待实现 |
| 黑匣子／审计只追加不改写 | 测试 `::append_only_no_mutation_path` | 待实现 |
| 步记录 payload 保真（核验对账字段可机检） | 钉 **`pin-12`**（P1，**落盘面**——字段面在 `specs/verification.md`）；测试 `::verify_fields_readable_in_step` | 待织网（阶段 5） |
| `run_id` 全盖章、可对账（**落盘面**） | 钉 **`pin-28`**（P1；全盖章面挂 `specs/agent-loop.md`）；测试 `::run_id_stamped_across_records` | 待织网（阶段 5） |
| 旧 run **黑匣子回放**如实（本块**唯一**挂断言的面；检查点**状态字段读入**面挂 `specs/state.md` 行为 8——两处对象不同：一是黑匣子回放、一是状态读入） | 钉 **`pin-30`**（P2）；测试 `::legacy_read_honest` | 待织网（阶段 5） |
| 审计四要素／action 闭世界 | 测试 `::audit_four_elements_required`／`::audit_action_closed_world` | 待实现 |
| 写失败不静默（fail-closed 上抛） | 测试 `::write_failure_fail_closed` | 待实现 |
| 检查点三表写操作只经本块五个行级口（编排块 saver 不直连表） | 测试 `::saver_writes_only_via_port_functions` | 待实现（阶段 5；编排块侧同测） |
| 本块不含行为、不判语义、零模型 | AST 断言 `::no_judgement_or_model_in_persistence` | 待实现（阶段 5） |
| 卡级澄清（框架类型归编排块／「只读 DB」含义／公开面补全） | **人审** | 原因：无「卡与规格一致」机检闸；本批已改卡并记施工流水 |
| 「不做什么」的纯范围排除（不编排／不发射帧／不落业务数据） | **人审** | 接不上闸的原因：纯范围排除没有形状／存在性／退出码判据；能降维的部分（不引框架／不引引擎／不引模型出口）已由边界闸 R5b／R6／R7 覆盖 |
