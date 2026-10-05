"""W-AUX 修复拍（停线裁决 C）——辅助检索＋叙述生成以 notice 旁注帧呈现。

票面（dispatch/pending/W-AUX.fix.md）验收对应用例：
- 辅助检索：N7.5 只读执行行数>0 后，原问句复用检索链双路召回（index_searcher_dual
  同一注入缝——零新缝）取小窗口辅助片段（AUX_TOP_K=4）；报告库空 → 纯表格自然
  降级零报错；
- 叙述生成：辅助片段＋表格数据进 gateway.complete（caller=chat.query.narrate，
  照 chat.query.rewrite 计费留痕惯例），提示词三约束：数值一律以表格为准（片段
  数值不采）／引用标注 cN／不得虚构；
- 旁注帧呈现（裁决 C——零合同变更，复用既有 notice 机制，P2-03 状态标注先例）：
  解读段以 notice 帧并列呈现，位置＝血缘帧后、answer 帧前（A1 帧合同：answer 恒
  最后；notice 载荷 {level, text} 冻结形状——零新帧型、answer 载荷零新增键）；
- 变异断言：片段携假数值 → 表格/血缘卡数值原样（旁注不污染权威数）；
- caller 计费留痕：chat.query.narrate 在 completer caller 记录中。
"""

import json
from datetime import timedelta
from typing import Any

from app.domains.chat import domain as d
from app.domains.chat.chains import CALLER_NARRATE, NARRATE_SYSTEM_PROMPT
from app.domains.chat.domain import IndexHitFace
from app.infra.clock import now
from app.infra.db import ConnectionManager
from tests.domains.chat.conftest import (
    AQIANG,
    Seams,
    collect,
    events_by_name,
    make_service,
    node_walk,
)

DATA_QUESTION = "上个月日产油量最高的三口井"

# A1 answer kind=table 载荷冻结键集（票面验收：解读段不得新增 answer 键——裁决 C
# 以 notice 帧并列呈现，answer 形状原样）。
TABLE_ANSWER_KEYS = {
    "kind", "title", "note", "columns", "rows", "source_note",
    "chart_suggestion", "citations", "tool_call", "lineage",
}

# 全景树节点键在册集（A1 册「key 与全景树 41 节点键一致」——旁注帧施工不发明新键；
# 集合同 test_chat_query_fallback_continue.py，本文件自持拷贝防跨文件漂移）。
PANORAMA_KEYS = {
    "N1", "N2a", "N2b", "N3", "N4", "N5", "N5a", "N5b", "N6",
    "N7.1", "N7.2", "N7.3", "N7.4", "N7.4a", "N7.4b", "N7.4c", "N7.5", "N7.6",
    "N13", "N17", "N18",
    "S0", "S1", "S3", "S4", "S5", "S6", "S7", "GEN",
}


def _hit(fragment_id: str, text: str, *, leg: str = "vector") -> IndexHitFace:
    """报告索引命中桩行（辅助检索双路任一腿——锚默认真锚 rpt-1，见 conftest）。"""
    return IndexHitFace(
        fragment_id=fragment_id, report_id="rpt-1", report="N-02 完井报告",
        section="02 完井总结", snippet=text[:40], score=0.7, leg=leg, text=text,
    )


def _waterline() -> d.WaterlineFace:
    """汇总层水位面（达标＝昨天——E2 T-1 语义，基准＝infra.clock）。"""
    data_date = now().date() - timedelta(days=1)
    return d.WaterlineFace(
        layer="汇总层", data_date=data_date, promise="T-1",
        tag="达标（承诺 T-1）", late_days=0,
    )


async def _ask(seams: Seams, chat_db: ConnectionManager, question: str = DATA_QUESTION,
               ) -> list[Any]:
    service = make_service(chat_db, seams)
    return await collect(service.ask(
        question, session_id=None, page_context=None, anchors=[], actor_who=AQIANG,
    ))


def _narrate_prompts(seams: Seams) -> list[list[dict[str, str]]]:
    """caller=chat.query.narrate 的消息捕获（计费留痕与提示词断言的观测面）。"""
    return [
        messages for caller, messages in seams.prompts if caller == CALLER_NARRATE
    ]


