# V2 安全阀（gate）

状态: 已定稿
来源: `specs/modules.md` `## gate` 卡、`docs/runtime-refactor/walk/02-理解-词面安全阀.md`（§一 现状／§七 旧裁／§八 重估）、`docs/runtime-refactor/walk/03-理解-禁用词闸.md`（废弃词闸原貌与移出后归属）、`docs/runtime-refactor/walk/07-理解段重估.md`（§一／§五）、`docs/runtime-refactor/walk/裁决表.md`（项目级裁决 #3／#5／#12／#13；§02／§04★／§07）、`docs/runtime-refactor/walk/判断归责表.md`（词面安全阀行）、`docs/runtime-refactor/eng/00-阶段2-模块划分草案.md`（§三 C gate 行／§四 R2 注／§五 覆盖声明／§七 H12 行）、`docs/runtime-refactor/eng/04a-应钉行为清单.md`（pin-18／pin-31 原文）、`docs/runtime-refactor/arch/P5a1-票堆V2-66至69.md`（A-P5a1-01…14）、`docs/runtime-refactor/recon/B2-档案渲染与安全闸族.md`（L1353-L1468：R-B2-09…15／R-B2-21／R-B2-24／R-B2-25；D-B2-01…04／11…15）、`docs/runtime-refactor/recon/C-理解与legacy决策节点.md`（R-C-04／R-C-06／R-C-07／R-C-13）、`docs/runtime-refactor/synth/S1-重写单元与证据交叉矩阵.md`（H12 行）、`docs/runtime-refactor/synth/S4-调用图.md`（understand 入口调用位）、`docs/runtime-refactor/synth/S6-事件与帧目录.md`（notice 恰三键；refused 取值真源见 `specs/transport.md`）、`tickets/v2/V2-66-注入拦截闸.md`（逐字稿载体）、`tickets/v2/V2-67-外发写意图闸.md`（逐字稿载体）、`appv2/runtime/graph.py`（L1353-L1468 现行代码字面——迁移源）、`tests/domains/test_v2_n0_word_gates.py`（V1 钉测——A 类问句语料）、`specs/preconditions.md`、`specs/tool_matching.md`、`specs/transport.md`、`specs/bookkeeping.md`、`specs/state.md`、`specs/understanding.md`、`specs/agent-loop.md`、`specs/parsing.md`、`specs/context.md`
版式: `docs/spec-format.md`（节标题按该文 §二之二 逐字命名） ｜ 工序: `docs/spec-process.md`
块性: 本块＝**结构早退块**（真源 `docs/runtime-refactor/walk/判断归责表.md`——「词面安全阀｜明显中招/越界的快路径早退（不是判据）｜程序（仅辅助快路径）｜结构（早退）」）——三族判定＝闭世界词表子串／共现（结构早退，非判据）；**零语义判断**（豁免／意图／「提及 vs 执行」一律不落本块）；「只读」（INV-2）硬保证在**执行层**（真源 `docs/runtime-refactor/walk/裁决表.md` §07）。

## 目标

把入口问句里**明显中招／越界**的三类情形（注入／外发／写意图）做成一次**零模型零执行的词面早退**——命中即不放行、以固定话术拒答收口；本块是**辅助快路径、不承载红线**——「只读」（INV-2）的硬保证在执行层，漏判由执行层兜。

## 不做什么

