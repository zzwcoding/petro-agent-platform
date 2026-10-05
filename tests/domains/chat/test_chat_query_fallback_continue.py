"""W-AUX 降级接续＋判型恢复测试——问数链出不了数自动接续检索问答链。

票面（dispatch/pending/W-AUX.md）验收 (a)(c)(d)：
- (a) 判型恢复：N5 裁决提示词携分型路由（数据型→状态机六站链／报告叙述型→
  检索问答链／复合题检索兜底／纯定义问法仍检索链）——P1F-01「自然语言一律
  检索问答链」过渡约束经 Owner 2026-10-05 批准撤除（状态机六站链已接线非空
  壳）；确定性信号路由兜底面回归（数据型入六站、纯定义留检索）；
- (c) 降级接续：0 行／全窗未出数／无注册声明三路自动接续检索问答链（同模块
  retrieval_chain 函数级复用），答案帧正文前置如实标注（检索结果非权威数值），
  引用照常；接续链仍无果 → 双重如实拒答（原拒答话术收场）；
- (d) 帧序合同：六站帧＋检索帧混排合法性（对照 A1 册 19 类帧协议——节点键
  全景树在册不发明新键、节点状态推进单向、token→citation→answer→done 收束、
  answer 恰一次）。
"""

from dataclasses import replace
from datetime import timedelta
from typing import Any

from app.domains.chat import domain as d
from app.domains.chat.domain import IndexHitFace
from app.domains.chat.service import INTENT_VERDICT_SYSTEM_PROMPT
from app.infra.clock import now
from app.infra.db import ConnectionManager
from tests.domains.chat.conftest import (
    AQIANG,
    DEFAULT_CONFIG,
    Seams,
    collect,
    events_by_name,
    make_service,
    node_walk,
)

DATA_QUESTION = "上个月日产油量最高的三口井"
DEFINITION_QUESTION = "什么是躺井？"
UNBOUND_QUESTION = "上个月产量完成率是多少"

# 票面规定的答案帧如实标注原文（W-AUX③——接续答案正文前置行）。
FALLBACK_ANNOTATION = "【数据库口径未能出数，以下为报告库检索结果（非权威数值）】"

# 全景树节点键在册集（A1 册「key 与全景树 41 节点键一致」——本域流水线＋四链
# 已用键的并集；混排合法性判据之一＝不发明集合外新键）。
PANORAMA_KEYS = {
    "N1", "N2a", "N2b", "N3", "N4", "N5", "N5a", "N5b", "N6",
    "N7.1", "N7.2", "N7.3", "N7.4", "N7.4a", "N7.4b", "N7.4c", "N7.5", "N7.6",
    "N13", "N17", "N18",
    "S0", "S1", "S3", "S4", "S5", "S6", "S7", "GEN",
}


def _hit(score: float = 0.7) -> IndexHitFace:
    """报告索引命中桩行（双路向量腿——接续检索链 S4 消费，score 过拒答线）。"""
    return IndexHitFace(
        fragment_id="f1", report_id="rpt-1", report="N-02 完井报告",
        section="01 井基本情况", snippet="检泵周期记录", score=score, leg="vector",
        text="N-02 井检泵周期记录——报告库检索片段",
    )


def _waterline(*, late_days: int = 0) -> d.WaterlineFace:
    """汇总层水位面（E2 T-1 语义——达标＝昨天；落后 N 天 · 超期）。"""
    today = now().date()
    data_date = today - timedelta(days=1 + late_days)
    tag = "达标（承诺 T-1）" if late_days <= 0 else f"落后 {late_days} 天 · 超期"
    return d.WaterlineFace(
        layer="汇总层", data_date=data_date, promise="T-1", tag=tag, late_days=late_days,
    )


def _node_notes(events: list[Any]) -> list[str]:
    return [str(e.data.get("note") or "") for e in events if e.event == "node"]


