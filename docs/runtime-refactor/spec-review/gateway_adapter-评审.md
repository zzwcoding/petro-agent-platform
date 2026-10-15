- 日期：2026-10-15 ｜ 状态：**评审发现清单（待 L0 逐条处置）**
- 被评对象：`specs/gateway_adapter.md`（`状态: 草稿`）＋ 同批代码 `appv2/runtimev2/gateway_adapter/fake.py`／`__init__.py`／`tests/runtimev2/test_gateway_adapter_fake.py` ＋ `specs/modules.md` `## gateway_adapter` 卡级修正
- 本清单只产发现，不修改任何现存文件。凡断言「X 不存在／X 与 Y 不一致」均附实读行号或 `grep`／实跑证据；未证实的怀疑写成「疑点」。

## 一、结论摘要

1. **版式骨架合格**：十节齐、标题逐字、顺序正确（同 `docs/spec-format.md` §二之二）；行为约定**无**含糊词（`grep -nE "尽量|合理|必要时|视情况"` **exit 1**，0 命中），行为 1–13 每条带【断言：…】；「不做什么」8 行俱带「由谁承担＋锚点」；验收测试 16 行全绑测试标识，【边界集】／【保留集】两行俱在。六道闸**亲跑全绿**（见 §四），`tests/runtimev2` 实测 **45 passed**。
2. **一处「高」（失败分类单源的锚不实且与 infra 实判冲突）**：规格 `:18/:62/:83` 把「失败分类判据单源」锚到 `specs/infra.md`（「429／可切不可切／可重试三分类」），但 `specs/infra.md`（已定稿、58 行）**通篇无任何失败分类**；现状真分类是 `appv2/infra/llm_client.py:107 classify_upstream_failure`（**二值**：网络错/超时/5xx＝可切；**429/4xx＝不可切**）与 `appv2/tools/registry.py:50 classify_exception`（**三分类** category）。规格行为 6 要把 429 当**可重试**，而 infra 判 **429＝不可切**——「复用 infra 单源、只消费其结论」推不出 429 可重试；现状 429-重试判据是旧 `llm.py:_is_rate_limited` 的私有重写（`recon/L3:82` D-L3-03 明记「文字对齐而非共享实现」）（**G-1**）。
3. **两处中**：「V1 侧 B6 契约」被当作本块（appv2）红线的**覆盖闸**——V1 B6 的 `root_package=app`（`pyproject.toml:60`）**不覆盖 appv2**，appv2 侧真闸是 `tools/importlinter_v2.toml:56` 的「**V2 B6**」（规格全文未提）（**G-2**）；「**45 测**」误挂单文件——`tests/runtimev2/test_gateway_adapter_fake.py` 实测 **14 测**（`uv run pytest tests/runtimev2/test_gateway_adapter_fake.py -q`→14 passed），**45** 是 `tests/runtimev2/` **整目录**总数（14＋8＋23）（**G-3**）。
4. **一处中（跨卡桥接留白）**：规格行为 1 把「发起方」钉死为 `bookkeeping.call_model` 单点，但 `## bookkeeping` 卡（`modules.md:331`）为 `call_model(state, caller, messages) -> str`——返回 `str`、无 `run_id` 参数；本块 `complete(...) -> ModelReply` 返回回执、`run_id` 为关键词。两卡形状桥接（`call_model` 如何取 `run_id`、记账字段如何从 `ModelReply` 落 bookkeeping）**全无落点**；行为 5 要的归因面／`pin-25` 的用量字段，`str` 回值承载不了（**G-4**）。
5. **六处低**：卡注路径笔误 `tests/runtimev2/gateway_adapter/fake.py`（该目录不存在）（**G-5**）；冻结钟接口 `frozen_date() -> date`／行为 9「`real`→真实日」与真源 `resolve_eval_frozen_date -> date | None`（`real`→`None`）口径不一（**G-6**）；接口新增 `EVAL_FROZEN_DATE_DEFAULT/REAL` 不在卡公开面（**G-7**）；`ModelReply` 规范化定义位置未落点（现寄居替身文件 `fake.py:28`）（**G-8**）；来源行引 `state.md 行为 15`（Manifest 全键恒出）／`agent-loop.md 行为 2`（调用前 Context Builder 编译）非同一物或锚偏（**G-9**）；`:129` 写死「2026-08-31」又声称「本规格不复制取值」（自我矛盾）（**G-10**）。
6. **计数**：**10 条**发现——`L0×0`／`高×1`（G-1）／`中×3`（G-2｜G-3｜G-4）／`低×6`（G-5…G-10）。**卡级**：G-5（卡注路径笔误）／G-7（卡公开面漏常量）属卡面欠账；**无「卡须回阶段 2 重做」的结论**（卡级修正本身自洽，见问答 12／16）。

## 二、发现清单表