| 不做 | 由谁承担 | 锚点 |
|---|---|---|
| 废弃词闸（判断与分派） | **判断**＝`tool_matching`（模型产出，与 `caliber_key` 同批）；**分派**＝`preconditions` 判定序第 1 位（机械分派）。Owner 裁决 #12 逐字：「**`gate` 只留安全阀**（注入／外发／写意图＝代码快路径），废弃词闸从 `gate` 移出」 | `docs/runtime-refactor/walk/裁决表.md` #12；`specs/preconditions.md` 判定序明文表；`specs/tool_matching.md` 行为面；`specs/modules.md` `## gate` 卡（职责行） |
| 卡面 `apply_term_verdict(verdict) -> Disposition` 符号 | **不施工**（已移出——见上）；卡面接口行与职责行的相抵＝卡级登记件（风险 7①，只登记不改卡） | `docs/runtime-refactor/walk/裁决表.md` #12 |
| 「提及 vs 执行」的语义判断＋豁免判定（元问／引用形） | 模型侧／**V2 不引入豁免**（裁决 §02-A「不加豁免」结论不变；**误伤面按已知接受态保留**——D-B2-01 元问共现形〔残留样本登记〕；真实收窄须 Owner 另裁） | `docs/runtime-refactor/walk/裁决表.md` §02／§04★ |
| 「只读」（INV-2）红线判定与承载 | **执行层**（无写／外发工具＋只读连接＝结构保证）——本块不承载红线 | `docs/runtime-refactor/walk/07-理解段重估.md` §五；`docs/runtime-refactor/walk/裁决表.md` §07 |
| 命中收口的**发射与落账执行**（notice／步／直答收口的执行面） | 入口消费方（理解相位）经 `bookkeeping` 写口；帧面归 `transport`（本块零 emit、零写） | `specs/bookkeeping.md`；`specs/transport.md`（`NOTICE_TYPES`）；`specs/understanding.md` 触及面「只消费其结论」 |
| 拒答话术轮的**对话链追加**与收口时点 | `bookkeeping`（追加唯一写口）＋编排面（时点） | `specs/bookkeeping.md` 行为 7（链只追加）＋行为 14（直答收口出口）＋行为 11（notice）；链尾收口时点＝编排面（agent-loop 未明写——登记） |
| 命中事件的**审计留痕**（`agent_v2.refused` 同源面——零新增审计型） | 审计唯一写口＝`security.audit`（`persistence`）；本块零审计写入 | `specs/persistence.md`；`docs/runtime-refactor/arch/P5a1-票堆V2-66至69.md` A-P5a1-03 |
| 任务书装配／模型调用／应答解析／定路由 | `understanding`（本块**零模型**——连 `gateway_adapter` 都不 import） | `specs/modules.md` `## understanding` |
| 逐子问题过闸（三态）与子问题级拒答 | `preconditions` | `specs/modules.md` `## preconditions` |
| 出数只认现行口径（结构约束） | `tool_matching`（旧名由本体账本归一） | `specs/tool_matching.md` 行为 7 |
| 台账／术语表读取（词典层缝） | **不做**——命中路径零 I/O（V1 的「当场再取一次词典层缝并写回」属现状缺陷 D-B2-02、无人读——重写不复刻，见差异点③） | `docs/runtime-refactor/recon/B2-档案渲染与安全闸族.md` D-B2-02 |
| 入口之后再被引导外发／写入的拦停（多轮场景） | 执行层兜底（本块只辖**入口**问句的词面快路径） | `docs/runtime-refactor/arch/P5a1-票堆V2-66至69.md` A-P5a1-14 |
| 用词表／正则替模型判语义 | **不做**——词表只作明显命中的结构早退（非判据） | `docs/runtime-refactor/walk/判断归责表.md` |

## 触及的模块

| 模块 | 改动类型 | 说明 |
|---|---|---|
| gate | 新增 | 本块本体：`screen` 三族判定（闭世界词表）＋`Refusal` 形状＋常量族（词表／话术／步标题） |
| state | 已定稿 | 卡面依赖行承接（卡面依赖＝`state`）；本块判定为纯文本进出、**零 state 字段与常量消费点**（收口步由消费方经 `bookkeeping` 产——行为 7 分工） |

## 接口定义

```python
# ── 卡面初拟形（逐字照录——真源 specs/modules.md `## gate` 卡）──
def screen(text: str) -> Refusal | None: ...              # 安全阀：明显中招／越界早退
def apply_term_verdict(verdict) -> Disposition: ...        # 废弃词闸：模型结论入、机械分派出
# 注：`apply_term_verdict` 一行与卡面职责行「废弃词闸已移出本模块」相抵——V2 定案＝
#     该件移出、不施工（判断归 tool_matching、分派归 preconditions 判定序第 1 位；
#     Owner 2026-10-15 裁决 #12）；两者差异＝卡级登记件（风险 7①，本规格不改卡）。

# ── V2 定案签名（名单＝本规格自定〔V2 承载位设计〕，逐成员真源见各行注；
#    逐件标【迁移】/【重建】）──
def screen(text: str) -> Refusal | None: ...
#   【迁移】安全阀判定（纯函数：文本 → 命中结论；三族先命先断、命中即返）。
#   现状载体＝appv2/runtime/graph.py `_n0_intent_word_gate` 及族内三 matcher
#   L1390-L1468；真源 docs/runtime-refactor/recon/B2-档案渲染与安全闸族.md
#   R-B2-09／R-B2-11／R-B2-12／R-B2-13；行为 1–5

@dataclass(frozen=True, slots=True)
class Refusal:
    family: Literal["injection", "outbound", "write"]   # 三族闭世界（收口步分型＝family＋"_refused"，
                                                         #  恰回 V1 三字面——R-B2-25）
    hit: str          # 命中槽值：注入＝模式词原形｜外发＝通道词｜写意图＝对象词（话术槽与步 term 取此值）
    content: str      # 拒答话术（三条模板逐字、槽已填——见下；恒非空）
#   【重建（V2 承载位设计）】V1 无此类型（_n0_refuse 直产 updates dict）——形状以本规格为准；
#   事实面真源 docs/runtime-refactor/arch/P5a1-票堆V2-66至69.md A-P5a1-03／08（收口三件套）

