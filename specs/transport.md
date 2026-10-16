# V2 事件通路（transport）

状态: 已定稿
来源: `specs/modules.md` `## transport` 卡、`docs/runtime-refactor/synth/S6-事件与帧目录.md`、`docs/runtime-refactor/iface/P9a1-端点与帧通路.md`、`docs/runtime-refactor/recon/K-上下文事件指南预算.md`（events.py 段）、`walk/裁决表.md` §01、`docs/runtime-refactor/walk/01-进门.md`、`synth/S3`（C-05／C-10）、`specs/agent-loop.md` 行为 4／行为 11、`specs/persistence.md` 行为 14
版式: `docs/spec-format.md`（节标题按该文 §二之二 逐字命名） ｜ 工序: `docs/spec-process.md`

## 目标

页面能看到的**唯一出口**：runtime 九类事件与 wire 三帧的闭世界、帧信封字节形、**全流单调游标**、断线续推与载荷透传——事件的本体在各发射方，**本块只管「出去的那一帧长什么样、怎么编号、怎么续」**。

## 不做什么

| 不做 | 由谁承担 | 锚点 |
|---|---|---|
| 判定「何时发哪类事件」（业务语义） | 各相位与编排层（发射方） | `specs/agent-loop.md` 行为 1／行为 8；`specs/modules.md` 各相位卡 |
| 三态落库、命令受理、挂起恢复的编排 | `orchestration` | `specs/agent-loop.md` 行为 8 |
| 帧载荷的**业务含义**（哪种条件下发哪种 `notice.type`） | 各发射方；本块只立**分型闭世界与形状** | 同上 |
| 步记录／黑匣子原文的落盘（帧只出**瘦指针**） | `persistence` | `specs/persistence.md`；`specs/modules.md` `## persistence` |
| 限额／阈值判定（触界注记的内容） | `state`（判定）＋`bookkeeping`（落地） | `specs/state.md` 行为 12／13 |
| 模型调用 | `gateway_adapter` | `specs/modules.md` `## gateway_adapter` |
| HTTP 鉴权、参数校验、开流前的错误码（400／401／404／409） | `api`（开流前同步段） | `specs/modules.md` `## api`；`docs/runtime-refactor/iface/P9a1-端点与帧通路.md`（T-P9a1-25） |
| **`session` 首帧的发射时机与载荷**（`{run_id, resume}`，三端点流首恒发） | `api`（开流段）——本块只保证**帧名在闭世界内**与信封形状 | `specs/modules.md` `## api`；`synth/S6-事件与帧目录.md` §二；`docs/runtime-refactor/iface/P9a1-端点与帧通路.md`（T-P9a1-07） |
| 用程序替模型做语义判断（本块只搬帧，零判断） | **不做** | `docs/runtime-refactor/walk/判断归责表.md` |

## 触及的模块

| 模块 | 改动类型 | 说明 |
|---|---|---|
| transport | 新增 | 本块本体：事件总线 ＋ 帧对象 ＋ 信封 ＋ 游标 ＋ 闭世界常量族 |
| state | 新增 | `RunHandle.stream` 的元素类型引用本块的帧类型（本批把「结构别名」收正为**字符串前向引用**；state 不 import 本块，守 R4） |
| orchestration | 新增 | 总线的持有方与三态收口发帧的调用侧（本块只出入口） |
| api | 新增 | 帧→SSE 的渲染与断线游标的接缝（本块只出帧与游标语义） |

## 接口定义