| 编号 | 严重度 | 发现 | 证据锚点 | 建议处置 |
|---|---|---|---|---|
| **G-1** | **高** | **失败分类「判据单源在 infra（`specs/infra.md`）」不实，且与 infra 实判语义冲突**。规格「不做什么」行（`:18`）与行为 7（`:83`）写「失败分类的**判据**（429／可切不可切／可重试三分类）｜`infra` 的单源分类（本块复用不另立）｜`specs/infra.md`」。① 实读 `specs/infra.md`（已定稿、58 行）**无 `classify_upstream_failure`／无「可切/不可切」／无「三分类」**——只有一句泛述「gateway 域（别名路由/重试/预算/动态闸）」（`:34`）。② 现状真正的分类：`appv2/infra/llm_client.py:107` 的 `classify_upstream_failure`＝**二值**（网络错/超时/5xx→`UpstreamUnavailable` 可切；**`429`/4xx→`UpstreamRejected` 不可切**，见 `:16-17,:108-122`）；`appv2/tools/registry.py:50` 的 `classify_exception`＝**三分类**（`CATEGORY_RETRYABLE/REFUSED/BAD_ARGS`，429→RETRYABLE，见 `:7,:50-110`）。规格把两条不同分类并成「429／可切不可切／可重试三分类」单一 infra 单源——不成立。③ **语义冲突**：infra 判 **429＝不可切**（`llm_client.py:111`）；规格行为 6（`:82`）要 429 **可重试**。若按「只消费 infra 结论」实现，429 永远不重试 → 与行为 6 相悖；现状 429 可重试判据是旧 `appv2/runtime/llm.py:_is_rate_limited` 的**私有重写**（`recon/L3:82` 明记「文字对齐而非共享实现」，D-L3-03 记其漂移风险）。 | `specs/gateway_adapter.md:18,62,83`（含 `:82` 行为 6）；`specs/infra.md`（全篇）；`appv2/infra/llm_client.py:16-17,107-122`；`appv2/tools/registry.py:7,50-110`；`docs/runtime-refactor/recon/L3-网关与支撑小件.md:70-84` | 改锚：把「分类判据单源」锚到 **`appv2/infra/llm_client.py` 的 `classify_upstream_failure`（可切/不可切）＋ `appv2/tools/registry.py` 的 `classify_exception`（三分类）**；并显写 **429 的「可重试」判据出处**（须与 infra「429 不切备」**分层**——重试≠切备，非同一判据），或把「单源」收窄为「本块不新造阈值/错误文案表（AST 断言）」。不得把 `specs/infra.md` 当作「三分类单源」 |
| **G-2** | 中 | **「V1 侧 B6 契约」被当作本块（appv2）红线的覆盖闸——覆盖关系错位；appv2 侧真闸「V2 B6」全文未提**。规格 `:70/:73/:144/:146` 四处把「模型供应商唯一出口＝infra」及「禁手写替代（不直连 SDK）」的覆盖闸写成「**V1 侧 B6 契约**」。实读 `pyproject.toml:59-60`：该 `[tool.importlinter]` 的 `root_package = "app"`、契约 `source_modules=["app"]`（`:88-94`）——**只约束 V1 包 `app`，不检查 `appv2`**。appv2 侧的等价契约是 `tools/importlinter_v2.toml:55-62`「**V2 B6：litellm 唯一接触点=appv2.infra.llm_client**」（本子代理实跑 KEPT）。规格引 V1 B6 作本块覆盖闸＝指了一个**不会在 appv2 代码上触发**的闸。 | `specs/gateway_adapter.md:70,73,144,146`；`pyproject.toml:59-60,88-94`；`tools/importlinter_v2.toml:55-62` | 本块 litellm 红线改锚 **`tools/importlinter_v2.toml` 的「V2 B6」契约**（并保留 R7 作 runtimev2 面）；「V1 侧 B6」至多作**先例/现状锚**，不得当作本块（appv2）的覆盖闸 |
| **G-3** | 中 | **「45 测」误挂单文件**。规格 `:131`／`:151` 与验收注 `:119` 称 `tests/runtimev2/test_gateway_adapter_fake.py`「**全绿（45 测）**」。实测该文件 **14 测**（`uv run pytest tests/runtimev2/test_gateway_adapter_fake.py -q` → `14 passed`）；**45 是 `tests/runtimev2/` 整目录**总数（`uv run pytest tests/runtimev2 -q` → `45 passed`＝fake 14 ＋ frozen_clock 8 ＋ leg_replay 23）。`eng/04 §五`（`:50`）亦把 45 归**整个 `tests/runtimev2/`**（「45 测中替身自证 15」）。规格把目录总数错挂到单文件。 | `specs/gateway_adapter.md:119,131,151`；`tests/runtimev2/test_gateway_adapter_fake.py`（14 个 test 函数）；实跑 `pytest tests/runtimev2 -q`（45）／`pytest tests/runtimev2/test_gateway_adapter_fake.py -q`（14）；`docs/runtime-refactor/eng/04-测试网设计.md` §五 `:50` | 改准：「该件 **14 测**全绿；`tests/runtimev2/` 共 45 测全绿」；或统一写「`tests/runtimev2/` 45 测全绿（其中替身自证 14 测）」 |
| **G-4** | 中 | **与 `## bookkeeping` 卡 `call_model(state, caller, messages) -> str` 的接口桥接未落点（无硬类型冲突，但两卡形状与记账要求对不上）**。规格「不做什么」行（`:15`）与行为 1（`:77`）把「调用的发起方」钉死为 `bookkeeping.call_model` **单点**；但 `## bookkeeping` 卡（`modules.md:331`）＝`def call_model(state, caller: str, messages) -> str`——**返回 `str`、无 `run_id` 参数**；本块 `complete(messages, *, caller, run_id) -> ModelReply`（`:48`）**返回回执、`run_id` 为关键词**。① `run_id`：`call_model` 无该参，须自 state 取（卡未写明）；② 记号面：行为 5（`:81`）要「逐调用归因（`caller`/`run_id`）」、`pin-25` 要 `cached_tokens`/用量字段——`call_model` 的 `str` 回值**承载不了**，谁从 `ModelReply` 取字段落记账未写明。两卡不构成硬类型冲突（`call_model` 可内部调 `complete` 后只回 content），但桥接**全无落点**。 | `specs/gateway_adapter.md:15,29,77,81,87`；`specs/modules.md:331,336,492`；`docs/runtime-refactor/00-决议与方法.md` 流水 30（`:101`） | 二选一（`bookkeeping` 卡由**窗 A** 可改）：① 在 `## bookkeeping` 卡 `call_model` 行补一句「内调 `gateway_adapter.complete`，归因/用量经回执落 bookkeeping，向节点只回 content」；② 本规格行为 1 补桥接说明（`call_model` 从 state 取 `run_id`、调 `complete`、取 `ModelReply.content` 返回，字段经 bookkeeping 记账） |
| **G-5** | 低 | **卡注路径笔误**。`modules.md:492` 卡级修正注写「同批：**`tests/runtimev2/gateway_adapter/fake.py`** 替身与包根导出按新面回写」。实读**无 `tests/runtimev2/gateway_adapter/` 目录**（`ls` → `No such file or directory`）；替身在 `appv2/runtimev2/gateway_adapter/fake.py`、测试件在 `tests/runtimev2/test_gateway_adapter_fake.py`（`git status`：`M appv2/runtimev2/gateway_adapter/fake.py`／`M tests/runtimev2/test_gateway_adapter_fake.py`）。卡注把两处路径糅成一条错路径。 | `specs/modules.md:492`；`ls tests/runtimev2/`（无 `gateway_adapter/`）；`git status --short` | 卡注改准：「`appv2/runtimev2/gateway_adapter/fake.py` 替身＋包根 `__init__.py` 导出按新面回写，随规格同步维护的看守件为 `tests/runtimev2/test_gateway_adapter_fake.py`」 |
| **G-6** | 低 | **冻结钟接口/行为与所锚真源的口径不一致（疑点）**。规格接口 `def frozen_date() -> date`（`:53`）与行为 9（`:85`）「`real` → **真实日期**」；但所锚数值真源 `recon/L3` §`resolve_eval_frozen_date` 与 `appv2/runtime/eval_clock.py:36-58` 为 `resolve_eval_frozen_date() -> date | None`，**`real` → `None`（回真实时钟）**（`eval_clock.py:49-50`）。规格风险 5（`:129`）自己把「数值真源」锚到该函数——**真源返回 `None`，规格要 `date`**。函数名 `frozen_date` 与卡（`modules.md:489`）一致（可接受，卡为准），但与现状 `resolve_eval_frozen_date` 不同名。 | `specs/gateway_adapter.md:51-53,85,129`；`appv2/runtime/eval_clock.py:36-58`；`docs/runtime-refactor/recon/L3-网关与支撑小件.md:252-270` | 辨明并写实：`real` 态本块 `frozen_date()` 到底「返回真实日」还是「返回 `None` 交调用方落 infra.clock」——与所引真源对齐一句（卡 `modules.md:489` 只写 `-> date`，若取 `date` 取向须说明与现状 `None` 的差异是有意收正） |
| **G-7** | 低 | **卡级：接口新增 `EVAL_FROZEN_DATE_DEFAULT`／`EVAL_FROZEN_DATE_REAL` 不在 `## gateway_adapter` 卡公开面**。规格接口定义列 `EVAL_FROZEN_DATE_DEFAULT: date`（`:51`）／`EVAL_FROZEN_DATE_REAL: str`（`:52`）；`specs/modules.md` `## gateway_adapter` 卡公开面（`:483-490`）**只有 `ModelReply`／`complete`／`ScriptedCompleter`／`frozen_date`**，**无这两常量**。规格自称「签名以卡为准」（`:65`）。 | `specs/gateway_adapter.md:51-52,65`；`specs/modules.md:483-490` | 回阶段 2 在卡公开面补这两常量（或规格删——判据 12「以卡为准」） |
| **G-8** | 低 | **`ModelReply` 的规范化定义位置未落点（现寄居替身文件）**。规格接口定义把 `ModelReply` 列为**本块回执类型**（`:35-46`，非「替身面」小节）；但仓内唯一定义在 `appv2/runtimev2/gateway_adapter/fake.py:28`（**测试替身模块**），包根 `__init__.py:10` 从 fake 转发。行为 11（`:87`）要求「替身与生产桥**同一回执形状**」——若阶段 5 生产桥另立 `ModelReply`，将出现**两个同类** → 同面漂移。 | `specs/gateway_adapter.md:35-46,87`；`appv2/runtimev2/gateway_adapter/fake.py:28`；`appv2/runtimev2/gateway_adapter/__init__.py:10` | 规格接口定义注一句：`ModelReply` 为**块级单一定义**（阶段 5 迁至非替身模块，替身只 import），杜绝双定义 |
| **G-9** | 低（疑点） | **来源行两处引用非同一物/锚偏**。① `:4` 引 `specs/state.md 行为 15`——state 行为 15（`state.md:121`）＝`Manifest.as_dict()` **全键恒出**，是 **Manifest** 的投影面；本块行为 3「`ModelReply` 十字段恒在场」是**回执**形状，疑为类比引用。② `:4`／「不做什么」行 2（`:16`）把「何时调用模型、调几次的循环与相位决策」锚 `agent-loop.md 行为 2`——实读 `agent-loop.md:101` 行为 2＝「模型每次调用前经 **Context Builder 确定性编译**（多轮消息历史簿记）」，讲**调用前的上下文编译**，不含「何时/几次」；「循环与相位决策」实在**行为 1（`:79` 四相位循环）／行为 3（`:114` 发射判据）**。 | `specs/gateway_adapter.md:4,16,79`；`specs/state.md:121`；`specs/agent-loop.md:79,101,114` | ① 删/换 `state.md 行为 15` 之引（非同一物）；② 「不做什么」行 2 锚改 `agent-loop.md` **行为 1**（四相位循环）或**行为 3**（发射判据） |
| **G-10** | 低 | **数字自相矛盾（裸字面值＋「不复制」并存）**。规格 `:129` 写「冻结点 **2026-08-31** 由 Owner 拍板；**本规格不复制取值**」——同一行既**写死裸字面值** `2026-08-31`，又声明不复制。数字本身与真源一致（`eval_clock.py:32` `date(2026, 8, 31)`），但违反 `spec-format.md` §三.2「数字单点／禁裸字面值」与规格自身声明。 | `specs/gateway_adapter.md:129`；`appv2/runtime/eval_clock.py:32`；`docs/spec-format.md:38-39` | 删去括号内「2026-08-31」字面值，只留真源指针（或删「不复制」声明、明写该值属真源复述） |

