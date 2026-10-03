"""domains.kb.domain —— 知识管线域语义（厚：B1 合同语义在此闭环）。

合同锚（真源在 teach-petro-agent/specs/api/，只引路径不复制正文）：
- B1-报告库.md v0.3：15 端点、合同常量表（五步节点名/机器键、任务四态、
  四开关机器键、三切段方式、智能切段参数、两复选、业务模板四枚举）、
  入库任务生命周期（直传两拍/配置定型点/状态机/失败语义/跳过语义/重跑定型）、
  「入库路由（阶段 1 实施项）」专节、行为规则汇总 11 条、错误码草案。
- 00-系统级API.md §5（受理 200 同步特例/轮询/重入 409/stuck 巡检）、
  §5.3（节点四态 wait|process|finish|error；note 服务端组装、前端零拼装）、
  §7.1（预签名直传两拍）、§7.2（GET 直链小时级上限 7 天）、§4.5（筛选命名）。
- 98-模块划分与分层.md §3.4 kb 卡：公开接口/聚合/事件（IngestCompleted、
  FragmentRevised——本票只发布前者）/测试计划。
- 99-数据库与连接层设计.md §2.5 kb 九表（本票落 8 表；kb_issue_report 归
  B2/P1-04、kb_extract_config 归 derivatives/P1-05）＋向量列落位注记
  （ADR-0003 裁决 1：pgvector；维度 P1-11 回填＝embo-01 1536）。

B1：本文件不 import fastapi/starlette/DB/LLM——切段器、结构图（LLM 应答解析/
逐字校验/规则复检为纯语义，LLM 触达在 service 编排）、分词、向量语义件、
节点说明组装、模板配置档、路由建议解析都是纯语义；IO 归 store（PG/对象
存储）/service（编排）。
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

# ---------- 合同常量（B1 合同常量表照抄，不可改） ----------

# 五步节点机器键（本合同冻结）——顺序即五步序。
STEP_KEYS: tuple[str, ...] = ("parse", "chunk", "embed", "index", "enrich")
# 五步节点名（label＝页面 FLOW 合同值照抄）。
STEP_LABELS: dict[str, str] = {
    "parse": "解析（读出文字和图）",
    "chunk": "切段",
    "embed": "向量化",
    "index": "建索引",
    "enrich": "索引期加法（摘要＋问题）",
}
# stop_at 用的步名（端点 7 种子「切段」同族——五步短名）。
STEP_SHORT_NAMES: dict[str, str] = {
    "parse": "解析",
    "chunk": "切段",
    "embed": "向量化",
    "index": "建索引",
    "enrich": "索引期加法",
}
TASK_STATES: tuple[str, ...] = ("running", "done", "failed", "stuck")
SWITCH_KEYS: tuple[str, ...] = ("semantic", "keyword", "wiki", "graph")
MODES: tuple[str, ...] = ("smart", "fixed", "mixed")
SOURCE_VALUES: tuple[str, ...] = ("上传入库", "片段修正", "重跑定型")
BIZ_TEMPLATES: tuple[str, ...] = ("completion", "monthly", "dynamic", "blank")
TEMPLATE_LABELS: dict[str, str] = {
    "completion": "完井报告类",
    "monthly": "生产月报类",
    "dynamic": "动态分析类",
    "blank": "空白默认",
}
LIB_STATUSES: tuple[str, ...] = ("active", "disabled")
FRAGMENT_TYPES: tuple[str, ...] = ("原文块", "图片说明块", "图片文字块", "摘要块", "问题块")

# ---------- B2 切片管理（B2-答案出处.md v0.3 合同常量） ----------

# 质检复核队列状态机（99 §2.5 kb_issue_report CHECK 四态冻结——v0.3 Owner 拍板批）。
ISSUE_STATES: tuple[str, ...] = ("待质检复核", "已修正", "已驳回", "已销记")
# 队列在途态（端点 4 出列域——终态已修正/已销记默认不出列，state=all 亦只出两在途态）。
ISSUE_OPEN_STATES: tuple[str, ...] = ("待质检复核", "已驳回")
# 标记两态文案（合同常量表——服务端 hint 保证一致，B1 端点 13 hint 先例）。
MARK_HINT = "已标记 · 待质检复核——复核确认后由管理员修正片段并重建索引。"
MARK_BUTTON_TEXT = "标记问题片段"
# F62 活动流 action（B1 挂账收口批增列值域——开放问题 2 兑现）。
MARK_ACTIVITY_ACTION = "标记问题片段"
# 摘要块/问题块回捞说明行（端点 2 无父块的唯一例外——页面 ctx 原值照抄）。
SUMMARY_CONTEXT_NOTE = "全文档摘要 ×1，入库时自动生成。"
QUESTION_CONTEXT_NOTE = "每 20 段自动生成一批\"可能被问的问题\"块。"

# 智能切段参数（合同常量：一段 256–1024 字，相邻段重叠 10–20%）。
SMART_MIN_CHARS = 256
SMART_MAX_CHARS = 1024
SMART_OVERLAP_RATIO = 0.15  # 10–20% 带内取中
# fixed 档位（B1 开放问题 6：维持实施批定档——本仓先落 512 字占位，挂疑点清单）。
FIXED_CHUNK_CHARS = 512
# mixed（F30 父子分块）参数：父块上限（大段只入库不索引）。
MIXED_PARENT_MAX_CHARS = 2048
MIXED_CHILD_MAX_CHARS = 512
# F37/R24：每 20 段自动生成问题一批。
QUESTIONS_BATCH_SIZE = 20

# 节点四态（00 §5.3；C3/D1/B1 同形）。
NODE_WAIT = "wait"
NODE_PROCESS = "process"
NODE_FINISH = "finish"
NODE_ERROR = "error"

# 文案合同值（照抄页面/常量表——服务端组装，前端零拼装）。
PARSE_NOTE = (
    "读出正文和插图；报告原文原样存进文件库（桶：报告原文），一个字不动——"
    "以后任何引用都能翻回原文。"
)
EMBED_NOTE = "把每段换成一串\"语义坐标\"：意思相近的段坐标就相近——问句换个说法也能搜到。"
CHUNK_NOTE_TAIL = "三种切法的对照在「库管理」页签点\"配置\"现场切换。"
MODE_TEXT: dict[str, str] = {
    "smart": "智能切段——按章节和语义边界切，一段 256–1024 字，相邻段重叠 10–20%。",
    "fixed": "固定大小——每段等长，句子可能被拦腰斩断。",
    "mixed": "大小段配合——小段进索引负责被找到，大段入库负责被读懂。",
}
INDEX_NOTE_TEMPLATE = (
    "按{lib_name}的四开关写入索引：语义 {semantic} · 关键词 {keyword} · "
    "百科页 {wiki} · 关系图谱 {graph}。关掉的支路不跑、不产生抽取费用。"
)
SAVE_HINT = "已保存——开关在下次入库时生效，正在处理的报告不受影响。"
DUP_WARNING = "检测到疑似重复，仍要上传？"
FAILURE_TEMPLATE = "停在「{stop_at}」阶段：{reason}——可重试；仍失败请报修。"
STUCK_SWEEP_SECONDS = 20 * 60  # 卡住判定＝超时无进展（阈值结合实际框架定；20 分钟＝演示值量级）

# 桶显示名（页面步 1 文案照抄）与物理名（F5 reports——出入对账 8）。
BUCKET_DISPLAY = "报告原文"

# 片段修正重建（P1-02b）：chunk 步说明（不重切——人工修正后的片段保持）与
# rebuild hint（端点 4 rebuild.hint 合同文案）。
REBUILD_CHUNK_NOTE = "片段修正重建：正文不重切——保留人工修正后的片段；仅重嵌修正片段并重生问题块。"
REBUILD_HINT = "已保存——将重建检索索引。"

# 平台默认配置档（页面 DEFAULT_CONFIG：语义/关键词/百科开、图谱关、智能、两加法勾）。
DEFAULT_CONFIG: dict[str, Any] = {
    "semantic": True,
    "keyword": True,
    "wiki": True,
    "graph": False,
    "mode": "smart",
    "add_summary": True,
    "add_questions": True,
}
# 业务模板默认配置档（B1 端点 15：模板只定初始档、建后可调——建库批拍板）。
TEMPLATE_CONFIGS: dict[str, dict[str, Any]] = {
    "completion": {**DEFAULT_CONFIG, "graph": True},  # 四开关全开（含图谱）
    "monthly": dict(DEFAULT_CONFIG),  # 图谱关（省抽取费，需要时再开）
    "dynamic": dict(DEFAULT_CONFIG),
    "blank": dict(DEFAULT_CONFIG),  # 平台默认档
}


def chunk_note(mode: str) -> str:
    """步 2 说明（随切段方式组装——端点 8 服务端组装合同）。"""
    return f"切段方式：{MODE_TEXT[mode]}{CHUNK_NOTE_TAIL}"


def index_note(lib_name: str, snapshot: Mapping[str, Any]) -> str:
    """步 4 说明（✓/✗ 随该次入库配置快照——合同模板）。"""
    return INDEX_NOTE_TEMPLATE.format(
        lib_name=lib_name,
        semantic="✓" if snapshot.get("semantic") else "✗",
        keyword="✓" if snapshot.get("keyword") else "✗",
        wiki="✓" if snapshot.get("wiki") else "✗",
        graph="✓" if snapshot.get("graph") else "✗",
    )


# ---------- 错误族（映射归 api/errors.py；00 §3 统一错误包） ----------


class KbNotFoundError(Exception):
    """报告/库/任务/片段/上传受理不存在（B1 错误码草案 404）。"""


class KbParamError(Exception):
    """入参形状非法/筛选枚举越界/停用库受理（B1 错误码草案 400）。"""

    def __init__(self, message: str, *, code: str = "kb_param_invalid") -> None:
        self.code = code
        super().__init__(message)


class KbConflictError(Exception):
    """状态机冲突（B1 错误码草案 409：running 重试/confirm 未落桶或凭证已用/
    任务未 done 读产物/路由未定型）。"""

    def __init__(self, message: str, *, code: str = "kb_conflict") -> None:
        self.code = code
        super().__init__(message)


class KbDeferredError(Exception):
    """端点壳（片段修正动作＋问题块重生归 P1-02b）——api 层映射 501＋
    kb_fragment_revise_deferred（差异登记票面）。"""


@dataclass(frozen=True, slots=True)
class RebuildInfo:
    """修正重建回执（端点 4 rebuild——triggered=true＋hint 合同文案）。"""

    triggered: bool
    hint: str


@dataclass(frozen=True, slots=True)
class ReviseReceipt:
    """片段修正回执（端点 4：记版后版本轴＋重建折算提示＋活动行）。"""

    id: str
    version: int
    versions: list[FragmentVersionRow]
    rebuild: RebuildInfo
    activity_row: ActivityRow
    task_id: str


# ---------- id 族（00 §1.5 机器短 id） ----------


def new_lib_id() -> str:
    return f"lib-{uuid.uuid4().hex[:8]}"


def new_upload_id() -> str:
    return f"up-{uuid.uuid4().hex[:8]}"


def new_task_id() -> str:
    return f"task-{uuid.uuid4().hex[:8]}"


def new_report_id() -> str:
    return f"rpt-{uuid.uuid4().hex[:8]}"


def new_fragment_id(seq: int) -> str:
    """片段号（99 §2.5：id（f1…）——全局自增序号直拼）。"""
    return f"f{seq}"


def new_issue_id() -> str:
    """标记单号（99 §2.5 kb_issue_report：id（iss-））。"""
    return f"iss-{uuid.uuid4().hex[:8]}"


# ---------- 展示名与归一化 ----------


def doc_display(filename: str) -> str:
    """报告展示名（端点 6 注记：按上传文件名生成——《去扩展名》）。"""
    stem = re.sub(r"\.[A-Za-z0-9]+$", "", filename).strip()
    return f"《{stem}》"


def normalize_name(name: str) -> str:
    """重名/重名检测归一化（B1 端点 15：忽略首尾空白＋大小写——实施批口径从简落）。"""
    return re.sub(r"\s+", " ", name.strip()).casefold()


def normalize_filename(filename: str) -> str:
    """dup_warning 同名比对口径（B1 端点 5：归一化规则随实施批对齐——从简：
    去扩展名、去空白、casefold；B3 端点 4 同族纪律的 B1 侧落法，挂疑点清单）。"""
    stem = re.sub(r"\.[A-Za-z0-9]+$", "", filename)
    return re.sub(r"\s+", "", stem).casefold()


# ---------- 切段器（三切段方式——B1 F5/F30/F32） ----------


_HEADING_RE = re.compile(
    r"^\s*(?:#+\s*|)(\d+(?:\.\d+)*|第[一二三四五六七八九十百0-9]+[章节篇])[、.．:：\s]"
)


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[。！？；!?;])", text)
    return [p for p in parts if p]


def _section_of(line: str) -> tuple[int, str] | None:
    """标题行识别：返回 (点分级, 标题文本)。1＝章级、2＝节级。"""
    m = _HEADING_RE.match(line)
    if not m:
        return None
    number = m.group(1)
    title = line.strip()
    if number.startswith("第"):
        return (1, title)
    depth = number.count(".") + 1
    return (1 if depth == 1 else 2, title)


# ---------- 结构图（P1F-05 方案 A：LLM 出图＋逐字校验＋复合规则守门） ----------
#
# Owner 2026-10-03 拍板混合架构：入库结构图＝LLM 理解产出（只认文档真实标题行）
# ＋逐字校验防幻觉（任一 miss 整图作废）＋复合规则复检（越四条件单行剔除）＋
# 纯规则独立回退（LLM 不可用不阻塞入库）；机械切块语义不动（尺寸带/重叠/打包
# 常量同源）。合同锚：B1 智能切段「按章节和语义边界切」——本节只改「章节边界
# 由谁供给」，切段参数 256–1024/10–20% 为合同冻结值原样。


@dataclass(frozen=True, slots=True)
class HeadingLine:
    """结构图标题行（line_no＝0 基 splitlines 索引；title＝该行 strip 后原文；
    level 1＝章级、2＝节级——_section_of 点分级同口径）。"""

    line_no: int
    title: str
    level: int


@dataclass(frozen=True, slots=True)
class StructureMap:
    """文档结构图（标题行号/标题文本/层级——chunk_text smart/mixed 支路的边界源）。

    source 两值：`llm`（LLM 图——逐字校验＋规则复检后定稿）｜`rules`（纯规则图
    ——复合规则独立产出，LLM 不可用回退面）。行号必须对准切段用的同一 text
    （splitlines 索引）——快照 roundtrip 经 to_snapshot/from_snapshot。
    """

    headings: tuple[HeadingLine, ...]
    source: str

    def to_snapshot(self, text_sha256: str) -> dict[str, Any]:
        """任务快照列形（kb_ingest_task.structure_snapshot——版本级缓存）。"""
        return {
            "text_sha256": text_sha256,
            "source": self.source,
            "headings": [
                {"line_no": h.line_no, "title": h.title, "level": h.level}
                for h in self.headings
            ],
        }

    @classmethod
    def from_snapshot(cls, payload: Any) -> StructureMap | None:
        """快照还原（形状坏/键型不合法 → None——调用方重走提取，不硬凑）。"""
        if not isinstance(payload, dict):
            return None
        sha = payload.get("text_sha256")
        source = payload.get("source")
        rows = payload.get("headings")
        if not isinstance(sha, str) or source not in ("llm", "rules"):
            return None
        if not isinstance(rows, list):
            return None
        headings: list[HeadingLine] = []
        for row in rows:
            if not isinstance(row, dict):
                return None
            no, title, level = row.get("line_no"), row.get("title"), row.get("level")
            if not isinstance(no, int) or isinstance(no, bool) or no < 0:
                return None
            if not isinstance(title, str) or level not in (1, 2):
                return None
            headings.append(HeadingLine(line_no=no, title=title, level=level))
        return cls(headings=tuple(headings), source=source)


# 复合规则参数（票面四条件）：标题行长上限 40 字——超长标题归正文的不对称取舍。
HEADING_MAX_CHARS = 40
# 表格特征（f42 形态守门）：全角空格连续格（列对齐）／多空格数字格（ASCII 连续
# 空格接数字列、全角空格格间数字——月报表格行「2026　7　4.5%」形）。
_TABLE_FEATURE_RE = re.compile(r"\u3000\u3000| {2,}\d|\d[　]\d")
# 行尾句读（正文句证据——标题不以句号类收尾）。
_TAIL_SENTENCE_RE = re.compile(r"[。；！？!?;]\s*$")

# 结构图 LLM 单呼口径：有界超时（chat INTENT_VERDICT_TIMEOUT_SECONDS 同款纪律）
# 与逐行文本进提示词上限（超限不提取、直接走规则图——行号完整性优先于覆盖面）。
STRUCTURE_TIMEOUT_SECONDS = 30.0
STRUCTURE_PROMPT_MAX_CHARS = 20000

STRUCTURE_PROMPT_TEMPLATE = """你是油田报告结构分析助手。
下面给你一份报告的逐行文本，每行以行号开头。
请识别文档中真实的章节标题行：章级标题（如「1 概述」「第一章 完井工程」）
与节级标题（如「1.1 井身结构」）。
规则：
- 只输出文档中真实存在的标题行：title 必须逐字照抄该行原文，
  不得改写、概括或新增文档没有的标题；