# ── 常量族（名单闭世界；文本＝逐字迁移，承载位换、文本不变——
#    逐字稿载体＝tickets/v2/V2-66-注入拦截闸.md ／ tickets/v2/V2-67-外发写意图闸.md
#    ＋现行代码 appv2/runtime/graph.py L1360-L1387）──
INJECTION_PATTERNS: tuple[str, ...] = (
    "忽略之前", "忽略你之前的", "无视之前", "ignore previous", "ignore all previous",
)
INJECTION_ANSWER_TEMPLATE = (
    "我注意到这句话包含「{feature}」——这类要求不会被执行，"
    "平台规则不可能被对话内容覆盖。"
)                                        # {feature}＝命中模式词原文（槽）
OUTBOUND_VERBS: tuple[str, ...] = (
    "发到", "发送到", "发送给", "发给", "推送到", "传到", "外传",
)
OUTBOUND_CHANNELS: tuple[str, ...] = (
    "邮箱", "邮件", "微信", "短信", "手机", "钉钉", "飞书", "外部系统",
)
OUTBOUND_ANSWER = (
    "本系统只读——未配置外发通道，数据不能发往邮箱、微信等外部渠道；"
    "可在本对话内查看，明细类结果可按行导出文本。"
)                                        # 固定话术（无槽）
WRITE_VERBS: tuple[str, ...] = (
    "下调", "上调", "调到", "调成", "改成", "改为", "写入", "删除", "停用", "启用",
)
WRITE_TARGETS: tuple[str, ...] = ("配注", "配产", "计划产量", "指标", "台账", "数据")
WRITE_ANSWER_TEMPLATE = (
    "本系统只读——不做任何写入或调整，「{target}」等生产参数不在本平台变更；"
    "如需变更请走线下变更流程。"
)                                        # {target}＝命中写对象词原文（槽）
# STEP_TITLES：family→标题映射闭世界（迁移照抄——与话术同批锁定）：
#   injection→「N0 注入拦截硬终止」／outbound→「N0 外发拦截硬终止」／write→「N0 写意图拦截硬终止」
#   （V1 字面——承载位 appv2/runtime/graph.py L1452／L1458／L1466；「N0」为迁移字面，
#    编号体系本身不入 V2——改名＝规格变更）
```

- **族名单是闭世界**：上列成员（`screen`＋`Refusal`＋常量族〔八件＋`STEP_TITLES` 映射〕）之外新增公开成员＝只许以「新增成员入名单＋同批对账消费方规格（`specs/understanding.md`／`specs/agent-loop.md`）」方式进块；消费方在相位块内私建同源副本（自写词表／话术字面）＝判失败（单点纪律，先例 `specs/parsing.md` 共用件单点）。
- **返回两态闭世界**：①`Refusal`（命中——三族先命先断、第一命中即返）；②`None`（未命中——闸静默）。**越界行为**：不在这两态内的返回形态（半成品、默认族、「疑似」形）＝判失败。
- **错误契约**：`screen` **不抛业务错**——任意 `str` 入参（含空串）恒返回两态之一；`Refusal` 构造越界（`family` 非三值／`hit` 空／`content` 空）＝判失败（fail-closed 抛错，不猜、不取默认）。
- **入参纪律**：纯文本进出（入口问句文本由调用方传入——本块**零 state 字段读**）；无时钟、无随机、无 IO、无模型；无数值面（本块词汇表外无任何额度／帽参数）。
- **Adapter 定界（卡面「固定词表 fixture」）**：本块依赖的唯一资料＝**模块内闭世界词表常量**；测试夹具＝固定词表 fixture（换词表内容不改 `screen` 签名与 `Refusal` 形状＝**替换面稳定声明**〔Seam 句见风险 1②〕；夹具只用于测命中面）；**零外部词源装载**（不读台账／名录／文件——命中路径零 I/O，见行为 12／13）。
- 真源：`specs/modules.md` `## gate` 卡（`screen` 签名逐字；`apply_term_verdict` 一行＝移出件）；**族成员（常量族＋`Refusal`）以本规格「V2 定案签名」为准**（卡面未列；补录需求＝卡级登记见风险 7①）。

## 框架与依赖红线

- **无点名框架**（本块不引入任何框架；纯字符串处理零依赖）。验收写法：依赖锁文件不出现框架包＋行为测试绿。对应闸：**R5b 契约**（`tools/importlinter_v2.toml` 的 source 含 `appv2.runtimev2.gate`——亲读属实）。
- **只许 import `state`（纯判定块）**：不引其余 runtimev2 块、不引旧码（`appv2.runtime.*`——**R5 契约**全包覆盖）。**诚实声明**：R1–R8 无「gate 依赖白名单」专属闸（R3 的 source 只列 parsing／prompts）；降维＝AST import 扫描测试（`::imports_state_only`），余面人审（见挂钩表）。
- **不引引擎**（`knowledge`／`query`／`retrieval`）＝**R6 契约**（source 含 `appv2.runtimev2.gate`——亲读属实）；**不直引 `appv2.infra.llm_client`**＝**R7 契约**（source 含 gate——亲读属实）。
- **零模型调用**——本块连 `gateway_adapter` 都不 import。**诚实声明**：R1–R8 无「gate 零模型」专属闸（R7 只咬 `appv2.infra.llm_client` 一面；R8 的 source 只列 preconditions／verification／execution）；降维＝AST 断言（`::imports_state_only`／`::screen_pure_deterministic`）。
- **消费方向（R2）的诚实声明**：R2 的 forbidden 现含九个公共层块深层子模块、**不含 `appv2.runtimev2.gate.*`**——契约实建九块 vs 设计注记「10 块全护（9 块公共层 ＋ `gate`）」（`docs/runtime-refactor/eng/00-阶段2-模块划分草案.md` §四）不一致；本块消费方（入口相位）只经包根消费＝规格层 doctrine；**补闸＝回阶段 2 登记**（风险 3）。降维＝AST 断言（登记待补）。
- **禁手写替代（判定单点）**：三族词表、三条话术与步标题映射（`STEP_TITLES`）在本 runtimev2 面内各恰一处定义，禁相位块另存副本（V1 病灶：注入词表双份并存、可各自演化且无防漂移断言——`docs/runtime-refactor/recon/B2-档案渲染与安全闸族.md` D-B2-11）。验收写法：runtimev2 面内唯一定义点断言（`::word_families_closed_world_single_source`）。

