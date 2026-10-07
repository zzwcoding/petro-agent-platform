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

# 闸单测密闭合法集（与 _config 对齐的桩声明——非本体导出物；本体导出物全组合
# 枚举与非法样例在 TestGateOntologySeeds 走缺省真源装载真跑）。
_LEGAL: dict[str, set[tuple[str, str]]] = {
    "隶属": {("井", "区块")},
    "承载": {("井", "平台")},
}


class TestGateTriples:
    def test_passing_edge_gates_through(self) -> None:
        passed, blocked = d.gate_triples(
            [_cand()], _config(), legal_triples=_LEGAL,
            chunk_text=CHUNK, chunk_id="f1", report_id="r1",
        )
        assert len(passed) == 1 and blocked == []
        assert passed[0].key == "N-02|隶属|渤南"
        assert passed[0].chunk_id == "f1"

    def test_type_gate_type_mismatch(self) -> None:
        passed, blocked = d.gate_triples(
            [_cand(rel="取样自"), _cand(to_type="化验样")], _config(),
            legal_triples=_LEGAL,
            chunk_text=CHUNK, chunk_id="f1", report_id="r1",
        )
        assert passed == []
        assert all(b.reason_code == "type_mismatch" for b in blocked)
        assert "类型闸" in blocked[0].reason

    def test_evidence_gate_no_evidence(self) -> None:
        passed, blocked = d.gate_triples(
            [_cand(evidence=""), _cand(evidence="原文里没有这句话"),
             _cand(evidence="位于渤南 区块 CEP-A 平台")],
            _config(), legal_triples=_LEGAL, chunk_text=CHUNK, chunk_id="f1", report_id="r1",
        )
        # 空依据/非原文句 → no_evidence；跨空白差异归一后命中 → 过闸。
        assert len(passed) == 1 and len(blocked) == 2
        assert {b.reason_code for b in blocked} == {"no_evidence"}

    def test_uncertain_gate_abstain(self) -> None:
        passed, blocked = d.gate_triples(
            [_cand(uncertain=True)], _config(),
            legal_triples=_LEGAL, chunk_text=CHUNK, chunk_id="f1", report_id="r1",
        )
        assert passed == []
        assert blocked[0].reason_code == "uncertain"
        assert "弃权" in blocked[0].reason

    def test_gate_order_type_before_evidence_before_uncertain(self) -> None:
        # 类型闸优先于依据闸、依据闸优先于弃权闸（铁律分解顺序）。
        _, blocked = d.gate_triples(
            [_cand(rel="未知"), _cand(evidence="不在原文", uncertain=True)],
            _config(), legal_triples=_LEGAL, chunk_text=CHUNK, chunk_id="f1", report_id="r1",
        )
        assert blocked[0].reason_code == "type_mismatch"
        assert blocked[1].reason_code == "no_evidence"

    def test_malformed_candidate_skipped_silently(self) -> None:
        passed, blocked = d.gate_triples(
            [_cand(from_=""), _cand(rel="")], _config(),
            legal_triples=_LEGAL, chunk_text=CHUNK, chunk_id="f1", report_id="r1",
        )
        assert passed == [] and blocked == []


# ---------- 类型闸三元组严格匹配（B3-01——对配必须命中声明终点组） ----------


class TestGateTripleStrict:
    def test_pairing_miss_rejected_with_members_ok(self) -> None:
        # 成员各自在清单、对配未命中声明终点组 → 拦（严格匹配新增面）。
        passed, blocked = d.gate_triples(
            [_cand(to="CEP-A", to_type="平台")], _config(), legal_triples=_LEGAL,
            chunk_text=CHUNK, chunk_id="f1", report_id="r1",
        )
        assert passed == []
        assert blocked[0].reason_code == "type_mismatch"

    def test_member_check_not_subsumed_by_pairing(self) -> None:
        # 对配合法但类型不在该库清单——成员检查仍独立生效（库清单外类型不许自创）。
        passed, blocked = d.gate_triples(
            [_cand(from_type="措施")], _config(),
            legal_triples={"隶属": {("措施", "区块")}},
            chunk_text=CHUNK, chunk_id="f1", report_id="r1",
        )
        assert passed == []
        assert blocked[0].reason_code == "type_mismatch"

    def test_dual_endpoint_group_either_hits(self) -> None:
        # 双终点组（B3 下入/坐封）任一命中即放行——井筒/井两形态。
        cfg = d.ExtractConfig(
            entity_types=["井", "井筒", "设备"],
            relation_tags=[d.RelationTag(rel="下入")],
            custom_instructions="x",
        )
        legal = {"下入": {("设备", "井筒"), ("设备", "井")}}
        passed, blocked = d.gate_triples(
            [d.TripleCandidate(from_="压力计", from_type="设备", rel="下入",
                               to="W-11井", to_type="井",
                               evidence="压力计下入 W-11 井", note=None, uncertain=False),
             d.TripleCandidate(from_="精密冲缝筛管", from_type="设备", rel="下入",
                               to="W-11井井筒", to_type="井筒",
                               evidence="筛管下入 W-11 井井筒", note=None, uncertain=False)],
            cfg, legal_triples=legal,
            chunk_text="压力计下入 W-11 井，筛管下入 W-11 井井筒",
            chunk_id="f1", report_id="r1",
        )
        assert blocked == [] and len(passed) == 2


