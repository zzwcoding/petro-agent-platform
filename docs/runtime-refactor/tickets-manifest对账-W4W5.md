# 拆票 manifest 对账 · W4–W5 半区

- 日期：2026-10-16 ｜ 范围：`tickets/v2-refactor/` W4–W5 票 ↔ 规格 understanding / clarification / tool_matching / preconditions / execution / answering / verification / agent-loop / gate（＋`modules.md` 对应卡、`transport.md` api 行）
- 方法：脚本逐行抽取规格「验收测试」表与票面对象表、按「规格源行」回比（逐字比对）；pin 行按「硬要求」文本唯一性核对；eng/04 §三 B 行按整行逐字比对；引文抽 3 条/票回读。
- **总结论（2026-10-16 收尾态）：全部 FAIL 已处置闭环，半区清零。**

## FAIL 处置台账（初核 6 项 → 全闭环）

| # | 严重度 | 问题 | 处置 |
|---|---|---|---|
| F1 | 高 | gate 全表 20 行＋pin-18／B4 无落点票 | ✅ 补拆：`RT-W3-03a/b-gate.md`（B4 归块转抄落 03a） |
| F2 | 中 | RT-W4-04 全 14 行源行 +1 | ✅ 修正批刷新（连施工要点/结构锚同源） |
| F3 | 中 | RT-W4-07a/b 全 18 行源行 +1 | ✅ 修正批刷新 |
| F4 | 中 | RT-W5-02 行 8/9/10 及 modules.md 锚引文过期 | ✅ 修正批按改批卡面重引（:606/:630/:612 等） |
| F5 | 中 | B4 归块票缺 | ✅ 同 F1 |
| F6 | 低 | W4-04/07 施工要点锚同源 +1 | ✅ 同 F2/F3 |

## 核对项结论

1. **票面对象全覆盖**：8 份规格 148 条验收行 ↔ 16 票——全覆盖、零遗漏、零重复、逐字一致（understanding 16／clarification 22／tool_matching 15／preconditions 14／execution 19／answering 22／verification 18／agent-loop 36）。gate 20 行经补拆由 RT-W3-03a/b 承接（见 W1–W3 半区报告）。W5-02 以规格原文行承载 12 行，9/12 初核命中＋3/12（modules.md 锚）经 F4 修正后全命中。
2. **pin 行分布**：各规格挂钩表 pin 行恰出现一次（主票转抄、其余指针）；补拆后 pin-18 落点＝RT-W3-03a；eng/04a 31 钉全有落点票。
3. **织网义务**：B2→W5-01a、B2b→W4-04 恰一票；B4→RT-W3-03a（补拆后）；B1/B3/B5/B6 为无明写块名关联行，各相关票按贡献面带「归块注／贡献面」声明引用（设计形态，主窗裁认可）。
4. **先读份数**：16 票全部 ≤6。补拆 6 票亦 ≤6。
5. **阻塞链**：块内 -b/-c 前置＝上一子票收票；W4→W5；W5-02 前置＝W5-01a/b/c；与 eng/03 §二波序一致。补拆后 W2＝五票（persistence/transport/gateway_adapter/prompts/parsing）、W3＝五票（bookkeeping a/b/c＋context a/b＋gate a/b）。
6. **规格引文真实**：修正批后全部锚回读命中。
7. **测试文件分配**：`tests/api/test_v2_asks.py` 6 用例归 W5-01 三票（3+3）、W5-02 不 claim；`test_v2_verification.py`（新建）vs `test_v2_agent_verify.py`（既有）边界不重叠；各新建测试文件单块单文件零重复 claim。
