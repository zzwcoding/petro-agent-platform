# J·现状调研报告
- 锚定：commit e4b75f1（行号以此为准）
- 覆盖：store.py + checkpointer.py + blackbox.py + audit.py（全文件）
- 锚点核验：`git diff e4b75f1 HEAD -- appv2/runtime/{store,checkpointer,blackbox,audit}.py` 为空——四文件在 HEAD(085b294) 与锚定 commit 逐字节同（行号两处一致）。
- def/class 清单：47 项逐一全列（含文件与行号区间），无省略。

**store.py（12 函数/方法 + 7 类）**

| 符号 | 行区间 |
|---|---|
| `AgentV2Run`（class） | L37-L55 |
| `AgentV2Step`（class） | L58-L71 |
| `AgentV2Blackbox`（class） | L74-L81 |
| `AgentV2Checkpoint`（class） | L84-L98 |
| `AgentV2CheckpointBlob`（class） | L101-L111 |
| `AgentV2CheckpointWrite`（class） | L114-L126 |
| `RunStore`（class） | L129-L262 |
| `RunStore.__init__` | L132-L133 |
| `RunStore.create_run` | L135-L150 |
| `RunStore.get_run` | L152-L154 |
| `RunStore.list_runs` | L156-L164 |
| `RunStore.finish_run` | L166-L187 |
| `RunStore.mark_running` | L189-L206 |
| `RunStore.put_steps` | L208-L225 |
| `RunStore.list_steps` | L227-L240 |
| `RunStore.put_blackbox` | L242-L248 |
| `RunStore.get_blackbox` | L250-L253 |
| `RunStore.count_checkpoints` | L255-L262 |
| `ensure_agent_v2_tables`（模块级函数） | L265-L277 |

**checkpointer.py（10 函数/方法 + 1 类）**

| 符号 | 行区间 |
|---|---|
| `PgCheckpointer`（class） | L36-L332 |
| `PgCheckpointer.__init__` | L39-L41 |
| `PgCheckpointer.aget_tuple` | L45-L99 |
| `PgCheckpointer.alist` | L101-L161 |
| `PgCheckpointer.aput` | L165-L214 |
| `PgCheckpointer.aput_writes` | L216-L246 |
| `PgCheckpointer.adelete_thread` | L248-L261 |
| `PgCheckpointer._loads` | L265-L266 |
| `PgCheckpointer._latest_or_by_id` | L268-L291 |
| `PgCheckpointer._load_blobs` | L293-L308 |
| `PgCheckpointer._upsert_blob` | L310-L332 |

**blackbox.py（6 函数 + 0 类）**

| 符号 | 行区间 |
|---|---|
| `distill` | L78-L105 |
| `pointer` | L108-L133 |
| `render_snapshots` | L136-L146 |
| `_plain` | L152-L160 |
| `_head` | L163-L165 |
| `_render_channel` | L168-L227 |

**audit.py（10 函数/方法 + 1 类 + 8 模块级常量）**

| 符号 | 行区间 |
|---|---|
| `summarize` | L49-L54 |
| `who_of` | L57-L59 |
| `RunAuditor`（class） | L62-L152 |
| `RunAuditor.__init__` | L69-L74 |
| `RunAuditor.ensure_ready` | L76-L81 |
| `RunAuditor.run_created` | L83-L91 |
| `RunAuditor.run_completed` | L93-L103 |
| `RunAuditor.run_failed` | L105-L113 |
| `RunAuditor.refused` | L115-L123 |
| `RunAuditor.ban_exempt` | L125-L138 |
| `RunAuditor.extable_decided` | L140-L152 |

> 清单差集说明：任务描述提到的 `get_next_version` 在本仓四文件内未定义——`PgCheckpointer` 继承 `BaseCheckpointSaver.get_next_version`（.venv 内 langgraph/checkpoint/base/__init__.py:692）；`serde` 同理继承（base:216）。

---

## 模块级常量与类事实

### `_TERMINABLE`（store.py L34）
- 规则条目：
  - R-J-01 终态白名单＝{waiting_ask, completed, failed} 三值 frozenset，仅 `finish_run` 消费。
- 疑点：无。

### `_DISTILL_KEYS`（blackbox.py L21-L42）
- 规则条目：
  - R-J-02 蒸馏白名单＝20 键 tuple，顺序即记录键插入顺序：messages/dialogue/process_notes/steps/observations/notices/question_group/precondition_verdicts/resume_choices/answer/draft/verdict/rounds/discover_used/budget_hit/pending_ask/task_type/window_miss_marks/chain_switch_marks/decision_error。
  - R-J-03 白名单闭世界——新增状态键须显式入列（注释 L19 声明），未入列键不进黑匣子。
- 疑点：
  - D-J-01 模块 docstring L8-10 称排除键含 `pending_*` 内部机械态，而白名单 L38 含 `pending_ask`——注释与清单不一致。
  - D-J-02 docstring 写「排除键（体积与噪声面）：ledger_dump/manifests/executed_payloads/pending_*」，代码无任何显式排除逻辑——排除实际由「白名单不含」实现，两条表述不同形。

### `CURATED_CHANNELS`（blackbox.py L46-L75）
- 规则条目：
  - R-J-04 回放曲面通道白名单＝26 元素 frozenset；与 `_DISTILL_KEYS` 的关系＝超集（20 键全含，另加 question/understanding/tool_matches/subtask_results/error/status 六通道）。
- 疑点：
  - D-J-03 两白名单的超集关系代码内无注记；消费方 tools/run_replay.py:44-46 用 `key in CURATED_CHANNELS` 过滤快照通道，蒸馏白名单与回放白名单的同步义务无闸看守（仅注释 L44 一句「蒸馏同族语义＋快照层超集」）。

### `ACTION_*` 常量（audit.py L35-L43）与 `SUMMARY_LIMIT`（L46）
- 规则条目：
  - R-J-05 action 闭世界七值：agent_v2.run_created / run_completed / run_failed / refused / extable_approved / extable_rejected / ban_exempt，恒 `agent_v2.*` 前缀（与 V1 命名空间隔离）。
  - R-J-06 SUMMARY_LIMIT=120——审计 content 摘要截断缺省长度。
- 疑点：
  - D-J-04 L33 注释写「action 闭世界（四事件六值）」，实际常量 7 个（`ACTION_BAN_EXEMPT` L43 为 V2-52 后补）——注释未随常量更新；模块 docstring L3 写「四事件闭世界」并列五类（含 N1 豁免）。

