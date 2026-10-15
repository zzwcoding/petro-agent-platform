# transport 规格回工补写（2026-10-15，复审⑥）

- 依据：独立复审⑥判 `specs/transport.md` **FAIL**——wire 帧 `id` 语义两可（行为 4「id＝当前游标值／＝cursor」与行为 5「cursor＝下一帧 seq、`cursor = id + 1`」不能同真，wire 帧 id 回送会跳帧）；主窗已裁 **a 案**：wire 帧 `id` 定义为「**最后已消费事件 seq**」（事件帧 id＝该事件自身 seq），`cursor = id + 1` 对两类 id 一致成立。
- 范围：只改 `specs/transport.md`（本文件是修改点台账）；不碰其他文件（另一代理正在改相位规格与 gateway_adapter/bookkeeping）。不 git commit。
- 闸验证：`uv run python tools/check_specs.py`＝**PASS（0 警告）**；`uv run python tools/ref_resolvable.py check`＝**绿（20 份规格可解析）**。

## 修改点清单

| # | 落点 | 改前 → 改后 | 对应 finding |
|---|---|---|---|
| 1 | `specs/transport.md:82`（行为 4 重写） | 原「wire 帧 id 写作**当前游标值**（即紧随其后会被消费的下一个 seq，与 cursor 同义）」→ 按 a 案改写：事件帧 `id`＝该帧自身 `seq`；wire 三帧不推进事件游标，其 `id` 写作**最后已消费事件 seq**（尚未消费任何事件时＝**-1**）；断言同步为「wire 帧 id＝最后已消费事件 seq（尚未消费任何事件时＝-1）且不改变游标」——旧「id＝下一帧 seq（=cursor）」表述全删 | **主裁 a 案（FAIL）** |
| 2 | `specs/transport.md:83`（行为 5 补句） | 公式 `cursor = id + 1` 不动；补「**该式对事件帧与 wire 帧两类 id 同式成立**（wire 帧 id＝最后已消费事件 seq，见行为 4；故断点无论落在事件帧还是 wire 帧，重连都从最后已消费事件之后续传，不漏不重）」；原括注「行为 4 的 `id` 即该帧 `seq`」收窄为「事件帧的 `id` 即该帧 `seq`」 | **主裁 a 案（FAIL）** |
| 3 | `specs/transport.md:110`（验收行同步） | 「信封 `id`＝事件游标；wire 帧不推进游标」→「信封 `id`：事件帧＝自身 `seq`、wire 帧＝最后已消费事件 `seq`（尚未消费任何事件时＝-1；不推进游标）」；测试标识 `::frame_id_equals_cursor` 不变 | 主裁自查项（验收行） |
| 4 | `specs/transport.md`（挂钩表游标行同步） | 「游标全流单调、`id`＝事件游标」→「游标全流单调；事件帧 `id`＝自身 `seq`、wire 帧 `id`＝最后已消费事件 `seq`（不推进游标）」——与行为 4/5、验收行三处同口径，不留第二说法 | 主裁自查项（同口径） |
| 5 | `specs/transport.md`（挂钩表新增 pin-04 行） | 新增「**发射 JSON 不进答案面的帧形面**：`emission_strip` 通知的帧形（`type` ∈ `NOTICE_TYPES` 闭世界、载荷恰三键）归本块；剥离行为面归 `specs/answering.md` 行为 11｜钉 **`pin-04`**（P0）；测试 `::notice_three_keys_closed_world`｜待织网（阶段 5）」——与 pin-09 帧面钩平行 | finding① |
| 6 | `specs/transport.md:52-55`（常量族注释两层混写） | 原「闭世界常量族（**本块唯一真源**）」而各行又写「真源 synth/S6」→ 改「取值真源逐族标注」：`EVENT_KINDS`／`WIRE_FRAMES` 各行标「取值真源 synth/S6 §一／§二」（不自封唯一真源）；`NOTICE_TYPES` 标「本规格自立：码面实测逐字列全」 | finding② |
| 7 | `specs/transport.md:62`／行为 7（`NOTICE_TYPES` 自立表述统一） | 「本规格立为本族唯一真源」→「本规格自立为该族取值真源（码面实测）」；行为 7「（二十二值，本规格为唯一真源）」→「（二十二值——本规格自立·码面实测）」 | finding② |
| 8 | `specs/transport.md:39`（`SseEvent.seq` 同名辨义） | `seq` 行补「——与载荷内步序号 `seq` 同名不同义（后者＝步记录序号，真源 `specs/persistence.md` `StepRecord.seq`；本字段真源＝本块行为 3）」——全流游标 vs 步序号，真源各指 | finding③ |
| 9 | `specs/transport.md:87`（行为 9 `error` 载荷定形） | 原「`error` 帧对外只出稳定话术」无键集 → 补「载荷**定形＝恰二键 `{code, message}`**（`code`＝稳定错误码；`message`＝稳定话术——话术约束另列：行为 14 ＋ Owner 裁决 `walk/裁决表.md` §01-D）」；断言补「载荷恰 `{code, message}` 二键」 | finding④ |

