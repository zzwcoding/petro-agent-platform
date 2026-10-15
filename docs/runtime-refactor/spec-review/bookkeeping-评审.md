- 日期：2026-10-15 ｜ 状态：**评审发现清单（待 L0 逐条处置）**
- 被评对象：`specs/bookkeeping.md`（`状态: 草稿`）＋ 同批 `specs/modules.md` `## bookkeeping` 卡级修正（施工流水 32）
- 本清单只产发现，不修改任何现存文件。凡断言「X 不存在／X 与 Y 不一致」均附实读行号或 `grep`／实跑证据；未证实的怀疑写成「疑点」。

## 一、结论摘要

1. **版式骨架合格**：十节齐、标题逐字、顺序正确（`grep -n "^## "` 得 10 节，与 `docs/spec-format.md` §二之二 逐字一致）；行为约定**无**含糊词（`grep -nE "尽量|合理|必要时|视情况"` → exit 1，0 命中）；「不做什么」7 行俱带「由谁承担＋锚点」；验收测试 20 行全绑测试标识，【边界集】（`:120`）／【保留集】（`:121`）两行俱在。**三道闸亲跑全绿**（见 §四）。
2. **一处「高」（`StepRecord` 形状与已定稿 `persistence` 硬冲突）**：规格自称 `StepRecord` 形状真源＝`specs/persistence.md` 接口定义（`:56`），接口 `record_step(...) -> StepRecord`（`:39`）；但行为 3（`:75`）称 `record_step` 产出 `{seq, step, status, title, manifest, payload}` **恰六键**——而 `specs/persistence.md:64-71` 的 `StepRecord` **恰七字段（含 `run_id`）**。同名的两个形状一处要求 7、一处要求 6，`run_id` 缺席（**B-1**）。
3. **四中**：① 「框架与依赖红线」写「**依赖只许两处**（`state`＋`gateway_adapter`）」＋降维「AST 断言 import 只出现这两块」（`:67`），但同规格 `接口定义` 返回 tools 的 `ToolContext`（`:52`）、`StepRecord`（persistence，`:39`）、`NOTICE_TYPES`（transport，`:56`），且 `依赖与风险` 行自列五处依赖（`:127`）——红线、依赖行、卡面三者互不一致，AST 断言按字面不可实现（**B-2**）；② `specs/tools.md` **不载**送窗预算数值（行为 15／依赖行称其真源，`:87/:127`），实读 `tools.md`（67 行）仅一次出现 `ToolContext` 名（`:28`）、无预算内容（**B-3**）；③ `record_step` 的 `status` 判定机制未落点——签名（卡＋规格）无 `status` 参，却称「由入参判」（`:57/:75`），行为 3 的「失败步 `status="failed"`」断言**无法构造**（**B-4**）；④ 钉 `pin-26`（对话层纯度）的**写入面**＝本块 `append_dialogue`（行为 8，`:80`），挂钩表却只登 `pin-22`／`pin-24`／`pin-12`，`pin-26` 写入面漏登（**B-5**）。
4. **四低**：卡注把 §四【结构-2】的字段四件混引两处（**B-6**）；来源行 `recon/H` 标注「并发写面」在 H 文件内无对应表述（**B-7**）；B1 公共位函数 `_user_turn` 承接/排除未登记（**B-8**）；`next_intent`（S5 列为共享写口）未进行为 1 的断言集（**B-9**）。
5. **计数**：**9 条**发现——`L0×0`／`高×1`（B-1）／`中×4`（B-2｜B-3｜B-4｜B-5）／`低×4`（B-6…B-9）。**卡级**：B-2（卡依赖只列 `state`＋`gateway_adapter`，欠 `tools`／`persistence`／`transport`）与 B-4（`record_step` 签名与「`status` 三值如实」不配套）属卡面欠账；**是否「卡须回阶段 2 改卡」见问答 12／16**（倾向：B-2 依 spec-process「依赖与卡不符→回阶段 2」触发）。

## 二、发现清单表

