# V2 网关桥（gateway_adapter）

状态: 已定稿
来源: `specs/modules.md` `## gateway_adapter` 卡、`docs/runtime-refactor/recon/L3-网关与支撑小件.md`（Completer／GatewayChatModel／calllog／eval_clock 段）、`docs/runtime-refactor/iface/P9b2-对接面出向-引擎与基建.md`（T-P9b2-37 测评冻结钟）、`docs/runtime-refactor/synth/S1-重写单元与证据交叉矩阵.md`、`docs/runtime-refactor/eng/04-测试网设计.md` §五（织网地基）、`specs/agent-loop.md` 行为 1（四相位循环）／行为 3（发射判据）
版式: `docs/spec-format.md`（节标题按该文 §二之二 逐字命名） ｜ 工序: `docs/spec-process.md`

## 目标

模型调用的**唯一出口桥**：一次调用的入参面、回执面、限流重试与退避、测试替身、评测冻结时钟——**供应商与路由细节不出本块**，运行时各相位只能从这里出去。

## 不做什么

| 不做 | 由谁承担 | 锚点 |
|---|---|---|
| 提示词／指令／合同的装配（**给模型看什么**） | `prompts`（装配）＋`bookkeeping` 的 `call_model` 单点（发起） | `specs/modules.md` `## prompts`／`## bookkeeping` |
| 「何时调用模型、调几次」的循环与相位决策 | `orchestration`／各相位 | `specs/agent-loop.md` 行为 1（四相位循环）／行为 3（发射判据） |
| 调用记录的落盘（calllog JSONL 的写路径） | `infra`（B6 出口内部）——本块只**传归因面**（`caller`／`run_id`） | `specs/modules.md` `## infra`；`appv2/infra/gateway/calllog.py` 自述 |
| **供应侧失败分类的单源化**（把现状两处判据归一） | `infra` 规格侧（**登记待办**）——本块只**摄入＋映射**（见行为 7） | `recon/L3-网关与支撑小件.md`（两分类现状＋旧码 429 私有重写 D-L3-03） |
| 事件与帧（模型产出如何变成页面帧） | `transport` | `specs/transport.md` |
| 限额／预算判定 | `state`（判定）＋`bookkeeping`（落地） | `specs/state.md` 行为 10／13 |
| **自由参数透传**（`**params` 一类「供应商参数随便传」的口子） | **不做**——调参在本块内单点；本块不对外开自由键 | 本规格行为 2 |
| 用程序替模型做语义判断（本块零判断：只转发与记账） | **不做** | `docs/runtime-refactor/walk/判断归责表.md` |

## 触及的模块

| 模块 | 改动类型 | 说明 |
|---|---|---|
| gateway_adapter | 新增 | 本块本体：调用桥 ＋ 回执形状 ＋ 重试退避 ＋ 测试替身 ＋ 评测时钟 |
| bookkeeping | 新增 | 节点侧调模型单点 `call_model`（本块只出桥面） |
| infra | 新增 | 供应侧唯一出口（B6：`llm_client`／`gateway.complete`）——本块消费其出口与**原始失败事实**（异常类型／状态码），不复用其判据（见行为 7） |

## 接口定义

