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


# ---------- FX-11：出厂 few-shot 例逐一过闸自检（防再漂——对齐声明方向） ----------

# 出厂例逐例的 (from_type, to_type) 注记——few-shot 三元组字符串「from|rel|to」
# 不带类型，喂闸须按例标注；例句与标注的类型失配同样会被类型闸拦下（本表即
# 机器可读的「例 × 类型」对账，例增删/换关系时此处必须随动）。
_FEWSHOT_TYPE_BINDINGS: list[tuple[str, str]] = [
    ("平台", "井"),     # 例 1：CEP-C平台|承载|W-11井（声明＝平台—承载→井，FX-11）
    ("井", "井"),       # 例 2：Y-24井|受效|Y-21井（声明＝注水井—受效→油井，FX-11）
    ("井", "井筒"),     # 例 3：W-11井|射孔|2405～2418米井筒段
    ("设备", "井筒"),   # 例 4：精密冲缝筛管|下入|W-11井井筒
    ("设备", "井筒"),   # 例 5：永久式封隔器|坐封|W-11井井筒
]


def test_factory_fewshot_triples_all_pass_gate() -> None:
    """出厂 5 例三元组逐一喂闸（legal_triples 自装载真导出物）必须全过（FX-11）。

    红先绿后取证：改前例 1/例 2 教的形状（井—承载→平台／井—隶属→油田）在此
    断言必红（type_mismatch）——本测试钉死出厂例与本体声明终点组不再漂移。
    """
    legal = d.ontology_legal_triples()
    examples = d.DEFAULT_FEWSHOT_EXAMPLES
    assert len(examples) == len(_FEWSHOT_TYPE_BINDINGS) == 5
    cands = []
    for (sentence, triple), (from_type, to_type) in zip(
        examples, _FEWSHOT_TYPE_BINDINGS, strict=True
    ):
        from_, rel, to = triple.split(d.EDGE_KEY_SEP)
        cands.append(
            d.TripleCandidate(
                from_=from_, from_type=from_type, rel=rel, to=to, to_type=to_type,
                evidence=sentence, note=None, uncertain=False,
            )
        )
    passed, blocked = d.gate_triples(
        cands, _default_full_config(),
        chunk_text="\n".join(s for s, _ in examples),
        chunk_id="f1", report_id="r1",
        legal_triples=legal,
    )
    assert blocked == []
    # 过闸现形＝两刀归一后的键（第一刀 NFKC 折叠「～」→「~」属预期无损规整）。
    assert [e.key for e in passed] == [
        d.edge_key(*(d._normalize_entity_alias(_normalize_entity(p))
                     for p in t.split(d.EDGE_KEY_SEP)))
        for _, t in examples
    ]
    # 例 1 兼任 B2-01 别名演示的收口钉：例句别名形、三元组规范名（FX-11）。
    assert "CEP-C 生产平台" in examples[0][0]
    assert examples[0][1].startswith("CEP-C平台|")


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


# ---------- 按族携带（B1-02——report_family 过滤关系标签清单；兜底全量） ----------


def _factory_config() -> d.ExtractConfig:
    """出厂默认配置（真实本体导出物投影——按族携带测试的真数据面）。"""
    from app.infra.config import load_ontology_export

    return d.default_extract_config(
        load_ontology_export("entity_types"),
        load_ontology_export("relation_types"),
    )