```python
@dataclass(frozen=True, slots=True)
class SseEvent:                      # 帧（wire 面单元）
    seq: int                         # 全流单调游标（跨段不重启、重放不位移）——与载荷内步序号 `seq` 同名不同义（后者＝步记录序号，真源 `specs/persistence.md` `StepRecord.seq`；本字段真源＝本块行为 3）
    event: str                       # 闭世界＝EVENT_KINDS ∪ WIRE_FRAMES（合十二值）
    data: dict[str, Any]             # 载荷（透传；唯一改造＝verdict 注入 subtype）

class EventBus:                      # per-run 总线（编排块持有、注入各相位）
    def emit(self, name: str, payload: dict[str, Any]) -> SseEvent: ...
    def stream(self, cursor: int = 0) -> AsyncIterator[SseEvent]: ...
    def close(self) -> None: ...
    @property
    def closed(self) -> bool: ...

def envelope(frame: SseEvent) -> str: ...        # 帧信封字节形

# ── 闭世界常量族（取值真源逐族标注，见各行注记）─────────────
EVENT_KINDS: frozenset[str]          # runtime 九类（取值真源 synth/S6 §一；取值：step/text/tool/observation/ask/verdict/citation/notice/blackbox）
WIRE_FRAMES: frozenset[str]          # wire 三帧（取值真源 synth/S6 §二；取值：session/done/error）
NOTICE_TYPES: frozenset[str]         # 通知类型（29 值——本规格自立：实测全集逐字列全，见下）
VERDICT_SUBTYPES: frozenset[str]     # verdict 两形（verify/final）
ASK_FRAME_KINDS: frozenset[str]      # ask 帧 kind（clarify/external_table_approval）
```

- **`EVENT_KINDS`（九值）**：`step`｜`text`｜`tool`｜`observation`｜`ask`｜`verdict`｜`citation`｜`notice`｜`blackbox`（真源 `synth/S6-事件与帧目录.md` §一；九类口径真源 `synth/S3-口径裁决清单.md` C-05——「八类」为陈旧注记）。**`blackbox` 必须与其他八类同列导出面**（现状缺漏见 `synth/S3-口径裁决清单.md` C-10；本块收正）。
- **`WIRE_FRAMES`（三值）**：`session`｜`done`｜`error`（真源 `synth/S6-事件与帧目录.md` §二）。
- **`NOTICE_TYPES`（二十九值，逐字列全）**：`refused`（**V1 遗留值、V2 无发射源（V2 拒答分型＝`subtask_refused`）——阶段 7 收词**）｜`run_failed`｜`ban_exempt`｜`budget_converged`｜`clarify_capped`｜`emission_strip`｜`emission_quote_repair`｜`material_truncated`｜`unsupported_claim`｜`contradiction_split`｜`attribution_split`｜`decision_note`｜`decision_rejected`｜`chain_switch_reentry`｜`window_miss_reentry`｜`approval_gate_pending`｜`approval_recorded`｜`tool_unavailable`｜`subtask_failed`（条件字面，旧码 `appv2/runtime/graph.py`（:3483））｜`subtask_refused`｜`audit_write_failed`｜`blackbox_write_failed`｜`window_note`｜`no_hit`｜`unbound_degrade`｜`freshness_block`｜`same_param_replay`｜`rebind`｜`schema_not_allowed`（**2026-10-16 补全（流水 53-C）：真源＝B5 golden 回放 54444 帧实测（1028 帧越界取值），来源＝V1 tools/query/gate 通道**——补全前 22 值之**来源＝现状码面实测**：`appv2/runtime/` 下 `graph.py`／`executor.py`／`budget.py`／`context.py` 的 `"type":` 发射点全量；`recon/K-上下文事件指南预算.md` 的疑点 D-K-48／D-K-56 只记「该值集合无闭世界常量」，未列全——**本规格自立为该族取值真源（实测全集）**，新增类型必须同批入列，见行为 7——2026-10-16 收词：`subtask_failed` 行的行号引用体例收齐为本仓体例（路径在反引号内、行号在反引号外））。
- **`VERDICT_SUBTYPES`（二值）**：`verify`｜`final`。
- **`ASK_FRAME_KINDS`（二值）**：`clarify`｜`external_table_approval`（对账：`preconditions` 的 `AskReason.kind` → 本闭世界的映射表在 `specs/preconditions.md` 接口定义）。
- **错误契约**：事件名越界 → **构造期抛错（fail-closed）**；`close` 后再 `emit` → **抛错（不静默丢弃）**；`stream` 的非法 `cursor`（负数）→ 抛错。
- 真源：`specs/modules.md` `## transport` 卡（签名以卡为准）。