```python
@dataclass(frozen=True, slots=True)
class ModelReply:                      # 一次模型调用的回执（**块级单一定义**：阶段 5 迁至非替身模块，替身只 import——禁双定义）
    content: str                       # 应答正文（失败尝试时为空串）
    caller: str                        # 归因：调用方标识（三桶族，见行为 5）
    run_id: str                        # 归因：所属 run（计费可对账——钉 pin-28 的调用盖章面）
    alias: str                         # 实际服务的模型别名（路由结果，随回执返回）
    prompt_tokens: int
    completion_tokens: int
    cached_tokens: int                 # 上游未上报时 **=0**（钉 pin-25）
    usage_estimated: bool              # 用量是否估算（非上游实数）
    duration_ms: int
    error: str | None                  # 非 None＝失败尝试（失败也留痕；content 为空串）
# 注：本批该类型暂寄居 `appv2/runtimev2/gateway_adapter/fake.py`（织网地基先行），**唯一定义**；
# 阶段 5 落地生产桥时迁至非替身模块并由包根转发，替身改为 import——**不许两处各定义一套**。

async def complete(messages: Sequence[Mapping[str, str]], *, caller: str, run_id: str) -> ModelReply: ...

# ── 评测冻结时钟（本块承接；数值真源见「依赖与风险」）──────────
EVAL_FROZEN_DATE_DEFAULT: date         # 缺省冻结日
EVAL_FROZEN_DATE_REAL: str             # 显式走真实时钟的唯一取值
def frozen_date() -> date: ...         # 冻结「今天」：未设/空串→缺省冻结日；real→**当日真实日期**（读 `infra.clock`）；非法→抛错

# ── 测试替身（同面——织网地基件，已随本规格回写）─────────────
class ScriptedCompleter:
    async def complete(self, messages, *, caller: str, run_id: str = "") -> ModelReply: ...
    calls: list[tuple[str, list[dict[str, str]]]]    # 公开留痕属性（测试断言专用）：逐调用 (caller, messages 拷贝) 快照
    def counts(self) -> dict[str, int]: ...          # per-caller 计数桶（观测面）
    def messages_of(self, caller: str) -> list[list[dict[str, str]]]: ...   # 逐轮 messages 回看
```

- **失败类别闭世界（本块自立，见行为 7）**：`rate_limited`｜`timeout`｜`upstream_unavailable`｜`rejected` 四类——本块的重试**只对前两类**（429／超时／网络错／5xx）退避重试，**后两类不重试、不误伤**。**分类判据不在 `infra` 侧现成单源**（现状是两处不同判据：可切／不可切 与 三分类）；本块做**摄入＋映射（单点）**，并把「供应侧分类单源化」登记为跨块待办。
- **`alias` 与自由 `params` 不进入参面**：模型调参在本块内单点（现阶段无对外调参面）；服务别名由路由决定并**随回执返回**。**`run_id` 必须进面**（每次调用盖章）。
- **错误契约**：可重试类重试耗尽、不可重试类当场 → **抛错（原异常上抛，fail-closed）**；由 `orchestration` 收口（转 `run_failed` 通知＋正常收束）。**本块不返回哨兵、不吞错**。
- 真源：`specs/modules.md` `## gateway_adapter` 卡（签名以卡为准；卡面已随本规格收正为 async ＋ `ModelReply`）。

## 框架与依赖红线

- **无点名框架**（本块不引入任何框架）。对应闸：**R5b 契约**。
- **模型供应商唯一出口＝`infra`**（`llm_client`／`gateway.complete`；B6）——本块是全工程**唯一允许**直引该出口的 runtimev2 块。对应闸：**R7 契约**（其 `forbidden` 列 `appv2.infra.llm_client`、`source` **不含** `gateway_adapter`——正是本块的例外面）＋ **V2 B6 契约**（`tools/importlinter_v2.toml`：`litellm` 唯一接触点＝`appv2.infra.llm_client`，**这才是覆盖 `appv2` 的面**；`pyproject.toml` 的 V1 B6 其 `root_package=app`、**只覆盖 V1 包**，仅作先例锚）。
- **不直引引擎**（`knowledge`／`query`／`retrieval`）。对应闸：**R6 契约**。
- **不引包内其它块**（本块只依赖 `infra`）。对应闸：**无该面的专属闸 → 人审**（原因：R5b 只覆盖框架、R6 只覆盖引擎，**没有**「本块只许依赖 `infra`」这一面；可降维面＝AST 断言「本块 import 只出现 `infra`」）。
- **禁手写替代**：不得自建 HTTP 客户端／供应商 SDK 直连（绕开 B6 出口）。对应闸：**V2 B6 契约**（`tools/importlinter_v2.toml`：`litellm` 唯一接触点＝`appv2.infra.llm_client`）＋ **无专属闸的半面 → 人审**（降维面＝AST 断言「本块不出现 `httpx`／`requests`／裸 SDK」——V1 B6 不覆盖 `appv2`，不能当本块的闸）。

## 行为约定