### 类与表事实（ORM 定义，无函数体）
- `AgentV2Run`（L37-55）＝表 agent_v2_run：PK run_id(String32)；question Text；actor String128 default ""；status String16 default "running"；answer/error Text nullable；manifest_digest String64 nullable；followup_of String32 default "" server_default ""（空串＝链根，L40-42 注记）；created_at default=now；updated_at default=now onupdate=now。created_at 无索引。
- `AgentV2Step`（L58-71）＝表 agent_v2_step：PK id(String64，形 "〈run_id〉:〈seq〉")；run_id String32 index=True；seq Integer；step_type String16；status String16 default "ok"；title Text default ""；manifest JSON nullable；payload JSON nullable；created_at default=now。
- `AgentV2Blackbox`（L74-81）＝表 agent_v2_blackbox：PK run_id(String32)；payload JSON；created_at default=now。
- `AgentV2Checkpoint`（L84-98）＝表 agent_v2_checkpoint：PK (thread_id, checkpoint_ns, checkpoint_id)；parent_checkpoint_id String64 nullable；type String16；checkpoint bytes；metadata_json bytes（列名沿官方 saver 命名的工程债注记 L95-97）。
- `AgentV2CheckpointBlob`（L101-111）＝表 agent_v2_checkpoint_blob：PK (thread_id, checkpoint_ns, channel(String128), version(String64))；type String16；blob bytes。
- `AgentV2CheckpointWrite`（L114-126）＝表 agent_v2_checkpoint_write：PK (thread_id, checkpoint_ns, checkpoint_id, task_id(String64), idx(Integer))；channel String128；type String16；blob bytes。
- 类间无 FK 约束（六表相互独立主键）。
- `PgCheckpointer`（L36）继承 `BaseCheckpointSaver[str]`；`RunAuditor`（L62）普通类无基类。

---

### `RunStore.__init__`（store.py L132-L133）｜保存 ConnectionManager 引用
- 消费：db（ConnectionManager）。
- 调用：无。
- 分支表（穷尽）：无（直线赋值）。
- 副作用：无。
- 返回：None（构造器）。
- 规则条目：
  - R-J-07 仅存 `self._db` 引用——不建连接、不校验、不建表。
- 耦合：appv2.infra.db.ConnectionManager（后续方法经其 session()）。
- 疑点：无。

### `RunStore.create_run`（store.py L135-L150）｜新建 run 行落 running
- 消费：run_id/question/actor（均 keyword-only 必填），followup_of 缺省 ""。
- 调用：`AgentV2Run(...)`；`self._db.session()`（appv2/infra/db.py:249）；session.add / flush。
- 分支表（穷尽）：
  1. 恒（无分支）→ 构造行 status 硬编码 "running" → add＋flush（INSERT）→ session 退出 commit（异常 rollback）。
- 副作用：持久化写 `agent_v2_run`（INSERT 一行）；emit 无。
- 返回：`AgentV2Run` 行对象（flush 后；会话关闭后属性可用，依赖 db.py:198 的 expire_on_commit=False）。
- 规则条目：
  - R-J-08 status 初值恒 "running"，方法内无入参可改；followup_of 原样入列（空串＝链根）。
  - R-J-09 run_id 冲突不预查——由 PK 在 flush 时抛错（无重复受理防护）。
- 耦合：appv2.infra.db.ConnectionManager.session；AgentV2Run。
- 疑点：
  - D-J-05 返回值在会话关闭后被调用方继续读属性（executor.py:187），代码注释未记「依赖 expire_on_commit=False」这一约定——该设置本文件不可见。

### `RunStore.get_run`（store.py L152-L154）｜按 run_id 取行
- 消费：run_id。
- 调用：`session.get(AgentV2Run, run_id)`。
- 分支表（穷尽）：
  1. 行存在 → 返回行 → 调用方（executor.py:211/280、api/chat.py:301 等）消费。
  2. 行不存在 → 返回 None。
- 副作用：无（只读）。
- 返回：`AgentV2Run | None`。
- 规则条目：
  - R-J-10 主键直取，无状态过滤——failed/completed 行同样可读。
- 耦合：appv2.infra.db.ConnectionManager.session；AgentV2Run。
- 疑点：无。

### `RunStore.list_runs`（store.py L156-L164）｜最近任务列表读口
- 消费：limit 缺省 20。
- 调用：`select(AgentV2Run).order_by(created_at.desc()).limit(limit)`；session.execute。
- 分支表（穷尽）：
  1. 恒（无分支）→ 无过滤全表按 created_at 降序取前 limit 行 → 返回 list。
- 副作用：无。
- 返回：`list[AgentV2Run]`。
- 规则条目：
  - R-J-11 排序键 created_at 降序；无 actor/status/followup_of 过滤（返回全部状态、全部用户的最近行）。
  - R-J-12 limit 原样进 SQL，无上下界钳制（调用方 api/chat.py:162 自行钳 1..100）。
- 耦合：sqlalchemy.select；AgentV2Run；ConnectionManager.session。
- 疑点：
  - D-J-06 created_at 列无索引（L54 定义），排序+截断在全表上做——行量增长后的性能面代码内无注记。
  - D-J-07 列表含 followup_of 非空行（追问轮）与链根混杂，分组呈现责任在调用方（docstring L40-42 只说明字段语义）——本方法不做链聚合。

### `RunStore.finish_run`（store.py L166-L187）｜终态/挂起态收口（状态机把守）
- 消费：run_id、status（keyword-only 必填），answer/error/manifest_digest（可选，缺省 None）。
- 调用：`_TERMINABLE` 校验；`session.get(AgentV2Run, run_id)`；`infra.clock.now()`；row 字段赋值；flush。
- 分支表（穷尽）：
  1. status 不在 {waiting_ask, completed, failed} → raise ValueError（消息含 status repr）→ 不触库。
  2. status 合法、行不存在 → raise ValueError("run 不存在：…")。
  3. status 合法、行存在 → status/answer/error/manifest_digest 四列整体覆写（显式 None 也写 None）＋updated_at=now → flush（UPDATE）。
  4. session 退出 → commit；异常 → rollback＋异常上抛。
- 副作用：持久化写 `agent_v2_run`（UPDATE）；emit 无。
- 返回：None。
- 规则条目：
  - R-J-13 目标 status 三值闭世界，越界拒写（写前校验）。
  - R-J-14 不校验当前状态：running→completed、completed→failed、failed→completed 均接受（仅 `mark_running` 有前置状态校验）。
  - R-J-15 answer/error/manifest_digest 无条件覆写——waiting_ask 挂起收口会把三列清为传入值（executor.py:431 只传 status，故 answer/error/manifest_digest 写 None）。
  - R-J-16 updated_at 显式写 now（与列 onupdate 双保险）。
- 耦合：_TERMINABLE；appv2.infra.clock.now；ConnectionManager.session。
- 疑点：
  - D-J-08 无当前状态前置校验（如 completed 行可再被 failed 覆写）——状态机守卫分散在 mark_running 与调用方，本方法内无注记。
  - D-J-09 waiting_ask 收口不携 manifest_digest（指纹仅终态路径 executor.py:454-459 落）——挂起段指纹不落库是事实，代码无说明。

