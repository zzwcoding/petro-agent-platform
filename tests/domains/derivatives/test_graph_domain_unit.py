"""B5 graph 子域纯语义单测（domain.py——无 DB/LLM/框架，B1 红线内）。"""

import pytest

from app.domains.derivatives import domain as d
from app.domains.derivatives.domain import _normalize_entity


def _config(**overrides: object) -> d.ExtractConfig:
    base = dict(
        entity_types=["井", "区块", "平台"],
        relation_tags=[
            d.RelationTag(rel="隶属", example="N-02 —隶属→ 渤南", desc="井属于哪个区块"),
            d.RelationTag(rel="承载", desc="井装在哪个平台上"),
        ],
        custom_instructions="关系必须原文有依据",
        few_shot_examples=[d.FewShotPair(sentence="N-02 井隶属渤南区块。",
                                         triple="N-02 —隶属→ 渤南")],
    )
    base.update(overrides)  # type: ignore[arg-type]
    return d.ExtractConfig(**base)  # type: ignore[arg-type]


# ---------- ExtractConfig 形状校验（端点 3 校验清单——400） ----------


class TestConfigFromPayload:
    def test_roundtrip(self) -> None:
        cfg = d.config_from_payload({
            "entity_types": ["井", " 区块 "],
            "relation_tags": [{"rel": "隶属", "example": "e", "desc": "d"}],
            "custom_instructions": "指令",
            "few_shot_examples": [{"sentence": "s", "triple": "t"}],
        })
        assert cfg.entity_types == ["井", "区块"]
        assert cfg.relation_tags[0].rel == "隶属"
        assert cfg.few_shot_examples[0].triple == "t"
        assert cfg.as_snapshot()["custom_instructions"] == "指令"

    def test_missing_section_rejected(self) -> None:
        with pytest.raises(d.GraphParamError) as ei:
            d.config_from_payload({"entity_types": ["井"]})
        assert "缺段" in str(ei.value)

    def test_empty_entity_types_rejected(self) -> None:
        with pytest.raises(d.GraphParamError):
            d.config_from_payload({
                "entity_types": [], "relation_tags": [], "custom_instructions": "",
            })

    def test_tag_missing_rel_rejected(self) -> None:
        with pytest.raises(d.GraphParamError):
            d.config_from_payload({
                "entity_types": ["井"], "relation_tags": [{"example": "e"}],
                "custom_instructions": "",
            })

    def test_tag_duplicate_rel_rejected(self) -> None:
        with pytest.raises(d.GraphParamError):
            d.config_from_payload({
                "entity_types": ["井"],
                "relation_tags": [{"rel": "隶属"}, {"rel": "隶属"}],
                "custom_instructions": "",
            })


# ---------- 对号强校（端点 3——P1-01 导出物接线） ----------


class TestOntologyCheck:
    def test_aligned_passes(self) -> None:
        mismatches = d.ontology_check(
            _config(),
            entity_catalog=["井", "区块", "平台", "油田"],
            relation_catalog=["隶属", "承载"],
        )
        assert mismatches == []

    def test_uncollected_rejected_with_nearest(self) -> None:
        mismatches = d.ontology_check(
            _config(entity_types=["井", "井筒", "归属"]),
            relation_catalog=["隶属", "承载"],
            entity_catalog=["井", "井筒", "区块"],
        )
        values = {m["value"]: m for m in mismatches}
        assert set(values) == {"归属"}
        item = values["归属"]
        assert item["kind"] == "entity_type"
        assert item["nearest"]  # 给出最接近台账词条

    def test_uncollected_relation_family_not_admitted(self) -> None:
        # 未收录关系族（如「取样自」缺族时自创标签）——对不上就是拒存。
        mismatches = d.ontology_check(
            _config(entity_types=["井", "化验样"],
                    relation_tags=[d.RelationTag(rel="取样于")]),
            entity_catalog=["井", "化验样"],
            relation_catalog=["隶属", "承载", "受效", "作用于"],
        )
        assert [m["kind"] for m in mismatches] == ["relation_tag"]

    def test_nearest_word_always_suggests(self) -> None:
        assert d.nearest_word("隶属", ["隶属", "承载"]) == "隶属"
        # 零相似也取最高项（非空目录恒有建议——对号明细第三列不空）。
        assert d.nearest_word("全完不存在", ["井", "区块"]) in ("井", "区块")
        assert d.nearest_word("任意", []) == ""


# ---------- 边唯一键（B5 合同冻结 from|rel|to） ----------


def test_edge_key_frozen_shape() -> None:
    assert d.edge_key("N-02", "隶属", "渤南") == "N-02|隶属|渤南"


