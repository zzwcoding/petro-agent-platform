"""kb 结构图单测（DE-05 同文同切定稿）——纯规则出图＋chunk 消费＋入库确定化。

语料注源（拟造数据，形态注源评测报告存照）：
- corpus/report_A_f26诱导求产.txt——eval/results/评测报告.md §4.5 A-正7 存照
  （f26 长正文句吞章名＋章号错）；第 7 行「12 mm 油嘴工作制度」为规则面漏判形
  （RE 命中/短/无句读/无表格特征）——纯规则确定化下按规则成章（已知取舍，
  见 chunk_text 铁律注记与 DE-05 回报疑点）。
- corpus/report_B_f42检泵月报.txt——§5 观察 1 存照（f42「章节 03 2026　7　4.5%…」
  表格行误判）＋B-正4 W-21 明细行形态。
- corpus/teach_prototype_n02样例.txt——页面 RAW_TEXT 同源口径（设定书 §A.1），
  markdown 章词/数字点级/第 N 章三支标题形。
- fixtures/report_C_heading双样式裁剪.txt——DE-04 双样式考题复用（A5 现象锚）。

演进注记：P1F-05 方案 A 的 LLM 结构图路径（parse/validate/refine/level 守门＋
kb.ingest.structure 提取＋版本缓存）已随 DE-05 退役——LLM 应答合法子集波动＝
「同文不同切」抽签根因（定位记录：tickets/phase3/reports/DE-05.收尾.md）；
相关旧用例由本文件 TestIngestDeterministic 与 test_kb_same_text_same_chunks.py
的确定化断言替代。
红线：桩 LLM 永不触网（B6）；kb_db 夹具复用同目录 conftest。
"""

from pathlib import Path
from typing import Any

from app.domains.gateway import Completion
from app.domains.kb import KbService
from app.domains.kb import domain as d
from app.domains.kb.store import UploadStore
from app.infra.eventbus import InMemoryEventBus

CORPUS_DIR = Path(__file__).parent / "corpus"
CORPUS_A = (CORPUS_DIR / "report_A_f26诱导求产.txt").read_text(encoding="utf-8")
CORPUS_B = (CORPUS_DIR / "report_B_f42检泵月报.txt").read_text(encoding="utf-8")
CORPUS_C = (CORPUS_DIR / "teach_prototype_n02样例.txt").read_text(encoding="utf-8")
# DE-04：C 报告标题双样式裁剪样例（票面指定 tests/fixtures——语料注源见文件头）。
FIXTURE_C_HEADING_STYLES = (
    Path(__file__).parents[2] / "fixtures" / "report_C_heading双样式裁剪.txt"
).read_text(encoding="utf-8")

ACTOR = "阿强 · 平台运维"
LIB_NAME = "完井报告库"


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


async def _wait_state(
    service: KbService, task_id: str, states: tuple[str, ...]
) -> Any:
    """轮询至任务进入给定状态集（F3 failed→retry 用例：failed 也是合法终等态）。"""
    import asyncio
    import time

    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        task = await service.ingest_task(task_id)
        if task.state in states:
            return task
        await asyncio.sleep(0.02)
    raise TimeoutError(f"入库等待超时（等待状态集 {states}）")


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


# ---------- DE-04：「一、」中文序号章级＋数字层级末段断言（A5 前半双样式） ----------


class TestHeadingCnOrdinalStyle:
    """中文序号行首（一、～九十九、）——A5 前半新分支（章级 level 1）。"""

    def test_cn_ordinal_headings_pass_at_chapter_level(self) -> None:
        # 正例 ≥2 票面验收：C 报告真实样式行逐字（一/三/十）＋九十九上界。
        for line in [
            "一、三季度生产运行",
            "三、三季度注水调整方案",
            "十、注水井分层测试汇总（三季度）",
            "九十九、边界样例",
        ]:
            assert d.is_heading_line(line) is True, line
            info = d._section_of(line)
            assert info is not None and info[0] == 1, line  # 中文序号＝章级

    def test_cn_ordinal_requires_following_body(self) -> None:
        # 「、」后必须接正文（非空白/非分隔标点）——孤立「一、」不成标题。
        for line in ["一、", "十、", "一、。", "九十九、"]:
            assert d.is_heading_line(line) is False, line

    def test_cn_ordinal_range_boundary(self) -> None:
        # 序号域边界外不认：一百（百位不属 1–99 域）、连写非法序号。
        for line in ["一百、边界外", "二三、非法序号"]:
            assert d.is_heading_line(line) is False, line

    def test_cn_ordinal_overlong_still_demoted(self) -> None:
        # 三约束不动（票面交付物②）：行长 ≤HEADING_MAX_CHARS 沿用——超长
        # 中文序号标题同归正文（超长标题归正文的不对称取舍对新样式同样生效）。
        line = "一、" + "超长章节标题" * 8
        assert len(line) > d.HEADING_MAX_CHARS
        assert d.is_heading_line(line) is False


