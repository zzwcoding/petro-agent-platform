"""domains.derivatives.domain —— 派生物域（wiki 支路）语义（厚：B4 合同语义在此闭环）。

合同锚（真源在 teach-petro-agent/specs/api/，只引路径不复制正文）：
- B4-报告百科.md v0.4（Owner 2026-10-04 拍板：版本治理整体撤除）：两读端点
  （目录/全文）、「与 B1 的生产/消费边界」（生成方＝B1 管线 wiki 支路；重建
  触发＝入库、重跑、片段修正；重写≠检索；1:1 报告；开关关→不生成；截断
  防护＝半页不落库；slug 稳定性＝id 承载）、「论断回链」节（claims[]
  fail-closed）、「台账挂接」节（glossary_terms[] 台账无账不挂、生成时固化
  不回溯）、wiki 模板语义（模板＝提示词约束、产出自由 markdown、零固定节
  schema）、覆盖语义（行为规则 1：重建覆盖当前版、current_version＝重建计数
  单调 +1、无版本历史不可回滚）、生成来源单态（v0.4 只余「自动重建」）、
  错误码草案（404/401/403）、行为规则汇总 12 条。
- B1-报告库.md v0.3 端点 4 注记：修正定型→FragmentRevised 事件→重铸队列→
  覆盖当前版（来源「自动重建」）；重铸失败不阻塞修正（记活动流，可手动重
  跑——当前版保持旧内容）。
- PRD F50：chunk 拼回全文（重叠去重＋图片回读）→LLM 重写 Markdown 页；
  32K 截断（WeKnora maxContentForWiki=32768）＋票 104 截断防护（最多续写
  3 轮、未完放弃本次写入不落半页）；F51 slug 稳定性/单字不挂链；
  F52 知识层/证据层分离＋论断回链（版本治理四件随 B4 v0.4 撤除或关单）。
- 98-模块划分与分层.md §3.5 derivatives 卡＋§8 事件表（IngestCompleted/
  FragmentRevised 订阅）；B9 边界（kb 禁直调 derivatives；derivatives→kb
  仅 record_activity＋报告读面＋wiki 重建计数投影回写）。
- 99-数据库与连接层设计.md §2.7：wiki_page/wiki_page_version 逐字段
  （v0.4 起版本表写路径撤除——表保留不删留档；99 册 §2.7 v0.4 已对齐
  （teach 000d11a）：wiki_page 页级三列＝当前版载体）。

B1：本文件不 import fastapi/starlette/DB/LLM——拼回去重、截断纪律、
claims 锚校验、台账 linkify、状态派生都是纯语义。
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from collections.abc import Set as AbstractSet
from dataclasses import dataclass, field
from dataclasses import replace as _replace
from difflib import SequenceMatcher
from typing import Any

# ---------- 合同常量（B4/99 照抄，不可改） ----------

# 来源态（99 §2.7 CHECK 四态冻结值照抄——B4 v0.4 起产生路径只余「自动重建」
# 一态（回滚/人工/智能体随版本治理撤除无产生路径），值域留档不删：版本表
# 保留不撤、CHECK 随表留档）。
WIKI_SOURCES: tuple[str, ...] = ("自动重建", "智能体", "人工", "回滚")
SOURCE_AUTO = "自动重建"

# 状态两态（B4 合同常量表：按当前版正文有无 [[flag:]] 修订提示判定）。
STATUS_PENDING = "字段待核对"
STATUS_OK = "正常"
FLAG_MARKER_PREFIX = "[[flag:"

# 截断纪律（PRD F50 票 104）：拼回稿 32K 截断（WeKnora maxContentForWiki）；
# LLM 输出最多续写 3 轮、仍未完放弃本次写入不落半页。
WIKI_SOURCE_MAX_CHARS = 32768
WIKI_CONTINUE_ROUNDS = 3
# 结束哨兵：生成侧纪律标记（提示词要求全文结束另起一行输出；落库前剥除，
# 不入 content——实现选型，挂差异登记）。
WIKI_END_MARKER = "<!--WIKI-END-->"

# 操作人口径（B4 端点 2 元数据条 operator：自动重建恒「系统（入库管线）」
# ——合同值照抄；v0.4 起生成来源单态，operator 恒该值、读面派生不落列）。
OPERATOR_SYSTEM = "系统（入库管线）"

# related_objects 链接（B4 元数据条展开区：#A2 井档案深查＋#B5 关系图谱）。
RELATED_OBJECT_LINKS: tuple[str, ...] = ("#/A2", "#/B5")

# digest 一句话摘要展示上限（B4 未冻结长度——实施批定档，常量集中可调）。
DIGEST_MAX_CHARS = 60

# 台账挂接防误链（F51 同族纪律）：单字不挂链。
GLOSSARY_MIN_WORD_CHARS = 2

# [[…]] 标记族（B4 链接标记语法冻结）。
MARKER_RE = re.compile(r"\[\[(well|route|claim|term|flag):([^\]]*)\]\]")
CLAIM_MARKER_RE = re.compile(r"\[\[claim:([^\]]+)\]\]")


# ---------- 错误族（映射归 api/errors.py；00 §3 统一错误包） ----------


class WikiNotFoundError(Exception):
    """百科页不存在（B4 错误码草案 404——含 wiki 开关关未生成、直调未知 id；
    v0.4 纯读两态：400/409 版本/回滚族错误码随端点撤除一并废止）。"""


# ---------- id/slug（F51 slug 稳定性＝id 承载；99：id（wiki- slug，稳定不随重建变化）） ----------


def page_slug_for_report(report_id: str) -> str:
    """报告 → 页 slug：rpt-n02-completion → wiki-n02-completion。

    稳定性由「1:1 报告一页＋按 source_report_id 原地复用」承载：报告重解析
    （重跑/重铸）命中既有页原地更新，slug 不再生成；非字母数字归一为连字符。
    """
    stem = re.sub(r"^rpt-", "", report_id)
    stem = re.sub(r"[^0-9A-Za-z]+", "-", stem).strip("-").casefold()
    return f"wiki-{stem}"


# ---------- 拼回全文（F50：chunk 拼回＋重叠去重＋图片回读） ----------

_IMAGE_TYPES: tuple[str, ...] = ("图片说明块", "图片文字块")
_IMAGE_PREFIX: dict[str, str] = {"图片说明块": "插图说明：", "图片文字块": "插图文字："}


def _drop_overlap(prev: str, nxt: str) -> str:
    """相邻重叠去重：next 的前缀若与 prev 的后缀重合（切段 10–20% 回带）则剥除。

    取最长安全重合（≤ 较短串一半，防假重合整段吞并）。
    """
    if not prev or not nxt:
        return nxt
    cap = min(len(prev), len(nxt)) // 2
    best = 0
    for size in range(min(cap, len(nxt)), 0, -1):
        if prev.endswith(nxt[:size]):
            best = size
            break
    return nxt[best:]


def reconstruct_content(chunks: list[tuple[str, str, str]]) -> str:
    """块拼回全文：入参 [(类型, 节路径, 文本)]——text 块拼回＋图片块连图注回读。

    - 相邻重叠去重（F50/WeKnora reconstructContent 只取 text 块拼回同象）；
    - 图片说明块/图片文字块连图注回读（F36——否则纯图片文档产出空内容），
      以「插图说明：/插图文字：」前缀行并入正文流。
    """
    parts: list[str] = []
    for frag_type, _section, text in chunks:
        text = (text or "").strip()
        if not text:
            continue
        if frag_type in _IMAGE_TYPES:
            parts.append(f"{_IMAGE_PREFIX.get(frag_type, '')}{text}")
            continue
        if parts:
            prev = parts[-1]
            parts.append(_drop_overlap(prev, text))
        else:
            parts.append(text)
    return "\n".join(part for part in parts if part)


def truncate_for_wiki(text: str) -> str:
    """32K 截断（F50）：超限在段落边界截断（半行不入稿）。"""
    if len(text) <= WIKI_SOURCE_MAX_CHARS:
        return text
    head = text[:WIKI_SOURCE_MAX_CHARS]
    cut = head.rfind("\n")
    return head[:cut] if cut > 0 else head


# ---------- 截断纪律（续写 3 轮、未完放弃——半页不落库） ----------


def looks_unfinished(content: str) -> bool:
    """未完判定：结束哨兵缺失（提示词要求全文结束另起一行输出哨兵）。"""
    return WIKI_END_MARKER not in content


def strip_sentinel(content: str) -> str:
    """落库前剥除哨兵行（纪律标记不入 content）。"""
    lines = [
        line for line in content.splitlines() if line.strip() != WIKI_END_MARKER
    ]
    return "\n".join(lines).strip()


CONTINUE_PROMPT_TEMPLATE = """上面的百科页尚未写完（缺结束标记）。请从截断处无缝续写剩余部分：
不要重复已有内容、不要另起开头，直接接续；全文写完后另起一行单独输出 {sentinel}。

