"""核验：断言级核验（零模型）、归属审、矛盾分源、verdict

模块卡见 `specs/modules.md` 的 `## verification` 一节；规格见 `specs/verification.md`（形状与行为
真源）；架构图见 docs/architecture-v3.html。包根即公开面（R2：消费方只经
`appv2.runtimev2.verification` 消费，深层子模块私有）：

- 相位单入口：`verify(state, *, bus=None, supplements=None)`（卡面签名 `verify(state) -> Verdict`；
  `bus`＝编排块持有的 per-run 总线，必给注入面——未注入即 fail-closed 抛错；`supplements`＝
  编排块持有的**增补面收集列表**（2026-10-17 EB3 D2——本块不再把分源／归属块写进 `state.draft`，
  改按原序入该列表、由编排层发 `supplement` 帧；缺省＝本块自持一份丢弃）；
- 三形状（规格接口定义节 :32–:51 逐字）：`Verdict`（九键齐备，缺键＝判失败）／`RewriteRecord`
  （`reason` 闭世界 `no_material`｜`conflict`）／`Gap`（**复用 `answering` 的 `Gap` 口径**——字段与
  闭世界逐字同源，核验侧只产 `kind="unverified"`；相位互不 import（R1），故本包自持一份同形形状）；
- 闭世界与文本单点：`REWRITE_REASONS`／`CARRIER_KINDS`（承载豁免域）／
  `ATTRIBUTION_CARRIER_KINDS`（归属审辖域）／`ROWSET_OBSERVATION_KINDS`（行集对账面）；
  **改写前缀退役**（2026-10-17 EB3 D3：真无据断言删句、不贴前缀——留痕＝`RewriteRecord` ＋
  `verdict.rewritten` 计数 ＋ `notice`）；核验豁免两类的形态字面（引擎披露行／组头行）与血缘
  五要素段特征字面同为单点常量；**2026-10-17 F1 核验面三件**：`VALUE_UNITS`（数值断言的**计量
  单位**族——标识符／日期不算数值断言，件一）／`FIELD_NAME_NOUN`（油田名名录面过滤位——油田归属
  对账，件四；机读键 `PAYLOAD_FIELD_MISMATCH_KEY`）；
- 帧面（只经 `transport` 公开面）：`EVENT_VERDICT`（核验裁决帧——**批次落定归 `orchestration`
  协调**，本块只保证自产部分就位，行为 10）＋ `EVENT_NOTICE`（通知帧，恰三键）；
- 步 payload 键名（六计数键 ＋ 行集对账两字段 ＋ 油田归属维度键，行为 6／11／13）。

一句话：答案交付前**逐句核对有没有材料撑着**——**纯程序、零模型**（防编造的机器底线）；没支撑的
话**改写掉**，两来源对不上就**分开列**。**它交出的判定卡 `Verdict` 是对外判定、不是答案侧文本。**

**依赖面**（规格「框架与依赖红线」＋卡「依赖」）：`state`（形状面）、`transport`（`verdict`／
`notice` 帧发射面）、`bookkeeping`（**写口面**——步记录／通知／路由意图经其唯一写口，只引函数、
不引其内部）；另经 `appv2.tools` 的**公开面**取题眼锚解析单点 `entity_anchor_tokens`（归属审的
题眼锚＝问句实体词，确定性零模型零 IO；现状核验步的同一调用面——`appv2/runtime/graph.py:3628`，
本包**不另立第二套解析**）。**R8 零 LLM 面**：本块不调模型、不存在模型调用发起面——不引
`gateway_adapter`（写口链 `verification → bookkeeping → …` 非本块发起面）；R5b／R2／R6／R7／R1／R5
各边界闸见 `tools/importlinter_v2.toml`。

**规格侧未给形状处的口径落定**（票面「规格侧缺口登记」②的登记事实——本包按下列口径落形状，
**不发明写口**；待主窗裁定后随规格回填）：

1. **改写留痕的载体**：`RewriteRecord` 逐条投影进 **step payload 的 `rewrites` 键**（改写
   **不得静默**——被改写原句与原因必须留痕）；
2. **行集对账注记的载体**（行为 11「补如实注记」）：注记落 **step payload 的 `row_note` 键**（行为
   11 是**记账面、非拦截阀门**——不改写答案面、不重试、不拦截）；「答案面无行集声明」的判据＝
   **`delivered_rows == 0`**（答案面一行在窗数据行都没交付＝无声明）；「在窗数据行数」的面＝
   `state.observations` 中 `locator.kind ∈ ROWSET_OBSERVATION_KINDS` 的支数。
   **2026-10-17 EB5c 扩面（机读两面恒在场）**：`rowset_missing`（缺行序号列——渲染行数≠引擎行
   数的逐号可复算面）＋ `rowset_aligned`（引标序对齐——交付的引擎行号列是否恰为引擎行号序前
   L 项；跳号／整体偏移＝off-by-one 错位）**与注记面三态解耦**：答案自述声明为真为假只能由对账
   事实判（L04-22 实态＝自述「共 86 口井已返回」而交付 84 行、缺第 24／46 号且引标错位一格），
   故两面**恒落账**；注记面（`row_note`，人读）三态不变（无声明→注记、有声明→零注记）。
   判据单点＝`rules.rowset_audit`（纯计数零语义）；**不改写、不重试、不拦截**不变；
3. **`Verdict.gaps` 的产出面**：改写>0 产一条聚合缺口、归属失败产一条缺口（均 `kind="unverified"`、
   `subtask_id=None`——核验侧无子问题归属面）；
4. **行为 8 的判据落定**：断言行＝**有引标行**——引标须可解析（不得自动判过：引标越界即无据）；
   无引标且无数值＝结构承载（原样保留且**不计有支撑数**）；无引标但有数值＝无据断言（**删句**，
   2026-10-17 EB3 D3——不贴前缀）——关闭现状「无引标数字行经窗内放行」形（钉 `pin-10`
   「不得 `cited=[]` 且数字在场」）；**豁免两类线**（EB3 D3，只豁免删句、不改写）：引擎披露行
   （窗 ISO 区间或披露标记四字面，且与材料披露行事实一致）与组头行（行尾「：」或后邻行带引标的
   数据表头）；
5. **行为 1 的剥除面**：发射围栏／裸发射令牌的剥离单点归 `answering`（答案面归属；相位互不 import
   ——R1），本包只做「整行即 JSON 对象／数组」的形态剥除（剥除不计改写）；**块头模式族段**
   （2026-10-17 EB3 D2 起血缘五要素整段、2026-10-17 EB5c 扩为族判据）同样在剥除拍离场——判据与
   段剥离单点＝`transport.blocks`（血缘族段入 `lineage` 增补面、剥除面块型〔引用清单〕段离场；
   单行口径说明（≤2 行、带 `[n]` 引标）保留在正文）。

**合法降级路径＝无**：闭世界越界一律 fail-closed 抛错；核验器自身抛错**不判 `ok=True`**——转
`Verdict.ok=False` ＋缺口（由 `orchestration` 承接），不静默放行。
"""

