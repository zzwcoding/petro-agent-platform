"""domains.faq.domain —— B3 常见问题库域语义层（合同语义真源；持久在 store.py）。

合同真源（只读引用，不复制正文）：teach-petro-agent/specs/api/B3-常见问题库.md
v0.2（17 端点＋三态/待审核发布流＋挖掘管线五拍＋导入导出＋⚙ 改版）· 98 §3.3
卡 · 99 §2.6 faq 四表 · 00 §4.4 批量口径（导入四计数）。

- 状态机（合同常量冻结）：`pending_review 待审核`（前置态）→ 审核 publish 按
  登记类型落 `serve 服务中`/`negative 负例`、reject 落 `disabled 已停用`；
  三态互斥（负例 disable 409）。种子直接发布。
- 索引可见性：服务中＝入索引命中即秒回；负例＝不入索引检索不可达（W-F35-3）；
  已停用＝摘出索引；待审核＝不入索引不被 A1 消费。
- 归一化（重复校验/导入去重）：去首尾空白、忽略大小写、全半角标点差异后比对
  （页面 norm 同构）；导入去重 R24＝归一化 SHA256（票 49）。
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# ---------- 合同常量（不可改，注源见模块 docstring 与各处行注） ----------

FAQ_STATUSES = ("pending_review", "serve", "negative", "disabled")
# 状态筛选：all/serve/neg/disabled（B3 合同常量）＋pending（企业化清理批页面
# 增设「待审核」筛项——页面现实现为准，差异登记 tickets/phase1 README P1-06）。
ENTRY_STATUS_FILTERS = ("all", "serve", "pending", "neg", "disabled")

CANDIDATE_STATUSES = ("pending", "compared", "drafted", "published")
# dup＝非待比对且比对结论疑似重复；ok＝已比对未判 dup（含草稿态）。
CANDIDATE_FILTERS = ("all", "pending", "dup", "ok", "drafted", "published")

SCAN_WINDOW = "近30天"  # 统计周期（合同常量维持）

# 相似问合并阈值（B3-4：归 B3 域配置；0.87 维持演示值、实施批校准——
# 承载与校准同批定，本票以模块常量承载，挂疑点清单）。
MERGE_THRESHOLD = 0.87

EMPTY_QUESTION_PLACEHOLDER = "（未填问题）"  # 空值占位（不拒空——端点 3 合同行为）
EMPTY_ANSWER_PLACEHOLDER = "（未填答案）"

DUP_HINT_TEMPLATE = (
    "与既有问答「{question}」疑似重复（系统忽略大小写、全角半角差异后比对）："
    "建议改用合并相似问，或确认继续入库。"
)
SIMILAR_DELETE_HINT = "已删除——该问法不再命中本条。"

# 入库提示（v0.2 审核流文案——合同常量表照抄；候选回写并入同模板）。
CREATED_HINT_TEMPLATE = "已提交审核：「{question}」——审核发布后命中即秒回。"
CREATED_NEGATIVE_HINT_TEMPLATE = (
    "已提交审核：「{question}」——审核发布后登记为负例，永不参与回答，检索也不可达。"
)
MERGE_HINT_TEMPLATE = (
    "已合并：2 条 → 1 条——「{from_question}」并入「{target_question}」，"
    "两种问法现在命中同一条答案。"
)

DRAFT_SOURCE_SUFFIX = "LLM 基于历史回答归纳，请人工核实"  # 溯源后缀（起草口径）
DUP_DRAFT_TEXT = "（疑似重复——不建议新增，请改用清单里的合并相似问。）"  # dup 不关起草闸

SCAN_RUNNING_HINT = (
    "正在扫描用户问句库（聚类＋频次统计）……可关闭弹窗继续其他操作，"
    "扫描不会中断；重开弹窗看结果。"
)
# A1 未上线前的扫库料源空态说明（票面：料＝A1 历史会话，未上线前留空态说明）。
SCAN_EMPTY_MATERIAL_HINT = (
    "扫描完成：本次新增 0 个候选簇——A1 问一问历史会话尚未上线，暂无可挖掘语料；"
    "上线后扫库将自动分析历史会话归纳候选簇。"
)

REVIEW_PUBLISH_SERVE_HINT_TEMPLATE = "审核通过已发布：「{question}」——命中即秒回，不走报告检索。"
REVIEW_PUBLISH_NEGATIVE_HINT_TEMPLATE = (
    "审核通过已发布：「{question}」——登记为负例，永不参与回答，检索也不可达。"
)
REVIEW_REJECT_HINT_TEMPLATE = "已驳回：「{question}」——条目转已停用，可修改后重新提审。"

# 导入模板列（合同值；导出列与之对称——端点 16）。
IMPORT_COLUMNS = ("标准问", "相似问法", "负例问法", "答案")
EXPORT_COLUMNS = ("标准问", "相似问法", "负例问法", "答案")
# 相似问法多值分隔（合同未冻结——导入接受多分隔符、导出统一「；」，对称自洽）。
SIM_SEPARATOR_EXPORT = "；"
_SIM_SEPARATOR_IMPORT = ("；", "、", "|")

LEDGER_MERGED_EVENT = "LedgerMerged"  # 订阅的语义台账事件（98 §8——B3-2 口径修订联动）


# ---------- 归一化与去重键（重复校验/导入去重——合同常量表） ----------


def normalize_text(text: str) -> str:
    """轻归一化：去首尾空白＋全半角折叠＋忽略大小写＋去标点/空白后比对。

    页面 norm 同构（`norm = s => s.trim().toLowerCase().replace(\\s+/g,'')
    .replace(/[？?！!。.,，]/g,'')`）；全半角差异按 NFKC 折叠承载（合同
    「全半角标点差异后比对」），标点/空白整体剥除比页面逐字符清单更稳（等价超集
    ——纯标点差异在两侧都剥除后不可区分，语义不变）。
    """
    folded = unicodedata.normalize("NFKC", text or "").casefold()
    return re.sub(r"[\s\W_]+", "", folded, flags=re.UNICODE)


def norm_hash(text: str) -> str:
    """归一化 SHA256 去重键（票 49 R24——结果等价的确定性实现）。"""
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


# ---------- 标识发生器（id 形照合同演示族） ----------


def new_entry_id(existing: list[str]) -> str:
    """条目号（faq-<n>，合同演示族 faq-1…faq-10——现库最大序号 +1）。"""
    seqs = [int(m.group(1)) for x in existing if (m := re.fullmatch(r"faq-(\d+)", x))]
    return f"faq-{max(seqs, default=0) + 1}"


def new_sim_id(existing: list[str]) -> str:
    """相似问号（sq-<n>，合同演示族 sq-101…）。"""
    seqs = [int(m.group(1)) for x in existing if (m := re.fullmatch(r"sq-(\d+)", x))]
    return f"sq-{max(seqs, default=100) + 1}"


def new_candidate_id(existing: list[str]) -> str:
    """候选簇号（c<n>，合同演示族 c1…c4）。"""
    seqs = [int(m.group(1)) for x in existing if (m := re.fullmatch(r"c(\d+)", x))]
    return f"c{max(seqs, default=0) + 1}"


def new_scan_task_id(now: datetime) -> str:
    """扫库任务号（scan-<MMDD>，合同演示形 scan-0929；同日冲突加序尾）。"""
    return f"scan-{now:%m%d}"


# ---------- 入参值对象 ----------


@dataclass(frozen=True, slots=True)
class Hook:
    """关联口径（端点 3 `hook`：null＝不挂接或 {kind: metric|term, name}）。

    选项与 C1 台账同源（票 93）；负例行 hook 恒 null（服务端忽略负例单的
    hook——合同冻结）。消费＝口径修订联动触发器（LedgerMerged 按 hook 定位）。
    """

    kind: str
    name: str

    def as_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "name": self.name}


@dataclass(frozen=True, slots=True)
class LedgerRef:
    """引用知识起草·台账口径源（端点 14——服务端直取台账定义，不信任前端文本）。"""

    kind: str  # metric | term
    id: int


@dataclass(frozen=True, slots=True)
class SliceRef:
    """引用知识起草·切片原文源（{report_id, fragment_id}——B2 片段 id 同一标识）。"""

    report_id: str
    fragment_id: str


# ---------- 领域异常（错误码 faq_*——api.errors 统一映射） ----------


class FaqParamError(Exception):
    """400 族（入参形状非法/枚举越界/空白；code 由构造携带）。"""

    def __init__(self, message: str, *, code: str = "faq_param_invalid") -> None:
        super().__init__(message)
        self.code = code


class FaqNotFoundError(Exception):
    """404 族（条目/候选/相似问/扫库任务不存在，含已合并删除与过期任务）。"""


class FaqConflictError(Exception):
    """409 族（状态机冲突/重入/重复，code 由构造携带）。"""

    def __init__(self, message: str, *, code: str = "faq_conflict") -> None:
        super().__init__(message)
        self.code = code


# ---------- 读出视图（端点 DTO 语义形——api 层折 pydantic） ----------


@dataclass(frozen=True, slots=True)
class SimilarRef:
    """相似问寻址行（端点 2 详情：id＝增删寻址键、text 与清单展示串一致）。"""

    id: str
    text: str


@dataclass(frozen=True, slots=True)
class FaqItem:
    """清单行（端点 1——similar_questions＝展示字符串原样）。"""

    id: str
    question: str
    answer: str
    similar_questions: list[str]
    status: str
    hook: Hook | None


@dataclass(frozen=True, slots=True)
class FaqList:
    """清单信封：total＝筛选命中（「筛选结果 X」）、grand_total＝全库条数。"""

    items: list[FaqItem]
    total: int
    grand_total: int


@dataclass(frozen=True, slots=True)
class FaqDetail:
    """详情（端点 2——maintainer/updated_at/version 支撑详情底行；日期粒度照抄）。"""

    id: str
    question: str
    answer: str
    status: str
    hook: Hook | None
    similar_questions: list[SimilarRef]
    maintainer: str
    updated_at: str
    version: int


@dataclass(frozen=True, slots=True)
class CandidateRef:
    """候选回写随行（端点 3 响应 candidate——v0.2 回写时点在审核发布事务内）。"""

    id: str
    status: str


@dataclass(frozen=True, slots=True)
class FaqCreated:
    """新增入库回执（端点 3——v0.2 恒 pending_review，hint 为审核流文案）。"""

    id: str
    status: str
    version: int
    hint: str
    candidate: CandidateRef | None


@dataclass(frozen=True, slots=True)
class DupHit:
    """重复校验命中（端点 4——非阻断，仅警告）。"""

    id: str
    question: str


@dataclass(frozen=True, slots=True)
class SimilarAdded:
    """相似问新增回执（端点 5——version 为条目版本自增后值）。"""

    id: str
    text: str
    version: int


@dataclass(frozen=True, slots=True)
class VersionBumped:
    """相似问删除回执（端点 6）。"""

    version: int
    hint: str


@dataclass(frozen=True, slots=True)
class MergeResult:
    """合并回执（端点 7——2 条 → 1 条；被并入条目删除）。"""

    from_id: str
    target_id: str
    merged_count: str
    target_similar_questions_count: int
    hint: str


@dataclass(frozen=True, slots=True)
class FaqStateView:
    """停用/启用回执（端点 8）。"""

    id: str
    status: str
    version: int


@dataclass(frozen=True, slots=True)
class FaqReviewed:
    """审核回执（端点 17——publish 落 serve/negative、reject 落 disabled）。"""

    id: str
    status: str
    version: int
    hint: str


@dataclass(frozen=True, slots=True)
class CompareResult:
    """向量比对结论（端点 12——三面去重；hint 服务端组装、前端零拼装）。"""

    verdict: str  # dup | ok
    dup_question: str | None
    similarity: float | None
    onto_hit: str | None
    hint: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "dup_question": self.dup_question,
            "similarity": self.similarity,
            "onto_hit": self.onto_hit,
            "hint": self.hint,
        }


@dataclass(frozen=True, slots=True)
class CandidateItem:
    """候选簇行（端点 9——compare 为 null 不显示展开按钮〔合同〕；频次倒序）。"""

    id: str
    question: str
    variants: list[str]
    freq: int
    window: str
    status: str
    compare: CompareResult | None
    draft: str | None
    hook: Hook | None


@dataclass(frozen=True, slots=True)
class ScanPanel:
    """扫库态随行（端点 9 scan 段——重开弹窗恢复提示用）。"""

    running_task_id: str | None
    last_hint: str | None


@dataclass(frozen=True, slots=True)
class CandidateList:
    """候选清单信封（total＝全部候选簇数，不受筛选影响——页头「候选 N 簇」）。"""

    items: list[CandidateItem]
    total: int
    scan: ScanPanel


@dataclass(frozen=True, slots=True)
class ScanHandle:
    """扫库受理回执（端点 10——202）。"""

    task_id: str
    status: str
    hint: str


@dataclass(frozen=True, slots=True)
class NewCluster:
    """扫库新增簇（端点 11 done 载荷）。"""

    id: str
    question: str
    freq: int


@dataclass(frozen=True, slots=True)
class ScanProgress:
    """扫库轮询回执（端点 11——running 时 clusters 空、hint null）。"""

    task_id: str
    status: str
    new_cluster_count: int
    new_clusters: list[NewCluster]
    hint: str | None


def scan_done_hint(clusters: list[NewCluster]) -> str:
    """扫库完成提示模板（合同常量——多簇逐个列举）。"""
    if not clusters:
        return SCAN_EMPTY_MATERIAL_HINT
    listed = "；".join(f"「{c.question}」（{c.freq} 次 / {SCAN_WINDOW}）" for c in clusters)
    return f"扫描完成：本次新增 {len(clusters)} 个候选簇——{listed}。"


@dataclass(frozen=True, slots=True)
class CandidateDraft:
    """候选起草回执（端点 13——草稿恒带溯源后缀；确认权在人）。"""

    id: str
    status: str
    draft: str
    hook_suggestion: Hook | None


@dataclass(frozen=True, slots=True)
class DraftResult:
    """引用知识起草回执（端点 14——本端点不落库，入库走端点 3）。"""

    draft: str
    hook_suggestion: Hook | None


@dataclass(frozen=True, slots=True)
class ImportRowFailure:
    """导入失败行（人话原因，不发明错误码数字——B1 同纪律）。"""

    row: int
    reason: str


@dataclass(frozen=True, slots=True)
class ImportStats:
    """批量导入四计数（00 §4.4 行内状态＋sums 口径；端点 15 合同冻结统计语义）。"""

    dry_run: bool
    added: int
    merged: int
    skipped: int
    failed: int
    failures: list[ImportRowFailure] = field(default_factory=list)
    hint: str = ""


@dataclass(frozen=True, slots=True)
class DownloadHandle:
    """导出直链回执（端点 16——预签名 GET 小时级有效；对象本体不过期，B3-8）。"""

    download_url: str
    expires_at: str
    columns: list[str]
    hint: str


@dataclass(frozen=True, slots=True)
class FaqHit:
    """FAQ 索引命中（运行时读口 match_index——A1 六路匹配器 FAQ 路消费，
    不经 HTTP；只服务中条目可达，v0.2 审核流）。"""

    entry_id: str
    question: str
    answer: str
