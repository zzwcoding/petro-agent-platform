"""kb 结构图单测（P1F-05 方案 A）——LLM 出图＋逐字校验＋复合规则复检＋规则回退＋版本缓存。

语料注源（拟造数据，形态注源评测报告存照）：
- corpus/report_A_f26诱导求产.txt——eval/results/评测报告.md §4.5 A-正7 存照
  （f26 长正文句吞章名＋章号错）；第 7 行「12 mm 油嘴工作制度」为规则面漏判形
  （RE 命中/短/无句读/无表格特征）——LLM 边际回归锚。
- corpus/report_B_f42检泵月报.txt——§5 观察 1 存照（f42「章节 03 2026　7　4.5%…」
  表格行误判）＋B-正4 W-21 明细行形态。
- corpus/teach_prototype_n02样例.txt——页面 RAW_TEXT 同源口径（设定书 §A.1），
  markdown 章词/数字点级/第 N 章三支标题形。
红线：桩 LLM 永不触网（B6）；kb_db 夹具复用同目录 conftest。
"""

import json
import logging
from pathlib import Path
from typing import Any

from app.domains.gateway import Completion, GatewayService
from app.domains.gateway.store import SpendRecord, ensure_gateway_tables
from app.domains.kb import KbService
from app.domains.kb import domain as d
from app.domains.kb.store import UploadStore
from app.infra.eventbus import InMemoryEventBus
from app.infra.llm_client import LlmCompletion

CORPUS_DIR = Path(__file__).parent / "corpus"
CORPUS_A = (CORPUS_DIR / "report_A_f26诱导求产.txt").read_text(encoding="utf-8")
CORPUS_B = (CORPUS_DIR / "report_B_f42检泵月报.txt").read_text(encoding="utf-8")
CORPUS_C = (CORPUS_DIR / "teach_prototype_n02样例.txt").read_text(encoding="utf-8")

ACTOR = "阿强 · 平台运维"
LIB_NAME = "完井报告库"

# 受控模型注册表（字面假值——tests/domains/gateway/conftest.py 同源形状）。
_GATEWAY_TEST_YAML = """\
models:
  - alias: petro-main
    provider: anthropic
    model: MiniMax-M3
    base_url: https://main.example.test
    api_key: sk-test-main
    context_window: 1000000
    group: standard
    name: MiniMax-M3
    access: Anthropic 兼容接口 · 测试线路
    note: 问答/问数/问智默认出口
  - alias: petro-lite
    provider: anthropic
    model: glm-5.3-flash
    base_url: https://lite.example.test
    api_key: sk-test-lite
    context_window: 1000000
    group: lite
    name: glm-5.3-flash
    access: Anthropic 兼容接口 · 测试线路
    note: 备用/降级组——fallback 与预算熔断的便宜出口
routing:
  default: petro-main
  fallback_order: [petro-main, petro-lite]
prices:
  default:
    input_per_mtok: 1.0
    output_per_mtok: 3.0
gateway:
  allowed_fails: 2
  cooldown_seconds: 60
  num_retries: 3
  request_timeout: 30
"""


class FakeStorage:
    """内存对象存储（同 conftest FakeObjectStorage 形状——本文件自带防耦合）。"""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def put(self, key: str, data: bytes) -> None:
        self.objects[key] = data

    async def presign_put(self, key: str, *, ttl_seconds: int = 1800) -> str:
        return f"https://minio.test/put/{key}"

    async def presign_get(self, key: str, *, ttl_seconds: int = 3600) -> str:
        return f"https://minio.test/get/{key}"

    async def exists(self, key: str) -> bool:
        return key in self.objects

    async def get_bytes(self, key: str) -> bytes:
        if key not in self.objects:
            raise KeyError(key)
        return self.objects[key]