from appv2.runtimev2.verification.constants import (
    ATTRIBUTION_CARRIER_KINDS,
    CARRIER_KINDS,
    EVENT_NOTICE,
    EVENT_VERDICT,
    GAP_UNVERIFIED,
    LINEAGE_OBSERVATION_KIND,
    NOTICE_ATTRIBUTION_SPLIT,
    NOTICE_CONTRADICTION_SPLIT,
    NOTICE_UNSUPPORTED_CLAIM,
    PAYLOAD_ATTRIBUTION_KEY,
    PAYLOAD_CITED_KEY,
    PAYLOAD_DELIVERED_ROWS_KEY,
    PAYLOAD_FIELD_MISMATCH_KEY,
    PAYLOAD_GAPS_KEY,
    PAYLOAD_OBS_ROWS_KEY,
    PAYLOAD_OK_KEY,
    PAYLOAD_PHASE_KEY,
    PAYLOAD_REWRITES_KEY,
    PAYLOAD_REWRITTEN_KEY,
    PAYLOAD_ROW_NOTE_KEY,
    PAYLOAD_ROWSET_ALIGNED_KEY,
    PAYLOAD_ROWSET_MISSING_KEY,
    PAYLOAD_SPLIT_KEY,
    PAYLOAD_SUPPORTED_KEY,
    PHASE,
    REWRITE_CONFLICT,
    REWRITE_NO_MATERIAL,
    REWRITE_REASONS,
    ROWSET_OBSERVATION_KINDS,
)
from appv2.runtimev2.verification.core import verify
from appv2.runtimev2.verification.models import (
    GAP_KINDS,
    GAP_MISSING,
    GAP_REFUSED,
    Gap,
    GapKind,
    RewriteReason,
    RewriteRecord,
    Verdict,
)

__all__ = [
    "ATTRIBUTION_CARRIER_KINDS",
    "CARRIER_KINDS",
    "EVENT_NOTICE",
    "EVENT_VERDICT",
    "GAP_KINDS",
    "GAP_MISSING",
    "GAP_REFUSED",
    "GAP_UNVERIFIED",
    "LINEAGE_OBSERVATION_KIND",
    "NOTICE_ATTRIBUTION_SPLIT",
    "NOTICE_CONTRADICTION_SPLIT",
    "NOTICE_UNSUPPORTED_CLAIM",
    "PAYLOAD_ATTRIBUTION_KEY",
    "PAYLOAD_CITED_KEY",
    "PAYLOAD_DELIVERED_ROWS_KEY",
    "PAYLOAD_FIELD_MISMATCH_KEY",
    "PAYLOAD_GAPS_KEY",
    "PAYLOAD_OBS_ROWS_KEY",
    "PAYLOAD_OK_KEY",
    "PAYLOAD_PHASE_KEY",
    "PAYLOAD_REWRITES_KEY",
    "PAYLOAD_REWRITTEN_KEY",
    "PAYLOAD_ROWSET_ALIGNED_KEY",
    "PAYLOAD_ROWSET_MISSING_KEY",
    "PAYLOAD_ROW_NOTE_KEY",
    "PAYLOAD_SPLIT_KEY",
    "PAYLOAD_SUPPORTED_KEY",
    "PHASE",
    "REWRITE_CONFLICT",
    "REWRITE_NO_MATERIAL",
    "REWRITE_REASONS",
    "ROWSET_OBSERVATION_KINDS",
    "Gap",
    "GapKind",
    "RewriteReason",
    "RewriteRecord",
    "Verdict",
    "verify",
]
