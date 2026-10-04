"""chat S6 生成窗分池单测（P2-03 开发拍——D2 v0.4 施工，阶段 2 挂账移交清单 #1）。

合同真源（teach-petro-agent/specs/api/D2-搜索与回答.md v0.4，2026-10-04 Owner
拍板分池案）：S6 生成窗从单池「候选上限 4 支」改**分类分池——报告类证据上限
4 支＋台账类材料上限 2 支，两池互不占位**；台账类＝装配层一等材料满分档
（词条卡/指标卡/@ 锚定直取/FAQ 精确命中并入，source∈faq/anchor/ledger）；
报告类＝S4/S5 检索片段证据（source∈vector/keyword）。各池内超出的截断并标
「另有 N 支未列出」。依据＝评测复测窗挤占组（D-诱5 ❌ 词条 3/4 窗饿死 f41、
D-诱15 ❌ f42、D-诱8/12 ⚠️ f46/f47/f33、A-正5 ⚠️ §6.2——满分台账材料同池
挤出真数据片段）。

票面验收对照（dispatch/pending/P2-03.md 测试 (a)-(f)）：
- (a) 台账材料 3＋报告材料 5 → 台账池恰 2（按原序前 2）/报告池恰 4、互不占位；
- (b) 仅报告类 6 条 → 报告池 4＋台账池空＝真数据保底 4 席（窗挤占反例固化）；
- (c) 池内排序与分池前同序（截断不改排序）；
- (d) 重评过闸（P1F-06 路径）截断同分池口径；
- (e) notice 文案断言（两池各超/单池超两形态）；
- (f) 全量回归（既有断言失配改断言适配——test_chat_chains_unit 同步）。
"""

from dataclasses import replace
from typing import Any

from app.domains.chat import chains as chains_mod
from app.domains.chat import domain as d
from tests.domains.chat.conftest import (
    AQIANG,
    DEFAULT_CONFIG,
    Seams,
    collect,
    events_by_name,
    make_service,
)

# 两个 @ 锚定（台账类满分档两支——S1 前门直取，source=anchor；均在台账真行）。
TWO_ANCHORS = ["指标卡·产量完成率", "术语·躺井"]


def _hit(fid: str, score: float, leg: str = "vector") -> d.IndexHitFace:
    """报告索引命中（fragment_id 进 snippet——窗口行逐支可辨）。"""
    return d.IndexHitFace(
        fragment_id=fid, report_id="rpt-1", report="N-02 完井报告",
        section="01 井基本情况", snippet=f"{fid} 片段正文", score=score, leg=leg,
    )


def _window_rows(seams: Seams) -> list[str]:
    """检索链生成步 user 消息的编号材料表行（窗口组成观测面——「cN：[kind]
    label——snippet」逐行；ref 序＝送生成序列）。"""
    gen = [msgs for caller, msgs in seams.prompts if caller == chains_mod.CALLER_RETRIEVAL]
    assert gen, "检索链生成步未被调用"
    user = next(m["content"] for m in gen[-1] if m["role"] == "user")
    marker = "依据材料（编号表）：\n"
    start = user.index(marker) + len(marker)
    end = user.index("\n\n请依据材料回答")
    return user[start:end].splitlines()


def _ledger_rows(rows: list[str]) -> list[str]:
    return [r for r in rows if "[台账条目]" in r]


def _report_rows(rows: list[str]) -> list[str]:
    return [r for r in rows if "[报告引用]" in r]


def _notices(events: list[Any]) -> list[str]:
    return [str(n["text"]) for n in events_by_name(events)["notice"]]


class TestWindowPoolConstants:
    """分池常量钉（D2 v0.4 行为规则 1 合同值不可改清单——生成窗分池上限）。"""

    def test_pool_caps_and_ledger_sources(self) -> None:
        assert d.EVIDENCE_CAP == 4  # 报告类池（语义不变——原单池值）
        assert d.LEDGER_EVIDENCE_CAP == 2  # 台账类池（v0.4 新增）
        assert d.LEDGER_EVIDENCE_SOURCES == frozenset({"faq", "anchor", "ledger"})