## 框架与依赖红线

- **无点名框架**（本块不引入任何框架）。对应闸：**R5b 契约**。
- **不引包内其它块**（本块只依赖 `state` 的类型名）。对应闸：**无专属闸 → 人审**（原因：R1–R8 无 transport 的边界条；可降维面＝AST 断言「本块 import 不出现其它 runtimev2 块」）。
- **模型出口零接触**：本块不含模型调用。对应闸：**R7 契约**。
- **不直引引擎**（`knowledge`／`query`／`retrieval`）。对应闸：**R6 契约**。
- **禁手写替代（不得自建第二套帧通路）**：帧对象、信封、游标都只在本块实现；`api` 只做渲染。对应闸：**无专属闸 → 人审**（降维面＝AST 断言「帧信封字节形只在本块出现一次实现」，登记待补）。
- **帧不承载业务判断**：本块不读词表、不判语义、不改写载荷内容。对应闸：测试 `::payload_passthrough_no_rewrite`。

## 行为约定

1. **事件名闭世界十二值**：`SseEvent.event` ∈ `EVENT_KINDS ∪ WIRE_FRAMES`；越界**构造期即抛错**（fail-closed，不静默丢弃、不降级为默认类）。断言：越界名构造抛错；十二个合法值各构造成功。
2. **帧信封字节形恒定**：`envelope(frame)` 恒为「`id: <int>` ＋ 换行 ＋ `event: <str>` ＋ 换行 ＋ `data: <json>` ＋ 换行 ＋ 空行」三行＋空行；JSON 以 `ensure_ascii=False` 序列化（中文不转义），非 JSON 原语值兜底为字符串而**不炸流**。断言：任一帧的信封恒三行＋空行；中文逐字不被转义；含 `Decimal`／`date` 的载荷能渲染。
3. **游标＝全流单调 `seq`（一处编号）**（Owner 裁决 `walk/裁决表.md` §01-A「游标全流单调——跨段不重启、重放不位移」）：`seq` 由总线历史长度唯一决定、0 起、严格递增、无跳号；**跨段（提问段→resume 段）不重启、重放不位移**；**响应内不再另起计数器**（治现状「首段／resume 段／重放流三套编号互不同源」的历史缺陷）。断言：两段拼接后 `seq` 严格递增且无重复；对同一帧重放两次得同一 `seq`。
4. **信封 `id:` 行＝「最后已消费事件 seq」（两类帧同语义）**：事件帧的 `id` ＝ 该帧自身 `seq`（交付即消费，故亦＝此刻最后已消费事件 `seq`）；**wire 三帧（session／done／error）不推进事件游标**——其 `id` 写作**最后已消费事件 `seq`**（尚未消费任何事件时＝**-1**；故 wire 帧 `id` 可与前帧相同、且不改动续传位置）。客户端以任一帧的 `id` 回送 `Last-Event-ID` 即可**无位移续传**。断言：连续事件帧的 `id` 严格递增；wire 帧的 `id` ＝ 最后已消费事件 `seq`（尚未消费任何事件时＝-1）且不改变游标。
5. **断线续推不重不漏（`cursor` 是排他起点）**：`cursor` 语义＝**下一帧的 `seq`**（等价现状 `recon/K-上下文事件指南预算.md` R-K-49「已收最大 `seq` ＋ 1」）；`stream(cursor)` 给出 `seq ≥ cursor` 的**全部帧**（含已在历史中的与后续新到的），**不重复、不遗漏**；客户端把 `id` 回送为 `Last-Event-ID` 时，**换算＝`cursor = id + 1`**（事件帧的 `id` 即该帧 `seq`）——**该式对事件帧与 wire 帧两类 id 同式成立**（wire 帧 `id`＝最后已消费事件 `seq`，见行为 4；故断点无论落在事件帧还是 wire 帧，重连都从**最后已消费事件之后**续传，不漏不重）。断言：以断点游标续推，帧序列＝原流中 `seq ≥ cursor` 的后缀（逐帧同 `seq`／同 `event`／同 `data`）；重复投递或漏帧即判失败。
6. **载荷透传（零裁剪零改名）——帧载荷的键集归发射方**（`step`／`text`／`tool`／`observation`／`citation`／`verdict` 各帧的键集真源＝`docs/runtime-refactor/iface/P9a1-端点与帧通路.md` T-P9a1-06／29／30 与发射点本身；**本块只透传、不校键、不补键、不删键**）：帧 `data` ＝ 发射方传入的 `payload` **原样**；**唯一改造＝`verdict` 帧注入 `subtype` 键**（判据单点：载荷含 `status` 键 → `final`，否则 → `verify`；键集越出契约时判 `verify` 且原键**如实透传**）。断言：除 verdict 外，任一帧的 `data` 与发射方 payload 深比较相等；verdict 两形的 `subtype` 取值落在 `VERDICT_SUBTYPES` 内。
7. **通知恰三键且分型闭世界**：`notice` 帧载荷**恰三键** `{type, gates, content}`；`type` ∈ `NOTICE_TYPES`（二十九值——本规格自立·实测全集），越界即拒；**取消现状的隐式兜底**（旧码 `locator.notice_type` 缺省填 `"notice"`）——**缺 `type` 即拒**（fail-closed，不猜不填）；**新增类型必须同批入列**（禁「白名单外偷偷发」）。断言：缺键／多键／越界 `type` 各判失败；二十九值各合法。
8. **ask 帧形状与 kind 闭世界**：`ask` 帧载荷＝`{frame: {kind, prompt, options, detail}, run_id}`；`kind` ∈ `ASK_FRAME_KINDS`（二值）。**挂起铁律：`ask` 帧之后照发 `done`**（挂起看 `ask` 帧、不看 `done`——`done` 只代表本腿流结束）。断言：`ask` 帧结构齐备；挂起路径的帧序列末尾仍见 `done`。
9. **流末恒发 `done`，帧通路自身异常改发 `error`**：正常收束 → `done`（载荷 `{run_id}`）；**帧通路／流渲染自身异常** → `error`，载荷**定形＝恰二键 `{code, message}`**（`code`＝稳定错误码；`message`＝稳定话术——**话术约束另列**：行为 14 ＋ Owner 裁决 `walk/裁决表.md` §01-D「不还给用户原始异常文本」，原始异常文本只进**内部留痕**（`persistence` 侧保管），帧内不得出现）（**不做 HTTP 状态**；**引擎／网关异常不发 `error` 帧**——它走 `notice{type:"run_failed"}`＋正常 `done`，见「不降级与静默禁令」节）。断言：异常路径帧为 `error`、载荷恰 `{code, message}` 二键且不含原始异常文本；正常路径为 `done`。
10. **`blackbox` 帧恒发一帧且是业务帧意义上的流末帧**：收口段**恒发一帧**（写库成败都在，以 `stored` 布尔区分），随后才 `close()`；载荷为**瘦指针**（七个键：`run_id`／`question`／`status`／`error`／`stored`／`bytes`／`counts{…}`——逐键真源 `synth/S6-事件与帧目录.md` §一），**全文入库不入帧**。断言：任一 run 的帧序列含恰一帧 `blackbox`、且在 `done` 之前；帧内无全文。
11. **多消费者各自独立游标与收束**：同一总线可被多个消费者（原响应／断线重连／后连观察者）按各自 `cursor` 读取，互不抢占；**每个消费者的收束由「已关闭且无新帧」判定，不依赖一次性哨兵**（治现状「哨兵单发→第二名消费者永久等待」的缺陷）。断言：两个消费者各自从 0 与中途游标读，均能正常收束且各自拿到的帧序列正确。
12. **`close` 幂等＋关闭后拒发**：重复 `close` 不重复投递终止信号；`close` 之后再 `emit` **抛错**（不静默丢弃）。断言：两次 `close` 无异常；`close` 后 `emit` 抛错。
13. **无「截断重放」帧**：wire 面无 `replay_truncated` 这类帧；重连时缓冲内无该 run → **由 `api` 在开流前拒（诚实拒）**，帧面**不带截断信号**（真源 `docs/runtime-refactor/iface/P9a1-端点与帧通路.md` T-P9a1-33）。断言：全帧集合里不存在截断类帧名。
14. **帧内不出现原始异常与内部路径**：`error` 帧的 `message` 为稳定话术；**任何帧都不得携带内部堆栈、模块路径、SQL 文本**。断言：异常路径全帧扫描——无堆栈／路径／SQL 片段（红线＝Owner 裁决 `walk/裁决表.md` §01-D「error 帧不给原始异常文本」；**无对应钉**，登记为人审面）。
15. **本块零判断零模型**：无词表／正则语义判定、无模型调用、无落盘。断言：AST 扫描本块源码。

