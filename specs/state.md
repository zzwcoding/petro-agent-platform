# V2 状态与限额（state）

状态: 已定稿
来源: `specs/modules.md` `## state` 卡、`docs/runtime-refactor/walk/06-过程图-循环挂起判断.md`、`walk/裁决表.md` §06-A／§06-B、`synth/S1`（H1／H8）、`synth/S5`（RunState 字段矩阵）、`recon/I2a-状态常量与清单.md`、`recon/I2b-RunState全字段.md`、`recon/K-上下文事件指南预算.md`（budget.py 段）
版式: `docs/spec-format.md`（节标题按该文 §二之二 逐字命名） ｜ 工序: `docs/spec-process.md`

## 目标

全运行期的**状态与限额单一形状真源**：运行状态字段形状、模型调用 Manifest、受理与回执载荷、闭世界常量族、限额参数表与触界**判定**结果形状——**纯数据形状＋纯计算**，零行为分支、零模型调用、零落盘、零业务语义判断。

## 不做什么

| 不做 | 由谁承担 | 锚点 |
|---|---|---|
| 状态迁移与路由决策（谁把状态改成什么、下一步走哪） | `orchestration` | `specs/agent-loop.md` 行为 8；`specs/modules.md` `## orchestration` |
| 触界收敛的**落地写入**（把判定结果写进状态） | `bookkeeping`（唯一写口） | `specs/modules.md` `## bookkeeping` |
| 检查点／运行记录／黑匣子／审计落盘 | `persistence` | `specs/modules.md` `## persistence` |
| 事件与帧的发射（含触界注记的发帧） | `transport` | `specs/modules.md` `## transport` |
| 任何模型调用（本块连模型出口类型都不引用） | `gateway_adapter` | `specs/modules.md` `## gateway_adapter` |
| 语义判断（限额触界＝纯数值比较；禁词表／正则参与判定） | **本块不做**；语义判断归各相位的模型产出 | `docs/runtime-refactor/walk/判断归责表.md` |
| 限额数值的复述（数值只许引真源） | 引数值真源（`recon/K` R-K-72…R-K-78 逐键 ＋ `walk/裁决表.md` §06-A 循环上限五项） | `docs/runtime-refactor/recon/K-上下文事件指南预算.md` |

## 触及的模块

| 模块 | 改动类型 | 说明 |
|---|---|---|
| state | 新增 | 本块本体：字段形状 ＋ 闭世界常量 ＋ 限额参数 ＋ 触界判定（纯计算） |
| bookkeeping | 新增 | 触界收敛的唯一写口与公共簿记入口（本块只交形状与判定结果） |
| orchestration | 新增 | 受理载荷与回执的消费侧、状态迁移方（本块只出形状） |

## 接口定义

```python
# ── 运行状态 ──────────────────────────────────────────────
@dataclass(slots=True)                      # 可变图状态（非 frozen）
class RunState: ...                         # 字段集＝synth/S5 矩阵全量（逐字段读写方见该表）

# ── 模型调用 Manifest（骨架逐字真源 recon/I2a）────────────
@dataclass(frozen=True, slots=True)
class Manifest:
    source_type: list[str]
    source_id: list[str]
    version: list[str | None]
    trust_level: list[str]
    selected_reason: str
    token_count: int
    transform: str
    material_total: int
    material_rendered: int
    material_truncated: bool
    def as_dict(self) -> dict[str, Any]: ...

# ── 受理载荷与回执（不可变；与 specs/agent-loop.md 接口定义逐字一致）──
@dataclass(frozen=True, slots=True)
class AskRequest:
    question: str | None = None
    resume_run_id: str | None = None
    followup_run_id: str | None = None
    actor: Actor
@dataclass(frozen=True, slots=True)
class AskChoice:
    kind: Literal["clarify", "external_table_approval"]
    choice: str | None = None
    decision: Literal["approve", "reject"] | None = None
    approval_id: str | None = None
@dataclass(frozen=True, slots=True)
class RunHandle:
    run_id: str
    stream: AsyncIterator[SseEvent]
    cursor: int
SseEvent = Mapping[str, Any]                 # 帧载荷的结构别名（形状真源在 transport；本块不 import——R4）

# ── 限额参数与触界判定 ────────────────────────────────────
@dataclass(frozen=True, slots=True)
class Budget: ...                            # 键集闭世界（行为 10）；数值不落本规格
@dataclass(frozen=True, slots=True)
class LimitHit:
    limit: Literal["rounds", "discovers_per_round", "executes_per_round",
                   "seconds", "tool_timeout", "discovers_per_run", "ask_cap"]
    used: float
    cap: float
@dataclass(frozen=True, slots=True)
class Convergence:
    hit: tuple[LimitHit, ...]                # 空元组＝未触界
    notice: dict[str, Any] | None            # 触界必带（恰三键）；未触界恒 None
def check_limits(state: RunState) -> Convergence: ...   # 纯函数：不改入参、不写状态、无 IO
```