- 正文长句、表格行（数字格）不是标题，不要输出；
- level：章级＝1，节级＝2；line_no＝该行的行号（从 1 起）。
只输出 JSON（不要多余文字）：
{{"headings": [{{"line_no": 1, "title": "标题行原文", "level": 1}}]}}
逐行文本：
{numbered}
"""


def is_heading_line(line: str) -> bool:
    """复合规则四条件（纯函数、独立可用——规则回退图与 LLM 图复检共用）：

    ①标题形（_HEADING_RE 分支命中）；②行长 ≤HEADING_MAX_CHARS；
    ③行尾无句读（。；！？——正文句证据）；④无表格特征（全角空格连续格/
    多空格数字格——f42 表格行形）。
    """
    stripped = line.strip()
    if not stripped or len(stripped) > HEADING_MAX_CHARS:
        return False
    if _section_of(stripped) is None:
        return False
    if _TAIL_SENTENCE_RE.search(stripped):
        return False
    return _TABLE_FEATURE_RE.search(stripped) is None


def _heading_from_line(line: str, line_no: int) -> HeadingLine | None:
    info = _section_of(line.strip())
    if info is None or not is_heading_line(line):
        return None
    return HeadingLine(line_no=line_no, title=line.strip(), level=info[0])


def rule_structure_map(text: str) -> StructureMap:
    """复合规则独立出图（LLM 不可用/整图作废的回退面——规则面单独有测）。"""
    headings = tuple(
        h
        for i, line in enumerate(text.splitlines())
        if (h := _heading_from_line(line, i)) is not None
    )
    return StructureMap(headings=headings, source="rules")


def parse_structure_json(raw: str) -> list[HeadingLine]:
    """解析 LLM 结构应答（宽容：剥代码围栏/前后杂文——chat _parse_intent_json
    同款纪律）。行号 1 基转 0 基；形状坏/无 JSON/任一行键型不合法 → []（整图
    作废口径，调用方回退规则图）。逐字校验在 validate_structure_map。"""
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return []
    try:
        payload = json.loads(text[start : end + 1])
    except ValueError:
        return []
    if not isinstance(payload, dict):
        return []
    rows = payload.get("headings")
    if not isinstance(rows, list):
        return []
    headings: list[HeadingLine] = []
    for row in rows:
        if not isinstance(row, dict):
            return []
        no, title, level = row.get("line_no"), row.get("title"), row.get("level")
        if not isinstance(no, int) or isinstance(no, bool):
            return []
        if not isinstance(title, str) or level not in (1, 2):
            return []
        headings.append(HeadingLine(line_no=no - 1, title=title.strip(), level=level))
    return headings


def validate_structure_map(
    headings: list[HeadingLine], lines: list[str]
) -> StructureMap | None:
    """逐字校验（防幻觉硬闸）：每张标题必须逐字命中文档真实行——任一 miss →
    None（整张作废，调用方回退规则图）。

    匹配口径：strip 后整行精确等值——不剥标点、不做子串/模糊匹配；行号本身
    也是校验对象（越界/指错行/重复行号同作废——幻觉与错位都按整图作废处置）。
    """
    seen: set[int] = set()
    ordered = sorted(headings, key=lambda h: h.line_no)
    for h in ordered:
        if h.line_no < 0 or h.line_no >= len(lines) or h.line_no in seen:
            return None
        seen.add(h.line_no)
        if lines[h.line_no].strip() != h.title:
            return None
    return StructureMap(headings=tuple(ordered), source="llm")


def _level_consistent(h: HeadingLine, line: str) -> bool:
    """层级一致性（P-007.fix F1）：行 level 与 `_section_of` 推导分级比对——
    推导不出分级（非标题形行）不算错标，归四条件复检处置。"""
    derived = _section_of(line.strip())
    return derived is None or derived[0] == h.level


def level_mismatch_rows(m: StructureMap, lines: list[str]) -> list[HeadingLine]:
    """层级错标行清单（P-007.fix F1 层级守门的判定输入）：LLM 标注 level 与
    文本推导分级（`_section_of` 点分级）不一致的行——章级行标 2／节级行标 1。
    调用方（service 编排）以错标行数过半（>50%）为 LLM 质量信号整图作废，
    未过半则随复检单行剔除。"""
    return [h for h in m.headings if not _level_consistent(h, lines[h.line_no])]


def refine_structure_map(m: StructureMap, lines: list[str]) -> StructureMap:
    """复合规则复检（双重保障）：逐字校验过的图再过四条件——通不过的行单行
    剔除（降级为正文）而非整图作废；与逐字校验两种处置分立（幻觉＝作废、
    越规则＝保守剔除）。

    P-007.fix F1：层级一致性同闸——level 与推导分级不一致的行（章级行错标
    level=2 会把 section 路径错挂成子节、章号停摆）同单行剔除；错标过半的
    整图作废判定在调用方（level_mismatch_rows 计数），不在本函数。
    """
    kept = tuple(
        h
        for h in m.headings
        if is_heading_line(lines[h.line_no]) and _level_consistent(h, lines[h.line_no])
    )
    return StructureMap(headings=kept, source=m.source)


def _pack(
    paragraphs: list[str],
    *,
    min_chars: int,
    max_chars: int,
    overlap: bool,
) -> list[str]:
    """把段落打包为 size 带内段（超长段落按句切＋overlap 回带）。"""
    chunks: list[str] = []
    buf = ""
    for para in paragraphs:
        candidate = f"{buf}{para}" if buf else para
        if len(candidate) <= max_chars:
            buf = candidate
            continue
        if buf:
            chunks.append(buf)
            buf = ""
        if len(para) <= max_chars:
            buf = para
            continue
        # 超长段落：按句切兜底打包（smart 语义边界；fixed 硬切另行处理）
        for sentence in _split_sentences(para):
            candidate = f"{buf}{sentence}" if buf else sentence
            if len(candidate) > max_chars and buf:
                chunks.append(buf)
                carry = (
                    buf[-max(32, int(len(buf) * SMART_OVERLAP_RATIO)) :] if overlap else ""
                )
                buf = f"{carry}{sentence}" if overlap else sentence
                if len(buf) > max_chars:  # 单句超上限：硬切保进度
                    while len(buf) > max_chars:
                        chunks.append(buf[:max_chars])
                        buf = buf[max_chars:]
            else:
                buf = candidate
    if buf:
        chunks.append(buf)
    # 末段过短且前段存在：并入前段（不产生碎段）
    if len(chunks) >= 2 and len(chunks[-1]) < min_chars:
        tail = chunks.pop()
        merged = f"{chunks[-1]}{tail}"
        if len(merged) <= max_chars * 1.2:  # 带内放宽 20% 优于碎段
            chunks[-1] = merged
        else:
            chunks.append(tail)
    return chunks


def chunk_text(
    text: str, mode: str, structure: StructureMap | None = None
) -> list[tuple[str, str]]:
    """切段：返回 [(section_path, chunk_text)]。

    - smart：按章节/语义边界切，一段 256–1024 字，相邻段重叠 10–20%；
    - fixed：每段等长（512 字硬切——句子可能被拦腰斩断，MODE_TEXT 同象）；
    - mixed：父子分块（F30）——父块＝章级大段（只入库不索引），子块由
      smart 打包；section 路径对子块标注父块锚。
    - structure（P1F-05 方案 A）：章节边界由结构图供给（LLM 理解＋逐字校验＋
      复合规则复检的定稿图，或复合规则独立图）；缺省按复合规则独立识别。
      图的 line_no 必须对准本函数收到的同一 text（splitlines 索引）。
      机械切块语义不动：尺寸带/重叠/片段 ID/父子打包全走既有同源常量。
    """
    if not text.strip():
        return []
    lines = text.splitlines()
    if mode == "fixed":
        flat = "".join(line.strip() for line in lines if line.strip())
        out: list[tuple[str, str]] = []
        for i in range(0, len(flat), FIXED_CHUNK_CHARS):
            out.append(("正文", flat[i : i + FIXED_CHUNK_CHARS]))
        return out
    map_ = structure if structure is not None else rule_structure_map(text)
    heading_at = {h.line_no: h for h in map_.headings}
    if mode == "mixed":
        # 父块＝章级段（标题及其后内容至下一章级标题）；无章级标题则整篇一父块。
        parents: list[tuple[str, str]] = []
        current_title = "正文"
        current: list[str] = []
        for i, line in enumerate(lines):
            heading = heading_at.get(i)
            if heading is not None and heading.level == 1:
                if current:
                    parents.append((current_title, "\n".join(current)))
                current_title = heading.title
                current = [line]
            else:
                current.append(line)
        if current:
            parents.append((current_title, "\n".join(current)))
        result: list[tuple[str, str]] = []
        for parent_title, parent_body in parents:
            parent_body = parent_body.strip()
            if not parent_body:
                continue
            if len(parent_body) > MIXED_PARENT_MAX_CHARS:
                parent_body = parent_body[:MIXED_PARENT_MAX_CHARS]
            parent_key = f"父块·{parent_title}"
            result.append((parent_key, parent_body))  # 父块行（is_parent_only 标记在落库侧）
            for child in _pack(
                [p for p in parent_body.splitlines() if p.strip()],
                min_chars=SMART_MIN_CHARS,
                max_chars=MIXED_CHILD_MAX_CHARS,
                overlap=True,
            ):
                result.append((parent_title, child))
        return result
    # smart（缺省）
    sections: list[tuple[str, list[str]]] = []
    current_title = "正文"
    current_lines: list[str] = []
    chapter_no = 0
    for i, line in enumerate(lines):
        heading = heading_at.get(i)
        if heading is not None:
            if current_lines:
                sections.append((current_title, current_lines))
            if heading.level == 1:
                chapter_no += 1
                current_title = f"章节 {chapter_no:02d} {heading.title}"
            else:
                current_title = f"{current_title} ＞ {heading.title}"
            current_lines = [line]
        else:
            current_lines.append(line)
    if current_lines:
        sections.append((current_title, current_lines))
    out = []
    for title, para_lines in sections:
        packed = _pack(
            [p for p in para_lines if p.strip()],
            min_chars=SMART_MIN_CHARS,
            max_chars=SMART_MAX_CHARS,
            overlap=True,
        )
        for piece in packed:
            out.append((title, piece))
    return out


# ---------- 关键词分词（倒排半边——99 §6-5 落法悬置，先立确定性分词） ----------


def tokenize(text: str) -> list[str]:
    """检索用确定性分词：ASCII 词＋CJK 二元组（stdlib 零依赖）。"""
    tokens: list[str] = []
    for raw in re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]", text):
        if raw.isascii():
            tokens.append(raw.casefold())
        else:
            tokens.append(raw)  # 单 CJK 字
    # CJK 二元组（对原文重扫，避免依赖分词器）
    cjk_runs = re.findall(r"[\u4e00-\u9fff]+", text)
    for run in cjk_runs:
        tokens.extend(run[i : i + 2] for i in range(len(run) - 1))
    return tokens


# ---------- 向量半边（pgvector 承载——99 §2.5 向量列落位注记） ----------

# 维度＝MiniMax embo-01 真维度 1536（P1-11 选型接线，Owner 2026-10-02 拍板
# MiniMax 优先；2026-10-02 curl 实测 vectors[N][1536] 已归一化。此前 384 为
# 本地占位维度——99 注记「维度待 embedding 模型选定后回填」本票回填，列形
# 随 Alembic 0012 迁移 384→1536、存量向量清重由 reembed 脚本重嵌）。
EMBED_DIM = 1536


class EmbeddingBackend(Protocol):
    """向量化 seam（真实 embedding 模型落位批只换实现，签名不动）。"""

    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class LocalHashEmbedder:
    """本地确定性向量（测试底座 fallback——非语义向量；生产装配＝RemoteEmbedder）。"""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._one(t) for t in texts]

    def _one(self, text: str) -> list[float]:
        vec = [0.0] * EMBED_DIM
        for token in tokenize(text):
            digest = hashlib.md5(token.encode("utf-8")).hexdigest()
            slot = int(digest[:8], 16) % EMBED_DIM
            sign = 1.0 if int(digest[8:10], 16) & 1 else -1.0
            vec[slot] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [round(v / norm, 6) for v in vec]


class RemoteEmbedder:
    """真 embedding 后端（P1-11——infra.llm_client.embeddings 缝的消费视图）。

    - B6 单点：供应商接触只在 infra.llm_client；本类是同一缝的域侧视图
      （faq.service.EmbeddingBackend 同构——组合根装配，kb 不 import infra）。
    - input_type＝MiniMax query/db 分离算法（实测形状见 models.yaml 头注释）：
      语料/入库文本＝db、检索探针＝query——两实例分别装配，禁混型单实例。
    - 上游失败（UpstreamUnavailable/UpstreamRejected）直抛调用方不静默——
      入库管线按阶段定位失败、检索向量腿按空腿处理（trigram 腿兜底）。
    """

    def __init__(
        self, client: Any, alias: str = "petro-embed", *, input_type: str = "db"
    ) -> None:
        self._client = client
        self._alias = alias
        self._input_type = input_type

    async def embed(self, texts: list[str]) -> list[list[float]]:
        out = await self._client.embeddings(self._alias, list(texts), input_type=self._input_type)
        vectors: list[list[float]] = [list(map(float, vec)) for vec in out.vectors]
        return vectors


# ---------- 报告索引检索读面（P1-08a——chat 六路装配报告索引路消费） ----------


@dataclass(frozen=True, slots=True)
class IndexHit:
    """报告索引命中（运行时读面 index_search 的行——chat 只见本面，不触 kb 表；
    98 §3.4 卡运行时读缝同 faq.match_index 惯例）。

    leg 两值＝检索瀑布 S4 两路（F58）：`vector` 语义一路 / `keyword` 字面一路
    （trigram 子串——P1-04 裁决；pg_trgm GIN 索引随 P1-10 上，查询语义不变）。
    text＝生成上下文用较长文本（P1-08b——snippet 仅 80 字，答案依据会被截断；
    生成窗＝SMART_MAX_CHARS（1024）全文进窗——与入库切段上限同源，不再截 500）。
    """

    fragment_id: str
    report_id: str
    report: str
    section: str | None
    snippet: str
    score: float
    leg: str  # vector | keyword
    text: str = ""


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


def trigram_coverage(question: str, text: str) -> float:
    """字面一路得分＝问句 trigram 集在文本 trigram 集中的覆盖率（0–1）。

    pg_trgm 子串匹配的阶段 1 语义代理（P1-04 裁决「关键词路＝trigram 子串匹配」；
    全问句子串命中→覆盖率 1.0）——中文免分词器，索引落位后查询语义不变。
    """
    q = _trigrams(question)
    if not q:
        return 0.0
    t = _trigrams(text)
    if not t:
        return 0.0
    return len(q & t) / len(q)


def _trigrams(text: str) -> set[str]:
    folded = re.sub(r"\s+", "", text or "")
    if not folded:
        return set()
    if len(folded) < 3:
        return {folded}
    return {folded[i : i + 3] for i in range(len(folded) - 2)}


@dataclass(frozen=True, slots=True)
class FragmentAnchor:
    """片段锚（fail-closed 校验读面——fragment_id 必须真实存在且属于命中报告；
    P1-08b citation locator 校验消费，chat 只见本面不触 kb 表）。"""

    fragment_id: str
    report_id: str
    report: str
    section: str | None


# ---------- 入库路由（B1 v0.3「入库路由（阶段 1 实施项）」专节） ----------


@dataclass(frozen=True, slots=True)
class RouteSuggestion:
    """路由建议（LLM 只建议、人确认后执行——不自动归库、不自动建库）。

    mode="existing"：建议归现有库（lib_id/lib_name＋reason＋confidence）；
    mode="new"：建议新建库（必带模板推荐 template——业务模板四枚举）；
    mode=None：分析不可用（LLM 失败/解析失败）——请手动指定目标库。
    """

    mode: Literal["existing", "new"] | None
    topic: str | None = None
    lib_id: str | None = None
    lib_name: str | None = None
    template: str | None = None
    reason: str | None = None
    confidence: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "topic": self.topic,
            "lib_id": self.lib_id,
            "lib_name": self.lib_name,
            "template": self.template,
            "reason": self.reason,
            "confidence": self.confidence,
        }


ROUTE_PROMPT_TEMPLATE = """你是油田知识平台的上库路由助手。
用户上传了一份报告，请根据话题判断它应归入哪个知识库。
已有知识库：{libs}
本体实体类型词表（辅助判断）：{entity_types}
规则：只建议、不执行；topic 与报告名是主要信号；confidence 取 0–1。
只输出 JSON（不要多余文字）：
{{"mode": "existing"|"new", "lib_name": "建议归入的现有库名（mode=existing 时必填）",
"template": "completion|monthly|dynamic|blank（mode=new 时必填）", "reason": "一句话理由",
"confidence": 0.0}}
用户话题：{topic}
报告文件名：{filename}
"""


def parse_route_suggestion(raw: str, libs: Mapping[str, str]) -> RouteSuggestion:
    """解析 LLM 路由应答（宽容 JSON 提取；lib_name → lib_id 归一）。

    归一失败/模板越界/库名不存在 → mode=None（分析不可用，不硬凑建议）。
    """
    text = raw.strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return RouteSuggestion(mode=None, reason="应答不含 JSON")
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return RouteSuggestion(mode=None, reason="应答 JSON 解析失败")
    mode = data.get("mode")
    reason = data.get("reason")
    try:
        confidence = round(float(data.get("confidence")), 4)
    except (TypeError, ValueError):
        confidence = None
    if mode == "existing":
        lib_name = str(data.get("lib_name") or "").strip()
        lib_id = libs.get(lib_name)
        if lib_id is None:
            return RouteSuggestion(mode=None, reason=f"建议库名「{lib_name}」不在现有库清单")
        return RouteSuggestion(
            mode="existing",
            lib_id=lib_id,
            lib_name=lib_name,
            reason=reason,
            confidence=confidence,
        )
    if mode == "new":
        template = str(data.get("template") or "").strip()
        if template not in BIZ_TEMPLATES:
            return RouteSuggestion(mode=None, reason=f"模板推荐「{template}」越界")
        return RouteSuggestion(mode="new", template=template, reason=reason, confidence=confidence)
    return RouteSuggestion(mode=None, reason="mode 取值不可识别")


# ---------- DTO（读面投影——api 层直接消费） ----------


@dataclass(frozen=True, slots=True)
class LibraryView:
    """库列表行（端点 11：开关快照＝最近一次入库所用——两态分离）。"""

    id: str
    name: str
    biz_template: str
    status: str
    last_ingestion: dict[str, Any] | None  # {doc, switches}——由最近 run 快照派生
    annotations: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class LibraryConfigView:
    """库配置读面（端点 12：双消费——上传预览/配置弹窗）。"""

    id: str
    name: str
    switches: dict[str, bool]
    mode: str
    add_summary: bool
    add_questions: bool
    saved_at: str | None
    saved_by: str | None


@dataclass(frozen=True, slots=True)
class FragmentVersionRow:
    v: int
    text: str
    note: str


@dataclass(frozen=True, slots=True)
class FragmentRow:
    """片段投影（端点 2 同源投影；path＝section 展示；父块不对外寻址）。"""

    id: str
    type: str
    path: str
    text: str
    version: int
    versions: list[FragmentVersionRow]


@dataclass(frozen=True, slots=True)
class ReportLedgerRow:
    """台账行（端点 1：refs/wiki 与 B2/B4 同源；status 两态合同值）。"""

    id: str
    doc: str
    lib_id: str
    lib: str
    refs: int | None
    wiki: str | None
    status: str  # 已入库 | 入库中


@dataclass(frozen=True, slots=True)
class ReportDetail:
    """报告详情（端点 2：片段预览含版本）。"""

    id: str
    doc: str
    lib_id: str
    lib: str
    subject: str | None
    refs: int | None
    wiki: str | None
    status: str
    related_objects: list[dict[str, str]]
    fragments: list[FragmentRow]


@dataclass(frozen=True, slots=True)
class UploadReceipt:
    """直传受理回执（端点 5：两拍第一拍）。"""

    upload_id: str
    lib_id: str | None
    lib_name: str | None
    dup_warning: str | None
    put_url: str
    expires_at: str
    bucket: str  # 显示名「报告原文」照抄
    routing: RouteSuggestion | None


@dataclass(slots=True)
class TaskNode:
    """五步节点（00 §5.3 四态；任务体推进时原地改 state/note——同 gateway DrillNode）。"""

    key: str
    label: str
    state: str = NODE_WAIT
    note: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"key": self.key, "label": self.label, "state": self.state, "note": self.note}


@dataclass(frozen=True, slots=True)
class TaskView:
    """任务行（端点 7：source 来源随行——Owner v0.2 拍板）。"""

    id: str
    doc: str
    lib_id: str
    lib_name: str
    source: str
    state: str
    current_step: int
    stop_at: str | None
    reason: str | None


@dataclass(frozen=True, slots=True)
class ConfirmReceipt:
    """确认入库回执（端点 6：任务号＋定型快照＋展示名）。"""

    task_id: str
    upload_id: str
    doc: str
    lib_id: str
    lib_name: str
    source: str
    state: str
    current_step: int
    config_snapshot: dict[str, Any]


@dataclass(frozen=True, slots=True)
class TaskProgress:
    """轮询视图（端点 8/10：五步节点＋服务端组装说明＋定型快照）。"""

    id: str
    state: str
    source: str
    current_step: int
    stop_at: str | None
    reason: str | None
    nodes: list[TaskNode]
    config_snapshot: dict[str, Any]


@dataclass(frozen=True, slots=True)
class AdditionsView:
    """索引期加法产物（端点 9：摘要块＋问题块两卡）。"""

    task_id: str
    doc: str
    summary: dict[str, Any] | None
    questions: dict[str, Any] | None


@dataclass(frozen=True, slots=True)
class ActivityRow:
    """库活动流行（F62 四列）。"""

    time: str
    who: str
    action: str
    target: str


@dataclass(frozen=True, slots=True)
class SaveReceipt:
    """配置保存回执（端点 13：含 v0.3 status 回显与活动行）。"""

    id: str
    saved_at: str
    saved_by: str
    status: str
    hint: str
    activity_row: ActivityRow


@dataclass(frozen=True, slots=True)
class CreateLibReceipt:
    """建库回执（端点 15：201）。"""

    lib_id: str
    lib_name: str
    biz_template: str
    status: str
    config: dict[str, Any]
    activity_row: ActivityRow


# ---------- B2 切片管理 DTO（B2-答案出处.md v0.3 关键形状） ----------


@dataclass(frozen=True, slots=True)
class FragmentListItem:
    """片段台账行（B2 端点 1——三件套 report/well/section＋五类型标＋hit；
    DTO 无 context 字段（INV 落点：列表只给子块，上下文仅经端点 2 按需回捞）。"""

    id: str
    report_id: str
    report: str
    well: str | None
    section: str | None
    type: str
    hit: str


@dataclass(frozen=True, slots=True)
class FragmentList:
    """片段列表（B2 端点 1：两读法分派——按报告整组取数整表返回；全库扁平清单
    分页读法回显 page/page_size——00 §4.1 信封）。"""

    items: list[FragmentListItem]
    total: int
    page: int | None = None
    page_size: int | None = None


@dataclass(frozen=True, slots=True)
class FragmentContext:
    """父块回捞（B2 端点 2——context 字段只在本端点存在）。"""

    id: str
    type: str
    hit: str
    context: str


@dataclass(frozen=True, slots=True)
class IssueReportView:
    """标记单视图（B2 端点 3/4/5/6——fragment_label 三件套同源拼装）。"""

    id: str
    fragment_id: str
    report_id: str
    fragment_label: str
    state: str
    marked_by: str
    marked_at: str
    reject_reason: str | None = None
    hint: str | None = None