def _dispatched_chain(events: list[Any]) -> str:
    """N6 finish 帧的实派链名（「已分派至「X」」注记解析）。"""
    note = next(
        str(e.data["note"]) for e in events
        if e.event == "node" and e.data["key"] == "N6" and e.data["state"] == "finish"
    )
    return note.split("已分派至「")[1].split("」")[0]


async def _ask(chat_db: ConnectionManager, seams: Seams, question: str) -> list[Any]:
    service = make_service(chat_db, seams)
    return await collect(service.ask(
        question, session_id=None, page_context=None, anchors=[], actor_who=AQIANG,
    ))


# ---------- (a) 判型恢复：分型路由提示词＋确定性兜底面回归 ----------


class TestIntentPromptTypedRouting:
    def test_prompt_typed_routing_replaces_all_retrieval_constraint(self) -> None:
        """(a) 提示词携分型路由四则；「自然语言一律选检索问答链」过渡约束已撤。"""
        prompt = INTENT_VERDICT_SYSTEM_PROMPT
        # 数据型（命中指标声明＋取值诉求）→ 状态机六站链。
        assert "分型路由" in prompt
        assert "状态机六站链" in prompt
        assert "取值诉求" in prompt  # P1F-02 精化：命中＋取值诉求合判
        for word in ("多少", "最高", "最低", "排名", "对比"):
            assert word in prompt, f"取值诉求词面缺「{word}」"
        # 报告型/叙述型 → 检索问答链；复合题 → 检索兜底；纯定义问法 → 检索链。
        assert "检索问答链" in prompt
        assert "复合题" in prompt
        assert "纯定义" in prompt
        # 旧过渡约束撤除（Owner 2026-10-05 批准——六站链已接线非空壳）。
        assert "一律选" not in prompt
        # @ 显式锚定兜底与「仅受理 @ 锚定」条款不变（P1F-01 其余纪律保留）。
        assert "@ 显式锚定" in prompt
        assert "「指标卡直出链」「口径消歧链」" in prompt
        assert "装配材料信号" in prompt


class TestDeterministicTypedRouting:
    async def test_llm_down_data_question_falls_back_to_six_station(
        self, chat_db: ConnectionManager, seams: Seams,
    ) -> None:
        """(a) 确定性兜底面回归：LLM 不可用——数据型问句（指标命中＋词面）→ 六站链。"""
        seams.fail_intent = True  # LLM 裁决失败——确定性信号路由兜底
        seams.waterline = _waterline()
        events = await _ask(chat_db, seams, DATA_QUESTION)
        by_name = events_by_name(events)
        assert by_name["verdict"][0]["source"] == "deterministic"
        assert _dispatched_chain(events) == "状态机六站链"  # 不再一律检索
        assert by_name["answer"][0]["kind"] == "table"

    async def test_llm_down_pure_definition_routes_retrieval(
        self, chat_db: ConnectionManager, seams: Seams,
    ) -> None:
        """(a) 纯定义问法（什么是 X）无取值诉求——确定性面仍派检索问答链。"""
        seams.fail_intent = True
        seams.index_vector = [_hit()]
        events = await _ask(chat_db, seams, DEFINITION_QUESTION)
        assert _dispatched_chain(events) == "检索问答链"
        answer = events_by_name(events)["answer"][0]
        assert answer["kind"] == "text"


# ---------- (c) 降级接续：三路出不了数 × 接续成功／双重拒答 ----------