# ---------- 辅助检索（行数>0 后双路召回复用——小窗口取片段） ----------


class TestAuxRetrieval:
    async def test_rows_found_reuses_dual_recall_small_window(
        self, chat_db: ConnectionManager, seams: Seams,
    ) -> None:
        """出数后原问句复用双路召回缝恰一次；片段小窗口 4 支；别名自 c3 起
        （表卡数据证据 c1/c2 已占——同一 run 内全局不撞号）。"""
        seams.fail_intent = True
        seams.waterline = _waterline()
        seams.index_vector = [_hit(f"f{i}", f"片段甲{i}——背景材料") for i in range(1, 7)]
        seams.index_keyword = [
            _hit(f"k{i}", f"片段乙{i}——背景材料", leg="keyword") for i in range(1, 7)
        ]
        events = await _ask(seams, chat_db)
        by_name = events_by_name(events)
        assert by_name["answer"][0]["kind"] == "table"
        assert seams.calls.get("query_exec") == 1  # 主路照常出数
        assert seams.calls.get("index_dual") == 1  # 双路召回缝恰一次（辅助检索复用）
        prompts = _narrate_prompts(seams)
        assert len(prompts) == 1  # 叙述生成恰一次调用
        user_content = prompts[0][1]["content"]
        fragment_lines = [
            ln for ln in str(user_content).splitlines() if ln.startswith("c")
        ]
        assert len(fragment_lines) == 4  # 小窗口 topK=4（票面定值）
        assert any(ln.startswith("c3：") for ln in fragment_lines)  # 别名自 c3 起
        assert all(not ln.startswith(("c1：", "c2：")) for ln in fragment_lines)
        assert "c7：" not in str(user_content)

    async def test_report_library_empty_pure_table_zero_error(
        self, chat_db: ConnectionManager, seams: Seams,
    ) -> None:
        """报告库空（检索无片段）→ 纯表格自然降级：零旁注帧、零模型调用、零报错。"""
        seams.fail_intent = True
        seams.waterline = _waterline()
        events = await _ask(seams, chat_db)
        by_name = events_by_name(events)
        answer = by_name["answer"][0]
        assert answer["kind"] == "table"
        assert [c["ref"] for c in answer["citations"]] == ["c1", "c2"]  # 表卡出处原样
        assert "notice" not in by_name  # 无旁注帧
        assert "error" not in by_name
        assert set(seams.completions) <= {"chat.intent.verdict"}  # 零新增模型调用
        assert events[-1].event == "done"


# ---------- 叙述生成（caller 计费留痕＋提示词三约束） ----------


class TestNarrateGeneration:
    def test_prompt_carries_three_constraints(self) -> None:
        """提示词三约束在位：表格为准（片段不采）／cN 引用标注／不得虚构。"""
        assert "表格为准" in NARRATE_SYSTEM_PROMPT
        assert "不采" in NARRATE_SYSTEM_PROMPT
        assert "[c1]" in NARRATE_SYSTEM_PROMPT  # cN 标注格式示例
        assert "不得虚构" in NARRATE_SYSTEM_PROMPT

    async def test_prompt_carries_table_and_fragments(
        self, chat_db: ConnectionManager, seams: Seams,
    ) -> None:
        """生成窗＝权威表格数据＋辅助片段同场；表格行与片段原文逐字进提示词。"""
        seams.fail_intent = True
        seams.waterline = _waterline()
        seams.index_vector = [_hit("f1", "渤南区块完井背景材料")]
        seams.completion = "上个月渤南区块领先 [c3]。"
        await _ask(seams, chat_db)
        prompts = _narrate_prompts(seams)
        assert len(prompts) == 1
        system_content, user_content = prompts[0][0]["content"], prompts[0][1]["content"]
        assert system_content == NARRATE_SYSTEM_PROMPT
        assert "4860" in str(user_content)  # 权威表格行值在场
        assert "渤南区块完井背景材料" in str(user_content)  # 辅助片段原文在场
        assert "c3" in str(user_content)  # 片段编号表可被引用

    async def test_caller_billing_trace(
        self, chat_db: ConnectionManager, seams: Seams,
    ) -> None:
        """caller 计费留痕：chat.query.narrate 进 completer caller 记录（照
        chat.query.rewrite 惯例）；除裁决外无其他新 caller。"""
        seams.fail_intent = True
        seams.waterline = _waterline()
        seams.index_vector = [_hit("f1", "背景材料")]
        seams.completion = "解读 [c3]。"
        await _ask(seams, chat_db)
        assert CALLER_NARRATE in seams.completions
        assert set(seams.completions) <= {"chat.intent.verdict", CALLER_NARRATE}