## 三、16 问逐条回答

**1 十节齐＋标题逐字？** **无发现。** `grep -n "^## "` 得十节且逐字有序：`## 目标`(:7)／`## 不做什么`(:11)／`## 触及的模块`(:24)／`## 接口定义`(:32)／`## 框架与依赖红线`(:67)／`## 行为约定`(:75)／`## 不降级与静默禁令`(:91)／`## 验收测试`(:98)／`## 依赖与风险`(:121)／`## 与闸的挂钩表`(:136)——与 `docs/spec-format.md` §二之二（`:33-34`）逐字一致（节数＝10）。

**2 行为约定每条能否写成 `assert`／含糊词？** **无发现。** 判 FAIL 的含糊词「尽量／合理／必要时／视情况」全文 **0 命中**（`grep` exit 1）；行为 1–13（`:77-89`）**每条**带【断言：…】，落成签名参数集合比较／抛错／协程断言／AST 扫描／计数等机检形。

**3 数字有无裸值？** **有发现——G-10。** 计数项「十个字段」（`:79`＝自含接口计数）、「三桶族」（`:81`，同 `recon/L3:166` 三桶 understand/decision/answer）、「45 测」（`:131/:151`，**错**，见 G-3）；裸字面值一项：`:129` 的「2026-08-31」（自我矛盾，G-10）。

**4 不做什么每条「由谁承担＋锚点」？** **无发现（G-9 锚偏属来源/锚点精度、非缺失）。** 8 行俱带：`:15`→`prompts`＋`bookkeeping` 单点／`## prompts`／`## bookkeeping`；`:16`→`orchestration`／各相位（锚点见 G-9）；`:17`→`infra`＋`## infra`／`calllog.py 自述`（文件实存 `appv2/infra/gateway/calllog.py`）；`:18`→`infra`（锚点见 G-1）；`:19`→`transport`／`specs/transport.md`；`:20`→`state`＋`bookkeeping`／`state.md 行为 10／13`（实读 `state.md:116,119` 为「限额参数键集闭世界」／「触界不静默」✔）；`:21`→**不做**（本块内单点）／本规格行为 3；`:22`→**不做**／`walk/判断归责表.md`。

**5 框架红线闸名真存在／source 真覆盖？** **有发现——G-2（B6 覆盖错位）。** 逐条实读 `tools/importlinter_v2.toml`：**R5b**（`:101-105`，`source` **含** `appv2.runtimev2.gateway_adapter`）、**R6**（`:107-111`，含）、**R7**（`:113-117`，**不含** `gateway_adapter`——spec 所述「例外面」**属实**：R7 的 `source` 列 gate/orchestration/bookkeeping 等却不列 gateway_adapter，`forbidden=["appv2.infra.llm_client"]` 属实）。三条**实跑 KEPT**。「无点名框架（本块不引入任何框架）」（`:69`）写法合 `spec-format.md` §二。**唯**「V1 侧 B6」当作本块覆盖闸错位（G-2）。

**6 不降级与静默禁令？** **无发现。** `:93`「合法降级路径：**无**」；`:94` 四条「不得静默」各配断言（失败留痕＝尝试次数／`usage_estimated` 两路径取值不同／未设 env 时取缺省冻结日 ≠ 真实当日）。每条机读信号＋断言齐备。

**7 验收测试（每行标识／边界集保留集）？** **有发现——G-3（数字误挂）。** 16 行**全部**绑标识（`:102-117`）：13 行绑**新建** `tests/domains/test_v2_gateway_adapter.py::<id>`（`:119` 注该文件阶段 5 建），3 行绑 `tests/runtimev2/test_gateway_adapter_fake.py`。**该 3 行的测试标识实存**：`TestCardFace::test_complete_signature_matches_card`（`test:124`）／`TestDefaultFallback::test_unscripted_without_default_fails_fast`（`test:99`）／`TestObservationFaces::test_script_injection_readonly`（`test:79`）——**该件实跑 14 passed（全绿属实）**。`：【边界集】`（`:116`）／【保留集】（`:117`）两行俱在。唯「45 测」错（G-3）。