class TestDataChainFallbackContinue:
    async def test_zero_rows_continues_to_retrieval_with_annotation(
        self, chat_db: ConnectionManager, seams: Seams,
    ) -> None:
        """(c) 0 行 → 自动接续检索问答链：答案帧前置如实标注＋引用照常＋零报错。"""
        seams.intent_reply = '{"chain": "状态机六站链", "confidence": 0.95}'
        seams.waterline = _waterline()
        seams.query_rows = []  # N7.6 核验 0 行
        seams.index_vector = [_hit()]  # 接续链真检索出报告证据
        events = await _ask(chat_db, seams, DATA_QUESTION)
        by_name = events_by_name(events)
        # 六站走到 N7.6 且如实报 0 行（note 留痕），随后接续检索链帧。
        seq = [key for key, _state in node_walk(events)]
        assert "N7.6" in seq and "N17" in seq
        assert seq.index("N7.6") < seq.index("N17")  # 六站在前、检索帧续后
        assert any("0 行" in note for note in _node_notes(events))
        # 接续提示 notice（如实标注）在检索链答案前。
        notice_texts = [str(n["text"]) for n in by_name["notice"]]
        assert any("数据库口径未能出数" in t for t in notice_texts)
        # 答案帧恰一次：kind=text＋正文前置标注＋引用照常。
        answers = by_name["answer"]
        assert len(answers) == 1
        answer = answers[0]
        assert answer["kind"] == "text"
        assert str(answer["text"]).startswith(FALLBACK_ANNOTATION)
        assert answer["citations"], "接续检索真出答案须携引用"
        # token 流与答案帧同文（标注进正文——流式不撒谎）。
        tokens = "".join(str(t["delta"]) for t in by_name["token"])
        assert tokens == answer["text"]
        assert events[-1].event == "done"

    async def test_zero_rows_double_miss_refuses_honestly(
        self, chat_db: ConnectionManager, seams: Seams,
    ) -> None:
        """(c) 接续链也兜底（证据全不过低分线）→ 双重如实拒答（0 行原话收场）。"""
        seams.intent_reply = '{"chain": "状态机六站链", "confidence": 0.95}'
        seams.waterline = _waterline()
        seams.query_rows = []
        seams.config = replace(DEFAULT_CONFIG, refuse_threshold=1.5)  # 一切证据不过线
        events = await _ask(chat_db, seams, DATA_QUESTION)
        by_name = events_by_name(events)
        answers = by_name["answer"]
        assert len(answers) == 1
        answer = answers[0]
        assert answer["kind"] == "alert"
        assert "查询执行成功但无数据行" in str(answer["text"])
        assert "如实回报，不编数" in str(answer["text"])
        # 接续链兜底流不外泄：无游离 token、无「台账有收录」兜底卡冒充答案。
        assert "token" not in by_name
        assert "台账有收录" not in str(answer["text"])
        assert events[-1].event == "done"

    async def test_unbound_metric_continues_to_retrieval(
        self, chat_db: ConnectionManager, seams: Seams,
    ) -> None:
        """(c) N7.1 无注册声明（未绑定计量列）→ 接续检索＋标注；降级注记保持。"""
        seams.intent_reply = '{"chain": "状态机六站链", "confidence": 0.9}'
        seams.index_vector = [_hit()]
        events = await _ask(chat_db, seams, UNBOUND_QUESTION)
        by_name = events_by_name(events)
        # 降级解释链注记保持（不冒充审定口径的立场不变），但不再以拒答收场。
        assert any("不冒充审定口径" in note for note in _node_notes(events))
        answer = by_name["answer"][0]
        assert answer["kind"] == "text"
        assert str(answer["text"]).startswith(FALLBACK_ANNOTATION)
        assert "请先在指标台账登记" not in str(answer["text"])
        assert answer["citations"]
        assert events[-1].event == "done"

    async def test_unbound_metric_double_miss_refuses(
        self, chat_db: ConnectionManager, seams: Seams,
    ) -> None:
        """(c) 无声明＋接续也无果 → 双重如实拒答（注册声明出路原话）。"""
        seams.intent_reply = '{"chain": "状态机六站链", "confidence": 0.9}'
        seams.config = replace(DEFAULT_CONFIG, refuse_threshold=1.5)
        events = await _ask(chat_db, seams, UNBOUND_QUESTION)
        answer = events_by_name(events)["answer"][0]
        assert answer["kind"] == "alert"
        assert "未命中注册指标声明" in str(answer["text"])
        assert "不冒充审定口径" in str(answer["text"])

    async def test_freshness_full_miss_double_miss_refuses(
        self, chat_db: ConnectionManager, seams: Seams,
    ) -> None:
        """(c) 全窗未出数＋接续也无果 → 双重如实拒答（新鲜度话术原样恢复）。"""
        seams.intent_reply = '{"chain": "状态机六站链", "confidence": 0.95}'
        seams.waterline = _waterline(late_days=9)  # 水位＝today-10——「今天」全窗未出数
        seams.config = replace(DEFAULT_CONFIG, refuse_threshold=1.5)
        events = await _ask(chat_db, seams, "今天日产油量最高的三口井")
        by_name = events_by_name(events)
        answer = by_name["answer"][0]
        assert seams.calls.get("query_exec") is None  # 闸仍拦停——执行缝零调用
        assert answer["kind"] == "alert"
        assert "新鲜度闸拦停" in str(answer["text"])
        assert "不返回空数冒充" in str(answer["text"])
        # 拒答 notice 一并恢复（原路径警告行不因接续丢失）。
        assert any("不返回空数冒充" in str(n.get("text")) for n in by_name["notice"])