class TestReportFamilyPromptCarry:
    def test_detect_report_family_rules(self) -> None:
        """标题关键词 → 文档族（规则序优先；无族词返回 None）。"""
        assert d.detect_report_family("A-W11井完井工程报告") == "completion"
        assert d.detect_report_family("渤中34-5油田躺井治理与检泵作业月报-202608") == "monthly"
        assert d.detect_report_family("渤中34-5油田三季度注水调整与生产运行分析") == "dynamic"
        assert d.detect_report_family("渤中34-8油田一季度注采调整与生产运行分析") == "dynamic"
        assert d.detect_report_family("年度综合汇报材料") is None
        assert d.detect_report_family("") is None

    def test_detect_six_corpus_report_stems(self) -> None:
        """阶段A六篇语料文件名 stem 逐一断言（FX-12③/R5-3 补钉）。

        stem＝上传文件名去扩展名＝kb ReportDetail.doc 入库形态（真数据面）。
        A/B/C 三篇在 eval/reports/；Y-21/34-8 月报/34-8 注采三篇在
        eval/drafts-q4/reports/（Y-21 与 34-8 月报两篇此前未直接断言——R5-3）。
        """
        cases: list[tuple[str, str]] = [
            ("A-W11井完井工程报告", "completion"),
            ("Y-21井完井工程报告", "completion"),
            ("B-渤中34-5油田躺井治理与检泵作业月报-202608", "monthly"),
            ("渤中34-8油田躺井治理与检泵作业月报-202701", "monthly"),
            ("C-渤中34-5油田三季度注水调整与生产运行分析", "dynamic"),
            ("渤中34-8油田一季度注采调整与生产运行分析", "dynamic"),
        ]
        for stem, family in cases:
            assert d.detect_report_family(stem) == family, stem

    def test_completion_report_carries_completion_and_cross_family(self) -> None:
        """completion 族报告：completion 组＋跨族三值组在清单，月报/动态专属组不在。

        断言锚＝关系标签清单行前缀「- 标签：」（few-shot/别名表段不含该形态，
        防 few-shot 例句词面误命中）。
        """
        prompt = d.build_extract_prompt(
            _factory_config(), section="1 基本情况", chunk_text=CHUNK,
            report_family="completion",
        )
        for rel in ("下入", "射孔", "坐封", "取样自"):  # completion 组
            assert f"- {rel}：" in prompt
        for rel in ("隶属", "承载", "作用于"):  # 跨族三值组随行（＋跨族组）
            assert f"- {rel}：" in prompt
        for rel in ("加装", "配注", "受效"):  # monthly/dynamic 专属组不携带
            assert f"- {rel}：" not in prompt

    def test_monthly_report_carries_monthly_and_cross_family(self) -> None:
        """monthly 族报告：加装（monthly）＋配注/受效（monthly, dynamic）＋跨族组。"""
        prompt = d.build_extract_prompt(
            _factory_config(), section="1 基本情况", chunk_text=CHUNK,
            report_family="monthly",
        )
        for rel in ("加装", "配注", "受效", "隶属", "承载", "作用于"):
            assert f"- {rel}：" in prompt
        for rel in ("下入", "射孔", "坐封", "取样自"):  # completion 专属组不携带
            assert f"- {rel}：" not in prompt

    def test_dynamic_report_carries_dynamic_and_cross_family(self) -> None:
        """dynamic 族报告（FX-12①/R5-3 补钉）：配注/受效（monthly, dynamic）＋跨族组。

        completion 专属组（下入/射孔/坐封/取样自）与 monthly 专属组（加装）不携带。
        """
        prompt = d.build_extract_prompt(
            _factory_config(), section="1 基本情况", chunk_text=CHUNK,
            report_family="dynamic",
        )
        for rel in ("配注", "受效", "隶属", "承载", "作用于"):
            assert f"- {rel}：" in prompt
        for rel in ("下入", "射孔", "坐封", "取样自", "加装"):  # completion/monthly 专属组不携带
            assert f"- {rel}：" not in prompt

    def test_no_family_signal_carries_full_set(self) -> None:
        """无族信号（缺省与显式 None 双形态）＝全量携带——现行为不变（兜底不收窄）。"""
        all_rels = [t.rel for t in _factory_config().relation_tags]
        assert len(all_rels) == 10  # G-05 词表扩充后 10 行
        for kwargs in ({}, {"report_family": None}):
            prompt = d.build_extract_prompt(
                _factory_config(), section="1 基本情况", chunk_text=CHUNK, **kwargs
            )
            for rel in all_rels:
                assert f"- {rel}：" in prompt

    def test_unknown_family_value_falls_back_full(self) -> None:
        """未知族值（FX-12②/R5-3 补钉）→ 族名集空 → 兜底全量携带不炸不收窄。

        值集外字符串（如拼写错 "weeky"）在 relation_types.json 无 group 命中，
        relation_names_for_family 返回空集，build_extract_prompt 按空集＝
        族标注不可判兜底全量（与旧产物部署态同一兜底路径）。
        """
        all_rels = [t.rel for t in _factory_config().relation_tags]
        prompt = d.build_extract_prompt(
            _factory_config(), section="1 基本情况", chunk_text=CHUNK,
            report_family="weeky",
        )
        for rel in all_rels:
            assert f"- {rel}：" in prompt

    def test_stale_export_without_group_falls_back_full(self, monkeypatch) -> None:
        """旧产物部署态（导出物全部行无 group）→ 兜底全量携带不收窄成零标签。"""
        import app.infra.config as infra_config

        rows = infra_config.load_ontology_export("relation_types")
        stripped = [{k: v for k, v in r.items() if k != "group"} for r in rows]
        monkeypatch.setattr(
            infra_config, "load_ontology_export",
            lambda kind, path=None: stripped,
        )
        prompt = d.build_extract_prompt(
            _factory_config(), section="1 基本情况", chunk_text=CHUNK,
            report_family="completion",
        )
        for t in _factory_config().relation_tags:
            assert f"- {t.rel}：" in prompt

    def test_family_filter_intersects_user_config(self) -> None:
        """按族过滤∩用户配置——用户已删的标签不因族过滤回场（收敛单向）。"""
        from app.infra.config import load_ontology_export

        cfg = d.default_extract_config(
            load_ontology_export("entity_types"),
            [
                r for r in load_ontology_export("relation_types")
                if r["name"] not in ("加装", "配注", "受效")
            ],
        )
        prompt = d.build_extract_prompt(
            cfg, section="1 基本情况", chunk_text=CHUNK,
            report_family="monthly",
        )
        assert "- 加装：" not in prompt  # 族内但用户未配——不回场
        assert "- 配注：" not in prompt and "- 受效：" not in prompt


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


