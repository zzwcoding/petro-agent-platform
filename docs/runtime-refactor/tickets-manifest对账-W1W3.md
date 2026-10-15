# 拆票 manifest 对账报告 —— W1–W3 半区

- **日期**：2026-10-16
- **范围（14 票）**：`RT-W1-01a/b-state`、`RT-W2-01a/b-persistence`、`RT-W2-02a/b-transport`、`RT-W2-03a/b-gateway_adapter`、`RT-W2-04a/b/c-prompts`、`RT-W3-01a/b/c-bookkeeping`（均在 `tickets/v2-refactor/`）
- **规格（6 份）**：`specs/state.md`、`persistence.md`、`transport.md`、`gateway_adapter.md`、`prompts.md`、`bookkeeping.md` ＋ `specs/modules.md` 对应卡
- **对照物**：`docs/runtime-refactor/eng/03-施工顺序与切换计划.md`（波序／依赖）、`eng/04-测试网设计.md` §三／§五、`eng/04a-应钉行为清单.md`（31 钉）
- **方法**：
  1. 逐规格解析「验收测试」表行与各票「票面对象」表行，脚本比对三列（验收标准文本／对应测试标识／规格源行号），并全量校验覆盖与去重；
  2. 逐规格解析「与闸的挂钩表」pin 行，核对在 14 票内的落点（-a 逐字转抄、其余票指针）；
  3. `eng/04` §三 盲区表归本半区块行逐行比对转抄票；
  4. 逐票清点「先读」份数；
  5. 逐票核对「前置／阻塞／被阻塞」字段与 `eng/03` §二波序；
  6. 每票抽 ≥3 条 `file:line` 引文（含代码锚）回读。

---

## 核对项 1 · 票面对象全覆盖 —— **PASS（全绿）**

脚本比对结论：每份规格「验收测试」表全行 → 该包各票「票面对象」表，合计＝规格表全行、零遗漏、零重复；验收标准文本、对应测试标识、规格源行号三列全部逐字一致（集合与文本比对）。

| 规格 | 规格表行数 | 各票覆盖 | 行号断点 | 结果 |
|---|---|---|---|---|
| state.md | 19 | -a：1–8、15、16（10 行）；-b：9–14、17–19（9 行） | -a :135–:142、:149–:150；-b :143–:148、:151–:153 | PASS |
| persistence.md | 20 | -a：1–5、9–12、15（10 行）；-b：6–8、13、14、16–20（10 行） | -a :165–:169、:173–:176、:179；-b :170–:172、:177–:178、:180–:184 | PASS |
| transport.md | 18 | -a：1–10（10 行）；-b：11–18（8 行） | -a :106–:115；-b :116–:123 | PASS |
| gateway_adapter.md | 16 | -a：1–10（10 行）；-b：11–16（6 行） | -a :105–:114；-b :115–:120 | PASS |
| prompts.md | 23 | -a：1–8、16–18（11 行）；-b：9–15（7 行）；-c：19–23（5 行） | -a :110–:117、:125–:127；-b :118–:124；-c :128–:132 | PASS |
| bookkeeping.md | 23 | -a：1–10、20（11 行）；-b：13–17（5 行）；-c：11、12、18、19、21–23（7 行） | -a :126–:135、:145；-b :138–:142；-c :136–:137、:143–:144、:146–:148 | PASS |

合计 119 行规格验收行全部有落点，各包内 `-b/-c` 续用规格表行序不重编，行序缺口说明与 `#` 列一致。**无 FAIL。**

---

## 核对项 2 · pin 行分布 —— **FAIL（1 处逐字不一致）**

设计符合要求：6 份规格挂钩表的每条 pin 行在本半区 **恰出现一次**——由该包 `-a` 票「测试网钉」节逐字转抄，其余票（-b/-c）零 pin 行、只留归属指针。落点如下：