# ---------- 三道闸（铁律合同常量——类型闸/依据闸/弃权闸） ----------


def _cand(**kw: object) -> d.TripleCandidate:
    base = dict(
        from_="N-02", from_type="井", rel="隶属", to="渤南", to_type="区块",
        evidence="位于渤南区块 CEP-A 平台", note=None, uncertain=False,
    )
    base.update(kw)  # type: ignore[arg-type]
    return d.TripleCandidate(**base)  # type: ignore[arg-type]


CHUNK = "1 基本情况\nN-02 井（渤中28-1-N2）位于渤南区块 CEP-A 平台，井别采油。"


class TestGateTriples:
    def test_passing_edge_gates_through(self) -> None:
        passed, blocked = d.gate_triples(
            [_cand()], _config(), chunk_text=CHUNK, chunk_id="f1", report_id="r1"
        )
        assert len(passed) == 1 and blocked == []
        assert passed[0].key == "N-02|隶属|渤南"
        assert passed[0].chunk_id == "f1"

    def test_type_gate_type_mismatch(self) -> None:
        passed, blocked = d.gate_triples(
            [_cand(rel="取样自"), _cand(to_type="化验样")], _config(),
            chunk_text=CHUNK, chunk_id="f1", report_id="r1",
        )
        assert passed == []
        assert all(b.reason_code == "type_mismatch" for b in blocked)
        assert "类型闸" in blocked[0].reason

    def test_evidence_gate_no_evidence(self) -> None:
        passed, blocked = d.gate_triples(
            [_cand(evidence=""), _cand(evidence="原文里没有这句话"),
             _cand(evidence="位于渤南 区块 CEP-A 平台")],
            _config(), chunk_text=CHUNK, chunk_id="f1", report_id="r1",
        )
        # 空依据/非原文句 → no_evidence；跨空白差异归一后命中 → 过闸。
        assert len(passed) == 1 and len(blocked) == 2
        assert {b.reason_code for b in blocked} == {"no_evidence"}

    def test_uncertain_gate_abstain(self) -> None:
        passed, blocked = d.gate_triples(
            [_cand(uncertain=True)], _config(),
            chunk_text=CHUNK, chunk_id="f1", report_id="r1",
        )
        assert passed == []
        assert blocked[0].reason_code == "uncertain"
        assert "弃权" in blocked[0].reason

    def test_gate_order_type_before_evidence_before_uncertain(self) -> None:
        # 类型闸优先于依据闸、依据闸优先于弃权闸（铁律分解顺序）。
        _, blocked = d.gate_triples(
            [_cand(rel="未知"), _cand(evidence="不在原文", uncertain=True)],
            _config(), chunk_text=CHUNK, chunk_id="f1", report_id="r1",
        )
        assert blocked[0].reason_code == "type_mismatch"
        assert blocked[1].reason_code == "no_evidence"

    def test_malformed_candidate_skipped_silently(self) -> None:
        passed, blocked = d.gate_triples(
            [_cand(from_=""), _cand(rel="")], _config(),
            chunk_text=CHUNK, chunk_id="f1", report_id="r1",
        )
        assert passed == [] and blocked == []


# ---------- 抽取输出宽容解析与提示词 ----------


class TestParseTriples:
    def test_plain_json(self) -> None:
        rows = d.parse_triples(
            '[{"from":"N-02","from_type":"井","rel":"隶属","to":"渤南",'
            '"to_type":"区块","evidence":"e","note":"批次","uncertain":false}]'
        )
        assert rows[0].note == "批次" and rows[0].uncertain is False

    def test_fenced_json_and_prose(self) -> None:
        raw = "好的，结果如下：\n```json\n[{\"from\":\"a\",\"from_type\":\"井\"," \
              "\"rel\":\"隶属\",\"to\":\"b\",\"to_type\":\"区块\",\"evidence\":\"e\"}]\n```"
        rows = d.parse_triples(raw)
        assert len(rows) == 1 and rows[0].from_ == "a"

    def test_unparseable_returns_empty(self) -> None:
        assert d.parse_triples("切片里没有可抽的关系。") == []
        assert d.parse_triples("") == []

    def test_missing_fields_projected_lenient(self) -> None:
        rows = d.parse_triples('[{"from":"a"}]')
        assert rows[0].rel == ""  # 残缺候选由 gate_triples 跳过


class TestBuildExtractPrompt:
    def test_four_sections_in_prompt(self) -> None:
        prompt = d.build_extract_prompt(
            _config(), section="1 基本情况", chunk_text=CHUNK
        )
        assert "井、区块、平台" in prompt
        assert "隶属" in prompt and "井属于哪个区块" in prompt
        assert "N-02 井隶属渤南区块。 → N-02 —隶属→ 渤南" in prompt
        assert "关系必须原文有依据" in prompt
        assert CHUNK in prompt
        assert '"evidence"' in prompt  # 依据闸输出协议
        assert '"uncertain"' in prompt  # 弃权闸输出协议