## 不降级与静默禁令

- **合法降级路径：无**（帧通路不自降级：发射失败＝异常上抛，不吞、不改写为别的帧）。
- **不得静默**：`seq` 无跳号／无重启（行为 3）、缺帧不吞（行为 5）、通知分型越界即拒（行为 7）、`close` 后发射抛错（行为 12）——四条都配断言。
- **失败披露一律走帧**：引擎／网关异常 → `notice{type:"run_failed"}` ＋ 正常 `done`（**不触发 `error` 帧**——真源 `synth/S6-事件与帧目录.md` §六 边界-2 ＋ `docs/runtime-refactor/iface/P9a1-端点与帧通路.md` T-P9a1-27）；帧通路自身异常才发 `error`。
- **脱敏是硬要求**：对外帧只带稳定话术（行为 9／14）；原始异常文本归内部留痕（`specs/persistence.md`）。

## 验收测试

| 验收标准 | 对应测试 |
|---|---|
| 事件名闭世界（九 runtime ＋ 三 wire ＝十二值）；越界构造抛错 | `tests/domains/test_v2_transport.py::event_kinds_closed_world` |
| `EVENT_KINDS` 九类全列导出面（含 `blackbox`） | `tests/domains/test_v2_transport.py::blackbox_kind_exported` |
| 帧信封恒三行＋空行；中文不转义；非原语不炸流 | `tests/domains/test_v2_transport.py::envelope_bytes_stable` |
| 游标全流单调：跨段不重启、重放不位移 | `tests/domains/test_v2_transport.py::cursor_monotonic_global` |
| 信封 `id`：事件帧＝自身 `seq`、wire 帧＝最后已消费事件 `seq`（尚未消费任何事件时＝-1；不推进游标） | `tests/domains/test_v2_transport.py::frame_id_equals_cursor` |
| 断线续推不重不漏（后缀逐帧相等） | `tests/domains/test_v2_transport.py::resume_no_dup_no_gap` |
| 载荷透传零裁剪；verdict 唯一改造＋两形闭世界 | `tests/domains/test_v2_transport.py::payload_passthrough_no_rewrite` |
| 通知恰三键＋`NOTICE_TYPES` 二十九值闭世界（越界／缺键／多键／缺 `type` 判失败） | `tests/domains/test_v2_transport.py::notice_three_keys_closed_world` |
| `ask` 帧形状齐备＋`kind` 闭世界；挂起后照发 `done` | `tests/domains/test_v2_transport.py::ask_frame_shape_and_done_after_ask` |
| 正常 `done`／异常 `error`；`error` 不含原始异常文本 | `tests/domains/test_v2_transport.py::done_error_split_no_raw_exception` |
| `blackbox` 帧恰一帧、在 `done` 之前、只出瘦指针 | `tests/domains/test_v2_transport.py::blackbox_pointer_frame_last` |
| 多消费者各自独立游标与收束（不靠一次性哨兵） | `tests/domains/test_v2_transport.py::multi_consumer_independent_cursor` |
| `close` 幂等；关闭后 `emit` 抛错 | `tests/domains/test_v2_transport.py::close_idempotent_rejects_after` |
| 帧面无截断类帧名 | `tests/domains/test_v2_transport.py::no_truncation_frame` |
| 任何帧不携带堆栈／路径／SQL 片段 | `tests/domains/test_v2_transport.py::no_internal_leak_in_frames` |
| 本块零判断零模型（AST 扫描） | `tests/domains/test_v2_transport.py::no_judgement_or_model_in_transport` |
| 【边界集】零事件 run／单帧 run／超长载荷／关闭后再发 → 各落对应分支 | `tests/domains/test_v2_transport.py::boundary_empty_single_huge_closed` |
| 【保留集】常规多帧 run 的帧序与载荷行为不变 | `tests/domains/test_v2_transport.py::retention_normal_stream_unchanged` |