# ---------- 旁注帧呈现（裁决 C——notice 帧并列，零合同变更） ----------


class TestNarrateNoticeFrame:
    async def test_narration_arrives_as_notice_with_cn_citations(
        self, chat_db: ConnectionManager, seams: Seams,
    ) -> None:
        """解读段以 notice 帧呈现：血缘后、answer 前；cN 引用先行展开
        （citation 帧冻结形状）；answer 载荷零新增键、表卡出处原样。"""
        seams.fail_intent = True
        seams.waterline = _waterline()
        seams.index_vector = [_hit("f1", "渤南区块完井背景材料")]
        narration_text = "上个月渤南区块日产油量领先，完井报告有相关背景 [c3]。"
        seams.completion = narration_text
        events = await _ask(seams, chat_db)
        by_name = events_by_name(events)
        order = [e.event for e in events]
        # citation 帧：c3 片段出处展开（A1 冻结形状四键）。
        citations = [c for c in by_name["citation"] if c["ref"] == "c3"]
        assert len(citations) == 1
        assert set(citations[0].keys()) == {"ref", "kind", "label", "locator"}
        assert citations[0]["kind"] == "报告引用"
        assert citations[0]["locator"]["fragment_id"] == "f1"
        # notice 帧：解读段全文、info 级（旁注并列——不冒充正文流）。
        narration_notices = [
            n for n in by_name["notice"]
            if n["text"] == narration_text and n["level"] == "info"
        ]
        assert len(narration_notices) == 1
        # 帧位次：lineage → citation(c3) → notice(解读) → answer → done。
        assert order.index("lineage") < order.index("citation") < \
            order.index("notice") < order.index("answer")
        assert order[-1] == "done"
        assert order.count("answer") == 1
        # answer 帧形状冻结：无解读槽位新键；表卡出处仍＝数据证据 c1/c2。
        answer = by_name["answer"][0]
        assert set(answer.keys()) <= TABLE_ANSWER_KEYS
        assert "narrative" not in answer and "caption" not in answer
        assert [c["ref"] for c in answer["citations"]] == ["c1", "c2"]
        # 旁注不走 token 流（P2-03 先例——通知帧并列，正文流语义不挪用）。
        assert "token" not in by_name
        assert "error" not in by_name

    async def test_mutation_fake_fragment_values_never_touch_table_or_lineage(
        self, chat_db: ConnectionManager, seams: Seams,
    ) -> None:
        """变异断言：片段携假数值 99999 → 表格行/血缘卡数值原样（旁注不污染
        权威数——票面「数值一律以表格为准」的红线由呈现位次物理保证）。"""
        seams.fail_intent = True
        seams.waterline = _waterline()
        seams.index_vector = [_hit("f1", "片段假数值：日产油量 99999 吨")]
        seams.completion = "各井日产油量合计高达 99999 吨，背景见 [c3]。"
        events = await _ask(seams, chat_db)
        by_name = events_by_name(events)
        # 变异路径在场：片段假数值确实进了生成窗并出现在旁注解读里。
        assert any("99999" in str(n.get("text")) for n in by_name["notice"])
        # 权威数零污染：answer 帧与 lineage 帧全文无假数值。
        answer = by_name["answer"][0]
        assert "99999" not in json.dumps(answer, ensure_ascii=False, default=str)
        assert "99999" not in json.dumps(
            by_name["lineage"][0], ensure_ascii=False, default=str,
        )
        assert answer["rows"] == seams.query_rows  # 表格行逐行原样

    async def test_hallucinated_ref_stripped_fail_closed(
        self, chat_db: ConnectionManager, seams: Seams,
    ) -> None:
        """fail-closed：解读段引用未提供的别名 [c9] → 拦截剥除＋warning 留痕，
        绝不带病出帧（照检索链 GEN 收口同款）。"""
        seams.fail_intent = True
        seams.waterline = _waterline()
        seams.index_vector = [_hit("f1", "背景材料")]
        seams.completion = "解读：产量背景见 [c9]。"
        events = await _ask(seams, chat_db)
        by_name = events_by_name(events)
        citation_refs = [c["ref"] for c in by_name.get("citation", [])]
        assert "c9" not in citation_refs  # 伪造别名不外发
        assert all("[c9]" not in str(n.get("text")) for n in by_name["notice"])
        assert any("已拦截 1 条失锚/伪造引用" in str(n.get("text"))
                   for n in by_name["notice"])