# ---------- 起草解析（LLM 起草三源辅助③） ----------


class TestParseDraft:
    def test_two_lines(self) -> None:
        assert d.parse_draft("N-02 井隶属渤南区块。\nN-02 —隶属→ 渤南") == (
            "N-02 井隶属渤南区块。",
            "N-02 —隶属→ 渤南",
        )

    def test_unparseable_raises(self) -> None:
        with pytest.raises(d.GraphParamError):
            d.parse_draft("只有一行")


# ---------- 出厂默认（本体对号表投影——与 P1-01 导出物对号自洽） ----------


class TestDefaultExtractConfig:
    def test_default_from_ontology_export(self) -> None:
        from app.infra.config import load_ontology_export

        cfg = d.default_extract_config(
            load_ontology_export("entity_types"),
            load_ontology_export("relation_types"),
        )
        assert cfg.entity_types == ["井", "井筒", "区块", "油田", "平台", "设备",
                                    "措施", "化验样", "受效关系", "配注层"]
        assert [t.rel for t in cfg.relation_tags] == [
            "隶属", "承载", "受效", "作用于", "取样自",
            "下入", "射孔", "坐封", "配注", "加装",  # G-05 词表扩充
        ]
        assert cfg.custom_instructions == d.DEFAULT_CUSTOM_INSTRUCTIONS
        # 对号自洽：默认值原样保存即过强校（出厂默认不卡对号闸）。
        assert d.ontology_check(
            cfg,
            entity_catalog=cfg.entity_types,
            relation_catalog=[t.rel for t in cfg.relation_tags],
        ) == []

    def test_f40_contract_constant_recorded(self) -> None:
        # F40 出厂默认 11 类通用实体——合同常量留档（差异登记：本仓出厂默认落
        # 本体对号表投影，理由见 default_extract_config 注记）。
        assert len(d.F40_DEFAULT_ENTITY_TYPES) == 11
        assert d.F40_DEFAULT_ENTITY_TYPES[0] == "Person"


# ---------- 快照投影（extract_snapshot——confirm 时刻定型形状） ----------


class TestSnapshotRoundtrip:
    def test_snapshot_roundtrip(self) -> None:
        snapshot = _config().as_snapshot()
        assert set(snapshot) == {
            "entity_types", "relation_tags", "few_shot_examples",
            "custom_instructions",
        }
        cfg = d.config_from_snapshot(snapshot)
        assert cfg == _config()


# ---------- G-03：实体名归一＋few-shot 出厂（词表质量第一刀） ----------


def test_normalize_entity_merges_variants() -> None:
    """空格/全半角/「X 井」变体归一——同实体落点合并（B5 截图双链直接成因）。"""

    assert _normalize_entity("W-11 井") == "W-11井"
    assert _normalize_entity("W-11井") == "W-11井"
    assert _normalize_entity(" 1482.6米 ") == "1482.6米"
    assert _normalize_entity("ＣＥＰ-Ｃ 平台") == "CEP-C 平台"  # 全半角折叠；内部空格保留


def test_gate_normalizes_entity_names_before_land(monkeypatch: pytest.MonkeyPatch) -> None:
    """候选实体名在闸内先归一再判——空格变体与规范名同点落图。"""
    cfg = d.ExtractConfig(
        entity_types=["井", "设备"],
        relation_tags=[d.RelationTag(rel="下入")],
        custom_instructions="x",
    )
    passed, _blocked = d.gate_triples(
        [d.TripleCandidate(from_="精密冲缝筛管", from_type="设备", rel="下入",
                         to="W-11 井", to_type="井",
                         evidence="筛管下入 W-11 井", note="", uncertain=False)],
        cfg, chunk_text="筛管下入 W-11 井", chunk_id="f1", report_id="rpt-1",
    )
    assert len(passed) == 1
    assert passed[0].to == "W-11井"


def test_default_extract_config_has_fewshot_and_entity_guidance() -> None:
    """G-03：出厂 few-shot 5 例＋指令含实体名规范指引（词表质量第一刀）。"""
    from app.domains.derivatives import domain as d
    from app.domains.derivatives.service import _ontology_catalogs

    cfg = d.default_extract_config(*_ontology_catalogs())
    assert len(cfg.few_shot_examples) == 5
    assert all(p.sentence and p.triple for p in cfg.few_shot_examples)
    assert "井号不含空格" in cfg.custom_instructions
    assert "纯数字与深度不是实体" in cfg.custom_instructions


