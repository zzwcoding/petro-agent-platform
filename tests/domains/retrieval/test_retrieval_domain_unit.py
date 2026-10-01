"""retrieval 域单测——D2 合同常量/patch 校验（节键白名单＋数值域带区间）/号段语义。

合同锚：D2-搜索与回答.md v0.2（合同常量节默认值表、错误码草案 400 带字段与
允许区间、qa_behavior 五字段）；00 §14-R1（snake_case 节键迁移）。
"""

from datetime import datetime

import pytest

from app.domains.retrieval import (
    DEFAULT_FALLBACK_TEXT,
    FAQ_EXPAND_ROUNDS_LIMIT,
    SECTION_KEYS,
    TOPK_LIMIT,
    ConfigVersion,
    RetrievalParamError,
    default_config_dict,
    merge_config,
    next_change_request_id,
    next_version_no,
    snapshot_from_dict,
    validate_patch,
)


def _qa_patch(**overrides: object) -> dict[str, object]:
    qa: dict[str, object] = {
        "faq_direct_hit": True,
        "refuse_threshold": 0.4,
        "clarify_strategy": "ask_missing",
        "confidence_thresholds": {"high": 0.8, "low": 0.4},
        "faq_expand_rounds": 3,
    }
    qa.update(overrides)
    return {"qa_behavior": qa}


def _params_patch(**overrides: int | str) -> dict[str, dict[str, object]]:
    params: dict[str, object] = {
        "semantic_top_k": 20,
        "keyword_top_k": 20,
        "merge": "rrf_rank",
        "top_n": 20,
    }
    params.update(overrides)
    return {"params": params}


class TestContractDefaults:
    def test_default_config_matches_d2_constants(self) -> None:
        """合同常量照抄断言（D2 各卡 useState 初值/默认值表——验收「配置读真返五字段」）。"""
        cfg = default_config_dict()
        assert cfg["order"]["levels"] == [
            {"level": 1, "enabled": True},
            {"level": 2, "enabled": True},
            {"level": 3, "enabled": True},
        ]
        assert cfg["order"]["early_stop"] is True
        assert cfg["params"] == {
            "semantic_top_k": 20,
            "keyword_top_k": 20,
            "merge": "rrf_rank",
            "top_n": 20,
        }
        assert cfg["rerank"] == "fast"
        assert cfg["citation_format"] == "page"
        assert cfg["fallback"] == {"strategy": "fixed", "text": DEFAULT_FALLBACK_TEXT}
        qa = cfg["qa_behavior"]
        assert qa["faq_direct_hit"] is True
        assert qa["refuse_threshold"] == 0.4  # 页面演示初值（不入不可改清单）
        assert qa["clarify_strategy"] == "ask_missing"  # 现值唯一档
        assert qa["confidence_thresholds"] == {"high": 0.8, "low": 0.4}  # F56 已拍板口径
        assert qa["faq_expand_rounds"] == 3  # 演示默认值（1–5——B3 收敛来）
        assert FAQ_EXPAND_ROUNDS_LIMIT == (1, 5) and TOPK_LIMIT[0] == 1

    def test_section_keys_enumerate_six_patch_sections(self) -> None:
        """patch 白名单枚举六节（「七个配置节」计数含 version 元信息节——version 走列）。"""
        assert SECTION_KEYS == (
            "order",
            "params",
            "rerank",
            "citation_format",
            "fallback",
            "qa_behavior",
        )


