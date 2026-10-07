"""DE-16 新鲜度闸配置开关测试——察2 形态替身两态行为＋additive 注记＋零触碰回归。

- false 态：无时间词＋外表问句（察2 同型——Q9W-数-察2.json 实跑帧为行为基准）
  不再被 N7.4a 拦停，直达 N7.4c 外表审批挂起（interrupt 帧）；N7.4a 出
  node_skip 帧（state=wait＋skipped:true）携 additive 注记（键名在场）；
  水位读缝零消费（不读水位——闸整体关）；N7.4b 行级/N7.4c 审批语义零触碰
  （批后续跑 extable 答案回归）。
- true 态：现行拦停接续回归零变化（对照既有 (f) 族）。
- 缺省态（未配置）：缺省 true＝现状（ChatService 组合缝缺省读 database.yaml
  chat 段——仓内缺省 true；显式缺省装配行为同 true 态）。

装配：sqlite 底座＋Seams 假缝（conftest）；察2 形态＝水位落后 36 天（实跑帧
同因——默认窗整体晚于水位）＋「无时间词＋ERP 外表」问句。
"""

from typing import Any

from app.domains.chat import domain as d
from app.domains.chat.domain import IndexHitFace
from app.infra.db import ConnectionManager
from tests.domains.chat.conftest import (
    AQIANG,
    Seams,
    collect,
    make_service,
    node_walk,
)
from tests.domains.chat.test_chat_query_chain import (
    _events_by_name,
    _node_notes,
    _run_id_of,
    _run_row,
    _waterline,
)

# 察2 形态替身：无时间词（→默认窗「最近 30 天」）＋ERP 外表引用（→N7.4c 越集）。
CHASH2_QUESTION = "日产油量最高的三口井，和 ERP 井位台账对一下"


def _chash2_waterline() -> d.WaterlineFace:
    """察2 实跑帧同因水位：落后 36 天（Q9W-数-察2.json——默认窗整体晚于水位）。"""
    return _waterline(late_days=36)


def _n74a_frames(events: list[Any]) -> list[dict[str, Any]]:
    return [
        event.data
        for event in events
        if event.event == "node" and event.data.get("key") == "N7.4a"
    ]