> **测试文件归属**：本块验收测试绑**新建** `tests/domains/test_v2_transport.py`（本块是阶段 2 新划的公共层块 `appv2/runtimev2/transport/`，与现状 `appv2/runtime/events.py` 的旧码测试形状不同）；旧码测试本批不改。

## 依赖与风险

- 依赖：`state`（`RunHandle.stream` 的元素类型以**字符串前向引用**指本块的帧类型）｜`synth/S6` 的事件与帧目录（本块立闭世界后它退为**现状证据**）｜`iface/P9a1` 的帧通路事实（现状锚）。
- 风险与对策（每条带检测手段）：
  1. **三种编号并存的历史缺陷**（首段／resume 段／重放流各一套帧号）→ 对策＝行为 3／4「一处编号＋`id`＝事件游标」。检测＝`::cursor_monotonic_global`／`::frame_id_equals_cursor`。
  2. **「八类事件」文案残留**（现状注释与上报文案写八类，实为九类）→ 对策＝闭世界只有一个常量族、文案随集合生成。检测＝`::event_kinds_closed_world`（九元）＋ 人审（文案）。
  3. **`notice.type` 无闭世界的旧状** → 对策＝行为 7 立闭世界并把**二十九值逐字入规格**＋**取消隐式兜底**。检测＝`::notice_three_keys_closed_world`。**风险**：告警类值（`audit_write_failed`／`blackbox_write_failed` 等）可能在重写后改名或合并——**变更是规格变更**（须同批改本表与测试），不许散落。
  4. **多消费者挂死**（现状一次性哨兵）→ 对策＝行为 11。检测＝`::multi_consumer_independent_cursor`。
  5. **缓冲无上限／无淘汰**（现状事实：per-run 缓冲全量常驻，无 TTL）→ 本批**不新增淘汰机制**（Owner 已把该现状缺陷登记为现状证据、不设「收债」环节）；登记为**阶段 5 可选项**，检测＝**人审**。
  6. **`error` 帧泄漏内部细节**（现状把异常文本直接拼进 `message`）→ 对策＝行为 9／14 脱敏。检测＝`::done_error_split_no_raw_exception`／`::no_internal_leak_in_frames`。
  7. **帧与 api 的接缝漂移**（信封／`id`／收场帧三处跨块）→ 对策＝本块出帧与游标语义、`api` 只渲染；检测＝`api` 块定稿时的对照（**人审**，登记）。
  8. **`SseEvent` 的类型表示**（`state` 不能 import 本块——R4）→ 对策＝字符串前向引用（卡注已定）。检测＝`::event_kinds_closed_world`（类型面）＋ 人审。
  9. **背压差异无人承接**（`docs/runtime-refactor/walk/01-进门.md` §四 D6「无背压声明 ↔ 通信契约含背压」；Owner 裁决 §01 未含、现状缺陷清单亦未列）→ **本批不新增背压机制**，定性归 `api`（SSE 流桥）——**呈主窗定性**，落地时在 `api` 规格登记。检测＝**人审**。
  10. **`pin-27` 的「帧」所指辨明**（`eng/04a` 原文「帧 `frozen_date` 全在场」）：现状 `frozen_date` 只出现在**评测跑批 jsonl 记录**与 `appv2/runtime/eval_clock.py`（其自述消费面＝跑批溯源字段），**SSE 帧代码无此键**——故该钉的「帧」＝**跑批记录**，**不属本块**（本块不登记正确）；建议 04a 钉文措辞改准（`04a` 为主窗文件，**呈主窗**）。检测＝**人审**。
  11. **「帧 vs 步记录」两处字段不同源**（现状：流内 `step` 帧不含 `manifest`／`payload`，那两键只在读口出现）→ 对策＝行为 6 透传＋本块只出帧面。检测＝**人审**（`api` 读口的字段面归 `api` 块）。