class TestHeadingNumericGuard:
    """数字层级末段断言（末段后非数字/非.数字）——金额/日期回溯误报守门。

    修复前基线（票面负例三型）：「1.1万元」「2026.10」「1.1」均被旧正则回溯
    误报（1.1万元→章号 1、2026.10→章号 2026.、孤立 1.1→章号 1）。
    """

    def test_amount_and_date_and_bare_number_not_heading(self) -> None:
        # 误报负例 ≥3 票面验收：金额连写/日期/孤立层级号（普通括号编号行）。
        assert d.is_heading_line("1.1万元") is False
        assert d.is_heading_line("2026.10") is False
        assert d.is_heading_line("1.1") is False
        assert d.is_heading_line("（3）注水井酸化") is False  # 括号编号行（既有不认）

    def test_numeric_level_positive_regression_unchanged(self) -> None:
        # 旧正例零变化（票面硬验收）：真层级号（含新补 1.1.1 三级形）照常识别。
        for line, level in [
            ("1.1 主要生产指标（月度）", 2),
            ("1.1.1 完井工艺细分", 2),
            ("2.10 注水月度数据", 2),
            ("1.概述", 1),
            ("1 概述", 1),
        ]:
            assert d.is_heading_line(line) is True, line
            info = d._section_of(line)
            assert info is not None and info[0] == level, line


class TestHeadingPrefixConsumer:
    """DE-04 交付物③：_HEADING_PREFIX_RE 消费面同步核对——新样式前缀已被
    `[0-9一二三四五六七八九十百]+\\s*[、.]` 覆盖，零改动不双写第二份正则
    （消费面＝_table_like 甄别：标题/条目形态不当数据行）。"""

    def test_new_style_prefixes_not_table_like(self) -> None:
        for line in [
            "一、三季度生产运行",
            "十、注水井分层测试汇总（三季度）",
            "1.1 主要生产指标（月度）",
            "1.1.1 完井工艺细分",
        ]:
            assert d._table_like(line) is False, line


# ---------- FX-04（R1-11）：标题号后首词计量/历法守门 ----------


class TestMeasureCalendarGuard:
    """数字层级/序号标题命中后，紧随分隔空格的首词为计量/历法闭世界常量
    → 不识别为标题。

    R1-11：DE-04 §六.1/§六.3 移交「LLM 图职责面」的两类同构误报（「1.1 万元」
    带空格金额、「2026.10 月报」日期带文字），随 DE-05 退役 LLM 结构路确定
    成章且无主——本守门收口。清单为整词等值制（首词恰等于清单词才排除，
    不做前缀匹配）——真标题「1.1 月度生产分析」「1.1 元数据管理」与清单词
    组词形零误伤；「井」「口」不进清单（取舍记录见 FX-04 回报）。
    """

    def test_spaced_amount_and_dated_report_not_heading(self) -> None:
        # 误报两形（R1-11 点名）＋扩展形（数值带单位/金额续句/序号标题形）。
        assert d.is_heading_line("1.1 万元") is False
        assert d.is_heading_line("2026.10 月报") is False
        assert d.is_heading_line("3.2 吨") is False
        assert d.is_heading_line("1.1 万元，较上月减少 0.7 个百分点") is False
        assert d.is_heading_line("一、万元") is False

    def test_measure_words_whole_word_matching_only(self) -> None:
        # 整词等值制：首词恰为清单词才排除——历法单字不做前缀匹配，
        # 「月报」以语料实证进清单（DE-04 §六.3 点名形）。
        assert d.is_heading_line("2.10 月报") is False
        assert d.is_heading_line("1.1 元") is False
        assert d.is_heading_line("1.1 %") is False
        assert d.is_heading_line("1.1 ％") is False

    def test_real_headings_with_similar_shapes_unchanged(self) -> None:
        # 真标题零伤（票面硬验收）：同构形真标题照常识别——含票面点名
        # 「1.1 井身结构」与「月度/年度/万元产值」组词形、语料既有
        # 「12 mm 油嘴工作制度」边际形。
        for line in [
            "1.1 主要生产指标（月度）",
            "1.1 井身结构",
            "1.1 月度生产分析",
            "1.1 年度工作总结",
            "1.1 元数据管理",
            "一、万元产值完成情况",
            "一、年度工作总结",
            "一、三季度生产运行",
            "2.10 注水月度数据",
            "12 mm 油嘴工作制度",
        ]:
            assert d.is_heading_line(line) is True, line


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

    def test_rules_map_is_deterministic_supply(self) -> None:
        # DE-05：生产链唯一图源＝纯规则图（source 恒 rules；两次出图全等）。
        m1 = d.rule_structure_map(CORPUS_A)
        m2 = d.rule_structure_map(CORPUS_A)
        assert m1 == m2 and m1.source == "rules"
        assert all(isinstance(h, d.HeadingLine) for h in m1.headings)
        # 规则面已知取舍（f26 边际行）：12 mm 短句按规则成章——确定化超集的
        # 组成部分（原 LLM 图可随机剔除它＝抽签面，已随 DE-05 退役）。
        rules_chunks = d.chunk_text(CORPUS_A, "smart")
        assert any("12 mm 油嘴工作制度" in s for s, _ in rules_chunks)
        assert any("章节 04 第八章" in s for s, _ in rules_chunks)

    def test_mixed_parents_follow_rule_map(self) -> None:
        parents_expected = ["父块·正文"] + [
            f"父块·{h.title}"
            for h in d.rule_structure_map(CORPUS_A).headings
            if h.level == 1
        ]
        pieces = d.chunk_text(CORPUS_A, "mixed")
        parents = [s for s, _ in pieces if s.startswith("父块·")]
        # 首章前导行＝「父块·正文」（既有 mixed 行为），其后随章级标题逐一立锚
        # （含 12 mm 规则边际章——确定化行为锁定）。
        assert parents == parents_expected
        assert "父块·12 mm 油嘴工作制度" in parents

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