# ---------- B2-01：实体别名归一（第二刀——别名→规范名单向收敛） ----------


def test_normalize_entity_alias_maps_alias_to_canonical() -> None:
    """正例：长形与带空格形均收敛到规范名「CEP-C平台」（Owner 2026-10-07 裁决）。"""
    assert d._normalize_entity_alias("CEP-C 生产平台") == "CEP-C平台"
    assert d._normalize_entity_alias("CEP-C 平台") == "CEP-C平台"


def test_normalize_entity_alias_canonical_and_unmatched_unchanged() -> None:
    """规范名自身恒等；映射外名字零变化（匹配失败不猜测——B2-01 红线）。

    映射外例子全取自 B2-01 确认单疑点清单（Owner 2026-10-07 裁决：维持不建
    映射不猜测）——防过度收敛。
    """
    assert d._normalize_entity_alias("CEP-C平台") == "CEP-C平台"
    assert d._normalize_entity_alias("渤中34-5油田") == "渤中34-5油田"
    assert d._normalize_entity_alias("精密冲缝筛管") == "精密冲缝筛管"
    assert d._normalize_entity_alias("电泵") == "电泵"  # 疑点：跨报告矛盾，不建映射
    assert d._normalize_entity_alias("筛管") == "筛管"  # 疑点：粒度关系非写法变体
    assert d._normalize_entity_alias("CEP-C") == "CEP-C"  # 疑点：裸码形未收编
    assert d._normalize_entity_alias("") == ""


def test_normalize_entity_alias_batch2_pairs() -> None:
    """批量二五对（Owner 2026-10-07 委托「按建议落」——B2-01 确认单 §2.2 建议列）。

    每对：别名→规范名单向收敛；规范名自身恒等。
    """
    # 对 1：CEP-D 两修饰形（生产平台/井口平台）→ 规范名钉「码＋通名」
    assert d._normalize_entity_alias("CEP-D 生产平台") == "CEP-D平台"
    assert d._normalize_entity_alias("CEP-D 井口平台") == "CEP-D平台"
    assert d._normalize_entity_alias("CEP-D平台") == "CEP-D平台"
    # 对 2：CEP-E 中心平台（语料「中心平台 CEP-E」）
    assert d._normalize_entity_alias("中心平台 CEP-E") == "CEP-E平台"
    assert d._normalize_entity_alias("CEP-E平台") == "CEP-E平台"
    # 对 3/4：油田名带空格形 → 紧凑形（few-shot/文件名形为规范）
    assert d._normalize_entity_alias("渤中 34-5 油田") == "渤中34-5油田"
    assert d._normalize_entity_alias("渤中34-5油田") == "渤中34-5油田"
    assert d._normalize_entity_alias("渤中 34-8 油田") == "渤中34-8油田"
    assert d._normalize_entity_alias("渤中34-8油田") == "渤中34-8油田"
    # 对 5：竣工表格省「式」写法 → 正文全称形（few-shot 现形）
    assert d._normalize_entity_alias("永久封隔器") == "永久式封隔器"
    assert d._normalize_entity_alias("永久式封隔器") == "永久式封隔器"


def test_normalize_entity_alias_keys_are_first_knife_stable() -> None:
    """别名键必须是第一刀归一后的形态（闸内先第一刀后第二刀，键漂移即失配）。"""
    for alias in d.ENTITY_NAME_ALIASES:
        assert _normalize_entity(alias) == alias, f"别名键未按第一刀形态登记: {alias}"


def test_gate_converges_alias_to_canonical_before_land() -> None:
    """闸内两刀串联：别名候选过闸落图即规范名（建节点/立边前收敛——B2-01）。

    legal_triples 显式传密闭集（含本测试方向）——本测试只测别名收敛语义，与
    B3-01 声明方向（承载＝平台→井）正交（R4 合并裁决）。
    """
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
        legal_triples={"承载": {("井", "平台")}},
    )
    assert len(passed) == 1
    assert passed[0].to == "CEP-C平台"  # 长形别名→规范名落图
    assert len(blocked) == 1
    assert blocked[0].to == "CEP-C平台"  # 带空格形在拦下记录中同样收敛（两刀在闸判前）


