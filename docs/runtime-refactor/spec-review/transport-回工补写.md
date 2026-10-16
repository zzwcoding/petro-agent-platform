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

## W3 前规格微修正批：`NOTICE_TYPES` 补全实测 7 值（2026-10-16，流水 53-C）

- 依据：`docs/runtime-refactor/00-决议与方法.md` 流水 53「**裁定 C＝`NOTICE_TYPES` 闭世界按实测全集补全**」——B5 golden 回放实测真帧流的 `notice.type` 取值面**大于**规格 22 值，越界 7 值（共 1028 帧，来源＝V1 `tools/query/gate` 通道），系现状真实语义、非编造。
- 范围：`specs/transport.md`（:55／:62／:85／:113／:133／:156）＋`appv2/runtimev2/transport/constants.py`（常量族取值，:23-59）＋`appv2/runtimev2/transport/frames.py:50`（越界文案计数）＋`appv2/runtimev2/state/constants.py:73`（跨块引用注计数）＋`tests/domains/test_v2_transport.py`（期望面）＋本记录；未 git commit。

### 改动

1. **规格表补 7 值**（`specs/transport.md:62`）：`blackbox_write_failed` 后增列 `window_note`｜`no_hit`｜`unbound_degrade`｜`freshness_block`｜`same_param_replay`｜`rebind`｜`schema_not_allowed`，并按派单补注逐字：「**2026-10-16 补全（流水 53-C）：真源＝B5 golden 回放 54444 帧实测（1028 帧越界取值），来源＝V1 tools/query/gate 通道**——补全前 22 值之**来源＝现状码面实测**：…」（后半为原句逐字保留）。
2. **条数口径 22 → 29**：规格六处（:55「29 值」、:62 表头「二十九值」、:85 行为 7 两处「二十九值」、:113 验收行、:133 风险 3、:156 挂钩表）；代码三处（`transport/constants.py:23` 块头注、`frames.py:50` 越界文案、`state/constants.py:73` 跨块引用注）。连带收词两处：:62「（码面实测）」→「（实测全集）」、:85「（本规格自立·码面实测）」→「（本规格自立·实测全集）」——原词只覆盖旧 22 值的来源，补全后应为实测全集。
3. **常量同步补值**（`appv2/runtimev2/transport/constants.py:23-59`）：`NOTICE_TYPES` 由 22 值长到 29 值，取值**照规格逐字**、顺序同规格表（7 值列尾并以注记行标明来源）；模块内无第二处取值（「闭世界只有一个常量族」纪律维持），`_FRAME_EVENTS`／`VERDICT_SUBTYPES`／`ASK_FRAME_KINDS` 及其它四族未动。
4. **测试期望同步**（`tests/domains/test_v2_transport.py`）：`_SPEC_NOTICE_TYPES`（:62-88）补 7 值；`::notice_three_keys_closed_world` 条数断言 `== 22` → `== 29`（:468，docstring :460 同步「二十九值」）；B5 golden 回放用例（:731-746）原「**越界真样本在场**」断言（`assert rejected_notice_types`）**失义**（补全后该回放再无被拒 notice），改写为正向断言「补全 7 值在真帧流实发且过闸」＋「零越界残留（`assert not rejected_notice_types`）」——即「照规格新表改测试期望」。

### 实测（本批自跑，非引用）

- `::test_b5_golden_frame_replay_protocol_timeline`：runtime 载体 **1031 件／55472 帧**。旧 22 值世界：**54444 帧过闸、1028 帧被拒**（明细：`window_note` 828／`no_hit` 93／`unbound_degrade` 63／`freshness_block` 29／`same_param_replay` 8／`rebind` 6／`schema_not_allowed` 1）——与流水 53 的「54444 帧／1028 帧越界」两数**逐字吻合**（54444＝旧世界过闸量）。
- 补全后：**55472 帧全过闸、被拒计数为空**（真帧流与闭世界对齐，行为 7 无残余越界）；7 值在真帧流**实发**（`accepted_notice_types ⊇ {window_note, no_hit, unbound_degrade, freshness_block, same_param_replay, rebind, schema_not_allowed}`，回放用例已钉为断言）。

### 闸与验证（本批实跑）

```
$ uv run python -m pytest tests/domains/test_v2_state.py tests/domains/test_v2_transport.py -q
                                              38 passed in 1.67s                  exit 0
$ uv run python -m pytest -q（全量，排除 3 个 real smoke 文件）
                                              1910 passed, 105 skipped in 77.78s  exit 0
$ uv run python tools/check_specs.py          → spec gate: PASS（0 警告）          exit 0
$ uv run python tools/ref_resolvable.py check → 真源引用可解析闸绿：22 份规格可解析 exit 0
$ uv run lint-imports ／ uv run lint-imports --config tools/importlinter_v2.toml
                                              6 kept,0 broken ／ 18 kept,0 broken  exit 0
$ uv run ruff check app appv2 tests migrations tools（本批涉及文件）  → All checks passed  exit 0
$ uv run mypy app appv2                      → Success（195 source files）        exit 0
```

### 遗留与说明（非本批面）

1. **派生视图待同步（讲释层，Owner 亲产面）**：`docs/runtime-refactor/explain/transport-讲释.md:56` 仍逐字列 22 值与「二十二个取值…二十二个合法值」——该层自声明「规格改，本文即废」，随派生视图节奏同步（本批未动讲释层）。
2. **已收票历史引文**：`tickets/v2-refactor/RT-W2-02a-transport.md:38／65／86` 的施工基准行仍作「二十二值」（该票 W2 已收）；已收票面属历史记录，本批未回改。
3. **`specs/modules.md` 卡面**：`## transport` 卡注释只以符号名引 `NOTICE_TYPES`、不带条数（:470），故本批无须改卡；条数口径只在规格表与常量注释处维持。