| 规格 | 挂钩表 pin 行 | -a 逐字转抄票 | 其余票 | 结果 |
|---|---|---|---|---|
| state.md（:186–:191） | pin-22／pin-23／pin-24／pin-26／pin-30／pin-29 | RT-W1-01a（6 钉） | RT-W1-01b 零钉、指针 | FAIL（见下 pin-30） |
| persistence.md（:217–:219） | pin-12／pin-28／pin-30 | RT-W2-01a（3 钉） | RT-W2-01b 零钉、指针 | PASS |
| transport.md（:158–:160） | pin-29／pin-09／pin-04 | RT-W2-02a（3 钉） | RT-W2-02b 零钉、指针 | PASS |
| gateway_adapter.md（:150–:152） | pin-25／pin-27／pin-28 | RT-W2-03a（3 钉） | RT-W2-03b 零钉、指针 | PASS |
| prompts.md（:163–:165） | pin-03／pin-13／pin-24 | RT-W2-04a（3 钉） | RT-W2-04b/-04c 零钉、指针 | PASS |
| bookkeeping.md（:180–:184） | pin-22（写入点单点面归属行）／pin-22／pin-24／pin-26／pin-12 | RT-W3-01a（5 行） | RT-W3-01b/-01c 零钉、指针 | PASS |

**eng/04a 31 钉归本半区块者的落点核对（全部有落点）**：pin-03→RT-W2-04a；pin-04→RT-W2-02a；pin-09→RT-W1-01a（字段面）＋RT-W2-02a（帧面）；pin-12→RT-W2-01a（落盘面）＋RT-W3-01a（承接面）；pin-13→RT-W2-04a；pin-22→RT-W1-01a（字段面）＋RT-W3-01a（写入面）；pin-23→RT-W1-01a；pin-24→RT-W1-01a＋RT-W3-01a＋RT-W2-04a；pin-25→RT-W2-03a；pin-26→RT-W1-01a＋RT-W3-01a；pin-27→RT-W2-03a；pin-28→RT-W2-01a＋RT-W2-03a（state 字段面经 RT-W1-01a 分工注）；pin-29→RT-W2-02a＋RT-W1-01a；pin-30→RT-W2-01a＋RT-W1-01a。pin-09／pin-15／pin-28 的 state 字段／参数键面在 RT-W1-01a 以「钉的字段面分工」注承接（非挂钩表行）。**无悬空。**

### FAIL 明细

| 票名 | 位置 | 期望（规格现文逐字） | 实际（票面逐字） |
|---|---|---|---|
| `RT-W1-01a-state.md` | 第 52 行「测试网钉」第 5 条 pin-30 | `specs/state.md:190` 现文末尾为：**「…`compaction 半面`归 `context`（`synth/S1` H6／V2-79d）——**已登记于 `specs/context.md` 行为 9**（2026-10-16 收词：原「该规格尚未定稿，**待 `context` 规格（窗 B 编写）定稿时登记**」系时点表述，已过时——context 已定稿并登记）」** | 票面仍作：**「…`compaction 半面`归 `context`（`synth/S1` H6／V2-79d）——该规格尚未定稿，**待 `context` 规格（窗 B 编写）定稿时登记**」** |

- 性质：`specs/state.md` 的 pin-30 行于 2026-10-16「收词」更新（加登记状态、判原表述过时），票面 `RT-W1-01a-state.md` 的逐字转抄**未同步**——违反逐字稿纪律（AGENTS.md 6b「每行均为所引规格表行原文照抄」）。
- 处置方向（供主窗）：回填 RT-W1-01a 第 52 行为 `specs/state.md:190` 现文逐字；或由主窗裁「票面是否随 context 定稿补登」。**不改规格、不改票面，本次只登记。**

---

## 核对项 3 · 织网义务（eng/04 §三 归本半区块行）—— **PASS**

`eng/04-测试网设计.md` §三 盲区表归本半区块的行：B1（bookkeeping）、B3（限额半行→state -b）、B5（transport -a）、B7b（gateway_adapter -a）；persistence／prompts 无明写行。各行**恰一票逐字转抄**、其余票只留指针：

| eng/04 §三 行 | 逐字转抄票 | 其余票指针 | 转抄比对 | 结果 |
|---|---|---|---|---|
| B1（公共位与结果归一＝`bookkeeping`） | RT-W3-01a（:81） | RT-W3-01b（:62）、RT-W3-01c（:65） | 与 eng/04:29 逐字一致 | PASS |
| B3（H8 预算四限额边界） | RT-W1-01b（:67） | RT-W1-01a（:77 指针）、RT-W3-01b（:61）、RT-W3-01c（:67） | 与 eng/04:32 逐字一致 | PASS |
| B5（帧协议级时序） | RT-W2-02a（:76） | RT-W2-02b（:64） | 与 eng/04:34 逐字一致 | PASS |
| B7b（429 重试旧钉改写） | RT-W2-03a（:79） | RT-W2-03b（:63） | 与 eng/04:36 逐字一致 | PASS |
| 无 persistence 行（事实） | RT-W2-01b（:69 照实写） | RT-W2-01a（:71 指针） | 与 §三表逐行核对一致 | PASS |
| 无 prompts 行（事实） | RT-W2-04a（:79 照实写） | RT-W2-04b（:65）、RT-W2-04c（:63） | 与 §三表逐行核对一致 | PASS |