class ScriptedCompleter:
    """caller 感知桩 LLM（记录调用序；answers 缺省应答不可解析→规则回退路径）。"""

    def __init__(self, answers: dict[str, str | Exception] | None = None) -> None:
        self.answers = answers or {}
        self.calls: list[tuple[str, str]] = []

    async def complete(
        self, alias: str, messages: list[dict[str, str]], *, caller: str, **params: Any
    ) -> Completion:
        content = messages[-1]["content"]
        self.calls.append((caller, content))
        answer: str | Exception = self.answers.get(caller, "应答")
        if isinstance(answer, Exception):
            raise answer
        return Completion(
            content=answer,
            prompt_tokens=10,
            completion_tokens=5,
            usage_estimated=False,
            call_id="call-stub",
            cost_yuan=0.0001,
            fallback=False,
            served_alias=alias,
        )


def _make_service(kb_db: Any, completer: Any) -> tuple[KbService, FakeStorage]:
    storage = FakeStorage()
    service = KbService(kb_db, completer, storage, eventbus=InMemoryEventBus())
    return service, storage


async def _make_lib(service: KbService) -> str:
    receipt = await service.create_library(LIB_NAME, "completion", ACTOR)
    return receipt.lib_id


async def _wait_done(service: KbService, task_id: str) -> None:
    import asyncio
    import time

    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        task = await service.ingest_task(task_id)
        if task.state in ("done", "failed"):
            assert task.state == "done", f"入库未完成：{task.state} {task.reason}"
            return
        await asyncio.sleep(0.02)
    raise TimeoutError("入库等待超时")


async def _ingest(
    service: KbService, storage: FakeStorage, lib_id: str, filename: str, content: str
) -> str:
    receipt = await service.upload_init(filename, 2048, lib_id, ACTOR)
    upload = await UploadStore(service._db).get(receipt.upload_id)
    assert upload is not None
    await storage.put(upload.object_key, content.encode("utf-8"))
    confirm = await service.upload_confirm(receipt.upload_id, ACTOR)
    await _wait_done(service, confirm.task_id)
    return confirm.task_id


async def _chunk_rows(service: KbService, report_id: str) -> list[tuple[str, str]]:
    """原文块片段集（含父块，落卷序——字节级一致性比对面）。

    落卷序按 id 数字尾缀归一（store 读面按 id 字典序，f10 先于 f2 的存量排序
    怪癖与本票无关，测试侧归一后比对字节级一致）。"""
    import re as _re

    frags = await service._fragments.for_report(report_id)
    rows = [(f.section or "", f.hit_text or "") for f in frags if f.type == "原文块"]

    def _seq(pair: tuple[str, str]) -> int:
        frag = next(f for f in frags if (f.section or "", f.hit_text or "") == pair)
        m = _re.search(r"(\d+)$", frag.id)
        return int(m.group(1)) if m else 0

    return sorted(rows, key=_seq)


def _structure_json(picks: list[tuple[int, str, int]]) -> str:
    """LLM 结构图应答脚手架（line_no 1 基——提示词口径）。"""
    return json.dumps(
        {"headings": [{"line_no": n, "title": t, "level": v} for n, t, v in picks]},
        ensure_ascii=False,
    )


def _corpus_a_llm_picks(lines: list[str]) -> list[tuple[int, str, int]]:
    """corpus A 真实标题行（1 基行号）：六/七/八三章。"""
    return [(2, lines[1], 1), (4, lines[3], 1), (9, lines[8], 1)]


# ---------- 域纯语义：复合规则四条件（规则面单独有测、不依赖 LLM） ----------