### `RunStore.mark_running`（store.py L189-L206）｜挂起恢复受理段回写 running
- 消费：run_id。
- 调用：`session.get`；row 赋值；`now()`；flush。
- 分支表（穷尽）：
  1. 行不存在 → ValueError("run 不存在：…")。
  2. row.status != "waiting_ask" → ValueError（消息"仅 waiting_ask→running"＋状态 repr）。
  3. 行存在且 waiting_ask → status="running"、updated_at=now → flush（UPDATE）。
- 副作用：持久化写 `agent_v2_run`（UPDATE 两列）；emit 无。
- 返回：None。
- 规则条目：
  - R-J-17 唯一合法转移 waiting_ask→running；running→running（重复调用）也拒。
  - R-J-18 调用时点＝executor.execute 在 spawn 前（docstring L192-194）。
- 耦合：appv2.infra.clock.now；ConnectionManager.session。
- 疑点：
  - D-J-10 running 一态兼「受理后执行中」与「挂起恢复执行中」；若 spawn 前进程死亡，行停留 running 且代码内无恢复扫描/超时机制（本文件内无可达注记，不判）。

### `RunStore.put_steps`（store.py L208-L225）｜步记录整体 upsert（重投影）
- 消费：run_id；steps: list[dict]（逐条须含 'seq'、'step' 键）。
- 调用：`session.get(AgentV2Step, f"{run_id}:{seq}")`；构造 AgentV2Step；session.add；`now()`；flush。
- 分支表（穷尽）：
  1. steps 为 falsy（空 list/None）→ 直接 return，不建会话。
  2. 逐条：行不存在 → 新建 id=f"{run_id}:{record['seq']}"、run_id=run_id → add。
  3. 逐条：行存在 → 复用对象（upsert UPDATE）。
  4. 逐条取 status：缺 "status" 键 → "ok"；title 缺 → ""；manifest 缺 → None 原样写；payload 取 `record.get("payload") or None`（空 dict/空 list/0 均转 None）。
  5. record 缺 'seq' 或 'step' 键 → KeyError 上抛（无兜底）；seq 非数字 → int() 抛错。
  6. 全程同一 session；退出 commit，异常 rollback。
- 副作用：持久化写 `agent_v2_step`（INSERT/UPDATE）；emit 无。
- 返回：None。
- 规则条目：
  - R-J-19 幂等 upsert——resume 续跑后整体重投影同一批步（docstring L209）。
  - R-J-20 行 id 形 "run_id:seq"（与 PK 定义一致）。
  - R-J-21 created_at 每条每次写 `now()`——非首次创建时间，而是末次投影时间。
  - R-J-22 payload 假值归一为 NULL（`or None`）。
  - R-J-23 无删除路径——steps 列表缩短（重投影丢步）时旧行留存。
- 耦合：AgentV2Step；infra.clock.now；ConnectionManager.session。
- 疑点：
  - D-J-11 created_at 语义＝末次投影时间，首次落库时间不可回溯（无独立列）。
  - D-J-12 payload 空结构→NULL：读面无法区分「从未有 payload」与「payload 为空 dict/list」。
  - D-J-13 旧步行不清理（重投影只增不减）——调用方 executor.py:429 传的列表若随 resume 变化，库内可能出现本次未投影响应行；代码无注记。

### `RunStore.list_steps`（store.py L227-L240）｜按 seq 升序读该 run 全步
- 消费：run_id。
- 调用：`select(AgentV2Step).where(run_id==).order_by(seq)`；session.execute。
- 分支表（穷尽）：
  1. 恒（无分支）→ 返回该 run 全部步，seq 升序。
- 副作用：无。
- 返回：`list[AgentV2Step]`。
- 规则条目：
  - R-J-24 仅按 run_id 过滤＋seq 升序；无分页、无条数上限。
- 耦合：sqlalchemy.select；AgentV2Step；ConnectionManager.session。
- 疑点：
  - D-J-14 长 run 全量读（无 limit/分页）——消费者 api/chat.py:308 直出；行量面代码无注记。

### `RunStore.put_blackbox`（store.py L242-L248）｜黑匣子档案 upsert
- 消费：run_id；payload（dict，整体入 JSON 列）。
- 调用：`session.merge(AgentV2Blackbox(run_id=..., payload=..., created_at=now()))`；flush。
- 分支表（穷尽）：
  1. merge 语义：行存在 → UPDATE payload＋created_at；不存在 → INSERT。
- 副作用：持久化写 `agent_v2_blackbox`（upsert）；emit 无。
- 返回：None。
- 规则条目：
  - R-J-25 run_id 主键取末次（同 run 重写覆盖，docstring L243）。
  - R-J-26 created_at 每次覆写为当次 now()。
- 耦合：infra.clock.now；ConnectionManager.session；AgentV2Blackbox。
- 疑点：
  - D-J-15 created_at 覆盖——原始首写时间不保留（与「末次」语义并存未注记）。

### `RunStore.get_blackbox`（store.py L250-L253）｜读黑匣子档案
- 消费：run_id。
- 调用：`session.get(AgentV2Blackbox, run_id)`；`dict(row.payload)`。
- 分支表（穷尽）：
  1. 行存在 → 返回 `dict(row.payload)`（外层浅拷贝）。
  2. 行不存在 → None。
- 副作用：无。
- 返回：`dict[str, Any] | None`。
- 规则条目：
  - R-J-27 返回值是 payload 的浅拷贝——嵌套对象引用与 ORM 反序列化结果共享（会话已关，无回写路径）。
- 耦合：ConnectionManager.session；AgentV2Blackbox。
- 疑点：无。

### `RunStore.count_checkpoints`（store.py L255-L262）｜按 run_id 数 checkpoint 行
- 消费：run_id。
- 调用：`select(func.count()).select_from(AgentV2Checkpoint).where(thread_id==run_id)`；session.scalar；`int(total or 0)`。
- 分支表（穷尽）：
  1. scalar 返回 None 或 0 → 0。
  2. 有行 → 行数 int。
- 副作用：无。
- 返回：int。
- 规则条目：
  - R-J-28 以 `thread_id == run_id` 计数（与 checkpointer 的 thread_id=run_id 约定同源）；不过滤 checkpoint_ns。
- 耦合：sqlalchemy.func/select；AgentV2Checkpoint；ConnectionManager.session。
- 疑点：
  - D-J-16 ns 维度不参与计数——单 run 仅默认 ns（""）时无差；多 ns 场景（子图）行数会合并，代码无注记。

