"""domains.chat.service —— A1 问一问编排引擎：四层流水线全在服务端（F56）。

公开面照 98 §3.1 卡骨架拍（P1-08a）：ask（统一入口无旁路——POST /api/chat/asks）
＋resume（interrupt 决策回流——POST /api/chat/runs/{run_id}/resume）＋运行时读
recent_qa_pairs（B3 扫库料源——session_loader 注入位，P1-06 疑点 6 收口）。

四层流水线（F56①→④）：
  ①统一安检：注入扫描/禁用词索引/身份与数据域——字面规则任一 ✗ 拦截出终局
    （sec_check blocked → answer kind=alert 拦截话术 → done；拦截也是审计事件）。
  ②知识装配：@ 前门直取（取不到＝落空拒答）＋六路匹配器并行查表共池——词级
    全扫全收集（不存在「命中就停」漏词）；被 @ 的一路不过匹配器、其他五路照跑；
    落空进建议池（F60 晋升闸：孤例不进池）。
  ③意图裁决：骨架期＝确定性路由（FAQ 精确命中＋faq_direct_hit→FAQ直出链；
    口径两译未消歧→澄清帧挂起；其余→检索问答链）——真实裁决唯一真源＝D2 模型
    （闭世界 17 链枚举·结构化输出），随 P1-08b 接线（skeleton 标注随帧下发）。
  ④执行链分发：17 链闭世界分派；三链分派缝（检索/FAQ 秒回/图谱问答）08b 填，
    未实现链回「该能力暂未开通」话术。

澄清帧有界循环（F56）：最多弹一次、两跳到终态（默认口径或拒答）——挂起帧写入
chat_run.pending_interrupt（clarify_count CHECK 0–1 存储强制）；回流带参重过安检
（不免检）→ 带参重判 → 续推；第二次 clarify 一律 409。

LLM 出口（B6）：骨架期四层流水线零 LLM 依赖（冒烟零成本）——D2 模型裁决与检
索链生成随 P1-08b 经 gateway.complete 接线，本文件不 import gateway。
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.chat import domain as d
from app.domains.chat.store import ChatRunRow, ChatStore
from app.domains.security.domain import ROLE_REGISTRY, AuditRow
from app.infra.clock import now

LOGGER = logging.getLogger("domains.chat")

# 报告索引命中档线与候选入池上限（骨架实施值——常量集中可调）。
INDEX_HIGH_FLOOR = 0.5
INDEX_CANDIDATE_MAX = 4

_TYPE_TO_MATCHER = {
    "指标卡": "指标卡台账", "术语": "术语台账", "FAQ": "FAQ 索引",
    "工具": "工具清单", "工作流": "分析工作流", "报告": "报告索引",
}
_TYPE_TO_KIND = {
    "指标卡": "metric", "术语": "term", "FAQ": "faq",
    "工具": "tool", "工作流": "workflow", "报告": "report",
}


class AuditSink(Protocol):
    """B12 审计写口缝（装配根注入 SecurityService——chat 不反向构造）。

    受理审计 `chat.ask.received`（票面）＋拦截审计（00 §8.2「拦截也是审计事件」）。
    """

    async def audit(self, row: AuditRow, *, session: AsyncSession | None = None) -> None: ...


class ChatService:
    """chat 域服务（编排；合同语义在 domain.py，持久在 store.py）。

    域读缝经组合根注入（B9 同款——运行期只见 callable，不 import
    retrieval/semantics/faq/kb）：qa 配置/指标台账/术语台账/FAQ 索引/报告索引。
    """

    def __init__(
        self,
        db: Any,
        *,
        audit: AuditSink | None = None,
        qa_config_loader: d.QaConfigLoader,
        metrics_loader: d.MetricsLoader,
        terms_loader: d.TermsLoader,
        faq_matcher: d.FaqMatcher,
        index_searcher: d.IndexSearcher,
        graph_searcher: d.GraphSearcher | None = None,
    ) -> None:
        self._db = db
        self._audit = audit
        self._qa_config_loader = qa_config_loader
        self._metrics_loader = metrics_loader
        self._terms_loader = terms_loader
        self._faq_matcher = faq_matcher
        self._index_searcher = index_searcher
        self._graph_searcher = graph_searcher
        self._store = ChatStore(db)
        self._dispatcher = d.ChainDispatcher()
        self._suggestions = d.SuggestionPool()

    # ---------- 分派缝注册面（08b 三链填肉入口）／建议池观测 ----------

    @property
    def dispatcher(self) -> d.ChainDispatcher:
        return self._dispatcher

    @property
    def suggestions(self) -> d.SuggestionPool:
        return self._suggestions

    # ---------- POST /api/chat/asks（统一入口无旁路——F56①） ----------

    async def ask(
        self, question: str, *, session_id: str | None,
        page_context: dict[str, Any] | None, anchors: list[str], actor_who: str,
    ) -> AsyncIterator[d.SseEvent]:
        """统一问答主端点的域面：一句问话 → 一路可续推的 SSE 事件帧流。"""
        text = question.strip()
        session = await self._store.ensure_session(
            session_id, user_id=_actor_key(actor_who), title=text[:50]
        )
        run = await self._store.create_run(session.id)
        await self._store.append_message(session.id, role="user", text=text, run_id=run.id)
        await self._store.touch_session(session.id)
        await self._audit_received(actor_who, run.id, text)

        yield d.SseEvent(d.FRAME_SESSION, {"run_id": run.id, "thread_id": session.id})
        yield d.SseEvent(d.FRAME_STAGE, {"stage": 0})
        yield d.SseEvent(d.FRAME_STAGE, {"stage": 1})

        # —— ① 统一安检（三道逐条翻；任一 ✗ 拦截出终局——禁用词先于一切解析）——
        blocked_feature = d.scan_injection(text)
        blocked_lane = "注入扫描" if blocked_feature is not None else None
        banned = d.check_banned(text)
        if blocked_feature is None and banned is not None:
            blocked_feature = banned
            blocked_lane = "禁用词索引"
        for seq, name in enumerate(d.SEC_CHECKS, start=1):
            if blocked_lane is not None and name == blocked_lane:
                note = (
                    f"命中注入特征「{blocked_feature}」"
                    if blocked_lane == "注入扫描"
                    else f"命中禁用词「{blocked_feature}」（废弃口径——先于一切解析）"
                )
                yield d.SseEvent(d.FRAME_SEC_CHECK, {
                    "seq": seq, "name": name, "result": "blocked", "note": note,
                })
                break
            if name == "身份与数据域":
                # 身份闸在路由层已过（401 同闸——CurrentActor）；数据域随 D3 行级批。
                yield d.SseEvent(d.FRAME_SEC_CHECK, {
                    "seq": seq, "name": name, "result": "pass", "note": actor_who,
                })
                continue
            yield d.SseEvent(d.FRAME_SEC_CHECK, {
                "seq": seq, "name": name, "result": "pass",
                "note": "字面规则未命中",
            })
        if blocked_lane is not None:
            assert blocked_feature is not None
            await self._audit_blocked(actor_who, run.id, blocked_lane, blocked_feature)
            answer = {
                "kind": "alert", "alert_type": "warning",
                "text": (
                    d.injection_answer_text(blocked_feature)
                    if blocked_lane == "注入扫描"
                    else d.ban_answer_text(blocked_feature)
                ),
            }
            yield d.SseEvent(d.FRAME_ANSWER, answer)
            yield d.SseEvent(d.FRAME_DONE, {})
            await self._store.append_message(
                session.id, role="assistant", text=str(answer["text"]),
                run_id=run.id, answer=answer,
            )
            await self._store.touch_session(session.id)
            await self._finish_run(run, verdict=None)
            return

        # —— ② 知识装配（@ 前门直取＋六路匹配器全扫全收集）——
        qa = await self._qa_config_loader()
        try:
            assembly = await self._assemble(text, anchors)
        except d.ChatParamError as exc:
            # @ 锚定取不到＝落空拒答（A1 端点 4 注记）——锚定落空非匹配器落空，
            # 不进建议池（建议池收六路匹配器落空信号，F56②）。
            answer = {"kind": "alert", "alert_type": "warning", "text": str(exc)}
            yield d.SseEvent(d.FRAME_ANSWER, answer)
            yield d.SseEvent(d.FRAME_DONE, {})
            await self._store.append_message(
                session.id, role="assistant", text=str(answer["text"]),
                run_id=run.id, answer=answer,
            )
            await self._store.touch_session(session.id)
            await self._finish_run(run, verdict=None)
            return
        for lane in assembly.lanes:
            data: dict[str, Any] = {"matcher": lane.matcher, "status": lane.status}
            if lane.confidence is not None:
                data["confidence"] = lane.confidence
            if lane.note is not None:
                data["note"] = lane.note
            yield d.SseEvent(d.FRAME_MATCH, data)
        if assembly.anchor_line:
            yield d.SseEvent(d.FRAME_NOTICE, {
                "level": "info",
                "text": d.ANCHOR_LOCK_NOTICE_TEMPLATE.format(token=assembly.anchor_line),
            })
        yield d.SseEvent(d.FRAME_ASSEMBLY, {
            "anchor_line": assembly.anchor_line,
            "slots": assembly.slots,
            "terms": assembly.terms,
            "candidates": [_candidate_wire(c) for c in assembly.candidates],
            "chains": list(d.CHAIN17),
        })

        # —— ③ 意图裁决（骨架期确定性路由；D2 模型裁决随 08b 接线）——
        yield d.SseEvent(d.FRAME_STAGE, {"stage": 2})
        verdict = self._skeleton_verdict(text, assembly, qa)
        await self._record_verdict(run, verdict)
        yield d.SseEvent(d.FRAME_VERDICT, _wire_verdict(verdict))
        if verdict.get("need_clarify") is True:
            # 澄清帧 interrupt 挂起（连接不占着）——流收束不发 done；
            # 有界循环＝clarify_count CHECK 0–1（第二次 409），两跳到终态在 resume。
            clarify = verdict.get("_clarify")
            assert isinstance(clarify, d.ClarifyFrame)
            yield d.SseEvent(d.FRAME_CLARIFY, _clarify_wire(clarify))
            await self._suspend_clarify(run, verdict, question=text)
            return

        # —— ④ 执行链分发（17 链闭世界；未实现链回未开通话术）——
        outcome = await self._dispatch_chain(str(verdict["chain"]), run, text, actor_who, assembly)
        async for event in self._emit_outcome(outcome, run, session.id, verdict):
            yield event

    # ---------- POST /api/chat/runs/{run_id}/resume（interrupt 决策回流） ----------

    async def resume_preflight(
        self, run_id: str, *, kind: str, decision: str | None, reason: str | None,
    ) -> ChatRunRow:
        """resume 前置校验（流开前的同步段——404/409/400 走 HTTP 错误包，流未开；
        00 §3.1：SSE 内异常不走 HTTP 错误包，故状态机校验必须在开流前完成）。"""
        run = await self._store.get_run(run_id)
        if run is None:
            raise d.ChatRunNotFoundError(f"运行不存在或已过期：{run_id}")
        if kind == "approval":
            if decision == "reject" and not (reason and reason.strip()):
                raise d.ChatParamError("Action 链驳回必须写理由（N12「须写理由的驳回」）")
            raise d.ChatRunStateError(
                f"run 非 interrupt 挂起态：{run_id}（status={run.status}）"
                "——审批挂起骨架期未产生（extable/action 链随 08b/后续批）"
            )
        if run.status != "interrupt_clarify":
            raise d.ChatRunStateError(
                f"run 非 interrupt 挂起态：{run_id}（status={run.status}）"
                "——对已终态 resume/重入 clarify 一律 409（状态机约束）"
            )
        return run

    async def resume(
        self, run_id: str, *, kind: str, choice: str | None, decision: str | None,
        reason: str | None, actor_who: str,
    ) -> AsyncIterator[d.SseEvent]:
        """澄清续推（骨架期唯一 interrupt 形态；approval 挂起骨架期不产生）。

        - 带 choice → 并入原问句上下文（输入严格变多）→ 重过安检（不免检）→
          带参重判 → 续推；
        - 有界循环：clarify_count 已 1（CHECK 0–1）时不再弹帧——两跳终态走默认
          口径锁定（notice）后照常分派；
        - approval 形态：骨架期无审批挂起 run——非 interrupt_approval 态一律 409。
        """
        run = await self.resume_preflight(run_id, kind=kind, decision=decision, reason=reason)
        pending = run.pending_interrupt or {}
        frame = _frame_from_interrupt(pending)
        if frame is None:
            raise d.ChatRunStateError(f"run 挂起帧不可解析：{run_id}")
        chosen = d.caliber_choice_value(choice, frame)
        if chosen is None:
            raise d.ChatParamError(
                f"澄清选项无效：{choice!r}（可选：{'、'.join(c.value for c in frame.choices)}）"
            )
        question, run, metric = await self._reload_clarify_context(run, pending, chosen)
        caliber_name = (
            d.caliber_name_from_value(chosen, metric) if metric is not None
            else chosen.removeprefix("默认口径 ")
        )
        await self._audit_received(
            actor_who, run.id, f"澄清回流：{question}（口径锁定＝{caliber_name}）"
        )

        yield d.SseEvent(d.FRAME_SESSION, {
            "run_id": run.id, "thread_id": run.session_id, "resume": True,
        })
        yield d.SseEvent(d.FRAME_STAGE, {"stage": 0})
        yield d.SseEvent(d.FRAME_STAGE, {"stage": 1})
        # 澄清续跑不免检（A1 端点 5：新输入重过 D1 统一安检）——三道照翻。
        for seq, name in enumerate(d.SEC_CHECKS, start=1):
            yield d.SseEvent(d.FRAME_SEC_CHECK, {
                "seq": seq, "name": name, "result": "pass", "note": "澄清带参复检（不免检）",
            })
        qa = await self._qa_config_loader()
        assembly = await self._assemble(question, [])
        for lane in assembly.lanes:
            data: dict[str, Any] = {"matcher": lane.matcher, "status": lane.status}
            if lane.confidence is not None:
                data["confidence"] = lane.confidence
            if lane.note is not None:
                data["note"] = lane.note
            yield d.SseEvent(d.FRAME_MATCH, data)
        yield d.SseEvent(d.FRAME_ASSEMBLY, {
            "anchor_line": assembly.anchor_line,
            "slots": assembly.slots,
            "terms": assembly.terms,
            "candidates": [_candidate_wire(c) for c in assembly.candidates],
            "chains": list(d.CHAIN17),
        })
        yield d.SseEvent(d.FRAME_STAGE, {"stage": 2})
        verdict = self._skeleton_verdict(question, assembly, qa)
        if verdict.get("need_clarify") is True:
            # 两跳到终态（默认口径或拒答）——不再弹澄清帧（有界循环：最多弹一次）。
            verdict = {
                "chain": "检索问答链", "slots": assembly.slots,
                "confidence": d.CLARIFY_CONFIDENCE, "need_clarify": False,
            }
            yield d.SseEvent(d.FRAME_NOTICE, {
                "level": "info",
                "text": f"已按默认口径「{caliber_name}」锁定并标注——澄清帧有界循环"
                        "（最多弹一次），两跳到终态。",
            })
        await self._record_verdict(run, verdict)
        yield d.SseEvent(d.FRAME_VERDICT, _wire_verdict(verdict))
        outcome = await self._dispatch_chain(
            str(verdict["chain"]), run, question, actor_who, assembly,
            clarified_caliber=caliber_name,
        )
        async for event in self._emit_outcome(outcome, run, run.session_id, verdict):
            yield event

    # ---------- 会话料源读口（B3 扫库消费——faq session_loader 注入位） ----------

    async def recent_qa_pairs(self) -> list[dict[str, str]]:
        """A1 历史会话问答对（[{question, answer}]——98 §3.3 faq 卡 session_loader
        料源缝；done 运行的问答配对，最近优先）。"""
        return await self._store.recent_qa_pairs(limit=d.RECENT_QA_LIMIT)

    # ---------- ② 知识装配（六路匹配器——并行查表共池，词级全扫全收集） ----------

    async def _assemble(self, question: str, anchors: list[str]) -> d.AssemblyResult:
        """装配层：@ 前门直取＋六路匹配器全扫全收集（装配候选共池）。

        - 被 @ 的一路不过匹配器、其他五路照跑（F56 @ 倾向协议——候选在场是
          「倾向≠直通」的物质基础）；被让位路不记落空（候选已经前门在场）；
        - 落空（含注册表未建的两路）逐路进建议池；
        - 装配候选不设上限（全扫全收集）；澄清帧候选上限 4 支在 clarify 构造截断。
        """
        needle = d.normalize_query(question)
        anchor_line: str | None = None
        candidates: list[d.Candidate] = []
        terms: list[str] = []
        slots_parts: list[str] = []
        anchored_matchers: set[str] = set()

        for token in anchors:
            parsed = d.parse_anchor_token(token)
            if parsed is None:
                raise d.ChatParamError(f"@ token 形状非法：{token}（「类型·名称」结晶体）")
            asset_type, name = parsed
            if not await self._resolve_anchor(asset_type, name):
                raise d.ChatParamError(d.ANCHOR_MISS_TEMPLATE.format(token=token))
            anchored_matchers.add(_TYPE_TO_MATCHER[asset_type])
            anchor_line = (anchor_line + "；" if anchor_line else "") + token
            candidates.append(d.Candidate(
                matcher=_TYPE_TO_MATCHER[asset_type], name=name, confidence="high",
                kind=_TYPE_TO_KIND[asset_type], note="@ 前门直取（倾向≠直通）",
            ))
            if asset_type == "术语":
                terms.append(name)

        metrics = list(await self._metrics_loader())
        term_rows = list(await self._terms_loader())
        # 被 @ 的一路不过匹配器、其他五路照跑（F56 @ 倾向协议——候选经前门在场）。
        faq_hit = (
            None if "FAQ 索引" in anchored_matchers else await self._faq_matcher(question)
        )
        index_hits = (
            [] if "报告索引" in anchored_matchers else list(await self._index_searcher(question))
        )

        lane_notes: dict[str, list[str]] = {}
        lane_conf: dict[str, str] = {}
        lane_anchored: set[str] = set()

        def mark(matcher: str, *, hit: bool, confidence: str | None, note: str) -> None:
            if hit:
                lane_notes.setdefault(matcher, []).append(note)
                if confidence is not None:
                    lane_conf[matcher] = confidence
            else:
                lane_notes.setdefault(matcher, []).append(note)

        def mark_anchored(matcher: str) -> None:
            lane_anchored.add(matcher)
            mark(matcher, hit=False, confidence=None, note="@ 已前门直取——匹配器让位")

        # 路 1：FAQ 索引（faq.match_index 运行时读口——只认服务中条目）
        if "FAQ 索引" in anchored_matchers:
            mark_anchored("FAQ 索引")
        elif faq_hit is not None:
            mark("FAQ 索引", hit=True, confidence="high", note="归一化精确命中")
            candidates.append(d.Candidate("FAQ 索引", faq_hit.question, "high", "faq",
                                          note="命中即秒回候选（FAQ直出链）"))
            slots_parts.append(f"FAQ＝{faq_hit.question}")
        else:
            mark("FAQ 索引", hit=False, confidence=None, note="归一化精确未命中")
            self._suggestions.record_miss("FAQ 索引", question)

        # 路 2：指标卡台账（台账精确——槽位名/台账名包含即命中；词级全扫不早停）
        metric_hits: list[d.MetricFace] = []
        if "指标卡台账" in anchored_matchers:
            mark_anchored("指标卡台账")
        else:
            for metric in metrics:
                names = {d.normalize_query(metric.slot_name), d.normalize_query(metric.name)}
                if any(name and name in needle for name in names):
                    metric_hits.append(metric)
            if metric_hits:
                mark("指标卡台账", hit=True, confidence="high",
                     note="命中 " + "、".join(f"「{m.slot_name}」" for m in metric_hits))
                for metric in metric_hits:
                    candidates.append(d.Candidate("指标卡台账", metric.slot_name, "high", "metric"))
                    slots_parts.append(f"指标＝{metric.slot_name}")
            else:
                mark("指标卡台账", hit=False, confidence=None, note="台账精确未命中")
                self._suggestions.record_miss("指标卡台账", question)

        # 路 3：术语台账（术语精确——同构两档；类型展示串「别名 → X」族即别名载体）
        if "术语台账" in anchored_matchers:
            mark_anchored("术语台账")
        else:
            term_hits = [
                t for t in term_rows
                if (d.normalize_query(t.term) and d.normalize_query(t.term) in needle)
                or (d.normalize_query(t.type) and d.normalize_query(t.type) in needle)
            ]
            if term_hits:
                mark("术语台账", hit=True, confidence="high",
                     note="命中 " + "、".join(f"「{t.term}」" for t in term_hits))
                for term in term_hits:
                    candidates.append(d.Candidate("术语台账", term.term, "high", "term"))
                    terms.append(term.term)
                    slots_parts.append(f"术语＝{term.term}")
            else:
                mark("术语台账", hit=False, confidence=None, note="台账未命中")
                self._suggestions.record_miss("术语台账", question)

        # 路 4/5：工具清单・分析工作流（注册表/运行时未建——落空进建议池）
        if "工具清单" in anchored_matchers:
            mark_anchored("工具清单")
        else:
            mark("工具清单", hit=False, confidence=None, note="工具注册表未建——落空")
            self._suggestions.record_miss("工具清单", question)
        if "分析工作流" in anchored_matchers:
            mark_anchored("分析工作流")
        else:
            mark("分析工作流", hit=False, confidence=None, note="工作流运行时未建——落空")
            self._suggestions.record_miss("分析工作流", question)

        # 路 6：报告索引（向量＋BM25〔trigram 缝——P1-04 裁决〕同池两腿）
        if "报告索引" in anchored_matchers:
            mark_anchored("报告索引")
        elif index_hits:
            best = max(index_hits, key=lambda h: h.score)
            mark("报告索引", hit=True,
                 confidence="high" if best.score >= INDEX_HIGH_FLOOR else "low",
                 note=f"命中《{best.report}》{best.section or ''}"
                      f"（{best.leg} 腿 · score={best.score:.2f}）")
            for hit in index_hits[:INDEX_CANDIDATE_MAX]:
                candidates.append(d.Candidate(
                    "报告索引",
                    f"《{hit.report}》{hit.section or ''}".strip() or hit.fragment_id,
                    "high" if hit.score >= INDEX_HIGH_FLOOR else "low", "report",
                    note=f"{hit.leg} 腿 · score={hit.score:.2f}",
                ))
            slots_parts.append(f"报告＝《{best.report}》")
        else:
            mark("报告索引", hit=False, confidence=None, note="向量＋关键词两腿未命中")
            self._suggestions.record_miss("报告索引", question)

        # 图谱缝（票面：08b 前落空——非 F56 六路匹配器，不发 match 帧；
        # 候选共池、落空进建议池；08b 图谱问答链接线时组合根注入真图检索）
        graph_hits = list(await self._search_graph(question))
        if graph_hits:
            for gh in graph_hits[:INDEX_CANDIDATE_MAX]:
                candidates.append(d.Candidate(
                    "图谱", f"{gh.entity}（{gh.relation}）", "high", "graph",
                    note=gh.evidence or "图谱缝命中——08b 图谱问答链消费",
                ))
            slots_parts.append(f"图谱＝{graph_hits[0].entity}")
        else:
            self._suggestions.record_miss("图谱", question)

        lanes = [
            d.LaneResult(
                matcher=matcher,
                status=(
                    "hit"
                    if matcher in lane_anchored
                    or any(n.startswith("命中") for n in lane_notes.get(matcher, []))
                    else "miss"
                ),
                confidence=lane_conf.get(matcher)
                or ("high" if matcher in lane_anchored else None),
                note="；".join(lane_notes.get(matcher, [])) or None,
            )
            for matcher in d.MATCHERS
        ]
        ambiguous_metric = next(
            (
                m for m in metric_hits
                if m.ambiguous and len(m.calibers) >= 2 and not _mentions_caliber(question, m)
            ),
            None,
        )
        return d.AssemblyResult(
            anchor_line=anchor_line,
            slots=" · ".join(slots_parts) if slots_parts else "∅",
            terms=terms,
            candidates=candidates,
            lanes=lanes,
            ambiguous_metric=ambiguous_metric,
        )

    async def _search_graph(self, question: str) -> list[d.GraphHitFace]:
        """图谱缝检索（08b 前落空——组合根未注入时恒空；票面「图谱〔08b 前落空〕」）。"""
        if self._graph_searcher is None:
            return []
        return list(await self._graph_searcher(question))

    async def _resolve_anchor(self, asset_type: str, name: str) -> bool:
        """@ 资产直取（服务端按主键/名称直取——取不到＝落空拒答）。

        骨架期注册表：指标卡/术语→semantics 台账；FAQ→match_index；工具/工作流/
        报告注册表未建（A1 端点 6 assets 面随其票落）——直取必落空。
        """
        probe = d.normalize_query(name)
        if not probe:
            return False
        if asset_type == "指标卡":
            return any(
                probe in d.normalize_query(m.slot_name)
                or probe in d.normalize_query(m.name)
                for m in await self._metrics_loader()
            )
        if asset_type == "术语":
            return any(probe == d.normalize_query(t.term) for t in await self._terms_loader())
        if asset_type == "FAQ":
            return await self._faq_matcher(name) is not None
        return False

    # ---------- ③ 意图裁决（骨架期确定性路由——D2 模型裁决随 08b 接线） ----------

    def _skeleton_verdict(
        self, question: str, assembly: d.AssemblyResult, qa: d.QaBehaviorFace
    ) -> dict[str, Any]:
        """骨架裁决 JSON（F56③ 形状 {chain, slots, confidence, need_clarify[, clarify_frame]}）。

        - FAQ 精确命中＋faq_direct_hit 开 → FAQ直出链（秒回闸——D2 运行时消费归 A1）；
        - 口径两译未消歧（ambiguous 台账命中且问句未点口径支名）→ need_clarify、
          chain null（裁决未定）、confidence 低——clarify_strategy 消费（非
          ask_missing 档骨架期不开闸；现值唯一档 ask_missing）；
        - 其余 → 检索问答链（A1 主链——08b 检索瀑布链体）。

        `_clarify`/`_clarify_metric` 为域内随行键——wire 前经 _wire_verdict 剥除。
        """
        faq_candidate = next((c for c in assembly.candidates if c.kind == "faq"), None)
        if faq_candidate is not None and qa.faq_direct_hit:
            return {
                "chain": "FAQ直出链", "slots": assembly.slots,
                "confidence": d.FAQ_ROUTE_CONFIDENCE, "need_clarify": False,
            }
        ambiguous = assembly.ambiguous_metric
        if (
            ambiguous is not None
            and qa.clarify_strategy == "ask_missing"
            and not _mentions_caliber(question, ambiguous)
        ):
            frame = d.build_caliber_clarify(ambiguous, frame_id=f"clarify-{now():%H%M%S%f}")
            if frame is not None:
                return {
                    "chain": None, "slots": assembly.slots,
                    "confidence": d.CLARIFY_CONFIDENCE, "need_clarify": True,
                    "clarify_frame": frame.question,
                    "_clarify": frame,
                    "_clarify_metric": {"metric_id": ambiguous.metric_id,
                                        "slot_name": ambiguous.slot_name},
                }
        return {
            "chain": "检索问答链", "slots": assembly.slots,
            "confidence": d.SKELETON_ROUTE_CONFIDENCE, "need_clarify": False,
        }

    # ---------- ④ 执行链分发与收场 ----------

    async def _dispatch_chain(
        self, chain: str, run: ChatRunRow, question: str, actor_who: str,
        assembly: d.AssemblyResult, *, clarified_caliber: str | None = None,
    ) -> d.ChainOutcome:
        return await self._dispatcher.dispatch(
            chain,
            d.ChainContext(
                run_id=run.id, question=question, actor_who=actor_who, assembly=assembly,
                clarified_caliber=clarified_caliber,
            ),
        )

    async def _emit_outcome(
        self, outcome: d.ChainOutcome, run: ChatRunRow, session_id: str,
        verdict: dict[str, Any],
    ) -> AsyncIterator[d.SseEvent]:
        yield d.SseEvent(d.FRAME_STAGE, {"stage": 3})
        for line in outcome.notices:
            yield d.SseEvent(d.FRAME_NOTICE, {"level": "info", "text": line})
        yield d.SseEvent(d.FRAME_ANSWER, outcome.answer)
        yield d.SseEvent(d.FRAME_DONE, {})
        await self._store.append_message(
            session_id, role="assistant", text=_answer_text(outcome.answer),
            run_id=run.id, answer=outcome.answer,
        )
        await self._store.touch_session(session_id)
        await self._finish_run(run, verdict=verdict)

    # ---------- 运行状态与挂起帧（chat_run 状态机——澄清有界循环存储强制） ----------

    async def _suspend_clarify(
        self, run: ChatRunRow, verdict: dict[str, Any], *, question: str,
    ) -> None:
        """澄清挂起（interrupt_clarify——pending_interrupt 落帧；clarify_count +1）。

        载荷携原问句与口径面（resume 带参重判的上下文——输入严格变多）；
        clarify_count CHECK 0–1 是「最多弹一次」的存储强制。
        """
        clarify = verdict.get("_clarify")
        if not isinstance(clarify, d.ClarifyFrame) or run.clarify_count >= d.CLARIFY_MAX_POPUPS:
            raise d.ChatRunStateError("澄清帧有界循环已尽——第二次 clarify 拒绝（409）")
        run.status = "interrupt_clarify"
        run.clarify_count = run.clarify_count + 1
        run.pending_interrupt = {
            "kind": "clarify",
            "frame": _clarify_wire(clarify),
            "question": question,
            "metric": dict(verdict.get("_clarify_metric") or {"metric_id": None}),
        }
        await self._store.save_run(run)

    async def _reload_clarify_context(
        self, run: ChatRunRow, pending: dict[str, Any], chosen: str
    ) -> tuple[str, ChatRunRow, d.MetricFace | None]:
        """澄清回流上下文恢复：原问句＋已选口径并入（输入严格变多，非重复裁决）。"""
        base_question = str(pending.get("question") or "")
        metric_payload = pending.get("metric") or {}
        metric: d.MetricFace | None = None
        metric_id = metric_payload.get("metric_id")
        if metric_id is not None:
            for candidate in await self._metrics_loader():
                if candidate.metric_id == int(metric_id):
                    metric = candidate
                    break
        caliber_name = (
            d.caliber_name_from_value(chosen, metric) if metric is not None
            else chosen.removeprefix("默认口径 ")
        )
        merged = base_question
        if caliber_name and d.normalize_query(caliber_name) not in d.normalize_query(base_question):
            merged = f"{base_question}（口径＝{caliber_name}）"
        run.status = "running"
        run.pending_interrupt = None
        await self._store.save_run(run)
        return merged, run, metric

    async def _record_verdict(self, run: ChatRunRow, verdict: dict[str, Any]) -> None:
        run.verdict = _wire_verdict(verdict)
        await self._store.save_run(run)

    async def _finish_run(self, run: ChatRunRow, *, verdict: dict[str, Any] | None) -> None:
        run.status = "done"
        if verdict is not None:
            run.verdict = _wire_verdict(verdict)
        run.finished_at = now()
        await self._store.save_run(run)

    # ---------- B12 审计（受理/拦截——00 §8.2 拦截也是审计事件） ----------

    async def _audit_received(self, who: str, run_id: str, question: str) -> None:
        if self._audit is None:
            return
        await self._audit.audit(AuditRow(
            who=who,
            action="chat.ask.received",
            content=f"受理提问（run {run_id}）：{question[:80]}",
        ))

    async def _audit_blocked(self, who: str, run_id: str, lane: str, feature: str) -> None:
        if self._audit is None:
            return
        await self._audit.audit(AuditRow(
            who=who,
            action="chat.ask.blocked",
            content=f"统一安检拦截（run {run_id}）——{lane} 命中「{feature}」，链路终止",
        ))


def _actor_key(actor_who: str) -> str:
    """who 展示名 → 会话归属技术列（五角色 label→键；未知串原样——演示量级）。"""
    for key, profile in ROLE_REGISTRY.items():
        if profile.display == actor_who:
            return key
    return actor_who


def _wire_verdict(verdict: dict[str, Any]) -> dict[str, Any]:
    """裁决 JSON 的 wire 形（剥域内随行键——A1 裁决帧字段照抄）。"""
    return {k: v for k, v in verdict.items() if not k.startswith("_")}


def _clarify_wire(frame: d.ClarifyFrame) -> dict[str, Any]:
    return {
        "frame_id": frame.frame_id,
        "question": frame.question,
        "choices": [
            {"value": c.value, "label": c.label, **({"primary": True} if c.primary else {})}
            for c in frame.choices
        ],
    }


def _candidate_wire(candidate: d.Candidate) -> dict[str, Any]:
    data: dict[str, Any] = {
        "matcher": candidate.matcher, "name": candidate.name,
        "confidence": candidate.confidence, "kind": candidate.kind,
    }
    if candidate.note is not None:
        data["note"] = candidate.note
    return data


def _mentions_caliber(question: str, metric: d.MetricFace) -> bool:
    """问句是否已点口径支名（点了＝已消歧，不再弹澄清）。"""
    folded = d.normalize_query(question)
    return any(
        d.normalize_query(str(c.get("name", ""))) in folded
        for c in metric.calibers
        if c.get("name")
    )


def _answer_text(answer: dict[str, Any]) -> str:
    kind = str(answer.get("kind", ""))
    if kind in ("text", "alert"):
        return str(answer.get("text", ""))
    return str(answer.get("note") or answer.get("title") or "")


def _frame_from_interrupt(pending: dict[str, Any]) -> d.ClarifyFrame | None:
    if pending.get("kind") != "clarify":
        return None
    frame = pending.get("frame") or {}
    choices = [
        d.ClarifyChoice(value=str(c.get("value", "")), label=str(c.get("label", "")),
                        primary=bool(c.get("primary", False)))
        for c in frame.get("choices", [])
    ]
    return d.ClarifyFrame(
        frame_id=str(frame.get("frame_id", "")),
        question=str(frame.get("question", "")),
        choices=choices,
    )