**8 与闸的挂钩表（填了没／接不上写原因／「已真跑」属实否）？** **有发现——G-2（B6 行覆盖错位）。** 表已填（`:138-154`）；`:140`「spec gate（该闸只校这两项——十节标题不在其作用面）」**诚实属实**（实读 `tools/check_specs.py`：只校 `## 触及的模块`／`## 验收测试` 绑定，**不校标题名**，`:267-279`）；`:147-149` R5b／R7／R6「已真跑」**由本子代理亲跑属实**（`lint-imports --config tools/importlinter_v2.toml` → 18 kept 0 broken；`lint-imports`（默认 pyproject）→ 6 kept 0 broken）；`:144`「已真跑（lint-imports 双配置）」属实，**但所挂 B6 是 V1 侧**（G-2）；`:146/:153/:154` 三处「无专属闸→人审＋原因」齐备。

**9 与 `walk/` 决策是否冲突？** **无发现。** 逐条比对：项目级裁决 #7（新建 `appv2/runtimev2`、旧码只备份，`裁决表:18`）✔；#4（现状缺陷只作**现状证据**，不设收债，`:15`）→ 本规格风险 4/8 把「MiniMax 不上报 `cached_tokens`」「alias 两处不同源」作**现状事实**登记 ✔；`判断归责表.md`（程序判结构/模型判语义，`:22-23`）＋`00-设计总纲.md` §二 总纪律→ 行为 13 零判断 ✔。本块**零判断面**，未见与任一条裁决冲突。

**10 覆盖（`synth/S1` 相关单元）／有无越界？** **无发现（覆盖面完整；划界与卡一致）。** `synth/S1` `H14 网关与模型缝`（`S1:49`「gateway.complete 单出口＋429 退避＋测试替身＋评测时钟」；表 B `S1:114`「V2-39 评测时钟／V2-40 429 降级／V2-80f LLM 全量留痕／V2-22 429 分类」）→ 本块目标/行为/替身/时钟**逐项接住**（模型出口＝行为 1–8｜记账归因＝行为 5｜评测时钟＝行为 9）。**三条划界核对**：calllog **写路径**归 `infra`（`:17`，`appv2/infra/gateway/calllog.py` 实存并自述「gateway.complete 逐调用落 JSONL」）✔｜提示词装配归 `prompts`（`:15`，`## prompts` 卡 `:349-354` 装配函数）✔｜发起单点归 `bookkeeping.call_model`（`:15`，`## bookkeeping` 卡 `:331`）✔——与 `specs/modules.md` 相应卡一致。**越界**：未见把别块的事写进来（`orchestration` 收口／`transport` 帧／`state` 判定均作**边界标注**）。

**11 总纪律残留（程序替模型判语义）？** **无发现。** 行为 13（`:89`）明文「本块零判断：不读词表、不判语义、不做业务分支（只有可重试/不可重试这类由 `infra` 判据给出的**结构分派**）」；本块无「若出现 X 词就 Y」形设计。

**12 与模块卡一致（职责／公开接口／依赖）＋卡级修正自查？** **有发现——G-4／G-5／G-7。** 一致项：职责 `:9`↔卡 `modules.md:480`；公开面 `:35-59`↔卡 `:483-490`（`ModelReply` 十字段／`complete` async 关键词／`ScriptedCompleter` 观测面／`frozen_date` **逐条对得上**）；依赖：卡 `模块:（无）／外部 infra`（`:494-496`）与规格 `:30`（本块只消费 infra）一致。**卡级修正自查**：① async（行为 4）／② `ModelReply`（接口）／③ 不留自由 `params`＋`run_id` 进面（行为 2／5）／④ 评测时钟入面（行为 9）——**与卡注 `:492` 逐字对得上**。**唯**：卡注路径笔误（G-5）／卡公开面漏两常量（G-7）／与 `## bookkeeping` 卡桥接留白（G-4）。**与 `## bookkeeping` 卡冲突判定**：**非硬类型冲突**（`call_model` 可内调 `complete` 后只回 content），但 `call_model -> str`／无 `run_id` 与 `complete -> ModelReply`／`run_id` 关键词的**形状桥接与记账字段流向全无落点**，是「留白」非「矛盾」——建议按 G-4 由窗 A 在 `## bookkeeping` 卡或本规格补一句（**卡由窗 A 可改**）。

**13 接口与已定稿规格逐字对账？** **无发现（无冲突）。** ① `specs/state.md`：`Manifest` 十字段（`state.md:40-52`）与 `ModelReply`（本块）**不同类型、无字段重叠**——无冲突；本规格未复述 `Manifest`。② `specs/persistence.md`：`:19`「模型调用与调用记账（calllog）｜`gateway_adapter`（记账出口在 `infra`）」与 `:145`「`run_id` 全盖章（**落盘面**）」——与本块「calllog 写路径归 `infra`」（`:17`）、`pin-28`「落盘面挂 `persistence`」（`:149`）**分工互不矛盾**；`persistence.md:217` 同标「全盖章面挂 `specs/agent-loop.md`」，与本块一致。③ `specs/transport.md`：`notice{type:"run_failed"}` 是引擎/网关异常**失败收口**帧（`transport.md:99,160`）；本块行为 8（`:84`）「抛错，由 `orchestration` 收口（转 `run_failed` 通知）」——**承接一致**（本块不产帧、不吞错）。

**14 钉登记（全表扫 `eng/04a`）？** **无发现（登记正确；一处措辞精度见 G-6）。** ① **同物核对**：`pin-25`（`04a:34`「`cached_tokens` 透传 calllog JSONL；上游未上报时字段=0（MiniMax 面）」）↔ 本块 `:43`／`:147`「`cached_tokens` 未上报＝0」——**同物（取其一半）**、P1 **对**；`pin-27`（`04a:36`「冻结时钟：`EVAL_FROZEN_DATE` 缺省 2026-08-31、**帧 frozen_date 全在场**；real 须显式」）↔ 本块 `:148`「冻结时钟：缺省冻结日＋`real` 须显式（**时钟面**；「帧 frozen_date」半面不属本块）」——**时钟面同物**、P0 **对**（「帧」半面取证见问答 15，不登记正确）；`pin-28`（`04a:37`「`run_id` 全盖章＋逐题 ledger 等值」）↔ 本块 `:149`「每次调用 `run_id` 盖章（**调用盖章面**）」——**同物**、P1 **对**。② **漏登核查（逐个判**）：`pin-02/03/04/09/10`（答案面内容/引标）→ 归 `answering`/`verification`，**不应登本块**；`pin-22/24/26`（`messages`/合同/对话层）→ 归 `state`/`agent-loop`；`pin-29`→`transport`/`agent-loop`；`pin-30`→`persistence`——**无应登而漏登项**；`04a` 全表**无 429-重试类**钉，故行为 6 无钉可登（挂测试，非漏）。③ **钉号/优先级**：`pin-25` P1／`pin-27` P0／`pin-28` P1——**全对**（`04a:34,36,37`）。④ **分工面**：`pin-28` 清楚（本块＝**调用盖章面**｜`state`＝字段面 `state.md:198`｜`persistence`＝落盘面｜`agent-loop`＝全盖章面）；`pin-27` 清楚（时钟面在本块、帧面他处）；**唯** `pin-25` 的「透传 calllog」半面——本块 `:17` 已把 calllog 写路径划给 `infra`，而 `specs/infra.md`（已定稿）**无 pin 登记**，该半面有「两头不认」之嫌（`低`，建议随 G-1 一并辨明归属）。