class TestCorpusCHeadingStyleFixture:
    """DE-04：C 报告裁剪 fixture——「一、」章级＋「1.1」节级识别齐＋误报负例
    行不识别（票面验收：两种新样式各 ≥2 处＋负例行 ≥3；A5 现象回归锚）。"""

    def test_both_new_styles_recognized(self) -> None:
        m = d.rule_structure_map(FIXTURE_C_HEADING_STYLES)
        titles = [h.title for h in m.headings]
        # 中文序号章级 ≥2
        assert "一、三季度生产运行" in titles
        assert "二、注水运行" in titles
        assert [h.level for h in m.headings if h.title == "一、三季度生产运行"] == [1]
        # 数字层级节级 ≥2
        assert "1.1 主要生产指标（月度）" in titles
        assert "2.1 注水月度数据" in titles
        assert [h.level for h in m.headings if h.title == "2.1 注水月度数据"] == [2]

    def test_false_positive_lines_stay_body(self) -> None:
        m = d.rule_structure_map(FIXTURE_C_HEADING_STYLES)
        titles = [h.title for h in m.headings]
        # 后两形＝FX-04（R1-11）追加：DE-05 退役 LLM 结构路后确定成章的两类
        # 同构误报（带空格金额/日期带文字），负例行清单随票面扩条。
        for bad in [
            "1.1万元",
            "2026.10",
            "1.1",
            "（3）注水井酸化",
            "1.1 万元",
            "2026.10 月报",
        ]:
            assert bad not in titles, bad
            # 负例行逐字留在正文块内（守门不丢内容）
            chunks = d.chunk_text(FIXTURE_C_HEADING_STYLES, "smart")
            assert any(bad in piece for _, piece in chunks), bad

    def test_chunk_paths_carry_chapter_no(self) -> None:
        # A5 主症状回归锚：章节路径不再恒「正文」——章号推进＋节级挂章。
        paths = [s for s, _ in d.chunk_text(FIXTURE_C_HEADING_STYLES, "smart")]
        assert any(s == "章节 01 一、三季度生产运行" for s in paths)
        assert any(
            s == "章节 01 一、三季度生产运行 ＞ 1.1 主要生产指标（月度）" for s in paths
        )
        assert any(s == "章节 02 二、注水运行 ＞ 2.1 注水月度数据" for s in paths)
        assert not any(s.startswith("正文") and "＞" in s for s in paths)




# ---------- 服务管线：切块确定化（DE-05 同文同切——chunk 步恒纯规则图） ----------


