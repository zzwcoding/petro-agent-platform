"""domains.semantics.exporter —— 模式派生导出器（petro/ YAML → B5 对号表消费形 JSON）。

落位裁决（tickets/phase1/README.md P1-01）：
- 放 **app 侧**（本文件）而非 ontology/tools/——①本票 ontology/ 只读纪律优先，
  导出器进 ontology/tools/ 即改动本体目录；②导出物是平台消费面（B5 抽取设置
  对号强校〔P1-05 接线〕与 A2 映射卡/白名单），消费方 import 路径在 app 侧最短；
  ③本导出器是 C1 对象与关系账（sem_object/sem_relation 投影行）与 M1 本体锚的
  对齐物化——归属 semantics 域导出面。
- 产物落 **config/**（entity_types.json / relation_types.json，进 git）——与
  database.yaml/models.yaml 同为配置资产区；不落 ontology/fixtures/（那是语义闸
  出厂集 schema-check-self 区，混入平台消费产物会搅 fixture_run 边界）。

消费形（B5 v0.2 端点 3 对号强校；A1/A2 同源）：id/name/来源 ref；
ASSOC 关系含 from/to 类型约束（聚合 id 承载，M1 头注「DDL 无外键」——引用结构
注源 R5·§5）；B3-01 起另含 endpoint_groups 全量终点组（多组时 from/to＝首组，
写入类型闸三元组合法集真源）。运行：`uv run python -m app.domains.semantics.exporter`。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.domains.semantics import domain as sem_domain
from app.domains.semantics.domain import OntologyDriftError
from app.domains.semantics.service import ONTOLOGY_PETRO_DIR, OntologyModels, load_ontology_models

CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"

# 关系账五行 × from/to 类型约束（对齐矩阵 §2.4 逐行；id＝C1 关系账行 id）：
# from/to 承载 M1 聚合 id——「DDL 无外键，引用结构全部注源 R5·§5」（m1 头注）。
# endpoints：该关系标签的合法终点组（(from聚合id, to聚合id) 列表——单一终点组
# 长度 1；B3-01 起下入/坐封双终点组）。assoc_check：逐组与 ASSOC 两端核对的
# 口径（与 endpoints 位置一一对应）——direct＝ASSOC.source→target 与终点组同向；
# reversed＝方向按 §5 语义反转（M1 ASSOC 为井 1..* 台账记录）；None＝无单一
# ASSOC 直配（受效边经受效关系实体展开）。
_RELATION_LINKS: dict[str, dict[str, Any]] = {
    "1": {
        "refs": ["ASSOC-PETRO-008"],
        "endpoints": [("AGG-PETRO-010", "AGG-PETRO-012")],
        "assoc_check": [("ASSOC-PETRO-008", "direct")],
        "note": ("C1 关系账行＝「井 —隶属→ 区块 —隶属→ 油田」链：井—隶属→区块段为 "
                 "AGG-PETRO-001.blockName 属性承载（引用化改造悬置，M1 头注）；"
                 "油田段＝ASSOC-PETRO-008（区块 AGG-PETRO-010 → 油田 AGG-PETRO-012）"),
    },
    "2": {
        "refs": ["ASSOC-PETRO-009"],
        "endpoints": [("AGG-PETRO-013", "AGG-PETRO-001")],
        "assoc_check": [("ASSOC-PETRO-009", "direct")],
        "note": ("平台—承载→井＝ASSOC-PETRO-009（裁决 b 联动增补）；引用现由 "
                 "AGG-PETRO-001.platform String 行内承载，引用化改造悬置"),
    },
    "3": {
        "refs": ["AGG-PETRO-009", "ASSOC-PETRO-006", "ASSOC-PETRO-007"],
        "endpoints": [("AGG-PETRO-001", "AGG-PETRO-001")],
        "assoc_check": None,
        "note": ("注水井—受效→油井（多对多）经受效关系实体 AGG-PETRO-009 展开；"
                 "劈分系数 Σ=1 invariant 与响应起始日随行"),
    },
    "4": {
        "refs": ["ASSOC-PETRO-004"],
        "endpoints": [("AGG-PETRO-005", "AGG-PETRO-001")],
        "assoc_check": [("ASSOC-PETRO-004", "reversed")],
        "note": ("措施—作用于→井；M1 ASSOC 方向＝井 1..* 井措施记录（wellRef），"
                 "台账行方向按 §5 语义反转承载"),
    },
    "5": {
        "refs": ["ASSOC-PETRO-005"],
        "endpoints": [("AGG-PETRO-006", "AGG-PETRO-001")],
        "assoc_check": [("ASSOC-PETRO-005", "reversed")],
        "note": "化验样—取样自→井；B5 演示配置未收录该族（B5 出入对账 3——治理批补全）",
    },
    # —— G-05 词表扩充（Owner 2026-10-05 会话裁决；note 即抽取提示词的标签说明，
    #     刻意写抽取友好白话＋报告动词同义词，治理锚引用压后）——
    # —— B3-01 终点放宽（Owner 2026-10-07 裁决）：下入/坐封合法终点在井筒外增
    #     「井」（压力计—下入→井类语义通顺边；双 ASSOC＝ASSOC-PETRO-010/015、
    #     ASSOC-PETRO-012/016，schema 单一 targetAggregate 的合法形状）——
    "6": {
        "refs": ["ASSOC-PETRO-010", "ASSOC-PETRO-015"],
        "endpoints": [("AGG-PETRO-007", "AGG-PETRO-011"), ("AGG-PETRO-007", "AGG-PETRO-001")],
        "assoc_check": [("ASSOC-PETRO-010", "direct"), ("ASSOC-PETRO-015", "direct")],
        "note": ("套管/尾管/筛管/油管/封隔器/压力计等管柱与井下设备，下到了哪口井"
                 "或哪口井的哪个井筒段（报告动词：下入/下放。"
                 "例：『7″ 筛管下入 2405～2412 米』）"),
    },
    "7": {
        "refs": ["ASSOC-PETRO-011"],
        "endpoints": [("AGG-PETRO-001", "AGG-PETRO-011")],
        "assoc_check": [("ASSOC-PETRO-011", "direct")],
        "note": ("井对哪个井筒段（射孔段）做了射孔、射开厚度/孔密多少"
                 "（报告动词：射孔/射开。例：『TCP 射孔三段合计 28 米，孔密 16 孔/米』）"),
    },
    "8": {
        "refs": ["ASSOC-PETRO-012", "ASSOC-PETRO-016"],
        "endpoints": [("AGG-PETRO-007", "AGG-PETRO-011"), ("AGG-PETRO-007", "AGG-PETRO-001")],
        "assoc_check": [("ASSOC-PETRO-012", "direct"), ("ASSOC-PETRO-016", "direct")],
        "note": ("封隔器等井下设备坐封锚定在哪口井或哪个井筒段——to 必须填井（段）名，"
                 "纯深度数字不是实体、写进 note。报告动词：坐封/验封。"
                 "例：『永久式封隔器坐封深度 1482.6 米』→ 永久式封隔器 —坐封→ 井筒"
                 "（note：坐封深度 1482.6 米）"),
    },
    "9": {
        "refs": ["ASSOC-PETRO-013"],
        "endpoints": [("AGG-PETRO-001", "AGG-PETRO-014")],
        "assoc_check": [("ASSOC-PETRO-013", "direct")],
        "note": ("注水井对哪个配注层配水、配注量多少及调整（报告动词：配注/提配。"
                 "例：『10 月配注由 180 m³/d 提至 240 m³/d』）"),
    },
    "10": {
        "refs": ["ASSOC-PETRO-014"],
        "endpoints": [("AGG-PETRO-001", "AGG-PETRO-007")],
        "assoc_check": [("ASSOC-PETRO-014", "direct")],
        "note": ("哪口井加装或更换了什么井口/井下设备（报告动词：加装/安装/更换。"
                 "例：『对 6 口套压高、功图气锁特征明显的井加装螺旋气锚』）"),
    },
}


def build_entity_types(ontology: OntologyModels) -> dict[str, Any]:
    """实体类型清单（C1 对象账 10 行 ↔ M1 聚合锚——对齐矩阵 §2.3 逐行）。"""
    m1_names = {
        str(agg["id"]): str(agg["name"]) for agg in ontology.models["m1"].get("aggregates") or []
    }
    entries: list[dict[str, Any]] = []
    for seed in sem_domain.OBJECT_SEEDS:
        ref = seed.ontology_refs[0]
        if ref not in m1_names:
            raise OntologyDriftError(f"导出器对象锚缺失：{ref} 不在 m1-object-model.yaml")
        entries.append(
            {
                "id": int(seed.row_id),
                "name": str(seed.payload["obj"]),
                "ref": ref,
                "ontology_name": m1_names[ref],  # §5 短名 vs M1 聚合名（对齐矩阵形状注记）
            }
        )
    return {
        "kind": "entity_types",
        "source": "ontology/petro/m1-object-model.yaml",
        "schema_version": ontology.manifest_version,
        "consumers": ["B5 抽取设置对号强校（B5 v0.2 端点 3）", "A2 映射卡/白名单"],
        "entity_types": entries,
    }


def build_relation_types(ontology: OntologyModels) -> dict[str, Any]:
    """关系类型清单（C1 关系账 5 行 ↔ M1 关联锚；from/to 类型约束若有则给）。

    B3-01 起终点组可为多组（endpoints 列表——下入/坐封双终点组）：导出行
    from_type/to_type＝首组（既有消费面兼容），endpoint_groups＝全量终点组
    （写入类型闸三元组合法集真源——derivatives.domain.build_legal_triples
    消费位）。assoc_check 逐组与 ASSOC 两端核对（位置一一对应）。
    """
    m1 = ontology.models["m1"]
    assocs = {str(a["id"]): a for a in m1.get("aggregate_associations") or []}
    agg_ids = {str(a["id"]) for a in m1.get("aggregates") or []}
    known: dict[str, Any] = {**assocs, **{agg_id: {} for agg_id in agg_ids}}
    entries: list[dict[str, Any]] = []
    for seed in sem_domain.RELATION_SEEDS:
        link = _RELATION_LINKS[seed.row_id]
        missing = [ref for ref in link["refs"] if ref not in known]
        if missing:
            raise OntologyDriftError(f"导出器关系锚缺失：{missing} 不在 m1-object-model.yaml")
        endpoints: list[tuple[str, str]] = [tuple(p) for p in link["endpoints"]]
        checks = link["assoc_check"]
        if checks is not None:
            if len(checks) != len(endpoints):
                raise OntologyDriftError(
                    f"关系 {seed.row_id} assoc_check 组数（{len(checks)}）与"
                    f"终点组数（{len(endpoints)}）不一致"
                )
            for (assoc_ref, direction), (f, t) in zip(checks, endpoints, strict=True):
                assoc = assocs[str(assoc_ref)]
                head, tail = str(assoc.get("sourceAggregate")), str(assoc.get("targetAggregate"))
                expected = (f, t) if direction == "direct" else (t, f)
                if (head, tail) != expected:
                    raise OntologyDriftError(
                        f"关系 {seed.row_id} 的终点组（{f}→{t}）与 {assoc_ref} 两端"
                        f"（{head}→{tail}，{direction}）不一致"
                    )
        entries.append(
            {
                "id": int(seed.row_id),
                "name": str(seed.payload["rel"]).split("→")[0].split("—")[-1].strip(),
                "refs": list(link["refs"]),
                "from_type": endpoints[0][0],
                "to_type": endpoints[0][1],
                "endpoint_groups": [
                    {"from_type": f, "to_type": t} for f, t in endpoints
                ],
                "note": link["note"],
            }
        )
    return {
        "kind": "relation_types",
        "source": "ontology/petro/m1-object-model.yaml",
        "schema_version": ontology.manifest_version,
        "consumers": ["B5 抽取设置对号强校（B5 v0.2 端点 3）", "A2 映射卡/白名单"],
        "relation_types": entries,
    }


def export(
    config_dir: Path = CONFIG_DIR, petro_dir: Path = ONTOLOGY_PETRO_DIR
) -> tuple[Path, Path]:
    """派生并落盘两份 JSON（幂等——同真源重跑字节级一致，测试即断言此性质）。"""
    ontology = load_ontology_models(petro_dir)
    outputs: dict[Path, dict[str, Any]] = {
        config_dir / "entity_types.json": build_entity_types(ontology),
        config_dir / "relation_types.json": build_relation_types(ontology),
    }
    written: list[Path] = []
    for path, payload in outputs.items():
        rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        path.write_text(rendered, encoding="utf-8")
        written.append(path)
    entity_path, relation_path = written
    return entity_path, relation_path


if __name__ == "__main__":  # pragma: no cover —— 运维入口（真源变更后重跑）
    for out in export():
        print(f"exported: {out}")