| 编号 | 严重度 | 发现 | 证据锚点 | 建议处置 |
|---|---|---|---|---|
| **B-1** | **高** | **`StepRecord` 形状两说、同名片面冲突**。规格接口 `record_step(...) -> StepRecord`（`:39`）且注「形状真源＝`specs/persistence.md` 接口定义」（`:56`）；行为 3 却称产出 `{seq, step, status, title, manifest, payload}` **恰六键**（`:75`）。实读 `specs/persistence.md:64-71`：`StepRecord` 有 **7 字段**，首字段即 `run_id: str`（`:65`）。六键与七字段不相容；`run_id` 是否随 `record_step` 产出（`state.run_id` 在场）规格未写。B1 现状 `R-B1-01` 的六键 dict 是**入 state 的旧形**（无 `run_id`），与 `persistence` 的**行投影形**不是同物，规格把两者并成了一个名字。 | `specs/bookkeeping.md:39,56,75`；`specs/persistence.md:64-71`（`:65` run_id）；`docs/runtime-refactor/recon/B1-公共位与结果归一.md`（R-B1-01，`:41`） | 二选一对齐：① 行为 3 改为「产出 `StepRecord`（七字段，含自 `state.run_id` 取的 `run_id`）」、删「恰六键」；② 或明写本块产**六键中间形**、`run_id` 落盘面由 `persistence` 补——但须与 `persistence.StepRecord` 的 7 字段无默认值相容（二者取一，禁两说并存） |
| **B-2** | 中 | **依赖面自相矛盾＋降维 AST 断言不可实现**。「框架与依赖红线」（`:67`）写「**依赖只许两处**（`state` 形状／判定 ＋ `gateway_adapter` 模型出口）」，降维面＝「AST 断言「import 只出现这两块」」；但同规格 `tool_context(state) -> ToolContext`（`:52`，tools 类型）、`record_step(...) -> StepRecord`（`:39`，persistence 类型）、`notice` 的 `type ∈ NOTICE_TYPES`（`:56`，transport 常量）；`依赖与风险` 行亦自列五处（`:127`：state｜gateway_adapter｜tools.md｜persistence.md｜transport.md）。① 红线（2）↔ 依赖行（5）**自相矛盾**；② 断言「import 只出现这两块」对 `ToolContext`（构造并返回）**必然 FAIL**；③ `specs/modules.md:347` 卡面依赖亦只列 `state`、`gateway_adapter`，而卡公开面自称 `tool_context(state) -> ToolContext`（`modules.md:340`）——**卡面依赖欠 `tools`／`persistence`／`transport`**；④ 「触及的模块」表（`:25-31`）列 5 块却**漏列 `tools`**（`tool_context` 返回其类型）。 | `specs/bookkeeping.md:25-31,39,52,56,67,127`；`specs/modules.md:340,347`；`appv2/tools/schema.py:70`（`ToolContext` 类） | 依 spec-process「依赖与卡不符→回阶段 2」：卡面依赖行补 `tools`／`persistence`／`transport`（或收窄为「仅类型/常量形状面」并显名）；规格红线改述为「运行逻辑只依赖 `state`／`gateway_adapter`；类型/常量形状引用 `tools`／`persistence`／`transport`」，并把 AST 断言白名单改为对应四类；「触及的模块」表补 `tools` |
| **B-3** | 中 | **「送窗预算数值真源＝`specs/tools.md`」不实（真源在代码）**。行为 15 写「送窗预算按**子问题数**取值（数值与公式真源＝`specs/tools.md`，本规格不复述）」（`:87`）；`依赖与风险` 行同（`:127`「`specs/tools.md`（`ToolContext` 与送窗预算数值真源）」）。实读 `specs/tools.md`（全 67 行）：**无「送窗／预算／budget」任何字样**（`grep` 零命中），仅 `:28` 一次出现 `ToolContext` **名**（调用签名，无字段定义）。真源实为 **`appv2/tools/schema.py:97-116`** 的 `SEND_BUDGET_PER_SUBTASK=6`／`SEND_BUDGET_CAP=24`／`resolve_send_budget`（B1 `R-B1-14` 逐条列值），`ToolContext` 字段定义在 `specs/modules.md:117`（`## tools` 卡）与 `appv2/tools/schema.py:70`。 | `specs/bookkeeping.md:87,127`；`specs/tools.md`（全 67 行，仅 `:28` 提及 `ToolContext` 名）；`appv2/tools/schema.py:70,97-116`；`specs/modules.md:117`；`docs/runtime-refactor/recon/B1-公共位与结果归一.md`（R-B1-14） | 改锚：送窗预算数值/公式锚 **`appv2/tools/schema.py` 的 `SEND_BUDGET_PER_SUBTASK`／`SEND_BUDGET_CAP`／`resolve_send_budget`**（或 `recon/B1` R-B1-14）＋ `ToolContext` 形状锚 `specs/modules.md` `## tools` 卡。**不得**把无该事实的 `specs/tools.md` 当作数值真源 |
| **B-4** | 中 | **`record_step` 的 `status` 判定机制未落点（断言不可构造）**。接口 bullet 写「`status` 由本块按**入参**判（`ok`｜`failed`｜`refused`）」（`:57`），行为 3 同（`:75`「由入参判」）；但 `record_step` 签名（卡＋规格）只有 `kind`／`title`／`payload`／`manifest`（`specs/bookkeeping.md:37-39`；`specs/modules.md:329`），**无 `status` 参数**——「按入参判」无参可判，若要由 `payload` 内容推断失败态则＝**程序替模型/业务判语义**（违总纪律与行为 17 零判断）。行为 3 断言「失败步的 `status="failed"`」**无法从签名构造**。卡注称「`record_step` 签名收正……且 `status` 三值如实」（`modules.md:344`），但签名与「三值如实」**不配套**。 | `specs/bookkeeping.md:37-39,57,75`；`specs/modules.md:329,344`；`docs/runtime-refactor/walk/判断归责表.md`；`docs/runtime-refactor/walk/00-设计总纲.md` §二 | 补齐机制二选一：① 卡与规格的 `record_step` 签名**补 `status` 参**（关键词、闭世界三值、越界抛错）；② 或明写 `status` 由哪个**结构入参**（非语义推断）决定并在行为 3 给可判规则与断言。卡面同步 |
| **B-5** | 中 | **钉 `pin-26`（对话层纯度）写入面漏登**。行为 8（`:80`）＝「对话层纯度：`append_dialogue` 的 `origin` 越界即拒；过程内容不得经该入口」——这正是 `pin-26` 的**写入面**；但挂钩表只登 `pin-22`（`:152`）／`pin-24`（`:153`）／`pin-12`（`:154`），**无 `pin-26`**。同款 `pin-22` 已按「写入点单点面」挂本块（`:151/:152`）＝先例：`pin-22` 三面（`state` 字段契约面／`bookkeeping` 写入面／`agent-loop` 循环行为面），`pin-26` 现分面为 `state` 字段面＋`understanding` 渲染面（`specs/state.md:189`），**写入面无人认领**（两头不认疑点）。 | `specs/bookkeeping.md:80,151-154`；`docs/runtime-refactor/eng/04a-应钉行为清单.md:35`（pin-26，P1）；`specs/state.md:189`（pin-26 字段面＋渲染面） | 挂钩表补一行：`pin-26`（P1）**写入面在本块**（`append_dialogue` 闭世界＋过程内容不入层），测试 `::dialogue_port_purity`；与 `state`（字段面）／`understanding`（渲染面）分面注清 |
| **B-6** | 低 | **卡注对 S5 §四【结构-2】的字段四件混引两处**。卡注（`modules.md:344`）与规格风险 1（`bookkeeping.md:129`）称「现状证据 `synth/S5` §四【结构-2】：`messages`／`steps`／`notices`／`next_intent` 几乎每个节点都写」。实读 `synth/S5:105`：【结构-2】原文＝「**`notices`/`steps`/`next_intent` 全节点共享写口**」（**无 `messages`**）；`messages` 出现在 **§二观察**（`synth/S5:86`「`notices`/`steps`/`next_intent`/`messages` 是全节点共享写口」）。四件字段取自两处（【结构-2】三件＋§二三件并集），卡注／风险行并成「§四【结构-2】四件」。 | `specs/modules.md:344`；`specs/bookkeeping.md:129`；`docs/runtime-refactor/synth/S5-RunState字段矩阵.md:86,105` | 改准锚：或写「§四【结构-2】（`notices`/`steps`/`next_intent`）＋ §二观察（含 `messages`）」；或统一写「§二观察与§四【结构-2】」 |
| **B-7** | 低 | **来源行 `recon/H` 标注「并发写面」在 H 文件内无对应表述**。规格来源行（`:4`）写「`recon/H-观察核验作答与图装配.md`（**并发写面**）」。实读 H：`grep -n "并发"` **0 命中**；H 讨论的是 observe/verify/answer 三节点的读写面（如 `D-H-01`，`H:57`），无「并发写面」概念。共享写口/写手收敛的证据在 `recon/B1` §二观察与 `synth/S5` 第四节，不在此。 | `specs/bookkeeping.md:4`；`docs/runtime-refactor/recon/H-观察核验作答与图装配.md`（`grep "并发"` 0 命中；`:57` D-H-01） | 改括注（如「（节点写面/多节点同写面）」）或改锚 `recon/B1` §二观察／`synth/S5` §四 |
| **B-8** | 低 | **B1 公共位函数 `_user_turn` 承接/排除未登记**。判据 10 清单含 `_user_turn`（user 消息条目构造单点，`R-B1-23`／`D-B1-15`）。本规格承接口 10 个 B1 公共位函数中 9 个（见问答 10），唯 `_user_turn` **既无承接亦无排除说明**。B1 `D-B1-15` 记其「仓库级 grep 零调用点（appv2 与 tests 全域仅定义处）——V2-80h 链化后各节点内联 `{"role":"user",…}` 字面量，本函数是否为退役残留待裁」。 | `docs/runtime-refactor/recon/B1-公共位与结果归一.md`（§一 #13 `:21`；`D-B1-15` `:241-244`）；`specs/bookkeeping.md`（全文无 `_user_turn`） | 在「不做什么」或依赖/风险处**登记 `_user_turn` 去留**（退役＝旧码证据；承接＝`append_message(role="user")` 覆盖其形，明写一句） |
| **B-9** | 低（疑点） | **`next_intent`（S5 列共享写口）未进行为 1 断言集，归属未说明**。行为 1 断言「AST／grep 扫描——`state.messages`／`steps`／`process_notes`／`notices`／`dialogue` 的写操作只出现在本块」（`:73`）；但 `synth/S5:105`【结构-2】与 `:86`§二观察均把 **`next_intent`** 列为全节点共享写口。规格未说明 `next_intent` 的写口归属（是否随路由归 `orchestration`／各相位），亦未列入断言集——与「共享写口单点」主张存在覆盖面缝隙（疑点，未证实为缺陷）。 | `specs/bookkeeping.md:73`；`docs/runtime-refactor/synth/S5-RunState字段矩阵.md:86,105`（`next_intent` 共享写口） | 辨明并补一句：`next_intent` 的写口归谁（若归 `orchestration` 路由，写明「本块只写收敛/直答时的 `next_intent` 取值」并说明其余写点归属） |

## 三、16 问逐条回答

**1 十节齐＋标题逐字？** **无发现。** `grep -n "^## "` 得 10 节且逐字有序：`## 目标`(:7)／`## 不做什么`(:11)／`## 触及的模块`(:23)／`## 接口定义`(:33)／`## 框架与依赖红线`(:62)／`## 行为约定`(:71)／`## 不降级与静默禁令`(:91)／`## 验收测试`(:98)／`## 依赖与风险`(:125)／`## 与闸的挂钩表`(:140)——与 `docs/spec-format.md` §二之二（`:33-34`）逐字一致（节数＝10）。

**2 行为约定每条能否写成 `assert`／含糊词？** **无发现（含糊词）＋一处见 B-4。** 判 FAIL 的含糊词「尽量／合理／必要时／视情况」全文 **0 命中**（`grep` exit 1）；行为 1–17（`:73-89`）**每条**带【断言：…】形（AST 扫描／计数／抛错／键集合比较）。唯行为 3 的断言「失败步 `status="failed"`」因 `record_step` 无 `status` 参而**不可构造**（**B-4**）。

**3 数字有无裸值？** **有发现——B-1／B-3。** 计数项「恰六键」（`:75`，与 `persistence` 七字段冲突，B-1）；「恰三键」（`:82`）／「六键」（`:83`）自含可核；`next_seq`＝「已有步记录数＋1」（`:74`）为公式常量、非裸值；过程档案上限（行为 9，`:81`）**不复述数字**、指 S5 条目口径 ✔。**真源错锚一项**：送窗预算「数值与公式真源＝`specs/tools.md`」（`:87`）——`tools.md` 无该内容（B-3）。

