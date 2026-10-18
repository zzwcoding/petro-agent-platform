• 两份代码核验回来了。我自己快速复核一个关键发现（生产 locator.kind 实际值域），然后读剩余小文件。

• 全部材料读完、代码论断已双代理核验并亲自复核关键疑点。以下为评审报告。

  ---

  ## 一、总裁定（成立 9／存疑 2／不成立 1）

  12 条裁定中 D-a/b/e/f/g/h/i/j/k 成立；D-c（方向对、数字与工勘错）与 D-l（自洽但越《清单》未标注）存疑；**D-d 不成立——它给出的「修正值域」本身与生产代码不符**。

  ## 二、D-a～D-l 逐条复核表

  | 裁定 | 判定 | 证据 file:line | 修正建议 |
  |---|---|---|---|
  | **D-a** 新建 `appv2/text_tokens.py` | **成立** | R6 source＝17 个 runtimev2 块、forbidden＝knowledge/query/retrieval、`allow_indirect_imports=true`（`tools/importlinter_v2.toml:109-114`）；`tools/__init__.py:65`→handlers→retrieval（`handlers.py:65,72`）成环属实；判据依赖仅字符集（`materials.py:222,224`） | 取①正确，优于②（迁 `_anchor_score` 需连 `_source_of:203`/`_content_length:376` 同迁，动 V2-90 已收面）与③（第二真源）。**补三点**：(i) 只下沉 `_boundary_hit:248`/`_num_token_hit:227` 两个纯判据，`_anchor_score` 留 L3；(ii) 新契约须禁其反向 import（防长成第二个 tools）；(iii) `appv2` 顶层新名须 Owner 点头（设计已报） |
  | **D-b** 不改帧、runner 取详情 | **成立** | `verification/core.py:709-715` rewrites 已落 StepRecord payload；`api/chat.py:365` `payload=step.payload` 属实；`graph.py:199-201` step 帧恰三键；`synth/S6:16` 明钉、`:53`「两面字段不同源…不得互推」 | 结论对。但 S6 自身已漂移（见 §八-3），帧闭世界地基须先修 |
  | **D-c** 默认档 `delete`＋conftest pin | **存疑（方向对、论据错）** | `test_v2_verification.py` 实 33 例（非票面「28」）；`test_v2_agent_verify.py` 22 例中 **约 19 例走旧 runtime** `appv2.runtime.graph.verify_draft`，断言退役前缀「未找到（材料未披露）：」（`:408/:651/:678`），V2-116 只动 runtimev2/verification → **不受影响**；真删行断言仅 `::test_unsupported_claim_rewritten:163-164` 1 例 | 真实敞口 ≈34 例（33+1），「55 例」高估约 21 例（既有评审称 55／我核为 34）。**conftest 现无任何 env pin 机制**（唯一 autouse fixture＝`_isolate_retrieval_calllog`），pin 须新建——两评审均未发现 |
  | **D-d** 值域改 `{metric,term,object,relation,family_annotation}` | **不成立** | 生产 locator.kind＝`{metric,term,object,relation,family}`（`knowledge/domain.py:28-32`，`KIND_FAMILY="family"`；`handlers.py:854` 直传 `evidence.kind`）。**生产无 `family_annotation`、亦无 `ledger`**；且 `materials.py:55` `_KIND_TRUST` 键 `family_annotation` 与生产 `family` 永不匹配（活缺陷） | 值域应改为**五 kind 实集**（family 非 family_annotation），并顺手修 `_KIND_TRUST:55` 键不匹配（族标注卡信任级正落默认）。两份评审都抄错值域（评审二称实点 `_KIND_TRUST:48-59`／我核为 :48-59 且键值错位属实，但把键当生产值） |
  | **D-e** NFKC 后判 ASCII `=` | **成立** | `normalize_for_match`（`rules.py:72`，NFKC）在零词表闸豁免单点名单（`test_v2_verification.py:1072-1080`）；闸咬四形：CJK 字面集合／非 ASCII 的 In/NotIn 字面／`re`/词面判方法（`:942-1091`） | 「NFKC 后 ASCII `=` 位点扫描」不触任何被咬形，可过闸。票面仍须禁 CJK 字面判据（既有评审 V13 判对） |
  | **D-f** reflect_subjects 调用点不跨相位 | **成立** | `execution/core.py:1178` 确为 append 调用点；R1 七相位互禁且 `allow_indirect_imports=false`（`toml:66-71`）⇒ execution 不得 import clarification；落 orchestration 调 clarification 抽取面合法 | 成立。票面边界红线（许动 clarification 抽取面）与裁定一致 |
  | **D-g** 时间量经注入参 | **成立** | `specs/context.md:110`「时间量不经本块（零时钟接触）」逐字在 | 评审一 S17 判对：注入参也是时间量经本块，**改规格逐字是硬前提**，D-g 已含，成立 |
  | **D-h** `quota_dropped` additive | **成立** | `over_budget` 置位仅三追加通道（`domain.py:793`）；余量步实存（`:764-772`）；设计伪代码确丢余量补给步与片段级去重上界 | 成立。补「片段级去重上界」必要，否则与 V2-86 单源上限冲突（评审二 #4 判对） |
  | **D-i** 兜底插在 `"\n".join` 之前 | **成立** | `verification/core.py:235` `text="\n".join(out_lines)` 逐字在 | 成立，修正了核设计 §2.6「收口处加闸」与代码不符处（评审二 #10 判对） |
  | **D-j** 常量名统一 `ANSWER_COVERAGE_*` | **成立** | 供设计 `COVERAGE_LINE`（供 §二 V2-119）vs 答设计 `ANSWER_COVERAGE_HEAD/LINE`（答 §二）确不一致 | 成立。**但注意**：D-j 只统一常量名，**未裁 V2-119 记号化第二真源**（`answering/core.py:266` vs `rules.py:82`）——评审一严重 #6（S13+P15）不在总方案 §二 8 条内，仍挂「余 12 条」，L0 漏裁（见 §七-严重 3） |
  | **D-k** 补 14 张票面 | **成立** | 实点 `tickets/v2/` 此段只有 V2-115..124；V2-100..113 恰 14 张无票面；114 并入 V2-122 票面标题 | 成立。AGENTS.md 6b 下 14 票不开工即 FAIL，裁定必要 |
  | **D-l** 采纳评审二 10 波 | **存疑** | 硬依赖边逐条核对自洽（116→{103,104,105,106,124核}、101→{121,124,109,122}、123→122、119→120、113→全批均满足）；但与《清单》§五三处偏离（100 与 119 次序、核验提前、116 默认值）评审二已自认 | 顺序本身可用；但三处偏离《清单》属改 Owner 已表态的顺序，总方案 §五「待 Owner 点头」未把这三条列入待确认——**应显式标注**，不算 L0 已授权 |

  ## 三、装配上下文最佳实践（逐条）

  | 实践 | 判定 | 证据 |
  |---|---|---|
  | 1 链只追加不改写 | **合规** | 118 改 `_HINT_LINE` 模板（`decision_round.py:140`）非改链机制；链追加形（`ports.py:110-118`）不动 |
  | 2 环节规章随请求（system 参）不入链 | **合规** | 120/109/124(作)/101/121① 全落 `constants.py` 族⑤⑥，经 `call_model(system=…)`（`answering/core.py:384`、`answer_round.py:86-102`） |
  | 3 user 位只放动态段 | **偏离（未修）** | V2-121② 静态「待核前提」句入 user 首入包（`_clarify_package`），而该函数自注「规章件不在本段」（`decision_round.py:449`）。评审一 P3 修法（移 `clarify_system_contract`）**未被票面/总方案采纳**，设计二 §三 row3 仍写「user 链」 |
  | 4 首入包一次性 | **合规** | `_clarify_package:438-460` run 内一次 |
  | 5 单点真源 | **风险×2** | (i) 119 记号化两处暂不同源（答 §七-2 自认）未裁；(ii) 122 `window_note_counts`＝第三计数面——`window_materials.rendered/total`（`materials.py:569-570`）＋`Verdict.delivered_rows/obs_rows`（`models.py:100-101`）已两面，须并键登记（评审一 S15 判对） |
  | 6 KV 前缀稳定 | **合规** | 三设计无 KV 改动 |
  | 7 token 预算与截断披露 | **合规** | over_budget 语义冻结（D-h）、披露行逐字零改（122 红线自述）；`SECTION_EXPAND_CAP:484` 复用 |

  ## 四、副作用与回归（含两份评审的漏项）

  **「≈40 例将破」核验**：核验面 33 例真实（collect 实测 33）；context 41 例（非设计一自报 35）且 `test_retention_normal_render_unchanged` 断言 `render_materials` 恰 3 参（`:2070-2096`）——122/123 加参必破，**设计漏报，评审二补上，判对**；`test_family_supply` 断言 `{"completion":3,"monthly":1}`（`:415`）必破 ✓；r1a 6 例名单全实，惟末者钉具体 id `f-cap-t3`（`:523`）非 `f-cap-t*`；prompts `lines[0]==_VERB_PIN`（`:794`）与 `count("；")==11`（`:439`）必破 ✓；state 56 字段（`:227`）＋INTENT 恰 11 值（`:535-547`）必破 ✓；react_loop `::test_consecutive_asks_capped_material_direct_answer:734` 必破 ✓。**两处高估/错记**：(i) agent_verify 22 例中 ~19 例钉旧 runtime 前缀，不在爆炸半径（§二 D-c）；(ii) `test_v2_v296_explore.py` 实 9 测（评审称 7）、`tests/tools` 实 108（评审称 103）。

  **冻结面核查**：披露行／三机检字段／`selected_reason` 三设计字面未碰 ✓；帧闭世界 D-b 保 ✓；`REWRITE_REASONS` 恰两值（`constants.py:35`）✓；`over_budget` 三通道置位（`:793`）✓；S5 字段矩阵 56 → 112/115/117/118 四票新增字段须同批 ✓（评审二已列）。

  **两份评审的漏项**：(1) conftest 无 env pin 机制（§二 D-c）；(2) runner `_steps` 取的是 `step` 键非 `title`（`runner.py:104`——核设计 §1 现状表写错，不影响结论）；(3) 票面行号系统性偏移 1–10 行（如 `over_budget` 793↔794、`_verify_lines` 票面写 :353 实为 :388），票面引用应锚函数名。

  ## 五、节序核验

  - **L1 供给**：✅。《流程》:13 L1 行已写「题眼锚/表格/原文候选先占预算→族配额→…（顺序以 §十二 D9 为准）」——设计一 §五自称的两处「真源不一致」**均不成立**（评审二 #1/#2 判对，设计一陈旧自报）。
  - **L3 渲染**：⚠️ V2-117 在 ⑤ 来源保底**之前**插主体保底席（`materials.py:452-457`）＝改序，《流程》§四无此节；D-f 只裁了 reflect 函数落点，**未裁这个插席**——L0 缺口。
  - **核验流水线**：✅ D-i 修正后与设计 §3.1「目标」一致；116 档位序（⓪档位→检测→标红→处置分叉）与代码 `_verify:207-341` 现状可对接。
  - **澄清流水线**：⚠️ 118「降级默认不占 ask_cap」落点未定——计数点 `_ask_count:831-845`，降级路径若过 `_on_ask` 会增计数（评审二 #13 判对，L0 未裁）。
  - **跨节遗留**：L1 `budget` 缺省 6 vs L3 cap＝`SEND_BUDGET_CAP` 24（`tools/schema.py:129`）两值两源，供 §六-7 已列、**D-a..D-l 未裁**。

  ## 六、与 EB11 证据自洽

  - **C3 8**：103 治 数-排1/SYS-1/数-察2/Q33（机制 1 实点 `:427-430`）；104 治 D-诱1（`number_tokens:82-109` 三形属实）；105 治 Q27；115/116 兜其余。**治不到：D-诱15**（题面给定值 40.2 参与计算被删——25 票无任何「题面给定值」豁免面，repair 档复检仍是确定性判据，照样咬）；Q38/Q42 删句空节（机制 1 型，103 应治，未复现，证据不足）。
  - **C1 23**：100 主刀＋117 加权＋119/120 激活 explore。**治不到/弱覆盖**：凡 L0 未召回者（池内未知，`EB11-核实.md` §④-5 自认不可确证）100 无能为力——NQ-C5/C7/C8/C10（完井册）、NQ-D7/D9 属此类高风险；**Q19**（`LIMIT 50` 截断，归因 S1-4 点名，无票）；**SYS-4**（`well_info` 数据面取数，无票）；**Q48**（仓外 CSV，池清单未落档）。
  - **C2 19**：100 治「同章异节」≥8；107 治 数-闸2/3；112 治 Q40/Q47/Q49；117 治 A-正6/NQ-M8 半面；122 治 A-正2 计数。**治不到：数-界1、Q17**（`LIMIT 50` 截断无票）；B-反2 机制未细分（证据不足）。
  - **C4 20**：110 治 7 题选项粒度；111 治 Q11/Q26/Q31/Q35/Q41；118 治 Q16＋29 次/22 题拒绝面；107 治 数-闸2/3、Q39 与 Q10/Q14 冒充面（只标红不删句，删句归 115）；112 治塌缩。**治不到/略过：Q15**（逻辑决定 L1 明示「略过」，挂待裁 #4）；Q01/Q06/Q34/Q37 分散行为缺陷无具名票。
  - **C5 13**：121＋124 治 Q45；123＋121 治 Q07；109 治 Q44 半面；119/120 治 Q13。**治不到：NQ-D10**（反题红线边缘「−42.6×0.89≈−37.9 万吨」——核验对它放行，无票）、**Q23**（寒暄夹带能力清单，无票）、Q09/Q36（无具名票）、Q18/Q20（仅半覆盖）。

  ## 七、必须修正清单

  **严重**
  1. **D-d 值域改 `{metric,term,object,relation,family}`**（非 family_annotation），并修 `materials.py:55` `_KIND_TRUST` 键活缺陷（族标注卡信任级落默认 report，与「台账全量」规格相悖）——照现裁定施工 Q27 类仍被删。
  2. **V2-121② 移出 user 首入包**（落 `clarify_system_contract`），否则破「user 只动态段／规章不入链」，与 `decision_round.py:449` 自注直接冲突；评审一 P3 已有修法，票面未采纳。
  3. **V2-119 记号化单点补裁**（评审一严重 #6 漏出总方案 §二）：`answering:266` vs `rules.py:82` 暂不同源＝数值比对域两套，须裁下沉或登记带票号过渡。
  4. **先修 synth/S6 漂移**再据它钉帧闭世界：S6:12 仍写「9 类」、引 `appv2/runtime/events.py` 旧路径；实 `transport/constants.py:19-35` 十类（增 `supplement`）；`specs/transport.md` 并不自定形 step 键——D-b 方向对、地基松。
  5. **conftest env-pin 机制新建**（现无）；按实点把回归敞口写为 ~34 例（33+1），票面「28 例」改 33。

  **中**
  6. L1 budget(6) vs L3 cap(24) 同源裁定（供 §六-7 悬空）。
  7. V2-117 L3 ⑤前插主体保底席＝改序，L0 给一句口径（D-f 未覆盖）。
  8. D-l 三处偏离《清单》§五显式列入「待 Owner 确认」。
  9. V2-118 降级默认「不占 ask_cap」写明落点（`_ask_count:831-845`）。
  10. 执行日单一真源挂 V2-123/113：真机日志 §A 执行日两版并存（2026-10-08×210／2026-10-18×7，`EB11-臆造上下文归因.md` §五-5），两票都要消费它。

  **轻**
  11. 计数勘误：v296 实 9 测、tests/tools 实 108、r1a 末例钉 `f-cap-t3`、票面「28 例」→33。
  12. 各设计/票面行号系统性偏移 1–10 行，引用改锚函数名。

  ## 八、两份评审漏掉的点

  1. **生产 locator.kind＝`family` 非 `family_annotation`**（`knowledge/domain.py:32`）＋ `_KIND_TRUST:55` 键不匹配活缺陷——两份评审把 `_KIND_TRUST` 的键当成生产值域抄进裁定（§二 D-d）。
  2. **agent_verify 22 例的 19 例钉旧 runtime 退役面**（`tests/domains/test_v2_agent_verify.py:46` 起，`appv2.runtime.graph.verify_draft`，断言「未找到（材料未披露）：」前缀）——不在 V2-116 爆炸半径；「55 例将破」高估 21 例，且这 19 例本身是「两代运行面混测」的债务，应单独立票清理。
  3. **conftest 无 env pin 机制**：全仓 `VERIFY_ACTION` 仅 4 处、全在文档；pin 不是「加一行」是「新建机制」。
  4. **执行日双值**（10-08 vs 10-18 两版 §A 并存）未与 V2-123 执行日注入／V2-113 冻结日断言挂钩。
  5. **LIMIT 50 截断与题面给定值两个机制无票**：数-界1/Q17/Q19（归因 S1-4 点名「封顶前 50 行」）与 D-诱15（题面值 40.2）均无票覆盖。

  ## 九、给 Owner 的 3 条最关键结论

  1. **D-a/b/e/f/g/h/i/j/k 九个裁定站得住，10 波顺序自洽，可按波 0 开工——但先把 D-d 的值域改对**（`family` 非 `family_annotation`）：这是唯一一条「按裁定施工仍治不好目标题（Q27）还会踩活缺陷」的裁定，且两份评审都没发现。
  2. **两份评审在测试面计数上系统性偏差**：「55 例将破」实为 ~34 例（19 例测的是旧 runtime 退役面），conftest 连 env pin 机制都不存在——D-c 的方向（默认 delete＋pin）是对的，但票面验收数字与工勘都得重写，否则施工子代理按错误清单回归。
  3. **与 EB11 对账：25 票接得住 C2/C3 的大头，但 C1 的 23 题里凡「L0 未召回」者 V2-100 无能为力，另有 D-诱15、数-界1/Q17/Q19、SYS-4、NQ-D10、Q23、Q15 至少七处缺陷无票覆盖**；EB12 出口闸「❌ 下降」大概率达标，「零交付=0、编造=0」则系于全批唯一 LLM 入环票 V2-115 的质量——它是波 3 最高风险票，建议在 observe 档先跑一轮 EB12 拿足「本应回炉」清单再开 repair。

