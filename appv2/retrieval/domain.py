"""retrieval.domain —— 检索 schema 与纯语义（V2-04，specs/retrieval.md 接口定义节）。

V1 S4 双路召回＋精排＋生成窗供给移植为确定性引擎的纯语义层（零 I/O——B1：
本文件不 import fastapi/DB/供应商 SDK；IO 归 source/engine 的注入缝）。

供给策略本体化（specs/retrieval.md 目标节——Q11 P0-2「生成窗截断→材料未披露
虚答」与同型抢锚病灶的治理面）：
- **矛盾来源同窗并立**：送窗预算内每来源（来源指纹＝报告）至少留代表支——
  supply_window 硬编码实现，不依赖 LLM 自觉；
- **截断显式**：window_note 如实带「召回 N 支/送窗 M 支」数字——agent 据此
  区分「没有」与「没送」；
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
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

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

# 切片上下文前缀逐字格式（票面钉：〔本段节选自〈报告名〉·〈章节路径〉〕——
# Anthropic 上下文感知检索式；报告名/章节路径取 kb 台账元数据，零模型调用）。
CONTEXT_PREFIX_TEMPLATE = "〔本段节选自{report}·{section}〕"
CONTEXT_PREFIX_NO_SECTION = "〔本段节选自{report}〕"

SECTION_PATH_SEPARATOR = "＞"  # 章节路径层级分隔（kb 台账 section 原生形）


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
    如实声明「召回 N 支/送窗 M 支/矛盾来源已同窗或已列缺位」。
    """

    observations: list[Observation]
    window_note: str


def build_window_note(
    recalled: int,
    sent: int,
    *,
    sources: Sequence[str] = (),
    missing: Sequence[str] = (),
    extra: str = "",
) -> str:
    """window_note 组装单点（截断显式＋同窗声明＋缺位枚举——specs 行为约定 2/3）。

    - 召回/送窗数字恒在位（agent 据此区分「没有」与「没送」）；
    - 已召回未送窗差额段：recalled > sent 时如实带数；
    - 矛盾来源同窗并立段：窗内来源 ≥2 时点名各来源（各留代表支——供给层
      硬规则的声明面）；
    - 缺位来源段：召回池有候选但未进窗的来源逐个点名（预算未及——不静默）。
    """
    note = f"召回 {recalled} 支/送窗 {sent} 支"
    if recalled > sent:
        note += f"；已召回未送窗 {recalled - sent} 支"
    if len(sources) >= 2:
        note += "；矛盾来源同窗并立（各留代表支）：" + "、".join(sources)
    if missing:
        note += "；缺位来源（预算未及）：" + "、".join(missing)
    if extra:
        note += "；" + extra
    return note


# ---------- 供给分池（同窗规则硬编码层——不依赖 LLM 自觉） ----------