## 行为约定

1. **三族闭世界＋先命先断（序＝注入→外发→写意图）**：`screen` 按此固定序判定、**第一命中即返**；三族皆未命中 → `None`（闸静默）。断言：三族样本各归对应族；注入＋写意图同句 → `family="injection"`（真源 `docs/runtime-refactor/arch/P5a1-票堆V2-66至69.md` A-P5a1-13；`docs/runtime-refactor/recon/B2-档案渲染与安全闸族.md` R-B2-09；`docs/runtime-refactor/recon/C-理解与legacy决策节点.md` R-C-04）。
2. **注入族判据（逐字迁移）**：五条模式（清单见接口定义）**大小写折叠（casefold）子串**匹配；命中 → 返回**列表序首个命中的模式原形**（槽值）。断言：五条各命中；英文大小写样本折叠命中；无关问句 `None`（真源 A-P5a1-02；R-B2-11）。
3. **外发族判据（逐字迁移）**：动词（七条）×通道（八条）**同问句共现**（子串；**不折叠**）才命中——单一词面不拦（降误伤）；命中 → 返回**列表序首个命中的通道词**（槽值）。断言：正样本命中且槽值＝通道词；「有动词无通道」「有通道无动词」两单边 → `None`（真源 A-P5a1-09；R-B2-12）。
4. **写意图族判据（逐字迁移）**：动词（十条）×对象（六条）共现才命中（**对象按列表序取首个命中者**＝可观测面；取序实现含动词按列表序取首个在场者——**无外显面〔实现细节〕**）；命中 → 返回**对象词**（槽值；动词分量不携——差异点②）。断言：正样本命中且槽值＝对象词；两单边 → `None`；多对象样本对象取序对（真源 A-P5a1-11；R-B2-13）。
5. **匹配方式三族面（迁移照抄）**：注入折叠、外发／写意图不折叠（纯子串）——三族不齐＝V1 事实面（现状证据 D-B2-04，仅作证据；统一折叠＝规格变更）。断言：各族按其在册规则判定（英文增量样本：注入折叠命中／外发不折叠不命中）。
6. **拒答话术三条逐字＋槽填充**：注入模板 `{feature}`＝命中模式词原文；外发话术固定（无槽）；写意图模板 `{target}`＝命中对象词原文；三条文本逐字（见接口常量族——承载位换、文本不变）。断言：三样本 `Refusal.content` 与迁移字面逐字相等（golden＝迁移前字面）（真源 A-P5a1-04／10／12；R-B2-14；逐字稿载体＝`tickets/v2/V2-66-注入拦截闸.md`／`tickets/v2/V2-67-外发写意图闸.md`）。
7. **命中＝早退（零模型零执行）＋收口信号形状**：命中 → 入口在**任务书装配与模型调用之前**早退（Q-C「前置即断、模型看不到」仍有效——`docs/runtime-refactor/walk/裁决表.md` §02 头注）；收口信号：
   - notice：恰三键 `{type, gates, content}`——`type="refused"`（取值 ∈ `specs/transport.md` `NOTICE_TYPES`）、`gates=[]`、`content=Refusal.content`；
   - 步记录：`decision` 类（取值真源 `specs/state.md` `STEP_KINDS`），标题＝三形逐字（行为 8），payload＝`{"phase": "understand", "gate": <分型>, "term": Refusal.hit}`——分型三值 `injection_refused`／`outbound_refused`／`write_refused`（**键名差异点①**：V1 `n1_gate` → V2 `gate`）；步 `status`＝`refused`（随 `specs/bookkeeping.md` 行为 3 如实——V1 恒 `ok` 为旧态）；
   - 直答收口：`draft=Refusal.content`、`draft_kind="direct"`（终稿即话术；`direct` 取值口径真源 `specs/state.md` 风险 6；**收口单点＝`specs/bookkeeping.md` 行为 14 `direct_answer` 三键——含闸拒同出口**）；
   - 过程档案一条（phase＝`understand`、title＝步标题、digest＝话术；截断面归 `bookkeeping.note`）。
   **分工**：本块产判定与话术（纯函数，零 IO）；早退位次与收口落账由入口消费方经 `bookkeeping` 写口执行、帧面归 `transport`（本块零 emit、零写）。**同名两义注**：本块 notice `type="refused"`＝**入口拒答**，与 `specs/answering.md` `Gap.kind="refused"`（子问题级拒答）不同物——勿混。断言（集成面，经消费方入口）：三样本各 → **零模型调用**（scripted completer 零 calls）＋**零工具执行**＋refused notice 恰一条＋步分型对＋`draft_kind="direct"`＋answer＝话术逐字（真源 A-P5a1-03／08；R-B2-10／15／25；`docs/runtime-refactor/walk/02-理解-词面安全阀.md` §一 收口三件套）。