## 与闸的挂钩表

| 本规格的硬要求 | 挂钩 | 现状 |
|---|---|---|
| 验收测试逐行有标识 ／ 触及模块名已声明 | spec gate（**该闸只校这两项**——十节标题不在其作用面） | 已进 CI |
| 十节标题齐备、逐字、有序 | **人审** | 原因：仓内无标题闸（登记：可降维为一条标题机检） |
| 真源引用可解析（路径／边界规则编号／被引卡片在册） | 真源引用闸 `tools/ref_resolvable.py` | 已进 CI |
| 不引框架 | 边界闸 **R5b** | 已真跑 |
| 不直引模型出口 | 边界闸 **R7** | 已真跑 |
| 不直引引擎 | 边界闸 **R6** | 已真跑 |
| 不引包内其它块（本块只依赖 `state` 的类型名） | **无专属闸 → 人审**（降维 AST 断言登记待补） | 原因：R1–R8 无 transport 边界条 |
| 禁手写第二套帧通路 | **无专属闸 → 人审**（降维：信封实现单点断言） | 登记待补 |
| 事件名闭世界（九 runtime ＋ 三 wire ＝十二值；`blackbox` 同列导出面） | 测试 `::event_kinds_closed_world`／`::blackbox_kind_exported`；九类口径真源 `synth/S3` C-05／C-10 | 待实现 |
| 通知分型闭世界（二十九值）＋恰三键＋无隐式兜底 | 测试 `::notice_three_keys_closed_world`（本规格自立的取值真源） | 待实现 |
| 游标全流单调；事件帧 `id`＝自身 `seq`、wire 帧 `id`＝最后已消费事件 `seq`（不推进游标） | 测试 `::cursor_monotonic_global`／`::frame_id_equals_cursor` | 待实现 |
| 挂起→resume 的**帧面**（`ask` 帧 kind 闭世界＋挂起后照发 `done`） | 钉 **`pin-29`**（P0；**闭环面挂 `specs/agent-loop.md`**）；测试 `::ask_frame_shape_and_done_after_ask` | 待织网（阶段 5） |
| **材料截断披露的帧面**：`material_truncated` 帧必发且其 `type` 在闭世界内（披露行为面挂 `specs/answering.md`、字段面挂 `specs/state.md`） | 钉 **`pin-09`**（P1）；测试 `::notice_three_keys_closed_world` | 待织网（阶段 5） |
| **发射 JSON 不进答案面的帧形面**：`emission_strip` 通知的帧形（`type` ∈ `NOTICE_TYPES` 闭世界、载荷恰三键 `{type, gates, content}`）归本块；剥离行为面归 `specs/answering.md` 行为 11 | 钉 **`pin-04`**（P0）；测试 `::notice_three_keys_closed_world` | 待织网（阶段 5） |
| 失败披露走 `notice`／`error` 帧不泄漏内部细节 | **无对应钉** → 红线锚 Owner 裁决 `walk/裁决表.md` §01-D；测试 `::no_internal_leak_in_frames` ＋ **人审** | 待实现 |
| 本块不含行为、不判语义、零模型 | AST 断言 `::no_judgement_or_model_in_transport` | 待实现（阶段 5） |
| 卡级修正（`EventBus` 形状／`SseEvent` 收正为帧对象） | **人审** | 原因：无「卡与规格一致」机检闸；本批已改卡并记施工流水 |
| 「不做什么」的纯范围排除（不判定发帧时机／不落盘／不渲染 HTTP） | **人审** | 接不上闸的原因：纯范围排除没有形状／存在性／退出码判据；能降维的部分（不引框架／引擎／模型出口）已由边界闸 R5b／R6／R7 覆盖 |
