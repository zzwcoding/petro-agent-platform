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
  （ADR-0003 裁决 1：pgvector，维度待 embedding 模型选定回填＝待办）。

B1：本文件不 import fastapi/starlette/DB/LLM——切段器、分词、向量占位、
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


def chunk_text(text: str, mode: str) -> list[tuple[str, str]]:
    """切段：返回 [(section_path, chunk_text)]。

    - smart：按章节/语义边界切，一段 256–1024 字，相邻段重叠 10–20%；
    - fixed：每段等长（512 字硬切——句子可能被拦腰斩断，MODE_TEXT 同象）；
    - mixed：父子分块（F30）——父块＝章级大段（只入库不索引），子块由
      smart 打包；section 路径对子块标注父块锚。
    """
    text = text.strip()
    if not text:
        return []
    lines = text.splitlines()
    if mode == "fixed":
        flat = "".join(line.strip() for line in lines if line.strip())
        out: list[tuple[str, str]] = []
        for i in range(0, len(flat), FIXED_CHUNK_CHARS):
            out.append(("正文", flat[i : i + FIXED_CHUNK_CHARS]))
        return out
    if mode == "mixed":
        # 父块＝章级段（标题及其后内容至下一章级标题）；无章级标题则整篇一父块。
        parents: list[tuple[str, str]] = []
        current_title = "正文"
        current: list[str] = []
        for line in lines:
            info = _section_of(line)
            if info is not None and info[0] == 1:
                if current:
                    parents.append((current_title, "\n".join(current)))
                current_title = info[1]
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
    for line in lines:
        info = _section_of(line)
        if info is not None:
            if current_lines:
                sections.append((current_title, current_lines))
            if info[0] == 1:
                chapter_no += 1
                current_title = f"章节 {chapter_no:02d} {info[1]}"
            else:
                current_title = f"{current_title} ＞ {info[1]}"
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

# 维度占位（99：维度待 embedding 模型选定后回填＝待办——本票以本地确定性
# 向量占位打通 pgvector 全链，EmbeddingBackend 为换模型唯一缝，挂疑点清单）。
EMBED_DIM = 384


class EmbeddingBackend(Protocol):
    """向量化 seam（真实 embedding 模型落位批只换实现，签名不动）。"""

    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class LocalHashEmbedder:
    """本地确定性向量（占位实现——非语义向量，仅打通链路与冒烟可查）。"""

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