已有正文：
{partial}
"""


# ---------- wiki 生成提示词（模板＝提示词约束——B4 v0.3/WeKnora prompts_wiki.go） ----------

# 按库业务模板的提示词取向（WikiConfig 落地＝B1 库业务模板投影——挂差异登记）。
WIKI_TEMPLATE_ORIENTATIONS: dict[str, str] = {
    "completion": (
        "面向完井报告：概述、完井段与投产信息、关键参数表（井别/投产日期/平台/区块/状态等）。"
    ),
    "monthly": "面向生产月报：概述、检修与停产情况、生产计量与折算口径、涉及指标与术语。",
    "dynamic": "面向动态分析：概述、动态特征、措施与效果、结论与建议。",
    "blank": "通用报告：按内容自由组织小节。",
}

WIKI_PROMPT_TEMPLATE = """你是油田知识平台的百科页写手。请把下面的「拼回稿」重写成一篇中文百科页。

写作要求（模板约束只在提示词里，产出自由 markdown、不设固定小节）：
- 自由 markdown：小节标题、段落、表格、列表随内容长出，像维基百科条目一样可读；
- 必须像 Wikipedia 一样建链接：正文出现的井号/井名等实体词写成 [[well:<井号>]] 标记；
- 论断可回链证据：关键论断、参数值、表格行后加证据锚 [[claim:<片段号>]]——
  片段号只能取下方清单中的号，清单之外一律不加（宁缺勿错挂）；
- 只写报告里有的事实，不发明数据、不改原始数值；中文行文；
- 全文写完后，另起一行单独输出一行 {sentinel} 作为结束标记（必须输出，不要省略）。

页面取向：{orientation}
来源报告：{doc}

片段清单（片段号：节路径 · 类型 · 摘录）：
{fragment_lines}