1. **唯一出口＋桥接单点**：运行时内所有模型调用都经本块的 `complete`；**发起方**是 `bookkeeping` 的 `call_model` 单点（其余相位不得自行发起）。**桥接规则**：`call_model` 从状态取 `run_id`、以 `(messages, caller, run_id)` 调本块 `complete`，**向节点只回 `content`**，而 **`ModelReply` 的用量与归因面（`caller`／`run_id`／token／`cached_tokens`／`alias`／`duration_ms`）交给 `bookkeeping` 记账并进 Manifest**——别让裸文本吞掉记账面。断言：全仓扫描——模型调用点只出现在本块与 `bookkeeping` 的该单点；记账面字段可由回执取到。
2. **入参面固定三件**：`messages`（消息序列）／`caller`（关键词）／`run_id`（关键词）；**无自由 `params`**。断言：签名参数集合恰为此三者（+`self`）；传未知键报错。
3. **回执面恒全键**：`ModelReply` 十个字段**恒在场**（失败尝试时 `error` 非 None、`content` 为空串）；`cached_tokens` **上游未上报时 =0**（不缺口、不省略——钉 `pin-25`）。断言：成功／失败两路径的回执键集合相等。
4. **`async` 是硬要求**：`complete` 是协程（真实 I/O）；**不得在事件循环内同步阻塞调用**。断言：`inspect.iscoroutinefunction(complete)`。
5. **归因面逐调用保留**：每次调用把 `caller` 与 `run_id` 交给出口（记账归因面），**逐调用不合并、不覆盖**；`caller` 取值来自调用方（三桶族：理解／决策／作答）。断言：逐调用留痕可按 `caller`／`run_id` 分组（替身 `calls`／`counts()`／`messages_of()` 与 calllog 行同口径——`calls` 测试断言专用）。
6. **重试只对可重试类**：限流／超时／网络错／5xx → 按配置的**重试次数与退避**重试（缺省值以现状 env 面 `appv2/runtime/llm.py`（:47-49）的 `GATEWAY_429_RETRIES`／`GATEWAY_429_BACKOFF` 为**现状锚**——env 可覆写；**正式数值阶段 5 随真机定**，本规格不复制字面值）；**4xx 业务性拒绝不重试**（不误伤）。断言：注入非限流失败 → 一次即抛（调用计数＝1）；注入限流失败 → 重试到上限后抛（调用计数＝上限）。
7. **可重试性的判据在本块成闭世界，且与「切备」分层（两件事，不许并成一句）**：合法失败类别＝`rate_limited`（429）｜`timeout`｜`upstream_unavailable`（网络错／5xx）｜`rejected`（4xx 业务性拒绝）；**可重试＝限流／超时／网络错／5xx（三类：`rate_limited`／`timeout`／`upstream_unavailable`）；不可重试＝`rejected` 等客户端拒绝（4xx 业务性拒绝）**——2026-10-16 回改（流水 53-D）：原「前两类可重试、后两类不可重试」与行为 6／接口注／B7b 前提（网络错可重试）相抵，按行为 6 落，本批只回改此句（行为 6／接口注未动）。**分层辨明**：`infra` 侧的现状判据回答的是「**要不要切备用部署**」（网络错／超时／5xx 可切；**429 不可切**——换部署救不了请求本身）；本块回答的是「**同一个调用要不要再试一次**」——**429 可重试**。两者判据方向不同、都不是对方。现状锚：`appv2/infra/llm_client.py`（可切／不可切二值）与 `appv2/tools/registry.py`（三分类，429→可重试）；旧码的 429 重试判据是旧 `appv2/runtime/llm.py` 的私有重写（漂移风险见 `recon/L3-网关与支撑小件.md` D-L3-03）。**跨块待办**：把供应侧失败分类**单源化**（`infra` 规格侧）——本块只做**摄入＋映射**，不新造第二张阈值表。断言：类别映射只在本块出现一次（单点函数）；`rejected` 类一次即抛、`rate_limited`／`timeout` 类重试到上限。
8. **重试耗尽 fail-closed**：重试耗尽或不可重试类 → **原异常上抛**（不返回空应答、不静默降级为「无材料」）；收口归 `orchestration`。断言：耗尽路径抛错且最后一个回执的 `error` 非 None（失败尝试也留痕）。
9. **评测冻结时钟**：`frozen_date()` 的解析规则——环境变量**未设或空串 → 缺省冻结日**（`EVAL_FROZEN_DATE_DEFAULT`，数值真源见「依赖与风险」）；**`real` → 当日真实日期**（读 `infra.clock`；**必须显式指定**，不得默认走真实钟）——**这一取向是对现状的有意收正**（现状 `resolve_eval_frozen_date` 在 `real` 时回 `None` 交调用方另取钟，两处判据易漂移；本块统一为「**恒回一个日期**」，取真实钟的细节封在本块内）；**ISO 日期 → 该日**；**非法值 → 抛错**（fail-fast，不静默回落）（钉 `pin-27` 的**时钟面**）。**生产装配路径不得读该环境变量**（只经显式注入缝）。断言：四种输入各按其规则；非法值抛错。
10. **用时与用量如实**：`duration_ms`／token 计数实测（非估算时 `usage_estimated=False`）；**估算必须显式标注**（不许把估算当实数——`usage_estimated` 就是那个机读信号）。断言：估算路径 `usage_estimated=True`；实测路径为 `False`。
11. **替身与生产桥同面**：测试替身 `ScriptedCompleter` 的 `complete` 与生产桥**同形签名（替身 `run_id` 可缺省＝测试便利，生产面必填）与同一回执形状**（`async`／关键词参数／`ModelReply`），离线零触网；观测面 `calls`／`counts()`／`messages_of()` 只读留痕（`calls` 为公开留痕属性，**测试断言专用**）、**不改注入剧本**。断言：替身测试 `tests/runtimev2/test_gateway_adapter_fake.py` **14 测**全绿（含签名卡面行）。
12. **替身不静默兜底**：未剧本化 caller 且未设 `default` → **当场抛错**（不静默返回空串）；设了 `default` 则照回且**调用照样留痕**（兜底不静默丢）。断言：无 `default` 时抛错、有 `default` 时计数含该 caller。
13. **本块零判断**：不读词表、不判语义、不做业务分支（只有「可重试／不可重试」这类由 `infra` 判据给出的结构分派）。断言：AST 扫描本块源码。