class TestValidatePatch:
    def test_full_sections_pass(self) -> None:
        sections = validate_patch(
            {
                "order": {
                    "levels": [
                        {"level": 1, "enabled": False},
                        {"level": 2, "enabled": True},
                        {"level": 3, "enabled": True},
                    ],
                    "early_stop": False,
                },
                "params": {
                    "semantic_top_k": 10,
                    "keyword_top_k": 15,
                    "merge": "concat",
                    "top_n": 5,
                },
                "rerank": "compound",
                "citation_format": "code",
                "fallback": {"strategy": "free", "text": "没有依据——请换个问法。"},
                "qa_behavior": {
                    "faq_direct_hit": False,
                    "refuse_threshold": 0.5,
                    "clarify_strategy": "ask_missing",
                    "confidence_thresholds": {"high": 0.9, "low": 0.5},
                    "faq_expand_rounds": 5,
                },
            }
        )
        assert set(sections) == set(SECTION_KEYS)
        assert sections["rerank"] == "compound"
        assert sections["citation_format"] == "code"
        assert sections["params"]["merge"] == "concat"
        assert sections["qa_behavior"]["faq_expand_rounds"] == 5

    def test_single_section_passes(self) -> None:
        assert validate_patch({"rerank": "llm"}) == {"rerank": "llm"}  # 标量节规范化值＝标量

    def test_non_mapping_and_empty_patch_rejected(self) -> None:
        with pytest.raises(RetrievalParamError) as shape:
            validate_patch(["params"])  # type: ignore[arg-type]
        assert shape.value.violations[0][0] == "patch"
        with pytest.raises(RetrievalParamError) as empty:
            validate_patch({})
        assert empty.value.violations == [
            ("patch", "至少一个配置节——" + "/".join(SECTION_KEYS))
        ]

    def test_unknown_section_rejected(self) -> None:
        with pytest.raises(RetrievalParamError) as ei:
            validate_patch({"citationFormat": "code"})  # R1 迁移前拼写——未知节
        assert ("patch.citationFormat", "未知配置节——允许 " + "/".join(SECTION_KEYS)) in (
            ei.value.violations
        )

    def test_partial_and_extra_section_keys_rejected(self) -> None:
        with pytest.raises(RetrievalParamError) as partial:
            validate_patch({"params": {"semantic_top_k": 10, "keyword_top_k": 20}})
        assert "键集须恰为" in partial.value.violations[0][1]
        with pytest.raises(RetrievalParamError) as extra:
            validate_patch(_params_patch(rerank="llm"))
        assert extra.value.violations[0][0] == "patch.params"

    def test_topk_range_with_bool_guard(self) -> None:
        with pytest.raises(RetrievalParamError) as low:
            validate_patch(_params_patch(semantic_top_k=0))
        assert ("patch.params.semantic_top_k", "1–100") in low.value.violations
        with pytest.raises(RetrievalParamError) as high:
            validate_patch(_params_patch(top_n=101))
        assert ("patch.params.top_n", "1–100") in high.value.violations
        with pytest.raises(RetrievalParamError) as boolean:
            validate_patch(_params_patch(keyword_top_k=True))  # bool 冒充 int
        assert ("patch.params.keyword_top_k", "1–100") in boolean.value.violations

    def test_faq_expand_rounds_domain_1_to_5(self) -> None:
        for bad in (0, 6):
            with pytest.raises(RetrievalParamError) as ei:
                validate_patch(_qa_patch(faq_expand_rounds=bad))
            assert ("patch.qa_behavior.faq_expand_rounds", "1–5") in ei.value.violations
        ok = validate_patch(_qa_patch(faq_expand_rounds=1))
        assert ok["qa_behavior"]["faq_expand_rounds"] == 1
        ok = validate_patch(_qa_patch(faq_expand_rounds=5))
        assert ok["qa_behavior"]["faq_expand_rounds"] == 5

    def test_refuse_threshold_domain_0_to_1(self) -> None:
        for bad in (-0.1, 1.1, "0.4", True):
            with pytest.raises(RetrievalParamError) as ei:
                validate_patch(_qa_patch(refuse_threshold=bad))
            assert ("patch.qa_behavior.refuse_threshold", "0.0–1.0") in ei.value.violations
        ok = validate_patch(_qa_patch(refuse_threshold=1))
        assert ok["qa_behavior"]["refuse_threshold"] == 1.0

    def test_confidence_thresholds_pair_and_ordering(self) -> None:
        with pytest.raises(RetrievalParamError) as missing:
            validate_patch(_qa_patch(confidence_thresholds={"high": 0.8}))
        assert (
            "patch.qa_behavior.confidence_thresholds",
            "键集须恰为 high/low",
        ) in missing.value.violations
        with pytest.raises(RetrievalParamError) as inverted:
            validate_patch(_qa_patch(confidence_thresholds={"high": 0.3, "low": 0.6}))
        assert (
            "patch.qa_behavior.confidence_thresholds.high",
            "须 ≥ low（F56 高/低线档位语义——倒挂即形状非法）",
        ) in inverted.value.violations
        ok = validate_patch(_qa_patch(confidence_thresholds={"high": 0.6, "low": 0.6}))
        assert ok["qa_behavior"]["confidence_thresholds"] == {"high": 0.6, "low": 0.6}

    def test_scalar_enum_sections(self) -> None:
        with pytest.raises(RetrievalParamError) as ei:
            validate_patch({"rerank": "极速", "citation_format": "编号"})
        assert ("patch.rerank", "fast|llm|compound") in ei.value.violations
        assert ("patch.citation_format", "page|code") in ei.value.violations

    def test_fallback_strategy_and_blank_text(self) -> None:
        with pytest.raises(RetrievalParamError) as strategy:
            validate_patch({"fallback": {"strategy": "retry", "text": "x"}})
        assert ("patch.fallback.strategy", "fixed|free") in strategy.value.violations
        with pytest.raises(RetrievalParamError) as blank:
            validate_patch({"fallback": {"strategy": "fixed", "text": "  "}})
        assert ("patch.fallback.text", "非空白字符串") in blank.value.violations

    def test_order_levels_shape_and_frozen_order(self) -> None:
        with pytest.raises(RetrievalParamError) as short:
            validate_patch(
                {"order": {"levels": [{"level": 1, "enabled": True}], "early_stop": True}}
            )
        assert (
            "patch.order.levels",
            "恰为三级 1/2/3（三级顺序合同冻结，不可增删倒序）",
        ) in short.value.violations
        with pytest.raises(RetrievalParamError) as reordered:
            validate_patch(
                {
                    "order": {
                        "levels": [
                            {"level": 2, "enabled": True},
                            {"level": 1, "enabled": True},
                            {"level": 3, "enabled": True},
                        ],
                        "early_stop": True,
                    }
                }
            )
        assert ("patch.order.levels[0].level", "恒为 1（三级顺序合同冻结——顺序不可改）") in (
            reordered.value.violations
        )
        with pytest.raises(RetrievalParamError) as enabled:
            validate_patch(
                {
                    "order": {
                        "levels": [
                            {"level": 1, "enabled": "是"},
                            {"level": 2, "enabled": True},
                            {"level": 3, "enabled": True},
                        ],
                        "early_stop": True,
                    }
                }
            )
        assert ("patch.order.levels[0].enabled", "布尔") in enabled.value.violations
        with pytest.raises(RetrievalParamError) as stop:
            validate_patch(
                {
                    "order": {
                        "levels": [
                            {"level": 1, "enabled": True},
                            {"level": 2, "enabled": True},
                            {"level": 3, "enabled": True},
                        ],
                        "early_stop": 1,
                    }
                }
            )
        assert ("patch.order.early_stop", "布尔") in stop.value.violations

    def test_order_valid_toggle_only(self) -> None:
        sections = validate_patch(
            {
                "order": {
                    "levels": [
                        {"level": 1, "enabled": False},
                        {"level": 2, "enabled": False},
                        {"level": 3, "enabled": True},
                    ],
                    "early_stop": False,
                }
            }
        )
        assert sections["order"]["levels"][0] == {"level": 1, "enabled": False}
        assert sections["order"]["early_stop"] is False