拼回稿：
{content}
"""


def build_wiki_prompt(
    doc: str, biz_template: str, fragments: list[tuple[str, str, str, str]],
    content: str,
) -> str:
    """组装生成提示词：fragments＝[(片段号, 节路径, 类型, 摘录)]。"""
    fragment_lines = "\n".join(
        f"- {fid}：{section} · {frag_type} · {excerpt}"
        for fid, section, frag_type, excerpt in fragments
    )
    return WIKI_PROMPT_TEMPLATE.format(
        sentinel=WIKI_END_MARKER,
        orientation=WIKI_TEMPLATE_ORIENTATIONS.get(
            biz_template, WIKI_TEMPLATE_ORIENTATIONS["blank"]
        ),
        doc=doc,
        fragment_lines=fragment_lines or "（无）",
        content=content,
    )


def build_continue_prompt(partial: str) -> str:
    return CONTINUE_PROMPT_TEMPLATE.format(sentinel=WIKI_END_MARKER, partial=partial)


# ---------- 论断回链（claims[]——fail-closed：锚失效/无锚论断不渲染 [证]） ----------


@dataclass(frozen=True, slots=True)
class ClaimRow:
    claim_id: str
    text: str
    evidence_chunk_ids: list[str]


def _strip_markers(line: str) -> str:
    return MARKER_RE.sub("", line).strip()


def extract_claims(
    content: str, valid_chunk_ids: set[str], *, claim_id_prefix: str = "c"
) -> tuple[str, list[ClaimRow]]:
    """从 LLM 稿提取论断锚并 fail-closed 校验（生成时做——票面）。

    - [[claim:<片段号>]] 逐个校验：片段号不在报告片段集 → **剥除标记**（不渲染
      [证]、不伪造回链——锚失效 fail-closed）；
    - 论断 text＝标记所在句/行的纯文本投影（剥除全部 [[…]] 标记）；
    - 校验后无有效锚的论断不进 claims[]（无锚论断不渲染）。
    返回 (剥除无效标记后的 content, claims)。
    """

    lines = content.splitlines()
    claims: list[ClaimRow] = []
    seen_lines: set[str] = set()
    out_lines: list[str] = []
    seq = 0
    for line in lines:
        anchors = CLAIM_MARKER_RE.findall(line)
        if not anchors:
            out_lines.append(line)
            continue
        # fail-closed：失效锚标记就地剥除（不渲染 [证]、不伪造回链）
        line = CLAIM_MARKER_RE.sub(
            lambda m: m.group(0) if m.group(1) in valid_chunk_ids else "", line
        )
        valid = [a for a in anchors if a in valid_chunk_ids]
        if valid:
            seq += 1
            claim_id = f"{claim_id_prefix}{seq}"
            text = _strip_markers(line)
            if text and text not in seen_lines:
                seen_lines.add(text)
                claims.append(
                    ClaimRow(claim_id=claim_id, text=text, evidence_chunk_ids=valid)
                )
        out_lines.append(line)
    return "\n".join(out_lines), claims


# ---------- 台账挂接（glossary_terms[]——台账无账不挂、单字不挂链） ----------


@dataclass(frozen=True, slots=True)
class GlossaryCard:
    """C1 卡片投影（端点 2/3 行同形——服务端生成时从台账直取投影、不建仓）。"""

    kind: str  # term | metric
    ref_id: int
    card: dict[str, Any]


@dataclass(frozen=True, slots=True)
class GlossaryRegistry:
    """挂接词表（＝C1 台账名册＋别名投影：术语名＋指标槽位纯名）→ 卡片。"""

    words: dict[str, GlossaryCard] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.words)


def linkify_glossary(
    content: str, registry: GlossaryRegistry
) -> tuple[str, list[dict[str, Any]]]:
    """台账挂接：正文词命中名册 → [[term:词]] 标记＋glossary_terms[] 投影。

    - 台账无账不挂（词表驱动，裸词「含水率」不挂、名册词「综合含水率」挂）；
    - 单字不挂链（F51 防误链同族）；
    - 标记不嵌套：已在 [[…]] 标记内的文本不再挂接；
    - 长词优先（防「净产量」截断「月度净产量」一类短词先吞）。
    返回 (挂接后 content, [{word, kind, ref_id, card}])。
    """
    words = sorted(
        (w for w in registry.words if len(w) >= GLOSSARY_MIN_WORD_CHARS),
        key=len, reverse=True,
    )
    protected_spans: list[tuple[int, int]] = [
        m.span() for m in re.finditer(r"\[\[[^\]]*\]\]", content)
    ]

    def _protected(pos: int) -> bool:
        return any(start <= pos < end for start, end in protected_spans)

    linked: list[dict[str, Any]] = []
    for word in words:
        start = 0
        while True:
            idx = content.find(word, start)
            if idx < 0:
                break
            end = idx + len(word)
            if _protected(idx) or _protected(end - 1):
                start = end
                continue
            content = content[:idx] + f"[[term:{word}]]" + content[end:]
            shift = len(word) + len("[[term:]]")
            protected_spans = [(s + shift, e + shift) if s >= idx else (s, e)
                               for s, e in protected_spans]
            protected_spans.append((idx, idx + shift))
            start = idx + shift
    for word in words:
        if f"[[term:{word}]]" in content:
            card = registry.words[word]
            linked.append(
                {
                    "word": word,
                    "kind": card.kind,
                    "ref_id": card.ref_id,
                    "card": dict(card.card),
                }
            )
    return content, linked


# ---------- 状态派生与 digest（服务端组装——前端零拼装业务文案） ----------


def page_status_of(content: str) -> str:
    """状态两态：当前版正文有未消除 [[flag:]] → 字段待核对，无 → 正常。"""
    return STATUS_PENDING if FLAG_MARKER_PREFIX in content else STATUS_OK


def derive_digest(content: str) -> str:
    """一句话摘要（B4 digest——目录/元数据条候选摘要用；展示串读侧派生不另调 LLM）。"""
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "|", "-", "*", ">", "!")):
            continue
        plain = _strip_markers(stripped)
        for stop in ("。", "；", "！？"):
            idx = plain.find(stop)
            if idx >= 0:
                plain = plain[: idx + 1]
                break
        return plain[:DIGEST_MAX_CHARS]
    return ""


# ---------- DTO（读面投影——api 层直接消费） ----------


@dataclass(frozen=True, slots=True)
class WikiPageListItem:
    """目录行（端点 1——B4 v0.4：撤 version_count，current_version＝重建计数）。"""

    id: str
    title: str
    lib: str
    source_report_id: str
    source_report_doc: str
    current_version: int
    updated: str
    status: str


@dataclass(frozen=True, slots=True)
class RelatedObjectView:
    """关联对象投影（元数据条展开区——井档案只读投影，链 #A2/#B5）。"""

    type: str
    id: str
    summary: str
    links: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {"type": self.type, "id": self.id, "summary": self.summary,
                "links": list(self.links)}


@dataclass(frozen=True, slots=True)
class WikiPageDetail:
    """百科页全文（端点 2——B4 v0.4：元数据＋自由 markdown 正文＋claims＋
    glossary_terms；恒当前版，无 ?version=N；撤 version_count）。"""

    id: str
    title: str
    lib: str
    slug: str
    digest: str | None
    source_report_id: str
    source_report_doc: str
    current_version: int
    updated: str
    status: str
    generation_source: str
    operator: str | None
    related_objects: list[RelatedObjectView]
    content: str
    claims: list[dict[str, Any]]
    glossary_terms: list[dict[str, Any]]


# =====================================================================
# graph 子域（B5-关系图谱.md v0.2——P1-05）
# =====================================================================

# ---------- 合同常量（B5 v0.2 照抄，不可改） ----------

# 被拦边 reason_code 三值（铁律三闸对偶，端点 4 合同冻结）。
REASON_TYPE_MISMATCH = "type_mismatch"
REASON_NO_EVIDENCE = "no_evidence"
REASON_UNCERTAIN = "uncertain"
REASON_CODES: tuple[str, ...] = (
    REASON_TYPE_MISMATCH, REASON_NO_EVIDENCE, REASON_UNCERTAIN,
)

# 拦下 reason 人话（服务端组装——端点 4 DTO reason 字段；铁律三闸语义对应）。
REASON_TEXT: dict[str, str] = {
    REASON_TYPE_MISMATCH: "类型/关系标签不在该库抽取配置清单内（类型闸拦下）",
    REASON_NO_EVIDENCE: "原文里找不到依据句（依据闸拦下）",
    REASON_UNCERTAIN: "抽取模型自报拿不准（弃权跳过——拿不准宁可跳过，不胡编）",
}

# F40 出厂默认实体类型（合同常量表冻结原文——留档；本仓出厂默认落本体对号
# 表，见 DEFAULT_EXTRACT_CONFIG 注记，此常量仅承载合同值供对账）。
F40_DEFAULT_ENTITY_TYPES: tuple[str, ...] = (
    "Person", "Organization", "Location", "Product", "Event", "Date",
    "Work", "Concept", "Resource", "Category", "Operation",
)

# 保存语义固定文案（B5 端点 3 hint＝服务端返回，页面照抄）。
SAVE_HINT = "已保存——设置在下次入库时生效。"

