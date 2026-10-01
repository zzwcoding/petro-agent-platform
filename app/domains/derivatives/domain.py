"""domains.derivatives.domain —— 派生物域（wiki 支路）语义（厚：B4 合同语义在此闭环）。

合同锚（真源在 teach-petro-agent/specs/api/，只引路径不复制正文）：
- B4-报告百科.md v0.3：四端点（目录/全文 ?version=N/版本列表/回滚）、
  「与 B1 的生产/消费边界」（生成方＝B1 管线 wiki 支路；重建触发＝入库、
  重跑、片段修正；重写≠检索；1:1 报告；开关关→不生成；截断防护＝半页
  不落库；slug 稳定性＝id 承载）、「论断回链」节（claims[] fail-closed）、
  「台账挂接」节（glossary_terms[] 台账无账不挂、生成时固化不回溯）、
  wiki 模板语义（模板＝提示词约束、产出自由 markdown、零固定节 schema）、
  版本三件套、回滚语义（追加新版本、指针前进、防呆 409）、来源四态、
  错误码草案、行为规则汇总 12 条。
- B1-报告库.md v0.3 端点 4 注记：修正定型→FragmentRevised 事件→重铸队列→
  版本+1 来源「自动重建」；重铸失败不阻塞修正（记活动流，可手动重跑）。
- PRD F50：chunk 拼回全文（重叠去重＋图片回读）→LLM 重写 Markdown 页；
  32K 截断（WeKnora maxContentForWiki=32768）＋票 104 截断防护（最多续写
  3 轮、未完放弃本次写入不落半页）；F51 slug 稳定性/单字不挂链；
  F52 版本治理（来源四态/回滚任意版）。
- 98-模块划分与分层.md §3.5 derivatives 卡＋§8 事件表（IngestCompleted/
  FragmentRevised 订阅）；B9 边界（kb 禁直调 derivatives；derivatives→kb
  仅 record_activity＋报告读面＋wiki 版号投影回写）。
- 99-数据库与连接层设计.md §2.7：wiki_page/wiki_page_version 逐字段
  （source CHECK 四态冻结值照抄；版本 append-only＋当前指针）。

B1：本文件不 import fastapi/starlette/DB/LLM——拼回去重、截断纪律、
claims 锚校验、台账 linkify、状态派生、横幅组装都是纯语义。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# ---------- 合同常量（B4/99 照抄，不可改） ----------

# 来源四态（F52 ① 值域冻结照抄——99 §2.7 CHECK 同值；「首次生成」是 v1 的
# desc 文案不是来源态）。
WIKI_SOURCES: tuple[str, ...] = ("自动重建", "智能体", "人工", "回滚")
SOURCE_AUTO = "自动重建"
SOURCE_ROLLBACK = "回滚"

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

# 操作人口径（B4 操作人列：自动重建版＝「系统（入库管线）」——合同值照抄）。
OPERATOR_SYSTEM = "系统（入库管线）"
# 回滚版 task_no＝null（B4 经由单号列口径：回滚无经由单号，页面记 —）。

# 版本 desc 文案（B4 版本序列/回滚响应模板同族）。
DESC_FIRST = "首次生成（报告入库自动建页）"
DESC_REINGEST = "报告重新解析后自动重建"
DESC_RECAST = "片段修正后自动重建"
ROLLBACK_DESC_TEMPLATE = "回滚：恢复到 v{target}"

# 回滚横幅模板（B4 合同常量表——被恢复摘要由服务端填）。
ROLLBACK_BANNER_TEMPLATE = (
    "已回滚：当前版 = v{new_version}（内容恢复自 v{target_version}），"
    "{summary}。注意：回滚本身也记成一次新提交（可再滚回）。"
)
ROLLBACK_BANNER_SUMMARY = "正文恢复为目标版快照"

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
    """百科页/版本不存在（B4 错误码草案 404——含 wiki 开关关未生成、直调未知 id）。"""


class WikiParamError(Exception):
    """入参形状非法（B4 错误码草案 400：target_version 缺失/等于当前版）。"""

    def __init__(self, message: str, *, code: str = "wiki_param_invalid") -> None:
        self.code = code
        super().__init__(message)


class WikiConflictError(Exception):
    """回滚防呆 409（目标版内容与当前版逐字相同——兜底横幅＝合同常量）。"""

    def __init__(self, message: str, *, code: str = "wiki_conflict") -> None:
        self.code = code
        super().__init__(message)


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


def rollback_banner(new_version: int, target_version: int) -> str:
    return ROLLBACK_BANNER_TEMPLATE.format(
        new_version=new_version,
        target_version=target_version,
        summary=ROLLBACK_BANNER_SUMMARY,
    )


# ---------- DTO（读面投影——api 层直接消费） ----------


@dataclass(frozen=True, slots=True)
class WikiPageListItem:
    """目录行（端点 1）。"""

    id: str
    title: str
    lib: str
    source_report_id: str
    source_report_doc: str
    current_version: int
    version_count: int
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
    """百科页全文（端点 2：元数据＋自由 markdown 正文＋claims＋glossary_terms）。"""

    id: str
    title: str
    lib: str
    slug: str
    digest: str | None
    source_report_id: str
    source_report_doc: str
    current_version: int
    version_count: int
    updated: str
    status: str
    generation_source: str
    operator: str | None
    related_objects: list[RelatedObjectView]
    content: str
    claims: list[dict[str, Any]]
    glossary_terms: list[dict[str, Any]]


@dataclass(frozen=True, slots=True)
class WikiVersionItem:
    """版本行（端点 3：来源四态/时间/操作人/经由单号/说明/当前版标）。"""

    v: int
    date: str
    source: str
    desc: str
    operator: str | None
    task_no: str | None
    current: bool


@dataclass(frozen=True, slots=True)
class RollbackReceipt:
    """回滚回执（端点 4：追加语义——new_version 为回滚来源新版本行）。"""

    page_id: str
    current_version: int
    new_version: WikiVersionItem
    status: str
    banner: str