### `ensure_agent_v2_tables`（store.py L265-L277）｜P0-08 前幂等建表
- 消费：engine（AsyncEngine，调用方 appv2/api/app.py:261 传 db.engine()）。
- 调用：六模型 `__table__.create`（checkfirst=True），逐表 `engine.begin()`＋`conn.run_sync`。
- 分支表（穷尽）：
  1. 表已存在（checkfirst 判定）→ 跳过 CREATE。
  2. 表不存在 → CREATE。
  3. 逐表独立事务——第 k 张失败时前 k-1 张已提交，余表不建（异常上抛）。
- 副作用：持久化 DDL 建六表（agent_v2_run/step/blackbox/checkpoint/checkpoint_blob/checkpoint_write）；emit 无。
- 返回：None。
- 规则条目：
  - R-J-29 幂等（checkfirst）；建表清单＝六模型 tuple（L267-274），与 Alembic 0022 双轨同形（docstring L266）。
  - R-J-30 每表一个 engine.begin() 事务，非全体单事务。
- 耦合：appv2.infra.db.Base（模型基类）；sqlalchemy.AsyncEngine/Table；AgentV2* 六模型。
- 疑点：
  - D-J-17 双轨同形的「形」无机器闸——本文件不引用/校验 Alembic 0022 迁移文件（本仓迁移目录不在本四文件面内，不判）。

### `PgCheckpointer.__init__`（checkpointer.py L39-L41）｜装配基类与现代理
- 消费：db（ConnectionManager）。
- 调用：`super().__init__()`（基类构造：serde 缺省 JsonPlusSerializer，base:216）；赋值 self._db。
- 分支表（穷尽）：无。
- 副作用：无。
- 返回：None。
- 规则条目：
  - R-J-31 不传 serde——使用基类默认 JsonPlusSerializer；序列化格式由基类决定，本类不选型。
  - R-J-32 会话一律经 ConnectionManager（B3；docstring L4 声明绕开官方 psycopg 直连）。
- 耦合：langgraph.checkpoint.base.BaseCheckpointSaver；appv2.infra.db.ConnectionManager。
- 疑点：
  - D-J-18 类声明 `BaseCheckpointSaver[str]`（版本类型 str），但未覆写 `get_next_version`：继承基类默认实现（base:692-713）返回 int（None→1，current+1），current 为 str 时抛 NotImplementedError；langgraph 在 checkpoint 装配时取 `checkpointer.get_next_version`（pregel/_draw.py:69-72）——运行时 version 实为 int，仅在落库处 str(version) 归一。声明类型与运行时版本类型不一致，代码无注记。
  - D-J-19 基类其他抽象面（aget/aget_tuple 之外的同步 get_tuple 等）未覆写——调用方仅异步路径（app.py:236 saver 注入）；混用同步 API 的后果代码无注记。

### `PgCheckpointer.aget_tuple`（checkpointer.py L45-L99）｜读单 checkpoint（最新/指定 id）
- 消费：config（`configurable.thread_id` 必取键；`checkpoint_ns` 缺省 ""；可选 `checkpoint_id`）。
- 调用：`_latest_or_by_id`；`_loads`；`_load_blobs`；`select(AgentV2CheckpointWrite)`；sorted；构造 CheckpointTuple。
- 分支表（穷尽）：
  1. 行不存在（无 checkpoint_id 且表空 / 指定 id 不存在）→ 返回 None。
  2. config 有 checkpoint_id（`get_checkpoint_id`）→ 取该 id 行；否则取 (thread, ns) 下 checkpoint_id desc 首行。
  3. 返回 config：入参含 checkpoint_id → 原样透传；否则重建含 row.checkpoint_id 的 config。
  4. 返回 parent_config：row.parent_checkpoint_id 非空 → 重建三元 config；空 → None。
  5. channel_values 装配：逐 channel_versions 查 blob；行缺或 type=="empty" → 该 channel 不入结果（永不出现空通道键）。
  6. pending_writes：取该 (thread, ns, checkpoint_id) 全部 write 行，按 (task_id, idx) 升序 → `(task_id, channel, loads(type, blob))` 三元组列表。
- 副作用：无（纯读）。
- 返回：`CheckpointTuple | None`。
- 规则条目：
  - R-J-33 metadata 用 `row.type`（checkpoint 行的类型标签）解码（与 aput「单 type 列两用」假设绑定）。
  - R-J-34 checkpoint dict 除 channel_values 外全部键原样回放（checkpoint 行存的 body 不含 channel_values）。
  - R-J-35 thread_id＝run_id（一 run 一线程，docstring L10）。
- 耦合：langgraph.checkpoint.base.{get_checkpoint_id, CheckpointTuple}；store.{AgentV2Checkpoint, AgentV2CheckpointWrite}；ConnectionManager.session。
- 疑点：
  - D-J-20 writes 读取不按 channel_versions 过滤、不按 task 状态区分——「该 checkpoint 行下所有 write」原样出（与官方 saver 行为差异未在注释声明）。
  - D-J-21 checkpoint body 键完整性不校验（直接 `checkpoint["channel_versions"]` 下标取，缺键即 KeyError）。
  - D-J-22 入参 config 带 checkpoint_id 时返回值 config 原样透传（含调用方可能多带的键）——与「重建 config」分支不同形。

### `PgCheckpointer.alist`（checkpointer.py L101-L161）｜按线程倒序列 checkpoint
- 消费：config（None 即空出）；filter/before 形参声明未使用；limit 可选。
- 调用：select … order_by(checkpoint_id.desc())；_loads；_load_blobs；yield CheckpointTuple。
- 分支表（穷尽）：
  1. config is None → return（空迭代）。
  2. `thread_id` 取 configurable.get 后为空 → return（空迭代）。
  3. 逐行（checkpoint_id desc）：limit 非 None 且 limit<=0 → return（停止）。
  4. limit 非 None → 递减 1 后 yield。
  5. 每行 yield 的 CheckpointTuple：config 重建、channel_values 由 blob 装配、metadata 解码、parent_config 由 parent_checkpoint_id 重建（空 → None）。
- 副作用：无。
- 返回：`AsyncIterator[CheckpointTuple]`（异步生成器）。
- 规则条目：
  - R-J-36 「倒序」＝checkpoint_id 字符串降序（非 created_at 类时间列——表无时间列）。
  - R-J-37 limit<=0 零产出；limit 恰出 N 条（先判后减）。
  - R-J-38 pending_writes 不装配（与 aget_tuple 不同——列表面不含 write 行）。
- 耦合：langgraph.checkpoint.base.CheckpointTuple；store.AgentV2Checkpoint；ConnectionManager.session。
- 疑点：
  - D-J-23 filter 与 before 两形参完全未读（L105-106）——调用方传值静默忽略；docstring L109 只自认「metadata filter 语义不承载」，before 未提。
  - D-J-24 与 aget_tuple 的输出形状不一致（列表项缺 pending_writes）——两读口无共享装配函数，差异无注记。
  - D-J-25 「最新」判定依赖 checkpoint_id 字典序——langgraph 生成的 id 形态决定时序正确性，代码内无约束注记（与 _latest_or_by_id 同根）。