8. **步标题三形逐字（迁移照抄）**：`N0 注入拦截硬终止`／`N0 外发拦截硬终止`／`N0 写意图拦截硬终止`（V1 字面；**行内锚**＝承载位 `appv2/runtime/graph.py` L1452／L1458／L1466＋真源 `docs/runtime-refactor/recon/B2-档案渲染与安全闸族.md` 分支表；「N0」为迁移字面——编号体系本身不入 V2，改名＝规格变更）。断言：三样本步标题逐字。
9. **A 类问句零误伤＋收窄口径**：零误伤判据＝A 类问句语料**逐条过三族全 `None`**（**以迁移钉测语料为准**：`tests/domains/test_v2_n0_word_gates.py::test_n0_no_false_positive_corpus`，实存 20 条逐条承接；票面 23／自检面 14 系前扩容口径——三口径差登记，风险 5）。断言：A 类语料逐条过三族全 `None`（`::class_a_no_false_positive`）。
   **收窄口径**（裁决 §02-A「收窄到最明显情形＋收窄标准进规格层」的落地形）＝①命中须动词＋通道／对象**共现**（常见单字面不拦）；②注入为**固定短语**（非泛词）；③**不靠扩词表覆盖间接／元问表达**——漏判由执行层兜（行为 14）；**不新增豁免机制**（V2 零豁免）。**诚实声明：三条＝V1 既有判据的规格层成立化、净收窄为零**——D-B2-01 元问共现形残留样本（如「删除的数据还能查到吗」）按已知接受态保留、登记在案；真实收窄（若须）＝Owner 另裁面。
10. **词表闭世界、只扩不删、单点**：三族清单＋三条话术为闭世界常量；**只扩不删**（扩容随红队用例回流——A-P5a1-06；扩条目须同批改本规格）；runtimev2 面内各恰一处定义、消费方零副本。断言：集合与清单相等；词表／话术特征子串在消费方块源码零命中。
11. **`Refusal` 形状与越界行为**：`{family, hit, content}` 三字段；`family` 闭世界三值；`hit`＝槽值非空；`content`＝话术逐字非空；越界构造＝判失败（不猜、不取默认）。断言：三样本字段值对；越界 `family`／空 `hit`／空 `content` → 判失败。
12. **确定性纯函数、零副作用**：同入参两跑输出相等；**零 IO、零模型调用、零时钟、零随机、零事件发射、零状态写**；**命中路径零台账接触**（V1「当场再取一次词典层缝并写回」属现状缺陷 D-B2-02——无人读的无效 I/O，重写不复刻；**差异点③**）。断言：两跑相等＋AST 扫描零命中（模型／时钟／随机／emit／DB／文件／ledger 符号）。
13. **本块零语义判断**：不做豁免／元问／引用形判定（V1 禁用词豁免机制不落本块；V2 亦不引入）；不判「提及 vs 执行」（已移出）；词表只作**明显命中的结构早退**（非判据）——判定清单逐条可指真源（`docs/runtime-refactor/walk/判断归责表.md`「词面安全阀」行）。断言：`::no_semantic_judgement_in_gate` 绿＋判定清单逐条可指真源条目。
14. **定位＝辅助快路径、非防线**：命中即不放行是**快路径早退**（省一次模型调用＋给固定友好话术），**不是防线**；漏判由执行层兜（系统没有写／外发工具、只读连接＝结构保证）——「只读」（INV-2）硬保证在执行层（逐字真源 `docs/runtime-refactor/walk/02-理解-词面安全阀.md` §八；卡面测试计划同款「漏判由执行层兜，不靠它」）。断言：本块零红线判定面（行为 12／13 的 AST 面）＋**人审**（定位声明与执行层声明对读）。
15. **废弃词闸不落本块（防写回门口）**：本块不定义 `apply_term_verdict`、不定义 `Disposition`（其 V2 等价物＝`specs/preconditions.md` 的 `SubtaskVerdict`——分派形状真源）、不读台账／术语表、不判「提及 vs 执行」——判断＝`tool_matching` 模型产出、分派＝`preconditions` 判定序第 1 位（两头认核：两规格各认其面）。断言：本块源码零 `apply_term_verdict`／`Disposition` 符号（AST／grep 扫描——`::no_writeback_of_term_gate`）；与两规格对读（人审）。