class TestHeadingRule:
    def test_f26_long_body_not_heading(self) -> None:
        line = CORPUS_A.splitlines()[4]
        assert "12 mm 油嘴制度下折算" in line  # 注源自检：正是 f26 存照行
        assert d.is_heading_line(line) is False

    def test_f26_variant_short_body_is_rule_margin(self) -> None:
        # 规则面漏判形（RE 命中/13 字/无句读/无表格特征）——规则放行＝LLM 边际，
        # 回归锚：本行由 LLM 图边界剔除（见 TestChunkConsumesStructure）。
        assert d.is_heading_line("12 mm 油嘴工作制度") is True

    def test_f42_table_rows_not_heading(self) -> None:
        assert d.is_heading_line("2026　7　4.5%　渤中34-5") is False
        assert d.is_heading_line("512　4.5　52.3") is False
        assert d.is_heading_line("W-21　512　4.5　52.3") is False

    def test_tail_sentence_punct_not_heading(self) -> None:
        assert d.is_heading_line("1 概述。") is False
        assert d.is_heading_line("2 进展；") is False
        assert d.is_heading_line("3 小结！") is False

    def test_normal_headings_pass_with_levels(self) -> None:
        for line, level in [
            ("1 概述", 1),
            ("1.1 投产信息", 2),
            ("第3章 检泵作业", 1),
            ("# 第一章 基本信息", 1),
            ("12.3.4 细分项", 2),
        ]:
            assert d.is_heading_line(line) is True, line
            info = d._section_of(line)
            assert info is not None and info[0] == level

    def test_overlong_numbered_heading_demoted(self) -> None:
        # 超长标题归正文的不对称取舍（票面验收 b）。
        line = "1 " + "超长章节标题" * 8
        assert len(line) > d.HEADING_MAX_CHARS
        assert d.is_heading_line(line) is False

    def test_blank_line_not_heading(self) -> None:
        assert d.is_heading_line("") is False
        assert d.is_heading_line("   ") is False


# ---------- 域纯语义：LLM 应答解析＋逐字校验＋规则复检 ----------


class TestParseAndValidate:
    def test_parse_lenient_fences_and_prose(self) -> None:
        payload = _structure_json([(2, "第六章 管柱结构与完井液", 1)])
        for raw in (
            f"```json\n{payload}\n```",
            f"```\n{payload}\n```",
            f"前言杂文 {payload} 后记杂文",
        ):
            headings = d.parse_structure_json(raw)
            assert len(headings) == 1
            assert headings[0].line_no == 1  # 1 基转 0 基
            assert headings[0].title == "第六章 管柱结构与完井液"

    def test_parse_garbage_forms_yield_empty(self) -> None:
        for raw in (
            "完全没有 JSON",
            "{broken",
            '{"result": 1}',
            '{"headings": "不是列表"}',
            '{"headings": ["不是对象"]}',
            '{"headings": [{"line_no": true, "title": "x", "level": 1}]}',
            '{"headings": [{"line_no": "2", "title": "x", "level": 1}]}',
            '{"headings": [{"line_no": 2, "title": 3, "level": 1}]}',
            '{"headings": [{"line_no": 2, "title": "x", "level": 3}]}',
        ):
            assert d.parse_structure_json(raw) == [], raw

    def test_validate_verbatim_miss_voids_whole_map(self) -> None:
        lines = CORPUS_A.splitlines()
        # 幻觉标题（文档不存在）
        assert (
            d.validate_structure_map(
                d.parse_structure_json(_structure_json([(1, "凭空捏造的第九章 幻觉标题", 1)])),
                lines,
            )
            is None
        )
        # 行号越界
        assert (
            d.validate_structure_map(
                d.parse_structure_json(_structure_json([(99, "第八章 措施效果评价", 1)])), lines
            )
            is None
        )
        # 标题真实存在但行号指错行——行号也是校验对象
        assert (
            d.validate_structure_map(
                d.parse_structure_json(_structure_json([(6, "第八章 措施效果评价", 1)])), lines
            )
            is None
        )

    def test_validate_strip_equal_passes(self) -> None:
        text = "  第六章 管柱结构与完井液  \n正文。\n"
        headings = d.parse_structure_json(
            _structure_json([(1, "第六章 管柱结构与完井液", 1)])
        )
        m = d.validate_structure_map(headings, text.splitlines())
        assert m is not None and m.source == "llm"

    def test_validate_duplicate_line_no_voids(self) -> None:
        lines = CORPUS_A.splitlines()
        raw = json.dumps(
            {
                "headings": [
                    {"line_no": 2, "title": lines[1], "level": 1},
                    {"line_no": 2, "title": lines[1], "level": 1},
                ]
            },
            ensure_ascii=False,
        )
        assert d.validate_structure_map(d.parse_structure_json(raw), lines) is None

    def test_refine_drops_single_rule_violating_row(self) -> None:
        # 逐字命中但越四条件的行（8 mm 长句带句尾句读）——单行剔除而非整图作废。
        lines = CORPUS_A.splitlines()
        raw = _structure_json(
            [
                (2, lines[1], 1),
                (6, lines[5], 1),  # 逐字真实但行长>40＋句尾。
                (9, lines[8], 1),
            ]
        )
        m = d.validate_structure_map(d.parse_structure_json(raw), lines)
        assert m is not None
        refined = d.refine_structure_map(m, lines)
        assert refined.source == "llm"
        assert [h.line_no for h in refined.headings] == [1, 8]

    def test_snapshot_roundtrip_and_malformed(self) -> None:
        m = d.StructureMap(
            headings=(d.HeadingLine(line_no=1, title="1 概述", level=1),), source="llm"
        )
        snap = m.to_snapshot("sha-abc")
        assert snap["text_sha256"] == "sha-abc"
        assert d.StructureMap.from_snapshot(snap) == m
        assert d.StructureMap.from_snapshot(None) is None
        assert d.StructureMap.from_snapshot({"headings": []}) is None
        bad = m.to_snapshot("sha")
        bad["headings"][0]["level"] = 9
        assert d.StructureMap.from_snapshot(bad) is None