### `PgCheckpointer.aput`（checkpointer.py L165-L214）｜写 checkpoint 行＋版本 blob
- 消费：config（thread_id 必取、checkpoint_ns 缺省 ""、可选 checkpoint_id＝父指针）；checkpoint（含 id、channel_values、channel_versions 等）；metadata；new_versions（channel→version）。
- 调用：`serde.dumps_typed`（body 一次、metadata 一次、逐通道值）；`_upsert_blob`；session.get/构造 AgentV2Checkpoint；flush；`get_checkpoint_metadata`。
- 分支表（穷尽）：
  1. `body.pop("channel_values")` —— checkpoint 输入含该键是前置（缺 → KeyError）。
  2. 逐 (channel, version) of new_versions：channel 在 values → dumps_typed(values[channel])；不在 → ("empty", b"") → upsert blob（key=channel＋str(version)）。
  3. checkpoint 行 (thread_id, ns, checkpoint["id"])：存在 → 复用；缺 → 新建 add。
  4. parent_checkpoint_id 取 `config["configurable"].get("checkpoint_id")`（首写 None）。
  5. metadata 的 dumps_typed 类型标签丢弃（`_meta_type` 未用）——行上 type 列只存 checkpoint body 的标签。
  6. session 退出 commit；异常 rollback。
- 副作用：持久化写 `agent_v2_checkpoint_blob`（逐 channel/version upsert）；`agent_v2_checkpoint`（upsert）；emit 无。
- 返回：新 config dict（thread_id/checkpoint_ns/checkpoint_id=checkpoint["id"]）——后续步骤引用该 checkpoint 的凭据。
- 规则条目：
  - R-J-39 checkpoint body 剔除 channel_values 后序列化；通道值归 blob 表（按版本去重——同版本重复写覆写）。
  - R-J-40 metadata 与 checkpoint 共用行上单 type 列（注释 L177-178 自认「骨架版，格式分拆需求出现时再拆列」）。
  - R-J-41 blob 键版本用 `str(version)`——与 _load_blobs 侧同形（int/str 归一为字符串）。
  - R-J-42 入参 checkpoint 只做顶层浅拷贝（`body = dict(checkpoint)`），pop 不影响调用方对象。
- 耦合：serde（BaseCheckpointSaver 属性）；langgraph.checkpoint.base.get_checkpoint_metadata；store 三 checkpoint 模型；ConnectionManager.session。
- 疑点：
  - D-J-26 metadata 解码路径（aget_tuple 用 row.type）依赖「checkpoint 标签与 metadata 标签恒同」——由 JsonPlusSerializer 恰好同实现，若 serde 更换/格式分拆则读面错解，注释只承认「格式分拆需求出现时再拆列」。
  - D-J-27 同一 checkpoint id 重复 aput 时旧版本 blob 行不清理（孤儿 blob 留存）；表无 GC 路径。
  - D-J-28 blob 的 "empty" 标记判据＝`channel in values` 键存在性而非值空否——值为 None 的通道仍走 dumps_typed 正常序列化，读面无法区分「真实 None」与「空标记」的语义边界无注释。

### `PgCheckpointer.aput_writes`（checkpointer.py L216-L246）｜写 task 级中间写入
- 消费：config（thread_id/checkpoint_ns/checkpoint_id）；writes（(channel, value) 序列）；task_id；task_path（声明未用）。
- 调用：`get_checkpoint_id`；`serde.dumps_typed`；`WRITES_IDX_MAP.get`；session.get/add；flush。
- 分支表（穷尽）：
  1. checkpoint_id 空（config 无）→ 直接 return——写静默丢弃。
  2. 逐 (idx, (channel, value))：write_idx = WRITES_IDX_MAP.get(channel, idx)（ERROR→-1 / SCHEDULED→-2 / INTERRUPT→-3 / RESUME→-4，其余用枚举 idx）。
  3. 行 (thread, ns, checkpoint_id, task_id, write_idx)：存在 → 复用；缺 → 新建 add。
  4. 恒写 channel/type/blob 三列。
- 副作用：持久化写 `agent_v2_checkpoint_write`（upsert）；emit 无。
- 返回：None。
- 规则条目：
  - R-J-43 保留通道（error/scheduled/interrupt/resume）用负索引，普通通道按写入序 idx——同键重复写覆写。
  - R-J-44 task_path 不持久化（表无对应列，形参未用）。
- 耦合：langgraph.checkpoint.base.{WRITES_IDX_MAP, get_checkpoint_id}；serde；store.AgentV2CheckpointWrite。
- 疑点：
  - D-J-29 无 checkpoint_id 时静默 return——写丢失零留痕（生产路径是否可达未在代码内注记）。
  - D-J-30 普通多值写（同 task 多写）按写入序 idx 定键；跨次调用 idx 重排会覆写旧 write 行（langgraph 调用语义是否保证 idx 稳定不由本类把守）。

### `PgCheckpointer.adelete_thread`（checkpointer.py L248-L261）｜删线程三表全部行
- 消费：thread_id。
- 调用：select(AgentV2Checkpoint/Blob/Write) where thread_id；session.delete 逐行。
- 分支表（穷尽）：
  1. 恒（无分支）→ 三表各自全量查出行并逐行 delete；不显式 flush，靠 session 退出 commit。
- 副作用：持久化写 `agent_v2_checkpoint`／`_blob`／`_write`（DELETE）；emit 无。
- 返回：None。
- 规则条目：
  - R-J-45 删除面＝checkpoint 三表；agent_v2_run/step/blackbox 不动（簿记与黑匣子不随线程删）。
- 耦合：store 三 checkpoint 模型；ConnectionManager.session。
- 疑点：
  - D-J-31 逐行 ORM delete（非批量 DELETE 语句）；调用点在本仓生产代码未现（本轮检索仅定义处）——基类契约面存在、生产是否走 DELETE 语义未注。
  - D-J-32 无 flush 显式调用，删除有效性依赖 session 上下文退出 commit（异常则整体 rollback——与逐行 delete 中间态无注记）。

### `PgCheckpointer._loads`（checkpointer.py L265-L266）｜serde 反序列化单点
- 消费：type_tag、blob（bytes）。
- 调用：`self.serde.loads_typed((type_tag, bytes(blob)))`。
- 分支表（穷尽）：无。
- 副作用：无。
- 返回：Any（反序列化值）。
- 规则条目：
  - R-J-46 `bytes(blob)` 拷贝转换——防 DB 驱动返回的 memoryview 类对象直入 serde。