- **闭世界常量族**（本块导出、全体消费）：`STEP_KINDS`（step 类型六值）｜`RUN_STATUS_KINDS`（run 状态四值）｜`INTENT`（路由意图十值）——三族都是 **`RunState` 字段的取值域**。取值与条数真源＝`recon/I2a-状态常量与清单.md`（22 条常量实测）；本规格不复述取值。**通知类型（`notice.type`）的闭世界不属本块**——它是帧载荷面，归 `transport`（其规格定稿时须立该闭世界并落定取值真源）。
- **三类不可变载荷的形态闭世界**：`AskRequest` 三形态——仅 `question`＝提问｜`resume_run_id`＝断线重连｜`question`＋`followup_run_id`＝追问续会话；`resume_run_id` 与 `followup_run_id` 同在场＝判失败。`AskChoice.kind`＝`clarify`｜`external_table_approval`；`AskChoice.decision`＝`approve`｜`reject`｜`None`。越界值一律判失败。
- **`RunHandle` 的结构别名**：`SseEvent` 只作类型别名（帧载荷是 JSON 对象），**形状真源在 `transport`**；本块不 import 任何 runtimev2 块（R4），故以别名表示，别名不得承载行为。
- **错误契约**：形态／枚举越界 → **抛参数错误**（由 `api`／`orchestration` 映射成对外错误码，映射表不在本块）；本块**不吞错、不返回哨兵值**。
- 真源：`specs/modules.md` `## state` 卡（签名以卡为准）。

## 框架与依赖红线

- **无点名框架**（本块不引入任何框架；`langgraph`／`langchain` 只许活在 `orchestration`）。验收写法：依赖锁文件不出现框架包 ＋ 行为测试绿。对应闸：**R5b 契约**。
- **不 import runtimev2 内任何其它块**（本块是最底层数据形状，防环）。对应闸：**R4 契约**（本批已按边界规则卡面文本把 forbidden 补全到公共层九块，并以探针验证：植入违规 import → BROKEN，移除 → 18/18 KEPT）。
- **模型出口零接触**：本块不含模型调用、不引用模型出口。对应闸＝**两闸合覆盖**：不直引 `appv2.infra.llm_client`＝**R7 契约**；不引 `gateway_adapter`＝**R4 契约**（本批补全后的 forbidden 含它。单挂 R7 属部分覆盖——R7 的 forbidden 只含 `infra.llm_client` 一面）。
- **不直引引擎**（`knowledge`／`query`／`retrieval`）。对应闸：**R6 契约**。
- **外部依赖只许 `infra`**（身份对象 `Actor` 的类型）。对应闸：**无专属闸 → 人审**（原因：R1–R8 里没有「依赖白名单」这一面）；**可降维的部分＝四闸合覆盖**——不引包内其它块＝**R4**、不引框架＝**R5b**、不引引擎＝**R6**、不直引 `appv2.infra.llm_client`＝**R7**，另加 **B6 出口纪律**（`appv2` 全层禁 litellm）。
- **禁手写替代**：本块不产帧、不调模型、不落盘，故无「自建通路」面；将来若需帧类型，只许引用 `transport` 的**结构别名**（见接口定义），不得自建第二套帧形状。对应闸：**无专属闸 → 人审**（原因：R1–R8 无「不许出现自建帧类型符号」一面；降维面＝AST 断言「本块不出现自建帧类型符号」，登记待补）。