# 自定义指令出厂预填（B5 合同常量表「演示预填值」——去「自定义指令：」前缀）。
# G-03 增补实体名规范句（实体碎片治理第一刀——确定性归一在 gate 落点兜底）。
DEFAULT_CUSTOM_INSTRUCTIONS = (
    "关系必须原文有依据；拿不准宁可跳过，不许创造新类型。"
    "实体名用原文最规范的完整写法：井号不含空格（W-11井），平台/油田用全称，"
    "同一实体跨片段保持同名；纯数字与深度不是实体。"
)

# few-shot 出厂 5 例（G-03——例句逐字取自拟造评测语料，三元组经人工核对）。
# FX-11：三元组侧一律本体声明方向（与严格闸终点组对齐，过闸自检测试钉死防再
# 漂——tests/…/test_graph_domain_unit.py::test_factory_fewshot_triples_all_pass_gate）；
# 例 1 兼任 B2-01 别名规范名演示（例句别名长形「CEP-C 生产平台」→ 三元组规范名
# 「CEP-C平台」）；例 2 兼任「文本→声明方向归一」演示（受效动词挂受效油井侧，
# 声明方向＝注水井—受效→油井，出处 eval/drafts-q4/reports/渤中34-8油田一季度
# 注采调整与生产运行分析.txt:105；例 1 出处 eval/reports/A-W11井完井工程报告.txt:15）。
DEFAULT_FEWSHOT_EXAMPLES = [
    ("W-11 井位于渤中 34-5 油田三号构造高部位，CEP-C 生产平台西侧井槽 8 号位。",
     "CEP-C平台|承载|W-11井"),
    ("Y-24 井 I 层强吸水对应的受效油井 Y-21、Y-22 两口一季度含水上升加快",
     "Y-24井|受效|Y-21井"),
    ("三开射孔前对 2405～2418 米井段实施 TCP 射孔，三段合计 28.0 米",
     "W-11井|射孔|2405～2418米井筒段"),
    ("7″ 精密冲缝筛管下入 2405～2412 米", "精密冲缝筛管|下入|W-11井井筒"),
    ("永久式封隔器坐封深度 1482.6 米，液压坐封，验封合格", "永久式封隔器|坐封|W-11井井筒"),
]

# 边唯一键（B5 合同冻结：key = from|rel|to）。
EDGE_KEY_SEP = "|"


def edge_key(from_: str, rel: str, to: str) -> str:
    """边唯一键（B5 合同冻结 `from|rel|to`——页面 edgeKey 同构）。"""
    return f"{from_}{EDGE_KEY_SEP}{rel}{EDGE_KEY_SEP}{to}"


# ---------- 错误族（映射归 api/errors.py；00 §3 统一错误包） ----------


class GraphNotFoundError(Exception):
    """库不存在（B5 错误码草案 404——端点 1/2/3/4 同）。"""


class GraphParamError(Exception):
    """入参形状非法（B5 错误码草案 400：entity_types 空/relation_tags 缺 rel
    或重复/缺段/形状非法）。"""

    def __init__(self, message: str, *, code: str = "graph_param_invalid") -> None:
        self.code = code
        super().__init__(message)


class GraphOntologyMismatchError(GraphParamError):
    """对号强校不过（B5 错误码草案 400 带对号明细——逐项未收录词条＋最接近
    台账词条；P1-01 导出物接线后拒存）。"""

    def __init__(self, mismatches: list[dict[str, str]]) -> None:
        self.mismatches = mismatches
        names = "、".join(m["value"] for m in mismatches)
        super().__init__(
            f"对号强校不过——以下类型/标签未收录进本体对号表，对不上拒存：{names}",
            code="graph_ontology_mismatch",
        )


class GraphConflictError(Exception):
    """报告级防重入冲突（B5 端点 6「同报告防重入 409」——E3/E4：该报告任何
    图谱支路在跑〔入库触发或手动重抽〕，新图谱支路受理一律拒；**独立异常类
    不继承 GraphParamError**——409 冲突不是 400 参数错误的子形态，Kb/Faq/
    Retrieval Conflict 先例同形；api 层映射归 errors.py）。

    message 携带两态文案（「入库支路在跑」/「重抽在跑」——登记来源可辨）；
    code 恒 graph_extract_running。
    """

    def __init__(self, message: str, *, code: str = "graph_extract_running") -> None:
        self.code = code
        super().__init__(message)


# ---------- ExtractConfig（F40 四段——按库待生效配置，B1 库配置同族语义） ----------


@dataclass(frozen=True, slots=True)
class RelationTag:
    """关系标签行（rel＋示例＋说明——desc＝抽取对号的人话解释，随配置整存整取）。"""

    rel: str
    example: str = ""
    desc: str = ""


@dataclass(frozen=True, slots=True)
class FewShotPair:
    """few-shot 示例对（左「报告原句」右「应抽出三元组」——B5 出入对账 9
    拆出为独立段；DTO 增列挂差异登记，合同 relation_tags[].example 不动）。"""

    sentence: str
    triple: str

    def as_dict(self) -> dict[str, str]:
        return {"sentence": self.sentence, "triple": self.triple}


@dataclass(frozen=True, slots=True)
class ExtractConfig:
    """抽取设置四段（实体类型清单＋关系 tags＋few-shot 示例＋自定义指令）。"""

    entity_types: list[str]
    relation_tags: list[RelationTag]
    custom_instructions: str
    few_shot_examples: list[FewShotPair] = field(default_factory=list)

    def as_snapshot(self) -> dict[str, Any]:
        """定型快照形状（B5 端点 3 注记：＝DTO 减 lib_id/saved_at/saved_by；
        随 B1 confirm 时刻入 kb_ingest_task.extract_snapshot）。"""
        return {
            "entity_types": list(self.entity_types),
            "relation_tags": [
                {"rel": t.rel, "example": t.example, "desc": t.desc}
                for t in self.relation_tags
            ],
            "few_shot_examples": [p.as_dict() for p in self.few_shot_examples],
            "custom_instructions": self.custom_instructions,
        }