- 耦合：BaseCheckpointSaver.serde。
- 疑点：无。

### `PgCheckpointer._latest_or_by_id`（checkpointer.py L268-L291）｜定位 checkpoint 行
- 消费：session、thread_id、checkpoint_ns、config。
- 调用：`get_checkpoint_id(config)`；session.get；select … order_by(checkpoint_id.desc()).limit(1)。
- 分支表（穷尽）：
  1. config 含 checkpoint_id → 按 (thread_id, checkpoint_ns, checkpoint_id) 主键取行（可 None）。
  2. 否则取 (thread_id, checkpoint_ns) 下 checkpoint_id 最大 1 行；无行 → None。
- 副作用：无。
- 返回：`AgentV2Checkpoint | None`。
- 规则条目：
  - R-J-47 「最新」＝checkpoint_id 字符串降序首行（非时间列）。
- 耦合：langgraph.checkpoint.base.get_checkpoint_id；store.AgentV2Checkpoint。
- 疑点：
  - D-J-33 checkpoint_id 若为非单调生成的字符串（uuid 等），「最新」判定失真——id 生成方在 langgraph 侧，本类无格式约束注记。

### `PgCheckpointer._load_blobs`（checkpointer.py L293-L308）｜按版本装配 channel_values
- 消费：session、thread_id、checkpoint_ns、versions（channel→version）。
- 调用：逐通道 session.get(AgentV2CheckpointBlob, (thread, ns, channel, str(version)) )；_loads。
- 分支表（穷尽）：
  1. 行缺 → 跳过（该 channel 不出现在结果）。
  2. row.type == "empty" → 跳过（空值通道不入 channel_values）。
  3. 其余 → result[channel] = loads(type, blob)。
- 副作用：无。
- 返回：`dict[str, Any]`。
- 规则条目：
  - R-J-48 结果键集 ⊆ versions 键集；「empty」标记列（aput 对 values 外通道写 ("empty", b"")）即此类行的解码拦截标记。
- 耦合：store.AgentV2CheckpointBlob。
- 疑点：
  - D-J-34 逐通道一次 session.get（N 次查询——无批量 IN）；通道数规模未见上限注记。

### `PgCheckpointer._upsert_blob`（checkpointer.py L310-L332）｜blob 行 upsert
- 消费：session、thread_id、checkpoint_ns、channel、version（str）、type_tag、blob。
- 调用：session.get；构造 AgentV2CheckpointBlob；add；字段赋值。
- 分支表（穷尽）：
  1. 行存在 → 复用（UPDATE）。
  2. 行缺 → 新建 (thread, ns, channel, version) → add。
  3. 恒写 type/blob。
- 副作用：持久化写 `agent_v2_checkpoint_blob`（upsert；flush 由调用方 aput 统一 flush）。
- 返回：None。
- 规则条目：
  - R-J-49 本方法不自 flush/commit——事务边界归调用方（aput 的 session 块）。
- 耦合：store.AgentV2CheckpointBlob。
- 疑点：无。

### `distill`（blackbox.py L78-L105）｜运行终态→黑匣子记录
- 消费：final（Mapping|None，RunState 终态）；run_id 缺省 ""；error 缺省 ""。
- 调用：`_plain`；`final.get`。
- 分支表（穷尽）：
  1. `final is None` → 骨架记录（run_id＝入参、question=""、status=""、error＝入参）→ 立即返回，零状态键。
  2. 逐 `_DISTILL_KEYS` 20 键：`final.get(key)` 为 None → 跳过；否则 `record[key] = _plain(value)`。
  3. 身份面三项覆写：run_id=`str(final.get("run_id") or run_id)`；question=`str(final.get("question") or "")`；status=`str(final.get("status") or "")`。
- 副作用：无（纯函数——不触 clock/db/langgraph，docstring L6）。
- 返回：`dict[str, Any]`。
- 规则条目：
  - R-J-50 记录恒含身份面四键 run_id/question/status/error；状态键按白名单闭世界拷贝。
  - R-J-51 final 的键值优先于入参 run_id（同名时 final 覆盖）。
  - R-J-52 final 内 "error" 键不在白名单——记录 error 只来自入参（终态错误文本经参数进）。
  - R-J-53 record 键插入顺序＝身份面先 4 键，再按白名单顺序。
- 耦合：collections.abc.Mapping；_plain。
- 疑点：
  - D-J-35 final 与入参 run_id 不一致时静默采 final——无告警/断言。
  - D-J-36 白名单含 messages 与 dialogue 并列（两键都进记录）——两者关系（历史/现役）代码内无注记。

### `pointer`（blackbox.py L108-L133）｜记录→瘦指针（wire 面）
- 消费：record（Mapping）；stored 缺省 False；bytes_written 缺省 0。
- 调用：`record.get`；`len(... or [])`。
- 分支表（穷尽）：无（无条件构造固定七键）。
- 副作用：无。
- 返回：dict：run_id/question/status/error（str 化）＋stored(bool)＋bytes(int)＋counts。
- 规则条目：
  - R-J-54 counts 五键固定：messages/dialogue/process_notes/observations/steps 的长度；缺键记 0。
  - R-J-55 wire 面只出指针（docstring L114：防帧/仓膨胀），完整面在库。
- 耦合：无外部模块（纯内建）。
- 疑点：
  - D-J-37 counts 集合与 `_DISTILL_KEYS` 不同步（rounds/notices 等有记录无计数）——指针口径裁剪依据无注记（含 dialogue 计数而 messages 为 v3 链形主载体的关系亦无注记）。

### `render_snapshots`（blackbox.py L136-L146）｜快照列→转写文本
- 消费：snapshots（list[dict]，含 checkpoint_id、channels）；as_json 缺省 False。
- 调用：`json.dumps`；`_render_channel`；`snap.get`。
- 分支表（穷尽）：
  1. as_json=True → `json.dumps(snapshots, ensure_ascii=False, indent=2, default=str)` 直返（不再蒸馏）。
  2. as_json=False → 逐 snap：`"== 快照 {snap.get('checkpoint_id','?')} =="` 头行＋`channels`（缺 → {}）逐通道 `_render_channel` 行；最终 `"\n".join`。
- 副作用：无（纯函数）。
- 返回：str。
- 规则条目：
  - R-J-56 人读缺省；机器面 as_json 全量直 dump（docstring L137）。
  - R-J-57 渲染顺序＝快照列顺序、通道 dict 插入顺序。
- 耦合：json；_render_channel。
- 疑点：
  - D-J-38 snap["channels"] 假值兜底为 {}，但非 Mapping 值（如 list）会在 `.items()` 处 AttributeError——输入契约代码无校验。

