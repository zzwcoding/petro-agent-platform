"""P1F-01 N5 未接线链回退单测：裁决选中未接线壳链 → N5b 接线核验回退检索问答链。

缺陷背景（eval/results/评测报告.md §4.3/4.8/4.9/§6 建议 1）：17 链清单只有三链
真实接线（检索问答/FAQ直出/图谱问答——ChainDispatcher 注册面），旧 N5b 只验
「链名 ∈ CHAIN17」不验接线——LLM 选任何壳链都直通分派，分发器回「该能力暂未
开通」（11/35 题中招、7 道彻底无法作答）。修复后：

- 未注册 → 覆写 verdict["chain"] 为「检索问答链」（只动 chain 键），N5b 帧
  note 记原裁决；已注册三链绝不覆写；
- resume 重判路径同款回退（与主路径共用 _verify_chain_wiring——单源一致）；
- 裁决提示词携约束段（源头降噪：台账命中只是装配材料信号，不构成选链依据）。
"""

import json
from collections.abc import AsyncIterator
from typing import Any

import pytest

from app.domains.chat import domain as d
from app.domains.chat.domain import ChainContext, IndexHitFace, SseEvent
from app.domains.chat.service import INTENT_VERDICT_SYSTEM_PROMPT
from app.domains.chat.store import ChatStore
from tests.domains.chat.conftest import AQIANG, Seams, collect, make_service

# 评测壳链中招三题（票面验收 3）：question 字段取自 eval/results/frames/
# B-B-正6.json、B-B-正7.json；C-C-正6.json 无 question 字段——题干取自
# eval/answers/C-题目与答案.md C-正6 行（偏差已记回报）。
B_ZHENG6_QUESTION = "近三年 8 月平均检泵周期的变化趋势？"
B_ZHENG7_QUESTION = "W-32 井“检泵周期”栏的 215 天是什么口径？"
C_ZHENG6_QUESTION = "累积亏空当前多少？与二季度比变化如何？说明什么？"


def _hit(score: float) -> IndexHitFace:
    """报告索引命中桩行（双路向量腿——检索链 S4 消费，score 过拒答线）。"""
    return IndexHitFace(
        fragment_id="f1", report_id="rpt-1", report="N-02 完井报告",
        section="01 井基本情况", snippet="检泵周期", score=score, leg="vector",
        text="检泵周期记录",
    )


def _node_finish(events: list[Any], key: str) -> dict[str, Any] | None:
    """某节点最后一个 finish 帧载荷（note 断言面）。"""
    out = [
        event.data for event in events
        if event.event == "node" and event.data["key"] == key
        and event.data["state"] == "finish"
    ]
    return out[-1] if out else None


def _dispatched_chain(events: list[Any]) -> str:
    """N6 finish 帧的实派链名（「已分派至「X」」注记解析）。"""
    note = str(_node_finish(events, "N6")["note"])
    return note.split("已分派至「")[1].split("」")[0]