> **V2 定案差异点（对 V1 显式声明——迁移照抄之外的改动全在此列，供逐字比对）**：①**收口步 payload 分型键改名**（`n1_gate` → `gate`——V1 历史遗痕 D-B2-03，全仓零读取方、无兼容面；分型值三字面不变）；②**写意图命中槽值只携对象词**（V1 `_n0_write_hit` 返回 (动词, 对象) 而动词在消费侧即弃——D-B2-12，现状证据；V2 `Refusal.hit`＝对象词）；③**命中路径零台账 I/O**（V1 `_n0_refuse` 的 ledger_dump 补写不复刻——D-B2-02；本块零 I/O）；④**步 payload 增 `term` 键**（＝`Refusal.hit` 槽值——V1 代码未实现该键〔code↔票面偏差〕，随 `tickets/v2/V2-66-注入拦截闸.md` 字面补齐并统一三族；`recon/B2` R-B2-25「拒答步附 term」系 N1 面事实——引注面勘误注）；⑤**步 `status`＝`refused`**（V1 恒 `ok`——随 `specs/bookkeeping.md` 行为 3 如实）。

## 不降级与静默禁令

- **合法降级路径：无**——本块不降级：判定恒两态（`Refusal`｜`None`），无半成品、无默认族、无「疑似」形；未命中＝静默放行（**漏判非降级面**——执行层兜，行为 14）。
- **命中必留机读信号（信号义务，发射面分工）**：notice `type="refused"`＋步分型＋过程档案——信号形状由本块锁定（行为 7／8）、**发射与落账＝消费方（早退收口）义务**：写口归 `bookkeeping`、帧面归 `transport`；本块零 emit、不冒充覆盖。
- **本块零截断**：话术全文出、不改写、不缩措辞（槽值＝命中词原文，不截断）。
- 红线原文：`docs/runtime-refactor/walk/02-理解-词面安全阀.md` §八「词面闸＝**辅助快路径**（明显中招/越界早退，省一次模型调用＋给友好话术）、**不是防线**；漏了由**执行层**兜（系统**没有**写/外发工具、**只读**连接＝结构保证）」。

## 验收测试

| 验收标准 | 对应测试 |
|---|---|
| 三族先命先断：序固定（注入→外发→写意图）、第一命中即返；注入＋写意图同句 → `injection` | `tests/domains/test_v2_gate.py::family_order_first_hit_wins` |
| 注入族：五条模式逐字＋casefold 折叠（英文大小写样本）＋模式原形返回值 | `tests/domains/test_v2_gate.py::injection_patterns_verbatim_casefold` |
| 外发族：动词×通道共现命中、槽值＝通道词；两单边不命中 | `tests/domains/test_v2_gate.py::outbound_verb_channel_cooccurrence` |
| 写意图族：动词×对象共现命中、槽值＝对象词、取序对；两单边不命中 | `tests/domains/test_v2_gate.py::write_verb_target_cooccurrence` |
| 拒答话术三条逐字＋槽填充（命中词原文） | `tests/domains/test_v2_gate.py::refusal_texts_verbatim_slots` |
| 步标题三形逐字（迁移照抄） | `tests/domains/test_v2_gate.py::step_titles_verbatim` |
| `Refusal` 形状闭世界（`family` 三值／`hit`／`content` 非空）＋越界判失败 | `tests/domains/test_v2_gate.py::refusal_shape_closed_world` |
| 命中＝早退：零模型零执行＋notice refused 恰一条＋`draft_kind="direct"`＋answer 话术逐字（**pin-18 承接**） | `tests/domains/test_v2_gate.py::hit_early_exit_zero_model` |
| 收口信号形状：notice 恰三键＋步 payload（`gate` 分型三值／`term` 对齐 `hit`／`phase`）＋步 `status="refused"` | `tests/domains/test_v2_gate.py::refusal_signal_shape` |
| A 类问句零误伤（语料逐条 `None`——**pin-18 承接**） | `tests/domains/test_v2_gate.py::class_a_no_false_positive` |
| 零语义判断（无豁免／意图／正则判定；词表＝结构快路径） | `tests/domains/test_v2_gate.py::no_semantic_judgement_in_gate` |
| 纯函数确定性：两跑相等；零 IO／模型／时钟／随机／emit／写（AST） | `tests/domains/test_v2_gate.py::screen_pure_deterministic` |
| 命中路径零台账接触（AST 零 ledger／DB 符号——差异点③） | `tests/domains/test_v2_gate.py::hit_path_zero_io` |
| 迁移字面逐字（词表／话术／步标题 vs V1 快照；差异点表外零偏离） | `tests/domains/test_v2_gate.py::migrated_literals_verbatim` |
| 早退位次（先于任务书装配与模型调用）＋闸静默零漂移（未命中零 refused 信号） | `tests/domains/test_v2_gate.py::early_exit_position_no_drift` |
| 词表闭世界只扩不删＋步标题映射＋runtimev2 面单点（消费方零副本） | `tests/domains/test_v2_gate.py::word_families_closed_world_single_source` |
| import 白名单（只 `state`；AST 扫描——依赖白名单半覆盖面的降维补位） | `tests/domains/test_v2_gate.py::imports_state_only` |
| 废弃词闸符号零命中（`apply_term_verdict`／`Disposition`／术语表接触零） | `tests/domains/test_v2_gate.py::no_writeback_of_term_gate` |
| 【边界集】A 类语料逐条零命中；三族明显中招样本各拒；注入＋写意图同句；单边样本零命中；空串零命中 | `tests/domains/test_v2_gate.py::boundary_corpus_and_single_side` |
| 【保留集】普通业务问句（语料内）过闸零命中零漂移；词表／话术迁移字面不变 | `tests/domains/test_v2_gate.py::retention_normal_questions_unchanged` |