def test_gate_converges_batch2_alias_before_land() -> None:
    """批量二闸内两刀串联抽样：CEP-D 长形候选落图即规范名（收敛语义与
    CEP-C 同一函数——test_gate_converges_alias_to_canonical_before_land 已
    钉全路径，本测只钉批量二映射在闸内真实生效）。"""
    cfg = d.ExtractConfig(
        entity_types=["井", "平台"],
        relation_tags=[d.RelationTag(rel="承载")],
        custom_instructions="x",
    )
    passed, blocked = d.gate_triples(
        [d.TripleCandidate(from_="Y-21井", from_type="井", rel="承载",
                           to="CEP-D 生产平台", to_type="平台",
                           evidence="平台：CEP-D 生产平台", note="", uncertain=False)],
        cfg, chunk_text="平台：CEP-D 生产平台", chunk_id="f1", report_id="rpt-2",
        legal_triples={"承载": {("井", "平台")}},
    )
    assert len(passed) == 1
    assert passed[0].to == "CEP-D平台"  # 批量二别名→规范名落图
    assert len(blocked) == 0


def test_first_knife_semantics_untouched_by_alias_step() -> None:
    """第一刀无损语义零变：别名步之前的纯空格规整结果不受映射影响（B2-01 红线）。"""
    assert _normalize_entity("ＣＥＰ-Ｃ 平台") == "CEP-C 平台"  # 第一刀只折全半角压空白
    assert d._normalize_entity_alias(_normalize_entity("ＣＥＰ-Ｃ 平台")) == "CEP-C平台"


def test_prompt_carries_alias_table() -> None:
    """抽取提示词引用别名表（B2-01：抽取时别名两形态均可识别；批量二行同面）。"""
    prompt = d.build_extract_prompt(
        _config(), section="1 基本情况", chunk_text="平台：CEP-C 生产平台"
    )
    assert "实体别名表" in prompt
    assert "- CEP-C 生产平台 → CEP-C平台" in prompt
    assert "- CEP-C 平台 → CEP-C平台" in prompt
    assert "- CEP-D 生产平台 → CEP-D平台" in prompt
    assert "- 中心平台 CEP-E → CEP-E平台" in prompt
    assert "- 渤中 34-8 油田 → 渤中34-8油田" in prompt
    assert "- 永久封隔器 → 永久式封隔器" in prompt


def test_fewshot_platform_shape_is_canonical() -> None:
    """few-shot 出厂例现形＝规范名（B2-01 交付物③；FX-11 起平台位为声明方向
    主语——CEP-C平台|承载|W-11井，规范名现形不变、方向随本体声明收口）。"""
    assert d.DEFAULT_FEWSHOT_EXAMPLES[0][1] == "CEP-C平台|承载|W-11井"


def test_alias_map_matches_glossary_carrier() -> None:
    """承载位漂移对账：代码常量＝glossary 实体别名行（GLS-PETRO-012~017，
    B2-01 批量一＋批量二）aliases 投影合计——YAML 改动不同步代码即红。"""
    from pathlib import Path

    import yaml

    model_path = Path(__file__).resolve().parents[3] / "ontology" / "petro" / "glossary-model.yaml"
    data = yaml.safe_load(model_path.read_text(encoding="utf-8"))
    row012 = next(t for t in data["terms"] if t["id"] == "GLS-PETRO-012")
    assert row012["term"] == "CEP-C平台"
    entity_ids = [f"GLS-PETRO-{n:03d}" for n in range(12, 18)]
    expected: dict[str, str] = {}
    for gid in entity_ids:
        row = next(t for t in data["terms"] if t["id"] == gid)
        expected.update({a: row["term"] for a in row["aliases"]})
    assert expected == d.ENTITY_NAME_ALIASES
    # 反向漏网检测：凡带非空 aliases 的 GLS 行必须已被正向清单覆盖或显式豁免
    # （002/004/005/011＝术语层同义对——净产量/停产待检泵/抽油机时率/日产液，
    # 术语账消费非图实体名，不进实体别名投影）——glossary 新增实体别名行而
    # 忘扩正向清单同样红。
    waived = {"GLS-PETRO-002", "GLS-PETRO-004", "GLS-PETRO-005", "GLS-PETRO-011"}
    aliased = {t["id"] for t in data["terms"] if t.get("aliases")}
    unaccounted = aliased - set(entity_ids) - waived
    assert not unaccounted, f"glossary 新增别名行未纳入对账: {sorted(unaccounted)}"