def config_from_payload(data: dict[str, Any]) -> ExtractConfig:
    """PUT body → ExtractConfig（形状校验：缺段/空清单/缺 rel/重复 rel → 400）。"""
    missing = [k for k in ("entity_types", "relation_tags", "custom_instructions") if k not in data]
    if missing:
        raise GraphParamError(f"抽取设置缺段：{missing}（四段合同——F40）")
    entity_types = data["entity_types"]
    relation_tags = data["relation_tags"]
    few_shot = data.get("few_shot_examples", [])
    if not isinstance(entity_types, list) or not entity_types:
        raise GraphParamError("entity_types 空数组（合同校验清单：400）")
    if not isinstance(relation_tags, list):
        raise GraphParamError("relation_tags 形状非法（需要数组）")
    if not isinstance(few_shot, list):
        raise GraphParamError("few_shot_examples 形状非法（需要数组）")
    tags: list[RelationTag] = []
    seen: set[str] = set()
    for row in relation_tags:
        if not isinstance(row, dict) or not str(row.get("rel", "")).strip():
            raise GraphParamError("relation_tags 缺 rel（合同校验清单：400）")
        rel = str(row["rel"]).strip()
        if rel in seen:
            raise GraphParamError(f"relation_tags 重复：{rel}（合同校验清单：400）")
        seen.add(rel)
        tags.append(
            RelationTag(
                rel=rel,
                example=str(row.get("example", "") or ""),
                desc=str(row.get("desc", "") or ""),
            )
        )
    pairs: list[FewShotPair] = []
    for row in few_shot:
        if not isinstance(row, dict):
            raise GraphParamError("few_shot_examples 行形状非法（需要 {sentence, triple}）")
        pairs.append(
            FewShotPair(
                sentence=str(row.get("sentence", "") or ""),
                triple=str(row.get("triple", "") or ""),
            )
        )
    return ExtractConfig(
        entity_types=[str(t).strip() for t in entity_types if str(t).strip()],
        relation_tags=tags,
        custom_instructions=str(data["custom_instructions"] or ""),
        few_shot_examples=pairs,
    )


# ---------- 对号强校（B5 端点 3 强校两态——P1-01 导出物接线） ----------


def default_extract_config(
    entity_rows: list[dict[str, Any]],
    relation_rows: list[dict[str, Any]],
) -> ExtractConfig:
    """出厂默认抽取配置（P1-01 本体对号表投影——挂差异登记）。

    合同 F40 出厂默认＝11 类通用实体（F40_DEFAULT_ENTITY_TYPES 留档）；本仓
    落**本体对号表投影**（entity_types.json/relation_types.json 的 P1-01 导出
    物）：①对号强校自洽——默认值原样保存即过强校（F40 通用类不在本体对号表，
    保存必拒）；②「本体消费从第一天可用」（B5 开放问题 7 裁决原文）——F55 A
    建图段生产形态。custom_instructions＝合同演示预填值常量。
    """
    return ExtractConfig(
        entity_types=[str(r["name"]) for r in entity_rows],
        relation_tags=[
            RelationTag(
                rel=str(r["name"]),
                example="",
                desc=str(r.get("note", "") or ""),
            )
            for r in relation_rows
        ],
        custom_instructions=DEFAULT_CUSTOM_INSTRUCTIONS,
        few_shot_examples=[
            FewShotPair(sentence=s, triple=t) for s, t in DEFAULT_FEWSHOT_EXAMPLES
        ],
    )


def config_from_snapshot(data: dict[str, Any]) -> ExtractConfig:
    """定型快照（extract_snapshot/kb_extract_config 行投影）→ ExtractConfig。

    宽容投影：存量行缺 few_shot_examples 键容错（99 DDL 无该列前的历史行）。
    """
    return ExtractConfig(
        entity_types=[str(t) for t in data.get("entity_types", [])],
        relation_tags=[
            RelationTag(
                rel=str(r.get("rel", "") or ""),
                example=str(r.get("example", "") or ""),
                desc=str(r.get("desc", "") or ""),
            )
            for r in data.get("relation_tags", [])
        ],
        custom_instructions=str(data.get("custom_instructions", "") or ""),
        few_shot_examples=[
            FewShotPair(
                sentence=str(p.get("sentence", "") or ""),
                triple=str(p.get("triple", "") or ""),
            )
            for p in data.get("few_shot_examples", [])
        ],
    )


def nearest_word(word: str, catalog: list[str]) -> str:
    """最接近的台账词条（400 对号明细第三列——二字串相似度取最高；空目录
    返回空串，非空目录恒有返回——零相似也取最高项）。"""
    best, best_ratio = "", -1.0
    for cand in catalog:
        ratio = SequenceMatcher(None, word, cand).ratio()
        if ratio > best_ratio:
            best, best_ratio = cand, ratio
    return best


def ontology_check(
    config: ExtractConfig,
    *,
    entity_catalog: list[str],
    relation_catalog: list[str],
) -> list[dict[str, str]]:
    """对号强校：实体类型/关系标签对 P1-01 导出物逐一对号（F55 A 接入点）。

    返回对号明细（空＝全对号）：[{kind, value, nearest}]——kind ∈
    entity_type | relation_tag；未收录关系族不因台账缺族放行自创标签
    （对不上就是拒存，补全走治理批——B5 端点 3 注记原文）。
    """
    mismatches: list[dict[str, str]] = []
    entity_set = set(entity_catalog)
    relation_set = set(relation_catalog)
    for name in config.entity_types:
        if name not in entity_set:
            mismatches.append({
                "kind": "entity_type", "value": name,
                "nearest": nearest_word(name, entity_catalog),
            })
    for tag in config.relation_tags:
        if tag.rel not in relation_set:
            mismatches.append({
                "kind": "relation_tag", "value": tag.rel,
                "nearest": nearest_word(tag.rel, relation_catalog),
            })
    return mismatches


# ---------- 三道闸（铁律合同化——类型闸/依据闸/弃权闸） ----------


@dataclass(frozen=True, slots=True)
class TripleCandidate:
    """LLM 抽取候选三元组（解析自模型输出 JSON 行）。"""

    from_: str
    from_type: str
    rel: str
    to: str
    to_type: str
    evidence: str
    note: str | None
    uncertain: bool


@dataclass(frozen=True, slots=True)
class GatedEdge:
    """过闸边（写 Neo4j：过闸标记＝能进本列表即过闸——端点 1 只含过闸边）。"""

    from_: str
    from_type: str
    rel: str
    to: str
    to_type: str
    evidence: str
    note: str | None
    chunk_id: str
    report_id: str

    @property
    def key(self) -> str:
        return edge_key(self.from_, self.rel, self.to)

    @property
    def label(self) -> str:
        return f"{self.from_} —{self.rel}→ {self.to}"


@dataclass(frozen=True, slots=True)
class BlockedEdgeDraft:
    """被拦边（写图存储 BlockedEdge 对账镜像——拦下的边不进图）。"""

    from_: str
    from_type: str
    rel: str
    to: str
    to_type: str
    reason_code: str
    reason: str
    chunk_id: str | None
    report_id: str

    @property
    def key(self) -> str:
        return edge_key(self.from_, self.rel, self.to)


def _squash(text: str) -> str:
    """依据闸比对归一：剥全部空白（切段回带/换行差异不影响依据判定）。"""
    return re.sub(r"\s+", "", text)