### `_plain`（blackbox.py L152-L160）｜状态值→JSON 安全面
- 消费：value（Any）。
- 调用：递归自身。
- 分支表（穷尽）：
  1. None / str / int / float / bool → 原样返回。
  2. Mapping → `{str(key): _plain(item)}`（键 str 化）。
  3. list / tuple → 逐项递归成 list。
  4. 其它对象 → `str(value)` 降级。
- 副作用：无。
- 返回：JSON 可序列化值。
- 规则条目：
  - R-J-58 非常规值降级 str——不因脏值抛错（docstring L153）。
  - R-J-59 tuple→list、非 str 键→str（结构归一）。
- 耦合：collections.abc.Mapping。
- 疑点：无。

### `_head`（blackbox.py L163-L165）｜单行摘要截断
- 消费：value（str）；limit 缺省 96。
- 调用：str.replace。
- 分支表（穷尽）：
  1. `len(text) <= limit` → 原样返回（换行已替换）。
  2. 超长 → `text[:limit] + "…"`。
- 副作用：无。
- 返回：str。
- 规则条目：
  - R-J-60 换行替换为 " ⏎ "；截断按替换后的字符数。
- 耦合：无外部模块。
- 疑点：无。

### `_render_channel`（blackbox.py L168-L227）｜单通道→转写行
- 消费：name（str）、value（Any）。
- 调用：`_head`、`len`、`str`。
- 分支表（穷尽）：
  1. name∈{messages, dialogue} 且 value 是 list → 头行 `"  {name}（{len} 轮）——{label}:"`（messages 标签「对话链（只追加——LLM 收发的逐轮形）」；dialogue「自然对话层（用户原话与终稿）」）＋逐消息 `[role] _head(content)`（dict → get role/content 缺省 "?"/""；非 dict → role="?"、str(message)）。
  2. name=="process_notes" 且 list → 头行「（N 条）——过程档案（有界摘要）」；dict → `[phase] _head(title,30)｜_head(digest,80)`；非 dict → `_head(str(note))`。
  3. name=="observations" 且 list → 头行「（N 支）——全字段:」；dict → locator 是 dict 取 kind 否则 "-"、trust 缺省 "-"、`源=_head(source,40)` 行＋`_head(content)` 行；非 dict → `_head(str(obs))`。
  4. name=="steps" 且 list → 头行「（N 条）:」；dict → `[seq] step _head(title,60)`＋payload 真值 → `payload _head(str(payload))`；非 dict → `_head(str(step))`。
  5. 其它 name 且 list → `"  {name}（{len} 条）: {_head(str(value))}"`。
  6. 非 list → `"  {name}: {_head(str(value))}"`。
- 副作用：无。
- 返回：`list[str]`（行）。
- 规则条目：
  - R-J-61 专属渲染仅四族（messages/dialogue/process_notes/observations/steps 中的前四判＋steps 判）——不在族中走通用短形。
  - R-J-62 _head 截断参数分面：title 30（process_notes）/60（steps）、digest 80、source 40、content 与通用值 96 缺省。
- 耦合：_head。
- 疑点：
  - D-J-39 name 命中专属族但 value 非 list 时静默降级到分支 5/6——无专属标签行（输入契约未校验）。
  - D-J-40 observations 的 kind 仅 locator 为 dict 时取，否则 "-"——locator 形态契约未在本文件声明。

### `summarize`（audit.py L49-L54）｜审计摘要单点
- 消费：text（str）；limit 缺省 SUMMARY_LIMIT=120。
- 调用：`" ".join(text.split())`、len、切片。
- 分支表（穷尽）：
  1. flat 长度 ≤ limit → 返回 flat。
  2. 超长 → `flat[:limit] + "…"`（截断可见）。
- 副作用：无。
- 返回：str。
- 规则条目：
  - R-J-63 所有空白（含换行）折叠为单空格；截断后缀「…」明示未全文（docstring L50）。
  - R-J-64 limit 可调——但全部调用点用缺省 120。
- 耦合：无外部模块。
- 疑点：无。

### `who_of`（audit.py L57-L59）｜who 槽单点
- 消费：actor（security.domain.Actor）。
- 调用：`actor.who`；`resolve_actor(actor.user_id).who`。
- 分支表（穷尽）：
  1. `actor.who` 真值 → 原样返回（经 Actor.who＝display 属性）。
  2. 空 → `resolve_actor(actor.user_id).who` 重新解析；非五角色键 → `UnauthenticatedError` 上抛（无捕获）。
- 副作用：无。
- 返回：str（label 全名）。
- 规则条目：
  - R-J-65 who 槽口径＝label 全名（00 §9.1）；缺省回落重新解析（docstring L58）。
- 耦合：appv2.infra.security.{Actor, resolve_actor}。
- 疑点：
  - D-J-41 actor.user_id 非法时本函数抛 401 语义异常——调用方 executor.py:181 段无捕获注记（异常是否可达取决于上游 resolve_actor 先行解析）。

### `RunAuditor.__init__`（audit.py L69-L74）｜装配审计出口
- 消费：db（ConnectionManager）；security（SecurityService|None 缺省 None）。
- 调用：`SecurityService(db)`（None 分支）。
- 分支表（穷尽）：
  1. security 传参非 None → 复用外部实例。
  2. 缺省 None → 自建 SecurityService(db)。
- 副作用：无；self._ready=False 初值。
- 返回：None。
- 规则条目：
  - R-J-66 审计唯一写口固定为 SecurityService.audit（B12）；本类不自建 SQL 写路径。
- 耦合：appv2.infra.security.SecurityService。
- 疑点：无。

### `RunAuditor.ensure_ready`（audit.py L76-L81）｜audit_log 幂等建表（每实例一次）
- 消费：self._ready、self._db。
- 调用：`ensure_audit_table(self._db.engine())`。
- 分支表（穷尽）：
  1. `self._ready` 真 → 直接 return。
  2. 假 → 先置 `self._ready = True`，再 await 建表（checkfirst 幂等）。
- 副作用：持久化 DDL 建表 `audit_log`（checkfirst）；emit 无。
- 返回：None。
- 规则条目：
  - R-J-67 先置后建——并发受理去重（docstring L80）；空库首写 500 防护。
- 耦合：appv2.infra.security.store.ensure_audit_table；ConnectionManager.engine。
- 疑点：
  - D-J-42 建表抛异常时 `_ready` 已置 True——后续调用不再重试；缺口暴露路径依赖调用方（executor.py:178 无 try 包本调用）。

### `RunAuditor.run_created`（audit.py L83-L91）｜受理留痕
- 消费：run_id/question/who（均 keyword-only）。
- 调用：`summarize`；`self._security.audit(AuditRow(...))`。
- 分支表（穷尽）：
  1. 恒（无分支）→ AuditRow(who, action=ACTION_RUN_CREATED, content=f"问答受理：{summarize(question)}", meta={"run_id": run_id}) → audit 写库。