**无 FAIL。**

---

## 核对项 4 · 先读份数（每票 ≤6；AGENTS.md 6b 常驻不计）—— **PASS**

| 票 | 票面声明 | 实点份数 | 结果 |
|---|---|---|---|
| RT-W1-01a-state | 4 | 4 | PASS |
| RT-W1-01b-state | 5 | 5 | PASS |
| RT-W2-01a-persistence | 5 | 5 | PASS |
| RT-W2-01b-persistence | 4 | 4 | PASS |
| RT-W2-02a-transport | 5 | 5 | PASS |
| RT-W2-02b-transport | 4 | 4 | PASS |
| RT-W2-03a-gateway_adapter | 6 | 6 | PASS |
| RT-W2-03b-gateway_adapter | 5 | 5 | PASS |
| RT-W2-04a-prompts | 6 | 6 | PASS |
| RT-W2-04b-prompts | 4 | 4 | PASS |
| RT-W2-04c-prompts | 3 | 3 | PASS |
| RT-W3-01a-bookkeeping | 5 | 5 | PASS |
| RT-W3-01b-bookkeeping | 6 | 6 | PASS |
| RT-W3-01c-bookkeeping | 5 | 5 | PASS |

全部 ≤6，票面声明份数与实点一致。**无 FAIL。**

---

## 核对项 5 · 阻塞链 —— **PASS**

**包内（-b/-c 前置＝上一子票收票）**：state（-b←-a）、persistence（-b←-a）、transport（-b←-a）、gateway_adapter（-03b←-03a）、prompts（-04b←-04a，-04c←-04b）、bookkeeping（-01b←-01a，-01c←-01b）——各票「前置」「阻塞」字段均明写，且与「同包顺序施工、同包不并行」一致。

**包间（W1→W2→W3）与 `eng/03` §二波序一致**：

| 票 | 波次前置（票面） | eng/03 §二 波序 | 结果 |
|---|---|---|---|
| RT-W1-01a/b | 无（W1 首波） | W1＝state | PASS |
| RT-W2-01a/b、RT-W2-02a/b | W1 state 收波 | W2＝parsing/prompts/transport/persistence/gateway_adapter（依赖 state/infra） | PASS |
| RT-W2-03a/b | W1 state 收波（注：依赖图 gateway_adapter→infra，波次归 W2 不变） | 同 W2 | PASS |
| RT-W2-04a/b/c | W1 state 收波（经 -a/-b 传递） | 同 W2 | PASS |
| RT-W3-01a/b/c | W2 全收波（经 -a/-b 传递） | W3＝context/bookkeeping/gate | PASS |

- 说明（非 FAIL、留痕）：`eng/03` §一依赖图 gateway_adapter 仅依赖 `infra`（不依赖 state），三张 gateway_adapter 票均已在「前置」字段显式登记该差异并保 W2 波次归属——与 §二波序不冲突。

**无 FAIL。**

---

## 核对项 6 · 规格引文真实 —— **PASS**

每票抽样回读 ≥3 条引文（施工要点 file:line 锚＋结构锚＋代码锚），逐条核对目标行内容与票面表述相符。抽检摘要：