# ---------- B2-01：实体别名归一（第二刀——别名→规范名单向收敛） ----------


def test_normalize_entity_alias_maps_alias_to_canonical() -> None:
    """正例：长形与带空格形均收敛到规范名「CEP-C平台」（Owner 2026-10-07 裁决）。"""
    assert d._normalize_entity_alias("CEP-C 生产平台") == "CEP-C平台"
    assert d._normalize_entity_alias("CEP-C 平台") == "CEP-C平台"


def test_normalize_entity_alias_canonical_and_unmatched_unchanged() -> None:
    """规范名自身恒等；映射外名字零变化（匹配失败不猜测——B2-01 红线）。"""
    assert d._normalize_entity_alias("CEP-C平台") == "CEP-C平台"
    assert d._normalize_entity_alias("渤中34-5油田") == "渤中34-5油田"
    assert d._normalize_entity_alias("精密冲缝筛管") == "精密冲缝筛管"
    assert d._normalize_entity_alias("CEP-D 井口平台") == "CEP-D 井口平台"  # 未裁决不猜
    assert d._normalize_entity_alias("") == ""


def test_normalize_entity_alias_keys_are_first_knife_stable() -> None:
    """别名键必须是第一刀归一后的形态（闸内先第一刀后第二刀，键漂移即失配）。"""
    for alias in d.ENTITY_NAME_ALIASES:
        assert _normalize_entity(alias) == alias, f"别名键未按第一刀形态登记: {alias}"


def test_gate_converges_alias_to_canonical_before_land() -> None:
    """闸内两刀串联：别名候选过闸落图即规范名（建节点/立边前收敛——B2-01）。"""
    cfg = d.ExtractConfig(
        entity_types=["井", "平台"],
        relation_tags=[d.RelationTag(rel="承载")],
        custom_instructions="x",
    )
    passed, blocked = d.gate_triples(
        [d.TripleCandidate(from_="W-11井", from_type="井", rel="承载",
                          to="CEP-C 生产平台", to_type="平台",
                          evidence="平台：CEP-C 生产平台", note="", uncertain=False),
         d.TripleCandidate(from_="W-12井", from_type="井", rel="承载",
                          to="CEP-C 平台", to_type="平台",
                          evidence="依据不在原文", note="", uncertain=False)],
        cfg, chunk_text="平台：CEP-C 生产平台", chunk_id="f1", report_id="rpt-1",
    )
    assert len(passed) == 1
    assert passed[0].to == "CEP-C平台"  # 长形别名→规范名落图
    assert len(blocked) == 1
    assert blocked[0].to == "CEP-C平台"  # 带空格形在拦下记录中同样收敛（两刀在闸判前）


def test_first_knife_semantics_untouched_by_alias_step() -> None:
    """第一刀无损语义零变：别名步之前的纯空格规整结果不受映射影响（B2-01 红线）。"""
    assert _normalize_entity("ＣＥＰ-Ｃ 平台") == "CEP-C 平台"  # 第一刀只折全半角压空白
    assert d._normalize_entity_alias(_normalize_entity("ＣＥＰ-Ｃ 平台")) == "CEP-C平台"


def test_prompt_carries_alias_table() -> None:
    """抽取提示词引用别名表（B2-01：抽取时别名两形态均可识别）。"""
    prompt = d.build_extract_prompt(
        _config(), section="1 基本情况", chunk_text="平台：CEP-C 生产平台"
    )
    assert "实体别名表" in prompt
    assert "- CEP-C 生产平台 → CEP-C平台" in prompt
    assert "- CEP-C 平台 → CEP-C平台" in prompt


def test_fewshot_platform_shape_is_canonical() -> None:
    """few-shot 出厂例现形＝规范名（Owner 裁决后零改动核对——B2-01 交付物③）。"""
    assert d.DEFAULT_FEWSHOT_EXAMPLES[0][1] == "W-11井|承载|CEP-C平台"


def test_alias_map_matches_glossary_carrier() -> None:
    """承载位漂移对账：代码常量＝glossary GLS-PETRO-012 aliases 投影（B2-01）。"""
    from pathlib import Path

    import yaml

    model_path = Path(__file__).resolve().parents[3] / "ontology" / "petro" / "glossary-model.yaml"
    data = yaml.safe_load(model_path.read_text(encoding="utf-8"))
    row = next(t for t in data["terms"] if t["id"] == "GLS-PETRO-012")
    assert row["term"] == "CEP-C平台"
    assert {a: row["term"] for a in row["aliases"]} == d.ENTITY_NAME_ALIASES