## 不降级与静默禁令

- **合法降级路径：无**（本块不降级：调用失败＝原异常上抛，由 `orchestration` 收口成 `run_failed` 通知；**不得**把失败静默改写成「无材料」「未找到」这类业务话术）。
- **失败必须留痕**：失败尝试同样产出回执（`error` 非 None）且**同样进记账归因面**（`caller`／`run_id` 齐备）。断言：失败路径的留痕条数＝尝试次数。
- **估算必标注**：`usage_estimated` 是「这是估算」的机读信号，不得恒定值。断言：两条路径取值不同。
- **冻结时钟不得静默回落真实钟**：`real` 必须显式（行为 9）。断言：未设环境变量时取缺省冻结日（≠ 真实当日）。

## 验收测试

| 验收标准 | 对应测试 |
|---|---|
| 唯一出口：模型调用点只在本块与 `bookkeeping.call_model` | `tests/domains/test_v2_gateway_adapter.py::single_model_egress` |
| 入参面固定三件、无自由 `params`（未知键报错） | `tests/domains/test_v2_gateway_adapter.py::params_face_fixed` |
| 回执十键恒在场；`cached_tokens` 未上报＝0（`pin-25`） | `tests/domains/test_v2_gateway_adapter.py::reply_all_keys_and_cached_zero` |
| `complete` 是协程 | `tests/domains/test_v2_gateway_adapter.py::complete_is_async` |
| 归因面逐调用保留（`caller`／`run_id` 可分组） | `tests/domains/test_v2_gateway_adapter.py::attribution_per_call` |
| 非限流失败一次即抛（不误伤）；限流失败重试到上限 | `tests/domains/test_v2_gateway_adapter.py::retry_only_on_retryable` |
| 分类判据不在本块另立 | `tests/domains/test_v2_gateway_adapter.py::no_second_classification_source` |
| 重试耗尽 fail-closed：原异常上抛＋失败留痕 | `tests/domains/test_v2_gateway_adapter.py::exhausted_fail_closed` |
| 冻结时钟四分支（缺省／`real`／ISO／非法）＋生产不读 env | `tests/domains/test_v2_gateway_adapter.py::frozen_clock_four_branches` |
| 用量实测与估算可区分（`usage_estimated`） | `tests/domains/test_v2_gateway_adapter.py::usage_estimated_flagged` |
| 替身与生产桥同面（签名＋回执形状） | `tests/runtimev2/test_gateway_adapter_fake.py::TestCardFace::test_complete_signature_matches_card` |
| 替身不静默兜底（无 default 抛错；有 default 照回且留痕） | `tests/runtimev2/test_gateway_adapter_fake.py::TestDefaultFallback::test_unscripted_without_default_fails_fast` |
| 替身观测面只读（注入剧本不被改写、留痕为调用时刻快照） | `tests/runtimev2/test_gateway_adapter_fake.py::TestObservationFaces::test_script_injection_readonly` |
| 本块零判断（AST 扫描） | `tests/domains/test_v2_gateway_adapter.py::no_judgement_in_gateway_adapter` |
| 【边界集】空 messages／超长 messages／限流失败／非法时钟值 → 各落对应分支 | `tests/domains/test_v2_gateway_adapter.py::boundary_empty_huge_ratelimit_clock` |
| 【保留集】常规成功调用的回执字段与归因行为不变 | `tests/domains/test_v2_gateway_adapter.py::retention_normal_call_unchanged` |

