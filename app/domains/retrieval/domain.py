"""domains.retrieval.domain —— 检索配置域语义（厚：D2 合同常量/patch 校验/版本号在
此闭环）。

合同锚（真源在 teach-petro-agent/specs/api/，只引路径不复制正文）：
- D2-搜索与回答.md v0.2：端点 1 config 读（七节＝version 元信息节＋六配置节；
  「七个配置节」计数含 version 节——R1 证据列「其 version 节」同口径；patch
  白名单枚举六节为合同字面）/端点 2 change-requests（202 受理；单号即 A3
  变动单号 `#CFG-…`）；qa_behavior 五字段（faq_direct_hit=true /
  refuse_threshold=0.4〔页面演示初值，不入不可改清单〕/ clarify_strategy=
  ask_missing〔现值唯一档〕/ confidence_thresholds={high:0.8, low:0.4}〔F56
  已拍板口径〕/ faq_expand_rounds=3〔演示默认值，合法域 1–5——Owner 2026-10-01
  B3 拍板批自 B3 收敛本页〕）；错误码草案（patch 非法 400 带字段名与允许区间；
  在途单 409）。
- 00 §14-R1：D2 主体 camelCase 键（semanticTopK/earlyStop/citationFormat/
  changeRequestId…）统一 snake_case——本端点即真实接线直接落 snake（D1 同款
  迁移纪律）；R2：version.updated_at 为展示列（空格分隔「YYYY-MM-DD HH:mm」，
  接口层拼装）。
- 99 §2.10：retrieval_config（生效指针单例行）＋retrieval_config_version
  （append-only 版本表，version_no 自然键、config jsonb、via 生效变动单号）。
- 阶段 1 过渡形态（D2 端点 2 生效链注记）：A3/C3 阶段 3 才上线——阶段 1 检索
  配置＝提交即生效（记审计＋版本推进，不走 A3/C3）；pendingChange 恒空
  （无审批等待期——驳回清空/批准后保留至生效的两态语义挂 A3 接入批兑现）。

topK/topN 上限（1–100）＝D2 开放问题 6 授权「实施批定上限」的实施值（防一次
捞爆索引/成本闸；常量集中本文件，Owner 可调）；refuse_threshold 0–1 为页面
控件值域（步长 0.05 是页面 InputNumber 步进，不入合同值域）。

B1：本文件不 import fastapi/starlette/DB——patch 校验、节合并、id 生成都是
纯语义；IO 归 store（PG）/service（编排）。
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

# ---------- 合同常量（值照抄 D2 册，注源见模块 docstring） ----------

SECTION_KEYS: tuple[str, ...] = (
    "order",
    "params",
    "rerank",
    "citation_format",  # R1 snake 迁移（合同字面 citationFormat）
    "fallback",
    "qa_behavior",
)

RERANK_TIERS = ("fast", "llm", "compound")
CITATION_FORMATS = ("page", "code")
MERGE_MODES = ("rrf_rank", "concat")
FALLBACK_STRATEGIES = ("fixed", "free")
CLARIFY_STRATEGIES = ("ask_missing",)  # 现值唯一档（其余档位待实施批定）

TOPK_LIMIT: tuple[int, int] = (1, 100)  # 上限＝实施批定（开放问题 6；Owner 可调）
FAQ_EXPAND_ROUNDS_LIMIT: tuple[int, int] = (1, 5)  # 合同冻结域（B3 收敛来）
THRESHOLD_RANGE: tuple[float, float] = (0.0, 1.0)  # 页面控件值域（低分线/置信度线）

DEFAULT_FALLBACK_TEXT = (
    "报告库里没有找到能回答这个问题的内容。我不能凭空编——请换个问法，或联系资料员补充报告。"
)
SEED_UPDATED_BY = "系统"  # 种子非人操作（00 §2.2 低风险自动执行 who＝「系统」）
PENDING_STATE = "pending"  # 合同字面（A3 审批链形态值——阶段 1 受理即生效，
# 生效性由 version.via＝本单号回链承载；A3/C3 接入批该字段语义如实化）

_PARAM_KEYS = ("semantic_top_k", "keyword_top_k", "merge", "top_n")
_QA_KEYS = (
    "faq_direct_hit",
    "refuse_threshold",
    "clarify_strategy",
    "confidence_thresholds",
    "faq_expand_rounds",
)


# ---------- 错误族（D2 错误码草案——api 层映射错误包） ----------


class RetrievalParamError(Exception):
    """patch 校验不过（D2 400：错误体带字段名与允许区间——D1 400 先例同形）。"""

    def __init__(self, violations: list[tuple[str, str]]) -> None:
        self.violations = violations  # [(字段路径, 允许区间/约束), ...]
        super().__init__("；".join(f"{f} 允许 {r}" for f, r in violations))


class RetrievalConflictError(Exception):
    """在途变更单重入（D2 409：同页在途单串行）。

    阶段 1 受理→生效一体、无审批等待期——在途窗口＝受理处理期，409 判据＝
    并发受理撞闸；A3/C3 接入批切回审批链后，在途单权威状态以 A3 单据投影
    （99 §2.4 注——pendingChange 不落本域表）。
    """


# ---------- patch 校验（整节替换——形状同端点 1 对应节） ----------

Violation = tuple[str, str]


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _exact_keys(section: Mapping[Any, Any], keys: tuple[str, ...]) -> bool:
    return set(section.keys()) == set(keys)


def _int_violation(
    out: dict[str, Any],
    value: object,
    path: str,
    limit: tuple[int, int],
    violations: list[Violation],
) -> None:
    low, high = limit
    if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high:
        out[path.rsplit(".", 1)[-1]] = value
    else:
        violations.append((path, f"{low}–{high}"))


def _threshold_violation(
    out: dict[str, Any],
    value: object,
    path: str,
    violations: list[Violation],
) -> None:
    low, high = THRESHOLD_RANGE
    if (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and low <= value <= high
    ):
        out[path.rsplit(".", 1)[-1]] = float(value)
    else:
        violations.append((path, f"{low}–{high}"))


def _enum_violation(
    out: dict[str, Any],
    value: object,
    path: str,
    allowed: tuple[str, ...],
    violations: list[Violation],
) -> None:
    if isinstance(value, str) and value in allowed:
        out[path.rsplit(".", 1)[-1]] = value
    else:
        violations.append((path, "|".join(allowed)))


def _validate_order(
    section: object, violations: list[Violation]
) -> dict[str, Any] | None:
    path = "patch.order"
    if not isinstance(section, Mapping) or not _exact_keys(section, ("levels", "early_stop")):
        violations.append(
            (path, "键集须恰为 levels/early_stop（整节替换——形状同端点 1 对应节）")
        )
        return None
    before = len(violations)
    levels_value = section["levels"]
    levels: list[dict[str, Any]] = []
    if not isinstance(levels_value, list) or len(levels_value) != 3:
        violations.append((f"{path}.levels", "恰为三级 1/2/3（三级顺序合同冻结，不可增删倒序）"))
    else:
        for pos, item in enumerate(levels_value, start=1):
            item_path = f"{path}.levels[{pos - 1}]"
            if not isinstance(item, Mapping) or not _exact_keys(item, ("level", "enabled")):
                violations.append((item_path, "键集须恰为 level/enabled"))
                continue
            level = item["level"]
            if not _is_int(level) or int(level) != pos:
                violations.append(
                    (f"{item_path}.level", f"恒为 {pos}（三级顺序合同冻结——顺序不可改）")
                )
            elif isinstance(item["enabled"], bool):
                levels.append({"level": pos, "enabled": item["enabled"]})
            else:
                violations.append((f"{item_path}.enabled", "布尔"))
    early_stop = section["early_stop"]
    if not isinstance(early_stop, bool):
        violations.append((f"{path}.early_stop", "布尔"))
        early_stop = None
    if len(violations) > before or early_stop is None:
        return None
    return {"levels": levels, "early_stop": early_stop}


def _validate_params(
    section: object, violations: list[Violation]
) -> dict[str, Any] | None:
    path = "patch.params"
    if not isinstance(section, Mapping) or not _exact_keys(section, _PARAM_KEYS):
        violations.append(
            (path, "键集须恰为 semantic_top_k/keyword_top_k/merge/top_n（整节替换）")
        )
        return None
    before = len(violations)
    out: dict[str, Any] = {}
    for key in ("semantic_top_k", "keyword_top_k", "top_n"):
        _int_violation(out, section[key], f"{path}.{key}", TOPK_LIMIT, violations)
    _enum_violation(out, section["merge"], f"{path}.merge", MERGE_MODES, violations)
    return None if len(violations) > before else out


def _validate_fallback(
    section: object, violations: list[Violation]
) -> dict[str, Any] | None:
    path = "patch.fallback"
    if not isinstance(section, Mapping) or not _exact_keys(section, ("strategy", "text")):
        violations.append((path, "键集须恰为 strategy/text（整节替换）"))
        return None
    before = len(violations)
    out: dict[str, Any] = {}
    _enum_violation(out, section["strategy"], f"{path}.strategy", FALLBACK_STRATEGIES, violations)
    text_value = section["text"]
    # free 态下文本域仍可编辑、端点原样存储不做联动校验（合同注记）——只拦空白串
    # （fixed 空文案无运行时承载；free 态空串同样按形状不符拒）。
    if isinstance(text_value, str) and text_value.strip():
        out["text"] = text_value
    else:
        violations.append((f"{path}.text", "非空白字符串"))
    return None if len(violations) > before else out


def _validate_qa_behavior(
    section: object, violations: list[Violation]
) -> dict[str, Any] | None:
    path = "patch.qa_behavior"
    if not isinstance(section, Mapping) or not _exact_keys(section, _QA_KEYS):
        violations.append(
            (
                path,
                "键集须恰为 faq_direct_hit/refuse_threshold/clarify_strategy/"
                "confidence_thresholds/faq_expand_rounds（整节替换）",
            )
        )
        return None
    before = len(violations)
    out: dict[str, Any] = {}
    if isinstance(section["faq_direct_hit"], bool):
        out["faq_direct_hit"] = section["faq_direct_hit"]
    else:
        violations.append((f"{path}.faq_direct_hit", "布尔"))
    _threshold_violation(out, section["refuse_threshold"], f"{path}.refuse_threshold", violations)
    _enum_violation(
        out, section["clarify_strategy"], f"{path}.clarify_strategy", CLARIFY_STRATEGIES, violations
    )
    thresholds = section["confidence_thresholds"]
    if not isinstance(thresholds, Mapping) or not _exact_keys(thresholds, ("high", "low")):
        violations.append((f"{path}.confidence_thresholds", "键集须恰为 high/low"))
    else:
        pair: dict[str, Any] = {}
        _threshold_violation(
            pair, thresholds["high"], f"{path}.confidence_thresholds.high", violations
        )
        _threshold_violation(
            pair, thresholds["low"], f"{path}.confidence_thresholds.low", violations
        )
        if len(violations) == before and float(pair["high"]) < float(pair["low"]):
            violations.append(
                (
                    f"{path}.confidence_thresholds.high",
                    "须 ≥ low（F56 高/低线档位语义——倒挂即形状非法）",
                )
            )
        elif len(violations) == before:
            out["confidence_thresholds"] = pair
    _int_violation(
        out,
        section["faq_expand_rounds"],
        f"{path}.faq_expand_rounds",
        FAQ_EXPAND_ROUNDS_LIMIT,
        violations,
    )
    return None if len(violations) > before else out


def validate_patch(patch: object) -> dict[str, Any]:
    """patch 校验（D2 端点 2 入参——节键白名单＋数值域，400 带字段与允许区间）。

    - 节键白名单＝合同枚举六节（order/params/rerank/citation_format/fallback/
      qa_behavior）；「七个配置节」计数含 version 元信息节（R1 证据列同口径），
      patch 白名单枚举六节为合同字面。
    - 整节替换：patch 内出现的节值必须是该节完整形状（缺键/多键即形状不符）；
      未出现的节保持现值。标量节（rerank/citation_format）规范化值＝标量本身，
      对象节规范化值＝扁平 dict。
    - 空 patch（零节）按形状不符拒——无变更的变更单无意义（版本推进无承载）。
    """
    violations: list[Violation] = []
    if not isinstance(patch, Mapping):
        violations.append(("patch", "对象形状（配置节→节值的映射）"))
        raise RetrievalParamError(violations)
    if not patch:
        violations.append(("patch", "至少一个配置节——" + "/".join(SECTION_KEYS)))
        raise RetrievalParamError(violations)
    sections: dict[str, Any] = {}
    for key, value in patch.items():
        if not isinstance(key, str) or key not in SECTION_KEYS:
            violations.append(
                (f"patch.{key}", "未知配置节——允许 " + "/".join(SECTION_KEYS))
            )
            continue
        if key == "order":
            validated = _validate_order(value, violations)
        elif key == "params":
            validated = _validate_params(value, violations)
        elif key == "fallback":
            validated = _validate_fallback(value, violations)
        elif key == "qa_behavior":
            validated = _validate_qa_behavior(value, violations)
        else:  # rerank / citation_format——标量枚举节（规范化值＝标量本身，非 dict）
            scalar: dict[str, Any] = {}
            allowed = RERANK_TIERS if key == "rerank" else CITATION_FORMATS
            _enum_violation(scalar, value, f"patch.{key}", allowed, violations)
            validated = scalar.get(key)
        if validated is not None:
            sections[key] = validated
    if violations:
        raise RetrievalParamError(violations)
    return sections


# ---------- 合同默认值（种子——D2 各卡 useState 初值/默认值表照抄） ----------


def default_config_dict() -> dict[str, Any]:
    """七节默认配置（version 元信息节走版本行列——jsonb 只存六配置节）。"""
    return {
        "order": {
            "levels": [
                {"level": 1, "enabled": True},
                {"level": 2, "enabled": True},
                {"level": 3, "enabled": True},
            ],
            "early_stop": True,
        },
        "params": {"semantic_top_k": 20, "keyword_top_k": 20, "merge": "rrf_rank", "top_n": 20},
        "rerank": "fast",
        "citation_format": "page",
        "fallback": {"strategy": "fixed", "text": DEFAULT_FALLBACK_TEXT},
        "qa_behavior": {
            "faq_direct_hit": True,
            "refuse_threshold": 0.4,  # 页面演示初值（不入不可改清单——实施批校准）
            "clarify_strategy": "ask_missing",
            "confidence_thresholds": {"high": 0.8, "low": 0.4},  # F56 已拍板口径
            "faq_expand_rounds": 3,  # 演示默认值（1–5——Owner 2026-10-01 B3 收敛）
        },
    }


# ---------- 版本号与变更单号 ----------

_VERSION_NO_RE = re.compile(r"^v(\d+)$")
_CFG_ID_RE = re.compile(r"^#CFG-(\d{8})-(\d+)$")


def next_version_no(existing: Sequence[str]) -> str:
    """版本号推进（v{n} 形——99 自然键注册表；D2 示例 v23 为演示值不构成初态）。"""
    numbers = [
        int(m.group(1)) for no in existing if (m := _VERSION_NO_RE.match(no)) is not None
    ]
    return f"v{max(numbers, default=0) + 1}"


def next_change_request_id(existing_vias: Sequence[str | None], at: datetime) -> str:
    """变更单号 #CFG-YYYYMMDD-NN（单号即 A3 变动单号——阶段 1 由本域自铸留痕）。

    A3/C3 接入批单号主铸权归 approval.submit_config_ticket（B10 单据产生口，
    99 §2.10 注）；本函数按既有 via 回链当日序号递推——种子行 via=None 不计。
    """
    today = at.strftime("%Y%m%d")
    serials = [
        int(m.group(2))
        for via in existing_vias
        if via is not None and (m := _CFG_ID_RE.match(via)) is not None and m.group(1) == today
    ]
    return f"#CFG-{today}-{max(serials, default=0) + 1:02d}"


# ---------- 配置快照（读面/落库统一形状——供 P1-08a/b 消费） ----------


@dataclass(frozen=True, slots=True)
class OrderLevel:
    """检索顺序单级（级序合同冻结 1/2/3——只有 enabled 可配）。"""

    level: int
    enabled: bool


@dataclass(frozen=True, slots=True)
class OrderSection:
    """检索顺序节（三级开关＋命中即停；S1/S3/S4~S5 检索动作级管辖——D2 行为规则 4）。"""

    levels: list[OrderLevel]
    early_stop: bool


@dataclass(frozen=True, slots=True)
class ParamsSection:
    """找候选参数节（topK/topN 下限 1；merge 两式——RRF 加权参数不入合同）。"""

    semantic_top_k: int
    keyword_top_k: int
    merge: str
    top_n: int


@dataclass(frozen=True, slots=True)
class FallbackSection:
    """兜底策略节（free 态 text 原样存储不消费——不做联动校验，合同注记）。"""

    strategy: str
    text: str


@dataclass(frozen=True, slots=True)
class ConfidenceThresholds:
    """置信度档位阈值（F56 已拍板口径——本段只承载阈值可配，不新增档位语义）。"""

    high: float
    low: float


@dataclass(frozen=True, slots=True)
class QaBehavior:
    """问答行为节（A1 作答行为在本页的承载段——五字段，P1-08a/b 消费口径）。"""

    faq_direct_hit: bool
    refuse_threshold: float
    clarify_strategy: str
    confidence_thresholds: ConfidenceThresholds
    faq_expand_rounds: int


@dataclass(frozen=True, slots=True)
class ConfigVersion:
    """配置版本元信息（D2 端点 1 version 节；updated_at 为机器时间——展示串接口层拼装）。"""

    no: str
    updated_at: datetime
    updated_by: str
    via: str | None  # 生效变动单号（#CFG-…）；种子行 None（非变更产生）


@dataclass(frozen=True, slots=True)
class ConfigSnapshot:
    """全量生效配置（version 元信息＋六配置节——端点 1 返回形状的域视图）。"""

    version: ConfigVersion
    order: OrderSection
    params: ParamsSection
    rerank: str
    citation_format: str
    fallback: FallbackSection
    qa_behavior: QaBehavior

    def sections_dict(self) -> dict[str, Any]:
        """六配置节 wire 形（jsonb 存取同形——snake_case，R1 迁移纪律）。"""
        return {
            "order": {
                "levels": [{"level": lv.level, "enabled": lv.enabled} for lv in self.order.levels],
                "early_stop": self.order.early_stop,
            },
            "params": {
                "semantic_top_k": self.params.semantic_top_k,
                "keyword_top_k": self.params.keyword_top_k,
                "merge": self.params.merge,
                "top_n": self.params.top_n,
            },
            "rerank": self.rerank,
            "citation_format": self.citation_format,
            "fallback": {"strategy": self.fallback.strategy, "text": self.fallback.text},
            "qa_behavior": {
                "faq_direct_hit": self.qa_behavior.faq_direct_hit,
                "refuse_threshold": self.qa_behavior.refuse_threshold,
                "clarify_strategy": self.qa_behavior.clarify_strategy,
                "confidence_thresholds": {
                    "high": self.qa_behavior.confidence_thresholds.high,
                    "low": self.qa_behavior.confidence_thresholds.low,
                },
                "faq_expand_rounds": self.qa_behavior.faq_expand_rounds,
            },
        }


def snapshot_from_dict(config: Mapping[str, Any], version: ConfigVersion) -> ConfigSnapshot:
    """jsonb → 快照（落库形状由 validate_patch/default_config_dict 保证——严格解析）。"""
    order_value = config["order"]
    params_value = config["params"]
    fallback_value = config["fallback"]
    qa_value = config["qa_behavior"]
    thresholds_value = qa_value["confidence_thresholds"]
    return ConfigSnapshot(
        version=version,
        order=OrderSection(
            levels=[
                OrderLevel(level=item["level"], enabled=item["enabled"])
                for item in order_value["levels"]
            ],
            early_stop=order_value["early_stop"],
        ),
        params=ParamsSection(
            semantic_top_k=params_value["semantic_top_k"],
            keyword_top_k=params_value["keyword_top_k"],
            merge=params_value["merge"],
            top_n=params_value["top_n"],
        ),
        rerank=str(config["rerank"]),
        citation_format=str(config["citation_format"]),
        fallback=FallbackSection(
            strategy=fallback_value["strategy"], text=fallback_value["text"]
        ),
        qa_behavior=QaBehavior(
            faq_direct_hit=qa_value["faq_direct_hit"],
            refuse_threshold=float(qa_value["refuse_threshold"]),
            clarify_strategy=str(qa_value["clarify_strategy"]),
            confidence_thresholds=ConfidenceThresholds(
                high=float(thresholds_value["high"]), low=float(thresholds_value["low"])
            ),
            faq_expand_rounds=int(qa_value["faq_expand_rounds"]),
        ),
    )


def merge_config(base: Mapping[str, Any], sections: Mapping[str, Any]) -> dict[str, Any]:
    """整节合并（patch 内节整节替换、未出现节保持现值——D2 端点 2 变更粒度）。

    对象节值＝扁平 dict 整体替换；标量节值（rerank/citation_format）＝标量直接
    替换——validate_patch 的规范化形状与此一一对应。
    """
    merged = {
        key: dict(value) if isinstance(value, Mapping) else value for key, value in base.items()
    }
    for key, value in sections.items():
        merged[key] = dict(value) if isinstance(value, Mapping) else value
    return merged