class TestIdsAndMerge:
    def test_next_version_no(self) -> None:
        assert next_version_no([]) == "v1"
        assert next_version_no(["v1"]) == "v2"
        assert next_version_no(["v1", "v9", "v23"]) == "v24"

    def test_next_change_request_id_daily_serial(self) -> None:
        at = datetime(2026, 10, 2, 12, 0)
        assert next_change_request_id([None], at) == "#CFG-20261002-01"  # 种子 via=None 不计
        assert next_change_request_id(
            [None, "#CFG-20261001-09", "#CFG-20261002-01"], at
        ) == "#CFG-20261002-02"  # 跨日序号不串

    def test_merge_config_replaces_whole_sections(self) -> None:
        base = default_config_dict()
        merged = merge_config(
            base,
            {"params": {"semantic_top_k": 7, "keyword_top_k": 20, "merge": "concat", "top_n": 3}},
        )
        assert merged["params"] == {
            "semantic_top_k": 7,
            "keyword_top_k": 20,
            "merge": "concat",
            "top_n": 3,
        }
        assert merged["qa_behavior"] == base["qa_behavior"]  # 未出现节保持现值
        assert merged["rerank"] == base["rerank"]

    def test_snapshot_roundtrip(self) -> None:
        version = ConfigVersion(
            no="v1", updated_at=datetime(2026, 10, 2, 12, 0), updated_by="系统", via=None
        )
        snapshot = snapshot_from_dict(default_config_dict(), version)
        assert snapshot.sections_dict() == default_config_dict()
        assert snapshot.version is version