> **测试文件归属**：生产桥与时钟的验收测试绑**新建** `tests/domains/test_v2_gateway_adapter.py`（阶段 5 落地时建）；**替身面**（卡片面／兜底／观测面）已由织网地基件 `tests/runtimev2/test_gateway_adapter_fake.py` 实测看守——本批已按新接口面回写并**全绿（该件 14 测；`tests/runtimev2/` 目录合计 45 测全绿）**（该件由替身随规格同步维护）。

## 依赖与风险

- 依赖：`infra`（供应侧出口 B6／原始失败事实／时钟）｜`recon/L3` 的网关事实（现状锚）｜`eng/04` §五（织网地基口径）。
- 风险与对策（每条带检测手段）：
  1. **供应商 SDK 旁路**（自建 HTTP 客户端绕开 B6 出口）→ 对策＝红线「不直引 SDK」＋AST 断言。检测＝`::single_model_egress` ＋ **人审**（无专属闸的半面）。
  2. **同步桥阻塞事件循环** → 对策＝行为 4（async 硬要求）。检测＝`::complete_is_async`。
  3. **重试误伤**（把 4xx 业务拒绝当限流重试、或反之）→ 对策＝行为 6／7（只对可重试类；类别映射单点在本块，且与 `infra` 的「切备」判据**分层**不混）。检测＝`::retry_only_on_retryable`／`::no_second_classification_source`。
  4. **`cached_tokens` 缺口或假值**（上游不报时漏字段／填 0 以外的猜测值）→ 对策＝行为 3（恒在场＋未上报＝0）。检测＝`::reply_all_keys_and_cached_zero`。**已知事实**：现用上游（MiniMax 面）不上报该字段。
  5. **冻结时钟被默认真实钟**（评测失去可复现性）→ 对策＝行为 9（`real` 须显式）。检测＝`::frozen_clock_four_branches`。**数值真源**＝`recon/L3-网关与支撑小件.md` 的 `resolve_eval_frozen_date` 段与 `eng/04-测试网设计.md`（冻结点由 Owner 拍板，取值只在真源一处）；**本规格不复制取值**。
  6. **`pin-27` 的「帧 `frozen_date` 全在场」半面**：经码面取证，`frozen_date` 只出现在**评测跑批 jsonl 记录**（非 SSE 帧）——该半面**不属本块**（属评测跑批记录面），**呈主窗**（建议 `eng/04a` 钉文措辞改准）。检测＝**人审**。
  7. **替身与生产桥脱节**（替身留在旧接口）→ 对策＝行为 11 同面＋本批已回写替身与包根导出。检测＝`tests/runtimev2/test_gateway_adapter_fake.py` **全绿（14 测；目录合计 45 测）**。
  8. **`alias` 语义漂移**（现状生产装配传空别名、替身缺省别名两处不同源）→ 对策＝行为 5 把 `alias` 收进**回执**（实际服务别名由路由给，调用方不再传）。检测＝回执断言 ＋ **人审**。
  9. **估算用量被当成实数计费** → 对策＝行为 3／10（`usage_estimated` 机读信号）。检测＝`::usage_estimated_flagged`。
  10. **调参面缺失**（当前无对外调参键）→ 若将来要按 caller 调参，**属规格变更**（须同批改接口与卡）。检测＝**人审**（本批登记）。