# ---------- 降级面（生成不可用 → 纯表格零报错）与帧序合同 ----------


class TestNarrateDegradationAndFrameContract:
    async def test_generation_unusable_pure_table_zero_error(
        self, chat_db: ConnectionManager, seams: Seams,
    ) -> None:
        """生成空输出（_complete 软失败）→ 纯表格自然降级：零旁注帧零报错，
        辅助检索行留痕照常（检索与生成两段降级互不牵连）。"""
        seams.fail_intent = True
        seams.waterline = _waterline()
        seams.index_vector = [_hit("f1", "背景材料")]
        seams.completion = ""  # 空输出＝生成不可用（照 rewrite 惯例回落）
        events = await _ask(seams, chat_db)
        by_name = events_by_name(events)
        answer = by_name["answer"][0]
        assert answer["kind"] == "table"
        assert [c["ref"] for c in answer["citations"]] == ["c1", "c2"]
        assert "notice" not in by_name and "error" not in by_name
        assert events[-1].event == "done"

    async def test_generation_raises_pure_table_zero_error(
        self, chat_db: ConnectionManager, seams: Seams,
    ) -> None:
        """生成调用硬异常 → 同款纯表格降级（不炸链——搜不到/生成不了都不报错）。"""
        seams.fail_intent = True
        seams.waterline = _waterline()
        seams.index_vector = [_hit("f1", "背景材料")]
        original = seams.complete

        async def exploding(
            alias: str, messages: list[dict[str, str]], *, caller: str, **params: Any,
        ) -> Any:
            if caller == CALLER_NARRATE:
                raise RuntimeError("解读生成上游失败（桩）")
            return await original(alias, messages, caller=caller, **params)

        seams.complete = exploding  # type: ignore[method-assign]
        events = await _ask(seams, chat_db)
        by_name = events_by_name(events)
        answer = by_name["answer"][0]
        assert answer["kind"] == "table"
        assert "notice" not in by_name and "error" not in by_name
        assert events[-1].event == "done"

    async def test_frame_sequence_contract_with_narration(
        self, chat_db: ConnectionManager, seams: Seams,
    ) -> None:
        """帧序合法性（对照 A1 帧合同）：节点键全景树在册、状态推进单向、
        notice level 枚举内、answer 恰一次且 done 收尾、零异常帧。"""
        seams.fail_intent = True
        seams.waterline = _waterline()
        seams.index_vector = [_hit("f1", "渤南区块完井背景材料")]
        seams.completion = "上个月渤南区块领先 [c3]。"
        events = await _ask(seams, chat_db)
        # 节点键在册——旁注施工不发明新键。
        keys = {key for key, _state in node_walk(events)}
        assert keys <= PANORAMA_KEYS
        # 节点状态推进单向：每键恰一终态（finish/wait）且终态最后。
        seen: dict[str, list[str]] = {}
        for key, state in node_walk(events):
            seen.setdefault(key, []).append(state)
        for key, states in seen.items():
            assert set(states) <= {"process", "finish", "wait"}, f"{key}: {states}"
            assert states[-1] in ("finish", "wait"), f"{key} 无终态"
            assert states.count("finish") + states.count("wait") == 1, f"{key}: {states}"
        # notice level 枚举内；citation 帧形状冻结；收束纪律。
        assert all(n["level"] in ("info", "warning") for n in events_by_name(events)["notice"])
        order = [e.event for e in events]
        assert order.count("answer") == 1
        assert order[-1] == "done"
        assert "error" not in order and "clarify" not in order and "approval" not in order
        assert "replay_truncated" not in order