def source_diversify(members: list[tuple[Hit, float]], cap: int) -> list[tuple[Hit, float]]:
    """来源多样性（G-06 移植——键＝来源指纹 report_id）。

    多报告语料下向量腿会饱和：单报告片段对问句普遍高分，按分直取会整窗挤满
    单报告。窗口内**同报告至多 cap/2 支**：按报告分组轮询各取首支，余量再按
    原序补齐——只改入选构成、不改相对序，不做任何语义判断。
    """
    if len(members) <= cap:
        return members
    per_source_cap = max(1, cap // 2)
    by_source: dict[str, list[tuple[Hit, float]]] = {}
    order: list[str] = []
    for pair in members:
        key = pair[0].fragment.report_id or "?"
        if key not in by_source:
            by_source[key] = []
            order.append(key)
        if len(by_source[key]) < per_source_cap:
            by_source[key].append(pair)
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
    进 window_note 留痕）；rowset_added＝表类整行集扩窗支数（不计入配额的
    增量实录）。两者缺省空——旧配额路径零漂移。
    """

    window: list[tuple[Hit, float]]
    missing_sources: list[str]
    anchor_seated: tuple[str, ...] = ()
    rowset_added: int = 0


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


def supply_window(
    ranked: list[tuple[Hit, float]],
    budget: int,
    family_hints: Sequence[str] = (),
    anchors: Sequence[str] = (),
    rowset_question: bool = False,
) -> WindowSupply:
    """生成窗供给（specs 行为约定 2——同窗规则在供给层硬编码实现）。

    算法（确定性，零模型调用）：
    1. 族配额：hints 命中的族共享 3/4 预算（每族 ≥1），其余族共享余下 1/4
       （每族 ≥1 保底——完井族题不挤占月报族配额）；无 hints 全族均分
       （每族 ≥1）。
    2. 族内来源多样性：source_diversify（同报告至多半额——每来源至少留
       代表支）。
    3. 族配额用不满（该族候选少于配额）→余量按融合序补给未满预算的其他候选。
    4. 题眼锚保底（V2-45 R1a——多来源竞争下锚命中来源 ≥1 席位，消灭目标
       报告零席位形）：逐锚找「片段文本命中该锚的来源」，未获席者取其融合序
       最优一支追加进窗（追加席——不挤占既有族分池代表支；窗支数照实可超
       预算，window_note 数字面如实）。锚集由调用方给（engine 侧
       anchor_seat_tokens——显式锚＋问句资产编号）。
    5. 表类整行集（V2-45 R1a——明细/表格类整行集优先）：rowset_question
       解锁时，目标表格片段＝融合序最前的「表格承载＋锚命中（无锚不设锚
       条件）」支；其同报告同 section 的已召回候选整组补席（不计入单支配额，
       只从召回池取——零新召回）。
    6. 预算 < 候选来源数→部分来源零席位＝缺位，报告名逐个枚举（调用方进
       window_note）——锚保底/整组已保席的来源不再入缺位。

    送窗序列保持融合序（只丢不重排——V1 分池纪律同尺）。hints 不改族遍历序
    （族序＝融合序首现），只改各族配额。
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
    for family in families:
        take = quotas[family]
        remaining = budget - len(window)
        if remaining <= 0:
            break
        take = min(take, remaining)
        members = by_family[family]
        for pair in source_diversify(members, take):
            if len(window) >= budget:
                break
            window.append(pair)
            picked_ids.add(pair[0].fragment.fragment_id)

    # 余量补给：族配额用不满（候选少于配额）时按融合序补齐预算。
    if len(window) < budget:
        for pair in ranked:
            if len(window) >= budget:
                break
            if pair[0].fragment.fragment_id not in picked_ids:
                window.append(pair)
                picked_ids.add(pair[0].fragment.fragment_id)

    # 题眼锚保底（追加席——见 docstring 4）：逐锚扫全召回池，文本命中该锚的
    # 每个来源未获席者各补 1 席（来源级去重；代表席＝该来源融合序最优命中支）。
    anchor_seated: list[str] = []
    for token in anchors:
        needle = token.casefold()
        if not needle:
            continue
        for pair in ranked:
            frag = pair[0].fragment
            if needle not in frag.text.casefold():
                continue
            if any(p[0].fragment.report == frag.report for p in window):
                continue  # 该来源已有席位——继续找同锚的其他命中来源
            window.append(pair)
            picked_ids.add(frag.fragment_id)
            anchor_seated.append(frag.report)

    # 表类整行集（追加席——见 docstring 5）：目标表格片段同组整补。
    rowset_added = 0
    if rowset_question:
        anchor_set = {token.casefold() for token in anchors}
        target_key: tuple[str, str | None] | None = None
        for pair in ranked:
            frag = pair[0].fragment
            if not _is_table_bearing(frag.text):
                continue
            if anchor_set and not any(
                token in frag.text.casefold() for token in anchor_set
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
                window.append(pair)
                picked_ids.add(frag.fragment_id)
                rowset_added += 1

    # 缺位来源：召回池有候选但零席位（预算 < 来源数）——报告名枚举不静默
    # （锚保底/整组已保席的来源不在此列——扩席如实先于缺位判定）。
    seated_reports = {pair[0].fragment.report for pair in window}
    missing: list[str] = []
    for pair in ranked:
        report = pair[0].fragment.report
        if report not in seated_reports and report not in missing:
            missing.append(report)

    # 保持融合序（只丢不重排）。
    order = {id(pair[0]): i for i, pair in enumerate(ranked)}
    window.sort(key=lambda pair: order[id(pair[0])])
    return WindowSupply(
        window=window,
        missing_sources=missing,
        anchor_seated=tuple(anchor_seated),
        rowset_added=rowset_added,
    )


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