**4 不做什么每条「由谁承担＋锚点」？** **无发现。** 7 行俱带：`:15`→`state`／`specs/state.md`；`:16`→`persistence`／`specs/persistence.md`；`:17`→`transport`／`specs/transport.md`；`:18`→`gateway_adapter`／`specs/gateway_adapter.md`；`:19`→`context`／`specs/modules.md ## context`；`:20`→各相位＋`orchestration`／`specs/agent-loop.md` 行为 1；`:21`→**不做**／`walk/判断归责表.md`。（`:20` 锚 `agent-loop` 行为 1（四相位循环），「该不该反问」的模型侧判据更贴行为 3；属锚精度、不单列发现，供 L0 参考。）

**5 框架与依赖红线：闸名真存在／source 真覆盖？** **闸名全部属实；含一处自相矛盾（B-2）。** 逐条实读 `tools/importlinter_v2.toml`：**R5b**（`:103` 的 `source` **含** `appv2.runtimev2.bookkeeping`）／**R6**（`:110` **含**）／**R7**（`:116` **含**，`forbidden=["appv2.infra.llm_client"]` `:117`）——三条**实跑 KEPT**（§四）；**R8**（`:122-123`）的 `source`＝`preconditions`／`verification`／`execution`，**不含** `bookkeeping`（规格未宣称其覆盖，无发现）。「无点名框架」（`:64`）写法合 §二。**唯**「依赖只许两处」＋降维 AST 断言与规格实际依赖面不符（**B-2**）。

**6 不降级与静默禁令？** **无发现。** `:93`「合法降级路径：**无**」（收敛＝有界终止、非降级）；三条「不许静默」（`:94` 触界不静默→行为 10／11 的断言；`:95` 记账不丢→行为 14；`:96` 不许自述完成→行为 11／13）均指到带【断言】的行为，红线锚 `arch/P7a` A-P7a-37。机读信号＋断言齐备。

**7 验收测试（每行标识／边界集保留集）？** **无发现。** 20 行**全部**绑 `tests/domains/test_v2_bookkeeping.py::<id>`（`:102-119` 18 行＋【边界集】`:120`＋【保留集】`:121`）；`:123` 注该件阶段 5 新建。**该件现不存在**（`ls tests/domains/test_v2_bookkeeping.py` → No such file），只能核标识形态、无法实跑（阶段 5）。

**8 与闸的挂钩表（填了没／接不上写原因／「已真跑」属实否）？** **已填；「已真跑」属实；一处行义见 B-2。** 表已填（`:142-159`）。`:144`「spec gate（**该闸只校这两项**——十节标题不在其作用面）」**诚实属实**（实读 `tools/check_specs.py`：只校 `## 触及的模块` 在册＋`## 验收测试` 绑定反引号标识＋状态取值，`:255,265,267,275`，**不校标题**）；`:147-149` R5b／R7／R6「已真跑」**由本子代理亲跑属实**（§四）；`:146`「真源引用闸」在 CI 属实。`:150`「依赖只许 `state`／`gateway_adapter`」——即 B-2 的自相矛盾行。其余「无专属闸→人审＋原因」齐备（`:150/:158/:159`）。

**9 与 `walk/` 决策是否冲突？** **无发现。** 逐条比对：项目级裁决 #7（新建 `appv2/runtimev2`，`裁决表:18`）✔；#4（现状缺陷只作现状证据，`裁决表:15`）→ 规格风险 2/3/4/5/9 把现状缺陷（恒 `ok`／`or{}` 归一／手工偏移／二次收敛／`detail` 归 None）作**现状证据**登记 ✔；#12／#13（语义交模型、程序只分派）→ 行为 17 零判断 ✔；`判断归责表.md`「收尾·完成判定＝程序」（`:23`）＋「语义交模型」→ 不降级「不许自述完成」（`:96`）✔；`walk/00-设计总纲.md` §二 总纪律（`绝不拿规则/词表替模型判语义`）→ 行为 17 ✔；`裁决表.md` §06-A（预算/收敛）→ 行为 11 收敛落地 ✔。本块**零判断面**，未见与任一裁决冲突。

**10 覆盖（B1 公共位函数逐条）／有无越界？** **有发现——B-8／B-9；其余 9 函数承接正确、无越界。** 逐条对照 `recon/B1` 公共位：`_step_record`→`record_step`✔｜`_next_seq`→`next_seq`✔｜`_converge`→`converge`（落地六键，判定归 `state.check_limits`：`：47/:83`）✔｜`_gate_or_none`→**正确排除**（入口闸判定归 `state.check_limits`，落点在 `：47/:83`；规格未把入口闸判定揽进本块）✔｜`_ctx_of`→`tool_context`✔｜`_result_dict`→`result_projection`✔｜`_direct_answer`→`direct_answer`✔｜`_note`＋`_notes_with`→`note`（构造＋只追加并一入口）✔｜`_user_turn`→**未承接亦未排除**（**B-8**）。**越界**：未见把别块的事写进来（判定归 `state`、落盘归 `persistence`、发帧归 `transport`、相位判断归各相位——均作边界标注）。**另核 S5 §四**：【结构-2】＝共享写口无归属（本块主证据，被承接）✔；【结构-3】＝M2 澄清写手 24 字段（属 `clarification`，**本块正确未揽**）✔。

**11 总纪律残留（程序替模型判语义）？** **无发现。** 行为 17（`:89`）明文「本块零判断：除 `call_model` 的转发与两侧闭世界分派外，无词表／正则语义判定」；行为 8 的「过程内容不入层」靠 `origin` 闭世界（调用方给值、越界即拒）而非词表判据；hit 面未见「若出现 X 词就 Y」形设计。

**12 与模块卡一致（职责／公开接口／依赖）＋卡级修正自查？** **有发现——B-2／B-4／B-6。** **一致项**：职责 `:9`↔卡 `modules.md:323`（逐项对上：步记录/序号/对话链与对话层/过程档案/通知/触界收敛/完成收口/调模型单点/工具上下文/结果投影）；**公开面 11 成员逐字对得上**（规格 `:37-53`↔卡 `:329-341`：`record_step`／`next_seq`／`append_message`／`append_dialogue`／`note`／`notice`／`converge`／`direct_answer`／`call_model`／`tool_context`／`result_projection`，签名与取值一致，规格补类型注解）。**卡级修正自查**（卡注 `modules.md:344`）：四类共享写口补全（`append_message`／`append_dialogue`／`note`／`notice`）＋`direct_answer`＋`result_projection`＋`record_step` 签名收正——**逐字与规格对上** ✔；`converge` 归属收正为落地写口（判定归 `state.check_limits`）✔。**唯**：① 卡面**依赖欠三块**（`tools`／`persistence`／`transport`，卡 `:347` 只列 `state`／`gateway_adapter`，而卡公开面自称返回 `ToolContext`／`StepRecord`）——**B-2**；② `record_step` 签名**无 `status` 参**却称「`status` 三值如实」——**B-4**；③ 卡注对 §四【结构-2】字段四件**混引两处**——**B-6**。**卡注补全理由（S5 结构-2）成立性**：**方向成立**（【结构-2】确实记「共享写口无归属单点」，支持补写口），**但字段映射loose**（【结构-2】列三件、本块补的四类与之不完全重合，且 `next_intent` 未覆盖，见 B-6／B-9）。

**13 接口与已定稿规格逐字对账？** **有发现——B-1（①）；② ③ ④ ⑤ 一致。** ① `StepRecord` ↔ `specs/persistence.md`：**不一致**（本块六键 vs persistence 七字段含 `run_id`）——**B-1**。② `NOTICE_TYPES` ↔ `specs/transport.md`：规格 `:56/:82` 称 `type ∈ NOTICE_TYPES`（真源 transport），`transport.md:55/:62/:85` 立为二十二值唯一真源——**一致**。③ `state.check_limits`（`state.md:87`）／`Manifest.as_dict`（`state.md:51`，全键恒出 `行为 15`）／`STEP_KINDS`（六值，`state.md:90`）／`RUN_STATUS_KINDS`（四值，`state.md:90`）引用——**一致**（规格 `:47/:75/:77/:127`）。④ `append_dialogue` 的 `origin` 三值（`user_verbatim`｜`assistant_final`｜`clarify_approval_replay`，`:56`）↔ `state.md:112` 行为 6 **逐字一致**。⑤ `call_model` 桥接口径 ↔ `gateway_adapter.md` 行为 1（`:79`「从状态取 `run_id`→调 `complete`→向节点只回 `content`，回执用量/归因交 `bookkeeping` 记账」）——本块行为 14（`:86`）**逐字一致**。**处置建议**：五处中唯一需动的是 ①，且 `persistence` 为**已定稿**，应改本块（B-1 建议①②）而非私改 `persistence`。

