"""模式派生导出器单测——JSON 产物与 petro/ YAML 双向一致（P1-01 验收项）。

验收（tickets/phase1/README.md P1-01）：「导出器 JSON 与 petro/ YAML 双向一致」
——①重跑导出器与仓内 committed config/*.json 字节级一致（真源漂移即测试红）；
②每个导出 id/ref 在 m1-object-model.yaml 真实存在；③B5 演示配置五类实体/四族
关系标签全部可对号（B5 v0.2 端点 3 对号强校的消费前提）。
B1-02 起④：导出行 group＝本体 scenario 族标注透传（值与 B1-01 Owner 拍板
一一对应；无标注缺省不带键；同标签多 ASSOC 锚漂移即红）。
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from app.domains.semantics import exporter
from app.domains.semantics.service import OntologyModels, load_ontology_models

REPO_ROOT = Path(exporter.CONFIG_DIR).parent

# B1-01 Owner 拍板族标注表（13 标签中已落导出账的 10 行——检泵边 ASSOC-PETRO-017
# 未进 RELATION_SEEDS，导出账行增补登记 B6 挂账；充填/偏磨悬置不落边）。
EXPECTED_GROUPS: dict[str, list[str]] = {
    "隶属": ["completion", "monthly", "dynamic"],
    "承载": ["completion", "monthly", "dynamic"],
    "受效": ["monthly", "dynamic"],
    "作用于": ["completion", "monthly", "dynamic"],
    "取样自": ["completion"],
    "下入": ["completion"],
    "射孔": ["completion"],
    "坐封": ["completion"],
    "配注": ["monthly", "dynamic"],
    "加装": ["monthly"],
}


def test_exported_json_matches_committed_products(tmp_path: Path) -> None:
    entity_path, relation_path = exporter.export(config_dir=tmp_path)
    for generated, committed in (
        (entity_path, REPO_ROOT / "config" / "entity_types.json"),
        (relation_path, REPO_ROOT / "config" / "relation_types.json"),
    ):
        assert generated.read_text(encoding="utf-8") == committed.read_text(
            encoding="utf-8"
        ), f"{committed.name} 与真源派生结果漂移——真源变更后须重跑导出器提交"


def test_entity_and_relation_refs_resolve_in_m1_yaml() -> None:
    ontology = load_ontology_models()
    m1 = ontology.models["m1"]
    agg_ids = {str(a["id"]) for a in m1.get("aggregates") or []}
    assoc_ids = {str(a["id"]) for a in m1.get("aggregate_associations") or []}
    entity_payload = json.loads((REPO_ROOT / "config" / "entity_types.json").read_text("utf-8"))
    relation_payload = json.loads((REPO_ROOT / "config" / "relation_types.json").read_text("utf-8"))
    assert entity_payload["schema_version"] == "1.1.0"  # 钉版契约轴随产物出证
    assert len(entity_payload["entity_types"]) == 10  # C1 对象账 10 行
    for entry in entity_payload["entity_types"]:
        assert entry["ref"] in agg_ids
        m1_name = next(
            a["name"] for a in m1["aggregates"] if str(a["id"]) == entry["ref"]
        )
        assert entry["ontology_name"] == m1_name  # 名称差如实标注（对齐矩阵形状注记）
    assert len(relation_payload["relation_types"]) == 10  # C1 关系账 10 行（G-05 词表扩充）
    for entry in relation_payload["relation_types"]:
        for ref in entry["refs"]:
            assert ref in agg_ids | assoc_ids, f"关系 ref 不在 M1：{ref}"


def test_b5_demo_config_types_all_matched() -> None:
    """B5 演示配置（五类实体/四族关系标签）对号全命中——对号强校第一天可用。"""
    entities = json.loads((REPO_ROOT / "config" / "entity_types.json").read_text("utf-8"))
    relations = json.loads((REPO_ROOT / "config" / "relation_types.json").read_text("utf-8"))
    entity_names = {e["name"] for e in entities["entity_types"]}
    relation_names = {r["name"] for r in relations["relation_types"]}
    # B5 合同常量「演示库实体类型配置值」与「关系标签演示配置值」（B5 v0.2）
    assert {"井", "区块", "平台", "油田", "措施"} <= entity_names
    assert {"隶属", "承载", "受效", "作用于"} <= relation_names
    # 「化验样—取样自→井」族本体侧有承载（B5 出入对账 3——缺口在抽取配置侧）
    assert "取样自" in relation_names


def test_endpoint_groups_match_m1_assoc_endpoints() -> None:
    """终点组与 M1 ASSOC 两端核对（direct/reversed 双口径；B3-01 双 ASSOC 组）。

    每个导出行的全量终点组（endpoint_groups）与其 ASSOC 锚两端集合一致；
    from_type/to_type＝首组（既有消费面兼容）。
    """
    ontology = load_ontology_models()
    payload = exporter.build_relation_types(ontology)
    for entry in payload["relation_types"]:
        if entry["id"] == 3:
            continue  # 受效边经受效关系实体展开——无单一 ASSOC 直配
        assoc_ends = {
            frozenset((str(a["sourceAggregate"]), str(a["targetAggregate"])))
            for a in ontology.models["m1"]["aggregate_associations"]
            if str(a["id"]) in entry["refs"]
        }
        group_ends = {
            frozenset((g["from_type"], g["to_type"]))
            for g in entry["endpoint_groups"]
        }
        assert assoc_ends == group_ends, f"关系 {entry['id']} 终点组与 ASSOC 两端不一致"
        first = entry["endpoint_groups"][0]
        assert (entry["from_type"], entry["to_type"]) == (
            first["from_type"], first["to_type"]
        )


def test_run_in_and_packer_declared_dual_endpoints() -> None:
    """B3-01：下入/坐封双终点组在案（井筒＋井——Owner 2026-10-07 裁决）。

    双 ASSOC 形状（schema 单一 targetAggregate 无多终点承载位——B3-01 票面）；
    本测读 committed 产物，与 test_exported_json_matches_committed_products
    共同锁「重导出幂等＋双终点在案」。
    """
    payload = json.loads(
        (REPO_ROOT / "config" / "relation_types.json").read_text("utf-8")
    )
    rows = {r["name"]: r for r in payload["relation_types"]}
    for rel in ("下入", "坐封"):
        groups = [(g["from_type"], g["to_type"]) for g in rows[rel]["endpoint_groups"]]
        assert ("AGG-PETRO-007", "AGG-PETRO-011") in groups  # 设备→井筒（既有）
        assert ("AGG-PETRO-007", "AGG-PETRO-001") in groups  # 设备→井（B3 增补）
        assert len(rows[rel]["refs"]) == 2  # 双 ASSOC（ASSOC-PETRO-010/015、012/016）


def test_relation_rows_carry_group_from_ontology_scenario() -> None:
    """B1-02：导出行 group＝本体 scenario 透传（与 B1-01 拍板值一一对应）。

    committed 产物逐行核对拍板表；再对 build_relation_types 现算结果核对
    ①group 与该行全部 ASSOC 锚的 scenario 标注逐值一致（透传零发明）；
    ②键序 additive（endpoint_groups 之后、note 之前）；③group 不进强校
    闭世界（id/name/refs/from_type/to_type 之外的新键——B5 对号强校消费面
    只读闭世界键，build_legal_triples 不读 group，回归由 derivatives 侧
    TestDefaultExtractConfig/TestBuildLegalTriples 承担）。
    """
    committed = json.loads(
        (REPO_ROOT / "config" / "relation_types.json").read_text("utf-8")
    )
    assert {
        r["name"]: r["group"] for r in committed["relation_types"]
    } == EXPECTED_GROUPS

    ontology = load_ontology_models()
    payload = exporter.build_relation_types(ontology)
    assocs = {
        str(a["id"]): a for a in ontology.models["m1"]["aggregate_associations"]
    }
    for entry in payload["relation_types"]:
        assert entry["group"] == EXPECTED_GROUPS[entry["name"]]
        anchor_scenarios = {
            tuple(str(v) for v in assocs[ref]["scenario"])
            for ref in entry["refs"]
            if ref in assocs and assocs[ref].get("scenario")
        }
        assert anchor_scenarios == {tuple(entry["group"])}, (
            f"关系 {entry['name']} group 与 ASSOC 锚 scenario 漂移"
        )
        keys = list(entry.keys())
        assert keys.index("group") == keys.index("endpoint_groups") + 1
        assert keys.index("note") == keys.index("group") + 1


def _m1_without_group_markers(*, drop_scenario: bool) -> dict:
    """现本体 m1 深拷贝变体（group 缺省/漂移负变体构造用）。"""
    ontology = load_ontology_models()
    m1 = copy.deepcopy(ontology.models["m1"])
    if drop_scenario:
        for a in m1["aggregate_associations"]:
            a.pop("scenario", None)
    return m1


def test_group_key_omitted_when_ontology_unmarked() -> None:
    """additive 缺省形态：本体无 scenario 标注 → 行不带 group 键（键不在场）。"""
    stub = OntologyModels(
        models={"m1": _m1_without_group_markers(drop_scenario=True)},
        raw_text={},
        manifest_version="1.1.0",
    )
    payload = exporter.build_relation_types(stub)
    assert payload["relation_types"]
    assert all("group" not in entry for entry in payload["relation_types"])


def test_group_anchor_scenario_drift_raises() -> None:
    """同标签多 ASSOC 锚 scenario 漂移 → OntologyDriftError（schema.md §4
    「ASSOC 级登记、标签级消费」一致性口径——禁静默并集）。"""
    m1 = _m1_without_group_markers(drop_scenario=False)
    for a in m1["aggregate_associations"]:
        if a["id"] == "ASSOC-PETRO-015":
            a["scenario"] = ["monthly"]  # 与 010（[completion]）同属下入标签——漂移
    stub = OntologyModels(models={"m1": m1}, raw_text={}, manifest_version="1.1.0")
    with pytest.raises(exporter.OntologyDriftError, match="scenario 不一致"):
        exporter.build_relation_types(stub)