# ---------- 域纯语义：chunk 消费结构图（smart/mixed） ----------


class TestChunkConsumesStructure:
    def test_rules_map_chunk_equivalence_three_corpus(self) -> None:
        for text in (CORPUS_A, CORPUS_B, CORPUS_C):
            assert d.chunk_text(text, "smart") == d.chunk_text(
                text, "smart", structure=d.rule_structure_map(text)
            )
            assert d.chunk_text(text, "mixed") == d.chunk_text(
                text, "mixed", structure=d.rule_structure_map(text)
            )

    def test_llm_map_overrides_rule_boundaries_and_chapter_no(self) -> None:
        lines = CORPUS_A.splitlines()
        rules_chunks = d.chunk_text(CORPUS_A, "smart")
        # 规则面极限回归锚：12 mm 短句被认章（且第八章章号被顶成 04）。
        assert any("12 mm 油嘴工作制度" in s for s, _ in rules_chunks)
        assert any("章节 04 第八章" in s for s, _ in rules_chunks)
        m = d.validate_structure_map(
            d.parse_structure_json(_structure_json(_corpus_a_llm_picks(lines))), lines
        )
        assert m is not None
        llm_chunks = d.chunk_text(CORPUS_A, "smart", structure=d.refine_structure_map(m, lines))
        assert not any("油嘴工作制度" in s for s, _ in llm_chunks)
        assert any(s == "章节 03 第八章 措施效果评价" for s, _ in llm_chunks)
        assert any("第七章" in s and "386" in piece for s, piece in llm_chunks)

    def test_mixed_parents_follow_map(self) -> None:
        lines = CORPUS_A.splitlines()
        m = d.validate_structure_map(
            d.parse_structure_json(_structure_json(_corpus_a_llm_picks(lines))), lines
        )
        assert m is not None
        pieces = d.chunk_text(CORPUS_A, "mixed", structure=d.refine_structure_map(m, lines))
        parents = [s for s, _ in pieces if s.startswith("父块·")]
        # 首章前导行＝「父块·正文」（既有 mixed 行为），加六/七/八三章；
        # 12 mm 短句不分裂父块（规则面会把它顶成第四章）。
        assert parents == [
            "父块·正文",
            "父块·第六章 管柱结构与完井液",
            "父块·第七章 诱导求产与初期产能",
            "父块·第八章 措施效果评价",
        ]

    def test_fixed_mode_ignores_structure(self) -> None:
        m = d.rule_structure_map(CORPUS_A)
        assert d.chunk_text(CORPUS_A, "fixed") == d.chunk_text(CORPUS_A, "fixed", structure=m)

    def test_size_band_untouched_with_map(self) -> None:
        text = "第1章 甲\n" + "内容句子。" * 300
        m = d.rule_structure_map(text)
        for _, piece in d.chunk_text(text, "smart", structure=m):
            assert len(piece) <= d.SMART_MAX_CHARS * 1.2