def _normalize_entity(name: str) -> str:
    """实体名确定性归一（G-03 第一刀——同实体空格/全半角变体落点合并）。

    - NFKC 全半角折叠＋去首尾空白＋连续空白压一；
    - 「X 井」→「X井」（井号前空格去除——B5 截图双链直接成因）。
    语义级消歧（全简称别名收敛）由其后的独立步 _normalize_entity_alias
    承载（B2-01——Owner 确认映射表驱动的第二刀），本函数不碰、无损语义零变。
    """
    import unicodedata

    text = unicodedata.normalize("NFKC", str(name or "")).strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+井$", "井", text)
    return text


# 实体别名映射（B2-01——Owner 2026-10-07 裁决：规范名＝「CEP-C平台」（短形），
# 「CEP-C 生产平台」等长形登记为别名；别名→规范名单向归一，映射外名字零变化
# 不猜测。承载位＝ontology/petro/glossary-model.yaml terms[].aliases
# （本常量为其运行期投影，漂移由测试对账钉死：
# tests/domains/derivatives/test_graph_domain_unit.py 别名漂移对账）。
# 键须为第一刀归一后的形态（内部连续空白压一后的写法）。
# 批量二（B2-02，Owner 2026-10-07 委托「按建议落」——确认单 §2.2 建议列五对：
# GLS-PETRO-013~017——CEP-D 两修饰形/CEP-E 中心平台/油田名空格形×2/封隔器省式形）。
ENTITY_NAME_ALIASES: dict[str, str] = {
    # 批量一（GLS-PETRO-012）
    "CEP-C 生产平台": "CEP-C平台",
    "CEP-C 平台": "CEP-C平台",  # 句内空格形（B2-01 确认单变体——同裁决口径收敛）
    # 批量二（GLS-PETRO-013~017）
    "CEP-D 生产平台": "CEP-D平台",
    "CEP-D 井口平台": "CEP-D平台",
    "中心平台 CEP-E": "CEP-E平台",
    "渤中 34-5 油田": "渤中34-5油田",
    "渤中 34-8 油田": "渤中34-8油田",
    "永久封隔器": "永久式封隔器",
}


def _normalize_entity_alias(name: str) -> str:
    """实体别名归一（G-03 第二刀，B2-01——别名→规范名单向收敛）。

    只按 Owner 确认的映射表（ENTITY_NAME_ALIASES，承载位 glossary
    GLS-PETRO-012~017）精确匹配收敛；映射外的名字原样返回（匹配失败不猜测——
    新变体落规范名确认单呈 Owner，不自动改名）。跟在第一刀 _normalize_entity
    之后、建节点/立边之前。
    """
    return ENTITY_NAME_ALIASES.get(name, name)


# ---------- 三元组合法集（B3-01——真源唯一＝本体导出物，闸内零发明） ----------


def build_legal_triples(
    entity_rows: list[dict[str, Any]],
    relation_rows: list[dict[str, Any]],
) -> dict[str, frozenset[tuple[str, str]]]:
    """本体导出物两册 → 关系标签 × 合法 (from_type, to_type) 名对集合。

    AGG id ↔ 实体类型名映射口径（B3-01 票内定案）：entity_types.json 行的
    ref 字段（＝M1 聚合 id，如 AGG-PETRO-007）↔ name 字段（＝抽取类型词表
    名——§5 短名，如 设备；非 ontology_name 聚合全名）；relation_types.json
    行的 endpoint_groups／from_type/to_type 承载 AGG id，经此映射换算为类型
    名对。映射缺失＝两册导出物漂移（部署错误）——显式报错禁静默
    （load_ontology_export 同款纪律）。
    """
    name_of: dict[str, str] = {}
    for row in entity_rows:
        ref, name = str(row.get("ref", "")), str(row.get("name", ""))
        if not ref or not name:
            raise ValueError(f"entity_types 导出物行缺 ref/name：{row}")
        name_of[ref] = name
    legal: dict[str, set[tuple[str, str]]] = {}
    for row in relation_rows:
        rel = str(row.get("name", ""))
        groups = row.get("endpoint_groups")
        if not groups:
            f, t = row.get("from_type"), row.get("to_type")
            groups = [{"from_type": f, "to_type": t}] if f and t else []
        if not rel or not groups:
            raise ValueError(f"relation_types 导出物行缺 name/终点组：{row}")
        pairs = legal.setdefault(rel, set())
        for group in groups:
            f, t = str(group.get("from_type", "")), str(group.get("to_type", ""))
            if f not in name_of or t not in name_of:
                raise ValueError(
                    f"关系「{rel}」终点 AGG id 无法映射到实体类型名：{f}/{t}"
                    "——entity_types.json 与 relation_types.json 漂移"
                )
            pairs.add((name_of[f], name_of[t]))
    return {rel: frozenset(pairs) for rel, pairs in legal.items()}


def ontology_legal_triples() -> dict[str, frozenset[tuple[str, str]]]:
    """从本体导出物装载三元组合法集（gate_triples 缺省真源——闸内零发明）。

    读 config/entity_types.json＋relation_types.json（P1-01 派生物，进 git；
    文件缺失/损坏显式报错）。现读不缓存——导出物重导出后即生效，零进程内
    陈旧态（每 chunk 两次小 JSON 读，相对 LLM 调用成本可忽略）。
    """
    from app.infra.config import load_ontology_export

    return build_legal_triples(
        load_ontology_export("entity_types"),
        load_ontology_export("relation_types"),
    )