| 票 | 抽检引文 | 回读结果 |
|---|---|---|
| RT-W1-01a-state | `specs/state.md:110`（行为 4 messages 只追加）、`:120`（行为 14 受理互斥）、`recon/I2a` 八类形状 | 目标行内容相符 |
| RT-W1-01b-state | `specs/state.md:116`（行为 10 限额键集）、`:122`（行为 16 零判断）、`recon/K R-K-72…R-K-76` | 相符 |
| RT-W2-01a-persistence | `specs/persistence.md:138`（行为 1 三语义）、`:149`（行为 12 旧检查点）、`recon/J` 表事实 | 相符 |
| RT-W2-01b-persistence | `specs/persistence.md:142`（行为 5 审计四要素）、`:150`（行为 13 截断）、`:183`（行 19 边界集） | 相符 |
| RT-W2-02a-transport | `specs/transport.md:79`（行为 1 十二值）、`:85`（行为 7 通知闭世界）、`synth/S6` 九类三帧 | 相符 |
| RT-W2-02b-transport | `specs/transport.md:90`（行为 12 close）、`:92`（行为 14 不泄内部）、`:122`（行 17 边界集） | 相符 |
| RT-W2-03a-gateway_adapter | `specs/gateway_adapter.md:80`（行为 1 唯一出口）、`:86-87`（行为 6/7 重试分层）、`appv2/runtime/llm.py:47-49`（重试 env 现状锚） | 目标行 `GATEWAY_429_RETRIES_DEFAULT` 等相符 |
| RT-W2-03b-gateway_adapter | `specs/gateway_adapter.md:90-91`（行为 11/12 替身面）、`tests/runtimev2/test_gateway_adapter_fake.py` 看守件 | 相符 |
| RT-W2-04a-prompts | `appv2/runtime/orientation.py` `_ANSWER_REQUIREMENTS`(L282-290)、`answer_turn_preamble`(L295-300)、`specs/prompts.md:84`（行为 5） | 目标行逐字相符 |
| RT-W2-04b-prompts | `specs/prompts.md:86-89`（行为 7-10）、`appv2/runtime/graph.py L2394-2416`（增量条）、`L2706-2708`（问题组 JSON） | 相符 |
| RT-W2-04c-prompts | `specs/prompts.md:93-94`（行为 14/15）、`:101-102`（不降级节）、`orientation.py L223-228` | 相符 |
| RT-W3-01a-bookkeeping | `specs/bookkeeping.md:23-39`（十六项承接表）、`:96`（行为 1）、`recon/B1` | 相符 |
| RT-W3-01b-bookkeeping | `specs/bookkeeping.md:107-110`（行为 12-15）、`arch/P7a` A-P7a-37 红线 | 相符 |
| RT-W3-01c-bookkeeping | `specs/bookkeeping.md:105-106`（行为 10/11）、`:111-113`（行为 16/17/18）、`appv2/tools/schema.py` 预算公式锚 | 相符 |

结构锚（各票 `:31/:33/:34/:52` 接口定义、`:68-:75/:85-:92/:96-:103/:124-:129/:154-:159/:115-:120` 红线与不降级节）逐行回读亦相符。`appv2/runtime/graph.py:3483`（`subtask_failed` 字面）等代码锚点解析成功。**无 FAIL。**

---

## 总结论 —— **未清零（1 处 FAIL）**

- **核对项 1、3、4、5、6：PASS（全绿）。** 119 行规格验收行全覆盖、零遗漏零重复、三列逐字一致；pin 行与织网义务行分布正确；先读份数、阻塞链、引文真实性均通过。
- **核对项 2：FAIL 1 处。** 唯一问题＝`RT-W1-01a-state.md:52`（pin-30 行）的逐字转抄落后于 `specs/state.md:190` 现文（规格 2026-10-16「收词」增补了「已登记于 `specs/context.md` 行为 9」并判原「待定稿登记」表述过时，票面未同步）。

### 待办清单（交主窗裁决，本次不改）

1. **[必办]** 回填 `RT-W1-01a-state.md:52` 的 pin-30 行为 `specs/state.md:190` 现文逐字（含「**已登记于 `specs/context.md` 行为 9**（2026-10-16 收词：…已过时——context 已定稿并登记）」段），清零该项后本半区对账即全绿。
2. **[留痕，非缺陷]** gateway_adapter 三票「前置」已显式登记「eng/03 §一依赖图只依赖 infra、不依赖 state」的差异，波次仍归 W2——与 §二波序一致，无需改票，保留对账留痕即可。

（本报告只读核对产物，未改票面、未改规格、未 commit。）

---

## 清零注记（2026-10-16 收尾）

唯一 FAIL（RT-W1-01a-state.md:52 pin-30 行落后于规格现文）已按 `specs/state.md:190` 现文逐字回填（修正批执行、脚本校验剥标后与源行首格逐字一致）。**本半区对账全绿清零。**