# ---------- 语料回归（三族：标题/正文/表格行） ----------


class TestCorpusRegression:
    def test_corpus_a_f26_not_heading(self) -> None:
        m = d.rule_structure_map(CORPUS_A)
        titles = [h.title for h in m.headings]
        assert not any("油嘴制度下折算" in t for t in titles)  # f26 长句不入章名
        assert any(t == "第六章 管柱结构与完井液" for t in titles)

    def test_corpus_b_f42_table_rows_stay_body(self) -> None:
        chunks = d.chunk_text(CORPUS_B, "smart")
        assert not any("2026" in s for s, _ in chunks)  # f42 表格行不入章名
        assert any("W-21　512　4.5　52.3" in piece for _, piece in chunks)
        assert any("章节 02" in s and "W-21" in piece for s, piece in chunks)  # 明细行落对章
        assert any("4.5%　渤中34-5" in piece for _, piece in chunks)  # 表格行逐字进正文

    def test_corpus_c_prototype_headings_and_nesting(self) -> None:
        m = d.rule_structure_map(CORPUS_C)
        assert [h.level for h in m.headings] == [1, 2, 1, 1]
        chunks = d.chunk_text(CORPUS_C, "smart")
        assert any("＞ 1.1 投产信息" in s for s, _ in chunks)
        assert any(s == "章节 03 第2章 完井液" for s, _ in chunks)


# ---------- 服务管线：LLM 结构提取＋守门＋回退＋缓存 ----------