> **测试文件归属**：本块验收测试绑**新建** `tests/domains/test_v2_gate.py`（`gate` 是阶段 2 新划的入口闸块 `appv2/runtimev2/gate/`；`ls tests/domains/` 实测无同名文件，无冲突）；旧承载位测试 `tests/domains/test_v2_n0_word_gates.py`（直引旧码私名 `_n0_injection_hit` 等）随阶段 5 迁移重写收口（本批不改）；fixture＝**固定词表 fixture**（卡面 Adapter）＋A 类问句语料。全部测试标识＝**待织网（阶段 5）**。

## 依赖与风险

- 依赖：`state`（卡面依赖行承接；`decision` 仅本规格引用、码面零消费——触及表）；消费方＝入口相位（`understanding`——早退与收口执行面，回提登记见风险 7②）＋编排面（收口时点／链同步）；真源＝`specs/modules.md` `## gate` 卡。
- 风险与对策（每条带检测手段）：
  1. **卡级张力四件（卡与规格分叉）**：①卡面公开接口仍列 `apply_term_verdict(verdict) -> Disposition`（废弃词闸件），与职责行「废弃词闸已移出本模块」相抵；②卡面 Seam 行「结论入口（模型结论 → 分派）」＝移出件遗物（安全阀的 V2 Seam＝词面判定入口「文本 → 命中结论」）；③卡面未列族成员（常量族〔八件＋`STEP_TITLES`〕＋`Refusal`——含补录需求）；④卡面测试计划行第二句「废弃词闸程序不做语义判断（只收模型结论）」＝移出件遗物。**登记件（四件，卡级，只登记不改卡，交主窗回阶段 2）**。检测手段＝**人审**（评审工序＋卡级登记；先例 `specs/parsing.md` 风险 7①）。
  2. **收口行为面承接缺口**：`specs/understanding.md` 认「入口安全阀→`gate`」「本 spec 只消费其结论」，但**无收口行为／验收行**（早退位次／零模型零执行／收口三件套的执行面）——**回提登记**（understanding 补承接，或主窗裁定落 `orchestration`；本规格持行为与断言、执行者以落地为准）。检测手段＝**人审**（主窗回提＋阶段 7 接口契约对账）＋`::hit_early_exit_zero_model`。
  3. **R2 覆盖面缺 gate 深层子模块**：`tools/importlinter_v2.toml` R2 forbidden 实建九块、不含 `appv2.runtimev2.gate.*`（设计注记「10 块全护」含 gate——`docs/runtime-refactor/eng/00-阶段2-模块划分草案.md` §四）——**登记**（主窗回提补闸）；**降维＝消费方 import 形 AST 扫描（登记待补）**——`::imports_state_only` 守的是本块自身依赖白名单、不覆此面。检测手段＝**人审**＋AST（登记待补）。
  4. **「固定词表 fixture」与「程序不做语义判断」的措辞边界**：本规格定界＝词表＝闭世界常量＋测试夹具（只作明显命中的结构早退）；「不做语义判断」的 V2 适用面＝废弃词闸（移出）与一切豁免／意图判定（行为 13）。检测手段＝**人审**（评审焦点 4）＋`::no_semantic_judgement_in_gate`。
  5. **收窄标准的规格层落地**（裁决 §02-A：「收窄到最明显情形」＋「收窄标准进规格层」——无 Owner 逐字条款）：本规格落法＝共现判据＋固定短语＋不扩词表覆盖间接表达（行为 9）——收窄不足＝误伤回归、收窄过度＝漏判面扩大，两面均由语料与执行层兜底口径检查；**净收窄为零**（三条＝V1 判据成立化）——D-B2-01 残留样本按已知接受态登记（行为 9）；A 类语料条数三口径（23／14／20）以钉测实存 20 条为准（登记）。检测手段＝`::class_a_no_false_positive`＋**人审**。
  6. **迁移字面与差异点表完整性**（词表／话术／步标题迁移；**五处差异点**：分型键名／动词分量／零台账 I/O／`term` 键／`status=refused`——按差异点表逐条）：检测手段＝`::migrated_literals_verbatim`＋**人审**（逐字比对）。
  7. **跨规格债与卡级登记清单（本批只登记、不代办——单写者纪律，交主窗统一回提）**：①卡级四件（风险 1——接口行／Seam 行／族成员补录／测试计划行遗物）；②`specs/understanding.md` 收口承接（风险 2）＋触及面「入口两道闸」措辞（现只一道——随②同批改述）；③R2 gate 深层子模块面（风险 3）；④`docs/runtime-refactor/eng/00-阶段2-模块划分草案.md` §三 C **子节整体**与 §七「H12 全量（含两部分）」措辞残留（§五 覆盖声明已就位——回提改述）＋`synth/S1` H12 行两处（「INV-2 只读面」括注等）随批核实加注；⑤**`pin-18` 落点＝本块（正面承接）／`pin-31` 移出本块**（两头认在 `specs/tool_matching.md`／`specs/preconditions.md`——核实结论见挂钩表）；⑥**`pin-21`（faq 五站链）零落点＝已裁定**（`docs/runtime-refactor/eng/04a-应钉行为清单.md` pin-21 行注记「主窗 2026-10-15 裁：零落点＝正确状态非缺陷」）——本块知悉不挂；⑦`appv2/runtimev2/gate/__init__.py` 占位 docstring 残留（旧双件定界——阶段 5 施工同批改述，登记）；⑧链尾收口时点（agent-loop 未明写——随②对账登记）。检测手段＝**人审**（主窗回提＋阶段 7 接口契约对账）。