## 行为约定

1. **字段集单点**：`RunState` 字段集＝`synth/S5` 矩阵全量；**增删字段必须同批改该矩阵与全部读写方**。断言：`{f.name for f in fields(RunState)}` 与矩阵首列集合相等（集合比较，不判顺序）。
2. **两类形态**：`RunState` **可变**；`Manifest`／`AskRequest`／`AskChoice`／`RunHandle`／`Budget`／`Convergence`／`LimitHit` **全 `frozen=True, slots=True`**。断言：对不可变类实例赋值抛错；对 `RunState` 赋值成功。
3. **状态可投影**：`RunState` 全部字段值是 JSON 原语（`json.dumps(asdict(state))` 成功）——这是「跨进程恢复无损」的结构前提。断言：全字段 fixture 可序列化。唯一例外是 `RunHandle.stream`（非状态字段）。
4. **`messages` 只追加不改写**（钉 `pin-22`，P0）：`messages` 是整条对话链，每次模型调用发送**整链**，任意相邻两次调用互为前缀延伸（`后[:-len(尾段)] == 前`）。断言：两轮脚本化调用后前缀关系成立；**任何替换／重排历史条＝判失败**。
5. **相位合同一次性**（钉 `pin-24`）：`contracts_appended` 记录已追加过合同文本的相位；**回炉轮不重发**。断言：同一相位二次进入后，`messages` 中该相位合同条数不变、标记写入幂等。
6. **对话层纯度**（钉 `pin-26`）：`dialogue` 只装**自然对话**——条目形态固定为 `{role, content, origin}`：`role` ∈ `user`｜`assistant`（同 `messages` 口径）；`origin` 是**来源闭世界**，合法值仅三——`user_verbatim`（用户原话）｜`assistant_final`（assistant 终稿）｜`clarify_approval_replay`（澄清与审批回收原文）。任务书、相位指令、过程原话、注记前缀只入 `process_notes`（有界摘要）。**`origin` 是本次重写自立的新结构**：现状 `dialogue` 条目只有 `role`／`content`、无来源标签，过程记录与自然对话同链混装（现状锚点＝`docs/runtime-refactor/arch/P5b1-对话状态重构方案.md` 与 `recon/I2b-RunState全字段.md` 的条目形态）——**待 Owner 过目**，阶段 5 以本规格为准。断言：注入含任务书与指令的一轮后，每个 `dialogue` 条目都带 `origin` 且取值落在三值内（越界即失败）——过程内容要混进 `dialogue` 只能伪造来源标签，伪造即越界被抓。
7. **追问播种＝前轮终链整链承接**（钉 `pin-23`，P0）：`followup_of` 非空的新 run，其 `messages` 以**前 run 检查点终链整条**为前缀（不裁剪、不摘要化），再接新问。断言：跨 run 前缀关系成立（后 run 链前 N 段与前轮终链逐字相等）。
8. **旧检查点如实读入**（钉 `pin-30` 的**状态字段面**）：v1／v2 旧检查点读入**不抛错**；`dialogue` 是兼容字段、本块对它**零业务写**（不得伪造或补写历史）；`schema_version` 真值真源＝`synth/S3-口径裁决清单.md` C-07。断言：读入 v1 fixture → 不抛错；`schema_version` 取读入态；`dialogue` 无本块写入点（AST＋行为双证）。（**分工**：「旧 run 的对话通道在**黑匣子回放**时如实空显」那一条断言归 `specs/persistence.md` 行为 12——同一钉的另一面，两处不各写一遍。）
9. **三族常量为闭世界且单点消费**：`STEP_KINDS`／`RUN_STATUS_KINDS`／`INTENT` 只在本块定义；**任何写入口的取值必须 ∈ 对应族**，越界抛错；**每族必须有真实消费点**（禁「定义了没人用」）。断言：越界值抛错；全仓无第二处自建状态集合、无裸状态字面量参与把守（`grep`／AST）。
10. **限额参数键集闭世界**：`Budget` 键＝轮数／轮内发现／轮内执行／段时长／单工具超时／全 run 发现／连续反问上限；**数值与缺省值只引真源**（`recon/K-上下文事件指南预算.md` R-K-72…R-K-78 逐键承载七项 ＋ `docs/runtime-refactor/walk/裁决表.md` §06-A 承载循环上限五项），**常量定义与合同文本同源引用、不重复硬编码**。断言：`Budget` 键集合相等；缺键取缺省、禁散落的兜底字面量。
11. **触界判定确定、纯、不改入参**：`check_limits` 同输入两次结果相等；调用前后入参深比较相等；无 IO、无模型、无随机。断言：两跑结果相等 ＋ `asdict` 深比较相等。
12. **触界必带如实注记**：`hit` 非空 ⇔ `notice` 非 None（`notice` 恰三键 `type`／`gates`／`content`，形状真源＝`synth/S6-事件与帧目录.md` §一）；**未触界恒 `notice is None`**（不得凭空产注记）。断言：超限 fixture → `hit` 非空且注记三键在场；未超限 → `hit` 为空元组且 `notice is None`。
13. **触界不静默**：触界时若未落 `budget_hit` 即判失败；「未完成项」明细由 `bookkeeping` 装配进注记（红线＝`arch/P7a-交接包与挂账清单.md` A-P7a-37「不许静默」）。断言：`Convergence` 与 `budget_hit` **同现**。
14. **受理三形态互斥**（钉 `pin-29` 的**形状面**；闭环面挂 `specs/agent-loop.md`）：`resume_run_id` 与 `followup_run_id` 同在场 → 抛参数错误；`AskChoice.kind`／`decision` 越界 → 抛错。断言：非法组合抛错、合法三形态各自构造成功。
15. **Manifest 全键恒出**：`as_dict()` 恒返回与字段同名的全部键；列表值返回**拷贝**（改返回值不改原对象）。断言：键集合相等 ＋ 拷贝语义成立（这是「同一件事多处数字」的预防面）。
16. **本块零判断、零 IO**：无词表／正则语义判定、无模型调用、无落盘。断言：AST 扫描本块源码——无模型调用、无事件发射、无 DB／文件读写、无语义词表。