class TestIngestStructure:
    async def test_llm_map_drives_sections_and_caller_attribution(self, kb_db: Any) -> None:
        lines = CORPUS_A.splitlines()
        completer = ScriptedCompleter(
            {
                "kb.ingest.structure": _structure_json(_corpus_a_llm_picks(lines)),
                "kb.ingest.summary": "摘要",
                "kb.ingest.questions": "问题？",
            }
        )
        service, storage = _make_service(kb_db, completer)
        lib_id = await _make_lib(service)
        task_id = await _ingest(service, storage, lib_id, "W11 井完井报告.txt", CORPUS_A)
        task = await service._tasks.get(task_id)
        assert task is not None
        frags = await service._fragments.for_report(task.report_id)
        sections = [
            f.section or "" for f in frags if f.type == "原文块" and not f.is_parent_only
        ]
        assert any(s == "章节 03 第八章 措施效果评价" for s in sections)  # 章号正确
        assert not any("油嘴工作制度" in s for s in sections)  # LLM 边际行不入章名
        assert any("第七章" in (f.section or "") and "386" in (f.hit_text or "") for f in frags)
        # caller 归因到达 LLM 出口入参面（gateway 按 caller 落 SpendRecord——B6/D1）
        assert any(caller == "kb.ingest.structure" for caller, _ in completer.calls)
        # 结构图随版本落库（任务快照字段）
        assert task.structure_snapshot is not None
        assert task.structure_snapshot["source"] == "llm"
        assert len(task.structure_snapshot["text_sha256"]) == 64

    async def test_hallucinated_map_voids_and_falls_back_to_rules(
        self, kb_db: Any, caplog: Any
    ) -> None:
        lines = CORPUS_A.splitlines()
        completer = ScriptedCompleter(
            {
                "kb.ingest.structure": _structure_json(
                    [(2, lines[1], 1), (4, lines[3], 1), (5, "凭空捏造的第九章 幻觉标题", 1)]
                ),
            }
        )
        service, storage = _make_service(kb_db, completer)
        lib_id = await _make_lib(service)
        with caplog.at_level(logging.WARNING, logger="domains.kb"):
            task_id = await _ingest(service, storage, lib_id, "W11 井完井报告.txt", CORPUS_A)
        task = await service._tasks.get(task_id)
        assert task is not None
        assert task.structure_snapshot is not None
        assert task.structure_snapshot["source"] == "rules"  # 整图作废→规则图
        assert any("整图作废" in r.message for r in caplog.records)  # warning 留痕
        frags = await service._fragments.for_report(task.report_id)
        sections = [
            f.section or "" for f in frags if f.type == "原文块" and not f.is_parent_only
        ]
        assert any("12 mm 油嘴工作制度" in s for s in sections)  # 规则面 signature

    async def test_rule_recheck_drops_verbatim_but_illegal_row(self, kb_db: Any) -> None:
        lines = CORPUS_A.splitlines()
        completer = ScriptedCompleter(
            {
                "kb.ingest.structure": _structure_json(
                    [
                        (2, lines[1], 1),
                        (4, lines[3], 1),
                        (6, lines[5], 1),  # 逐字真实但越四条件（长句＋句尾。）
                        (9, lines[8], 1),
                    ]
                ),
            }
        )
        service, storage = _make_service(kb_db, completer)
        lib_id = await _make_lib(service)
        task_id = await _ingest(service, storage, lib_id, "W11 井完井报告.txt", CORPUS_A)
        task = await service._tasks.get(task_id)
        assert task is not None
        assert task.structure_snapshot is not None
        assert task.structure_snapshot["source"] == "llm"  # 单行剔除，图不作废
        assert [h["line_no"] for h in task.structure_snapshot["headings"]] == [1, 3, 8]
        frags = await service._fragments.for_report(task.report_id)
        sections = [
            f.section or "" for f in frags if f.type == "原文块" and not f.is_parent_only
        ]
        assert not any("8 mm 油嘴制度下折算" in s for s in sections)
        assert any(s == "章节 03 第八章 措施效果评价" for s in sections)

    async def test_llm_down_falls_back_to_pure_rules_baseline(
        self, kb_db: Any, caplog: Any
    ) -> None:
        completer = ScriptedCompleter(
            {"kb.ingest.structure": RuntimeError("LLM 不可用（模拟断网）")}
        )
        service, storage = _make_service(kb_db, completer)
        lib_id = await _make_lib(service)
        with caplog.at_level(logging.WARNING, logger="domains.kb"):
            task_id = await _ingest(service, storage, lib_id, "W11 井完井报告.txt", CORPUS_A)
        task = await service._tasks.get(task_id)
        assert task is not None
        assert task.structure_snapshot is not None
        assert task.structure_snapshot["source"] == "rules"
        assert any("回退规则图" in r.message for r in caplog.records)
        # 片段集与纯规则基线字节级一致
        assert await _chunk_rows(service, task.report_id) == d.chunk_text(CORPUS_A, "smart")

    async def test_reentry_same_version_zero_llm_and_identical_fragments(
        self, kb_db: Any
    ) -> None:
        lines = CORPUS_A.splitlines()
        completer = ScriptedCompleter(
            {
                "kb.ingest.structure": _structure_json(_corpus_a_llm_picks(lines)),
                "kb.ingest.summary": "摘要",
                "kb.ingest.questions": "问题？",
            }
        )
        service, storage = _make_service(kb_db, completer)
        lib_id = await _make_lib(service)
        task_id = await _ingest(service, storage, lib_id, "W11 井完井报告.txt", CORPUS_A)
        first = await service._tasks.get(task_id)
        assert first is not None
        rows_first = await _chunk_rows(service, first.report_id)
        assert sum(1 for c, _ in completer.calls if c == "kb.ingest.structure") == 1

        retry = await service.retry_ingest(task_id, ACTOR)
        await _wait_done(service, retry.id)
        second = await service._tasks.get(retry.id)
        assert second is not None
        # 同版本重入：零 LLM 调用＋片段集字节级一致
        assert sum(1 for c, _ in completer.calls if c == "kb.ingest.structure") == 1
        assert await _chunk_rows(service, second.report_id) == rows_first
        assert second.structure_snapshot is not None
        assert second.structure_snapshot["source"] == "llm"  # 缓存继承

    async def test_cache_key_binds_to_text_version(self, kb_db: Any) -> None:
        lines = CORPUS_A.splitlines()
        completer = ScriptedCompleter(
            {
                "kb.ingest.structure": _structure_json(_corpus_a_llm_picks(lines)),
                "kb.ingest.summary": "摘要",
                "kb.ingest.questions": "问题？",
            }
        )
        service, storage = _make_service(kb_db, completer)
        lib_id = await _make_lib(service)
        task_id = await _ingest(service, storage, lib_id, "W11 井完井报告.txt", CORPUS_A)
        # 篡改快照版本键（模拟内容已换版）——重入必须重新提取，不许误用旧图
        row = await service._tasks.get(task_id)
        assert row is not None and row.structure_snapshot is not None
        snap = dict(row.structure_snapshot)
        snap["text_sha256"] = "0" * 64
        row.structure_snapshot = snap
        await service._tasks.save(row)
        retry = await service.retry_ingest(task_id, ACTOR)
        await _wait_done(service, retry.id)
        assert sum(1 for c, _ in completer.calls if c == "kb.ingest.structure") == 2

    async def test_fixed_mode_skips_structure_extraction(self, kb_db: Any) -> None:
        completer = ScriptedCompleter()
        service, storage = _make_service(kb_db, completer)
        lib_id = await _make_lib(service)
        await service.save_library_config(
            lib_id,
            switches={
                "semantic": True,
                "keyword": True,
                "wiki": True,
                "graph": False,
            },
            mode="fixed",
            add_summary=True,
            add_questions=True,
            status=None,
            actor_who=ACTOR,
        )
        await _ingest(service, storage, lib_id, "W11 井完井报告.txt", CORPUS_A)
        assert not any(caller == "kb.ingest.structure" for caller, _ in completer.calls)