## 与闸的挂钩表

| 本规格的硬要求 | 挂钩 | 现状 |
|---|---|---|
| 触及模块名已声明 | spec gate | 已进 CI |
| 验收测试逐行有标识 | spec gate | 已进 CI |
| 不引框架 | 边界闸 **R5b**（source 含 `appv2.runtimev2.gate`——亲读属实） | 已真跑 |
| 不引引擎（禁直引 knowledge/query/retrieval） | 边界闸 **R6**（source 含 gate——亲读属实） | 已真跑 |
| 不直引 `appv2.infra.llm_client` | 边界闸 **R7**（source 含 gate——亲读属实） | 已真跑 |
| 不引旧码（`appv2.runtime.*`） | 边界闸 **R5**（source＝`appv2.runtimev2` 全体） | 已真跑 |
| 零模型调用（连 `gateway_adapter` 都不 import） | 测试 `::imports_state_only`（AST）＋**诚实声明**：R1–R8 无 gate 专属零模型闸（R7 只咬 `infra.llm_client`、R8 只列三相位） | 待实现（阶段 5）；诚实声明原因：无专属闸 |
| 只许 import `state`（依赖白名单） | 测试 `::imports_state_only`（AST）＋**人审** | 待实现；人审原因：R1–R8 无「gate 依赖白名单」面（R3 只列 parsing／prompts） |
| 消费方只经包根（禁深层子模块） | **诚实声明**：R2 forbidden **不含** `appv2.runtimev2.gate.*`（实建九块 vs 设计「10 块全护」——风险 3 登记）→ **人审**＋降维 AST 断言（登记待补） | 半覆盖（R2 实读） |
| 命中＝早退、零模型零执行、notice `type=refused`、A 类零误伤（**pin-18 承接**，P0） | 钉 **`pin-18`**——本块落点＝行为 1–9＋验收 `::family_order_first_hit_wins`／`::hit_early_exit_zero_model`／`::refusal_signal_shape`／`::class_a_no_false_positive`；**分工**：notice 类型闭世界面＝`specs/transport.md`（`NOTICE_TYPES` 含 `refused`）、收口落账面＝`specs/bookkeeping.md` | 待织网（阶段 5） |
| 命中收口信号机读（notice 恰三键＋步分型＋过程档案） | 测试 `::refusal_signal_shape`／`::hit_early_exit_zero_model`；帧面＝`specs/transport.md` | 待实现（阶段 5） |
| 程序不判语义（无豁免／意图判；词表＝结构快路径） | 测试 `::no_semantic_judgement_in_gate` | 待实现 |
| 词表闭世界只扩不删＋步标题映射（`STEP_TITLES`）＋runtimev2 面单点（消费方零副本） | 测试 `::migrated_literals_verbatim`／`::word_families_closed_world_single_source` | 待实现（阶段 5） |
| `pin-31`（废弃词闸新行为）经逐条核实**不落本块**（防一头两认） | 钉落点对读：判断＝`specs/tool_matching.md`（其挂钩表 pin-31 行）；分派＝`specs/preconditions.md` 判定序第 1 位（其挂钩表 pin-31 行）；出数只认现行口径＝`specs/tool_matching.md` 行为 7——**两头认核成立**；本块反向保证＝行为 15＋`::no_writeback_of_term_gate` | 已核实（本批起草时逐条对读） |
| 真源引用可解析（本规格全部引用行） | 真源引用闸（`tools/ref_resolvable.py` 的 check 子命令） | 交稿前本地实跑 |
| 「不做什么」的纯范围排除（不判语义／不触台账／不发射等） | **人审** | 接不上闸的原因：纯范围排除没有形状／存在性／退出码判据；能降维的部分（零模型／只引 state／闭世界）已由 R5／R5b／R6／R7＋AST 测试覆盖 |