## 不降级与静默禁令

- **合法降级路径：无**（数据形状不降级；限额触界**不是降级**，是契约内的**有界终止**）。
- 触界必须产生**机读信号**（本块承诺面＝两处）：`budget_hit`（状态字段）＋ `Convergence.notice`（恰三键）；断言：两处同现（行为 13）。**第三处「触界步的过程记录（计数与命中项）」是消费方义务**——由 `bookkeeping` 的写口落账并在其规格中断言，本块不冒充覆盖。
- **唯一允许的「降级」是旧检查点读入**：缺字段按 `schema_version` 补缺省并**如实标注**（禁伪造历史）；机读信号＝`schema_version` 取值 ＋ 读入注记；断言：v1 fixture 读入后 `schema_version` 为读入态、对话通道空显（行为 8）。
- **不许自述完成**：完成判定归程序侧（`verification`／`orchestration`）；本块只承载状态取值，**不判断完成**。

## 验收测试

| 验收标准 | 对应测试 |
|---|---|
| 字段集与 `synth/S5` 矩阵一致（集合比较） | `tests/domains/test_v2_state.py::field_set_matches_matrix` |
| 不可变载荷全 `frozen+slots`、`RunState` 可变 | `tests/domains/test_v2_state.py::mutability_split` |
| 全字段 JSON 可投影（跨进程恢复无损前提） | `tests/domains/test_v2_state.py::state_json_projectable` |
| `messages` 只追加：相邻调用互为前缀延伸 | `tests/domains/test_v2_state.py::messages_append_only_prefix` |
| 相位合同一次性：回炉轮不重发、标记幂等 | `tests/domains/test_v2_state.py::contracts_appended_idempotent` |
| 对话层纯度：`dialogue` 条目 `origin` 全部落在来源闭世界内（不混层） | `tests/domains/test_v2_state.py::dialogue_layer_purity` |
| 追问播种＝前轮终链整链承接（跨 run 前缀延伸） | `tests/domains/test_v2_state.py::followup_seeds_full_chain` |
| 旧检查点如实读入（不抛错、对话通道空显、`schema_version` 如实） | `tests/domains/test_v2_state.py::legacy_checkpoint_read_honest` |
| 三族常量闭世界：越界取值抛错 | `tests/domains/test_v2_state.py::constant_families_closed_world` |
| 常量单点消费：无第二处自建集合、无裸状态字面量把守 | `tests/domains/test_v2_state.py::no_second_source_of_constants` |
| 限额参数键集闭世界、缺键取缺省（无散落字面量） | `tests/domains/test_v2_state.py::budget_keys_closed_world` |
| 触界判定确定、纯、不改入参 | `tests/domains/test_v2_state.py::check_limits_pure_and_deterministic` |
| 触界必带注记（恰三键）；未触界恒无注记 | `tests/domains/test_v2_state.py::converge_requires_notice` |
| `budget_hit` 与注记同现（触界不静默） | `tests/domains/test_v2_state.py::budget_hit_signal_present` |
| 受理三形态互斥、`AskChoice` 两枚举闭世界 | `tests/domains/test_v2_state.py::ask_payload_shape_closed_world` |
| `Manifest.as_dict` 全键恒出＋列表拷贝语义 | `tests/domains/test_v2_state.py::manifest_all_keys_and_copy` |
| 本块零判断零 IO（AST 扫描） | `tests/domains/test_v2_state.py::no_judgement_or_io_in_state` |
| 【边界集】空状态／超限状态／v1 旧态／异参受理 → 各落对应分支 | `tests/domains/test_v2_state.py::boundary_empty_overlimit_legacy_variants` |
| 【保留集】常规状态读写与未触界路径行为不变 | `tests/domains/test_v2_state.py::retention_normal_state_unchanged` |