class TestStructureCallerLandsSpendRecord:
    async def test_spend_record_carries_kb_ingest_structure_caller(
        self, kb_db: Any, tmp_path: Any
    ) -> None:
        """新 caller 计费留痕断言（票面验收 3）：真实 GatewayService 记账→
        SpendRecord.caller 落列 kb.ingest.structure（D1 v0.2 聚合基础）。"""
        from sqlalchemy import select

        import app.infra.config as infra_config

        yaml_path = tmp_path / "models.yaml"
        yaml_path.write_text(_GATEWAY_TEST_YAML, encoding="utf-8")
        infra_config.load_models_config(yaml_path)
        try:
            await ensure_gateway_tables(kb_db.engine())

            class _Backend:
                async def complete(
                    self,
                    alias: str,
                    messages: list[dict[str, str]],
                    *,
                    timeout_seconds: float,
                    max_tokens: int = 4096,
                    **params: Any,
                ) -> LlmCompletion:
                    return LlmCompletion(
                        content="结构应答",
                        prompt_tokens=1200,
                        completion_tokens=120,
                        usage_estimated=False,
                        duration_ms=1500,
                        model="anthropic/MiniMax-M3",
                    )

            storage = FakeStorage()
            service = KbService(
                kb_db, GatewayService(kb_db, _Backend()), storage,
                eventbus=InMemoryEventBus(),
            )
            lib_id = await _make_lib(service)
            await _ingest(service, storage, lib_id, "W11 井完井报告.txt", CORPUS_A)
            async with kb_db.readonly() as session:
                rows = (await session.execute(select(SpendRecord))).scalars().all()
            assert "kb.ingest.structure" in {r.caller for r in rows}
        finally:
            infra_config._models_cache = None  # 注册表缓存复位（测试隔离）
