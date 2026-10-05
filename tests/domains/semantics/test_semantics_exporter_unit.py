"""模式派生导出器单测——JSON 产物与 petro/ YAML 双向一致（P1-01 验收项）。

验收（tickets/phase1/README.md P1-01）：「导出器 JSON 与 petro/ YAML 双向一致」
——①重跑导出器与仓内 committed config/*.json 字节级一致（真源漂移即测试红）；
②每个导出 id/ref 在 m1-object-model.yaml 真实存在；③B5 演示配置五类实体/四族
关系标签全部可对号（B5 v0.2 端点 3 对号强校的消费前提）。
"""

from __future__ import annotations

import json
from pathlib import Path

from app.domains.semantics import exporter
from app.domains.semantics.service import load_ontology_models

REPO_ROOT = Path(exporter.CONFIG_DIR).parent


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


def test_from_to_constraints_match_m1_assoc_endpoints() -> None:
    """from/to 类型约束与 M1 ASSOC 两端核对（direct/reversed 双口径）。"""
    ontology = load_ontology_models()
    payload = exporter.build_relation_types(ontology)
    for entry in payload["relation_types"]:
        if entry["id"] == 3:
            continue  # 受效边经受效关系实体展开——无单一 ASSOC 直配
        assoc = next(
            a
            for a in ontology.models["m1"]["aggregate_associations"]
            if str(a["id"]) in entry["refs"]
        )
        head, tail = str(assoc["sourceAggregate"]), str(assoc["targetAggregate"])
        assert {head, tail} == {entry["from_type"], entry["to_type"]}