class TestS6WindowPooling:
    """S6 生成窗分池（两池互不占位）——假 completer 机制测。"""

    async def test_ledger_and_report_pools_no_cross_occupation(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """(a) 台账材料 3＋报告材料 5：台账池恰 2（按原序前 2）、报告池恰 4，
        互不占位——反向断言：台账满 2 时报告池仍满 4（旧单池病灶＝满分台账
        挤出真数据片段，本断言钉死不回归）。"""
        seams.index_vector = [_hit(f"v{i}", 0.9 - i * 0.05) for i in range(1, 6)]
        seams.faq_hit = d.FaqHitFace(entry_id="faq-1", question="标准问", answer="答")
        seams.config = replace(DEFAULT_CONFIG, early_stop=False, faq_direct_hit=False)
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask(
            "N-02 的情况", session_id=None, page_context=None,
            anchors=TWO_ANCHORS, actor_who=AQIANG,
        ))
        rows = _window_rows(seams)
        ledger = _ledger_rows(rows)
        report = _report_rows(rows)
        # 台账池恰 2（两支 @ 锚定按原序前 2——FAQ 并入材料被截，不占报告席位）
        assert len(ledger) == 2
        assert "台账「产量完成率」" in ledger[0] and "台账「躺井」" in ledger[1]
        # 报告池恰 4（互不占位反向断言——台账满 2 时报告仍满 4）
        assert len(report) == 4
        # 总窗口 6 席（4＋2，两池互不占位——不再单池 4 支互挤）
        assert len(rows) == 6
        # 分池截断 notice 两行（两池都有超出）
        cap_notices = [t for t in _notices(events) if "支未列出" in t]
        assert len(cap_notices) == 2
        assert events_by_name(events)["answer"][0]["kind"] == "text"

    async def test_report_only_keeps_four_seat_floor(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """(b) 仅报告类 6 条：报告池 4＋台账池空＝真数据保底 4 席（窗挤占反例
        固化——报告证据永不因台账池空置而少于 4 席，反之亦然）。"""
        seams.index_vector = [_hit(f"v{i}", 0.9 - i * 0.05) for i in range(1, 7)]
        seams.config = replace(DEFAULT_CONFIG, early_stop=False)
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask(
            "随便问一句", session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        rows = _window_rows(seams)
        assert len(_report_rows(rows)) == 4  # 真数据保底 4 席
        assert _ledger_rows(rows) == []  # 台账池空——不占位也不虚占
        # 单池超形态：只有报告类一行溢出 notice，无台账类行
        cap_notices = [t for t in _notices(events) if "支未列出" in t]
        assert len(cap_notices) == 1
        assert "报告类" in cap_notices[0] and "台账类" not in cap_notices[0]

    async def test_pool_internal_order_preserved(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """(c) 池内排序与分池前同序：分池只丢不重排——台账池原序（锚定序）、
        报告池原序（融合排名 v1→v4）、送生成序列保持分池前全局序。"""
        seams.index_vector = [_hit(f"v{i}", 0.9 - i * 0.05) for i in range(1, 6)]
        seams.faq_hit = d.FaqHitFace(entry_id="faq-1", question="标准问", answer="答")
        seams.config = replace(DEFAULT_CONFIG, early_stop=False, faq_direct_hit=False)
        svc = make_service(chat_db, seams)
        await collect(svc.ask(
            "N-02 的情况", session_id=None, page_context=None,
            anchors=TWO_ANCHORS, actor_who=AQIANG,
        ))
        rows = _window_rows(seams)
        # 全局序＝分池前证据序（S1 锚定→S4 报告→FAQ 并入），各池内同序截断：
        # c1/c2＝台账前 2（锚定序），c3~c6＝报告前 4（融合排名序）
        assert [r.split("：")[0] for r in rows] == ["c1", "c2", "c3", "c4", "c5", "c6"]
        assert "台账「产量完成率」" in rows[0] and "台账「躺井」" in rows[1]
        for i, row in enumerate(rows[2:], start=1):
            assert f"v{i} 片段正文" in row
        # 台账池第 3 支（FAQ 并入材料）被截——报告池前 4 不受影响（池内同序）
        assert not any("FAQ「标准问」" in r for r in rows)

    async def test_rescore_gate_truncation_same_pool_semantics(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """(d) 重评过闸（P1F-06 第一道放宽窗口）截断同分池口径：放宽池 6 支
        报告类 → 报告池 4＋溢出 notice（同款「另有 N 支未列出」）——过闸照常
        生成、零改写调用（第二道不触发）。"""
        seams.config = replace(DEFAULT_CONFIG, semantic_top_k=3, keyword_top_k=3)
        # 常规窗口只回前 3 支（best 0.35 落低分带）→ 放宽窗口（k=6）回捞全 6 支
        # （best 0.9 过闸）——单桩按 k 切片天然承载两窗。
        seams.index_vector = [
            _hit("v1", 0.35), _hit("v2", 0.34), _hit("v3", 0.33),
            _hit("v4", 0.9), _hit("v5", 0.89), _hit("v6", 0.88),
        ]
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask(
            "请帮忙梳理二季度注水开发月度动态并逐月合计对比", session_id=None,
            page_context=None, anchors=[], actor_who=AQIANG,
        ))
        rows = _window_rows(seams)
        assert len(_report_rows(rows)) == 4  # 重评过闸同分池口径——报告池 4
        assert _ledger_rows(rows) == []
        cap_notices = [t for t in _notices(events) if "支未列出" in t]
        assert cap_notices == [
            "报告类证据 6 支，仅送前 4 支进生成——另有 2 支未列出。",
        ]  # 重评过闸同分池口径（报告类池 6→4）
        assert "chat.query.rewrite" not in seams.completions  # 第二道未触发
        answer = events_by_name(events)["answer"][0]
        assert answer["kind"] == "text"


class TestPoolingNoticeForms:
    """截断 notice 分池口径（e——两池各超/单池超两形态；复用既有 notice 机制，
    不造新帧类型）。"""

    async def test_both_pools_overflow_two_notice_lines(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """两池都有超出 → 两行 notice（各池各自标「另有 N 支未列出」）。"""
        seams.index_vector = [_hit(f"v{i}", 0.9 - i * 0.05) for i in range(1, 6)]
        seams.faq_hit = d.FaqHitFace(entry_id="faq-1", question="标准问", answer="答")
        seams.config = replace(DEFAULT_CONFIG, early_stop=False, faq_direct_hit=False)
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask(
            "N-02 的情况", session_id=None, page_context=None,
            anchors=TWO_ANCHORS, actor_who=AQIANG,
        ))
        cap_notices = [t for t in _notices(events) if "支未列出" in t]
        assert cap_notices == [
            "报告类证据 5 支，仅送前 4 支进生成——另有 1 支未列出。",
            "台账类材料 3 支，仅送前 2 支进生成——另有 1 支未列出。",
        ]

    async def test_single_pool_overflow_single_notice_line(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """单池超 → 单行 notice（未超池不标溢出行——观测面不发明）。"""
        seams.index_vector = [_hit(f"v{i}", 0.9 - i * 0.05) for i in range(1, 7)]
        seams.config = replace(DEFAULT_CONFIG, early_stop=False)
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask(
            "随便问一句", session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        cap_notices = [t for t in _notices(events) if "支未列出" in t]
        assert cap_notices == [
            "报告类证据 6 支，仅送前 4 支进生成——另有 2 支未列出。",
        ]

    async def test_s6_note_and_config_check_line_pooled_caliber(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """S6 收束注记「（上限 N）」与出口「配置核对」行同口径——分池两上限
        明义（报告类 4＋台账类 2），不再单池口径。"""
        seams.index_vector = [_hit(f"v{i}", 0.9 - i * 0.05) for i in range(1, 6)]
        seams.faq_hit = d.FaqHitFace(entry_id="faq-1", question="标准问", answer="答")
        seams.config = replace(DEFAULT_CONFIG, early_stop=False, faq_direct_hit=False)
        svc = make_service(chat_db, seams)
        events = await collect(svc.ask(
            "N-02 的情况", session_id=None, page_context=None,
            anchors=TWO_ANCHORS, actor_who=AQIANG,
        ))
        s6_notes = " ".join(
            str(f.get("note") or "") for f in events_by_name(events)["node"]
            if f["key"] == "S6"
        )
        assert "报告类上限 4" in s6_notes and "台账类上限 2" in s6_notes
        check_lines = [str(f["text"]) for f in events_by_name(events)["node_line"]
                       if f["key"] == "N17"]
        assert any(
            "生成窗＝报告类 4＋台账类 2" in text for text in check_lines
        )