def gate_triples(
    candidates: list[TripleCandidate],
    config: ExtractConfig,
    *,
    legal_triples: Mapping[str, AbstractSet[tuple[str, str]]] | None = None,
    chunk_text: str,
    chunk_id: str,
    report_id: str,
) -> tuple[list[GatedEdge], list[BlockedEdgeDraft]]:
    """三道闸（铁律合同常量——顺序照铁律分解：类型闸→依据闸→弃权闸）。

    - 类型闸（B3-01 起三元组严格匹配）：from/to 类型不在 entity_types、rel
      不在启用 relation_tags、或 (from_type, rel, to_type) 未命中该 rel 在
      本体导出物声明的终点组 → type_mismatch（不自创类型/标签，不自配对配；
      合法集真源唯一＝relation_types.json 声明终点组经 entity_types.json
      映射换算——legal_triples 缺省时闸内现读本导出物装载，零发明）；
    - 依据闸：evidence 空或归一后不在 chunk 原文 → no_evidence
      （原文里没有依据的关系不立边——evidence 必须是 chunk 原句逐字摘录）；
    - 弃权闸：LLM 自报 uncertain → uncertain（拿不准宁可跳过，不胡编）；
    - 形状残缺候选（缺字段）不属抽取尝试——跳过不记（LLM 噪声行）。
    """
    entity_set = set(config.entity_types)
    rel_set = {t.rel for t in config.relation_tags}
    legal = (
        ontology_legal_triples()
        if legal_triples is None
        else {rel: frozenset(pairs) for rel, pairs in legal_triples.items()}
    )
    chunk_norm = _squash(chunk_text)
    passed: list[GatedEdge] = []
    blocked: list[BlockedEdgeDraft] = []

    def _reject(c: TripleCandidate, code: str) -> None:
        blocked.append(
            BlockedEdgeDraft(
                from_=c.from_, from_type=c.from_type, rel=c.rel,
                to=c.to, to_type=c.to_type,
                reason_code=code, reason=REASON_TEXT[code],
                chunk_id=chunk_id, report_id=report_id,
            )
        )

    for c in candidates:
        if not (c.from_ and c.to and c.rel and c.from_type and c.to_type):
            continue  # 形状残缺——不属抽取尝试，跳过不记
        # G-03 实体名归一（确定性第一刀）：空格/全半角/「X 井」变体落点合并——
        # 此处只做无损规整。紧随其后的别名归一（第二刀，B2-01）：Owner 确认
        # 映射表的别名→规范名单向收敛，映射外名字零变化——两刀独立不混。
        c = _replace(c, from_=_normalize_entity(c.from_), to=_normalize_entity(c.to))
        c = _replace(c, from_=_normalize_entity(c.from_), to=_normalize_entity(c.to))
        c = _replace(
            c,
            from_=_normalize_entity_alias(c.from_),
            to=_normalize_entity_alias(c.to),
        )
        if (
            c.from_type not in entity_set
            or c.to_type not in entity_set
            or c.rel not in rel_set
            or (c.from_type, c.to_type) not in legal.get(c.rel, frozenset())
        ):
            _reject(c, REASON_TYPE_MISMATCH)
        elif not c.evidence or _squash(c.evidence) not in chunk_norm:
            _reject(c, REASON_NO_EVIDENCE)
        elif c.uncertain:
            _reject(c, REASON_UNCERTAIN)
        else:
            passed.append(
                GatedEdge(
                    from_=c.from_, from_type=c.from_type, rel=c.rel,
                    to=c.to, to_type=c.to_type, evidence=c.evidence,
                    note=c.note, chunk_id=chunk_id, report_id=report_id,
                )
            )
    return passed, blocked


# ---------- 抽取提示词（few-shot 配置进 prompt——B5 端点 3 快照消费） ----------

EXTRACT_PROMPT_TEMPLATE = """你是油田知识平台的关系抽取器。从下面的报告切片里抽出实体关系三元组。

铁律（三条都守）：
1. 类型闸：实体 from_type/to_type 只能取「实体类型清单」内的类型，
   关系 rel 只能取「关系标签清单」内的标签——清单之外的类型/标签一律不许自创；
2. 依据闸：每条三元组必须带 evidence 字段＝切片原文里**逐字摘录**的支持原句
   （不许改写、不许拼装）——原文里没有依据的关系不立边；
3. 弃权闸：拿不准的三元组把 uncertain 设为 true（宁可跳过，不胡编）。

实体类型清单：{entity_types}
关系标签清单：{rel_lines}
实体别名表（同一实体的其他写法 → 规范名；实体名抽到别名写法时一律写规范名，
别名两形态均须识别——evidence 仍按原文逐字摘录，不改写）：
{alias_lines}
few-shot 示例（报告原句 → 应抽出三元组）：
{few_shot}
自定义指令：{instructions}

输出要求：只输出一个 JSON 数组，不要输出任何其他文字。每个元素形如：
{{"from": "实体名", "from_type": "类型", "rel": "关系标签",
  "to": "实体名", "to_type": "类型", "evidence": "原文支持句",
  "note": "可选溯源小注（无则省略）", "uncertain": false}}
切片里没有可抽的关系就输出空数组 []。

报告切片（{section}）：
{chunk}
"""


# ---------- 报告族信号与按族携带（B1-01 scenario 族标注的消费面——B1-02） ----------

# 报告标题关键词 → 文档族（B1-01 值集 completion/monthly/dynamic）。
# 规则序即优先序（首条命中即返回）——阶段A六篇语料标题无重叠命中，重叠标题
# 未见语料（登记 B1-02 收尾报告疑点）；分族依据＝阶段A全语料动词盘点报告的
# 六篇语料分族（完井工程报告/躺井治理与检泵作业月报/注水调整（注采调整）与
# 生产运行分析）。
REPORT_FAMILY_RULES: tuple[tuple[str, str], ...] = (
    ("完井", "completion"),
    ("月报", "monthly"),
    ("注水调整", "dynamic"),
    ("注采调整", "dynamic"),
    ("生产运行分析", "dynamic"),
)


def detect_report_family(title: str) -> str | None:
    """报告标题 → 文档族（无族信号返回 None——调用方按全量携带兜底）。

    报告族信号来源定案（B1-02 票内核对）：kb 报告行 `doc` 字段
    （kb ReportDetail.doc——入库时取自上传文件名 stem，语料六篇标题即含
    族词）。生产接线位＝derivatives/service.py 图谱支路 chunk 循环处
    （detail 已在作用域，一行接线：report_family=d.detect_report_family(
    detail.doc)）——service.py 不在 B1-02 边界红线许可清单内，接线登记
    待办（B1-02 收尾报告偏差节，L0 不动手）。
    """
    for needle, family in REPORT_FAMILY_RULES:
        if needle in (title or ""):
            return family
    return None


def relation_names_for_family(family: str) -> set[str]:
    """本体导出物 group → 指定文档族的关系标签名集（真源唯一＝relation_types.json）。

    group 为 B1-01 scenario 族标注的导出透传（completion/monthly/dynamic
    可空多值——跨族标签如 作用于/隶属/承载 三值全含，按族过滤时自然随行
    ＝票面「对应组（＋跨族组）」口径）。导出物全部行均无 group（旧产物
    部署态）→ 返回空集，调用方兜底全量携带（防旧产物把提示词收窄成零标签
    ——兜底不收窄）；个别行无 group（本体未标注）→ 该标签不属任何族，
    按族过滤时自然排除。
    """
    from app.infra.config import load_ontology_export

    names: set[str] = set()
    for row in load_ontology_export("relation_types"):
        group = row.get("group")
        if group and family in group:
            names.add(str(row.get("name", "")))
    return names