**15 真源引用真实且该节真有事实？** **有发现——G-1（`infra.md` 无该事实）。** 逐条核实为真：`recon/L3` 的 Completer／GatewayChatModel／calllog／eval_clock 段**全在**（`L3:111-186`／`:190-248`／`:252-284`）——「**重试与退避在何处**」＝`GatewayChatModel._agenerate`（`L3:164-186`，429 退避循环）✔；「**alias 缺省两处不同源**」＝D-L3-12（`L3:202`「替身硬编码 `petro-main` vs 生产默认别名在网关 routing.default」）✔；「**`run_id` 经 `**params` 上行被剥除**」＝D-L3-10（`L3:185`「生产 `GatewayService` 在 `service.py:_DOMAIN_ONLY_PARAMS` 剥除 note/run_id」）✔；`iface/P9b2` **T-P9b2-37**（评测冻结钟）**实存**（`P9b2:151`）✔；`eng/04 §五`（织网地基）实存（`eng/04:47-55`）✔。**不实／不符**：`specs/infra.md`（无失败分类单源，G-1）。**特别核**（上块复审结论）：规格 `:130` 称「`frozen_date` 只出现在**评测跑批 jsonl 记录**（非 SSE 帧）」——本子代理 `grep -rn "frozen_date" appv2 web eval` 核实：命中共 **4 处 `.py`**（`appv2/runtime/eval_clock.py:14,36,69`／`appv2/runtime/__init__.py:40,61,240`／`eval/results/tools/rerun.py:87,130-131,509-521`）＋ **`eval/results/*.jsonl`**；**`frozen_date` 在 SSE 帧代码（`graph.py`/`executor.py`/`events.py`/`wire.py`/`bridge.py`）与 `web/` **零命中****——**该结论属实，未发现相反证据**（`pin-27` 的「帧」＝跑批 jsonl 记录）。

**16 卡级问题（只报不改）？** **有发现，均非「卡须重做」。** ① 卡注路径笔误 `tests/runtimev2/gateway_adapter/fake.py`（G-5，卡面欠账）；② 卡公开面漏 `EVAL_FROZEN_DATE_DEFAULT/REAL` 两常量（G-7）；③ 与 `## bookkeeping` 卡的形状桥接留白（G-4，建议窗 A 补，**卡由窗 A 可改**）。**职责／边界／依赖三面未见卡错**；卡级修正（async／`ModelReply`／不留自由 `params`／评测时钟入面）**本身自洽**（与 R5b/R6 不冲突、与 `state` 行为 12/13 不冲突）。**无「卡须回阶段 2 重做」的结论。**

## 四、闸实跑记录（2026-10-15）

```
$ uv run python tools/check_specs.py
spec gate: PASS（0 警告）                                    # exit 0

$ uv run python tools/ref_resolvable.py check
真源引用可解析闸绿：18 份规格的真源引用与边界规则编号均可解析。   # exit 0

$ uv run lint-imports --config tools/importlinter_v2.toml
Analyzed 129 files, 509 dependencies.
... （R1–R8 逐条 KEPT；含 R7 / R8 / V2 B6）
Contracts: 18 kept, 0 broken.                               # exit 0

$ uv run lint-imports            # 默认 pyproject.toml（V1 侧）
Analyzed 115 files, 557 dependencies.
... B6 供应商 SDK 唯一接触点（litellm 只在 infra.llm_client——gateway 是唯一消费方） KEPT (1 ignored import)
Contracts: 6 kept, 0 broken.                                # exit 0

$ uv run ruff check app appv2 tests migrations tools
All checks passed!                                          # exit 0

$ uv run mypy app appv2
Success: no issues found in 169 source files                # exit 0

$ uv run pytest tests/runtimev2 -q
45 passed in 0.33s                                          # exit 0
```

辅助取证命令（关键）：
- `grep -nE "尽量|合理|必要时|视情况" specs/gateway_adapter.md` → **exit 1（0 命中）**。
- `grep -n "^## " specs/gateway_adapter.md` → 10 节，标题逐字有序。
- `uv run pytest tests/runtimev2/test_gateway_adapter_fake.py -q` → **14 passed**；`uv run pytest tests/runtimev2 --collect-only -q` 分文件＝ **fake 14 ／ frozen_clock 8 ／ leg_replay 23 ＝ 45**（**G-3 依据**）。
- `grep -rn "frozen_date" appv2 web eval` → 仅 `appv2/runtime/eval_clock.py`／`appv2/runtime/__init__.py`／`eval/results/tools/rerun.py`（＋`eval/results/*.jsonl`）；**SSE 帧代码与 `web/` 零命中**（问答 15 依据）。
- `sed -n '16,17p;107,122p' appv2/infra/llm_client.py` → `classify_upstream_failure`＝可切/不可切二值，**429→`UpstreamRejected` 不可切**（**G-1 依据**）。
- `sed -n '7p;50,110p' appv2/tools/registry.py` → `classify_exception` 三分类，429→`CATEGORY_RETRYABLE`（**G-1 依据**）。
- `cat specs/infra.md`（全 58 行）→ **无失败分类单源**（**G-1 依据**）。
- `grep -n "root_package\|forbidden_modules\|B6" pyproject.toml` → V1 `root_package="app"`（`:60`）、B6 `source=["app"]`（`:88-94`）（**G-2 依据**）；`grep -n "V2 B6" tools/importlinter_v2.toml` → `:56`。
- `sed -n '113,117p' tools/importlinter_v2.toml` → **R7 的 `source` 不含 `gateway_adapter`**（问答 5 依据）。
- `ls tests/runtimev2/` → **无 `gateway_adapter/` 子目录**（**G-5 依据**）；`git status --short` → `M appv2/runtimev2/gateway_adapter/{__init__,fake}.py`／`M tests/runtimev2/test_gateway_adapter_fake.py`／`M specs/modules.md`／`?? specs/gateway_adapter.md`。
- `grep -n "gateway_adapter" docs/runtime-refactor/00-决议与方法.md` → 流水 30（`:101`）＋流水 17（`:87`，45 测归 `tests/runtimev2/`）。

### 未验证清单