**14 钉登记（全表扫 `eng/04a`）？** **有发现——B-5（漏登）。** ① **同物核对**：`pin-22`（`04a:31`「`RunState.messages` 只追加不改写：相邻调用互为前缀延伸」）↔ 本块行为 6（`:78`「`append_message` 只追加不改写」）——**同物**（本块承**写入面**）；`pin-24`（`04a:33`「相位合同一次性：`contracts_appended` 标记——回炉轮不重发」）↔ 行为 7（`:79`）——**同物**；`pin-12`（`04a:21`「verify 对账机读字段入 step payload」）↔ 行为 4（`:76`「`payload` 原样保真」）——**承（写入面）**。② **漏登核查**：**`pin-26`（对话层纯度）写入面＝行为 8，未登**——**B-5**；其余钉（`pin-01～pin-11`／`13～21`／`23`／`25`／`27～31`）主题在答案面/核验/前置/网关/时钟/归档等他块，**不应登本块**。③ **钉号/优先级**：`pin-22` **P0** ✔／`pin-24` **P1** ✔／`pin-12` **P1** ✔（与 `04a:31/33/21` 一致）。④ **分工面**：`pin-22` 清（本块＝写入点单点面｜`state`＝字段面｜`agent-loop`＝循环行为面）；`pin-24` 清（本块＝写入面｜`state`＝标记/字段面）；`pin-12` 清（本块＝承接写入面｜`persistence`＝落盘面｜`verification`＝字段面）；**唯 `pin-26` 写入面无人认领**（B-5）。

**15 真源引用真实存在且该节真有那条事实？** **有发现——B-3／B-7；其余属实。** **逐条核实**：`recon/B1` 的 **D-B1-01**（恒 `ok`，`:44`）／**D-B1-02**（调用方手加偏移，`:58`）／**D-B1-03**（`toolmatch` 直调免幂等守卫，`:81`）／**D-B1-04**（前缀恒称「已取得材料未及核验」，`:82`）／**D-B1-13**（`detail` 空 dict 归 None 与「无 detail」不可分，`:199`）——**五条实存且与规格风险 2/4/5/6/9 所述同物** ✔；`synth/S5` §四【结构-2】（`:105`）／【结构-3】（`:106`）**实存**（字段四件锚偏见 B-6）✔；`walk/裁决表.md` §06（`:88-97`）实存 ✔。**不实／不符**：`specs/tools.md` **无送窗预算数值**（B-3）；`recon/H` **无「并发写面」表述**（B-7）。

**16 卡级问题（只报不改）？** **有发现，倾向触发「卡须回阶段 2」。** ① **卡面依赖欠账**（B-2）：`## bookkeeping` 卡依赖只列 `state`／`gateway_adapter`（`modules.md:347`），而卡公开面／规格实际引用 `tools`（`ToolContext`）／`persistence`（`StepRecord`）／`transport`（`NOTICE_TYPES`）——**依 spec-process「依赖与卡不符→停下回阶段 2 改卡」触发回阶段 2**（须补卡依赖行，或在规格收窄措辞并明标「仅类型/常量形状引用」，二者取一由 L0 定）。② **`record_step` 签名与「`status` 三值如实」不配套**（B-4）：协议要「三值如实」而签名无 `status` 参——属卡与规格**同缺**，改法要么补卡签名要么规格写实判定来源，亦触及卡面。③ 卡注 §四【结构-2】字段四件混引（B-6，卡面注记）。**职责／边界两面无卡错**（职责行与规格目标一致；边界方向：判定归 `state`、落盘归 `persistence`、发帧归 `transport` 与各卡不冲突）；**卡级修正（四写口补全／`converge` 落地归位／`record_step` 签名收正／`direct_call`＋`result_projection` 补入）本身自洽**，与 R5b/R6/R7 及 `state` 行为不冲突。

## 四、闸实跑记录（2026-10-15）

```
$ uv run python tools/check_specs.py
spec gate: PASS（0 警告）                                    # exit 0

$ uv run python tools/ref_resolvable.py check
真源引用可解析闸绿：19 份规格的真源引用与边界规则编号均可解析。   # exit 0

$ uv run lint-imports --config tools/importlinter_v2.toml
Analyzed ...（R1–R8、R5b、V2 B6 逐条 KEPT；含 R6／R7／R8）
Contracts: 18 kept, 0 broken.                               # exit 0
```

关键辅助取证：
- `grep -n "^## " specs/bookkeeping.md` → **10 节**、标题逐字有序（问答 1 依据）。
- `grep -nE "尽量|合理|必要时|视情况" specs/bookkeeping.md` → **exit 1（0 命中）**（问答 2 依据）。
- `grep -n "pin-" specs/bookkeeping.md` → 仅 `pin-22`／`pin-24`／`pin-12`（**无 `pin-26`**，B-5 依据）。
- `grep -n "送窗\|预算\|budget\|ToolContext" specs/tools.md` → 仅 `:28` 一处 `ToolContext` **名**（无预算字样）（B-3 依据）；`sed -n '97,116p' appv2/tools/schema.py` → `SEND_BUDGET_PER_SUBTASK=6`／`SEND_BUDGET_CAP=24`／`resolve_send_budget`（B-3 真源依据）。
- `sed -n '64,71p' specs/persistence.md` → `StepRecord` **7 字段**（首字段 `run_id`）（B-1 依据）。
- `grep -n "并发" docs/runtime-refactor/recon/H-观察核验作答与图装配.md` → **0 命中**（B-7 依据）。
- `grep -n "class ToolContext" appv2/tools/schema.py` → `:70`；`grep -n "ToolContext =" specs/modules.md` → `:117`（B-2／B-3 依据）。
- 逐 token 核 `tools/importlinter_v2.toml`：R5b（`:103`）／R6（`:110`）／R7（`:116`）的 `source` **含** `appv2.runtimev2.bookkeeping`；R8（`:122`）**不含**（问答 5 依据）。
- `ls tests/domains/test_v2_bookkeeping.py` → **No such file**；`ls appv2/runtimev2/bookkeeping/` → 仅 `__init__.py`（阶段 2 骨架，无实现）。

### 未验证清单

1. `tests/domains/test_v2_bookkeeping.py` **不存在**（阶段 5 新建）——20 行验收测试只能核标识形态，**无法实跑**。
2. `appv2/runtimev2/bookkeeping/` 仅有骨架 `__init__.py`（无生产实现）——R5a/R6/R7 等边界契约对本块为**契约空过**（契约存在且 KEEPT 已实测，实现层待阶段 5）。
3. **B-2** 的严重度取决于 L0 定性：若判「`tools`／`persistence`／`transport` 仅类型/常量形状引用、不算行为依赖」则可降为「规格红线措辞→人审」，否则维持「依赖与卡不符→回阶段 2」。
4. **B-4** 的修法（补 `status` 参 vs 写实判定来源）须 L0 定；本清单按「签名与『三值如实』不配套」维持中。

---

## 五、L0 处置表（逐条清零 · 2026-10-15）

> 规格文本由 **L0 直接落笔**；**卡级修正**（窗 A 权限）同批落 `specs/modules.md`（公开面签名＋依赖行）。