def build_extract_prompt(
    config: ExtractConfig,
    *,
    section: str,
    chunk_text: str,
    report_family: str | None = None,
) -> str:
    """组装抽取提示词（ExtractConfig 四段全进 prompt——B6 出口由服务编排）。

    B2-01 增实体别名表段（ENTITY_NAME_ALIASES 全量进 prompt——抽取时别名
    两形态均可识别，模型直接落规范名；闸内别名归一步兜底收敛）。
    B1-02 增按族携带（report_family 给定时，关系标签清单只带该族标签——
    组=本体导出物 group 含该族的行 ∩ 当前配置 relation_tags；无族信号
    （report_family=None）或导出物无族标注（旧产物）→ 全量携带＝现行为
    不变，兜底不收窄）。
    """
    rel_tags = config.relation_tags
    if report_family is not None:
        family_names = relation_names_for_family(report_family)
        if family_names:  # 空集＝族标注不可判（旧产物）——兜底全量不收窄
            rel_tags = [t for t in rel_tags if t.rel in family_names]
    rel_lines = "\n".join(
        f"- {t.rel}：{t.desc}（示例：{t.example}）" if t.example or t.desc
        else f"- {t.rel}"
        for t in rel_tags
    )
    alias_lines = "\n".join(
        f"- {alias} → {canonical}" for alias, canonical in ENTITY_NAME_ALIASES.items()
    ) or "（无——未登记实体别名）"
    few_shot = "\n".join(
        f"- {p.sentence} → {p.triple}"
        for p in config.few_shot_examples
    ) or "（无）"
    return EXTRACT_PROMPT_TEMPLATE.format(
        entity_types="、".join(config.entity_types),
        rel_lines=rel_lines or "（无——未配置关系标签则抽不出任何过闸边）",
        alias_lines=alias_lines,
        few_shot=few_shot,
        instructions=config.custom_instructions or "（无）",
        section=section,
        chunk=chunk_text,
    )


_JSON_ARRAY_RE = re.compile(r"\[[^\[\]]*\]", re.DOTALL)


def parse_triples(raw: str) -> list[TripleCandidate]:
    """宽容解析 LLM 输出（首 patched：剥 markdown 围栏→取首个 JSON 数组→逐行投影）。

    解析失败/空输出 → 空列表（本 chunk 无抽取尝试——弃权语义的实现替代面）；
    字段缺失行投影为残缺候选，由 gate_triples 跳过。
    """
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", text).strip()
    match = _JSON_ARRAY_RE.search(text)
    if match is None:
        return []
    try:
        rows = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    if not isinstance(rows, list):
        return []
    out: list[TripleCandidate] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        out.append(
            TripleCandidate(
                from_=str(row.get("from", "") or "").strip(),
                from_type=str(row.get("from_type", "") or "").strip(),
                rel=str(row.get("rel", "") or "").strip(),
                to=str(row.get("to", "") or "").strip(),
                to_type=str(row.get("to_type", "") or "").strip(),
                evidence=str(row.get("evidence", "") or "").strip(),
                note=(str(row["note"]).strip() or None) if row.get("note") else None,
                uncertain=bool(row.get("uncertain", False)),
            )
        )
    return out


# ---------- 起草示例（LLM 起草——三源辅助③；真实实现走 gateway.complete） ----------

DRAFT_PROMPT_TEMPLATE = """你是油田知识平台的抽取配置助手。
请为关系标签「{rel}」起草一条 few-shot 示例对（报告原句 → 应抽出的三元组），
用于指导后续报告的关系抽取。

要求：报告原句要像油田报告里的自然句子（井—隶属→区块、平台—承载→井、
注水井—受效→油井、措施—作用于→井等业务语境）；
三元组用「起点 —关系→ 终点」形态。
只输出两行，第一行是报告原句，第二行是三元组，不要输出其他任何文字。
"""


def parse_draft(raw: str) -> tuple[str, str]:
    """宽容解析起草输出（两行——原句/三元组；解析失败抛 GraphParamError）。"""
    lines = [
        ln.strip().lstrip("-• ").strip()
        for ln in (raw or "").strip().splitlines() if ln.strip()
    ]
    if len(lines) < 2 or not lines[0] or not lines[1]:
        raise GraphParamError("起草输出无法解析——请重试或手填示例")
    return lines[0], lines[1]


# ---------- DTO（读面投影——api 层直接消费） ----------


@dataclass(frozen=True, slots=True)
class GraphNodeView:
    """图节点（端点 1：label＝完整展示名、short＝图内短名、sub＝节点下注记）。"""

    id: str
    label: str
    type: str
    short: str
    sub: str


@dataclass(frozen=True, slots=True)
class GraphEdgeView:
    """图边（端点 1：key 冻结 `from|rel|to`；note 无注记 null；evidence_chunk_id/
    report_id 为溯源增列——挂差异登记，合同字段全保留）。"""

    key: str
    from_: str
    rel: str
    to: str
    note: str | None
    evidence_chunk_id: str
    report_id: str


@dataclass(frozen=True, slots=True)
class LegendItem:
    """图例计数行（服务端按节点聚合——与 nodes 必然一致）。"""

    type: str
    count: int


@dataclass(frozen=True, slots=True)
class GraphNet:
    """整图（端点 1：整图一次给——高亮/隐显/邻接过滤全为前端本地计算）。"""

    lib_id: str
    lib_name: str
    nodes: list[GraphNodeView]
    edges: list[GraphEdgeView]
    legend: list[LegendItem]
    stats: dict[str, int]


@dataclass(frozen=True, slots=True)
class ExtractConfigView:
    """抽取设置读面（端点 2：返回当前库配置值＋轻量审计两字段）。"""

    lib_id: str
    lib_name: str
    config: ExtractConfig
    saved_at: str | None
    saved_by: str | None


@dataclass(frozen=True, slots=True)
class ExtractConfigSaveReceipt:
    """保存回执（端点 3：hint＝固定文案服务端返回）。"""

    lib_id: str
    saved_at: str
    saved_by: str
    hint: str


@dataclass(frozen=True, slots=True)
class BlockedEdgeView:
    """被拦边行（端点 4：被拦边＋拦下原因＋所属报告——治理复盘/E3 消费）。"""

    key: str
    from_: str
    from_type: str
    rel: str
    to: str
    to_type: str
    reason_code: str
    reason: str
    report_id: str
    report_title: str
    chunk_id: str | None
    blocked_at: str


@dataclass(frozen=True, slots=True)
class BlockedEdgesPage:
    """被拦边清单（端点 4：纯只读——无任何写端点）。"""

    lib_id: str
    lib_name: str
    blocked_edges: list[BlockedEdgeView]
    stats: dict[str, int]


@dataclass(frozen=True, slots=True)
class DraftedExample:
    """起草示例对（LLM 起草——人核对后保存）。"""

    sentence: str
    triple: str