> **测试文件归属**：本块验收测试绑**新建** `tests/domains/test_v2_state.py`（`state` 是阶段 2 新划的公共层块 `appv2/runtimev2/state/`，与现状 `appv2/runtime/state.py` 所在的旧码测试形状不同）；既有旧码测试本批不改。

## 依赖与风险

- 依赖：`infra`（身份对象类型）｜字段矩阵真源＝`synth/S5`｜数值真源＝`recon/K` R-K-72…R-K-78（逐键）＋ `walk/裁决表.md` §06-A（循环上限五项）。
- 风险与对策（每条带检测手段）：
  1. **卡与实装分叉（`converge` 双卡）**——两卡各列一个同签名函数。已裁：**判定**归本块（更名 `check_limits`，纯计算）／**落地写入**归 `bookkeeping` 唯一写口。检测＝卡与规格一致人审 ＋ 签名断言；已记施工流水。
  2. **共享写口无归属**（`synth/S5` 第四节的写手收敛问题）：`messages`／`steps`／`notices`／`next_intent` 几乎每个节点都写。对策＝写口归 `bookkeeping` 单点、本块**不提供写函数**。检测＝`bookkeeping` 侧的「禁旁路直写」测试（本批不新增）。
  3. **限额参数键集未定义**（现状 `budget: dict[str, float]`）。对策＝本块定闭世界键集。检测＝`::budget_keys_closed_world`。
  4. **`dialogue` 兼容字段两说**（注释称零读写，又称追问播种降级抽取用它）。对策＝定为**兼容读入面、零业务写**。检测＝`::legacy_checkpoint_read_honest` ＋ 钉 `pin-30`。
  5. **身份两类型面**（受理面是对象、状态里是字符串投影）。对策＝转换点**唯一**在 `orchestration` 受理段，本块两处形状各自固定。检测＝类型断言；**转换点单一性＝人审**（无对应闸）。
  6. **草稿字段两义**（空串＝待核验草稿；`direct`＝确定性直答）。对策＝保留闭世界取值，释义真源＝`specs/answering.md`。检测＝闭世界断言。
  7. **预算类与截断类分型双轨**（预算类落 `budget_hit`、截断类走通知分型）。对策＝两轨并存但**强制同现**（触界即须有注记）。检测＝`::budget_hit_signal_present`。
  8. **数值双源**（同一上限在合同文本与代码常量各写一遍、调用点再兜底字面量）。对策＝单点化到本块常量，文本与调用点引用常量。检测＝`grep` 无重复字面量断言 ＋ 人审。
  9. **字段重划漏项**：字段集改动若只改一侧即全链失配。检测＝`::field_set_matches_matrix` ＋ 阶段 5 逐字段读写方对账（人审）。
  10. **旧检查点迁移**：旧码 `schema_version` 真值见 `synth/S3-口径裁决清单.md` C-07，读入分流必须如实。检测＝`::legacy_checkpoint_read_honest`。
  11. **本块「不含行为」是纯范围排除**（没有形状判据）。对策＝降维为 AST 断言。检测＝`::no_judgement_or_io_in_state` ＋ 人审。
  12. **「统一预算表」是未落盘的引用名**（跨规格命名债）：`walk/裁决表.md` §06-A 只是一行循环上限、仓内无同名文件，而多份规格曾拿它当数值真源名。对策＝本规格改用**双指**（`recon/K` R-K-72…R-K-78 逐键 ＋ `walk/裁决表.md` §06-A 五项）；**改述对象＝`specs` 目录下 `grep -rn 统一预算表 specs` 的全量命中**（现含 `specs/agent-loop.md`、`specs/clarification.md`、`specs/tool_matching.md`）——其中 `specs/agent-loop.md` 三处**已由本批就地改述**，其余两份（含未提交改动）**登记待主窗统一改述**。检测＝真源引用闸（路径可解析）＋ **人审**（该节里是否真有那条事实）。
  13. **`dialogue` 条目的 `origin` 是本规格自立的新结构**（现状 `dialogue` 条目只有 `role`／`content`，无来源标签——现状锚点 `recon/I2b-RunState全字段.md`）：无现状真源可抄，属本次重写新立的设计。对策＝在规格里**列全合法值**并明标「本规格自立、待 Owner 过目」，阶段 5 以本规格为准。检测＝`::dialogue_layer_purity` ＋ **人审**（Owner 过目）。