| 编号 | 处置 | 落法 |
|---|---|---|
| **B-1**（高） | **采纳（取建议①）** | 行为 3 改述为「产出 **`StepRecord` 七个字段**（`run_id` 自 `state.run_id` 取，**不由调用方传**；＋`seq`／`step`／`status`／`title`／`manifest`／`payload`）」，删「恰六键」；并写明「现状『入状态的六键 dict』不含 `run_id`——那是**旧形**（`recon/B1` R-B1-01），重写以 `specs/persistence.md` 的七字段为准」；断言改「键集合恒七＋`run_id` 与状态一致」；验收行与风险 2 的测试标识同步改名 `::step_record_all_fields_and_status` |
| **B-2**（中） | **采纳（三处同修）** | ① 红线改述：「**运行逻辑只依赖两处**（`state`／`gateway_adapter`）；**类型与常量形状**另引 `tools`／`persistence`／`transport`——只许引类型与常量，**不许引其行为**」，AST 白名单改为「这五块＋三处形状块只用于类型/常量」；② 「触及的模块」补 `tools` 行；③ **卡面依赖行补三块**（形状面）——并**踩了一次自己的老坑**：该行初稿把所有类型的反引号都写上，被 spec gate 判为「依赖未声明模块」（`ToolContext`／`StepRecord`／`NOTICE_TYPES`），已按「`- 模块:` 行只许反引号包模块名」修正后闸绿 |
| **B-3**（中） | **采纳** | 送窗预算数值/公式真源改锚 **`appv2/tools/schema.py`** 的 `resolve_send_budget` 与其配套常量；`ToolContext` 形状锚 **`specs/modules.md` `## tools` 卡**——删「`specs/tools.md` 是数值真源」（该规格无此内容，`grep` 零命中） |
| **B-4**（中） | **采纳（取建议①）** | `record_step` **签名补 `status` 关键词参**（闭世界 `ok`｜`failed`｜`refused`，缺省 `ok`，越界抛错）——卡与规格同批；接口 bullet 改述为「由**调用方如实给**，本块**不猜**、不从 payload 推断语义（守总纪律）」——「按入参判」这句误导性措辞删掉 |
| **B-5**（中） | **采纳** | 挂钩表补一行：**`pin-26` 的写入面在本块**（`append_dialogue` 的 `origin` 闭世界＋过程内容不入层，测试 `::dialogue_port_purity`），并注清分面（字段面→`specs/state.md`、渲染面→`specs/understanding.md`）——「两头不认」消除 |
| **B-6**（低） | **采纳** | 锚改准：`synth/S5-RunState字段矩阵.md` §四【结构-2】只列 `notices`／`steps`／`next_intent` 三件，`messages` 在 §二观察——两处分别标注，不再并成「§四【结构-2】四件」（卡注同批改） |
| **B-7**（低） | **采纳** | 来源行 `recon/H` 的括注由「（并发写面）」改为「（节点读写面）」（H 内无「并发」表述） |
| **B-8**（低） | **采纳** | 「依赖与风险」开头登记**旧码残留 `_user_turn` 的去留**：旧码已零调用点（`recon/B1` D-B1-15），重写**不承接**——其形由 `append_message(role="user", …)` 覆盖（行为 7） |
| **B-9**（低，疑点） | **采纳 → 辨明并补行为 6** | 新增**行为 6**「`next_intent` 的写口归属」：收敛（行为 12）与直答旁路（行为 14）两处的取值由本块写；**其余写点＝各相位自己的过相位结果**（每相位返回面携路由意图），**闭世界校验归 `orchestration` 的路由表**——本块不接管全量 `next_intent` 写入（S5 列的「共享写口」由此分工消解）；行为编号顺延（旧 6–17 → 新 7–18），全文「行为 N」引用一次性重映射并复核 |

**净结果**：9 条**全部采纳**（B-1 高；B-2／B-4 涉卡由窗 A 亲改；B-9 新增一条行为并全文重编号）。**无升 Owner 的业务裁决项**；**卡级欠账（B-2／B-4）已随批补齐**，无须另开阶段 2 轮次。

---

## 六、复审结论（独立子代理）

- 日期：2026-10-15 ｜ 状态：**复审（闭合核验 ＋ 判据 16 问复跑）**
- 复审对象：`specs/bookkeeping.md`（修订稿，`状态: 草稿`）＋同批 `specs/modules.md` `## bookkeeping` 卡（`record_step` 补 `status` 参／依赖行补三块形状面／卡注补理由）
- 纪律：**只读现存文件、只追加本件**；凡断言附实读行号／`grep`／实跑证据；未证实者标「疑点」。

### 6.1 闭合核验表（B-1…B-9）

| 编号 | 判定 | 证据（实读行号 ＋ 文本） |
|---|---|---|
| **B-1**（高） | **闭合** | ① 行为 3（`:77`）现文＝「产出 **`StepRecord` 的七个字段**——`run_id`（自 `state.run_id` 取，**不由调用方传**）＋`seq`＋`step`＋`status`＋`title`＋`manifest`＋`payload`」，与 `specs/persistence.md:64-71` 的七字段（`run_id/seq/step/status/title/manifest/payload`，同序）逐一对上。② 验收行 `:107`＝`::step_record_all_fields_and_status`；风险 2 `:134`＝同名——两处已改名。③ `grep -n "step_record_six_keys"` → **exit 1（零命中）**。④ `grep -n "六键"` 仅余 `:86`（行为 12「落地**六键**」＝converge 六键，另一物）与 `:115/:160` 的 `converge_lands_six_keys`（converge 测试名）——**非 B-1 面、无残留**。⑤ `StepRecord.status` 闭世界 `ok|failed|refused`（`persistence.md:69`）与行为 3 一致。 |
| **B-2**（中） | **闭合（四处口径一致）；挂钩表第五处残留另立 BZ-3** | ① 红线 `:69`＝「**运行逻辑只依赖两处**（`state`…＋`gateway_adapter`…）；**类型与常量形状**另引三处：`tools`／`persistence`／`transport`——只许引类型与常量，不许引其行为」，可降维面＝「AST 断言「import 只出现这五块」＋「三处形状块只用于类型/常量」」。② 触及的模块表 `:27-32` 六行、含 `tools`（`:30`，注「只引形状与数值，不走其行为面」）。③ 依赖行 `:131`＝state／gateway_adapter／`specs/modules.md ## tools` 卡＋`appv2/tools/schema.py`／`specs/persistence.md`／`specs/transport.md`。④ 卡面依赖行 `specs/modules.md:347`＝「模块: `state`、`gateway_adapter`（**运行逻辑**）；`tools`、`persistence`、`transport`（**类型与常量形状面**……只引形状，不许引其行为）」——**反引号只包模块名**（`ToolContext`／`StepRecord`／`NOTICE_TYPES` 均未入反引号）；`uv run python tools/check_specs.py` → **spec gate: PASS（0 警告）**（实跑，见 7.2）。四处对同一件事口径一致。 |
| **B-3**（中） | **闭合** | `grep -nE "tools\.md" specs/bookkeeping.md` → **exit 1（零命中）**。行为 16（`:90`）现锚「数值与公式真源＝`appv2/tools/schema.py` 的 `resolve_send_budget` 与其配套常量；`ToolContext` 的形状真源＝`specs/modules.md` `## tools` 卡」；依赖行 `:131` 同锚。实读 `appv2/tools/schema.py`：`SEND_BUDGET_PER_SUBTASK = 6`／`SEND_BUDGET_CAP = 24`／`def resolve_send_budget(subtask_count: int) -> int`（含「每子问题基线 6×子问题数、上限 24」同文注释）；`specs/modules.md:117`＝`ToolContext = {actor, budget, metric_candidates, approved_tables}`——两锚实存且含该事实。 |
| **B-4**（中） | **闭合** | ① 规格接口 `:38-41`＝`def record_step(state, *, kind: str, title: str, status: str = "ok", payload: dict[str, Any] | None = None, manifest: Manifest | None = None) -> StepRecord: ...`；卡面 `modules.md:329`＝`def record_step(state, *, kind, title, status="ok", payload=None, manifest=None) -> StepRecord: ...  # status 闭世界 ok/failed/refused（由调用方如实给，本块不猜）`——参数名／顺序／缺省值两处一致（卡面按既有风格不带类型注解）。② 接口 bullet `:59`＝「**`status` 是显式关键词参**（闭世界 `ok`｜`failed`｜`refused`，越界抛错；缺省 `ok`）——**由调用方如实给**（本块**不猜**、不从 payload 推断语义，守总纪律）」，措辞已按要求改。③ 误导性措辞「按入参判」`grep` → **exit 1（零命中）**。行为 3 的「失败步 `status="failed"`」断言（`:77`）现可构造。 |
| **B-5**（中） | **闭合** | 挂钩表 `:158` 新增行＝「对话层纯度（**写入面**：`append_dialogue` 的 `origin` 闭世界＋过程内容不入层）｜钉 **`pin-26`**（P1；字段面挂 `specs/state.md`、渲染面挂 `specs/understanding.md`）；测试 `::dialogue_port_purity`」。另两份文件核分面：`specs/state.md:189`（字段／形状面＋`::dialogue_layer_purity`，并注「渲染面同钉挂 `specs/understanding.md`」）与 `specs/understanding.md:133`（渲染／输出面，落点＝行为 9）——**三处各认一面，无冲突、无两头不认**；`pin-26` **P1** 与 `04a` 第 26 行（`04a:35` 行、优先级栏 P1）一致。 |
| **B-6**（低） | **未闭合（规格侧已改；卡面与流水未改）** | 规格侧已准：风险 1（`:133`）＝「§四【结构-2】列 `notices`／`steps`／`next_intent` 三件全节点共享写口，§二观察另把 `messages` 并列」——与 `synth/S5:105`（【结构-2】原文「**notices/steps/next_intent 全节点共享写口**」）、`synth/S5:86`（§二观察含 `messages`）对得上。**卡面注记未改**：`specs/modules.md:344` 仍写「现状证据 `synth/S5-RunState字段矩阵.md` 第四节【结构-2】：`messages`／`steps`／`notices`／`next_intent` 几乎每个节点都写、无归属单点」——四件仍并成 §四【结构-2】；**同款误引亦见施工流水** `docs/runtime-refactor/00-决议与方法.md:104`（流水 32）。L0 处置表「卡注同批改」**未兑现**。另注：该卡注称「四个共享写口没有承接函数」而补齐名单为「对话链／对话层／过程档案／通知四类」——**两名单不是同四件**（`steps` 本就有 `record_step`；`next_intent` 至今无承接函数），注记内部不自洽。 |
| **B-7**（低） | **闭合** | 来源行 `:4` 括注已改＝「`docs/runtime-refactor/recon/H-观察核验作答与图装配.md`（**节点读写面**）」。核 `recon/H`：`grep -c "并发"` → **0**；括注所指事实实存——`recon/H:282-284`「本段读写的 state 字段全集：读：… 写（经返回 updates）：…」＋`recon/H:21`（覆盖 observe/verify/answer 三节点）。字面「节点读写面」五字在 H 内无原文，属改写标签（概念对得上）。 |
| **B-8**（低） | **闭合** | 依赖与风险开头 `:130`＝「**旧码残留登记**：`recon/B1` 的 `_user_turn`（user 消息条目构造单点）在旧码里**已零调用点**（各节点内联 `{"role":"user",…}` 字面量——`recon/B1` D-B1-15）——重写**不承接该函数**：其形由本块 `append_message(role="user", …)` 覆盖（见行为 7）」。核 `recon/B1:21`（§一 #13 `_user_turn`）／`:232`（条目标题「对话链 user 消息条目构造」）／`:244`（D-B1-15 零调用点原话）——登记与现状证据同物。指向「行为 7」（`:81` 对话链只追加，正文含 `append_message`）成立（若并点接口 bullet `:58` 的 `role ∈ user｜assistant` 更精确，供参考、非缺陷）。 |
| **B-9**（低，疑点） | **闭合（原发现面：行为 6 在位、编号连续、引用全对）；新增行为 6 自带两条新问题（BZ-1／BZ-2）** | ① 行为 6 在位（`:80`）。② 编号 **1…18 连续无重号**（`grep -nE "^[0-9]+\. \*\*"` → `:75-92`，18 行，逐行为 1…18）。③ 全文「行为 N」引用 **14 处逐条对照全对**（表见 6.2）。 |