class TestFreshnessGateOff:
    async def test_false_skips_block_reaches_extable_approval(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """false 态：察2 形态替身不再拦停——直达 N7.4c 审批挂起（interrupt 帧）。

        基准＝eval/results/frames/Q9W-数-察2.json（true 态实证：N7.4a 拦停接续
        检索，审批永不可达）；false 态翻转该结局：审批帧在场、流收束不发 done。
        """
        seams.waterline = _chash2_waterline()
        service = make_service(chat_db, seams, freshness_gate_enabled=False)
        events = await collect(service.ask(
            CHASH2_QUESTION, session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        by_name = _events_by_name(events)
        # 直达审批位：approval 帧（A1 帧 15 形状）＋run 挂起 interrupt_approval。
        approval = by_name["approval"][0]
        assert approval["scene"] == "extable"
        assert "erp_well_register" in approval["reason"]
        assert "done" not in by_name and "answer" not in by_name
        assert seams.calls.get("query_exec") is None  # 未批准不执行
        run = await _run_row(chat_db, _run_id_of(events))
        assert run.status == "interrupt_approval"
        assert run.pending_interrupt is not None
        assert run.pending_interrupt["kind"] == "approval"
        assert run.pending_interrupt["tables"] == ["erp_well_register"]

    async def test_false_emits_skip_frame_with_additive_note(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """false 态：N7.4a 出 node_skip 帧（wait＋skipped:true）——additive 注记
        携配置键名在场（照 chunk_check additive 先例——帧内文字，不改帧枚举）。"""
        seams.waterline = _chash2_waterline()
        service = make_service(chat_db, seams, freshness_gate_enabled=False)
        events = await collect(service.ask(
            CHASH2_QUESTION, session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        frames = _n74a_frames(events)
        assert len(frames) == 1  # 单帧跳过——不出 process/finish 对
        skip_frame = frames[0]
        assert skip_frame["state"] == d.NODE_WAIT
        assert skip_frame.get("skipped") is True
        note = str(skip_frame.get("note") or "")
        assert "新鲜度闸已按配置关闭" in note
        assert "freshness_gate_enabled" in note  # 配置键名在场（票面要求）

    async def test_false_never_touches_waterline_seam(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """false 态：水位读缝零消费——闸整体关（不读水位、不比对、不改绑）。"""
        seams.waterline = _chash2_waterline()
        service = make_service(chat_db, seams, freshness_gate_enabled=False)
        events = await collect(service.ask(
            CHASH2_QUESTION, session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        assert seams.calls.get("waterline") is None
        # N7.4b/N7.4c 零触碰：行级权限帧与审批帧照常在场。
        notes = _node_notes(events)
        assert any("行级权限" in note for note in notes)
        assert any("erp_well_register" in note and "人工审批" in note for note in notes)

    async def test_false_extable_approve_resumes_to_result(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """false 态挂起后批准续跑：N7.4c 审批状态机零变化（extable 答案＋留痕）。"""
        seams.waterline = _chash2_waterline()
        service = make_service(chat_db, seams, freshness_gate_enabled=False)
        first = await collect(service.ask(
            CHASH2_QUESTION, session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        run_id = _run_id_of(first)
        events = await collect(service.resume(
            run_id, kind="approval", choice=None, decision="approve", reason=None,
            actor_who=AQIANG,
        ))
        by_name = _events_by_name(events)
        assert by_name["answer"][0]["kind"] == "extable"
        assert by_name["answer"][0]["decision"] == "approved"
        assert "lineage" in by_name  # 血缘帧照发（审批支专帧不断）
        assert "done" in by_name
        # 血缘④补读恰一次（FX-10/R3-10）：闸关态只在批准续跑出数后消费水位读缝
        # （挂起段零消费——见 test_false_never_touches_waterline_seam）。
        assert seams.calls.get("waterline") == 1
        # 血缘④行含替身水位日期真值——防补读三行被删后渲染成
        # 「—（水位未回写——如实缺行，不造达标假象）」的造假象形态而测试全绿。
        watermark_value = next(
            item["value"] for item in by_name["lineage"][0]["items"]
            if item["key"] == d.LINEAGE_KEY_WATERMARK
        )
        assert _chash2_waterline().data_date.isoformat() in watermark_value


class TestFreshnessGateOn:
    async def test_true_state_blocks_as_before(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """true 态（显式注入）：察2 形态照旧拦停接续检索——审批永不可达（现状回归）。"""
        seams.waterline = _chash2_waterline()
        seams.index_vector = [IndexHitFace(
            fragment_id="f1", report_id="rpt-1", report="N-02 完井报告",
            section="01 井基本情况", snippet="检泵周期记录", score=0.7, leg="vector",
            text="N-02 井检泵周期记录——报告库检索片段",
        )]
        service = make_service(chat_db, seams, freshness_gate_enabled=True)
        events = await collect(service.ask(
            CHASH2_QUESTION, session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        by_name = _events_by_name(events)
        assert any("拦停，不出空数" in note for note in _node_notes(events))
        assert seams.calls.get("waterline") == 1  # 闸照常读水位
        assert "approval" not in by_name  # 拦停在前——审批不可达（察2 现状）
        answer = by_name["answer"][0]
        assert answer["kind"] == "text"
        assert "数据库口径未能出数" in str(answer["text"])
        assert "done" in by_name

    async def test_default_is_true_same_block(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """缺省（未注入参数）：缺省 true＝现状——拦停行为与 true 态一致。"""
        seams.waterline = _chash2_waterline()
        service = make_service(chat_db, seams)
        events = await collect(service.ask(
            CHASH2_QUESTION, session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        by_name = _events_by_name(events)
        assert any("拦停，不出空数" in note for note in _node_notes(events))
        assert "approval" not in by_name
        assert seams.calls.get("waterline") == 1


class TestGateWiring:
    async def test_service_wires_explicit_flag_into_chain_deps(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """组合缝：显式参数进 ChainDeps；缺省装配读 chat 配置面（缺省 true）。"""
        service_off = make_service(chat_db, seams, freshness_gate_enabled=False)
        assert service_off._deps.freshness_gate_enabled is False
        service_default = make_service(chat_db, seams)
        assert service_default._deps.freshness_gate_enabled is True

    async def test_off_frame_walk_keeps_three_gates_in_order(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """false 态帧序：N7.4 三闸站序不乱——N7.4a 跳过帧仍在 N7.4b/N7.4c 之前。"""
        seams.waterline = _chash2_waterline()
        service = make_service(chat_db, seams, freshness_gate_enabled=False)
        events = await collect(service.ask(
            CHASH2_QUESTION, session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        seq = [key for key, _state in node_walk(events)]
        firsts = [seq.index(k) for k in ("N7.4", "N7.4a", "N7.4b", "N7.4c")]
        assert firsts == sorted(firsts)