1. `tests/domains/test_v2_gateway_adapter.py` **不存在**（`ls` 无）——13 行绑定它的验收测试只能核标识形态，**无法实跑**（阶段 5）；`tests/runtimev2/test_gateway_adapter_fake.py` 的 3 行**已实跑全绿（14 测）**。
2. 本块「实现层真合规」（R5b/R6/R7 契约）为**契约空过**（gateway_adapter 无生产实现）——契约存在且 KEPT 已实测，实现层待阶段 5。
3. **G-1** 的严重度取决于评审对「`infra` 失败分类单源是否已成立、`specs/infra.md` 是否应承载该单源」的判定：本清单按「真源不实＋与 infra 实判 429＝不可切 相悖」维持 **高**。若判「分类将随重写重立单源、现锚仅指模块」可降为中。
4. **G-6**（`frozen_date()` `real` 态返回 `date` 还是 `None`）须辨明——卡 `modules.md:489` 写 `-> date`、现状 `eval_clock.py` 返回 `None`，两者不一致，待定「有意收正 vs 笔误」。

---

## 五、L0 处置表（逐条清零 · 2026-10-15）

> 规格文本由 **L0 直接落笔**；**卡级修正**（窗 A 权限）同批落 `specs/modules.md`（含 `## bookkeeping` 卡补桥接句）。

| 编号 | 处置 | 落法 |
|---|---|---|
| **G-1**（高） | **采纳 → 改锚＋分层辨明** | 删「判据单源在 `specs/infra.md`」这一不实锚（该规格无失败分类）。改述：**可重试性的判据在本块成闭世界**（`rate_limited`｜`timeout`｜`upstream_unavailable`｜`rejected`；前两类可重试），并**分层辨明**——`infra` 侧现状判据回答「**要不要切备用部署**」（429 **不切**），本块回答「**同一个调用要不要再试一次**」（429 **可重试**），**两者不是同一判据、不许并成一句**；现状锚改为 `appv2/infra/llm_client.py`（二值）＋ `appv2/tools/registry.py`（三分类），并记「旧码 429 重试判据是旧 `appv2/runtime/llm.py` 私有重写（`recon/L3` D-L3-03）」。**跨块待办登记**：供应侧失败分类**单源化**（`infra` 规格侧）——本块只摄入＋映射，不新造第二张阈值表 |
| **G-2**（中） | **采纳** | litellm 红线四处改锚 **V2 B6 契约**（`tools/importlinter_v2.toml`：`litellm` 唯一接触点＝`appv2.infra.llm_client`——**这才是覆盖 `appv2` 的面**）；`pyproject.toml` 的 V1 B6（`root_package=app`，**不检查 `appv2`**）降格为先例锚并写明其不覆盖 |
| **G-3**（中） | **采纳** | 「45 测」误挂单文件——四处改准为「**该件 14 测；`tests/runtimev2/` 目录合计 45 测**」 |
| **G-4**（中） | **采纳（两处同补）** | 行为 1 补**桥接规则**：`bookkeeping.call_model` 从状态取 `run_id` → 调本块 `complete` → **向节点只回 `content`**，**回执的用量与归因面交 bookkeeping 记账并进 Manifest**（禁裸文本吞掉记账面）；`## bookkeeping` 卡同批补同款一句 |
| **G-5**（低） | **采纳 → 已改卡** | 卡注路径笔误（`tests/runtimev2/gateway_adapter/fake.py` 不存在）改为「替身 `appv2/runtimev2/gateway_adapter/fake.py` ＋包根导出；看守件 `tests/runtimev2/test_gateway_adapter_fake.py`」 |
| **G-6**（低） | **采纳 → 辨明为有意收正** | `real` 态定为**恒回当日真实日期**（读 `infra.clock`）——**有意收正**现状 `resolve_eval_frozen_date` 在 `real` 时回 `None`、交调用方另取钟的两处判据漂移；卡面 `-> date` 与此一致，规格已写明差异 |
| **G-7**（低） | **采纳 → 已改卡** | `## gateway_adapter` 卡公开面补 `EVAL_FROZEN_DATE_DEFAULT`／`EVAL_FROZEN_DATE_REAL` 两常量 |
| **G-8**（低） | **采纳** | 接口定义注明 `ModelReply` 是**块级单一定义**（本批暂寄居替身文件；阶段 5 迁至非替身模块、替身改 import——**禁两处各定义一套**） |
| **G-9**（低） | **采纳** | ① 来源行删 `specs/state.md 行为 15` 之引（`Manifest.as_dict` 与本块回执形状非同一物）；②「何时调用模型」的锚由 `agent-loop.md` 行为 2（那是**调用前的上下文编译**）改为**行为 1（四相位循环）／行为 3（发射判据）** |
| **G-10**（低） | **采纳** | 删风险 5 括号内的裸字面值（冻结点日期），只留真源指针——数字单点、规约「本规格不复制取值」自洽 |

**净结果**：10 条**全部采纳**（G-1 为高、含分层辨明与跨块登记；G-4／G-5／G-7 涉卡、由窗 A 亲改）。**无升 Owner 的业务裁决项**；**无「卡须回阶段 2 重做」**。

---

## 六、复审结论（独立子代理）

- 复审日期：2026-10-15 ｜ 复审对象：`specs/gateway_adapter.md`（修订稿）＋ `specs/modules.md` 同批卡级修正 ｜ 上轮评审件＝本文件 §二／§五
- 纪律：只读＋只追加；凡断言均附实读行号或实跑证据，未证实者标「疑点」。

### 6.1 逐条闭合核验（G-1…G-10）

