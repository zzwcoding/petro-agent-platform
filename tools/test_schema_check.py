#!/usr/bin/env python3
"""schema_check.py 的单测（stdlib unittest + PyYAML，TDD 先行）。

合成两模型（M1/M2）迷你 schema 走端到端，AC1–7 各一条（AC 对应 specs/schema_check.md 断言表）；
票 10 增 GLS 套件（GlossaryModel）；票 11 增 L2 一致性对套件（ConsistencyPairs，
CONS-AC1–3 对应 tickets/11-一致性对核验.md AC 表，基座扩到 M5/M6/M7）；
票 13 增必填闸套件（RequiredFields：L1 required-field 元素级闸）与 AC6 反向套件
（MissingModelFile：L4 missing-model-file + omittedModels 豁免）。
"""

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import schema_check as sc


def quiet_main(argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = sc.main(argv)
    return rc


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


REGISTRY = {
    "version": 1,
    "models": {
        "M1": {
            "name": "对象模型", "yamlFile": "m1-object-model.yaml",
            "modelType": "OBJECT", "camp": "business-core",
            "consumers": ["runtime", "build"],
            "profiles": ["full", "mini"],
            "dependsOn": [], "lockedFields": {},
        },
        "M2": {
            "name": "行为模型", "yamlFile": "m2-behavior-model.yaml",
            "modelType": "BEHAVIOR", "camp": "business-core",
            "consumers": ["runtime", "build"],
            "profiles": ["full"],
            "dependsOn": ["M1"], "lockedFields": {},
        },
        "GLS": {
            "name": "术语模型", "yamlFile": "glossary-model.yaml",
            "modelType": "GLOSSARY", "camp": "business-core",
            "consumers": ["runtime", "build"],
            "profiles": ["full"],
            "dependsOn": ["M1"], "lockedFields": {},
        },
    },
}

DEPS = {
    "version": 1,
    "idPrefixes": {"AGG-": "M1", "BH-": "M2", "GLS-": "GLS"},
    "refKeys": ["ownerEntity", "relatedObjectRefs"],
    "edges": [
        {"from": "M2", "field": "ownerEntity", "to": ["M1"]},
        {"from": "GLS", "field": "relatedObjectRefs", "to": ["M1"]},
    ],
}

M1 = """model_type: OBJECT
version: "1.0.0"
domain: demo
aggregates:
  - id: AGG-DEMO-001
    name: 井
    alias: Well
    aggregateType: AGGREGATE_ROOT
    attributes: []
"""

M2 = """model_type: BEHAVIOR
version: "1.0.0"
domain: demo
behaviors:
  - id: BH-DEMO-Record
    name: 录入
    ownerEntity: AGG-DEMO-001
    behaviorType: COMMAND
    triggerType: USER_ACTION
    preconditions: []
    postconditions: []
    appliedRules: []
    requiredPermissions: []
"""


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "onto"
        write(self.root / "schema" / "model-registry.json", json.dumps(REGISTRY))
        write(self.root / "schema" / "model-deps.json", json.dumps(DEPS))
        # 票 13 起 manifest 预置 omittedModels（覆盖注册表全模型）：本基座各测试
        # 只加部分模型文件是常态，AC6 反向闸（missing-model-file）不该改变老测试
        # 语义——反向闸的正负变体由 MissingModelFile 专类用自管 manifest 覆盖。
        write(self.root / "demo" / "manifest.json", json.dumps(
            {"domain": "demo", "profile": "full", "schemaVersion": "1.0.0",
             "omittedModels": [
                 {"model": "M1", "reason": "单测基座：模型文件按需加装"},
                 {"model": "M2", "reason": "单测基座：模型文件按需加装"},
                 {"model": "GLS", "reason": "单测基座：模型文件按需加装"},
             ]}))

    def tearDown(self):
        self.tmp.cleanup()

    def add(self, name, text, domain="demo"):
        write(self.root / domain / name, text)

    def run_check(self, target=None):
        return sc.run(target or self.root)

    def kinds(self, report=None):
        r = report or self.run_check()
        return [v["kind"] for v in r["violations"]]


class Ac1ValidOntologyPasses(Base):
    def test_valid_domain_exits_zero(self):
        self.add("m1-object-model.yaml", M1)
        self.add("m2-behavior-model.yaml", M2)
        report = self.run_check()
        self.assertEqual(report["status"], "pass", report["violations"])
        self.assertEqual(quiet_main(["--json", str(self.root)]), 0)


class Ac2YamlSyntaxError(Base):
    def test_syntax_error_reports_l1_with_filename(self):
        self.add("m2-behavior-model.yaml",
                 "model_type: BEHAVIOR\nbehaviors:\n\t- id: x\n")
        report = self.run_check()
        self.assertEqual(report["status"], "fail")
        kinds = self.kinds(report)
        self.assertIn("yaml-syntax", kinds)
        v = report["violations"][0]
        self.assertEqual(v["level"], "L1")
        self.assertIn("m2-behavior-model.yaml", v["file"])
        self.assertEqual(quiet_main(["--json", str(self.root)]), 1)


class Ac3MissingCommonField(Base):
    def test_missing_version_named(self):
        self.add("m1-object-model.yaml",
                 "\n".join(l for l in M1.splitlines() if not l.startswith("version")))
        report = self.run_check()
        self.assertIn("missing-common-field", self.kinds(report))
        msgs = " ".join(v["message"] for v in report["violations"])
        self.assertIn("version", msgs)

    def test_missing_model_type_named(self):
        self.add("m1-object-model.yaml",
                 "\n".join(l for l in M1.splitlines() if not l.startswith("model_type")))
        msgs = " ".join(v["message"] for v in self.run_check()["violations"])
        self.assertIn("model_type", msgs)


class Ac4DanglingRef(Base):
    def test_dangling_ref_reports_l2_with_location(self):
        self.add("m1-object-model.yaml", M1)
        self.add("m2-behavior-model.yaml",
                 M2.replace("AGG-DEMO-001", "AGG-DEMO-999"))
        report = self.run_check()
        self.assertIn("dangling-ref", self.kinds(report))
        v = next(v for v in report["violations"] if v["kind"] == "dangling-ref")
        self.assertEqual(v["level"], "L2")
        self.assertIn("AGG-DEMO-999", v["message"])
        self.assertIn("m2-behavior-model.yaml", v["file"])
        self.assertGreater(v["line"], 0)


class Ac5DependencyWhitelist(Base):
    def test_cross_model_ref_out_of_whitelist(self):
        # M2 依赖白名单只有 M1：构造 M2 ref 指向本迷你仓不存在的第三类 ID
        # （用锁定外的未登记 ref 字段指向 M1 之外的模型——这里以 M1 引 BH- 反向例证）
        self.add("m1-object-model.yaml", M1 + "\nextraRef: BH-DEMO-Record\n")
        self.add("m2-behavior-model.yaml", M2)
        report = self.run_check()
        self.assertIn("dep-whitelist", self.kinds(report))
        v = next(v for v in report["violations"] if v["kind"] == "dep-whitelist")
        self.assertEqual(v["level"], "L2")
        self.assertIn("M1", v["message"])
        self.assertIn("M2", v["message"])

    def test_registry_deps_conflict_with_edges_is_l1(self):
        deps = json.loads(json.dumps(DEPS))
        deps["edges"].append({"from": "M1", "field": "whatever", "to": ["M2"]})
        write(self.root / "schema" / "model-deps.json", json.dumps(deps))
        self.add("m1-object-model.yaml", M1)
        self.assertIn("deps-registry-conflict", self.kinds())


class Ac6ProfileNotEnabled(Base):
    def test_disabled_model_file_is_l4(self):
        write(self.root / "demo" / "manifest.json", json.dumps(
            {"domain": "demo", "profile": "mini", "schemaVersion": "1.0.0"}))
        self.add("m1-object-model.yaml", M1)
        self.add("m2-behavior-model.yaml", M2)  # M2 不在 mini profile
        report = self.run_check()
        self.assertIn("profile-disabled", self.kinds(report))
        v = next(v for v in report["violations"] if v["kind"] == "profile-disabled")
        self.assertEqual(v["level"], "L4")
        self.assertIn("M2", v["message"])

    def test_unknown_profile_is_violation(self):
        write(self.root / "demo" / "manifest.json", json.dumps(
            {"domain": "demo", "profile": "nope", "schemaVersion": "1.0.0"}))
        self.assertIn("unknown-profile", self.kinds())


class Ac7FieldRedefinition(Base):
    def test_locked_field_is_l4(self):
        registry = json.loads(json.dumps(REGISTRY))
        registry["models"]["M2"]["lockedFields"] = {
            "producedEvents": "v6 事件异步引用；v9 由 syncTriggers 承载"}
        write(self.root / "schema" / "model-registry.json", json.dumps(registry))
        self.add("m1-object-model.yaml", M1)
        self.add("m2-behavior-model.yaml",
                 M2 + "    producedEvents: [EV-DEMO-001]\n")
        report = self.run_check()
        self.assertIn("field-redefinition", self.kinds(report))
        v = next(v for v in report["violations"] if v["kind"] == "field-redefinition")
        self.assertEqual(v["level"], "L4")
        self.assertIn("producedEvents", v["message"])
        self.assertIn("换义", v["message"])


class Misc(Base):
    def test_domain_without_manifest_is_violation(self):
        write(self.root / "wild" / "m1-object-model.yaml", M1)
        self.assertIn("missing-manifest", self.kinds())

    def test_missing_schema_files_is_config_error(self):
        (self.root / "schema" / "model-deps.json").unlink()
        with self.assertRaises(ValueError):
            self.run_check()

    def test_line_numbers_are_one_based_and_accurate(self):
        self.add("m1-object-model.yaml", M1)
        self.add("m2-behavior-model.yaml",
                 M2.replace("AGG-DEMO-001", "AGG-DEMO-999"))
        report = self.run_check()
        v = next(v for v in report["violations"] if v["kind"] == "dangling-ref")
        # ownerEntity 行是 M2 文本的第 7 行
        self.assertEqual(v["line"], 7)


# ---------- 票 34 P2-A：patterns/ 素材目录排除（裸仓根绿灯红线恢复）----------

class PatternDirExclusion(Base):
    """票 34 P2-A 单测面：patterns/ 是建模素材区不是域——域发现整体排除，
    素材目录不补 manifest（manifest=域声明，素材目录补=撒谎，设计裁决）。
    两场景钉死（排除只按目录名 patterns，不按内容）+ 真域零扰动红线；
    约定成文 ontology/schema/schema.md §1「素材目录约定」。
    """

    PATTERN_YAML = """model_type: OBJECT
version: "1.0.0"
domain: patterns
aggregates:
  - id: AGG-PATTERN-001
    name: 状态机聚合模式件
    aggregateType: AGGREGATE_ROOT
    attributes: []
"""

    def test_patterns_yaml_without_manifest_not_reported(self):
        # 甲（票 33 复现场景）：patterns/ 放模式件 YAML、无 manifest——
        # 修前裸仓根报 L1 missing-manifest 1 处（P2-A 实锤），修后整体排除
        write(self.root / "patterns" / "state-machine-lifecycle.yaml",
              self.PATTERN_YAML)
        report = self.run_check()
        self.assertEqual(report["status"], "pass", report["violations"])
        self.assertNotIn("missing-manifest", self.kinds(report))
        self.assertNotIn("patterns", [d["domain"] for d in report["domains"]])
        # 红线：真域扫描一个不少——同仓根 demo 域照常在列
        self.assertIn("demo", [d["domain"] for d in report["domains"]])

    def test_patterns_with_manifest_still_not_scanned_as_domain(self):
        # 乙（防内容漂移）：patterns/ 下将来出现真域结构（含 manifest）仍不作为
        # 域扫描——排除只按目录名；其结构纪律归 fixtures/pattern-library/ 出厂集
        # 与归档闸 ontology-pattern 类，不归语义闸域扫描
        write(self.root / "patterns" / "manifest.json", json.dumps(
            {"domain": "patterns", "profile": "full", "schemaVersion": "1.0.0"}))
        write(self.root / "patterns" / "m1-object-model.yaml", self.PATTERN_YAML)
        report = self.run_check()
        self.assertNotIn("patterns", [d["domain"] for d in report["domains"]])
        # 若被当域扫：profile=full 启用 M2/GLS 缺文件必红 missing-model-file——
        # 零违规即证明确实没扫
        self.assertEqual(report["violations"], [])

    def test_non_pattern_dir_with_yaml_still_missing_manifest(self):
        # 对照（排除不外溢）：其余名字的目录含模型 YAML 缺 manifest 照报——
        # 排除只对 patterns 目录生效，真域缺失 manifest 一个不少
        write(self.root / "wild" / "m1-object-model.yaml", M1)
        write(self.root / "patterns" / "state-machine-lifecycle.yaml",
              self.PATTERN_YAML)
        kinds = self.kinds()
        self.assertIn("missing-manifest", kinds)
        v = next(v for v in self.run_check()["violations"]
                 if v["kind"] == "missing-manifest")
        self.assertIn("wild", v["file"])
        self.assertNotIn("patterns", v["file"])


GLOSSARY = """model_type: GLOSSARY
version: "1.0.0"
domain: demo
terms:
  - id: GLS-DEMO-001
    term: 生产井
    aliases: [油井]
    definition: 正在采油的井。
    relatedObjectRefs: [AGG-DEMO-001]
"""


class GlossaryModel(Base):
    """票 10：GLS 术语模型进 schema（元模型演进）——GLS-AC1…AC4 的单测面。"""

    def test_valid_glossary_passes(self):
        # GLS-AC1：合法 glossary + relatedObjectRefs 指向真实 M1 对象 → 全过
        self.add("m1-object-model.yaml", M1)
        self.add("glossary-model.yaml", GLOSSARY)
        report = self.run_check()
        self.assertEqual(report["status"], "pass", report["violations"])

    def test_gls_in_disabled_profile_is_l4(self):
        # GLS-AC2：GLS 不入 mini 组合（对应真仓 v9-core），文件出现 → L4 红
        write(self.root / "demo" / "manifest.json", json.dumps(
            {"domain": "demo", "profile": "mini", "schemaVersion": "1.0.0"}))
        self.add("glossary-model.yaml", GLOSSARY)
        report = self.run_check()
        v = next(v for v in report["violations"] if v["kind"] == "profile-disabled")
        self.assertEqual(v["level"], "L4")
        self.assertIn("GLS", v["message"])

    def test_gls_dangling_object_ref_is_l2(self):
        # GLS-AC3：relatedObjectRefs 指向不存在的 AGG- → L2 悬空引用红
        self.add("m1-object-model.yaml", M1)
        self.add("glossary-model.yaml", GLOSSARY.replace("AGG-DEMO-001", "AGG-DEMO-999"))
        report = self.run_check()
        v = next(v for v in report["violations"] if v["kind"] == "dangling-ref")
        self.assertEqual(v["level"], "L2")
        self.assertIn("AGG-DEMO-999", v["message"])
        self.assertIn("glossary-model.yaml", v["file"])

    def test_gls_dep_whitelist_allows_m1(self):
        # 依赖边 GLS.relatedObjectRefs→[M1] 已登记：指向真实 M1 不触发白名单违规
        self.add("m1-object-model.yaml", M1)
        self.add("glossary-model.yaml", GLOSSARY)
        self.assertNotIn("dep-whitelist", self.kinds())

    def test_filename_model_type_mismatch_is_l1(self):
        # GLS-AC4 甲：glossary 文件 model_type 写错（如 OBJECT）→ L1 filename-mismatch
        self.add("m1-object-model.yaml", M1)
        self.add("glossary-model.yaml", GLOSSARY.replace("GLOSSARY", "OBJECT"))
        report = self.run_check()
        v = next(v for v in report["violations"] if v["kind"] == "filename-mismatch")
        self.assertEqual(v["level"], "L1")
        self.assertIn("glossary-model.yaml", v["file"])
        self.assertIn("m1-object-model.yaml", v["message"])

    def test_gls_content_in_wrong_filename_is_l1(self):
        # GLS-AC4 乙：GLS 内容错挂 m1 文件名 → L1 filename-mismatch
        self.add("m1-object-model.yaml", GLOSSARY)
        report = self.run_check()
        v = next(v for v in report["violations"] if v["kind"] == "filename-mismatch")
        self.assertEqual(v["level"], "L1")
        self.assertIn("glossary-model.yaml", v["message"])

    def test_existing_correct_filenames_still_pass(self):
        # 红线：filename 检查对既有合规文件（m1/m2 按注册表 yamlFile 命名）零扰动
        self.add("m1-object-model.yaml", M1)
        self.add("m2-behavior-model.yaml", M2)
        self.assertNotIn("filename-mismatch", self.kinds())


# ---------- 票 11：L2 一致性对（M7↔M2 / M2↔M5 / M6 roleRef）----------

CONS_REGISTRY = {
    "version": 1,
    "models": {
        "M1": dict(REGISTRY["models"]["M1"], profiles=["full"]),
        "M2": dict(REGISTRY["models"]["M2"], dependsOn=["M1", "M5"]),
        "M5": {
            "name": "主体模型", "yamlFile": "m5-actor-model.yaml",
            "modelType": "ACTOR", "camp": "business-core",
            "consumers": ["runtime", "build"], "profiles": ["full"],
            "dependsOn": ["M1", "M2"], "lockedFields": {},
        },
        "M6": {
            "name": "流程模型", "yamlFile": "m6-flow-model.yaml",
            "modelType": "FLOW", "camp": "business-core",
            "consumers": ["build"], "profiles": ["full"],
            "dependsOn": ["M1", "M2", "M5"], "lockedFields": {},
        },
        "M7": {
            "name": "查询统计与报表模型", "yamlFile": "m7-report-model.yaml",
            "modelType": "REPORT", "camp": "business-core",
            "consumers": ["runtime", "build"], "profiles": ["full"],
            "dependsOn": ["M1", "M2"], "lockedFields": {},
        },
    },
}

CONS_DEPS = {
    "version": 1,
    "idPrefixes": {"AGG-": "M1", "BH-": "M2", "ROLE-": "M5", "PERM-": "M5",
                   "FLOW-": "M6", "QR-": "M7"},
    "refKeys": ["ownerEntity", "requiredPermissions", "roles", "permissions",
                "targetRef", "roleRefs", "businessObjectRefs"],
    "edges": [
        {"from": "M2", "field": "ownerEntity", "to": ["M1"]},
        {"from": "M2", "field": "requiredPermissions", "to": ["M5"]},
        {"from": "M5", "field": "roles", "to": ["M5"]},
        {"from": "M5", "field": "permissions", "to": ["M5"]},
        {"from": "M5", "field": "targetRef", "to": ["M1", "M2"]},
        {"from": "M6", "field": "businessObjectRefs", "to": ["M1"]},
        {"from": "M6", "field": "roleRefs", "to": ["M5"]},
        {"from": "M6", "field": "roleRef", "to": ["M5"]},
        {"from": "M7", "field": "behaviorRef", "to": ["M2"]},
    ],
}

CONS_M1 = """model_type: OBJECT
version: "1.0.0"
domain: demo
aggregates:
  - id: AGG-DEMO-001
    name: 井
    alias: Well
    aggregateType: AGGREGATE_ROOT
    attributes: []
"""

CONS_M2 = """model_type: BEHAVIOR
version: "1.0.0"
domain: demo
behaviors:
  - id: BH-DEMO-Record
    name: 录入
    ownerEntity: AGG-DEMO-001
    behaviorType: COMMAND
    triggerType: USER_ACTION
    preconditions: []
    postconditions: []
    appliedRules: []
    requiredPermissions:
      - PERM-DEMO-Record
  - id: BH-DEMO-Query
    name: 查询
    ownerEntity: AGG-DEMO-001
    behaviorType: QUERY
    triggerType: USER_ACTION
    preconditions: []
    postconditions: []
    appliedRules: []
    requiredPermissions: []
"""

CONS_M5 = """model_type: ACTOR
version: "1.0.0"
domain: demo
roles:
  - roleId: ROLE-DEMO-001
    name: 录入员
    inheritsFrom: []
    permissions:
      - PERM-DEMO-Record
  - roleId: ROLE-DEMO-002
    name: 场外角色
    inheritsFrom: []
    permissions: []
permissions:
  - permissionId: PERM-DEMO-Record
    targetType: BEHAVIOR
    targetRef: BH-DEMO-Record
    dataScope: ALL
"""

CONS_M6 = """model_type: FLOW
version: "1.0.0"
domain: demo
flows:
  - id: FLOW-DEMO-001
    name: 录入流程
    flowType: COLLABORATION
    businessObjectRefs:
      - AGG-DEMO-001
    roleRefs:
      - ROLE-DEMO-001
    trigger:
      triggerType: MANUAL
    startActivity: ACT-DEMO-001
    endActivities:
      - ACT-DEMO-002
    activities:
      - activityId: ACT-DEMO-001
        name: 录入
        activityType: USER_TASK
        roleRef: ROLE-DEMO-001
        nextActivities:
          - ACT-DEMO-002
      - activityId: ACT-DEMO-002
        name: 结束
        activityType: END
"""

CONS_M7 = """model_type: REPORT
version: "1.0.0"
domain: demo
query_reports:
  - id: QR-DEMO-001
    name: 查询报表
    alias: demoQuery
    objectType: DETAIL_QUERY
    behaviorRef: BH-DEMO-Query
"""


class ConsBase(Base):
    """票 11 基座：注册表/依赖表扩到 M5/M6/M7（一致性对所需的模型面）。"""

    def setUp(self):
        super().setUp()
        write(self.root / "schema" / "model-registry.json", json.dumps(CONS_REGISTRY))
        write(self.root / "schema" / "model-deps.json", json.dumps(CONS_DEPS))
        # omittedModels 与本基座注册表对齐（票 13：引用未注册模型 = L1 红）
        write(self.root / "demo" / "manifest.json", json.dumps(
            {"domain": "demo", "profile": "full", "schemaVersion": "1.0.0",
             "omittedModels": [
                 {"model": k, "reason": "单测基座：模型文件按需加装"}
                 for k in ("M1", "M2", "M5", "M6", "M7")
             ]}))

    def add_cons_domain(self):
        self.add("m1-object-model.yaml", CONS_M1)
        self.add("m2-behavior-model.yaml", CONS_M2)
        self.add("m5-actor-model.yaml", CONS_M5)
        self.add("m6-flow-model.yaml", CONS_M6)
        self.add("m7-report-model.yaml", CONS_M7)

    def cons_kinds(self, report=None):
        r = report or self.run_check()
        return [v["kind"] for v in r["violations"] if v["kind"].startswith("consistency-")]


class ConsistencyPairs(ConsBase):
    """票 11 AC 表（CONS-AC1–3）：三对一致性检查的正例与负变体。"""

    def test_consistent_domain_passes(self):
        # 正例：三对全闭合（QR→QUERY 一对一、PERM 回指、活动角色∈流程角色）→ 无 consistency- 行
        self.add_cons_domain()
        report = self.run_check()
        self.assertEqual(report["status"], "pass", report["violations"])
        self.assertEqual(self.cons_kinds(report), [])

    def test_m7_bound_to_non_query_behavior_is_redirection(self):
        # CONS-AC1 甲：behaviorRef 指向 COMMAND 行为 → consistency-redirection（L2）
        self.add_cons_domain()
        self.add("m7-report-model.yaml",
                 CONS_M7.replace("BH-DEMO-Query", "BH-DEMO-Record"))
        report = self.run_check()
        self.assertIn("consistency-redirection", self.cons_kinds(report))
        v = next(v for v in report["violations"]
                 if v["kind"] == "consistency-redirection")
        self.assertEqual(v["level"], "L2")
        for needle in ("QR-DEMO-001", "BH-DEMO-Record", "COMMAND", "behaviorRef"):
            self.assertIn(needle, v["message"])

    def test_shared_query_behavior_is_not_one_to_one(self):
        # CONS-AC1 乙：同一 QUERY 行为被两个 QR 绑定 → consistency-not-one-to-one（L2），
        # 报文含先绑者与再绑者双方 ID
        self.add_cons_domain()
        qr2 = """  - id: QR-DEMO-002
    name: 查询报表二
    alias: demoQueryTwo
    objectType: DETAIL_QUERY
    behaviorRef: BH-DEMO-Query
"""
        self.add("m7-report-model.yaml", CONS_M7 + qr2)
        report = self.run_check()
        self.assertIn("consistency-not-one-to-one", self.cons_kinds(report))
        v = next(v for v in report["violations"]
                 if v["kind"] == "consistency-not-one-to-one")
        self.assertEqual(v["level"], "L2")
        for needle in ("QR-DEMO-001", "QR-DEMO-002", "BH-DEMO-Query"):
            self.assertIn(needle, v["message"])

    def test_perm_target_ref_not_backlinking_is_permission_break(self):
        # CONS-AC2：PERM 存在（dangling 不红）但 targetRef 未回指要求它的行为
        # → consistency-permission（L2）
        self.add_cons_domain()
        self.add("m5-actor-model.yaml",
                 CONS_M5.replace("targetRef: BH-DEMO-Record", "targetRef: BH-DEMO-Query"))
        report = self.run_check()
        self.assertIn("consistency-permission", self.cons_kinds(report))
        v = next(v for v in report["violations"]
                 if v["kind"] == "consistency-permission")
        self.assertEqual(v["level"], "L2")
        for needle in ("BH-DEMO-Record", "PERM-DEMO-Record", "BH-DEMO-Query"):
            self.assertIn(needle, v["message"])

    def test_unknown_perm_stays_dangling_ref_not_consistency(self):
        # P2 存在性向仍归 dangling-ref（requiredPermissions 在 refKeys∪edges），
        # 不重复报 consistency-permission——红因不混
        self.add_cons_domain()
        self.add("m2-behavior-model.yaml",
                 CONS_M2.replace("PERM-DEMO-Record", "PERM-DEMO-999"))
        report = self.run_check()
        self.assertIn("dangling-ref", self.kinds(report))
        self.assertNotIn("consistency-permission", self.cons_kinds(report))

    def test_activity_role_outside_flow_rolerefs_is_flow_role(self):
        # CONS-AC3：活动 roleRef 指向存在但不在流程 roleRefs 内的角色
        # → consistency-flow-role（L2），报文含流程/活动/角色三方 ID
        self.add_cons_domain()
        self.add("m6-flow-model.yaml",
                 CONS_M6.replace("roleRef: ROLE-DEMO-001", "roleRef: ROLE-DEMO-002"))
        report = self.run_check()
        self.assertIn("consistency-flow-role", self.cons_kinds(report))
        v = next(v for v in report["violations"]
                 if v["kind"] == "consistency-flow-role")
        self.assertEqual(v["level"], "L2")
        for needle in ("FLOW-DEMO-001", "ACT-DEMO-001", "ROLE-DEMO-002", "roleRefs"):
            self.assertIn(needle, v["message"])

    def test_json_report_carries_consistency_rows(self):
        # 报告行可机读：--json 输出中每条一致性违规一行（level/kind/file/line/message）
        self.add_cons_domain()
        self.add("m7-report-model.yaml",
                 CONS_M7.replace("BH-DEMO-Query", "BH-DEMO-Record"))
        buf = io.StringIO()
        with redirect_stdout(buf):
            sc.main(["--json", str(self.root)])
        rows = json.loads(buf.getvalue())["violations"]
        cons = [r for r in rows if r["kind"].startswith("consistency-")]
        self.assertTrue(cons)
        for r in cons:
            self.assertEqual(r["level"], "L2")
            self.assertTrue(r["file"].endswith("m7-report-model.yaml"))
            self.assertGreater(r["line"], 0)

    def test_pairs_degenerate_without_models(self):
        # 退化面：注册表只有 M1/M2（Base 迷你表）时一致性对静默跳过，不崩不误报
        # （manifest 同步回 Base 基座形态，票 13：omittedModels 须引用注册模型）
        write(self.root / "schema" / "model-registry.json", json.dumps(REGISTRY))
        write(self.root / "schema" / "model-deps.json", json.dumps(DEPS))
        write(self.root / "demo" / "manifest.json", json.dumps(
            {"domain": "demo", "profile": "full", "schemaVersion": "1.0.0",
             "omittedModels": [
                 {"model": "M1", "reason": "单测基座：模型文件按需加装"},
                 {"model": "M2", "reason": "单测基座：模型文件按需加装"},
                 {"model": "GLS", "reason": "单测基座：模型文件按需加装"},
             ]}))
        self.add("m1-object-model.yaml", M1)
        self.add("m2-behavior-model.yaml", M2)
        self.assertEqual(self.run_check()["status"], "pass")

# ---------- 票 13：L1 元素级必填闸 + L4 AC6 反向（missing-model-file/omittedModels）----------

REQ_REGISTRY = {
    "version": "1.2.0",
    "models": {
        "M1": dict(REGISTRY["models"]["M1"], profiles=["full"]),
        "M2": dict(REGISTRY["models"]["M2"], profiles=["full"],
                   requiredElementFields={
                       "BH-": ["id", "name", "ownerEntity", "behaviorType"]}),
        "M7": {
            "name": "查询统计与报表模型", "yamlFile": "m7-report-model.yaml",
            "modelType": "REPORT", "camp": "business-core",
            "consumers": ["runtime", "build"], "profiles": ["full"],
            "dependsOn": ["M1", "M2"], "lockedFields": {},
            "requiredElementFields": {
                "QR-": ["id", "name", "behaviorRef"]},
        },
    },
}

REQ_DEPS = {
    "version": "1.2.0",
    "idPrefixes": {"AGG-": "M1", "BH-": "M2", "QR-": "M7"},
    "refKeys": ["ownerEntity", "behaviorRef"],
    "edges": [
        {"from": "M2", "field": "ownerEntity", "to": ["M1"]},
        {"from": "M7", "field": "behaviorRef", "to": ["M2"]},
    ],
}


class ReqBase(Base):
    """票 13 基座：M1/M2/M7 迷你注册表，M2/M7 带 requiredElementFields。"""

    def setUp(self):
        super().setUp()
        write(self.root / "schema" / "model-registry.json", json.dumps(REQ_REGISTRY))
        write(self.root / "schema" / "model-deps.json", json.dumps(REQ_DEPS))
        write(self.root / "demo" / "manifest.json", json.dumps(
            {"domain": "demo", "profile": "full", "schemaVersion": "1.2.0",
             "omittedModels": [
                 {"model": "M1", "reason": "单测基座：模型文件按需加装"},
                 {"model": "M2", "reason": "单测基座：模型文件按需加装"},
                 {"model": "M7", "reason": "单测基座：模型文件按需加装"},
             ]}))

    def req_violations(self, report=None, kind="required-field"):
        r = report or self.run_check()
        return [v for v in r["violations"] if v["kind"] == kind]


class RequiredFields(ReqBase):
    """票 13 AC 表 AC1/AC2 的单测面：元素级结构性必填闸。"""

    def test_all_required_fields_present_passes(self):
        self.add("m1-object-model.yaml", M1)
        self.add("m2-behavior-model.yaml", M2 + """  - id: BH-DEMO-Query
    name: 查询
    ownerEntity: AGG-DEMO-001
    behaviorType: QUERY
""")
        self.add("m7-report-model.yaml", CONS_M7)
        self.assertEqual(self.run_check()["status"], "pass",
                         self.run_check()["violations"])

    def test_missing_type_discriminator_is_required_field(self):
        # AC1：M2 行为缺 behaviorType（一致性锚点）→ L1 required-field 红（不再静默跳过）
        self.add("m1-object-model.yaml", M1)
        self.add("m2-behavior-model.yaml",
                 "\n".join(l for l in M2.splitlines()
                           if not l.startswith("    behaviorType")))
        report = self.run_check()
        vs = self.req_violations(report)
        self.assertTrue(vs)
        v = vs[0]
        self.assertEqual(v["level"], "L1")
        self.assertIn("BH-DEMO-Record", v["message"])
        self.assertIn("behaviorType", v["message"])
        self.assertIn("requiredElementFields", v["message"])
        self.assertGreater(v["line"], 0)

    def test_missing_anchor_field_reports_element_and_field(self):
        # AC2 同款：M7 报表缺 behaviorRef → L1 required-field 红
        self.add("m7-report-model.yaml",
                 "\n".join(l for l in CONS_M7.splitlines()
                           if not l.startswith("    behaviorRef")))
        vs = self.req_violations()
        self.assertTrue(vs)
        self.assertIn("QR-DEMO-001", vs[0]["message"])
        self.assertIn("behaviorRef", vs[0]["message"])

    def test_empty_shell_file_is_required_field(self):
        # AC3 同款：behaviors 空列表 = 空壳文件 → L1 required-field 红
        self.add("m2-behavior-model.yaml",
                 "model_type: BEHAVIOR\nversion: \"1.0.0\"\ndomain: demo\nbehaviors: []\n")
        vs = self.req_violations()
        self.assertTrue(vs)
        self.assertIn("空壳", vs[0]["message"])
        self.assertIn("M2", vs[0]["message"])

    def test_filename_mismatch_skips_required_gate(self):
        # 红因纯净：文件名与 model_type 错挂时内容与模型锚已断，必填闸让位给
        # filename-mismatch，不叠加空壳红因（gls-ac4 形态，lessons/13）
        self.add("m1-object-model.yaml",
                 "model_type: BEHAVIOR\nversion: \"1.0.0\"\ndomain: demo\nbehaviors: []\n")
        report = self.run_check()
        self.assertEqual(self.req_violations(report), [])
        self.assertIn("filename-mismatch", self.kinds(report))


class MissingModelFile(ReqBase):
    """票 13 AC 表 AC5/AC6 的单测面：AC6 反向 + omittedModels 豁免机制。"""

    def test_enabled_model_without_file_is_l4(self):
        # AC5：profile 启用 M2 但域内无文件、无豁免 → L4 missing-model-file 红
        write(self.root / "demo" / "manifest.json", json.dumps(
            {"domain": "demo", "profile": "full", "schemaVersion": "1.2.0"}))
        self.add("m1-object-model.yaml", M1)
        report = self.run_check()
        vs = self.req_violations(report, kind="missing-model-file")
        self.assertTrue(vs)
        v = vs[0]
        self.assertEqual(v["level"], "L4")
        self.assertIn("M2", v["message"])
        self.assertIn("omittedModels", v["message"])

    def test_waived_model_with_reason_passes(self):
        # AC6：同上但 omittedModels 带理由豁免 → 不红
        write(self.root / "demo" / "manifest.json", json.dumps(
            {"domain": "demo", "profile": "full", "schemaVersion": "1.2.0",
             "omittedModels": [
                 {"model": "M2", "reason": "无素材证据，有意裁剪"},
                 {"model": "M7", "reason": "无素材证据，有意裁剪"},
             ]}))
        self.add("m1-object-model.yaml", M1)
        report = self.run_check()
        self.assertEqual(report["status"], "pass", report["violations"])

    def test_waiver_without_reason_is_not_exemption(self):
        # 豁免条目缺 reason / reason 空串 = 无效豁免，缺文件照红
        for reason in (None, "", "   "):
            entry = {"model": "M2"}
            if reason is not None:
                entry["reason"] = reason
            write(self.root / "demo" / "manifest.json", json.dumps(
                {"domain": "demo", "profile": "full", "schemaVersion": "1.2.0",
                 "omittedModels": [entry]}))
            self.add("m1-object-model.yaml", M1)
            vs = self.req_violations(self.run_check(), kind="missing-model-file")
            self.assertTrue(vs, f"reason={reason!r} 不应构成有效豁免")
            self.assertIn("M2", vs[0]["message"])

    def test_waiver_referencing_unknown_model_is_l1(self):
        # omittedModels 引用未注册模型 = 配置错误，L1 红（防错别字静默失效）
        write(self.root / "demo" / "manifest.json", json.dumps(
            {"domain": "demo", "profile": "full", "schemaVersion": "1.2.0",
             "omittedModels": [{"model": "MX", "reason": "手滑写错模型键"}]}))
        self.add("m1-object-model.yaml", M1)
        self.assertIn("unknown-omitted-model", self.kinds())

    def test_malformed_waiver_entry_is_l1(self):
        # omittedModels 条目缺 model 键 = 配置错误，L1 红
        write(self.root / "demo" / "manifest.json", json.dumps(
            {"domain": "demo", "profile": "full", "schemaVersion": "1.2.0",
             "omittedModels": [{"reason": "不是合法条目"}]}))
        self.add("m1-object-model.yaml", M1)
        self.assertIn("bad-omitted-model", self.kinds())

    def test_unknown_profile_does_not_trigger_missing_check(self):
        # profile 未知时 enabled 为空，反向闸不触发（unknown-profile 已单独红）
        write(self.root / "demo" / "manifest.json", json.dumps(
            {"domain": "demo", "profile": "nope", "schemaVersion": "1.2.0"}))
        kinds = self.kinds()
        self.assertIn("unknown-profile", kinds)
        self.assertNotIn("missing-model-file", kinds)


# ---------- 票 16：L4 禁用词拦截面（GLS×schema_check 联动闸，BAN-* 出厂断言）----------

BAN_GLS = """model_type: GLOSSARY
version: "1.0.0"
domain: demo
terms:
  - id: GLS-DEMO-001
    term: 老完成率
    aliases: []
    termType: 禁用词
    definition: v1 口径，已废弃；禁用旧称，替代=新完成率。
    status: 禁用（替代：新完成率）
    source: 合成·票 16 出厂集
  - id: GLS-DEMO-002
    term: 剔检产量
    aliases: [净产量]
    termType: 别名
    definition: 剔除检修井口径的产量。
    status: 有效
    source: 合成·票 16 出厂集
"""


class BannedTerm(Base):
    """票 16 AC 表（AC1–4）：禁用词拦截面。真源=域内 GLS 术语 status 含「禁用」
    条目的 term+aliases；匹配面=全文件递归收集键恰为 name/alias 的字符串值
    （description/notes 不扫=文档自由）。防误报对照（AC4/描述提及/GLS 自身 term
    不自匹配）是本套件的灵魂断言——钉死匹配面，防止未来放大。"""

    def test_name_containing_banned_term_is_l4(self):
        # AC1：元素 name 含禁用词（子串）→ L4 banned-term，报文含 GLS 条目 ID 与命中词
        self.add("m1-object-model.yaml", M1.replace("name: 井", "name: 老完成率（v1 口径）"))
        self.add("glossary-model.yaml", BAN_GLS)
        report = self.run_check()
        self.assertIn("banned-term", self.kinds(report))
        v = next(v for v in report["violations"] if v["kind"] == "banned-term")
        self.assertEqual(v["level"], "L4")
        self.assertIn("GLS-DEMO-001", v["message"])
        self.assertIn("老完成率", v["message"])
        self.assertIn("m1-object-model.yaml", v["file"])
        self.assertGreater(v["line"], 0)

    def test_alias_containing_banned_term_is_l4(self):
        # AC2：元素 alias 撞禁用词 → L4 banned-term
        self.add("m1-object-model.yaml", M1.replace("alias: Well", "alias: Well老完成率"))
        self.add("glossary-model.yaml", BAN_GLS)
        report = self.run_check()
        self.assertIn("banned-term", self.kinds(report))
        v = next(v for v in report["violations"] if v["kind"] == "banned-term")
        self.assertEqual(v["level"], "L4")

    def test_alias_of_banned_entry_is_also_banned(self):
        # 禁用条目的 aliases 也是禁用词表成员（设计裁决：term 与 aliases 都算）
        gls = BAN_GLS.replace("    aliases: []", "    aliases: [废弃口径]")
        self.add("m1-object-model.yaml", M1.replace("name: 井", "name: 废弃口径"))
        self.add("glossary-model.yaml", gls)
        report = self.run_check()
        self.assertIn("banned-term", self.kinds(report))
        v = next(v for v in report["violations"] if v["kind"] == "banned-term")
        self.assertIn("废弃口径", v["message"])

    def test_status_substring_wide_gate(self):
        # 宽进严出：status 值含「禁用」子串即入表（不枚举状态值）——
        # 「已禁用待复核」这类非「禁用（替代…）」形态照样拦
        self.add("m1-object-model.yaml", M1.replace("name: 井", "name: 老完成率"))
        self.add("glossary-model.yaml",
                 BAN_GLS.replace("status: 禁用（替代：新完成率）", "status: 已禁用待复核"))
        self.assertIn("banned-term", self.kinds())

    def test_valid_status_term_in_name_passes(self):
        # AC4 防误报对照：status=有效的 GLS 术语出现在 name → 必须绿
        #（只拦禁用 status，不拦全部术语）
        self.add("m1-object-model.yaml", M1.replace("name: 井", "name: 剔检产量"))
        self.add("glossary-model.yaml", BAN_GLS)
        report = self.run_check()
        self.assertNotIn("banned-term", self.kinds(report))
        self.assertEqual(report["status"], "pass", report["violations"])

    def test_description_mention_passes(self):
        # AC3 单域版：description 提及禁用词合法（文档自由）——拦截面只在 name/alias
        self.add("m1-object-model.yaml",
                 M1 + "    description: 禁用旧称「老完成率」——v1 口径，2024 年废弃。\n")
        self.add("glossary-model.yaml", BAN_GLS)
        report = self.run_check()
        self.assertNotIn("banned-term", self.kinds(report))
        self.assertEqual(report["status"], "pass", report["violations"])

    def test_gls_own_terms_do_not_self_match(self):
        # 防自匹配：禁用词表来自 GLS term 值，匹配面是 name/alias 键——
        # GLS 条目以 term/aliases 承载词面，不在匹配面 → 域内仅 GLS 也全绿
        self.add("glossary-model.yaml", BAN_GLS)
        report = self.run_check()
        self.assertNotIn("banned-term", self.kinds(report))
        self.assertEqual(report["status"], "pass", report["violations"])

    def test_matching_face_is_exactly_name_and_alias_keys(self):
        # 匹配面钉死：键恰为 name/alias 的字符串值——label/definition/notes 等
        # 同持禁用词的键不入面（函数级直测，防匹配面悄悄放大成全字段）
        data = sc.load_yaml_from_text(
            "a:\n"
            "  name: 老完成率\n"
            "  alias: 老完成率别名\n"
            "  label: 老完成率标签\n"
            "  definition: 提及老完成率\n"
            "  notes: 老完成率\n"
            "  aliases: [老完成率]\n")
        hits = [v for v, _m, _k in sc.iter_name_alias_values(data)]
        self.assertEqual(hits, ["老完成率", "老完成率别名"])

    def test_nested_name_face_is_matched(self):
        # 通用口径递归收集：M2 behaviors[].name 撞禁用词同红（不逐模型硬列挂点）
        self.add("m1-object-model.yaml", M1)
        self.add("m2-behavior-model.yaml", M2.replace("name: 录入", "name: 录入老完成率"))
        self.add("glossary-model.yaml", BAN_GLS)
        report = self.run_check()
        self.assertIn("banned-term", self.kinds(report))
        v = next(v for v in report["violations"] if v["kind"] == "banned-term")
        self.assertIn("m2-behavior-model.yaml", v["file"])

    def test_filename_mismatch_file_skips_banned_face(self):
        # 红因纯净（沿票 13 先例）：文件名与 model_type 错挂的文件跳过禁用词匹配面，
        # 让位 filename-mismatch，不叠杂音红因
        self.add("m1-object-model.yaml", M1)
        self.add("glossary-model.yaml", BAN_GLS)
        self.add("m2-behavior-model.yaml",
                 M2.replace("model_type: BEHAVIOR", "model_type: OBJECT")
                 .replace("name: 录入", "name: 录入老完成率"))
        report = self.run_check()
        self.assertIn("filename-mismatch", self.kinds(report))
        self.assertNotIn("banned-term", self.kinds(report))


# ---------- 票 27：主集合逐字典枚举（缺 id 盲区修复；出厂断言 MID-AC1/2）----------

MID_REGISTRY = {
    "version": "1.2.0",
    "models": {
        "M1": dict(REGISTRY["models"]["M1"], profiles=["full"],
                   requiredElementFields={
                       "AGG-": ["id", "name", "alias", "aggregateType",
                                "attributes"]}),
        "M2": dict(REGISTRY["models"]["M2"], profiles=["full"],
                   requiredElementFields={
                       "BH-": ["id", "name", "ownerEntity", "behaviorType"]}),
        "GLS": dict(REGISTRY["models"]["GLS"], profiles=["full"],
                    requiredElementFields={
                        "GLS-": ["id", "term", "definition", "source"]}),
    },
}


MID_DEPS = {
    "version": "1.2.0",
    "idPrefixes": {"AGG-": "M1", "BH-": "M2", "GLS-": "GLS"},
    "refKeys": ["ownerEntity", "relatedObjectRefs"],
    "edges": [
        {"from": "M2", "field": "ownerEntity", "to": ["M1"]},
        {"from": "GLS", "field": "relatedObjectRefs", "to": ["M1"]},
    ],
}


class ElementIdEnumeration(ReqBase):
    """票 27 单测面：元素枚举去 id 锚定——主集合每个字典即元素（无 id 也枚举）。

    三形态（混入逃逸/纯无 id/空集合）+ 嵌套合法形态（attributes 字典无 id 不报）
    + 错前缀红因迁移 + 禁用词族回归抽查；真源 = tickets/27 AC 表（MID-AC1/2/3/4）。
    空壳守卫收窄为「主集合键缺失或集合为空」，集合内有字典就逐元素报缺身份字段。
    """

    def setUp(self):
        super().setUp()
        write(self.root / "schema" / "model-registry.json", json.dumps(MID_REGISTRY))
        write(self.root / "schema" / "model-deps.json", json.dumps(MID_DEPS))
        write(self.root / "demo" / "manifest.json", json.dumps(
            {"domain": "demo", "profile": "full", "schemaVersion": "1.2.0",
             "omittedModels": [
                 {"model": k, "reason": "单测基座：模型文件按需加装"}
                 for k in ("M1", "M2", "GLS")]}))

    def req_rows(self, report=None):
        return [v for v in (report or self.run_check())["violations"]
                if v["kind"] == "required-field"]

    def test_mixed_valid_and_idless_element_flags_only_idless(self):
        # MID-AC1 混入形态：合法 BH-DEMO-Record + 无 id 行为（引用全有效）→
        # 修前整域静默全绿（逃逸），修后仅无 id 元素报缺 id，合法元素零扰动
        self.add("m1-object-model.yaml", M1)
        self.add("m2-behavior-model.yaml", M2 + """  - name: 无id行为
    ownerEntity: AGG-DEMO-001
    behaviorType: COMMAND
""")
        report = self.run_check()
        rows = self.req_rows(report)
        self.assertEqual(len(rows), 1, report["violations"])
        self.assertIn("无id行为", rows[0]["message"])
        self.assertIn("缺必填字段「id」", rows[0]["message"])
        self.assertNotIn("BH-DEMO-Record", rows[0]["message"])
        self.assertGreater(rows[0]["line"], 0)

    def test_pure_idless_file_reports_per_element_not_empty_shell(self):
        # MID-AC2 纯无 id 形态：两个无 id 行为 → 逐元素两行缺 id（name 提示可指认），
        # 不再被空壳一条吞
        self.add("m2-behavior-model.yaml",
                 """model_type: BEHAVIOR
version: "1.0.0"
domain: demo
behaviors:
  - name: 无id行为甲
    behaviorType: COMMAND
  - name: 无id行为乙
    behaviorType: QUERY
""")
        rows = self.req_rows()
        self.assertEqual(len(rows), 2, rows)
        msgs = " ".join(v["message"] for v in rows)
        self.assertIn("无id行为甲", msgs)
        self.assertIn("无id行为乙", msgs)
        self.assertNotIn("空壳", msgs)

    def test_gls_pure_idless_terms_report_per_element(self):
        # MID-AC2 GLS 版：术语字典无 id → 逐元素缺 id（term 键提示），空壳不背锅
        self.add("glossary-model.yaml",
                 """model_type: GLOSSARY
version: "1.0.0"
domain: demo
terms:
  - term: 悬空术语甲
    definition: 无 id 术语甲。
    source: 合成·票 27
  - term: 悬空术语乙
    definition: 无 id 术语乙。
    source: 合成·票 27
""")
        rows = self.req_rows()
        self.assertEqual(len(rows), 2, rows)
        msgs = " ".join(v["message"] for v in rows)
        self.assertIn("悬空术语甲", msgs)
        self.assertIn("悬空术语乙", msgs)
        self.assertNotIn("空壳", msgs)

    def test_empty_terms_still_empty_shell(self):
        # MID-AC4（=REQ-AC3b 语义）：terms:[] 仍红——空壳守卫收窄后只管
        # 「主集合键缺失或集合为空」，纯空集合形态语义不回退
        self.add("glossary-model.yaml",
                 "model_type: GLOSSARY\nversion: \"1.0.0\"\ndomain: demo\nterms: []\n")
        rows = self.req_rows()
        self.assertEqual(len(rows), 1, rows)
        self.assertIn("空壳", rows[0]["message"])
        self.assertIn("GLS", rows[0]["message"])

    def test_missing_collection_key_is_empty_shell(self):
        # 收窄后另一支：主集合键整个缺失（无 behaviors 键）同样是空壳
        self.add("m2-behavior-model.yaml",
                 "model_type: BEHAVIOR\nversion: \"1.0.0\"\ndomain: demo\n")
        rows = self.req_rows()
        self.assertEqual(len(rows), 1, rows)
        self.assertIn("空壳", rows[0]["message"])

    def test_nested_attributes_without_id_not_enumerated(self):
        # MID-AC3 嵌套不误伤：attributes[] 子结构字典无 id 是合法形态，不进元素
        # 枚举（由 ref 扫描与字段检查覆盖）——对象域照旧全绿
        m1_nested = M1.replace(
            "    attributes: []",
            """    attributes:
      - name: wellCode
        label: 井号
        type: String
      - name: status
        label: 井状态
        type: String""")
        self.add("m1-object-model.yaml", m1_nested)
        self.add("m2-behavior-model.yaml", M2)
        report = self.run_check()
        self.assertEqual(report["status"], "pass", report["violations"])
        self.assertEqual(self.req_rows(report), [])

    def test_stray_prefix_id_migrates_from_empty_shell_to_identity(self):
        # 红因迁移：集合内 id 前缀不判回本模型（如 M2 集合挂 AGG- id）→
        # 修前=空壳一条（误吞），修后=缺身份字段（红因可指认，不留新盲区）
        self.add("m2-behavior-model.yaml",
                 """model_type: BEHAVIOR
version: "1.0.0"
domain: demo
behaviors:
  - id: AGG-DEMO-001
    name: 错前缀行为
    behaviorType: COMMAND
""")
        rows = self.req_rows()
        self.assertEqual(len(rows), 1, rows)
        self.assertIn("错前缀行为", rows[0]["message"])
        self.assertIn("AGG-DEMO-001", rows[0]["message"])
        self.assertNotIn("空壳", rows[0]["message"])

    def test_banned_term_scan_unaffected_by_idless_element(self):
        # 禁用词族回归抽查：无 id 元素的 name 照样进禁用词匹配面（拦截面不依赖
        # id）——与必填闸同域并行，两闸各自出红互不遮蔽
        self.add("m1-object-model.yaml", M1)
        self.add("m2-behavior-model.yaml",
                 """model_type: BEHAVIOR
version: "1.0.0"
domain: demo
behaviors:
  - name: 录入老完成率
    behaviorType: COMMAND
""")
        self.add("glossary-model.yaml", BAN_GLS)
        kinds = self.kinds()
        self.assertIn("banned-term", kinds)
        self.assertIn("required-field", kinds)


# ---------- 票 38：同域元素 id 唯一（duplicate-id，L1 身份族；出厂断言 DUP-AC1）----------

class DuplicateId(Base):
    """票 38 单测面：同一 manifest 域值之下，元素 id（id/*Id 定义键）不得重复。

    唯一性判定键 = manifest 域值（同一 domain 值之下建 id→位置索引，撞即红）；
    跨域不判（fixture 各域合法复用同形 ID）；id 索引收 id/*Id 全部定义键
    （M5 式 actorId/roleId/permissionId 跨键同值同判）；文件名错挂的文件跳过
    （红因纯净，沿票 13/16 先例）。真源 = tickets/38 AC 表（DUP-AC1）。
    本类用 Base 迷你表（无 requiredElementFields）：顺带证明 duplicate-id 闸
    独立于必填闸，不依赖 req_map 在场。
    """

    def test_duplicate_id_in_same_collection_is_l1(self):
        # DUP-AC1：同一主集合两元素同 id → duplicate-id（L1）红，
        # 报文含双位置（先出现 file:line + 后出现 file:line）与双元素名
        self.add("m1-object-model.yaml", M1 + """  - id: AGG-DEMO-001
    name: 井乙
    alias: WellB
    aggregateType: AGGREGATE_ROOT
    attributes: []
""")
        report = self.run_check()
        self.assertIn("duplicate-id", self.kinds(report))
        v = next(v for v in report["violations"] if v["kind"] == "duplicate-id")
        self.assertEqual(v["level"], "L1")
        for needle in ("AGG-DEMO-001", "井", "井乙",
                       "m1-object-model.yaml:5", "m1-object-model.yaml:10"):
            self.assertIn(needle, v["message"])
        self.assertEqual(v["line"], 10)  # 挂后出现者
        self.assertEqual(quiet_main([str(self.root)]), 1)

    def test_duplicate_id_across_files_same_domain(self):
        # 跨文件同域（跨模型同值形态）：m2 集合挂 AGG- id 与 m1 的定义撞 → 红
        self.add("m1-object-model.yaml", M1)
        self.add("m2-behavior-model.yaml",
                 M2.replace("id: BH-DEMO-Record", "id: AGG-DEMO-001"))
        v = next(v for v in self.run_check()["violations"]
                 if v["kind"] == "duplicate-id")
        self.assertIn("m1-object-model.yaml", v["message"])
        self.assertIn("m2-behavior-model.yaml", v["message"])

    def test_duplicate_id_across_definition_keys(self):
        # id/*Id 全部定义键入索引：id 与 *Id（roleId 式）键同值同判——
        # 防踩坑：M5 actorId/roleId/permissionId 任一撞另一元素 id 都算重复
        self.add("m1-object-model.yaml", M1)
        self.add("m2-behavior-model.yaml", M2 + """  - roleId: BH-DEMO-Record
    name: 跨键同值元素
    ownerEntity: AGG-DEMO-001
    behaviorType: COMMAND
""")
        v = next(v for v in self.run_check()["violations"]
                 if v["kind"] == "duplicate-id")
        self.assertIn("roleId", v["message"])

    def test_unique_ids_still_pass(self):
        # 正例红线：同域全异 id 零扰动（valid-domain/bohai 形态）
        self.add("m1-object-model.yaml", M1)
        self.add("m2-behavior-model.yaml", M2)
        report = self.run_check()
        self.assertEqual(report["status"], "pass", report["violations"])
        self.assertNotIn("duplicate-id", self.kinds(report))

    def test_same_id_in_other_domain_not_reported(self):
        # 跨域不判：另一域（manifest 域值不同）合法复用同形 ID → 无 duplicate-id
        self.add("m1-object-model.yaml", M1)
        write(self.root / "other" / "manifest.json", json.dumps(
            {"domain": "other", "profile": "full", "schemaVersion": "1.0.0",
             "omittedModels": [
                 {"model": k, "reason": "单测：另一域按需加装"}
                 for k in ("M1", "M2", "GLS")]}))
        write(self.root / "other" / "m1-object-model.yaml", M1)
        kinds = self.kinds()
        self.assertNotIn("duplicate-id", kinds)
        self.assertEqual(kinds, [])

    def test_same_domain_value_across_dirs_shares_namespace(self):
        # 唯一性判定键=manifest 域值：两目录域值相同 → 同一命名空间，撞 id 照红
        #（报文双位置各指一个目录下的文件）
        self.add("m1-object-model.yaml", M1)
        write(self.root / "twin" / "manifest.json", json.dumps(
            {"domain": "demo", "profile": "full", "schemaVersion": "1.0.0",
             "omittedModels": [
                 {"model": k, "reason": "单测：孪生域按需加装"}
                 for k in ("M1", "M2", "GLS")]}))
        write(self.root / "twin" / "m1-object-model.yaml", M1)
        v = next(v for v in self.run_check()["violations"]
                 if v["kind"] == "duplicate-id")
        self.assertIn("twin", v["message"])
        self.assertIn("demo", v["message"])

    def test_filename_mismatch_file_skips_duplicate_gate(self):
        # 红因纯净：文件名与 model_type 错挂的文件跳过 id 索引
        #（OBJECT 内容错挂 m2 文件名，其 AGG- id 不与 m1 撞报 duplicate-id，
        # 让位 filename-mismatch，沿票 13/16 先例）
        self.add("m1-object-model.yaml", M1)
        self.add("m2-behavior-model.yaml", M1)
        report = self.run_check()
        self.assertIn("filename-mismatch", self.kinds(report))
        self.assertNotIn("duplicate-id", self.kinds(report))


# ---------- 票 41：L3 确定性闸（l3-*；指标/SQL/安全确定性可判子集，出厂断言 L3-AC1a–d）----------

L3_REGISTRY = {
    "version": "1.2.0",
    "models": {
        "M1": dict(REGISTRY["models"]["M1"], profiles=["full"]),
        "M2": dict(REGISTRY["models"]["M2"], profiles=["full"]),
        "M3": {
            "name": "规则模型", "yamlFile": "m3-rule-model.yaml",
            "modelType": "RULE", "camp": "business-core",
            "consumers": ["runtime", "build"], "profiles": ["full"],
            "dependsOn": ["M1", "M2"], "lockedFields": {},
        },
        "M7": {
            "name": "查询统计与报表模型", "yamlFile": "m7-report-model.yaml",
            "modelType": "REPORT", "camp": "business-core",
            "consumers": ["runtime", "build"], "profiles": ["full"],
            "dependsOn": ["M1", "M2"], "lockedFields": {},
        },
    },
}

L3_DEPS = {
    "version": "1.2.0",
    "idPrefixes": {"AGG-": "M1", "BH-": "M2", "RULE-": "M3", "QR-": "M7"},
    "refKeys": ["ownerEntity", "behaviorRef"],
    "edges": [
        {"from": "M2", "field": "ownerEntity", "to": ["M1"]},
        {"from": "M7", "field": "behaviorRef", "to": ["M2"]},
    ],
}

L3_M1 = """model_type: OBJECT
version: "1.0.0"
domain: demo
aggregates:
  - id: AGG-DEMO-001
    name: 井
    alias: Well
    aggregateType: AGGREGATE_ROOT
    attributes:
      - { name: wellCode, label: 井号, type: String }
      - { name: currentStatus, label: 状态, type: String }
  - id: AGG-DEMO-002
    name: 单井日产量记录
    alias: DailyProductionRecord
    aggregateType: AGGREGATE_ROOT
    attributes:
      - { name: outputVolume, label: 产液量, type: Decimal }
      - { name: prodDate, label: 生产日期, type: Date }
"""

L3_M2 = """model_type: BEHAVIOR
version: "1.0.0"
domain: demo
behaviors:
  - id: BH-DEMO-Query
    name: 查询单井日产量
    ownerEntity: AGG-DEMO-001
    behaviorType: QUERY
    triggerType: USER_ACTION
    preconditions: []
    postconditions: []
    appliedRules: []
    requiredPermissions: []
"""

L3_M3 = """model_type: RULE
version: "1.0.0"
domain: demo
rules:
  - id: RULE-DEMO-001
    name: 日产量非负
    ruleType: VALIDATION
    inputParams:
      - name: outputVolume
        type: Decimal
        sourceField: dailyProduction.outputVolume
        required: true
    outputType: Boolean
    expression: outputVolume >= 0
  - id: RULE-DEMO-002
    name: 叙述式规则
    ruleType: TRANSFORMATION
    inputParams:
      - name: wellCode
        type: String
        sourceField: well.wellCode
        required: true
    outputType: String
    narrative: 把井号归一化为标准写法
"""

L3_M7 = """model_type: REPORT
version: "1.0.0"
domain: demo
query_reports:
  - id: QR-DEMO-001
    name: 单井日产量查询
    alias: wellDailyOutputQuery
    objectType: DETAIL_QUERY
    behaviorRef: BH-DEMO-Query
    sourceObjects:
      - objectRef: AGG-DEMO-001
        alias: w
        primary: true
      - objectRef: AGG-DEMO-002
        alias: d
        primary: false
    resultColumns:
      - name: wellCode
        label: 井号
        dataType: String
        sourceExpression: w.wellCode
      - name: outputVolume
        label: 产液量
        dataType: Decimal
        sourceExpression: d.outputVolume
"""


class L3Base(Base):
    """票 41 基座：M1/M2/M3/M7 迷你注册表（OBJECT/RULE/REPORT 进 L3 扫描面；
    RULE 无 requiredElementFields——L3 与必填闸解耦的证明面，同票 38 先例）。"""

    def setUp(self):
        super().setUp()
        write(self.root / "schema" / "model-registry.json", json.dumps(L3_REGISTRY))
        write(self.root / "schema" / "model-deps.json", json.dumps(L3_DEPS))
        write(self.root / "demo" / "manifest.json", json.dumps(
            {"domain": "demo", "profile": "full", "schemaVersion": "1.2.0",
             "omittedModels": [
                 {"model": k, "reason": "单测基座：模型文件按需加装"}
                 for k in ("M1", "M2", "M3", "M7")]}))

    def add_l3_domain(self):
        self.add("m1-object-model.yaml", L3_M1)
        self.add("m2-behavior-model.yaml", L3_M2)
        self.add("m3-rule-model.yaml", L3_M3)
        self.add("m7-report-model.yaml", L3_M7)

    def l3_rows(self, report=None, kind=None):
        return [v for v in (report or self.run_check())["violations"]
                if v["level"] == "L3" and (kind is None or v["kind"] == kind)]


class L3Helpers(unittest.TestCase):
    """纯函数直测：匹配序分层与 sourceField 拆段（判定基准=存量反推，票 41 防踩坑）。"""

    def test_match_order_layers(self):
        # 匹配序 id→alias→name→别名驼峰词唯一包含，首层命中即解析
        aggs = [
            {"id": "AGG-X-001", "name": "日产", "alias": "OilProductionDaily",
             "attrs": set()},
            {"id": "AGG-X-002", "name": "注水", "alias": "WaterInjectionDaily",
             "attrs": set()},
        ]
        agg, layer = sc.l3_resolve_object_segment("AGG-X-002", aggs)
        self.assertEqual((agg["id"], layer), ("AGG-X-002", "id"))
        agg, layer = sc.l3_resolve_object_segment("waterinjectiondaily", aggs)
        self.assertEqual((agg["id"], layer), ("AGG-X-002", "alias"))  # 大小写不敏感
        agg, layer = sc.l3_resolve_object_segment("日产", aggs)
        self.assertEqual((agg["id"], layer), ("AGG-X-001", "name"))
        # 自造短名（schema.md §6 示例形态）：非 id/alias/name 直配，靠末层唯一包含
        agg, layer = sc.l3_resolve_object_segment("dailyProduction", aggs)
        self.assertEqual((agg["id"], layer), ("AGG-X-001", "alias-tokens"))
        self.assertEqual(sc.l3_resolve_object_segment("nope", aggs), (None, None))

    def test_split_source_field_shapes(self):
        # 双段 / 中文注记后缀剥离 / 非双段（无承载字段注记）三形态
        self.assertEqual(
            sc.l3_split_source_field("dailyProduction.oilOutput（区块月合计）"),
            ("dailyProduction", "oilOutput"))
        self.assertEqual(sc.l3_split_source_field("well.currentStatus"),
                         ("well", "currentStatus"))
        self.assertIsNone(sc.l3_split_source_field("存水率变动（无承载字段，待 Owner）"))
        self.assertIsNone(sc.l3_split_source_field(None))

    def test_sql_blacklist_word_boundary(self):
        # 词边界：UPDATE 命中；updated_at/created_at 列名不误伤；大小写不敏感。
        # 注释里出现独立黑名单词照命中（纯词扫描不解析注释——确定性取舍，lessons/41）
        for bad in ("UPDATE t SET a=1", "update t set a=1", "TRUNCATE TABLE t",
                    "-- 增量处理 delete 旧表"):
            self.assertTrue(sc.L3_SQL_BLACKLIST_RE.search(bad), bad)
        for good in ("SELECT updated_at FROM t WHERE created_at > :d",):
            self.assertFalse(sc.L3_SQL_BLACKLIST_RE.search(good), good)


class L3DeterministicGate(L3Base):
    """票 41 单测面：L3 四项检查。真源 = tickets/41-L3确定性闸.md AC 表（AC1a–d）
    + 可机判子集清单（L0 裁决）。红因纯净与文件名错挂让位沿票 13/16 先例。"""

    def test_valid_l3_domain_passes(self):
        # 正例：自造短名 dailyProduction 末层解析；叙述式规则/无 referenceSql 全绿
        self.add_l3_domain()
        report = self.run_check()
        self.assertEqual(report["status"], "pass", report["violations"])
        self.assertEqual(report["levels"], {"L1": 0, "L2": 0, "L3": 0, "L4": 0})

    def test_count_line_and_json_cover_l3(self):
        # AC4：人类输出计数行含 L3 段；--json levels 含 L3
        self.add_l3_domain()
        self.add("m3-rule-model.yaml",
                 L3_M3.replace("sourceField: dailyProduction.outputVolume",
                               "sourceField: dailyProduction.missingField"))
        buf = io.StringIO()
        with redirect_stdout(buf):
            sc.main([str(self.root)])
        self.assertIn("L1: 0 | L2: 0 | L3: 1 | L4: 0", buf.getvalue())
        self.assertEqual(self.run_check()["levels"]["L3"], 1)

    def test_source_field_missing_attribute_is_l3(self):
        # AC1a：字段段不在所指聚合 attributes → l3-source-field（对象段解析成功，
        # 红因钉在字段上——报文含规则 ID 与字段名，行级定位）
        self.add_l3_domain()
        self.add("m3-rule-model.yaml",
                 L3_M3.replace("sourceField: dailyProduction.outputVolume",
                               "sourceField: dailyProduction.missingField"))
        rows = self.l3_rows(kind="l3-source-field")
        self.assertEqual(len(rows), 1, rows)
        v = rows[0]
        self.assertEqual(v["level"], "L3")
        for needle in ("RULE-DEMO-001", "missingField"):
            self.assertIn(needle, v["message"])
        self.assertIn("m3-rule-model.yaml", v["file"])
        self.assertGreater(v["line"], 0)
        self.assertEqual(quiet_main([str(self.root)]), 1)

    def test_source_field_unresolvable_object_is_l3(self):
        # AC1a 乙：对象段全匹配序未唯一命中 → 本码承载（sourceField 非 ref 键，
        # dangling-ref 不管，红因不外溢）
        self.add_l3_domain()
        self.add("m3-rule-model.yaml",
                 L3_M3.replace("sourceField: dailyProduction.outputVolume",
                               "sourceField: noSuchObject.outputVolume"))
        rows = self.l3_rows(kind="l3-source-field")
        self.assertEqual(len(rows), 1, rows)
        self.assertIn("noSuchObject", rows[0]["message"])

    def test_ambiguous_relaxed_match_is_not_resolved(self):
        # 末层防歧义：对象段驼峰词被两个聚合 alias 同时包含 → 不唯一=不解析（红）
        self.add_l3_domain()
        self.add("m1-object-model.yaml", L3_M1 + """  - id: AGG-DEMO-003
    name: 日产量台账
    alias: DailyProductionLedger
    aggregateType: AGGREGATE_ROOT
    attributes: []
""")
        rows = self.l3_rows(kind="l3-source-field")
        self.assertEqual(len(rows), 1, rows)
        self.assertIn("dailyProduction", rows[0]["message"])
        self.assertIn("解析不到", rows[0]["message"])

    def test_annotation_suffix_is_stripped(self):
        # 存量形态兼容（bohai）：中文注记后缀「（区块月合计）」不挡解析与字段判定
        self.add_l3_domain()
        self.add("m3-rule-model.yaml",
                 L3_M3.replace("sourceField: dailyProduction.outputVolume",
                               "sourceField: dailyProduction.outputVolume（区块月合计）"))
        self.assertEqual(self.l3_rows(), [])

    def test_single_segment_source_field_not_judged(self):
        # 无承载字段注记（无点值，RULE-BOHAI-008 形态）不在 L3-1 机判面
        self.add_l3_domain()
        self.add("m3-rule-model.yaml",
                 L3_M3.replace("sourceField: dailyProduction.outputVolume",
                               "sourceField: 拟合基线（无承载字段，待 Owner）"))
        self.assertEqual(self.l3_rows(), [])

    def test_expression_undeclared_alias_is_l3(self):
        # AC1b：sourceExpression 引用未声明别名 → l3-expression-ref
        self.add_l3_domain()
        self.add("m7-report-model.yaml",
                 L3_M7.replace("sourceExpression: w.wellCode",
                               "sourceExpression: x.wellCode"))
        rows = self.l3_rows(kind="l3-expression-ref")
        self.assertEqual(len(rows), 1, rows)
        v = rows[0]
        for needle in ("QR-DEMO-001", "x.wellCode", "未在 sourceObjects 声明"):
            self.assertIn(needle, v["message"])
        self.assertIn("m7-report-model.yaml", v["file"])
        self.assertGreater(v["line"], 0)

    def test_expression_field_not_in_aggregate_is_l3(self):
        # AC1b 乙：别名已声明但字段不在所指聚合 attributes → 同码
        self.add_l3_domain()
        self.add("m7-report-model.yaml",
                 L3_M7.replace("sourceExpression: d.outputVolume",
                               "sourceExpression: d.nonexistent"))
        rows = self.l3_rows(kind="l3-expression-ref")
        self.assertEqual(len(rows), 1, rows)
        for needle in ("d.nonexistent", "AGG-DEMO-002"):
            self.assertIn(needle, rows[0]["message"])

    def test_dangling_objectref_stays_with_dangling_ref(self):
        # 红因不混（票面设计裁决）：objectRef 悬空 → dangling-ref（L2）管辖，L3-2 不叠红
        self.add_l3_domain()
        self.add("m7-report-model.yaml",
                 L3_M7.replace("AGG-DEMO-001", "AGG-DEMO-999"))
        report = self.run_check()
        self.assertEqual(self.l3_rows(report), [])
        self.assertIn("dangling-ref", self.kinds(report))

    def test_reference_sql_dml_is_l3(self):
        # AC1c：referenceSql 在场且含 DML 词 → l3-sql-readonly（大小写不敏感）
        self.add_l3_domain()
        self.add("m7-report-model.yaml",
                 L3_M7.replace(
                     "    behaviorRef: BH-DEMO-Query",
                     "    behaviorRef: BH-DEMO-Query\n"
                     "    referenceSql: \"update well_info set current_status ="
                     " '停产' where well_code = :w\""))
        rows = self.l3_rows(kind="l3-sql-readonly")
        self.assertEqual(len(rows), 1, rows)
        v = rows[0]
        self.assertIn("QR-DEMO-001", v["message"])
        self.assertIn("UPDATE", v["message"])
        self.assertGreater(v["line"], 0)
        self.assertEqual(quiet_main([str(self.root)]), 1)

    def test_reference_sql_column_names_not_hit(self):
        # 词边界防误伤：updated_at/created_at 式列名出现不触发（\b 边界）
        self.add_l3_domain()
        self.add("m7-report-model.yaml",
                 L3_M7.replace(
                     "    behaviorRef: BH-DEMO-Query",
                     "    behaviorRef: BH-DEMO-Query\n"
                     "    referenceSql: \"SELECT well_code, updated_at FROM"
                     " well_info WHERE created_at > :d\""))
        report = self.run_check()
        self.assertEqual(self.l3_rows(report), [])
        self.assertEqual(report["status"], "pass", report["violations"])

    def test_expression_type_rule_without_expression_is_l3(self):
        # AC1d：ruleType=EXPRESSION 缺 expression → l3-rule-form
        self.add_l3_domain()
        self.add("m3-rule-model.yaml",
                 L3_M3.replace("    ruleType: VALIDATION", "    ruleType: EXPRESSION")
                 .replace("    expression: outputVolume >= 0\n", ""))
        rows = self.l3_rows(kind="l3-rule-form")
        self.assertEqual(len(rows), 1, rows)
        v = rows[0]
        for needle in ("RULE-DEMO-001", "EXPRESSION"):
            self.assertIn(needle, v["message"])

    def test_rule_without_any_form_is_l3(self):
        # 二选一形态（schema.md §6）：expression/narrative 均不在场 → 每规则一红
        self.add_l3_domain()
        self.add("m3-rule-model.yaml",
                 L3_M3.replace("    expression: outputVolume >= 0\n", "")
                 .replace("    narrative: 把井号归一化为标准写法\n", ""))
        rows = self.l3_rows(kind="l3-rule-form")
        self.assertEqual(len(rows), 2, rows)

    def test_rule_type_missing_not_double_reported(self):
        # ruleType 缺失归 L1 required-field 管辖（真仓 requiredElementFields 面），
        # L3-4 跳过不叠红因——红因不混
        self.add_l3_domain()
        self.add("m3-rule-model.yaml",
                 "\n".join(l for l in L3_M3.splitlines()
                           if not l.startswith("    ruleType")) + "\n")
        self.assertEqual(self.l3_rows(kind="l3-rule-form"), [])

    def test_filename_mismatch_file_skips_l3(self):
        # 红因纯净：内容错挂文件名 → 跳过 L3 扫描，让位 filename-mismatch
        self.add_l3_domain()
        self.add("m7-report-model.yaml",
                 L3_M3.replace("sourceField: dailyProduction.outputVolume",
                               "sourceField: dailyProduction.missingField"))
        report = self.run_check()
        self.assertEqual(self.l3_rows(report), [])
        self.assertIn("filename-mismatch", self.kinds(report))


if __name__ == "__main__":
    unittest.main()


class BannedTermDomainPairing(Base):
    """票 72（第十轮 T8 回归钉）：L4 禁用词按域内配对——A 域禁用词不得命中
    B 域词面（单域/仓根双跑一致）；本域命中照红（防修过头）。
    T8 实况（2026-09-27 探针）：his 建模重构后现行闸已是域内配对，本类把
    两态钉成回归测试防回退。"""

    BANNED_GLS = """model_type: GLOSSARY
version: "1.0.0"
domain: demo
terms:
  - id: GLS-DEMO-002
    term: 老完成率
    aliases: [旧完成率]
    definition: 废弃口径。
    status: 禁用（替代：产量完成率）
"""

    DEMO2_M1 = """model_type: OBJECT
version: "1.0.0"
domain: demo2
aggregates:
  - id: AGG-DEMO2-001
    name: 老完成率对照聚合
    alias: legacyProbe
    aggregateType: AGGREGATE_ROOT
    attributes: []
"""

    def _seed_two_domains(self):
        self.add("glossary-model.yaml", self.BANNED_GLS)  # demo：禁用词源
        self.add("manifest.json", json.dumps(
            {"domain": "demo2", "profile": "full", "schemaVersion": "1.0.0",
             "omittedModels": [{"model": "M2", "reason": "单测：按需加装"},
                               {"model": "GLS", "reason": "单测：demo2 无 GLS"}]}),
            domain="demo2")
        self.add("m1-object-model.yaml", self.DEMO2_M1, domain="demo2")

    def test_t8_cross_domain_wordface_stays_green(self):
        # T8 复现样本：demo 禁用词「老完成率」出现在 demo2 词面 → 单域/仓根双绿
        self._seed_two_domains()
        root_report = self.run_check(self.root)
        self.assertEqual(root_report["status"], "pass",
                         [v for v in root_report["violations"]
                          if v["kind"] == "banned-term"])
        sub = self.run_check(self.root / "demo2")
        self.assertEqual(sub["status"], "pass", sub["violations"])

    def test_own_domain_banned_match_still_red(self):
        # 负变体：demo 自家词面命中自家禁用词 → 仓根/单域照红（防修过头）
        self.add("glossary-model.yaml", self.BANNED_GLS)
        self.add("m1-object-model.yaml",
                 M1.replace("name: 井", "name: 老完成率对照聚合"))
        report = self.run_check(self.root)
        self.assertIn("banned-term", self.kinds(report))
        sub = self.run_check(self.root / "demo")
        self.assertIn("banned-term", [v["kind"] for v in sub["violations"]])


class CrossDomainIsolation(ConsBase):
    """票 76（第十三轮 P1-1/P1-2 回归钉）：跨域借 ID 与跨域绑定必须红——
    第十轮 T4 用不存在的 ID 验证隔离属假阴性；本类用真实他域 ID 注入实证。
    基座用 ConsBase（M1–M7 五模型面），demo2 为第二域（Vite 式按需加装）。"""

    DEMO2_MANIFEST = {"domain": "demo2", "profile": "full", "schemaVersion": "1.0.0",
                      "omittedModels": [{"model": k, "reason": "单测：按需加装"}
                                        for k in ("M1", "M2", "M5", "M6", "M7")]}

    def _seed_two_domains(self, m7_cross_behavior_ref):
        # demo 域：五文件全装（M1–M7），正向合法
        self.add_cons_domain()
        # demo2 域：仅 M1+M2（有 QUERY 行为），M7 指向 demo 域行为（跨域借 ID）
        self.add("manifest.json", json.dumps(self.DEMO2_MANIFEST), domain="demo2")
        m2_text = M2.replace("domain: demo", "domain: demo2").replace(
            "BH-DEMO-Record", "BH-DEMO2-Record").replace(
            "BH-DEMO-Query", "BH-DEMO2-Query").replace(
            "    appliedRules:\n      - RULE-DEMO-002\n      - RULE-DEMO-003\n",
            "    appliedRules: []\n")
        self.add("m2-behavior-model.yaml", m2_text, domain="demo2")
        m7_cross = CONS_M7.replace("domain: demo", "domain: demo2").replace(
            "BH-DEMO-Query", m7_cross_behavior_ref)
        self.add("m7-report-model.yaml", m7_cross, domain="demo2")

    def test_cross_domain_real_id_borrow_is_red(self):
        # demo2 m7 的 ownerEntity 指向 demo 域真实聚合 AGG-DEMO-001 → 仓根/单域都红
        self._seed_two_domains("AGG-DEMO-001")
        report = self.run_check(self.root)
        self.assertIn("dangling-ref", self.kinds(report))
        # 单域 demo2 也红
        sub = self.run_check(self.root / "demo2")
        self.assertIn("dangling-ref", [v["kind"] for v in sub["violations"]])

    def test_consistency_buckets_domain_scoped(self):
        # P1-2 回归：demo2 用独立 M2+M7（不与 demo 共享行为），各域一致性独立判定
        self._seed_two_domains("BH-DEMO2-Query")  # demo2 的 M7 引用 demo2 自己的 QUERY 行为
        report = self.run_check(self.root)
        # demo 自家绑定不被拉红
        demo_reds = [v for v in report["violations"]
                     if "QR-DEMO-001" in v.get("message", "") and "not-one-to-one" in v.get("kind", "")]
        self.assertEqual(demo_reds, [])
        # demo2 自家绑定也不被拉红（独立域内闭合）
        self.assertNotIn("consistency-not-one-to-one", self.cons_kinds(report))