### 6.2 B-9 引用对照表（引用的编号 ↔ 该编号下的实际行为）

| 引用处（行） | 引用 | 该编号的实际行为（实读首句） | 判定 |
|---|---|---|---|
| `:80`（行为 6 自身） | 行为 12／14 | 12＝「触界收敛落地（幂等）」；14＝「完成收口旁路单点（`direct_answer`）」 | ✔ 对（收敛／直答两处正是写 `next_intent` 的两条） |
| `:97`（不降级） | 行为 11／12 | 11＝「通知恰三键＋分型闭世界」；12＝触界收敛落地（命中→通知追加如实注记） | ✔ 对（「注记必落」＝通知写入面） |
| `:98`（不降级） | 行为 15 | 15＝「调模型单点（桥接）」（用量与归因记账） | ✔ 对 |
| `:99`（不降级） | 行为 12／14 | 12／14 同上 | ✔ 对（「本块只落地它给的结论」） |
| `:130`（旧码登记） | 行为 7 | 7＝「对话链只追加（钉 `pin-22` 的写入面，`append_message`）」 | ✔ 对 |
| `:133`（风险 1） | 行为 1 | 1＝「写口单点」（`messages`／`steps`／`process_notes`／`notices`／`dialogue`） | ✔ 对（同一条风险里 `next_intent` 面未进断言集，见 BZ-2） |
| `:134`（风险 2） | 行为 3 | 3＝「步记录形状＝`StepRecord` 全字段（含 `run_id`）且状态如实」 | ✔ 对 |
| `:135`（风险 3） | 行为 4 | 4＝「`payload` 原样保真」 | ✔ 对 |
| `:136`（风险 4） | 行为 2 | 2＝「序号单调且与步记录成对」 | ✔ 对 |
| `:137`（风险 5） | 行为 12 | 12＝触界收敛落地（幂等段） | ✔ 对 |
| `:138`（风险 6） | 行为 13 | 13＝「收敛答案与通知材料面同源」 | ✔ 对 |
| `:139`（风险 7） | 行为 15 | 15＝调模型单点 | ✔ 对 |
| `:140`（风险 8） | 行为 16 | 16＝「工具上下文装配」（身份只从状态取） | ✔ 对 |
| `:141`（风险 9） | 行为 17 | 17＝「结果归一投影」 | ✔ 对 |

跨文件引用另核：`:58` 引 `specs/state.md` 行为 6（`:112` 对话层纯度）✔／行为 10（`:116` 限额参数键集——**精度问题见 BZ-5**）；`:60` 引 `specs/persistence.md` 行为 8（`:144`）✔；`:80` 引 `specs/state.md` 行为 9（`:115` 三族闭世界）✔；`:89` 引 `specs/gateway_adapter.md` 行为 1（`:79`）✔；`:20` 引 `specs/agent-loop.md` 行为 1 ✔。

### 6.3 结论（一句话）

**不可定稿**——B-1…B-5、B-7、B-8、B-9 八条闭合（规格侧改动到位、三闸实跑全绿），**B-6 未闭合**（卡面注记与施工流水仍沿用「§四【结构-2】四件」误锚）；另新增 6 条（BZ-1 中／BZ-2…BZ-5 低／BZ-6 疑点）。
**必须先修**：① **BZ-1**（新增行为 6 与已定稿 `specs/state.md:162` 的 `next_intent` 写口归属**两说并存**，须 L0 一句定性并就地对齐）；② **B-6 卡面**（`specs/modules.md:344` 锚改准＋施工流水 32 同款一句；另修「四个共享写口」名单与补齐名单不符）；③ **BZ-2**（行为 6 无【断言】形、无验收行，违判据 2）。
**随批清**：BZ-3（挂钩表 `:154` 依赖口径残留）／BZ-4（`pin-12` 括注）／BZ-5（`gates` 真源）。
**「卡须回阶段 2 修改」结论**：**不另开轮次**——`## bookkeeping` 卡的公开面与依赖行**已与规格逐字对齐**（11 成员同形、依赖行三块形状面、反引号只包模块名、spec gate PASS），本轮只欠**卡注一句＋流水一句**更正，按本仓先例（L0 窗 A 亲改卡＋记流水）随批清即可，**非结构性改卡**。

## 七、新增发现清单（复审轮）