## 与闸的挂钩表

| 本规格的硬要求 | 挂钩 | 现状 |
|---|---|---|
| 验收测试逐行有标识 ／ 触及模块名已声明 | spec gate（**该闸只校这两项**——十节标题不在其作用面） | 已进 CI |
| 十节标题齐备、逐字、有序 | **人审** | 原因：仓内无标题闸（登记：可降维为一条标题机检） |
| 真源引用可解析（路径／边界规则编号／被引卡片在册） | 真源引用闸 `tools/ref_resolvable.py` | 已进 CI |
| 不引框架 | 边界闸 **R5b** | 已真跑 |
| 模型供应商唯一出口＝`infra`（本块是全工程唯一允许面） | 边界闸 **R7**（其 `source` 不含本块——例外面）＋ **V2 B6 契约**（`tools/importlinter_v2.toml`） | 已真跑（`lint-imports` 双配置：V1 6 KEPT／V2 18 KEPT） |
| 不直引引擎 | 边界闸 **R6** | 已真跑 |
| 不引包内其它块／不自建 HTTP 客户端 | **无该面的专属闸 → 人审**（降维 AST 断言登记待补） | 原因：R5b 只覆盖框架、R6 只覆盖引擎、V2 B6 只覆盖 `litellm`——**都没有**「本块只许依赖 `infra`／不出现裸 HTTP 客户端」这一面 |
| `cached_tokens` 未上报＝0（**回执面**）；「透传 calllog JSONL」的**落痕面**归 `infra`（`specs/infra.md` 侧）——**登记待补**，本块不冒充覆盖 | 钉 **`pin-25`**（P1）；测试 `::reply_all_keys_and_cached_zero` | 待织网（阶段 5） |
| 冻结时钟：缺省冻结日＋`real` 须显式（时钟面；「帧 `frozen_date`」半面不属本块） | 钉 **`pin-27`**（P0，时钟面）；测试 `::frozen_clock_four_branches` | 待织网（阶段 5） |
| 每次调用 `run_id` 盖章、计费可对账（**调用盖章面**） | 钉 **`pin-28`**（P1；落盘面挂 `specs/persistence.md`、全盖章面挂 `specs/agent-loop.md`）；测试 `::attribution_per_call` | 待织网（阶段 5） |
| 重试只对可重试类、判据不另立、耗尽 fail-closed | 测试 `::retry_only_on_retryable`／`::no_second_classification_source`／`::exhausted_fail_closed` | 待实现 |
| 替身与生产桥同面、不静默兜底 | 测试 `tests/runtimev2/test_gateway_adapter_fake.py`（织网地基件，本批已回写） | **已实测全绿（该件 14 测；目录合计 45 测）** |
| 本块零判断 | AST 断言 `::no_judgement_in_gateway_adapter` | 待实现（阶段 5） |
| 卡级修正（async／`ModelReply`／不留自由 `params`／评测时钟入面） | **人审** | 原因：无「卡与规格一致」机检闸；本批已改卡＋回写替身与包根导出并记施工流水 |
| 「不做什么」的纯范围排除（不装配提示词／不落盘 calllog／不建自由参数面） | **人审** | 接不上闸的原因：纯范围排除没有形状／存在性／退出码判据；能降维的部分（不引框架／引擎／SDK 直连）已由边界闸 R5b／R6／B6 覆盖 |