| 编号 | 判定 | 证据（文件:行 ＋ 实读文本／实跑） |
|---|---|---|
| **G-1** | **未闭合**（半改：`:18`／`:85` 已改，`:64` 及 `:30/:125/:129` 残留且自相矛盾） | **已改**：`:18`（不做什么行）与行为 7（`:85`）按分层重写——`:85`「可重试性的判据**在本块成闭世界**…`infra` 侧回答「要不要切备用部署」（429 不可切）；本块回答「同一个调用要不要再试一次」（429 可重试）…**跨块待办**：把供应侧失败分类**单源化**（`infra` 规格侧）」。**未改（残留）**：接口节 bullet `:64` 仍写「**失败分类闭世界（复用 `infra` 单源，不另立）**…——判据单源在 `infra`（`specs/infra.md`），本块只消费其结论。」——① 与 `:85`「本块成闭世界」**直接矛盾**；② 重新写死上轮判为不实的锚 `specs/infra.md`（实读该文件 57 行，`grep -n "classify\|可切\|不可切\|三分类\|429\|rate" specs/infra.md` → **exit 1、0 命中**）。另 `:30`（触及模块）「分类判据单源（本块只消费）」、`:125`（依赖）「分类判据单源」、`:129`（风险 3）「判据复用 `infra` 单源」三处以**现在时**称 infra 为分类单源，与 `:85`「跨块待办（尚未成单源）」相悖。`grep -n "infra.md\|单源" specs/gateway_adapter.md` → 命中 `:18,:30,:64,:125,:129`。 |
| **G-2** | **闭合** | `:72` 改锚「**R7 契约**（`forbidden` 列 `appv2.infra.llm_client`、`source` **不含** gateway_adapter——例外面）＋ **V2 B6 契约**（`tools/importlinter_v2.toml`…**这才是覆盖 `appv2` 的面**；`pyproject.toml` 的 V1 B6 其 `root_package=app`、只覆盖 V1 包，仅作先例锚）」；`:75`／`:146` 同改 V2 B6。**契约实核**：`pyproject.toml:60` `root_package="app"`＋`:88-91` B6 `source_modules=["app"]`、`forbidden=["litellm"]`（不覆盖 appv2）；`tools/importlinter_v2.toml:56-59` V2 B6 `source=["appv2"]`、`forbidden=["litellm"]`；逐 token 核（`grep -o`）R7（`:116`）`source` **不含** gateway_adapter、R5b（`:103`）／R6（`:110`）**含** gateway_adapter。实跑 `lint-imports` 双配置 6／18 KEPT。无残留。 |
| **G-3** | **闭合** | 四处口径一致：`:89`（行为 11）「**14 测**全绿」；`:121` 验收注「全绿（该件 14 测；`tests/runtimev2/` 目录合计 45 测全绿）」；`:133`（风险 7）「全绿（14 测；目录合计 45 测）」；`:153`（挂钩表）同。实跑：`uv run pytest tests/runtimev2/test_gateway_adapter_fake.py -q` → **14 passed**；`uv run pytest tests/runtimev2 -q` → **45 passed**。 |
| **G-4** | **闭合** | 规格 `:79`（行为 1）桥接规则「`call_model` 从状态取 `run_id`、以 `(messages, caller, run_id)` 调本块 `complete`，**向节点只回 `content`**，而 `ModelReply` 的用量与归因面…交给 `bookkeeping` 记账并进 Manifest」；`specs/modules.md:331` `call_model` 行尾注同款「从 state 取 run_id → 调 gateway_adapter.complete → 向节点只回 content；回执的用量/归因面归本块记账（禁裸文本吞掉记账面）」。两处口径一致。 |
| **G-5** | **闭合** | `specs/modules.md` 卡级修正注已改「同批回写：替身 `appv2/runtimev2/gateway_adapter/fake.py` ＋ 包根 `__init__.py` 导出…随规格同步维护的看守件＝`tests/runtimev2/test_gateway_adapter_fake.py`」；`ls tests/runtimev2/` 无 `gateway_adapter/`。旧错路径已不见。 |
| **G-6** | **闭合** | `:55` 接口注「`real`→**当日真实日期**（读 `infra.clock`）」；`:87`（行为 9）「`real` → 当日真实日期…必须显式指定…**这一取向是对现状的有意收正**（现状 `resolve_eval_frozen_date` 在 `real` 时回 `None` 交调用方另取钟…本块统一为**恒回一个日期**）」；实读 `appv2/runtime/eval_clock.py:49-50` 确为 `real→None`，规格已辨明差异为有意收正。 |
| **G-7** | **闭合** | `specs/modules.md` `## gateway_adapter` 公开面（`:483-490`）已列 `EVAL_FROZEN_DATE_DEFAULT: date`／`EVAL_FROZEN_DATE_REAL: str`，与规格 `:53-54` 对应。 |
| **G-8** | **闭合** | 规格 `:36` 类型注「**块级单一定义**：阶段 5 迁至非替身模块，替身只 import——禁双定义」＋`:47-48` 同款补注；代码实核 `ModelReply` 唯一定义在 `appv2/runtimev2/gateway_adapter/fake.py:28-29`，包根 `__init__.py:10` 转发（`from …fake import ModelReply, ScriptedCompleter`）。 |
| **G-9** | **闭合** | 来源行 `:4` 已删 `specs/state.md 行为 15` 之引，锚改「`specs/agent-loop.md` 行为 1（四相位循环）／行为 3（发射判据）」；「不做什么」行 2（`:16`）同步改同锚。实读 `agent-loop.md:79`＝行为 1（四相位循环）、`:114`＝行为 3（发射判据），锚实。`grep -n "state.md\|行为 15"` → 仅 `:20` 引「`state.md` 行为 10／13」（限额行，另物，正确）。 |
| **G-10** | **闭合** | `grep -n "2026-08-31\|2026-8-31" specs/gateway_adapter.md` → **0 命中**；风险 5（`:131`）只留真源指针「数值真源＝`recon/L3`…与 `eng/04`…；**本规格不复制取值**」，裸字面值与「不复制」并存之矛盾已消。 |

### 6.2 结论

**9 条闭合、1 条未闭合（G-1）**。**不可定稿**——须先修项：**修复 G-1 残留**，即 `specs/gateway_adapter.md:64` 与行为 7（`:85`）对齐（删去「复用 `infra` 单源…`specs/infra.md`」表述，改为「本块成闭世界＋跨块单源化待办」），并同步 `:30`／`:125`／`:129` 的「分类判据单源」现在时表述。其余 9 条闭合、闸全绿、无非法残留。

---

## 七、新增发现清单（复审轮）

| 编号 | 严重度 | 发现 | 证据锚点 | 建议处置 |
|---|---|---|---|---|
| **GZ-1** | 低 | **「不做什么」表第 4 行（`:18`）自洽矛盾**：列 1「不做」＝「供应侧失败事实的采集（异常类型／HTTP 状态码的枚举与判据表）」，列 2「由谁承担」＝「**本块采集并出闭世界**（见行为 7）」——把**本块自己承担**的采集列进「不做」表（其余 7 行列 2 均为他块或「不做」）。系 G-1 改锚时把原「不做：失败分类判据／由 infra」行改写所致。 | `specs/gateway_adapter.md:18`（对照 `:15-22` 同表其余行） | 二选一：① 列 1 改为「失败分类判据的**跨块单源化**（现存两块判据）」，列 2＝`infra`（规格侧待办）；② 把本行移出「不做什么」表（本块确实承担采集）。仅措辞／表义，不动行为语义。 |
| **GZ-2** | 低 | **`:74` 括注「R1–R8 无 `gateway_adapter` 的边界条」与实况不符**：R5b（`tools/importlinter_v2.toml:103`）与 R6（`:110`）的 `source_modules` **含** `appv2.runtimev2.gateway_adapter`；R8（`:122-123`）的 `forbidden_modules` **含** `appv2.runtimev2.gateway_adapter`。准确表述应为「无**禁止本块引包内其它块**的契约」（该要求确无契约）。`:148` 挂钩行同措辞「R1–R8 无本块边界条」。 | `specs/gateway_adapter.md:74,148`；`tools/importlinter_v2.toml:103,110,116,122-123` | 改措辞为「无禁止本块引包内其它块的契约」，避免与 R5b／R6／R8 实况相抵。 |
| **GZ-3** | 低（疑点，归属缺失未证实） | **钉 `pin-25` 的「透传 calllog JSONL」半面在 `infra` 规格侧无落点**：`eng/04a:34` pin-25＝「`cached_tokens` **透传 calllog JSONL**；上游未上报时字段=0」。规格 `:149` 登记 pin-25 并称「逐调用透传」，但 calllog **写路径**归 `infra`（`:17`）；实读 `specs/infra.md`（57 行）**零 pin 登记、无 `calllog`／`cached_tokens` 字样**（`grep -n "pin\|calllog\|cached_tokens" specs/infra.md` → **exit 1**）。该半面在 infra 规格侧无落点，「两头不认」之嫌未消（上轮问答 14 已提，随 G-1 辨明者未见处理）。 | `specs/gateway_adapter.md:17,149`；`specs/infra.md`（全篇）；`docs/runtime-refactor/eng/04a-应钉行为清单.md:34` | 随 G-1 跨块登记一并：在 `infra` 规格侧或本块挂钩表显写 pin-25「calllog 透传」半面归属；或收窄本块登记为「未上报=0」单半面并注 calllog 半面挂 `infra`（待登）。 |