| 编号 | 严重度 | 发现 | 证据锚点 | 建议处置 |
|---|---|---|---|---|
| **BZ-1** | **中** | **新增行为 6 的 `next_intent` 写口归属与已定稿 `specs/state.md` 风险 2 口径冲突（两说并存）**。行为 6（`:80`）＝「其余写点＝**各相位自己的过相位结果**（每相位返回面携路由意图）……**本块不接管全量 `next_intent` 写入**」；`specs/state.md:162`（风险 2）原文＝「**共享写口无归属**……：`messages`／`steps`／`notices`／`next_intent` 几乎每个节点都写。对策＝**写口归 `bookkeeping` 单点**、本块不提供写函数。检测＝`bookkeeping` 侧的「禁旁路直写」测试（本批不新增）」——含 `next_intent` 且主张写口归本块。而本块行为 1（`:75`）的断言字段集（`messages`／`steps`／`process_notes`／`notices`／`dialogue`）**不含 `next_intent`**，即 state 所指检测对 `next_intent` 面落空。 | `specs/bookkeeping.md:75,80`；`specs/state.md:162` | 二选一收正、禁两说并存（本仓先例＝跨规格就地改述，如 transport 批改 `state.md` 的 `SseEvent`）：① 以行为 6 为准，就地改述 `state.md:162` 的 `next_intent` 项（相位返回面携意图、闭世界校验归 `orchestration` 路由表）；② 或在行为 6 写明相位意图落状态所经的单一写口 |
| **BZ-2** | 低 | **新增行为 6 无【断言】形、无验收测试行**（异于其余 17 条）：`sed -n '80p' specs/bookkeeping.md \| grep -c "断言"` → **0**；验收测试 20 行（`:105-124`，18 行＋【边界集】／【保留集】）覆盖行为 1–5、7–18，**无行为 6 对应行**。行为 6 的「本块只写收敛／直答两处」半面可由行为 12／14 的断言间接覆盖，「其余写点不属本块」半面**无检测**——判据 2「每条能不能写成 assert」在该行无落点。 | `specs/bookkeeping.md:80`；`:105-124`；`:75`（行为 1 断言字段集） | 补一句机读断言（例：AST 扫描本块源码——`next_intent` 赋值只出现在 `converge`／`direct_answer` 两处）＋验收行（例 `::next_intent_write_points_owned`） |
| **BZ-3** | 低 | **挂钩表依赖行口径残留**：`:154` 仍写「依赖只许 `state`／`gateway_adapter`；不落盘；禁旁路直写」——红线 `:69` 已改述为「运行逻辑只依赖两处＋类型/常量另引三块」，此为**第五处**未同步；按字面读该行禁止 `tools`／`persistence`／`transport`，与红线／依赖行（`:131`）／卡面（`modules.md:347`）新口径相抵。 | `specs/bookkeeping.md:154`；对比 `:69`／`:131`；`specs/modules.md:347` | 同步为「**运行逻辑**只许 `state`／`gateway_adapter`；形状面另引三块、只许类型/常量；不落盘；禁旁路直写」 |
| **BZ-4** | 低 | **`pin-12` 括注「钉本体」落点与另两份规格表述不一致**：本规格 `:159`＝「钉 **`pin-12`**（P1，承接面——**钉本体落 `specs/persistence.md` 落盘面**）」；`specs/verification.md:140`＝「钉 `pin-12`（**落点＝接口 `Verdict` 两字段 ＋ 行为 11 行集对账**）」；`specs/persistence.md:216`＝「钉 `pin-12`（P1，**落盘面**——**字段面在 `specs/verification.md`**）」。三处对「钉本体／落点在哪」有两种说法。 | `specs/bookkeeping.md:159`；`specs/verification.md:140`；`specs/persistence.md:216` | 本规格括注改述为「钉落点＝`specs/verification.md` 的 `Verdict` 两字段＋行为 11；`specs/persistence.md`＝落盘面；本块＝承接写入面」 |
| **BZ-5** | 低 | **`gates` 值闭世界真源不精确（且断言用中文描述、无字面值）**：`:58`＝「`gates` 取值闭世界＝轮数／时长两项（真源＝`specs/state.md` 行为 10 与 `walk/裁决表.md` §06-A）」；行为 11（`:85`）断言＝「`gates` ⊆ 轮数／时长两项」。实读两处被指真源：`specs/state.md:116`（行为 10）＝**`Budget` 键集闭世界**（七键）＋数值真源指向 `recon/K` 与 §06-A，**全篇无 `gates` 取值面**（`grep -n "gates" specs/state.md` 仅 `:118` 行为 12 的「恰三键」形状句）；`walk/裁决表.md` §06-A（`:88-98`）＝循环上限五项。另：`specs/state.md:79-80` 的 `LimitHit.limit` 是**七值 `Literal`**（`rounds`／`discovers_per_round`／`executes_per_round`／`seconds`／`tool_timeout`／`discovers_per_run`／`ask_cap`）；`grep -rnE "max_rounds\|total_seconds" specs/ docs/runtime-refactor/synth/ docs/runtime-refactor/walk/` → **零命中**——现状两值闭世界（`max_rounds`／`total_seconds`）在册唯一证据＝`recon/B1` 的 `_converge` 条目 **R-B1-04**。 | `specs/bookkeeping.md:58,85`；`specs/state.md:79-80,116,118`；`docs/runtime-refactor/walk/裁决表.md:88-98`；`docs/runtime-refactor/recon/B1-公共位与结果归一.md`（`_converge` 条目 R-B1-04） | 真源改锚 `recon/B1` R-B1-04 或 `specs/state.md` 的 `LimitHit.limit` 面，并写明**机读字面值**（勿用「轮数／时长」中文描述当断言口径） |
| **BZ-6** | **疑点（未证实为缺陷）** | **`recon/B1` 公共位清单 16 项中 6 项既未承接、亦未排除登记**：`_MESSAGE_CLS`（#5）／`_complete`（#6）／`_observations_of`（#7）／`_timeout_result`（#9）／`_clarify_capped_answer`（#12）／`_tool_note`（#16）。多数可由他块属性解释（`_MESSAGE_CLS` 耦合 langchain 消息类＝框架面；`_complete` 由本块 `call_model`＋`gateway_adapter.complete` 取代；`_observations_of` 为读侧浅取；`_clarify_capped_answer` 行为面可由 `specs/state.md:198` 的分工注＋`specs/clarification.md:91,149` 承接）——但 **`_tool_note`（工具台账→过程档案条目、五形分型措辞）与 `_timeout_result`（单工具超时失败形构造）在 `specs/` 全量零命中**；`_tool_note` 恰是 `process_notes` 写入面的**条目构造器**，与 B-8 的 `_user_turn` 同类（本块 `note` 只收调用方给的 `digest`，分型措辞归属未登记）。**疑点，未证实为缺陷**（或归 `execution` 台账行构造，待 L0 辨明）。 | `docs/runtime-refactor/recon/B1-公共位与结果归一.md:11-27`（§一 16 项；`:19` #5／`:20` #6／`:21` #7／`:23` #9／`:26` #12／`:27` #16）＋该文 `_tool_note`／`_timeout_result` 条目；`grep -nE "_tool_note\|_timeout_result" specs/*.md` → 零命中 | L0 一句辨明并登记（承接／指定归属块／退役），或明写「B1 清单剩余 6 项属他块，本规格不覆盖」 |

### 7.1 判据 16 问复跑（逐条一行结论）