# ---------- (d) 帧序合同：六站帧＋检索帧混排合法性（对照 A1 帧协议） ----------


class TestMixedFrameSequenceContract:
    async def test_six_station_and_retrieval_frames_interleave_legally(
        self, chat_db: ConnectionManager, seams: Seams,
    ) -> None:
        """(d) 0 行接续场景全帧序：节点键在册／状态单向／answer 恰一次且 done 收尾。"""
        seams.intent_reply = '{"chain": "状态机六站链", "confidence": 0.95}'
        seams.waterline = _waterline()
        seams.query_rows = []
        seams.index_vector = [_hit()]
        events = await _ask(chat_db, seams, DATA_QUESTION)
        # ① 节点键全景树在册——混排不发明新键。
        keys = {key for key, _state in node_walk(events)}
        assert keys <= PANORAMA_KEYS
        # ② 节点状态推进单向：process→finish（或跳过级单帧 wait）；终态后无帧。
        seen: dict[str, list[str]] = {}
        for key, state in node_walk(events):
            seen.setdefault(key, []).append(state)
        for key, states in seen.items():
            assert set(states) <= {"process", "finish", "wait"}, f"{key}: {states}"
            assert states[-1] in ("finish", "wait"), f"{key} 无终态: {states}"
            assert states.count("finish") + states.count("wait") == 1, f"{key}: {states}"
            assert states.index(states[-1]) == len(states) - 1
        # ③ 六站痕迹与检索痕迹并存：tool_call（六站只读留痕，0 行）＋N17/S/GEN 帧。
        order = [e.event for e in events]
        tool_calls = [e.data for e in events if e.event == "tool_call"]
        assert len(tool_calls) == 1 and tool_calls[0]["readonly"] is True
        assert tool_calls[0]["rows_returned"] == 0
        seq = [key for key, _state in node_walk(events)]
        for station in ("N7.1", "N7.4a", "N7.4b", "N7.4c", "N7.5", "N7.6"):
            assert station in seq
        for node in ("N17", "S0", "S3", "S4", "S6", "S7", "GEN"):
            assert node in seq
        # ④ 收束纪律：token/citation 先行、answer 恰一次、done 最后、零异常帧。
        assert order.count("answer") == 1
        assert order[-1] == "done"
        assert "error" not in order and "clarify" not in order and "approval" not in order
        assert "lineage" not in order  # 0 行未达血缘卡站——接续答案不带表卡血缘
        assert max(i for i, e in enumerate(order) if e == "token") < \
            min(i for i, e in enumerate(order) if e == "citation") < \
            order.index("answer")