def _events_by_name(events: list[Any]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        out.setdefault(event.event, []).append(event.data)
    return out


async def _stub_handler(ctx: ChainContext) -> AsyncIterator[SseEvent]:
    yield SseEvent(d.FRAME_ANSWER, {"kind": "text", "text": "ok"})


class TestN5ShellChainFallback:
    """票面验收 1：主路径四用例（未注册回退×2／已注册不覆写／提示词约束）。"""

    async def test_metric_direct_shell_chain_falls_back(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """(a) mock 裁决返回「指标卡直出链」→ 实派检索问答链＋N5b 帧含原链名。"""
        seams.index_vector = [_hit(0.7)]  # 检索链真出答案——回退落到能作答的链
        seams.intent_reply = '{"chain": "指标卡直出链", "confidence": 0.92}'
        service = make_service(chat_db, seams)
        events = await collect(service.ask(
            B_ZHENG6_QUESTION, session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        n5b = _node_finish(events, "N5b")
        assert n5b is not None
        assert "原裁决＝「指标卡直出链」未接线" in str(n5b["note"])
        assert "回退检索问答链" in str(n5b["note"])
        assert _dispatched_chain(events) == "检索问答链"
        answer = _events_by_name(events)["answer"][0]
        assert answer["kind"] == "text"  # 检索链真作答——不是未开通 alert
        assert "该能力暂未开通" not in str(answer["text"])

    async def test_report_shell_chain_falls_back(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """(b) mock 裁决返回「汇报生成链」→ 同回退。"""
        seams.index_vector = [_hit(0.7)]
        seams.intent_reply = '{"chain": "汇报生成链", "confidence": 0.88}'
        service = make_service(chat_db, seams)
        events = await collect(service.ask(
            C_ZHENG6_QUESTION, session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        n5b = _node_finish(events, "N5b")
        assert n5b is not None
        assert "原裁决＝「汇报生成链」未接线" in str(n5b["note"])
        assert _dispatched_chain(events) == "检索问答链"
        assert "该能力暂未开通" not in str(_events_by_name(events)["answer"][0]["text"])

    @pytest.mark.parametrize("chain", ["检索问答链", "FAQ直出链", "图谱问答链"])
    async def test_registered_chains_never_overwritten(
        self, chat_db: Any, seams: Seams, chain: str,
    ) -> None:
        """(c) mock 返回已接线三链之一 → 不覆写（N5b 无回退注记、实派原链）。"""
        seams.index_vector = [_hit(0.7)]
        seams.intent_reply = json.dumps({"chain": chain, "confidence": 0.9},
                                        ensure_ascii=False)
        service = make_service(chat_db, seams)
        events = await collect(service.ask(
            B_ZHENG6_QUESTION, session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        n5b = _node_finish(events, "N5b")
        assert n5b is not None
        note = str(n5b["note"])
        assert "未接线" not in note and "原裁决" not in note
        assert "已接线" in note
        assert _dispatched_chain(events) == chain

    def test_intent_prompt_carries_constraint(self) -> None:
        """(d) 裁决提示词约束段（W-AUX 判型恢复后）：分型路由取代「一律检索」
        过渡约束——数据型入六站链、报告叙述型留检索链；@ 锚定与仅受理条款保留。"""
        assert "分型路由" in INTENT_VERDICT_SYSTEM_PROMPT
        assert "状态机六站链" in INTENT_VERDICT_SYSTEM_PROMPT
        assert "取值诉求" in INTENT_VERDICT_SYSTEM_PROMPT
        assert "装配材料信号" in INTENT_VERDICT_SYSTEM_PROMPT
        assert "@ 显式锚定" in INTENT_VERDICT_SYSTEM_PROMPT
        assert "「指标卡直出链」「口径消歧链」" in INTENT_VERDICT_SYSTEM_PROMPT
        assert "一律选" not in INTENT_VERDICT_SYSTEM_PROMPT  # P1F-01 过渡约束已撤


class TestResumePathFallback:
    """票面验收 2：resume 重判路径同款回退（防只改主路径）。"""

    async def test_resume_rejudge_shell_chain_falls_back(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """澄清回流带参重判：mock 返回壳链 → 同样回退检索问答链。"""
        seams.index_vector = [_hit(0.7)]
        service = make_service(chat_db, seams)
        # 首问触发口径两译澄清挂起（deterministic 硬闸——不涉 LLM）
        first = await collect(service.ask(
            "有效产量是多少", session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        first_data = _events_by_name(first)
        assert first_data["verdict"][0]["need_clarify"] is True
        run_id = first_data["session"][0]["run_id"]
        # 回流带口径（问句已点口径支名——闸不再触发）→ LLM 重判选中壳链
        seams.intent_reply = '{"chain": "指标卡直出链", "confidence": 0.92}'
        second = await collect(service.resume(
            run_id, kind="clarify", choice="B · 检修剔除", decision=None, reason=None,
            actor_who=AQIANG,
        ))
        second_data = _events_by_name(second)
        assert second_data["verdict"][0]["source"] == "llm"
        n5b = _node_finish(second, "N5b")
        assert n5b is not None
        assert "原裁决＝「指标卡直出链」未接线" in str(n5b["note"])
        assert "回退检索问答链" in str(n5b["note"])
        assert _dispatched_chain(second) == "检索问答链"
        assert "该能力暂未开通" not in str(second_data["answer"][0]["text"])
        assert second_data["answer"][0]["kind"] == "text"


class TestRoutingRegression:
    """票面验收 3：评测壳链中招三题原句问法——最终分派非未接线链。

    mock 复刻评测败因（LLM 裁决选中壳链——评测报告 §4.8/§4.9 verdict 帧），
    断言修复后实派链落在分派器注册面内、答案不再出现「未开通」话术。
    """

    @pytest.mark.parametrize(("question", "shell_chain"), [
        (B_ZHENG6_QUESTION, "指标卡直出链"),  # B-正6（评测 verdict 0.92 派壳链）
        (B_ZHENG7_QUESTION, "口径消歧链"),    # B-正7（评测 verdict 0.95——本组最高置信）
        (C_ZHENG6_QUESTION, "指标卡直出链"),  # C-正6（评测 verdict 0.85 派壳链）
    ])
    async def test_eval_questions_never_dispatch_unwired(
        self, chat_db: Any, seams: Seams, question: str, shell_chain: str,
    ) -> None:
        seams.index_vector = [_hit(0.7)]
        seams.intent_reply = json.dumps(
            {"chain": shell_chain, "confidence": 0.92}, ensure_ascii=False,
        )
        service = make_service(chat_db, seams)
        events = await collect(service.ask(
            question, session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        assert _dispatched_chain(events) in set(service.dispatcher.registered())
        answer = _events_by_name(events)["answer"][0]
        assert "该能力暂未开通" not in str(answer["text"])


class TestTerminalVerdictInvariant:
    """「run 终态 verdict 与实派链一致」不变量的持久面钉住（中途审查发现 2）。

    service._verify_chain_wiring docstring 声明：分派前覆写使 run 终态 verdict
    与实派链一致——_record_verdict 先落原裁决、_finish_run 终态用覆写后 dict
    重写；若后续写序调乱，流内帧断言不红，此测经 store 读口兜底。
    """

    async def test_persisted_terminal_verdict_matches_dispatched_chain(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """LLM 桩返回壳链名 → 跑完整 ask 流 → store 读口回取持久 verdict 终态＝检索问答链。"""
        seams.index_vector = [_hit(0.7)]
        seams.intent_reply = '{"chain": "指标卡直出链", "confidence": 0.92}'
        service = make_service(chat_db, seams)
        events = await collect(service.ask(
            B_ZHENG6_QUESTION, session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        run_id = _events_by_name(events)["session"][0]["run_id"]
        run = await ChatStore(chat_db).get_run(run_id)
        assert run is not None and run.status == "done"
        assert run.verdict is not None
        # 终态持久 verdict＝实派链（非 LLM 原裁决的壳链名「指标卡直出链」）
        assert run.verdict["chain"] == "检索问答链"
        assert run.verdict["chain"] == _dispatched_chain(events)
        # 覆写只动 chain 键——confidence/source 留痕不动（LLM 原裁决置信仍在）
        assert run.verdict["source"] == "llm"
        assert str(run.verdict["confidence"]).startswith("高")


class TestDispatcherWiringFace:
    """is_registered 查询面（domain.py 新 API——注册表键即接线事实）。"""

    def test_is_registered_mirrors_registry(self) -> None:
        dispatcher = d.ChainDispatcher()
        assert dispatcher.is_registered("检索问答链") is False
        dispatcher.register("检索问答链", _stub_handler)
        assert dispatcher.is_registered("检索问答链") is True
        assert dispatcher.is_registered("指标卡直出链") is False
        assert dispatcher.registered() == ("检索问答链",)


class TestRerouteAudit:
    """M-07 F-03：接线回退补 B12 审计行（chat.ask.rerouted）。

    R-MAIN F-03：回退事实此前只在 N5b 帧 note 与 run 终态 verdict 可见——
    00 §8.2「拦截也是审计事件」同族的路由改写不留审计痕迹。修法：回退发生时
    落笔一行（动作语义照 chat.ask 审计族惯例），正常路径零开销。
    """

    async def _audit_rows(self, db: Any) -> list[tuple[str, str]]:
        import sqlite3

        url = str(db.engine().url)
        conn = sqlite3.connect(url.removeprefix("sqlite+aiosqlite:///"))
        try:
            rows = conn.execute(
                "SELECT action, content FROM audit_log ORDER BY id"
            ).fetchall()
        finally:
            conn.close()
        return [(str(a), str(c)) for a, c in rows]

    async def test_reroute_writes_b12_audit_row(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """回退发生→审计行：action=chat.ask.rerouted，content 携原裁决链与 run。"""
        seams.index_vector = [_hit(0.7)]  # 检索链真出答案——回退落到能作答的链
        seams.intent_reply = '{"chain": "指标卡直出链", "confidence": 0.92}'
        service = make_service(chat_db, seams)
        events = await collect(service.ask(
            B_ZHENG6_QUESTION, session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        run_id = _events_by_name(events)["session"][0]["run_id"]
        assert _dispatched_chain(events) == "检索问答链"  # 回退确已发生（前置）
        rows = await self._audit_rows(chat_db)
        reroutes = [c for a, c in rows if a == "chat.ask.rerouted"]
        assert len(reroutes) == 1  # 回退一行——恰一次落笔
        assert "指标卡直出链" in reroutes[0]  # 原裁决链名留痕
        assert run_id in reroutes[0] and "检索问答链" in reroutes[0]

    async def test_registered_chain_writes_no_reroute_row(
        self, chat_db: Any, seams: Seams,
    ) -> None:
        """正常路径零开销：已接线链——零回退审计行（受理行照常在）。"""
        seams.index_vector = [_hit(0.7)]
        seams.intent_reply = '{"chain": "检索问答链", "confidence": 0.9}'
        service = make_service(chat_db, seams)
        events = await collect(service.ask(
            B_ZHENG6_QUESTION, session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        assert _dispatched_chain(events) == "检索问答链"
        rows = await self._audit_rows(chat_db)
        assert [a for a, _c in rows if a == "chat.ask.rerouted"] == []
        assert any(a == "chat.ask.received" for a, _c in rows)  # 受理审计不受影响