1. **十节齐＋标题逐字**：**无发现**（`grep -n "^## "` → 10 节：`:7/11/23/34/64/73/94/101/128/144`，标题与 `docs/spec-format.md` §二之二 逐字一致）。
2. **行为逐条可 assert（含糊词）**：含糊词 `grep -nE "尽量|合理|必要时|视情况"` → **exit 1（0 命中）**；**行为 6 无【断言】形——见 BZ-2**。
3. **数字／真源**：「落地六键」（`:86`）／「恰三键」（`:85`）自含可核；过程档案上限不复述数字（`:84` 指 `synth/S5:32` 的「过程档案（digest≤200）」口径，实存）✔；**`gates` 真源精度见 BZ-5**。
4. **不做什么锚点**：**无发现**（`:15-21` 七行俱带「由谁承担＋锚点」）。
5. **框架红线闸名与覆盖**：**无发现**（逐条实读 `tools/importlinter_v2.toml`：R5b `:103`／R6 `:110`／R7 `:116` 的 `source_modules` **含** `appv2.runtimev2.bookkeeping`；R7 `forbidden_modules=["appv2.infra.llm_client"]` `:117`；R8 `:122-123` 不含本块、规格未宣称覆盖）。
6. **不降级与静默禁令**：**无发现**（`:96` 合法降级＝无；`:97-99` 三条禁令各指带断言的行为；红线 `arch/P7a-交接包与挂账清单.md:98` A-P7a-37 实存）。
7. **验收测试（每行标识／边界集保留集）**：**无发现**（20 行全绑 `tests/domains/test_v2_bookkeeping.py::<id>`；【边界集】`:123`／【保留集】`:124` 俱在；`ls tests/domains/test_v2_bookkeeping.py` → **No such file**，`:126` 已注阶段 5 新建）。
8. **挂钩表与「已真跑」**：已填、接不上闸俱写原因；「已真跑」三条**经本子代理亲跑属实**（7.2 三闸全绿）；唯 `:154` 口径残留见 **BZ-3**。
9. **与 `walk/` 决策冲突**：**无发现**（裁决 #4／#7／#12／#13 与 `walk/判断归责表.md:23`「收尾·完成判定＝程序」逐一比对不冲突；新行为 6 与 `walk/05-理解-定路由.md:12-13` 的路由实质相容，`specs/agent-loop.md:149` 行为 8「路由表在 `orchestration` 一处集中——业务相位不得自行决定跳转」＝行为 6「闭世界校验归 `orchestration` 路由表」的同向表述）。
10. **覆盖（`recon/B1` 公共位逐条）**：承接 8 项（`_step_record`→`record_step`／`_next_seq`→`next_seq`／`_converge`→`converge`／`_ctx_of`→`tool_context`／`_result_dict`→`result_projection`／`_direct_answer`→`direct_answer`／`_note`＋`_notes_with`→`note`）＋正确排除 1 项（`_gate_or_none`——入口闸判定归 `state.check_limits`）＋登记不承接 1 项（`_user_turn`，`:130`）；**剩余 6 项见 BZ-6（疑点）**、无越界（判定归 `state`／落盘归 `persistence`／发帧归 `transport` 均作边界标注）。
11. **总纪律残留**：**无发现**（行为 18 `:92` 明文零判断；行为 9 的「过程内容不入层」靠 `origin` 闭世界拒收而非词表判据）。
12. **与模块卡一致**：公开面 11 成员逐字对上（规格 `:38-55` ↔ 卡 `modules.md:329-341`；`record_step` 的 `status` 两处同形）；职责行 `modules.md:323` ↔ 规格目标 `:9` 对上；**卡注锚误＋「四个共享写口」名单不自洽见 B-6**（卡级，只报不改）。
13. **接口与已定稿规格逐字对账**：**无发现**（`persistence.StepRecord` 七字段／`transport.NOTICE_TYPES`（`transport.md:62` 二十二值唯一真源，本块只引不述）／`state` 三处（`check_limits:87`、`Manifest.as_dict:51`、`STEP_KINDS`＋`RUN_STATUS_KINDS`:90）／`gateway_adapter` 桥接（`gateway_adapter.md:79` ↔ 本块 `:89` 同口径：从状态取 `run_id`→调 `complete`→只回 `content`→用量归因交记账并进 Manifest））。
14. **钉登记（`04a` 全表）**：漏登／漏配**无发现**（`04a` 第 22 行＝`pin-22` P0、第 24 行＝`pin-24` P1、第 26 行＝`pin-26` P1、第 12 行＝`pin-12` P1，与 `specs/bookkeeping.md:78/81/82/156-159` 的编号／优先级逐一相符；`pin-26` 写入面已认领且与 `state` 字段面／`understanding` 渲染面不冲突）；唯 `pin-12` 括注见 **BZ-4**。
15. **真源真实存在且含该事实**：**多数属实**（`recon/B1` D-B1-01`:44`／D-B1-02`:58`／D-B1-03`:81`／D-B1-04`:82`／D-B1-13`:199`／D-B1-15`:244`；`synth/S5:105,86,32`；`walk/裁决表.md:88-98`；`appv2/tools/schema.py` 的 `resolve_send_budget` 与常量；`modules.md:117`；`arch/P7a:98`）；**例外＝`gates` 真源（BZ-5）**。
16. **卡级问题（只报不改）**：卡注 §四【结构-2】锚误＋「四个共享写口已补全」名单不实（`next_intent` 无承接函数）＝**卡面注记须修**；公开面／依赖行**无卡错**（与规格逐字对齐、spec gate PASS）。**「卡须回阶段 2 改卡」本轮不触发**——只欠卡注一句＋流水一句更正，按先例随批清。

### 7.2 闸实跑记录（2026-10-15，本子代理亲跑）

```
$ uv run python tools/check_specs.py
spec gate: PASS（0 警告）                                       # exit 0

$ uv run python tools/ref_resolvable.py check
真源引用可解析闸绿：19 份规格的真源引用与边界规则编号均可解析。   # exit 0

$ uv run lint-imports --config tools/importlinter_v2.toml
Contracts: 18 kept, 0 broken.（R1–R8、R5b、V2 B6 逐条 KEPT）      # exit 0
```

本轮新增关键取证：`grep -nE "tools\.md" specs/bookkeeping.md` → **exit 1**；`grep -n "step_record_six_keys"` → **exit 1**；`sed -n '80p' … | grep -c "断言"` → **0**；`grep -c "并发" recon/H…md` → **0**；`grep -rnE "max_rounds|total_seconds" specs/ …/synth/ …/walk/` → **0**；`grep -n "gates" specs/state.md` → 仅 `:118`；`grep -nE "_tool_note|_timeout_result" specs/*.md` → **0**；`grep -nE "pin-(22|24|26|12)" docs/runtime-refactor/eng/04a-应钉行为清单.md` → 该件表体用**行号**非 `pin-NN` 字面（第 22／24／26／12 行＝`:31/:33/:35/:21`，与上轮引用同物）。

---

## 八、复审轮新增发现的 L0 处置（2026-10-15）

| 编号 | 处置 | 落法 |
|---|---|---|
| **B-6 未闭合**（承诺未兑现） | **采纳 → 补兑现** | `specs/modules.md` 的 `## bookkeeping` 卡注与施工流水 32 同批改准：由「§四【结构-2】四件」改为「**§四【结构-2】列 `notices`／`steps`／`next_intent` 三件**；同文件 **§二观察**另把 `messages` 并列」——锚与真源两处对齐 |
| **BZ-1**（中，两说并存） | **采纳 → 定死唯一写口** | 与已定稿 `specs/state.md` 风险 2「写口归 `bookkeeping` 单点」对齐：**新增 `set_intent(state, intent)` 为 `next_intent` 唯一写口**（卡＋规格同批）；行为 6 改述为「各相位**经它**给路由意图；收敛与直答两处由本块内部写；**『去哪』的决策仍在 `orchestration`**（写字段≠做路由决策）」；`next_intent` 并入行为 1 的写口单点断言集——**无需改 state（它本就主张写口归本块）** |
| **BZ-2**（低） | **采纳** | 行为 6 补 **【断言】**（越界抛错＋全仓写点只在本块）＋**验收行** `::set_intent_single_port_closed_world` |
| **BZ-3**（低） | **采纳** | 挂钩表该行改述为「**运行逻辑**只许 `state`／`gateway_adapter`；`tools`／`persistence`／`transport` **只许引类型与常量形状**」——与红线、依赖行、卡面四处口径统一 |
| **BZ-4**（低） | **采纳** | `pin-12` 的括注三处统一为「**承接面**——钉本体挂 `specs/persistence.md` 的落盘面」 |
| **BZ-5**（低） | **采纳** | `gates` 取值闭世界真源指实：`recon/B1-公共位与结果归一.md` R-B1-04（`max_rounds`／`total_seconds`）；限额数值仍指 `walk/裁决表.md` §06-A ＋ `recon/K` |
| **BZ-6**（低，疑点） | **采纳 → 补对照表** | 新增「**旧码公共位承接对照**」表（`recon/B1` 十六项逐条落点）：承接＝`_step_record`／`_next_seq`／`_note`／`_notes_with`／`_result_dict`／`_observations_of`／`_ctx_of`／`_direct_answer`；拆分＝`_converge`（判定→`state`／落地→本块）、`_complete`（实作→`gateway_adapter`／转发→本块）；排除＝`_gate_or_none`（判定归 `state`、入口调用归 `orchestration`）／`_MESSAGE_CLS`（含框架类型→只许在 `orchestration`，R5b）／`_timeout_result`（随工具调用点归 `execution`）／`_clarify_capped_answer`（文本面归 `clarification`／`answering`）／`_user_turn`（退役）／`_tool_note`（措辞归 `execution`，本块只收定型条目） |

**净结果**：复审 9 条＝**8 闭合／1 未闭合（B-6）**；新增 6 条（中×1／低×4／疑点×1）**全部采纳并清**；**必须先修三项（BZ-1／BZ-2／B-6）已清**。**无升 Owner 项**；**无「卡须回阶段 2 修改」**（卡级欠账随批补齐）。