class TestIngestDeterministic:
    """DE-05：入库 chunk 步边界供给＝纯规则图、零 LLM 参与——同文同切在
    服务管线的落位（跨进程双跑见 test_kb_same_text_same_chunks.py）。"""

    async def test_chunk_step_never_calls_llm_and_uses_rule_map(self, kb_db: Any) -> None:
        completer = ScriptedCompleter({})  # 缺省应答「应答」——若被查即不可解析
        service, storage = _make_service(kb_db, completer)
        lib_id = await _make_lib(service)
        task_id = await _ingest(service, storage, lib_id, "W11 井完井报告.txt", CORPUS_A)
        task = await service._tasks.get(task_id)
        assert task is not None
        # 铁律面：切块不查 LLM——调用序中不存在任何结构提取 caller
        assert not any("structure" in caller for caller, _ in completer.calls)
        # 规则图 signature：f26 边际行「12 mm 油嘴工作制度」按规则成章（确定化超集，
        # 第八章顺延为章节 04）；第七章 386 数据行落对章。
        frags = await service._fragments.for_report(task.report_id)
        sections = [
            f.section or "" for f in frags if f.type == "原文块" and not f.is_parent_only
        ]
        assert any("12 mm 油嘴工作制度" in s for s in sections)
        assert any(s == "章节 04 第八章 措施效果评价" for s in sections)
        assert any(
            "第七章" in (f.section or "") and "386" in (f.hit_text or "") for f in frags
        )
        # LLM 结构快照列退役：不再写（存量列保留、本任务恒 NULL）
        assert task.structure_snapshot is None

    async def test_same_text_double_ingest_identical_chunks(self, kb_db: Any) -> None:
        """同文同切（票面验收②）：同 fixture 两次独立入库→原文块切片序列全等
        （含章节路径与顺序）。富化应答两次不同（摘要/问题不在铁律域）。"""
        completer = ScriptedCompleter(
            {
                "kb.ingest.summary": "第一次摘要",
                "kb.ingest.questions": "第一批问题？",
            }
        )
        service, storage = _make_service(kb_db, completer)
        lib_id = await _make_lib(service)
        task_id_1 = await _ingest(
            service, storage, lib_id, "C报告.txt", FIXTURE_C_HEADING_STYLES
        )
        first = await service._tasks.get(task_id_1)
        assert first is not None
        rows_first = await _chunk_rows(service, first.report_id)

        completer.answers["kb.ingest.summary"] = "第二次摘要"
        completer.answers["kb.ingest.questions"] = "第二批问题？"
        task_id_2 = await _ingest(
            service, storage, lib_id, "C报告.txt", FIXTURE_C_HEADING_STYLES
        )
        second = await service._tasks.get(task_id_2)
        assert second is not None
        rows_second = await _chunk_rows(service, second.report_id)

        assert rows_first
        assert rows_first == rows_second  # 切片序列逐元素全等（section＋text＋顺序）
        # C 样例章节路径带章号（DE-04 行为保持）——两次跑同形
        for rows in (rows_first, rows_second):
            assert any(s == "章节 01 一、三季度生产运行" for s, _ in rows)
            assert any(
                s == "章节 01 一、三季度生产运行 ＞ 1.1 主要生产指标（月度）"
                for s, _ in rows
            )
            assert any(s == "章节 02 二、注水运行 ＞ 2.1 注水月度数据" for s, _ in rows)

    async def test_service_chunks_equal_pure_domain_chain(self, kb_db: Any) -> None:
        # 生产链片段集与域纯函数链（rule map＋chunk_text）字节级一致
        service, storage = _make_service(kb_db, ScriptedCompleter({}))
        lib_id = await _make_lib(service)
        task_id = await _ingest(service, storage, lib_id, "W11 井完井报告.txt", CORPUS_A)
        task = await service._tasks.get(task_id)
        assert task is not None
        assert await _chunk_rows(service, task.report_id) == d.chunk_text(CORPUS_A, "smart")

    async def test_reingest_via_retry_identical_chunks(self, kb_db: Any) -> None:
        # 同任务重入（retry）也全等——重入零 LLM、重算纯规则即同（不依赖缓存）
        completer = ScriptedCompleter({})
        service, storage = _make_service(kb_db, completer)
        lib_id = await _make_lib(service)
        task_id = await _ingest(service, storage, lib_id, "W11 井完井报告.txt", CORPUS_A)
        first = await service._tasks.get(task_id)
        assert first is not None
        rows_first = await _chunk_rows(service, first.report_id)
        retry = await service.retry_ingest(task_id, ACTOR)
        await _wait_done(service, retry.id)
        second = await service._tasks.get(retry.id)
        assert second is not None
        assert await _chunk_rows(service, second.report_id) == rows_first
        assert not any("structure" in caller for caller, _ in completer.calls)

    async def test_fixed_mode_never_calls_structure(self, kb_db: Any) -> None:
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
        assert not any("structure" in caller for caller, _ in completer.calls)