### 7.2 独立复跑判据 16 条（逐条一行结论）

1. **十节齐＋标题逐字？** 无发现——`grep -n "^## "` 得 10 节、顺序与 `docs/spec-format.md` §二之二一致（`目标:7／不做什么:11／触及的模块:24／接口定义:32／框架与依赖红线:69／行为约定:77／不降级与静默禁令:93／验收测试:100／依赖与风险:123／与闸的挂钩表:138`）。
2. **行为逐条可 assert／含糊词？** 无发现——`grep -nE "尽量|合理|必要时|视情况"` → **exit 1（0 命中）**；行为 1–13 各带【断言：…】。
3. **数字裸值／真源？** 无发现——裸日期已清零（`grep "2026-08-31"` 0 命中）；计数项「十个字段」（`:81`）自含、「14／45 测」与实测一致。
4. **不做什么锚点？** 无发现（GZ-1 属行义自洽，非锚缺失）——8 行俱带「由谁承担＋锚点」。
5. **框架红线闸名（含 R7 例外面／V2 B6／R5b／R6 的 source 真覆盖）？** 无发现——R5b／R6 `source` 含 gateway_adapter、R7 不含（例外面属实）、V2 B6 覆盖 `appv2`，均逐 token 实测。
6. **不降级与静默禁令？** 无发现——`:95-98` 四条，三条带「断言：」，首条「合法降级路径：无」为结论声明。
7. **验收测试（每行标识＋边界集／保留集）？** 无发现——16 行全绑标识；`:118` 边界集／`:119` 保留集两行俱在；替身 3 行标识实存并实跑 14 passed。
8. **挂钩表与「已真跑」？** 无发现——`:146`「V1 6 KEPT／V2 18 KEPT」属实（双配置实跑）；`:140` spec gate 只校两项属实。
9. **与 `walk/` 决策冲突？** 无发现——零判断面（`:91`）与 `判断归责表`／裁决 #7／#4 不冲突。
10. **覆盖（S1 单元＋三处划界）？** 无发现——calllog 写路径归 `infra`（`:17`）／提示词装配归 `prompts`（`:15`）／发起单点归 `bookkeeping`（`:15`）三处划界在册且与卡一致。
11. **总纪律残留？** 无发现——`:91` 明文本块零判断（不读词表、不判语义）。
12. **与模块卡一致？** 无发现（G-5／G-7 已闭合）——职责／公开面／依赖与卡 `modules.md:480-490` 对齐。
13. **接口与已定稿规格逐字对账？** 无发现——`state`（行为 10／13 实核 `state.md:116,119`）／`persistence`／`transport` 三处分工互不矛盾。
14. **钉登记（全表 `pin-25/27/28`）？** **有发现——GZ-3**（pin-25 半面疑点）；`pin-25／27／28` 同物、优先级（P1／P0／P1）与 `04a:34/36/37` 一致，无漏登／错号。
15. **真源真实存在且含该事实？** 无发现（`specs/infra.md` 不实锚已在 G-1）——`recon/L3`、`iface/P9b2`、`eng/04`、`agent-loop` 各锚实存。
16. **卡级问题？** **有发现——GZ-1（规格内、非卡）／GZ-2（规格内、非卡）**；卡面 G-5／G-7 已改准。**无「卡须回阶段 2 修改」的结论**（卡级修正自洽，与 R5b／R6 及 `state` 行为 12／13 不冲突）。

### 7.3 闸实跑记录（复审轮，2026-10-15）

```
$ uv run python tools/check_specs.py
spec gate: PASS（0 警告）                                    # exit 0
$ uv run python tools/ref_resolvable.py check
真源引用可解析闸绿：18 份规格…                                # exit 0
$ uv run lint-imports --config tools/importlinter_v2.toml
Contracts: 18 kept, 0 broken.                               # exit 0
$ uv run lint-imports            # 默认 pyproject.toml（V1 侧）
Contracts: 6 kept, 0 broken.                                # exit 0
$ uv run ruff check app appv2 tests migrations tools
All checks passed!                                          # exit 0
$ uv run mypy app appv2
Success: no issues found in 169 source files                # exit 0
$ uv run pytest tests/runtimev2/test_gateway_adapter_fake.py -q
14 passed                                                   # exit 0
$ uv run pytest tests/runtimev2 -q
45 passed                                                   # exit 0
```

关键辅助取证：`grep -n "infra.md\|单源" specs/gateway_adapter.md` → `:18,:30,:64,:125,:129`（**G-1 残留依据**）；`grep -n "classify\|可切\|不可切\|三分类\|429\|rate" specs/infra.md` → **exit 1**；`grep -n "2026-08-31" specs/gateway_adapter.md` → **0 命中**；逐 token 核 `tools/importlinter_v2.toml:103/110/116`（R5b/R6 含 gateway_adapter、R7 不含）；`grep -n "pin\|calllog\|cached_tokens" specs/infra.md` → **exit 1**（GZ-3 依据）。

---

## 八、复审轮新增发现的 L0 处置（2026-10-15）

| 编号 | 处置 | 落法 |
|---|---|---|
| **G-1 残留**（未闭合项） | **采纳 → 收净** | 接口节那条「失败分类闭世界（复用 `infra` 单源，不另立）」改为「**失败类别闭世界（本块自立，见行为 7）**：四类、前两类可重试」＋明写「**分类判据不在 `infra` 侧现成单源**（现状两处不同判据）」；连带清三处现在时表述：触及模块的 `infra` 行（改为「消费其**原始失败事实**，不复用其判据」）、依赖行、风险 3（改为「类别映射单点在本块、与 `infra` 切备判据**分层**」） |
| **GZ-1**（低） | **采纳** | 「不做什么」第 4 行**行义矛盾**（把本块承担的采集写进「不做」列）改为本块**不做**的那件事：「**供应侧失败分类的单源化**（把现状两处判据归一）→ `infra` 规格侧（登记待办）」，本块只摄入＋映射 |
| **GZ-2**（低） | **采纳** | 两处括注「R1–R8 无 gateway_adapter 的边界条」不实（R5b／R6 的 `source` 都含本块）——改为「**无该面的专属闸**：R5b 只覆盖框架、R6 只覆盖引擎、V2 B6 只覆盖 `litellm`，都没有『本块只许依赖 `infra`／不出现裸 HTTP 客户端』这一面」 |
| **GZ-3**（低） | **采纳** | `pin-25` 的**落痕面**（calllog JSONL 逐调用写行）归属写明：**归 `infra`（`specs/infra.md` 侧）**、**登记待补**；本块只挂**回执面**（字段必在场、未上报＝0）——两头不认之嫌消除 |

**净结果**：复审 10 条＝**9 闭合／1 未闭合（G-1 残留）**；新增 3 条（全低）全部采纳并清；**必须先修的 G-1 残留在本批清完**。**无升 Owner 项**、**无「卡须回阶段 2 修改」**。