## 断线重连两例走通记录（主裁指定自查）

修复后依据：行为 3（`seq` 0 起、全流单调）＋行为 4（事件帧 id＝自身 seq；wire 帧 id＝最后已消费事件 seq，未消费任何事件时＝-1）＋行为 5（`cursor` 排他起点；`cursor = id + 1` 对两类 id 同式）。

- **例 1（新 run 首连）**：客户端开流 → 先收到 `session` wire 帧，其 `id`＝-1（新 run 尚未消费任何事件）→ 按行为 5 换算 `cursor = -1 + 1 = 0` → `stream(0)` 给出 `seq ≥ 0` 的全部帧 → **从 seq=0 开始**。不漏（首事件帧 seq=0 在后缀内）；不重（此前无已消费事件）。与 `EventBus.stream(cursor: int = 0)` 缺省值一致——客户端即使不回送 `Last-Event-ID` 也落在同一起点。**走通。**
- **例 2（消费至 seq=7 断开）**：客户端已消费至事件帧 seq=7，最后收到帧的 `id`＝7（事件帧＝自身 seq；若断开前恰有 wire 帧，其 id 亦＝7＝最后已消费事件 seq）→ 回送 `Last-Event-ID=7` → 换算 `cursor = 7 + 1 = 8` → `stream(8)` 给出 `seq ≥ 8` 的后缀 → **从 seq=8 续传**。不漏（seq ≤ 7 已消费、不必重投）；不重（seq=7 不再出现）。与 R-K-49「已收最大 seq ＋ 1」一致。**走通。**

两例共同结论：a 案下「wire 帧 id＝最后已消费事件 seq」使 `cursor = id + 1` 恒等于「最后已消费 seq ＋ 1」＝排他起点，客户端无论最后停在事件帧还是 wire 帧，公式不分型、重连不漏不重。

## 遗留与说明

1. **风险 1 的简写「一处编号＋`id`＝事件游标」保留未动**：该句是行为 3／4 对策的压缩引述（引号内为简写非逐字），事件帧 id＝自身 seq 在交付时点即游标值，语义仍真；未改以控制改动面。若主窗要求全篇换新口径，随下批一并改。
2. **`stream(cursor)` 对 wire 帧的重放面**：行为 5「给出 `seq ≥ cursor` 的全部帧」中 wire 帧不占 `seq`、`session` 帧由 api 流首恒发（T-P9a1-07）——wire 帧重放语义（重连流是否重发 done/error）本规格未显名，归 `api` 开流段；本轮未扩写（超出本 finding 面）。
3. pin-04 行为面的承接规格为 `specs/answering.md` 行为 11（发射剥离，泄漏=0）；本块只保帧形闭世界面，与该行不重复建钉。