## 与闸的挂钩表

| 本规格的硬要求 | 挂钩 | 现状 |
|---|---|---|
| 验收测试逐行有标识 ／ 触及模块名已声明 | spec gate（**该闸只校这两项**——十节标题不在其作用面） | 已进 CI |
| 十节标题齐备、逐字、有序 | **人审** | 原因：`tools/check_specs.py` 不校标题名／顺序，仓内无标题闸（登记：可降维为一条标题机检，本批未授权） |
| 真源引用可解析（路径／边界规则编号／被引卡片在册） | 真源引用闸 `tools/ref_resolvable.py` | 已进 CI |
| 不 import runtimev2 内任何其它块 | 边界闸 **R4**（本批补公共层九块＋探针验证） | 已真跑（18/18 KEPT） |
| 不引框架 | 边界闸 **R5b** | 已真跑 |
| 不直引引擎 | 边界闸 **R6** | 已真跑 |
| 不调模型／不直引模型出口（**两闸合覆盖**） | 边界闸 **R7**（不直引 `infra.llm_client`）＋ **R4**（不引 `gateway_adapter`） | 已真跑 |
| `RunState.messages` 只追加不改写（本块的**字段契约面**） | 钉 **`pin-22`**（P0）；测试 `::messages_append_only_prefix` | 待织网（阶段 5）；循环行为面同钉挂 `specs/agent-loop.md` |
| 追问播种＝前轮终链整链承接（**状态字段面**） | 钉 **`pin-23`**（P0）；测试 `::followup_seeds_full_chain` | 待织网（阶段 5）；播种动作面同钉挂 `specs/agent-loop.md` |
| 相位合同一次性（`contracts_appended`） | 钉 **`pin-24`**；测试 `::contracts_appended_idempotent` | 待织网（阶段 5） |
| 对话层纯度（`dialogue`／`process_notes` 不混层） | 钉 **`pin-26`**；测试 `::dialogue_layer_purity` | 待织网（阶段 5）；渲染面同钉挂 `specs/understanding.md` |
| 旧 run **状态字段读入**如实（`schema_version` 如实、`dialogue` 无业务写）——`pin-30` 另两面：**回放面**挂 `specs/persistence.md`；**compaction 半面**归 `context`（`synth/S1` H6／V2-79d）——该规格尚未定稿，**待 `context` 规格（窗 B 编写）定稿时登记** | 钉 **`pin-30`**（P2）；测试 `::legacy_checkpoint_read_honest` | 待织网（阶段 5） |
| `AskChoice` 的 `kind` 判别字段（**形状面**） | 钉 **`pin-29`**（P0，**闭环面挂 `specs/agent-loop.md`**）；本块测试 `::ask_payload_shape_closed_world` | 待织网（阶段 5） |
| 触界不静默（注记＋`budget_hit` 同现） | 测试 `::converge_requires_notice`／`::budget_hit_signal_present` | 待实现 |
| 限额数值单点（禁散落字面量） | 测试 `::budget_keys_closed_world`／`::no_second_source_of_constants` | 待实现 |
| 本块不含行为、不判语义、零 IO | AST 断言 `::no_judgement_or_io_in_state` | 待实现（阶段 5） |
| 卡与规格一致（`converge` 归属／公开面补全） | **人审** | 原因：无「卡与规格一致」的机检闸；本批已裁并记施工流水（`docs/runtime-refactor/00-决议与方法.md` 流水 20） |
| 「不做什么」的纯范围排除（不迁移／不落盘／不调模型） | **人审** | 接不上闸的原因：纯范围排除没有形状／存在性／退出码判据；能降维的部分（相位互不 import、模型出口唯一、不引引擎）已由边界闸 R4／R6／R7 覆盖 |

> **钉的字段面分工（避双头）**：分工判据＝**钉的主体是行为时，其载体字段不另挂本块**（如 `pin-06` 的 `empty_probes`、`pin-16` 的 `chain_switch_marks`、`pin-12` 的 `delivered_rows`／`obs_rows`——载体字段在本块、实质行为在他块，故只在他块登记）。据此以下三钉由**他块挂行为面**、本块只承载**字段／参数键面**，故不重复挂行为测——`pin-09`（`Manifest.material_truncated` 的**字段面**←本块；材料截断披露行为面←`specs/answering.md`）｜`pin-15`（连续反问上限的**参数键面**←本块；到顶截断与挂起不计轮行为面←`specs/clarification.md`）｜`pin-28`（`run_id` 的**字段面**←本块；全盖章与计费对账面←`specs/agent-loop.md`）。
