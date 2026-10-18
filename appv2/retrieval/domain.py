"""retrieval.domain —— 检索 schema 与纯语义（V2-04，specs/retrieval.md 接口定义节）。

V1 S4 双路召回＋精排＋生成窗供给移植为确定性引擎的纯语义层（零 I/O——B1：
本文件不 import fastapi/DB/供应商 SDK；IO 归 source/engine 的注入缝）。

供给策略本体化（specs/retrieval.md 目标节——Q11 P0-2「生成窗截断→材料未披露
虚答」与同型抢锚病灶的治理面）：
- **矛盾来源同窗并立**：送窗预算内每来源（来源指纹＝报告）至少留代表支——
  supply_window 硬编码实现，不依赖 LLM 自觉；
- **截断显式**：window_note 如实带「共检索到 N 条材料，M 条用进了答案」数字
  ——agent 据此区分「没有」与「没送」（V2-82e 起措辞为出厂即用户语的
  NOTE_* 常量——内部行话不进材料段）；
- **出处链完整**：Observation 三级出处 fragment→report→library＋family 标注
  （库 biz_template 透传）＋locator 携 library/报告名（同型文档来源标注——
  锚错 A-W11 vs Y-21 可被核验步发现）。

V1 移植源（app/domains/kb/domain.py 与 app/domains/chat/domain.py，语义逐款
同形、模块路径换 appv2）：extract_units/bm25_scores/normalize_bm25/
promote_entity_hits（G-07 应用层 BM25＋编号保送）、cosine_similarity、
RRF_K/rrf_merge（D2 融合）、_report_diversify（G-06 多样性——本文件
source_diversify，键从 report_id 泛化为来源指纹同物）。

family 闭世界＝V1 kb_library.biz_template CHECK 四值（99 §2.5 原样——本文件
FAMILY_ALL 单点；库行列不进本票，值域随库合同）。
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from appv2.text_tokens import boundary_hit, num_token_hit

# ---------- family 闭世界（V1 kb_library.biz_template CHECK——99 §2.5） ----------

FAMILY_COMPLETION = "completion"
FAMILY_MONTHLY = "monthly"
FAMILY_DYNAMIC = "dynamic"
FAMILY_BLANK = "blank"
FAMILY_ALL: tuple[str, ...] = (FAMILY_COMPLETION, FAMILY_MONTHLY, FAMILY_DYNAMIC, FAMILY_BLANK)

# 语料节点分型（FragmentRecord.node_kind 闭世界）：slice＝原文切片（缺省——旧
# 构造零漂移）；section_summary＝节级摘要节点（V2-47 R1b 富化产物——按节聚类
# 的 LLM 摘要，独立可检索、命中展开节内切片）。
NODE_SLICE = "slice"
NODE_SECTION_SUMMARY = "section_summary"

# 问题块型（kb_fragment.type 五值之一——入库问题块重生批次生成
# （app/domains/kb/service.py F37，「这份报告可能被问的 10 个问题」）。
# 展示面专用（端点 9 ingest_additions 直读消费），非答案材料——V2-65 附 A
# 裁决：不参加检索排序（通篇问句零答案内容、逐字包含报告关键题眼，融合分
# 天然抢占代表席——V264F1 实锤 12 支占语料 8% 抢走 6 席中 3 席）。
QUESTION_BLOCK_TYPE = "问题块"

# 切片上下文前缀逐字格式（票面钉：〔本段节选自〈报告名〉·〈章节路径〉〕——
# Anthropic 上下文感知检索式；报告名/章节路径取 kb 台账元数据，零模型调用）。
CONTEXT_PREFIX_TEMPLATE = "〔本段节选自{report}·{section}〕"
CONTEXT_PREFIX_NO_SECTION = "〔本段节选自{report}〕"

SECTION_PATH_SEPARATOR = "＞"  # 章节路径层级分隔（kb 台账 section 原生形）

# ---------- 引擎注记白话文案（V2-82e 方案 A：注记出厂即用户语） ----------
# 病灶（流水 81／取证 agent-186）：注记原文＝内部行话，模型照抄进用户答案（EB5H
# 违例）；本区常量＝注记各段逐字载体，数字经 format 槽参数化。计数同时落
# RetrievalBundle.recalled/sent 结构化字段（additive）。段头
# answering.constants.ENGINE_NOTES_HEAD 属冻结点，不动。
NOTE_RECALLED_SENT = "共检索到 {recalled} 条材料，{sent} 条用进了答案"
NOTE_RECALL_GAP = "另有 {gap} 条已找到但未用进答案（受送入答案的数量限制）"
NOTE_CONFLICT_SOURCES = "以下材料来源说法不一，各保留了代表条目："
NOTE_MISSING_SOURCES = "以下来源因数量限制未纳入："

# ── V2-122 注记尾接两条范围指令（S2＋S5——注记改写为「对作答面的范围指令」）─────────
# 病根（`eval/suite-147/results/EB11-臆造上下文归因.md` §三反向证据）：注记**如实披露**了
# 「另有 N 条未用进答案」，却**无一条指令**把断言/否定的适用域限定在已见材料内——于是
# `NQ-M8` 明知 47/48 条未见仍下报告级否定、`A-正6` 以「没有任何一条材料提及」下池级否定
# （池计数 51≠45）。两条逐字稿＝`tickets/v2/V2-122-材料范围限定与计数如实.md` §逐字稿
# （照抄、零改写；与 V2-101 首句措辞互斥不重复——本票管范围与计数、落注记尾）。
NOTE_SCOPE_DIRECTIVE = (
    "【范围限定】你的断言与否定只对已见材料成立：不得因「未见」而断言材料中不存在；"
    "需说明「本次材料未覆盖」，不得升格为「报告/资料库未载」。"
)
NOTE_COUNT_TRUTHFUL = (
    "【计数如实】注记中的「检索到 N 条／用进 M 条」为本次真实计数，必须与实际一致。"
)

# ── 按来源取节／取篇（V2-96 D5——KB 只读读面的披露话术单点）────────────────────
# 真源＝`docs/runtime-refactor/接手-召回全链路最终决议与运行流程-20261018.md` §五·5.4：
# `fetch_section`／`fetch_report` **必须截断+披露**（截断显式、不假装全文）。
NOTE_FETCH_REPORT_SENT = "母报告全文 {total} 字，本次交付 {kept} 字"
NOTE_FETCH_TRUNCATED = "母报告全文 {total} 字，本次交付前 {kept} 字（截断显式）"
NOTE_FETCH_SECTION_SENT = "本报告本节共 {recalled} 条片段，本次交付 {sent} 条"
NOTE_FETCH_SECTION_MISSING = "该报告无此节：{report}·{section}（如实告知，不代取他节）"
# 正文尾截断标记（截断**可见**——不静默硬切）。
FETCH_TRUNCATION_MARK = "……（母报告全文未完，已按上限截断）"


# ---------- 检索单元与向量（V1 kb.domain 移植——G-07/P1-11 同款） ----------

BM25_K1 = 1.2  # BM25 词频饱和常数（教科书值——代码常量，不入配置面）
BM25_B = 0.75  # BM25 长度归一常数
BM25_NORM_K = 3.0  # 归一化尺度：强命中（原始分≈8）→0.73、弱命中（≈0.3）→0.09
RRF_K = 60  # RRF 固定推荐值（D2 开放问题 8 裁决——加权参数不入合同）
SNIPPET_CHARS = 80  # 短面长度（V1 IndexHit.snippet 同值——长面 text 不截）


def extract_units(text: str) -> list[str]:
    """检索单元切分（G-07——免分词器的 BM25 单元）。

    - CJK 连续串按二字滑窗：二字组是中文 IR 免分词器的标准单元；
    - 字母数字连串（含内部连字符）整取：W-33／SCSSV／2462——编号与数字是
      区分度最高的单元，不许被切碎；
    - 单字不成单元（字面噪声，IDF 也救不住）。
    """
    units: list[str] = []
    for run in re.findall(r"[\u4e00-\u9fff]+", text or ""):
        if len(run) >= 2:
            units.extend(run[i : i + 2] for i in range(len(run) - 1))
    for tok in re.findall(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*", text or ""):
        if len(tok) >= 2:
            units.append(tok)
    return units


def alnum_tokens(text: str) -> list[str]:
    """问句中的字母数字 token（G-07 编号保送通道的判定单元——W-33/SCSSV/2462）。"""
    return [
        tok
        for tok in re.findall(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*", text or "")
        if len(tok) >= 2
    ]


def bm25_scores(question: str, texts: list[str]) -> list[float]:
    """关键词腿 BM25 打分（G-07）。

    - 单元＝extract_units；IDF 查询时现算（df＝含该单元的文本数，语料＝texts
      全集；平滑式自带小语料保护）；
    - 返回与 texts 等长的**原始分**列表（无界量级）——对外消费前必须经
      normalize_bm25 映射 0~1（score 分数契约）。
    """
    q_units = sorted(set(extract_units(question)))
    if not q_units or not texts:
        return [0.0] * len(texts)
    n_docs = len(texts)
    doc_tfs: list[dict[str, int]] = []
    doc_lens: list[int] = []
    df: dict[str, int] = dict.fromkeys(q_units, 0)
    for text in texts:
        tf: dict[str, int] = {}
        for u in extract_units(text):
            tf[u] = tf.get(u, 0) + 1
        doc_tfs.append(tf)
        doc_lens.append(sum(tf.values()))
        for u in q_units:
            if u in tf:
                df[u] += 1
    avgdl = (sum(doc_lens) / n_docs) if n_docs else 0.0
    out: list[float] = []
    for tf, dl in zip(doc_tfs, doc_lens, strict=True):
        if avgdl == 0.0:
            out.append(0.0)
            continue
        s = 0.0
        for u in q_units:
            f = tf.get(u, 0)
            if f == 0:
                continue
            idf = math.log((n_docs - df[u] + 0.5) / (df[u] + 0.5) + 1.0)
            s += idf * (f * (BM25_K1 + 1)) / (
                f + BM25_K1 * (1.0 - BM25_B + BM25_B * dl / avgdl)
            )
        out.append(s)
    return out


def normalize_bm25(raw: float) -> float:
    """BM25 原始分 → 0~1（score/(score+K)——分数契约单点，G-07 最隐蔽的翻车点）。"""
    if raw <= 0:
        return 0.0
    return raw / (raw + BM25_NORM_K)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """向量余弦（embo-01 1536 维/LocalHash 同维——异维度护栏返回 0.0 不误配）。"""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = float(sum(x * y for x, y in zip(a, b, strict=True)))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def promote_entity_hits(
    ranked: list[tuple[Hit, float]],
    scored: list[tuple[Hit, float]],
    tokens: list[str],
    *,
    top_k: int,
    text_of: Callable[[Hit], str],
) -> list[tuple[Hit, float]]:
    """编号保送（G-07）：tokens 逐字命中而未进榜的命中保送进 topK 尾席。

    - 上限 4（多编号问句不把窗占满，余下靠 BM25 兜底）；
    - 榜上已有的不重复（按片段身份判定）；
    - 返回总长恒 ≤ top_k——保送占的是尾席，不是扩窗。纯函数。
    """
    if not tokens:
        return ranked
    cap = min(4, top_k)
    ranked_keys = {hit.fragment.fragment_id for hit, _ in ranked}
    promoted: list[tuple[Hit, float]] = []
    for hit, score in scored:
        if len(promoted) >= cap:
            break
        if hit.fragment.fragment_id in ranked_keys:
            continue
        text = text_of(hit)
        if any(tok in text for tok in tokens):
            promoted.append((hit, score))
            ranked_keys.add(hit.fragment.fragment_id)
    return ranked[: top_k - len(promoted)] + promoted


# ---------- 片段/图谱边记录（kb_* 台账读面投影——source 层与引擎共用的行形状） ----------


@dataclass(frozen=True, slots=True)
class FragmentRecord:
    """kb_fragment 读面行（V1 FragmentRow 运行时投影——chat 只见面不触表同款）。

    text＝生成上下文用全文（V1 生成窗全文纪律——不再截 500）；embedding＝None
    表示未入向量索引（向量腿跳过、关键词腿兜底）；family＝库 biz_template
    透传（供给分池的族键）；library/report＝出处链 library/报告名两级；
    node_kind＝语料节点分型（V2-47 R1b——缺省 slice，旧构造零漂移）；
    well＝切片本体标签（V2-64——入库抽取回写 kb_fragment.well，缺省 None 零漂移）。
    """

    fragment_id: str
    report_id: str
    report: str
    section: str | None
    library_id: str
    library: str
    family: str
    text: str
    embedding: list[float] | None = None
    node_kind: str = NODE_SLICE
    well: str | None = None
    # kb_fragment.type 透传（V2-65 附 A——缺省内容主型＝既有构造零漂移；
    # 「问题块」型在 engine 语料装配层退赛，不进召回/送窗/展开语料）。
    frag_type: str = "原文块"

    def __post_init__(self) -> None:
        if self.node_kind not in (NODE_SLICE, NODE_SECTION_SUMMARY):
            raise ValueError(
                f"node_kind 越界：{self.node_kind!r}（允许 {NODE_SLICE}/{NODE_SECTION_SUMMARY}）"
            )


@dataclass(frozen=True, slots=True)
class GraphEdgeRecord:
    """图谱边读面行（V1 GraphHitFace 邻域边投影＋库归属——图谱面候选源）。

    chunk_id/report_id＝边出处（依据闸留存的原文片段/立边来源报告——B5 边
    出处列同域）；engine 图谱面对 chunk_id 做 fail-closed 锚校验（锚不上片段
    台账的边拦截丢弃）。
    """

    entity_from: str
    rel: str
    entity_to: str
    evidence: str = ""
    chunk_id: str | None = None
    report_id: str | None = None
    report: str = ""
    library_id: str | None = None
    library: str = ""
    family: str = ""


# ---------- 索引富化节点分型与纯语义（V2-47 R1b——切片上下文前缀＋节级摘要层） ----------

def context_prefix(report: str, section: str | None) -> str:
    """切片上下文前缀（索引期富化——报告名＋章节路径；元数据已备，确定性拼装）。

    - 章节路径在位：〔本段节选自〈报告名〉·〈章节路径〉〕（全路径逐字——
      BM25 词面与向量语义双受益）；
    - 路径缺席：〔本段节选自〈报告名〉〕（不发明章节）。

    勘误（P-046 中途审查 consider 2 采纳）：上下文前缀为「报告名＋章节路径」
    的元数据确定性拼装（非 LLM 生成前缀）；书中"检索失败率降 49%"系 LLM
    前缀实验口径，本实现不作效果背书。
    """
    if section:
        return CONTEXT_PREFIX_TEMPLATE.format(report=report, section=section)
    return CONTEXT_PREFIX_NO_SECTION.format(report=report)


def section_root(section: str | None) -> str | None:
    """章节路径顶层段（节聚类的簇键——「章节 04 … ＞ 4.1 … ＞ 4.2 …」取首段）。

    节级摘要层的「节」粒度＝顶层章（切片→章→全文的中间层——RAPTOR 单级版；
    「正文」「全文档摘要」「问题块·第 N 批」等非章节路径整段即顶层）。None
    原样返回（无路径切片不入节聚类）。
    """
    if section is None:
        return None
    return section.split(SECTION_PATH_SEPARATOR)[0].strip()


def summary_node_id(report_id: str, root: str) -> str:
    """节级摘要节点确定性身份（md5(report_id|root) 前 12 位——幂等钉半边）。

    同（报告，节）恒同 id：富化重跑 upsert 同键零重复节点；旧节点可追溯。
    """
    digest = hashlib.md5(f"{report_id}|{root}".encode()).hexdigest()
    return f"ensum-{digest[:12]}"


def enriched_index_text(frag: FragmentRecord) -> str:
    """检索单元的索引文本（BM25 腿与编号保送共用的拼接单点）。

    - 切片：上下文前缀＋原文（前缀进索引——BM25 词面扩容，问句点名的报告名/
      章节路径可在前缀逐字命中）；
    - 节级摘要节点：摘要文本照入（节路径与覆盖要点已在其文本内——不再套前缀）。

    送窗原文（Observation.text）不走本函数——前缀只进索引面，生成窗文本零漂移。
    """
    if frag.node_kind == NODE_SECTION_SUMMARY:
        return frag.text
    return context_prefix(frag.report, frag.section) + frag.text


# ---------- 命中与融合（V1 IndexHitFace/rrf_merge 同款） ----------


@dataclass(frozen=True, slots=True)
class Hit:
    """单路召回命中（score 恒原始腿分——精排只重排不改分，S4 与重评同尺）。"""

    fragment: FragmentRecord
    score: float
    leg: str  # vector | keyword


def rrf_merge(
    vector: list[Hit], keyword: list[Hit], *, k: int = RRF_K
) -> list[tuple[Hit, float]]:
    """RRF 按名次融合（V1 S4 锚——1/(k+rank) 逐路累加，按融合分倒序）。

    同片段两路并中：条目取向量腿的 Hit（V1 hits.setdefault 同序——vector 在
    前），融合分累加两路名次。
    """
    fused: dict[str, float] = {}
    hits: dict[str, Hit] = {}
    for leg in (vector, keyword):
        for rank, hit in enumerate(leg, start=1):
            fid = hit.fragment.fragment_id
            fused[fid] = fused.get(fid, 0.0) + 1.0 / (k + rank)
            hits.setdefault(fid, hit)
    return sorted(
        ((hits[fid], score) for fid, score in fused.items()),
        key=lambda pair: pair[1],
        reverse=True,
    )


# ---------- schema（specs/retrieval.md 接口定义节——RetrievalNeed/Bundle 定稿） ----------


@dataclass(frozen=True, slots=True)
class RetrievalNeed:
    """检索需求（doc_retrieve/graph_query 工具入参投影）。

    - question：检索问句（空白构造即拒——闭世界）；
    - anchors：@ 锚定资产名（指标/术语/对象名——并入问句检索单元与保送通道，
      V1 S1 锚定材料语义的检索侧投影）；
    - family_hints：族提示（闭世界四族——未知族构造即拒；驱动 supply_window
      分池配额）；
    - budget：送窗预算 M（≥1；截断显式的 M）。
    """

    question: str
    anchors: tuple[str, ...] = ()
    family_hints: tuple[str, ...] = ()
    budget: int = 4

    def __post_init__(self) -> None:
        if not isinstance(self.question, str) or not self.question.strip():
            raise ValueError("question 须为非空白字符串")
        if isinstance(self.budget, bool) or not isinstance(self.budget, int) or self.budget < 1:
            raise ValueError(f"budget 须为 ≥1 整数：{self.budget!r}")
        anchors = tuple(self.anchors)
        if any(not isinstance(a, str) or not a.strip() for a in anchors):
            raise ValueError("anchors 须为非空白字符串序列")
        object.__setattr__(self, "anchors", anchors)
        hints = tuple(self.family_hints)
        for hint in hints:
            if hint not in FAMILY_ALL:
                raise ValueError(f"family_hints 越界：{hint!r}（允许 {'/'.join(FAMILY_ALL)}）")
        object.__setattr__(self, "family_hints", hints)


@dataclass(frozen=True, slots=True)
class Observation:
    """供给窗单支证据（kind 两值闭世界：fragment＝片段/GraphEdgeRecord 面＝图谱边）。

    score 恒原始腿分（精排只重排不改分）；locator＝出处链 wire 面
    {library, report, section, fragment_id}——同型文档来源标注（specs 行为
    约定 4：锚错 A-W11 vs Y-21 可被核验步发现）；well＝切片本体标签透传
    （V2-64——装配面把出处/对象随材料交模型，缺省 None 零漂移）。
    """

    kind: str  # fragment | graph
    text: str  # 生成上下文长面
    snippet: str  # 80 字短面
    score: float
    leg: str  # vector | keyword | graph
    family: str
    fragment_id: str | None
    report_id: str | None
    report: str
    library_id: str | None
    library: str
    section: str | None
    locator: Mapping[str, str]
    well: str | None = None


@dataclass(frozen=True, slots=True)
class RetrievalBundle:
    """检索供给窗（specs 接口定义节原形——observations＋window_note）。

    observations 每次调用现造（返回容器零共享——INV-2 副本纪律）；window_note
    如实声明「共检索到 N 条材料，M 条用进了答案／材料来源说法不一各留代表条目／
    未纳入来源逐条点名」。recalled/sent＝计数结构化字段（V2-82e additive——
    window_note 措辞面之外的机读面；缺省 0＝旧构造零漂移）。

    V2-89b additive 四字段（D3 归因机读面——`retrieval_calls` 留痕行的值源；
    缺省零值＝旧构造零漂移）：
    - `over_budget`＝本轮有**追加席候选**（锚保底/表类行集/节内展开）因预算
      不足被丢（真封顶判据——不是「召回池大于预算」的普通截断，后者由
      `recalled > sent` 表达）；
    - `anchor_seated`/`rowset_added`/`summary_expanded`＝三通道**实际入窗席数**
      （`WindowSupply` 同名字段的计数投影——只数不列名）。

    V2-100 additive 一字段（D-h 可观测链收口——L0 授权）：
    - `quota_dropped`＝本轮有**族配额候选**因剩余预算不足被丢的支数（`WindowSupply`
      同名字段的计数投影）；**不得**并入 `over_budget`——两者各有独立值源、可分别判读。
    """

    observations: list[Observation]
    window_note: str
    recalled: int = 0
    sent: int = 0
    over_budget: bool = False
    anchor_seated: int = 0
    rowset_added: int = 0
    summary_expanded: int = 0
    quota_dropped: int = 0


def build_window_note(
    recalled: int,
    sent: int,
    *,
    sources: Sequence[str] = (),
    missing: Sequence[str] = (),
    extra: str = "",
) -> str:
    """window_note 组装单点（截断显式＋同窗声明＋缺位枚举——specs 行为约定 2/3）。

    - 检索/用进答案数字恒在位（agent 据此区分「没有」与「没送」）；
    - 差额段：recalled > sent 时如实带数；
    - 材料来源说法不一并立段：窗内来源 ≥2 时点名各来源（各留代表条目——供给层
      硬规则的声明面）；
    - 未纳入来源段：召回池有候选但未进窗的来源逐个点名（数量限制未及——不静默）。

    各段逐字＝本文件 NOTE_* 常量（措辞单点，V2-82e）；段间连接符「；」保持。
    **V2-122 尾接两条范围指令**（S2＋S5）：旧段（主段／差额段／同窗段／缺位段／extra）
    逐字零改，串尾按序接 `NOTE_SCOPE_DIRECTIVE`＋`NOTE_COUNT_TRUTHFUL`（同一「；」连接符）
    ——把「注记」改写成**对作答面的范围指令**：断言/否定只锚已见材料、计数必须与实际一致。
    """
    note = NOTE_RECALLED_SENT.format(recalled=recalled, sent=sent)
    if recalled > sent:
        note += "；" + NOTE_RECALL_GAP.format(gap=recalled - sent)
    if len(sources) >= 2:
        note += "；" + NOTE_CONFLICT_SOURCES + "、".join(sources)
    if missing:
        note += "；" + NOTE_MISSING_SOURCES + "、".join(missing)
    if extra:
        note += "；" + extra
    return note + "；" + NOTE_SCOPE_DIRECTIVE + "；" + NOTE_COUNT_TRUTHFUL


# ---------- 供给分池（同窗规则硬编码层——不依赖 LLM 自觉） ----------

# 节内展开通道总补席上界（V2-89b D3「节内展开加上界」）：窗内摘要支触发同节
# 切片补席时，一次检索的展开补席总数恒 ≤ 本值（且同时守 budget——双上界）。
# 数值取既有席位帽族同量级（`context/materials.MAX_REPORT_SEATS_PER_SOURCE`＝6／
# `ANCHOR_SEATS`＝6），治 RC18「按节全量追加→窗支数翻倍」。
SECTION_EXPAND_CAP = 6


def source_diversify(members: list[tuple[Hit, float]], cap: int) -> list[tuple[Hit, float]]:
    """来源多样性（G-06 移植——键＝来源指纹 report_id）。

    多报告语料下向量腿会饱和：单报告片段对问句普遍高分，按分直取会整窗挤满
    单报告。窗口内**同报告至多 cap/2 支**：按报告分组轮询各取首支，余量再按
    原序补齐——只改入选构成、不改相对序，不做任何语义判断。

    代表席摘要优先（V2-65 附 B）：每来源队列若含节级摘要支（node_kind=
    section_summary 结构标记——零语义判定），以其为队首（代表席＝摘要席，
    进窗即触发 R1b 节内整组展开——1 席撬一节，数据正文随摘要进窗；治
    V264F1 实锤「代表支被高分标题/问句类切片占据、数据表进不了窗」形）。
    摘要支占一个本源席位，队列总长仍守 per_source_cap；无摘要支队列原样，
    输出逐支不变（零漂移）。
    """
    if len(members) <= cap:
        return members
    per_source_cap = max(1, cap // 2)
    by_source: dict[str, list[tuple[Hit, float]]] = {}
    summary_pair: dict[str, tuple[Hit, float]] = {}
    order: list[str] = []
    for pair in members:
        key = pair[0].fragment.report_id or "?"
        if key not in by_source:
            by_source[key] = []
            order.append(key)
        if pair[0].fragment.node_kind == NODE_SECTION_SUMMARY:
            if key not in summary_pair:
                summary_pair[key] = pair  # 融合序最前的摘要支（首见即最优）
            continue
        if len(by_source[key]) < per_source_cap:
            by_source[key].append(pair)
    for key, pair in summary_pair.items():
        queue = by_source[key]
        queue.insert(0, pair)
        del queue[per_source_cap:]  # 摘要席占一个本源名额——总队列仍守 cap
    picked: list[tuple[Hit, float]] = []
    seen: set[int] = set()
    while len(picked) < cap:
        progressed = False
        for key in order:
            if by_source[key]:
                pair = by_source[key].pop(0)
                picked.append(pair)
                seen.add(id(pair[0]))
                progressed = True
                if len(picked) >= cap:
                    break
        if not progressed:
            break
    for pair in members:
        if len(picked) >= cap:
            break
        if id(pair[0]) not in seen:
            picked.append(pair)
            seen.add(id(pair[0]))
    return picked


@dataclass(frozen=True, slots=True)
class WindowSupply:
    """供给窗构成结果（window＝入选候选；missing＝缺位来源报告名）。

    anchor_seated（V2-45 R1a）＝题眼锚保底新增席位的来源报告名（保底实录——
    进 window_note 留痕）；rowset_added＝表类整行集扩窗支数。两者缺省空——
    旧配额路径零漂移。

    V2-89b additive 两字段（D3）：
    - `summary_expanded`＝节级摘要展开实际补席数（V2-47 R1b 通道计数）；
    - `over_budget`＝本轮有追加席候选（锚保底/行集/节内展开）因预算不足被丢
      ——**真封顶**机读位（`window` 支数恒 ≤ budget）。

    V2-100 additive 一字段（D-h）：
    - `quota_dropped`＝本轮有**族配额候选**因剩余预算不足被丢的支数（题眼席先占预算后
      配额用剩余——新丢席族）。**不得**并入 `over_budget`（后者语义冻结为「追加席候选
      被丢」——保 EB10 20/20 区分度）；两者各有独立值源，可分别判读。
    """

    window: list[tuple[Hit, float]]
    missing_sources: list[str]
    anchor_seated: tuple[str, ...] = ()
    rowset_added: int = 0
    summary_expanded: int = 0
    over_budget: bool = False
    quota_dropped: int = 0


# ---------- 题面词面判定（V2-45 R1a——表类解锁与题眼锚集，确定性零模型） ----------

# 表格/明细类问句词面：「表」后不跟动词性后缀（表示/表达/表面/表演/表决/
# 表露/表态/表述/表征/表彰——名词形「表格/表中/对照表/配注调整表/明细表」
# 全命中）；另收明细/逐日/每天/表格/行集（问数组明细题与表类题同 unlocks）。
_TABLE_NOUN_RE = re.compile(r"表(?![示达面演决露态述征彰])|明细|逐日|每天|行集")

# 题眼资产 token：字母前缀连字号数字（Y-24/W-22/SCSSV-1）与数字连字号数字
# （34-8/2025-11）两形——井号/报告号是跨来源区分度最高的题眼；纯数字
# （320/12）与纯字母词（MPa/报告）不作保底判据（防保底泛化成全员摊派）。
_ASSET_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:[A-Za-z][A-Za-z0-9]*-\d+|\d+-\d+)(?![0-9])"
)

# 表格承载片段判定：全角/宽空白缩进且含数字的行 ≥2（本库表格版式——
# 「　　Y-24　　　320　　　…」行；prose 节无缩进数字行）。
_TABLE_ROW_LINE_RE = re.compile(r"^[　 \t]{2,}.*[0-9０-９]", re.MULTILINE)


def is_table_rowset_question(question: str) -> bool:
    """表格/明细类问句判定（整行集优先规则的解锁词面——确定性零模型调用）。"""
    return _TABLE_NOUN_RE.search(question or "") is not None


def anchor_seat_tokens(
    question: str, anchors: Sequence[str] = ()
) -> tuple[str, ...]:
    """题眼锚 token 集（席位保底判定面——need.anchors 全收＋问句资产编号）。

    - 显式 anchors 全收后去重在前（@ 锚定资产名是最高置信题眼）；
    - 问句侧取资产编号形 token（井号 Y-24、报告号 34-8——alnum token 中过
      _ASSET_TOKEN_RE 全匹配者；「渤中34-8油田」连写由 alnum 切分自然出
      「34-8」）；
    - 非编号语义词锚（「注采比」类）不进保底集——它们已在召回/保送通道生效，
      不作席位判据。
    """
    tokens: list[str] = []
    for token in [*anchors, *alnum_tokens(question)]:
        cleaned = token.strip()
        if cleaned and cleaned not in tokens and _ASSET_TOKEN_RE.fullmatch(cleaned):
            tokens.append(cleaned)
    return tuple(tokens)


def _is_table_bearing(text: str) -> bool:
    """表格承载片段判定（缩进数字行 ≥2——确定性版式词面，不靠模型判断）。"""
    return len(_TABLE_ROW_LINE_RE.findall(text or "")) >= 2


# ---------- 题眼席序件（V2-100 D9／D-h——题眼锚/表格/原文候选先占预算） ----------


def _anchor_text_hit(token: str, text: str) -> bool:
    """锚 token 对单个词面的命中（V2-100 D-a——判据本体单点＝`appv2.text_tokens`）。

    - 纯数字 token → **数字记号全等**（`22` 不中 `2200`／`4.2`／`202608`）；
    - 其余（井号／资产编号／油田名）→ **边界命中**（`W-11` 不中 `W-111`）。

    本函数只做「形→判据」分派（纯字符形态判断，零语义），边界／全等**本体零副本**；
    调用方以 `casefold` 归一（L1 旧面大小写不敏感语义零漂移）。
    """
    if not token or not text:
        return False
    if token.isdigit():
        return num_token_hit(text, token)
    return boundary_hit(text, token)


def _anchor_hits(token: str, haystacks: tuple[str, ...]) -> bool:
    """锚命中三面任一（V2-82d：text ∪ report ∪ well——题面主体常只落报告名/本体标签）。

    词面先 `casefold` 归一（L1 旧面大小写不敏感语义零漂移），判据本体仍走
    `appv2.text_tokens`（边界／全等单点）。
    """
    return any(_anchor_text_hit(token, haystack.casefold()) for haystack in haystacks)


def _topic_source_cap(budget: int) -> int:
    """片段级去重上界（D-h）：同源**题眼席**数 ≤ 半个预算。

    量纲复用 `source_diversify` 的「同报告至多 cap/2 支」规则（L1 单点同尺）——
    防「同源多锚可重复占席」把预算吃干；**不**引 L3 常量（`ANCHOR_SEATS`／
    `MAX_REPORT_SEATS_PER_SOURCE`）、**不**新增数值常量。
    """
    return max(1, budget // 2)


def promote_subject_hits(
    ranked: list[tuple[Hit, float]],
    tokens: Sequence[str],
    *,
    text_of: Callable[[Hit], str],
) -> list[tuple[Hit, float]]:
    """主体命中候选**分池序内提权**（V2-117 任务 2 第一处加权——稳定分区、不改融合序公式）。

    - **池＝族**（`fragment.family`，出场序＝融合序首现序）：逐族把命中题面主体 token 的候选
      前移，族内其余候选保持原相对序；**族与族之间的出场序不动**（「分池序内提权」逐字——不是
      全局重排）；
    - 命中判据＝**三面任一**（正文 ∪ 报告名 ∪ 油田标签，复用 `_anchor_hits`——与题眼锚保底同
      判据单点）；判据本体仍走 `appv2.text_tokens` 边界／数字全等（零第二份）；
    - `tokens` 空／无命中／`ranked` 空 ⇒ **原样返回**（零漂移面）；`rrf_merge` 融合序公式零改。

    纯函数、零 IO、零模型调用。
    """
    needles = tuple(str(token).casefold() for token in tokens if str(token).strip())
    if not needles or not ranked:
        return ranked
    by_family: dict[str, list[tuple[Hit, float]]] = {}
    order: list[str] = []
    for pair in ranked:
        key = pair[0].fragment.family
        if key not in by_family:
            by_family[key] = []
            order.append(key)
        by_family[key].append(pair)
    promoted: list[tuple[Hit, float]] = []
    for key in order:
        members = by_family[key]
        hits: list[tuple[Hit, float]] = []
        misses: list[tuple[Hit, float]] = []
        for pair in members:
            frag = pair[0].fragment
            faces = (
                text_of(pair[0]),
                frag.report or "",
                frag.well or "",
            )
            if any(_anchor_hits(needle, faces) for needle in needles):
                hits.append(pair)
            else:
                misses.append(pair)
        promoted.extend(hits)
        promoted.extend(misses)
    return promoted


def _anchor_hit_sources(
    ranked: list[tuple[Hit, float]], anchors: Sequence[str]
) -> set[str]:
    """锚命中来源集（三面命中任一——V2-82d；题眼表/原文两通道的取材面）。"""
    needles = tuple(token.casefold() for token in anchors if token.strip())
    sources: set[str] = set()
    for pair in ranked:
        frag = pair[0].fragment
        if any(
            _anchor_hits(needle, (frag.text, frag.report or "", frag.well or ""))
            for needle in needles
        ):
            sources.add(frag.report_id)
    return sources


def _topic_anchor_seats(
    ranked: list[tuple[Hit, float]],
    anchors: Sequence[str],
    window: list[tuple[Hit, float]],
    picked_ids: set[str],
    budget: int,
    source_cap: int,
    source_seats: Counter[str],
) -> tuple[list[str], bool]:
    """题眼锚保底席（**新序①——先占预算**；V2-45 R1a／V2-82d／V2-100 D9）。

    逐锚取融合序**最优一支**命中该锚的未选片段（命中面＝text ∪ report ∪ well）；
    片段级去重（`picked_ids`）＋同源上界（`source_cap`）；预算尽→丢并回 `True`
    （锚保底属追加席三通道之一——`over_budget` 语义冻结面）。返回（来源报告名留痕，
    是否有锚候选因预算被丢）。
    """
    seated: list[str] = []
    dropped = False
    for token in anchors:
        needle = token.casefold()
        if not needle:
            continue
        for pair in ranked:
            frag = pair[0].fragment
            if frag.fragment_id in picked_ids:
                continue
            if not _anchor_hits(needle, (frag.text, frag.report or "", frag.well or "")):
                continue
            if len(window) >= budget:
                dropped = True
                continue
            if source_seats[frag.report_id] >= source_cap:
                continue
            window.append(pair)
            picked_ids.add(frag.fragment_id)
            source_seats[frag.report_id] += 1
            seated.append(frag.report)
            break  # 逐锚一席
    return seated, dropped


def _topic_table_seats(
    ranked: list[tuple[Hit, float]],
    anchors: Sequence[str],
    window: list[tuple[Hit, float]],
    picked_ids: set[str],
    budget: int,
    source_cap: int,
    source_seats: Counter[str],
    anchor_sources: set[str],
) -> None:
    """题眼表保底席（**新序②**；V2-93 D8 的 L1 半面——题眼表进窗，B-正6／B-正2 形）。

    每个**锚命中来源**取其首个未选**表格承载**支占一席；表文须命中锚（复用行集目标
    判据——防无关高位表格片被误当题眼表）。片段级去重＋同源上界；预算尽＝不再追加
    （表/原文两通道不属 `over_budget` 三通道，不置位）。
    """
    needles = tuple(token.casefold() for token in anchors if token.strip())
    table_sources = {
        pair[0].fragment.report_id
        for pair in window
        if _is_table_bearing(pair[0].fragment.text)
    }
    for pair in ranked:
        frag = pair[0].fragment
        key = frag.report_id
        if key not in anchor_sources or key in table_sources:
            continue
        if not _is_table_bearing(frag.text):
            continue
        if not any(_anchor_text_hit(token, frag.text.casefold()) for token in needles):
            continue
        if frag.fragment_id in picked_ids:
            continue
        if len(window) >= budget or source_seats[key] >= source_cap:
            continue
        window.append(pair)
        picked_ids.add(frag.fragment_id)
        source_seats[key] += 1
        table_sources.add(key)


def _topic_original_seats(
    ranked: list[tuple[Hit, float]],
    window: list[tuple[Hit, float]],
    picked_ids: set[str],
    budget: int,
    source_cap: int,
    source_seats: Counter[str],
    anchor_sources: set[str],
) -> None:
    """题眼原文保底席（**新序③**；D9／V2-93 D8——摘要不得顶替同源原文，NQ-C9 形）。

    锚命中来源若**尚无** `node_kind=slice` 原文席，取其首个未选原文切片占一席
    （原文本身不要求命中锚——同 L3 ②判据：节摘要命中即节相关信号）；片段级去重＋
    同源上界；预算尽＝不再追加。
    """
    slice_sources = {
        pair[0].fragment.report_id
        for pair in window
        if pair[0].fragment.node_kind == NODE_SLICE
    }
    for pair in ranked:
        frag = pair[0].fragment
        key = frag.report_id
        if key not in anchor_sources or key in slice_sources:
            continue
        if frag.node_kind != NODE_SLICE:
            continue
        if frag.fragment_id in picked_ids:
            continue
        if len(window) >= budget or source_seats[key] >= source_cap:
            continue
        window.append(pair)
        picked_ids.add(frag.fragment_id)
        source_seats[key] += 1
        slice_sources.add(key)


def supply_window(
    ranked: list[tuple[Hit, float]],
    budget: int,
    family_hints: Sequence[str] = (),
    anchors: Sequence[str] = (),
    rowset_question: bool = False,
    *,
    corpus: Sequence[FragmentRecord] = (),
) -> WindowSupply:
    """生成窗供给（specs 行为约定 2——同窗规则在供给层硬编码实现）。

    算法（确定性，零模型调用）——**V2-100 D9 席序重排：题眼候选先占预算，族配额其次**：
    1. **题眼锚/表格/原文候选先占预算**（三通道均只对**锚命中来源**生效；`anchors` 空
       ＝三通道零动作，席序与旧序逐字等价——零漂移面）：
       - 题眼锚保底（V2-45 R1a／V2-82d）：逐锚取融合序最优一支命中支（text ∪
         report ∪ well 三面任一）——消灭「多来源竞争下目标报告零席位」形；
       - 题眼表保底（V2-93 D8 的 L1 半面）：锚命中来源的表格承载支（表文命中锚）；
       - 题眼原文保底（D9）：锚命中来源的 `node_kind=slice` 原文（摘要不得顶替）；
       三通道共用**片段级去重**（`picked_ids`）＋**同源上界**（`_topic_source_cap`）。
    2. **族配额其次（用剩余预算）**：hints 命中的族共享 3/4 预算（每族 ≥1），其余族
       共享余下 1/4（每族 ≥1——完井族题不挤占月报族配额）；无 hints 全族均分。族内
       来源多样性＝source_diversify（同报告至多半额）。配额候选因剩余预算不足被丢→
       计入 additive `quota_dropped`（**不**并入 `over_budget`）。
    3. **追加席（表类整行集→节内展开）按序竞争剩余预算**（V2-89b D3 真封顶——追加席
       **计入 budget**，超预算即丢并落 `over_budget`）：
       - 表类整行集（V2-45 R1a）：rowset_question 解锁时，目标表格片段＝融合序最前的
         「表格承载＋锚命中（无锚不设锚条件）」支；其同报告同 section 的已召回候选
         整组补席（零新召回）；
       - 节内展开（V2-47 R1b）：取材＝全节语料（含未召回支）；通道总补席 ≤
         `SECTION_EXPAND_CAP`（V2-89b 加上界）。
    4. **余量补给（D-h 保留）**：以上席位仍不满预算→按融合序补未获席候选。
    5. 预算 < 候选来源数→部分来源零席位＝缺位，报告名逐个枚举（调用方进
       window_note）——题眼/整组/展开已保席的来源不再入缺位。

    送窗序列保持融合序（只丢不重排——V1 分池纪律同尺；节内展开支非召回产物
    ——接在融合序席之后，序＝窗内摘要序×语料序）。hints 不改族遍历序（族序＝
    融合序首现），只改各族配额。

    `over_budget`＝本轮有**追加席候选**因预算不足被丢（锚/行集/展开三通道任一；
    节内展开触 `SECTION_EXPAND_CAP` 上界不算——那是设计上界，不是预算不足）。
    `quota_dropped`＝本轮有**族配额候选**因剩余预算不足被丢的支数（V2-100 D-h 新
    丢席族——与 `over_budget` 各有独立值源，互不并入）。
    `corpus` 缺省空＝不启用节内展开（旧直接构造面零漂移）。
    """
    if budget <= 0 or not ranked:
        return WindowSupply(window=[], missing_sources=[])
    families: list[str] = []
    by_family: dict[str, list[tuple[Hit, float]]] = {}
    hints = frozenset(family_hints)
    for pair in ranked:
        key = pair[0].fragment.family
        if key not in by_family:
            by_family[key] = []
            families.append(key)
        by_family[key].append(pair)

    quotas: dict[str, int] = {}
    if hints:
        hinted = [f for f in families if f in hints]
        others = [f for f in families if f not in hints]
        if hinted:
            share = max(1, math.ceil(budget * 3 / 4))
            per = max(1, share // len(hinted))
            for family in hinted:
                quotas[family] = per
        if others:
            rest = max(1, budget - sum(quotas.values()))
            per = max(1, rest // len(others))
            for family in others:
                quotas[family] = per
    else:
        per = max(1, budget // len(families))
        for family in families:
            quotas[family] = per

    window: list[tuple[Hit, float]] = []
    picked_ids: set[str] = set()
    source_seats: Counter[str] = Counter()
    source_cap = _topic_source_cap(budget)

    # ① 题眼锚/表格/原文候选**先占预算**（V2-100 D9 新序——anchors 空＝三通道零动作，
    # 席序与旧序逐字等价）。三通道共用片段级去重＋同源上界（D-h）。
    anchor_seated: list[str] = []
    anchor_dropped = False
    if anchors:
        anchor_seated, anchor_dropped = _topic_anchor_seats(
            ranked, anchors, window, picked_ids, budget, source_cap, source_seats
        )
        anchor_sources = _anchor_hit_sources(ranked, anchors)
        _topic_table_seats(
            ranked, anchors, window, picked_ids, budget, source_cap,
            source_seats, anchor_sources,
        )
        _topic_original_seats(
            ranked, window, picked_ids, budget, source_cap, source_seats,
            anchor_sources,
        )

    # ② 族配额**用剩余预算**（不再预先吃干——配额候选因剩余不足被丢→ additive
    # `quota_dropped`，**不**并入 `over_budget`）。族内来源多样性同旧尺。
    quota_dropped = 0
    for family in families:
        take = quotas[family]
        available = [
            pair
            for pair in by_family[family]
            if pair[0].fragment.fragment_id not in picked_ids
        ]
        for pair in source_diversify(available, take):
            if len(window) >= budget:
                quota_dropped += 1  # 新丢席族（V2-100 D-h）
                continue
            window.append(pair)
            picked_ids.add(pair[0].fragment.fragment_id)

    # 表类整行集（追加席——计入 budget，超则丢）：目标表格片段同组整补。
    # 锚命中判据＝`appv2.text_tokens` 单点（V2-100 D-a——边界/全等本体零副本）。
    rowset_added = 0
    rowset_dropped = False
    if rowset_question:
        anchor_tokens = tuple(token.casefold() for token in anchors if token.strip())
        target_key: tuple[str, str | None] | None = None
        for pair in ranked:
            frag = pair[0].fragment
            if not _is_table_bearing(frag.text):
                continue
            if anchor_tokens and not any(
                _anchor_text_hit(token, frag.text.casefold()) for token in anchor_tokens
            ):
                continue
            target_key = (frag.report_id, frag.section)
            break
        if target_key is not None:
            for pair in ranked:
                frag = pair[0].fragment
                if (frag.report_id, frag.section) != target_key:
                    continue
                if frag.fragment_id in picked_ids:
                    continue
                if len(window) >= budget:
                    rowset_dropped = True  # 真封顶：预算尽→不再追加
                    continue
                window.append(pair)
                picked_ids.add(frag.fragment_id)
                rowset_added += 1

    # 节内展开（追加席——计入 budget；通道总上界 SECTION_EXPAND_CAP）。
    expanded, expand_dropped = _expand_summary_seats(
        window, picked_ids, corpus, budget
    )

    # 余量补给（D-h 显式保留）：以上席位仍不满预算时按融合序补齐（追加席优先于
    # 通用余量；计数含节内展开支——总席恒 ≤ budget）。
    if len(window) + len(expanded) < budget:
        for pair in ranked:
            if len(window) + len(expanded) >= budget:
                break
            if pair[0].fragment.fragment_id not in picked_ids:
                window.append(pair)
                picked_ids.add(pair[0].fragment.fragment_id)

    # 缺位来源：召回池有候选但零席位（预算 < 来源数）——报告名枚举不静默
    # （题眼/整组/展开已保席的来源不在此列——扩席如实先于缺位判定）。
    seated_reports = {pair[0].fragment.report for pair in [*window, *expanded]}
    missing: list[str] = []
    for pair in ranked:
        report = pair[0].fragment.report
        if report not in seated_reports and report not in missing:
            missing.append(report)

    # 保持融合序（只丢不重排）；节内展开支非召回产物——接在融合序席之后。
    order = {id(pair[0]): i for i, pair in enumerate(ranked)}
    window.sort(key=lambda pair: order[id(pair[0])])
    window.extend(expanded)
    return WindowSupply(
        window=window,
        missing_sources=missing,
        anchor_seated=tuple(anchor_seated),
        rowset_added=rowset_added,
        summary_expanded=len(expanded),
        over_budget=anchor_dropped or rowset_dropped or expand_dropped,
        quota_dropped=quota_dropped,
    )


def _expand_summary_seats(
    window: list[tuple[Hit, float]],
    picked_ids: set[str],
    corpus: Sequence[FragmentRecord],
    budget: int,
    *,
    cap: int = SECTION_EXPAND_CAP,
) -> tuple[list[tuple[Hit, float]], bool]:
    """节级摘要展开（V2-47 R1b——窗内摘要节点→其节内切片补席，计入预算）。

    - 成员判据＝（report_id, section_root(section)）同簇（簇键与富化批聚类
      同一单点 domain.section_root）；
    - 取材＝全节语料（含未召回支——R1b 索引期治本面：摘要命中即节相关信号，
      节内切片不该因自身词面弱而被拒）；
    - 追加席：窗内已有支不重补；序＝窗内摘要序×语料序（确定性）；融合分槽
      记 0.0（非召回产物——只作窗成员，不参与供给序）；
    - **双上界（V2-89b D3）**：补席总数 ≤ `cap`（SECTION_EXPAND_CAP）且
      `len(window) + 补席数 ≤ budget`——超预算丢席并回 `True`（over_budget
      值源；触 `cap` 上界不回 True——那是设计上界，非预算不足）。
    """
    expanded: list[tuple[Hit, float]] = []
    dropped = False
    if not corpus or cap <= 0:
        return expanded, dropped
    for pair in window:
        frag = pair[0].fragment
        if frag.node_kind != NODE_SECTION_SUMMARY:
            continue
        for cand in corpus:
            if cand.node_kind != NODE_SLICE:
                continue
            if cand.report_id != frag.report_id:
                continue
            if section_root(cand.section) != frag.section:
                continue
            if cand.fragment_id in picked_ids:
                continue
            if len(window) + len(expanded) >= budget:
                dropped = True  # 预算尽——不再追加
                continue
            if len(expanded) >= cap:
                continue  # 通道上界（设计上界，不记 over_budget）
            picked_ids.add(cand.fragment_id)
            expanded.append((Hit(cand, pair[0].score, pair[0].leg), 0.0))
    return expanded, dropped


# ---------- LLM 精排解析面（批量排序＋来源置信度——失败回退由 engine 兜） ----------


def parse_rank_order(content: str, n: int) -> list[int]:
    """批量精排应答 → 候选下标序（0 基；未覆盖的下标按原序追加在尾）。

    只重排不丢弃——编号表未覆盖的候选按原序补齐（W-F34-2 回退不炸链的解析半边）；
    无任何合法编号 → 空表（调用方按原序放行）。
    """
    nums = [int(v) for v in re.findall(r"\d+", content or "")]
    seen: set[int] = set()
    ordered: list[int] = []
    for value in nums:
        if 1 <= value <= n and value not in seen:
            seen.add(value)
            ordered.append(value - 1)
    for i in range(n):
        if i not in seen:
            seen.add(i)
            ordered.append(i)
    return ordered


def parse_confidence_scores(content: str, source_count: int) -> dict[int, float] | None:
    """来源置信度应答 → {来源序号(1 基): 0~10 分}；解析失败/缺任一来源分 → None。

    缺任一来源的分＝整份打分不可信——回退固定配额，不静默丢来源（V1 A9 同判据）。
    """
    try:
        payload = json.loads(_json_blob(content or ""))
        raw = payload["scores"]
        if not isinstance(raw, Mapping):
            return None
        scored: dict[int, float] = {}
        for i in range(1, source_count + 1):
            if str(i) not in raw:
                return None
            scored[i] = max(0.0, min(10.0, float(raw[str(i)])))
        return scored or None
    except Exception:
        return None


def _json_blob(text: str) -> str:
    """从模型回复截取首个平衡的 {...} 块（MiniMax 偶发 ```json 围栏包裹——括号配平）。"""
    start = text.find("{")
    if start < 0:
        raise ValueError("回复中无 JSON 块")
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    raise ValueError("JSON 块未闭合")


def snippet_window(text: str, question: str, width: int = 200) -> str:
    """锚点窗口摘录（V1 精排/置信度摘录共用——问句强 token 首次命中处对准取窗）。

    固定开头会把「锚词在片段中后部」的含锚片段判成无关（Q8 云端实证）；无命中
    回落片段开头。纯词面零模型调用。
    """
    plain = (text or "").replace("\n", " ")
    best: int | None = None
    for tok in re.findall(r"[A-Za-z]+-\d+|\d+(?:\.\d+)?|[A-Za-z]{2,}", question or ""):
        if len(tok) < 2:
            continue
        pos = plain.find(tok)
        if pos >= 0 and (best is None or pos < best):
            best = pos
    if best is None:
        return plain[:width]
    start = max(0, best - 40)
    return ("…" if start > 0 else "") + plain[start : start + width]