class TestBuildLegalTriples:
    """AGG id ↔ 实体类型名映射口径（票内定案）：entity_types.json 行 ref（M1
    聚合 id）↔ name（抽取类型词表名——§5 短名，非 ontology_name 全名）。"""

    def test_maps_agg_ids_to_type_names_from_real_export(self) -> None:
        from app.infra.config import load_ontology_export

        legal = d.build_legal_triples(
            load_ontology_export("entity_types"),
            load_ontology_export("relation_types"),
        )
        # B3-01 双终点组：下入/坐封＝设备→井筒＋设备→井（Owner 2026-10-07 裁决）
        assert legal["下入"] == frozenset({("设备", "井筒"), ("设备", "井")})
        assert legal["坐封"] == frozenset({("设备", "井筒"), ("设备", "井")})
        assert legal["隶属"] == frozenset({("区块", "油田")})
        assert legal["承载"] == frozenset({("平台", "井")})
        assert legal["受效"] == frozenset({("井", "井")})
        assert legal["射孔"] == frozenset({("井", "井筒")})
        assert legal["取样自"] == frozenset({("化验样", "井")})
        assert legal["作用于"] == frozenset({("措施", "井")})
        assert legal["配注"] == frozenset({("井", "配注层")})
        assert legal["加装"] == frozenset({("井", "设备")})

    def test_row_without_endpoint_groups_falls_back_to_from_to(self) -> None:
        legal = d.build_legal_triples(
            [{"ref": "AGG-PETRO-001", "name": "井"}],
            [{"name": "承载", "from_type": "AGG-PETRO-001", "to_type": "AGG-PETRO-001"}],
        )
        assert legal == {"承载": frozenset({("井", "井")})}

    def test_unknown_agg_id_raises_loud(self) -> None:
        with pytest.raises(ValueError, match="漂移"):
            d.build_legal_triples(
                [{"ref": "AGG-PETRO-001", "name": "井"}],
                [{"name": "下入", "from_type": "AGG-PETRO-007", "to_type": "AGG-PETRO-011"}],
            )

    def test_row_missing_endpoints_raises_loud(self) -> None:
        with pytest.raises(ValueError, match="终点组"):
            d.build_legal_triples(
                [{"ref": "AGG-PETRO-001", "name": "井"}],
                [{"name": "下入"}],
            )


# ---------- B3-01 验收①：本体种子全部既有边过闸零误杀（缺省真源装载真跑） ----------


def _default_full_config() -> d.ExtractConfig:
    """出厂默认配置（本体对号表投影——生产形态），供全组合枚举用。"""
    from app.infra.config import load_ontology_export

    return d.default_extract_config(
        load_ontology_export("entity_types"),
        load_ontology_export("relation_types"),
    )


class TestGateOntologySeeds:
    def test_all_declared_combinations_pass(self) -> None:
        """10 关系 × 各自声明终点组（8 单终点＋下入/坐封双终点＝12 对配）逐一
        过闸零误杀——legal_triples 缺省＝本体导出物（生产缺省路径同测）。"""
        legal = d.ontology_legal_triples()
        combos = [(rel, pair) for rel, pairs in legal.items() for pair in sorted(pairs)]
        assert len(combos) == 12
        cands = [
            d.TripleCandidate(
                from_=f"F{i}", from_type=f, rel=rel, to=f"T{i}", to_type=t,
                evidence="支持原句在切片里", note=None, uncertain=False,
            )
            for i, (rel, (f, t)) in enumerate(combos)
        ]
        passed, blocked = d.gate_triples(
            cands, _default_full_config(),
            chunk_text="支持原句在切片里", chunk_id="f1", report_id="r1",
        )
        assert blocked == []
        assert len(passed) == 12

    def test_undeclared_pairs_rejected(self) -> None:
        """非法三元组样例被拒（验收②≥3 例）：类型对配不在声明终点组——
        reason_code 零变（type_mismatch）。"""
        legal = d.ontology_legal_triples()
        illegal = [
            ("井", "坐封", "油田"),     # 票面样例：井—坐封→油田
            ("设备", "受效", "井筒"),   # 票面样例族：设备—受效→井筒
            ("井", "射孔", "设备"),
            ("平台", "下入", "井筒"),
        ]
        # 断言自洽防护：四个 rel 都是声明内关系、四对配都不在声明组内
        for f, rel, t in illegal:
            assert rel in legal and (f, t) not in legal[rel]
        cands = [
            d.TripleCandidate(
                from_=f"F{i}", from_type=f, rel=rel, to=f"T{i}", to_type=t,
                evidence="支持原句在切片里", note=None, uncertain=False,
            )
            for i, (f, rel, t) in enumerate(illegal)
        ]
        passed, blocked = d.gate_triples(
            cands, _default_full_config(),
            chunk_text="支持原句在切片里", chunk_id="f1", report_id="r1",
        )
        assert passed == []
        assert [b.reason_code for b in blocked] == ["type_mismatch"] * len(illegal)
        assert all("类型闸" in b.reason for b in blocked)


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
        cfg, legal_triples={"下入": {("设备", "井")}},
        chunk_text="筛管下入 W-11 井", chunk_id="f1", report_id="rpt-1",
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