- 副作用：持久化写 `audit_log`（append-only 一行；SecurityService.audit 缺省自管会话独立提交，service.py:27-37）；emit 无。
- 返回：None。
- 规则条目：
  - R-J-68 meta 仅携 run_id；question 全文不入审计（content 摘要 ≤120，模块注 L45）。
  - R-J-69 调用序：executor.py:193 在 run 行创建后、spawn 前。
- 耦合：ACTION_RUN_CREATED；summarize；SecurityService.audit；AuditRow。
- 疑点：无。

### `RunAuditor.run_completed`（audit.py L93-L103）｜终态收口留痕
- 消费：run_id/answer/manifest_digest/who。
- 调用：`summarize`；`audit`。
- 分支表（穷尽）：
  1. 恒 → AuditRow(action=ACTION_RUN_COMPLETED, content=f"回答收口：{summarize(answer)}", meta={"run_id", "manifest_digest"})。
- 副作用：`audit_log` 追加一行；emit 无。
- 返回：None。
- 规则条目：
  - R-J-70 manifest_digest 必填参数——空串也照写入 meta（executor.py:468-470 传 final 的 digest 值）。
- 耦合：ACTION_RUN_COMPLETED；summarize；SecurityService.audit。
- 疑点：无。

### `RunAuditor.run_failed`（audit.py L105-L113）｜失败收口留痕
- 消费：run_id/error/who。
- 调用：`summarize`；`audit`。
- 分支表（穷尽）：
  1. 恒 → AuditRow(action=ACTION_RUN_FAILED, content=f"执行失败：{summarize(error)}", meta={"run_id"})。
- 副作用：`audit_log` 追加一行；emit 无。
- 返回：None。
- 规则条目：
  - R-J-71 error 全文不入审计（摘要截断）；异常与状态分支共用本方法（executor.py:443/476）。
- 耦合：ACTION_RUN_FAILED。
- 疑点：无。

### `RunAuditor.refused`（audit.py L115-L123）｜拒答收口留痕
- 消费：run_id/reason/who。
- 调用：`summarize`；`audit`。
- 分支表（穷尽）：
  1. 恒 → AuditRow(action=ACTION_REFUSED, content=f"拒答收口：{summarize(reason)}", meta={"run_id"})。
- 副作用：`audit_log` 追加一行；emit 无。
- 返回：None。
- 规则条目：
  - R-J-72 与事件流 notice type=refused 机读同源（docstring L8）；拒答与正常收口互斥恰一行（executor.py:544-546 分型）。
- 耦合：ACTION_REFUSED。
- 疑点：无。

### `RunAuditor.ban_exempt`（audit.py L125-L138）｜N1 豁免放行留痕
- 消费：run_id/term/who。
- 调用：`summarize`；`audit`。
- 分支表（穷尽）：
  1. 恒 → AuditRow(action=ACTION_BAN_EXEMPT, content=f"N1 禁用词豁免放行（元问/引用形）：{summarize(term)}", meta={"run_id", "term"})。
- 副作用：`audit_log` 追加一行；emit 无。
- 返回：None。
- 规则条目：
  - R-J-73 豁免必留痕（V2-52 附 C）；content 摘要截断、meta["term"] 原文不截断。
- 耦合：ACTION_BAN_EXEMPT。
- 疑点：
  - D-J-43 meta["term"] 与 content 摘要口径不同（meta 可超 120 字符）——两槽互补关系无注记。

### `RunAuditor.extable_decided`（audit.py L140-L152）｜外表审批决定留痕（一类两值）
- 消费：run_id/approved(bool)/approval_id/who。
- 调用：`audit`。
- 分支表（穷尽）：
  1. `approved` 真 → action=ACTION_EXTABLE_APPROVED、verb="批准"。
  2. 假 → action=ACTION_EXTABLE_REJECTED、verb="驳回"。
  3. `approval_id` 假值（空串）→ 单号占位「（未携）」；真值 → 原样。
  4. 恒 → AuditRow(content=f"外表审批{verb}：单号 {…}", meta={"run_id", "approval_id"})。
- 副作用：`audit_log` 追加一行；emit 无。
- 返回：None。
- 规则条目：
  - R-J-74 批准/驳回单方法两值分派（action 与话术同步切换）；meta 恒两键。
- 耦合：ACTION_EXTABLE_APPROVED/REJECTED；AuditRow。
- 疑点：无。

---

## 覆盖自检
- def/class 清单差集：无（47/47：9 类＋38 函数/方法，全部有节或清单事实块；`get_next_version`/`serde` 属继承面，已注记于清单差集说明）。
- 四文件引用的外部符号全集（本四文件内定义的除外）：
  - 标准库：`__future__.annotations`；`datetime.datetime`；`json`；`collections.abc.{AsyncIterator, Mapping, Sequence}`；`typing.{Any, cast}`。
  - 第三方：`sqlalchemy.{Integer, String, Text, func, select}`；`sqlalchemy.ext.asyncio.{AsyncEngine, AsyncSession}`；`sqlalchemy.orm.{Mapped, mapped_column}`；`sqlalchemy.sql.schema.Table`；`sqlalchemy.types.JSON`；`langchain_core.runnables.RunnableConfig`；`langgraph.checkpoint.base.{WRITES_IDX_MAP, BaseCheckpointSaver, ChannelVersions, Checkpoint, CheckpointMetadata, CheckpointTuple, get_checkpoint_id, get_checkpoint_metadata}`；`langgraph.checkpoint.base.BaseCheckpointSaver.serde`（实例属性，含 `dumps_typed`/`loads_typed`）；`langgraph.checkpoint.base.WRITES_IDX_MAP` 键值 ERROR/SCHEDULED/INTERRUPT/RESUME。
  - 本仓（四文件外）：`appv2.infra.clock.now`；`appv2.infra.db.{Base, ConnectionManager}`（`session`/`engine`）；`appv2.infra.security.{Actor, AuditRow, SecurityService, resolve_actor}`（包出口 appv2/infra/security/__init__.py）；`appv2.infra.security.store.ensure_audit_table`。
  - 四文件互引：checkpointer.py 引 store.py 的 `AgentV2Checkpoint`/`AgentV2CheckpointBlob`/`AgentV2CheckpointWrite`。
  - 调用点（生产侧，供重构对账）：store ← executor.py:187/211/221/280/429/431/441/454/473/494、api/chat.py:162/301/308、api/app.py:261；checkpointer ← api/app.py:236、executor.py:146、tools/run_replay.py:33；blackbox ← executor.py:490/509、tools/run_replay.py:29/46/77/88；audit ← executor.py:31/172/178/181/193/443/476 等、executor._audit_decisions/_audit_closeout/_audit_ban_exempts。
