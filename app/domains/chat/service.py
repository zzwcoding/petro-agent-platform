"""domains.chat.service —— A1 问一问编排引擎：四层流水线全在服务端（F56）。

公开面照 98 §3.1 卡（P1-08a 骨架拍＋P1-08b 三链拍）：ask（统一入口无旁路——
POST /api/chat/asks）＋resume（interrupt 决策回流——POST /api/chat/runs/
{run_id}/resume）＋运行时读 recent_qa_pairs（B3 扫库料源——session_loader
注入位，P1-06 疑点 6 收口）。

四层流水线（F56①→④）：
  ①统一安检：注入扫描/禁用词索引/身份与数据域——字面规则任一 ✗ 拦截出终局
    （sec_check blocked → answer kind=alert 拦截话术 → done；拦截也是审计事件）。
  ②知识装配：@ 前门直取（取不到＝落空拒答）＋六路匹配器并行查表共池——词级
    全扫全收集（不存在「命中就停」漏词）；被 @ 的一路不过匹配器、其他五路照跑；
    落空进建议池（F60 晋升闸：孤例不进池）。
  ③意图裁决：D2 当前生效配置驱动——FAQ 直出闸（faq_direct_hit）/口径两译澄清
    （clarify_strategy=ask_missing）/图谱关系问句路由/置信度真实计算（检索得分
    ＋装配信号，D2 confidence_thresholds 档位：低 <low 必弹澄清帧——多候选在
    场弹候选澄清帧，无候选直派检索链走兜底）。
  ④执行链分发：17 链闭世界分派；N5b 接线核验（P1F-01）——裁决选中未注册链
    （17 链清单已接线四链：状态机六站/检索问答/FAQ直出/图谱问答——分派器注册面）
    即覆写回退「检索问答链」，原裁决随 N5b 帧 note 留痕；链体见 chains.py；
    「该能力暂未开通」话术不再是主路径行为，仅作已接线链内部注桩缺陷安全网
    （同 _run_chain 的 answer=None 兜底分支族）。

审批 interrupt（M-06 extable——A1 端点 5 合同形状）：问数链 N7.4c 越集比对命中
  → approval 哨兵拦截 → interrupt_approval 挂起（pending_approval_id 落列）；
  resume decision=approve/reject → 链恢复整节点重跑（F7 节点幂等）——N7.4c 以
  ctx.extable_decision 判别批准续跑/驳回终局（extable 驳回不强制理由——A1：
  Action 链才须写理由）。

澄清帧有界循环（F56）：最多弹一次、两跳到终态（默认口径/锁定候选/拒答）——
挂起帧写入 chat_run.pending_interrupt（clarify_count CHECK 0–1 存储强制）；
回流带参重过安检（不免检）→ 带参重判 → 续推；第二次 clarify 一律 409。
挂起帧 subtype＝caliber（口径两译——默认口径项 primary）｜candidates（低置信
多候选——无默认项，不选＝拒答终态，宁可不答不瞎猜）｜rewrite（P1F-06 链内
低分带改写澄清——无默认项，选是＝优化句上下文续推、选否/不选＝诚实兜底）｜
missing（M-06 问数链缺参反问——askback 时间窗三选一无默认项，补参并入问句
续推、不选＝拒答终态：缺的是用户事实）。
clarify 帧 wire＝A1 帧 14 冻结形状＋additive `subtype` 键（透传给前端分支渲染；
挂起/重放/链内哨兵三路同形，剥除面＝_wire_verdict 的 _ 前缀域内随行键）。

LLM 出口（B6）：链内生成/打分与意图裁决只走注入 completer（生产＝
GatewayService.complete，别名 petro-main；裁决 caller=chat.intent.verdict，
失败/超时/解析坏兜底确定性信号路由——不许问挂）——安检/装配零 LLM 依赖。
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from functools import partial
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.chat import chains as chains_mod
from app.domains.chat import domain as d
from app.domains.chat.store import ChatRunRow, ChatStore
from app.domains.security.domain import ROLE_REGISTRY, AuditRow
from app.infra.clock import now

LOGGER = logging.getLogger("domains.chat")

# 报告索引命中档线与候选入池上限（装配层实施值——常量集中可调）。
INDEX_HIGH_FLOOR = 0.5
INDEX_CANDIDATE_MAX = 4

# LLM 意图裁决提示词（F56③ 结构化输出——只回 JSON；闭世界清单由 user 消息携带）。
# 约束段沿革（P1F-01 源头降噪 → W-AUX 判型恢复）：评测显示 LLM 把「台账命中」
# 误读成派链指令，旧过渡约束「自然语言问法一律选检索问答链」是当时六站链空壳
# 期的止损；现状态机六站链已接线非空壳（M-06 落地），经 Owner 2026-10-05 批准
# 撤除该过渡约束，改分型路由——数据型（命中指标声明＋取值诉求）→ 状态机六站链；
# 报告/叙述型 → 检索问答链；复合题 → 检索兜底（拆步随工具执行链阶段 3 接线）；
# 纯定义问法（什么是 X）仍检索链（P1F-02「命中只是材料信号」精化为「命中＋取值
# 诉求合判」）。@ 显式锚定兜底与 N5b 未注册链覆写回退（P1F-01）全部不变。
INTENT_VERDICT_SYSTEM_PROMPT = (
    "你是油田数据问答平台的意图裁决器。根据问句与装配信号，从给定的 17 链清单中"
    "选出唯一应执行的链名，并给出 0 到 1 的置信度数值。"
    '只输出一个 JSON 对象：{"chain": "<链名>", "confidence": <0-1 数值>}，'
    "不要输出任何其他文字、解释或代码块标记。"
    "分型路由：问句命中指标卡台账且意在取值/排名/对比（多少、最高、最低、排名、"
    "对比等取值诉求）→ 选「状态机六站链」；措施、原因、定义、机理等报告型叙述型"
    "问法 → 选「检索问答链」；一词多事件或跨族的复合题 → 选「检索问答链」兜底；"
    "纯定义问法（什么是 X）即使命中台账也选「检索问答链」——台账命中只是装配"
    "材料信号，须与取值诉求合判，不构成选链唯一依据。"
    "除用户用 @ 显式锚定外按上述分型路由；「指标卡直出链」「口径消歧链」等链"
    "仅受理 @ 显式锚定提问。"
)


def _parse_intent_json(text: str) -> tuple[str | None, float | None]:
    """LLM 裁决输出解析（宽容：剥代码围栏/前后杂文；链名闭世界校验在调用方）。"""
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:]
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        return None, None
    try:
        payload = json.loads(raw[start : end + 1])
    except ValueError:
        return None, None
    if not isinstance(payload, dict):
        return None, None
    chain = payload.get("chain")
    value = payload.get("confidence")
    if not isinstance(chain, str) or not isinstance(value, (int, float)):
        return None, None
    if isinstance(value, bool):  # 布尔冒充数值守卫（retrieval 域同款纪律）
        return None, None
    return chain, float(value)

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
    """chat 域服务（编排；合同语义在 domain.py，三链链体在 chains.py，持久在 store.py）。

    域读缝经组合根注入（B9 同款——运行期只见 callable，不 import
    retrieval/semantics/faq/kb/gateway）：D2 生效配置/指标台账/术语台账/FAQ 索
    引（精确＋扩检）/报告索引（装配合并路＋链内双路）/图谱缝/片段锚校验/LLM 出口。
    """

    def __init__(
        self,
        db: Any,
        *,
        audit: AuditSink | None = None,
        config_loader: d.ConfigLoader,
        metrics_loader: d.MetricsLoader,
        terms_loader: d.TermsLoader,
        faq_matcher: d.FaqMatcher,
        faq_searcher: d.FaqSearcher,
        index_searcher: d.IndexSearcher,
        index_searcher_dual: d.IndexSearcherDual,
        graph_searcher: d.GraphSearcher | None = None,
        anchor_loader: d.FragmentAnchorLoader | None = None,
        completer: d.Completer | None = None,
        faq_lister: d.FaqLister | None = None,
        workflow_lister: d.WorkflowLister | None = None,
        report_lister: d.ReportLister | None = None,
        query_executor: d.QueryExecutor | None = None,
        waterline_loader: d.WaterlineLoader | None = None,
    ) -> None:
        self._db = db
        self._audit = audit
        self._config_loader = config_loader
        self._metrics_loader = metrics_loader
        self._terms_loader = terms_loader
        self._faq_matcher = faq_matcher
        self._faq_searcher = faq_searcher
        self._index_searcher = index_searcher
        self._index_searcher_dual = index_searcher_dual
        self._graph_searcher = graph_searcher
        self._anchor_loader = anchor_loader
        # A1 端点 6 assets 读缝（P1-11——缺省空投影：单测装配不必注入全缝隙）。
        self._faq_lister = faq_lister
        self._workflow_lister = workflow_lister or _empty_pairs
        self._report_lister = report_lister or _empty_strs
        self._store = ChatStore(db)
        self._dispatcher = d.ChainDispatcher()
        self._suggestions = d.SuggestionPool()
        self._deps = chains_mod.ChainDeps(
            config_loader=config_loader,
            metrics_loader=metrics_loader,
            terms_loader=terms_loader,
            faq_matcher=faq_matcher,
            faq_searcher=faq_searcher,
            index_searcher_dual=index_searcher_dual,
            graph_searcher=self._search_graph,
            anchor_loader=self._load_anchor,
            completer=completer,
            query_executor=query_executor,
            waterline_loader=waterline_loader,
        )
        # 四链填肉（P1-08b 三链＋M-06 问数链——分派缝注册面；链体只见 ChainDeps 注入缝）。
        self._dispatcher.register("状态机六站链", partial(chains_mod.query_chain, self._deps))
        self._dispatcher.register("检索问答链", partial(chains_mod.retrieval_chain, self._deps))
        self._dispatcher.register("FAQ直出链", partial(chains_mod.faq_direct_chain, self._deps))
        self._dispatcher.register("图谱问答链", partial(chains_mod.graph_chain, self._deps))

    # ---------- 分派缝观测面／建议池观测 ----------

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
        # 思考树（P1-08c）：N1 统一安检节点点亮——node 帧族沿实时路径推进。
        yield d.node_frame("N1", state=d.NODE_PROCESS, tag="代码 · 字面规则",
                           note="统一安检——三道逐条翻（注入扫描/禁用词索引/身份与数据域）")
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
            yield d.node_frame(
                "N1", state=d.NODE_FINISH,
                note=f"{blocked_lane}命中「{blocked_feature}」——拦截，链路终止",
            )
            tree_node = "N2a" if blocked_lane == "注入扫描" else "N2b"
            yield d.node_frame(
                tree_node, state=d.NODE_FINISH, tag="拦截终局 · 留痕入审计",
                note=(
                    f"命中注入特征「{blocked_feature}」——拦截终局（不进模型、不出数），拦截事件已留痕审计"
                    if tree_node == "N2a"
                    else f"命中禁用词「{blocked_feature}」——废弃口径纠正口，现行叫法随答案卡"
                ),
            )
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

        yield d.node_frame("N1", state=d.NODE_FINISH, note="三道全过——放行")

        # —— ② 知识装配（@ 前门直取＋六路匹配器全扫全收集）——
        yield d.node_frame("N3", state=d.NODE_PROCESS, tag="代码 · 毫秒级",
                           note="轻装配——@ 前门直取＋六路匹配器全扫全收集")
        try:
            assembly = await self._assemble(text, anchors)
        except d.ChatParamError as exc:
            # @ 锚定取不到＝落空拒答（A1 端点 4 注记）——锚定落空非匹配器落空，
            # 不进建议池（建议池收六路匹配器落空信号，F56②）。
            yield d.node_frame("N3", state=d.NODE_FINISH,
                               note=f"@ 锚定落空——装配终止，拒答收场（{exc}）")
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
        lane_hits = sum(1 for lane in assembly.lanes if lane.status == "hit")
        yield d.node_frame(
            "N3", state=d.NODE_FINISH,
            note=f"六路候选：命中 {lane_hits} 路——共池 {len(assembly.candidates)} 支"
                 "（全扫全收集，落空进建议池）",
        )
        yield d.node_frame("N4", state=d.NODE_PROCESS, tag="给裁决的呈堂材料",
                           note="装配块——锚点/槽位/候选/17 链清单组卷")
        yield d.SseEvent(d.FRAME_ASSEMBLY, {
            "anchor_line": assembly.anchor_line,
            "slots": assembly.slots,
            "terms": assembly.terms,
            "candidates": [_candidate_wire(c) for c in assembly.candidates],
            "chains": list(d.CHAIN17),
        })
        yield d.node_frame("N4", state=d.NODE_FINISH,
                           note=f"装配块组卷完成——slots＝{assembly.slots}")

        # —— ③ 意图裁决（P1-11：petro-main 分类——失败兜底确定性信号路由）——
        yield d.SseEvent(d.FRAME_STAGE, {"stage": 2})
        yield d.node_frame(
            "N5", state=d.NODE_PROCESS, tag="意图裁决 · LLM＋兜底",
            note=f"意图裁决——petro-main 分类（caller={d.CALLER_INTENT_VERDICT}，"
                 f"超时 {d.INTENT_VERDICT_TIMEOUT_SECONDS:.0f}s）；"
                 "失败/超时/解析坏→确定性信号路由兜底（不许问挂）",
        )
        cfg = await self._config_loader()
        verdict = await self._decide(text, assembly, cfg)
        await self._record_verdict(run, verdict)
        yield d.SseEvent(d.FRAME_VERDICT, _wire_verdict(verdict))
        if verdict.get("need_clarify") is True:
            # 澄清帧 interrupt 挂起（连接不占着）——流收束不发 done；
            # 有界循环＝clarify_count CHECK 0–1（第二次 409），两跳到终态在 resume。
            clarify = verdict.get("_clarify")
            assert isinstance(clarify, d.ClarifyFrame)
            subtype = str(verdict.get("_clarify_subtype") or "caliber")
            yield d.node_frame("N5", state=d.NODE_FINISH,
                               note="低置信/口径两译——澄清挂起（interrupt，连接不占着）")
            yield d.node_frame(
                "N5a", state=d.NODE_FINISH, tag="最多弹一次 · 两跳到终态",
                note=(
                    "口径两译澄清——默认口径项 primary 恒带（按修饰词最少的基础口径出数并标注）"
                    if subtype == "caliber"
                    else "多候选聚焦澄清——无默认项（缺的是用户意图，不代选）"
                ),
            )
            yield d.SseEvent(d.FRAME_CLARIFY, _clarify_wire(clarify, subtype))
            await self._suspend_clarify(run, verdict, question=text, anchors=anchors)
            return
        yield d.node_frame(
            "N5", state=d.NODE_FINISH,
            note=f"裁决输出（来源＝{verdict.get('source')}）——chain＝{verdict.get('chain')}"
                 f" · confidence＝{verdict.get('confidence')}",
        )
        yield d.node_frame("N5b", state=d.NODE_PROCESS)
        n5b_note, rerouted_from = self._verify_chain_wiring(verdict)
        if rerouted_from is not None:
            await self._audit_rerouted(actor_who, run.id, rerouted_from)
        yield d.node_frame("N5b", state=d.NODE_FINISH, note=n5b_note)
        yield d.node_frame("N6", state=d.NODE_PROCESS, tag="查映射表派链")
        yield d.node_frame(
            "N6", state=d.NODE_FINISH,
            note=f"已分派至「{verdict.get('chain')}」——后续步骤由链体执行",
        )

        # —— ④ 执行链分发（17 链闭世界；未接线链已在 N5b 回退检索问答链——P1F-01）——
        async for event in self._run_chain(
            str(verdict["chain"]), run, text, actor_who, assembly, verdict=verdict,
            anchors=anchors,
        ):
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
            if decision not in ("approve", "reject"):
                raise d.ChatParamError(
                    f"审批决策无效：{decision!r}（可选：approve／reject）"
                )
            if decision == "reject" and not (reason and reason.strip()):
                # Action 链驳回必须写理由（N12）；extable 驳回不强制（A1 端点 5）——
                # 按挂起场景判别：无审批挂起/非 extable 场景一律按 Action 链口径要理由。
                scene = str((run.pending_interrupt or {}).get("scene") or "")
                if scene != d.EXTABLE_SCENE:
                    raise d.ChatParamError("Action 链驳回必须写理由（N12「须写理由的驳回」）")
            if run.status != "interrupt_approval":
                raise d.ChatRunStateError(
                    f"run 非 interrupt 审批挂起态：{run_id}（status={run.status}）"
                    "——审批挂起仅由问数链 N7.4c 外表审批产生（A1 端点 5）"
                )
            return run
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
        """澄清续推（interrupt 形态：caliber 口径两译｜candidates 低置信多候选）。

        - caliber：带 choice → 并入原问句上下文（输入严格变多）→ 重过安检（不
          免检——带参输入真扫描）→ 带参重判 → 续推；不选＝默认口径项（primary）。
        - candidates：带 choice → 锁定候选并入问句（焦点）→ 重判续推；不选＝
          拒答终态（「宁可不答、不瞎猜」——缺的是用户意图，不代选）。
        - rewrite（P1F-06 链内改写澄清）：选是 → 用优化问法上下文续推（输入严格
          变多——链内低分带改写过闸的问法；澄清额度已尽，重判不再弹帧）；选否/
          不选 → 坚持原问法诚实兜底（skip_rescore——链内低分带双重重评整段跳过）。
          链已定（检索问答链）——不重复意图裁决（澄清只裁决问法取舍）。
        - 有界循环：clarify_count 已 1（CHECK 0–1）时不再弹帧——两跳终态走
          默认口径/锁定候选后照常分派；第二次 clarify 一律 409。
        - approval 形态（M-06 extable）：decision=approve → 链恢复续跑出结果；
          reject → 权限拒答零重试（不自动改 SQL 重试，extable 驳回不强制理由）。
          无审批挂起 run——非 interrupt_approval 态一律 409（preflight）。
        """
        run = await self.resume_preflight(run_id, kind=kind, decision=decision, reason=reason)
        if kind == "approval":
            async for event in self._resume_approval(run, str(decision), actor_who):
                yield event
            return
        pending = run.pending_interrupt or {}
        frame = _frame_from_interrupt(pending)
        if frame is None:
            raise d.ChatRunStateError(f"run 挂起帧不可解析：{run_id}")
        subtype = str(pending.get("subtype") or "caliber")
        base_question = str(pending.get("question") or "")
        caliber_name: str | None = None
        locked_candidate: str | None = None
        rewrite_declined = False
        if subtype == "rewrite":
            # P1F-06 改写澄清回流：选是＝按优化问法续答；选否/不选＝诚实兜底
            # （两跳到终态防卡死——无默认项，不代选）。选项校验同 candidates 纪律。
            optimized = str(pending.get("optimized_question") or "")
            if choice and choice not in (d.REWRITE_CHOICE_ACCEPT, d.REWRITE_CHOICE_KEEP):
                raise d.ChatParamError(
                    f"澄清选项无效：{choice!r}"
                    f"（可选：{d.REWRITE_CHOICE_ACCEPT}／{d.REWRITE_CHOICE_KEEP}）"
                )
            if choice == d.REWRITE_CHOICE_ACCEPT and optimized:
                question: str | None = optimized
            else:
                question = base_question
                rewrite_declined = True
            run.status = "running"
            run.pending_interrupt = None
            await self._store.save_run(run)
        elif subtype == "candidates":
            if choice and choice.strip():
                if choice not in {c.value for c in frame.choices}:
                    raise d.ChatParamError(
                        f"澄清选项无效：{choice!r}"
                        f"（可选：{'、'.join(c.value for c in frame.choices)}）"
                    )
                locked_candidate = choice
                merged = base_question + (
                    "" if d.normalize_query(choice) in d.normalize_query(base_question)
                    else f"（焦点＝{choice}）"
                )
                run.status = "running"
                run.pending_interrupt = None
                await self._store.save_run(run)
                question = merged
            else:
                # 不选≠卡死：候选澄清无默认项——拒答终态（两跳到终态防卡死）。
                question = None
        elif subtype == d.MISSING_SUBTYPE:
            # M-06 缺参反问回流（askback 时间窗三选一——无默认项：缺的是用户
            # 事实，不代选）：choice＝补参候选并入问句（输入严格变多——链体重
            # 解析即得窗）；不选＝拒答终态（同 candidates 纪律，两跳到终态）。
            if choice and choice.strip():
                if choice not in {c.value for c in frame.choices}:
                    raise d.ChatParamError(
                        f"澄清选项无效：{choice!r}"
                        f"（可选：{'、'.join(c.value for c in frame.choices)}）"
                    )
                merged = base_question + (
                    "" if choice in base_question else f"（时间窗＝{choice}）"
                )
                run.status = "running"
                run.pending_interrupt = None
                await self._store.save_run(run)
                question = merged
            else:
                question = None
        else:
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
        if locked_candidate:
            audit_detail = f"候选锁定＝{locked_candidate}"
        elif question is None:
            audit_detail = "未选择——拒答终态"
        elif subtype == "rewrite":
            audit_detail = (
                "改写选择＝按优化问法续答" if not rewrite_declined
                else "改写选择＝坚持原问法——诚实兜底"
            )
        elif subtype == d.MISSING_SUBTYPE:
            audit_detail = f"缺参补齐＝{choice}"
        else:
            audit_detail = f"口径锁定＝{caliber_name}"
        await self._audit_received(
            actor_who, run.id, f"澄清回流：{base_question}（{audit_detail}）",
        )

        yield d.SseEvent(d.FRAME_SESSION, {
            "run_id": run.id, "thread_id": run.session_id, "resume": True,
        })
        yield d.SseEvent(d.FRAME_STAGE, {"stage": 0})
        yield d.SseEvent(d.FRAME_STAGE, {"stage": 1})
        # 澄清续跑不免检（A1 端点 5：新输入重过 D1 统一安检）——带参输入真扫描
        # （08a 帧面恒 pass 的缝隙本拍收口：拦截语义与 ask 同款终局）。
        recheck_text = question if question is not None else base_question
        yield d.node_frame("N1", state=d.NODE_PROCESS, tag="代码 · 字面规则",
                           note="统一安检——澄清带参复检（不免检）")
        blocked_feature = d.scan_injection(recheck_text)
        blocked_lane = "注入扫描" if blocked_feature is not None else None
        if blocked_feature is None:
            banned = d.check_banned(recheck_text)
            if banned is not None:
                blocked_feature = banned
                blocked_lane = "禁用词索引"
        if blocked_lane is not None:
            assert blocked_feature is not None
            for seq, name in enumerate(d.SEC_CHECKS, start=1):
                if name == blocked_lane:
                    note = (
                        f"命中注入特征「{blocked_feature}」"
                        if blocked_lane == "注入扫描"
                        else f"命中禁用词「{blocked_feature}」（废弃口径——先于一切解析）"
                    )
                    yield d.SseEvent(d.FRAME_SEC_CHECK, {
                        "seq": seq, "name": name, "result": "blocked", "note": note,
                    })
                    break
                yield d.SseEvent(d.FRAME_SEC_CHECK, {
                    "seq": seq, "name": name, "result": "pass", "note": "澄清带参复检（不免检）",
                })
            yield d.node_frame(
                "N1", state=d.NODE_FINISH,
                note=f"{blocked_lane}命中「{blocked_feature}」——拦截，链路终止",
            )
            tree_node = "N2a" if blocked_lane == "注入扫描" else "N2b"
            yield d.node_frame(
                tree_node, state=d.NODE_FINISH, tag="拦截终局 · 留痕入审计",
                note=(
                    f"命中注入特征「{blocked_feature}」——拦截终局（不进模型、不出数），拦截事件已留痕审计"
                    if tree_node == "N2a"
                    else f"命中禁用词「{blocked_feature}」——废弃口径纠正口，现行叫法随答案卡"
                ),
            )
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
                run.session_id, role="assistant", text=str(answer["text"]),
                run_id=run.id, answer=answer,
            )
            await self._store.touch_session(run.session_id)
            await self._finish_run(run, verdict=None)
            return
        for seq, name in enumerate(d.SEC_CHECKS, start=1):
            yield d.SseEvent(d.FRAME_SEC_CHECK, {
                "seq": seq, "name": name, "result": "pass", "note": "澄清带参复检（不免检）",
            })
        yield d.node_frame("N1", state=d.NODE_FINISH, note="三道全过——放行")
        if question is None:
            yield d.node_frame(
                "N5a", state=d.NODE_FINISH, tag="两跳到终态",
                note="候选未选——拒答终态（宁可不答、不瞎猜——缺的是用户意图，不代选）",
            )
            yield d.SseEvent(d.FRAME_NOTICE, {
                "level": "info",
                "text": "未选择候选——按「宁可不答、不瞎猜」铁律拒答（澄清帧两跳到终态）。",
            })
            # P-004 修复拍④：拒答终态文案独立（不借 D2 fallback_text——该路径
            # 拿不到装配物，「报告库里没有找到」对澄清收场不诚实）。
            answer = {
                "kind": "alert", "alert_type": "warning", "text": d.REFUSE_TERMINAL_TEXT,
            }
            yield d.SseEvent(d.FRAME_ANSWER, answer)
            yield d.SseEvent(d.FRAME_DONE, {})
            await self._store.append_message(
                run.session_id, role="assistant", text=str(answer["text"]),
                run_id=run.id, answer=answer,
            )
            await self._store.touch_session(run.session_id)
            await self._finish_run(run, verdict=None)
            return
        yield d.node_frame("N3", state=d.NODE_PROCESS, tag="代码 · 毫秒级",
                           note="轻装配——带参问句重过六路匹配器（输入严格变多）")
        # @ 锚定回流持久（M-07 F-01）：挂起载荷携 anchors 回流——重装配锚定语义
        # 不丢（存量挂起帧无此键＝空表兜底，行为同旧）。
        assembly = await self._assemble(question, _pending_anchors(pending))
        for lane in assembly.lanes:
            data: dict[str, Any] = {"matcher": lane.matcher, "status": lane.status}
            if lane.confidence is not None:
                data["confidence"] = lane.confidence
            if lane.note is not None:
                data["note"] = lane.note
            yield d.SseEvent(d.FRAME_MATCH, data)
        lane_hits = sum(1 for lane in assembly.lanes if lane.status == "hit")
        yield d.node_frame(
            "N3", state=d.NODE_FINISH,
            note=f"六路候选：命中 {lane_hits} 路——共池 {len(assembly.candidates)} 支"
                 "（全扫全收集，落空进建议池）",
        )
        yield d.node_frame("N4", state=d.NODE_PROCESS, tag="给裁决的呈堂材料",
                           note="装配块——锚点/槽位/候选/17 链清单组卷")
        yield d.SseEvent(d.FRAME_ASSEMBLY, {
            "anchor_line": assembly.anchor_line,
            "slots": assembly.slots,
            "terms": assembly.terms,
            "candidates": [_candidate_wire(c) for c in assembly.candidates],
            "chains": list(d.CHAIN17),
        })
        yield d.node_frame("N4", state=d.NODE_FINISH,
                           note=f"装配块组卷完成——slots＝{assembly.slots}")
        yield d.SseEvent(d.FRAME_STAGE, {"stage": 2})
        cfg = await self._config_loader()
        pending_chain = str(pending.get("chain") or "检索问答链")
        if subtype in ("rewrite", d.MISSING_SUBTYPE):
            # 链内澄清续推不重复意图裁决（P1F-06／M-06 missing 同纪律）：帧由链内
            # 弹出——链已定（挂起帧携发起链），澄清只裁决参数取舍；覆写为确定性
            # 续推裁决（零意图调用；澄清额度已尽——need_clarify 恒 false，不再弹帧）。
            if subtype == "rewrite":
                confidence = (
                    "中（按优化问法续答——改写澄清锁定）" if not rewrite_declined
                    else "低（坚持原问法——诚实兜底）"
                )
                verdict_note = "改写澄清续推——链不变，不重复意图裁决（澄清只裁决问法取舍）"
            else:
                confidence = "中（缺参补齐——时间窗锁定续推）"
                verdict_note = "缺参反问续推——链不变，不重复意图裁决（补参并入问句续推）"
            verdict = {
                "chain": pending_chain, "slots": assembly.slots,
                "confidence": confidence,
                "need_clarify": False,
                "source": d.VERDICT_SOURCE_DETERMINISTIC,
            }
            yield d.node_frame(
                "N5", state=d.NODE_PROCESS, tag="意图裁决 · 链内澄清续推",
                note=verdict_note,
            )
        else:
            yield d.node_frame(
                "N5", state=d.NODE_PROCESS, tag="意图裁决 · LLM＋兜底",
                note="意图裁决——带参重判（非重复裁决；LLM 分类＋确定性兜底同 ask）",
            )
            verdict = await self._decide(question, assembly, cfg)
            if verdict.get("need_clarify") is True:
                # 两跳到终态（默认口径/锁定候选）——不再弹澄清帧（有界循环：最多弹一次）。
                if subtype == "candidates":
                    verdict = {
                        "chain": "检索问答链", "slots": assembly.slots,
                        "confidence": d.CLARIFY_LOCKED_CONFIDENCE, "need_clarify": False,
                    }
                    yield d.SseEvent(d.FRAME_NOTICE, {
                        "level": "info",
                        "text": f"已按你选定的候选「{locked_candidate}」锁定并继续——澄清帧有界循环"
                                "（最多弹一次），两跳到终态。",
                    })
                else:
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
        chain_clarify = subtype in ("rewrite", d.MISSING_SUBTYPE)
        yield d.node_frame(
            "N5", state=d.NODE_FINISH,
            note=f"{'链内澄清续推裁决输出' if chain_clarify else '带参重判输出'}"
                 f"（来源＝{verdict.get('source')}）——chain＝{verdict.get('chain')}"
                 f" · confidence＝{verdict.get('confidence')}",
        )
        yield d.node_frame("N5b", state=d.NODE_PROCESS)
        n5b_note, rerouted_from = self._verify_chain_wiring(verdict)
        if rerouted_from is not None:
            await self._audit_rerouted(actor_who, run.id, rerouted_from)
        yield d.node_frame("N5b", state=d.NODE_FINISH, note=n5b_note)
        yield d.node_frame("N6", state=d.NODE_PROCESS, tag="查映射表派链")
        yield d.node_frame(
            "N6", state=d.NODE_FINISH,
            note=f"已分派至「{verdict.get('chain')}」——后续步骤由链体执行",
        )
        async for event in self._run_chain(
            str(verdict["chain"]), run, question, actor_who, assembly,
            verdict=verdict, clarified_caliber=caliber_name,
            skip_rescore=rewrite_declined, anchors=_pending_anchors(pending),
        ):
            yield event

    # ---------- 会话料源读口（B3 扫库消费——faq session_loader 注入位） ----------

    async def recent_qa_pairs(self) -> list[dict[str, str]]:
        """A1 历史会话问答对（[{question, answer}]——98 §3.3 faq 卡 session_loader
        料源缝；done 运行的问答配对，最近优先）。"""
        return await self._store.recent_qa_pairs(limit=d.RECENT_QA_LIMIT)

    # ---------- 断线重连真恢复（P1-08c——重放已持久化帧序列） ----------

    async def replay_preflight(self, run_id: str) -> ChatRunRow:
        """重连形态前置校验（开流前同步段——404 走 HTTP 错误包，流未开）。

        P0-08「run 存在性不校验」判据随真恢复退役：会话/消息已持久
        （chat_run/chat_message），run 不存在＝无可恢复对象——A1 错误码草案
        「run/session/task 不存在或已过期」404。
        """
        run = await self._store.get_run(run_id)
        if run is None:
            raise d.ChatRunNotFoundError(f"运行不存在或已过期：{run_id}")
        return run

    async def replay(self, run_id: str) -> AsyncIterator[d.SseEvent]:
        """断线重连真恢复：重放已持久化帧序列——能补多少补多少（P1-08c）。

        - done：session(resume)→verdict→citation×N（answer.citations 同形回放）
          →answer→done——已出内容不丢（重放流帧序号自断点续枚举，归 api 层；
          重放帧与原流帧 id 不对齐——能补的是持久化内容而非原流断点后的原帧序列）。
        - interrupt_clarify：session→verdict→clarify（pending_interrupt 持久帧）
          ——流收束不发 done（镜像原 ask 挂起形态；决策回流仍走端点 5）。
        - interrupt_approval（M-06 extable）：session→verdict→approval（持久帧）
          ——同形挂起重放；批准/驳回仍走端点 5。
        - running/failed/cancelled（及 done 而答案缺失）：持久前缀＋replay_truncated
          ③收场——生成已随断连取消，诚实收场不假装续传。
        - 中间过程帧（stage/sec_check/match/assembly/node/node_line/token/notice）
          不落库（99 §1.5「SSE 事件缓冲不落库」）——重放不伪造。
        只读重放：零消息写入、零 run 状态变更（recent_qa_pairs 料源语义不受扰动）。
        """
        run = await self.replay_preflight(run_id)
        yield d.SseEvent(d.FRAME_SESSION, {
            "run_id": run.id, "thread_id": run.session_id, "resume": True,
        })
        if run.verdict:
            yield d.SseEvent(d.FRAME_VERDICT, dict(run.verdict))
        if run.status == "interrupt_clarify":
            frame = (run.pending_interrupt or {}).get("frame")
            if frame:
                yield d.SseEvent(d.FRAME_CLARIFY, dict(frame))
                return
        elif run.status == "interrupt_approval":
            payload = run.pending_interrupt or {}
            if payload.get("kind") == "approval":
                yield d.SseEvent(d.FRAME_APPROVAL, {
                    "approval_id": str(payload.get("approval_id") or ""),
                    "scene": str(payload.get("scene") or d.EXTABLE_SCENE),
                    "title": d.EXTABLE_TITLE,
                    "reason": d.EXTABLE_REASON_TEMPLATE.format(
                        tables="、".join(payload.get("tables") or []) or "—"),
                    "impact": d.EXTABLE_IMPACT,
                })
                return
        elif run.status == "done":
            messages = await self._store.messages_of_run(run.id)
            answer = next(
                (m.answer for m in reversed(messages)
                 if m.role == "assistant" and m.answer is not None),
                None,
            )
            if answer is not None:
                for citation in answer.get("citations") or []:
                    yield d.SseEvent(d.FRAME_CITATION, dict(citation))
                yield d.SseEvent(d.FRAME_ANSWER, dict(answer))
                yield d.SseEvent(d.FRAME_DONE, {})
                return
        yield d.SseEvent(d.FRAME_REPLAY_TRUNCATED, {"message": d.REPLAY_CANCELLED_MESSAGE})

    # ---------- 审批回流续跑（M-06 extable——interrupt 恢复整节点重跑） ----------

    async def _resume_approval(
        self, run: ChatRunRow, decision: str, actor_who: str,
    ) -> AsyncIterator[d.SseEvent]:
        """审批回流（A1 端点 5：approve → 链恢复续跑出结果；reject → extable
        权限拒答零重试）。无新输入——不重过安检不重裁决；恢复时整节点重跑
        （F7 节点幂等——链体从 N7.1 确定性重推导，N7.4c 以 extable_decision
        判别两路）。审批留痕走 B12 审计（extable 纯链内闸——不进 A3 台账）。
        """
        pending = run.pending_interrupt or {}
        question = str(pending.get("question") or "")
        approval_id = str(pending.get("approval_id") or "")
        tables = "、".join(str(t) for t in (pending.get("tables") or []))
        chain = str(pending.get("chain") or "状态机六站链")
        run.status = "running"
        run.pending_interrupt = None
        run.pending_approval_id = None
        await self._store.save_run(run)
        await self._audit_approval(actor_who, run.id, approval_id, decision, tables)

        yield d.SseEvent(d.FRAME_SESSION, {
            "run_id": run.id, "thread_id": run.session_id, "resume": True,
        })
        yield d.SseEvent(d.FRAME_STAGE, {"stage": 2})
        verdict = {
            "chain": chain, "slots": "—（审批回流——不重装配裁决）",
            "confidence": (
                "中（审批批准——interrupt 恢复续跑）" if decision == "approve"
                else "低（审批驳回——权限拒答零重试）"
            ),
            "need_clarify": False,
            "source": d.VERDICT_SOURCE_DETERMINISTIC,
        }
        await self._record_verdict(run, verdict)
        yield d.SseEvent(d.FRAME_VERDICT, _wire_verdict(verdict))
        yield d.node_frame(
            "N5", state=d.NODE_FINISH,
            note=f"审批回流（决策＝{'批准续跑' if decision == 'approve' else '驳回'}）"
                 f"——无新输入不重裁决，链恢复整节点重跑（F7 节点幂等）",
        )
        yield d.node_frame("N5b", state=d.NODE_PROCESS)
        n5b_note, rerouted_from = self._verify_chain_wiring(verdict)
        if rerouted_from is not None:
            await self._audit_rerouted(actor_who, run.id, rerouted_from)
        yield d.node_frame("N5b", state=d.NODE_FINISH, note=n5b_note)
        yield d.node_frame("N6", state=d.NODE_PROCESS, tag="查映射表派链")
        yield d.node_frame(
            "N6", state=d.NODE_FINISH,
            note=f"已分派至「{chain}」——interrupt 恢复续跑",
        )
        assembly = await self._assemble(question, _pending_anchors(pending))
        async for event in self._run_chain(
            chain, run, question, actor_who, assembly,
            verdict=verdict, extable_decision=decision,
            extable_approval_id=approval_id or None,
            anchors=_pending_anchors(pending),
        ):
            yield event

    # ---------- ② 知识装配（六路匹配器——并行查表共池，词级全扫全收集） ----------

    async def _assemble(self, question: str, anchors: list[str]) -> d.AssemblyResult:
        """装配层：@ 前门直取＋六路匹配器全扫全收集（装配候选共池）。

        - 被 @ 的一路不过匹配器、其他五路照跑（F56 @ 倾向协议——候选在场是
          「倾向≠直通」的物质基础）；被让位路不记落空（候选已经前门在场）；
        - 落空（含注册表未建的两路）逐路进建议池；
        - 装配候选不设上限（全扫全收集）；澄清帧候选上限 4 支在 clarify 构造截断；
        - 词条卡装卡（P1F-02）：术语/指标命中完整行与 @ 前门直取术语/指标投影成
          term_cards/metric_cards 随行材料（修复拍二②补齐 @ 指标对称补卡）——
          零新增查询（只复用已查得行）。
        """
        needle = d.normalize_query(question)
        anchor_line: str | None = None
        candidates: list[d.Candidate] = []
        terms: list[str] = []
        slots_parts: list[str] = []
        anchored_matchers: set[str] = set()
        anchored_term_names: list[str] = []
        anchored_metric_names: list[str] = []

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
                anchored_term_names.append(name)
            if asset_type == "指标卡":
                anchored_metric_names.append(name)

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
        term_hits: list[d.TermFace] = []  # 命中完整行（词条卡装卡源——P1F-02）
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

        # 图谱缝（P1-08b 组合根注入真图检索——非 F56 六路匹配器，不发 match 帧；
        # 候选共池、落空进建议池；图谱问答链消费）
        graph_hits = list(await self._search_graph(question))
        if graph_hits:
            for gh in graph_hits[:INDEX_CANDIDATE_MAX]:
                candidates.append(d.Candidate(
                    "图谱", f"{gh.entity}（{gh.relation}）", "high", "graph",
                    note=gh.evidence or "图谱缝命中——图谱问答链消费",
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

        # —— 词条卡装卡（P1F-02：一等材料常驻装配——完整行投影成卡，零新增查询）——
        # @ 前门直取术语/指标按锚定序补卡（_resolve_anchor 已核验在账——术语归一化
        # 等值、指标槽位名/台账名包含，补卡匹配随各自治缝；修复拍二②补齐指标对称
        # ——匹配器让位路同样出卡），匹配器命中行随后逐条装卡；去重防同一行双卡。
        term_cards: list[d.TermCard] = []
        carded: set[str] = set()
        for name in anchored_term_names:
            probe = d.normalize_query(name)
            for row in term_rows:
                if probe and d.normalize_query(row.term) == probe and row.term not in carded:
                    term_cards.append(_term_card(row))
                    carded.add(row.term)
        for row in term_hits:
            if row.term not in carded:
                term_cards.append(_term_card(row))
                carded.add(row.term)
        metric_cards: list[d.MetricCard] = []
        carded_metrics: set[int] = set()
        for name in anchored_metric_names:
            probe = d.normalize_query(name)
            for metric in metrics:
                if (
                    probe
                    and metric.metric_id not in carded_metrics
                    and (
                        probe in d.normalize_query(metric.slot_name)
                        or probe in d.normalize_query(metric.name)
                    )
                ):
                    metric_cards.append(_metric_card(metric))
                    carded_metrics.add(metric.metric_id)
        for metric in metric_hits:
            if metric.metric_id not in carded_metrics:
                metric_cards.append(_metric_card(metric))
                carded_metrics.add(metric.metric_id)

        return d.AssemblyResult(
            anchor_line=anchor_line,
            slots=" · ".join(slots_parts) if slots_parts else "∅",
            terms=terms,
            candidates=candidates,
            lanes=lanes,
            ambiguous_metric=ambiguous_metric,
            faq_hit=faq_hit,
            index_hits=index_hits,
            graph_hits=graph_hits,
            term_cards=term_cards,
            metric_cards=metric_cards,
        )

    async def _search_graph(self, question: str) -> list[d.GraphHitFace]:
        """图谱缝检索（组合根注入真图检索；未注入时恒空——候选共池落空）。"""
        if self._graph_searcher is None:
            return []
        return list(await self._graph_searcher(question))

    async def _load_anchor(self, fragment_id: str) -> d.FragmentAnchorFace | None:
        """片段锚校验缝（fail-closed——组合根注入 kb.fragment_anchor）。"""
        if self._anchor_loader is None:
            return None
        return await self._anchor_loader(fragment_id)

    async def _resolve_anchor(self, asset_type: str, name: str) -> bool:
        """@ 资产直取（服务端按主键/名称直取——取不到＝落空拒答）。

        注册表面：指标卡/术语→semantics 台账；FAQ→match_index；工作流→
        sem_workflow（P1-11 assets 同源）；报告→kb 报告台账（P1-11 assets 同源）；
        工具注册表未建（m8 随其票）——直取必落空（assets 投影同为空，界面选不到）。
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
        if asset_type == "工作流":
            workflows = await self._workflow_lister()
            return any(probe == d.normalize_query(wname) for wname, _s in workflows)
        if asset_type == "报告":
            return any(probe in d.normalize_query(doc) for doc in await self._report_lister())
        return False

    # ---------- A1 端点 2/6 读端点（P1-11 真接线——前端去降级标） ----------

    async def list_sessions(self, actor_who: str) -> list[d.SessionItem]:
        """历史会话（A1 端点 2——当前身份，updated_at 倒序；合同形状 id/title/
        group/scenario_id/updated_at）。group/scenario_id 骨架期 null（场景注册表
        端点 1 随其票——null 前端渲染空串）。"""
        rows = await self._store.list_sessions(user_id=_actor_key(actor_who))
        return [
            d.SessionItem(
                id=row.id, title=row.title, group=row.group, scenario_id=row.scenario_id,
                updated_at=row.updated_at.isoformat(timespec="seconds"),
            )
            for row in rows
        ]

    async def session_messages(self, session_id: str, actor_who: str) -> list[d.SessionMessageItem]:
        """会话消息回放（A1 端点 3——合同形状 id/role/text/run_id/answer）。

        answer 与 SSE answer 帧同形（一份 DTO 两处消费——citations 随 answer
        内嵌），直出 jsonb 不折形；seq 升序即回放序。会话不存在或非当前身份
        一律 404（端点 2 身份隔离同款——不泄漏存在性）。历史「思考过程」逐帧
        回放不在本版合同（A1 开放问题 2——事件级存档回放待 D5 产品化批）。
        """
        row = await self._store.get_session(session_id)
        if row is None or row.user_id != _actor_key(actor_who):
            raise d.ChatSessionNotFoundError(f"会话不存在或已过期：{session_id}")
        return [
            d.SessionMessageItem(
                id=m.id, role=m.role, text=m.text, run_id=m.run_id, answer=m.answer,
            )
            for m in await self._store.list_messages(session_id)
        ]

    async def assets(self, q: str | None, type_filter: str | None) -> list[d.AssetItem]:
        """@ 资产面板（A1 端点 6——各注册表现取投影不建仓，永不与注册表漂移）。

        数据直取各域清单（C1 台账指标卡/术语＋工作流、B3 服务中 FAQ、B1 报告
        索引；工具注册表未建投影为空）；type 越界 400（合同六类闭世界）；
        q＝name 子串包含（大小写不敏感——资产面板客户端过滤语义服务端化）。
        阶段 1 单一角色系统管理员全权（P1-00b 拍板基线）——无角色裁剪面。
        """
        if type_filter is not None and type_filter not in d.ASSET_TYPES:
            raise d.ChatParamError(
                f"type 筛选值越界：{type_filter}（允许：{'、'.join(d.ASSET_TYPES)}）"
            )
        items: list[d.AssetItem] = []
        for metric in await self._metrics_loader():
            items.append(d.AssetItem("指标卡", metric.slot_name, f"指标卡·{metric.slot_name}"))
        for term in await self._terms_loader():
            items.append(d.AssetItem("术语", term.term, f"术语·{term.term}"))
        if self._faq_lister is not None:
            for question in await self._faq_lister():
                items.append(d.AssetItem("FAQ", question, f"FAQ·{question}"))
        for name, _status in await self._workflow_lister():
            items.append(d.AssetItem("工作流", name, f"工作流·{name}"))
        for doc in await self._report_lister():
            items.append(d.AssetItem("报告", doc, f"报告·{doc}"))
        if type_filter is not None:
            items = [item for item in items if item.type == type_filter]
        needle = (q or "").strip().casefold()
        if needle:
            items = [item for item in items if needle in item.name.casefold()]
        return items

    # ---------- ③ 意图裁决（P1-11：LLM 分类裁决＋确定性信号路由兜底） ----------

    def _verdict(
        self, question: str, assembly: d.AssemblyResult, cfg: d.RetrievalConfigFace
    ) -> dict[str, Any]:
        """确定性信号路由（LLM 不可用时的兜底面——source=deterministic）。

        路由（闭世界 17 链——确定性信号序）：
        - FAQ 精确命中＋faq_direct_hit 开 → FAQ直出链（秒回闸——D2 运行时消费归 A1）；
        - 口径两译未消歧（ambiguous 台账命中且问句未点口径支名）→ need_clarify、
          chain null（裁决未定）——clarify_strategy 消费（ask_missing 档开闸）；
        - 图谱缝命中＋关系问句信号（或报告索引未命中）→ 图谱问答链；
        - 其余按置信度真实计算（检索得分＋装配信号）：低 <low 必弹澄清帧（F56
          拍板口径）——候选在场弹候选澄清帧（S6 资格裁决），无候选直派检索链
          走兜底（refuse_threshold 消费）。

        `_clarify`/`_clarify_metric`/`_clarify_subtype` 为域内随行键——wire 前经
        _wire_verdict 剥除。
        """
        gate = self._verdict_gates(question, assembly, cfg)
        if gate is not None:
            return gate
        return self._verdict_signals(question, assembly, cfg)

    def _verdict_gates(
        self, question: str, assembly: d.AssemblyResult, cfg: d.RetrievalConfigFace
    ) -> dict[str, Any] | None:
        """合同硬闸（确定性、先于 LLM——FAQ 直出闸＋口径两译澄清；无闸命中=None）。

        两闸是 D2 配置驱动的合同行为（P1-08b 行为变化测试在案）——意图裁决换
        LLM 不改变硬闸语义；LLM 只对剩余路由空间分类。
        """
        if assembly.faq_hit is not None and cfg.faq_direct_hit:
            return {
                "chain": "FAQ直出链", "slots": assembly.slots,
                "confidence": d.FAQ_ROUTE_CONFIDENCE, "need_clarify": False,
                "source": d.VERDICT_SOURCE_DETERMINISTIC,
            }
        ambiguous = assembly.ambiguous_metric
        if (
            ambiguous is not None
            and cfg.clarify_strategy == "ask_missing"
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
                    "_clarify_subtype": "caliber",
                    "source": d.VERDICT_SOURCE_DETERMINISTIC,
                }
        return None

    def _verdict_signals(
        self, question: str, assembly: d.AssemblyResult, cfg: d.RetrievalConfigFace
    ) -> dict[str, Any]:
        """确定性信号路由（图谱关系信号＋数据问句信号＋置信度真实计算——LLM 兜底面）。

        数据问句信号（M-06）：指标台账命中＋时间/数量/排名词面 → 状态机六站链
        （零模型调用——N7.1 复用同源装配做三要素校验；纯检索/释义问法不劫走，
        维持检索问答链主路径）。查询策略配置面挂阶段 3——本信号是链内确定性规则，
        不读配置。
        """
        if (
            assembly.graph_hits
            and (d.is_relation_question(question) or not assembly.index_hits)
        ):
            return {
                "chain": "图谱问答链", "slots": assembly.slots,
                "confidence": d.GRAPH_ROUTE_CONFIDENCE, "need_clarify": False,
                "source": d.VERDICT_SOURCE_DETERMINISTIC,
            }
        metric_hit = any(c.kind == "metric" for c in assembly.candidates)
        if metric_hit and d.is_data_question(question):
            return {
                "chain": "状态机六站链", "slots": assembly.slots,
                "confidence": d.DATA_ROUTE_CONFIDENCE, "need_clarify": False,
                "source": d.VERDICT_SOURCE_DETERMINISTIC,
            }
        best_score = max((h.score for h in assembly.index_hits), default=0.0)
        ledger_hit = any(c.kind in ("metric", "term") for c in assembly.candidates)
        value = d.compute_confidence(
            anchored=bool(assembly.anchor_line), ledger_hit=ledger_hit,
            faq_hit=False, best_index_score=best_score,
        )
        label = d.confidence_label(
            value, high=cfg.confidence_high, low=cfg.confidence_low,
            best_score=best_score, anchored=bool(assembly.anchor_line),
            ledger_hit=ledger_hit,
        )
        if value < cfg.confidence_low:
            frame = d.build_candidate_clarify(
                assembly.candidates, frame_id=f"clarify-{now():%H%M%S%f}"
            )
            if frame is not None:
                return {
                    "chain": None, "slots": assembly.slots,
                    "confidence": label, "need_clarify": True,
                    "clarify_frame": frame.question,
                    "_clarify": frame,
                    "_clarify_subtype": "candidates",
                    "source": d.VERDICT_SOURCE_DETERMINISTIC,
                }
        return {
            "chain": "检索问答链", "slots": assembly.slots,
            "confidence": label, "need_clarify": False,
            "source": d.VERDICT_SOURCE_DETERMINISTIC,
        }

    async def _decide(
        self, question: str, assembly: d.AssemblyResult, cfg: d.RetrievalConfigFace
    ) -> dict[str, Any]:
        """裁决层主入口（P1-11 LLM 意图裁决接线）：硬闸 → LLM 分类 → 信号兜底。

        - 合同硬闸恒先行（FAQ 直出闸/口径两译澄清——source=deterministic）；
        - LLM 分类（petro-main，caller=chat.intent.verdict，有界超时）成功且
          chain 过闭世界校验 → 采信（source=llm；低置信 <low 仍必弹澄清帧——
          F56 拍板，阈值闸不因来源豁免）；
        - LLM 失败/超时/解析坏/链名越界 → 确定性信号路由兜底（不许问挂——
          source=deterministic）。
        """
        gate = self._verdict_gates(question, assembly, cfg)
        if gate is not None:
            return gate
        llm = await self._verdict_llm(question, assembly, cfg)
        if llm is not None:
            value = llm["_value"]
            if value >= cfg.confidence_low:
                return llm
            frame = d.build_candidate_clarify(
                assembly.candidates, frame_id=f"clarify-{now():%H%M%S%f}"
            )
            if frame is not None:
                return {
                    "chain": None, "slots": assembly.slots,
                    "confidence": llm["confidence"], "need_clarify": True,
                    "clarify_frame": frame.question,
                    "_clarify": frame,
                    "_clarify_subtype": "candidates",
                    "source": d.VERDICT_SOURCE_LLM,
                }
            return llm  # 低置信但无候选可澄清——直派检索链走兜底（LLM 裁决仍采信）
        return self._verdict_signals(question, assembly, cfg)

    async def _verdict_llm(
        self, question: str, assembly: d.AssemblyResult, cfg: d.RetrievalConfigFace
    ) -> dict[str, Any] | None:
        """petro-main 意图分类（闭世界 17 链枚举·结构化输出——F56③ 真源接线）。

        任一环不可用（completer 未装配/调用失败/超时/JSON 解析坏/链名越界/置信
        度非数值）返回 None——调用方走确定性信号路由兜底（不许问挂）。
        """
        completer = self._deps.completer
        if completer is None:
            return None
        lanes = "；".join(f"{lane.matcher}={lane.status}" for lane in assembly.lanes)
        candidates = "、".join(c.name for c in assembly.candidates[:8]) or "无"
        messages = [
            {"role": "system", "content": INTENT_VERDICT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"问句：{question}\n"
                    f"六路装配信号：{lanes}\n"
                    f"装配候选：{candidates}\n"
                    f"17 链清单：{'、'.join(d.CHAIN17)}"
                ),
            },
        ]
        try:
            completion = await asyncio.wait_for(
                completer.complete(
                    chains_mod.MAIN_ALIAS, messages, caller=d.CALLER_INTENT_VERDICT
                ),
                timeout=d.INTENT_VERDICT_TIMEOUT_SECONDS,
            )
        except Exception:
            LOGGER.warning(
                "chat LLM 意图裁决不可用（失败/超时 %.0fs）——确定性信号路由兜底",
                d.INTENT_VERDICT_TIMEOUT_SECONDS,
            )
            return None
        chain, value = _parse_intent_json(str(completion.content or ""))
        if chain is None or value is None or chain not in d.CHAIN17:
            LOGGER.warning(
                "chat LLM 意图裁决解析坏/链名越界（%r）——确定性信号路由兜底", chain
            )
            return None
        return {
            "chain": chain, "slots": assembly.slots,
            "confidence": d.confidence_label_llm(
                value, high=cfg.confidence_high, low=cfg.confidence_low
            ),
            "need_clarify": False,
            "source": d.VERDICT_SOURCE_LLM,
            "_value": value,
        }

    def _verify_chain_wiring(self, verdict: dict[str, Any]) -> tuple[str, str | None]:
        """N5b 接线核验（P1F-01）：闭世界校验之上再验接线注册面——未注册链回退。

        17 链清单已接线四链（状态机六站/检索问答/FAQ直出/图谱问答——分派器
        注册面）；裁决选中未注册壳链时就地覆写 verdict["chain"] 为「检索问答链」
        （只动 chain 键——confidence/source 留痕不动，分派前覆写使 run 终态
        verdict 与实派链一致），返回 (note, 回退原链)——回退发生时原链非 None，
        供调用方落 B12 审计行（M-07 F-03：chat.ask.rerouted，正常路径零开销）；
        已注册四链绝不覆写。ask 主路径与 resume 重判路径共用本核验——回退逻辑
        单源，两处行为一致由构造保证。
        """
        chain = str(verdict.get("chain") or "")
        if self._dispatcher.is_registered(chain):
            return (
                f"chain「{chain}」在 17 链清单内且已接线——核验通过（闭世界枚举＋注册面）",
                None,
            )
        verdict["chain"] = "检索问答链"
        return (f"原裁决＝「{chain}」未接线——回退检索问答链", chain)

    # ---------- ④ 执行链分发与收场 ----------

    async def _run_chain(
        self, chain: str, run: ChatRunRow, question: str, actor_who: str,
        assembly: d.AssemblyResult, *, verdict: dict[str, Any],
        clarified_caliber: str | None = None, skip_rescore: bool = False,
        extable_decision: str | None = None, extable_approval_id: str | None = None,
        anchors: list[str] | None = None,
    ) -> AsyncIterator[d.SseEvent]:
        """链体帧流透传＋收场（stage(3) → 链内帧 → answer → done；答案落会话历史）。

        链内澄清哨兵（P1F-06 rewrite／M-06 缺参反问）在流内拦截：clarify 帧
        wire（subtype 透传）下发＋_suspend_clarify 挂起、流收束不发 done（镜像
        ask 澄清路径）——哨兵本体（域内对象）不出域。链内审批哨兵（M-06 extable）
        同形拦截：approval 帧 wire（A1 帧 15 冻结形状）下发＋_suspend_approval
        挂起（interrupt_approval——pending_approval_id 落列）。skip_rescore 供
        rewrite 选否/不选回流续推；extable_decision/approval_id 供审批回流整节点
        重跑（F7 节点幂等——N7.4c 判据）；anchors 供挂起载荷携锚（M-07 F-01——
        resume 重装配时锚定语义不丢）。"""
        yield d.SseEvent(d.FRAME_STAGE, {"stage": 3})
        answer: dict[str, Any] | None = None
        ctx = d.ChainContext(
            run_id=run.id, question=question, actor_who=actor_who, assembly=assembly,
            clarified_caliber=clarified_caliber,
            clarify_available=run.clarify_count < d.CLARIFY_MAX_POPUPS,
            skip_rescore=skip_rescore,
            extable_decision=extable_decision,
            extable_approval_id=extable_approval_id,
        )
        async for event in self._dispatcher.dispatch(chain, ctx):
            if event.event == d.FRAME_CLARIFY and event.data.get("_chain_signal"):
                frame = event.data["frame"]
                subtype = str(event.data.get("subtype") or "rewrite")
                yield d.SseEvent(d.FRAME_CLARIFY, _clarify_wire(frame, subtype))
                await self._suspend_clarify(run, {
                    "_clarify": frame,
                    "_clarify_subtype": subtype,
                    "_optimized_question": str(event.data.get("optimized_question") or ""),
                    "_chain": chain,
                }, question=question, anchors=anchors)
                return
            if event.event == d.FRAME_APPROVAL and event.data.get("_chain_signal"):
                payload = dict(event.data["payload"])
                yield d.SseEvent(d.FRAME_APPROVAL, d.approval_wire(payload))
                await self._suspend_approval(run, payload, question=question,
                                             anchors=anchors)
                return
            if event.event == d.FRAME_ANSWER:
                answer = event.data
            yield event
        if answer is None:
            # 链体未产 answer 帧（注桩缺陷/异常安全网）——不收场不带病。
            answer = {
                "kind": "alert", "alert_type": "error",
                "text": "链内未产出答案——请重新提问。",
            }
            yield d.SseEvent(d.FRAME_ANSWER, answer)
        yield d.SseEvent(d.FRAME_DONE, {})
        await self._store.append_message(
            run.session_id, role="assistant", text=_answer_text(answer),
            run_id=run.id, answer=answer,
        )
        await self._store.touch_session(run.session_id)
        await self._finish_run(run, verdict=verdict)

    # ---------- 运行状态与挂起帧（chat_run 状态机——澄清有界循环存储强制） ----------

    async def _suspend_clarify(
        self, run: ChatRunRow, verdict: dict[str, Any], *, question: str,
        anchors: list[str] | None = None,
    ) -> None:
        """澄清挂起（interrupt_clarify——pending_interrupt 落帧；clarify_count +1）。

        载荷携原问句、挂起帧（subtype 透传进持久 wire——重放同形）与 subtype
        （caliber｜candidates｜rewrite）——resume 带参重判的上下文（输入严格变多）；
        rewrite 挂起另携 optimized_question（P1F-06——选是续推的优化问句）；
        anchors 携发起时 @ 锚定 tokens（M-07 F-01——回流重装配锚定语义不丢，
        additive 键、存量帧无此键＝空表兜底）；
        clarify_count CHECK 0–1 是「最多弹一次」的存储强制。
        """
        clarify = verdict.get("_clarify")
        if not isinstance(clarify, d.ClarifyFrame) or run.clarify_count >= d.CLARIFY_MAX_POPUPS:
            raise d.ChatRunStateError("澄清帧有界循环已尽——第二次 clarify 拒绝（409）")
        subtype = str(verdict.get("_clarify_subtype") or "caliber")
        run.status = "interrupt_clarify"
        run.clarify_count = run.clarify_count + 1
        pending: dict[str, Any] = {
            "kind": "clarify",
            "subtype": subtype,
            "frame": _clarify_wire(clarify, subtype),
            "question": question,
            "metric": dict(verdict.get("_clarify_metric") or {"metric_id": None}),
            "anchors": list(anchors or []),
        }
        if verdict.get("_optimized_question"):
            pending["optimized_question"] = str(verdict["_optimized_question"])
        if verdict.get("_chain"):
            # 发起链（M-06 缺参反问——resume 续推按原链分派，不重裁决）；
            # rewrite 先例缺省＝检索问答链（pending 无此键时同值兜底）。
            pending["chain"] = str(verdict["_chain"])
        run.pending_interrupt = pending
        await self._store.save_run(run)

    async def _suspend_approval(
        self, run: ChatRunRow, payload: dict[str, Any], *, question: str,
        anchors: list[str] | None = None,
    ) -> None:
        """审批挂起（M-06 extable——interrupt_approval；pending_approval_id 落列）。

        A1：extable＝纯链内闸，不产生变动单、不进 A3 台账——留痕＝审批留痕单号
        随答案展示＋审计可查（B12 审计在 resume 决策拍落笔）。载荷携原问句、
        发起链与计划 wire（审批回流整节点重跑的上下文——F7 节点幂等）；
        anchors 携发起时 @ 锚定 tokens（M-07 F-01——回流重装配锚定语义不丢）。
        """
        run.status = "interrupt_approval"
        run.pending_approval_id = str(payload.get("approval_id") or "")
        run.pending_interrupt = {
            "kind": "approval",
            "scene": str(payload.get("scene") or d.EXTABLE_SCENE),
            "approval_id": str(payload.get("approval_id") or ""),
            "chain": "状态机六站链",
            "question": question,
            "tables": list(payload.get("_tables") or []),
            "plan": dict(payload.get("_plan") or {}),
            "anchors": list(anchors or []),
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

    async def _audit_approval(
        self, who: str, run_id: str, approval_id: str, decision: str, tables: str,
    ) -> None:
        """审批决策留痕（B12——extable 纯链内闸的「审计可查」半边；A1 端点 5）。"""
        if self._audit is None:
            return
        outcome = (
            "批准续跑（只读执行，生产库未动）" if decision == "approve"
            else "驳回——权限拒答零重试"
        )
        await self._audit.audit(AuditRow(
            who=who,
            action="chat.ask.approval",
            content=f"外表审批回流（run {run_id} · 单号 {approval_id}）——外表 {tables}：{outcome}",
        ))

    async def _audit_rerouted(self, who: str, run_id: str, original_chain: str) -> None:
        """接线回退留痕（B12——M-07 F-03：00 §8.2「拦截也是审计事件」同族的路由
        改写不留盲区；动作语义照 chat.ask 审计族惯例——回退发生时落笔，正常
        路径零开销）。"""
        if self._audit is None:
            return
        await self._audit.audit(AuditRow(
            who=who,
            action="chat.ask.rerouted",
            content=(
                f"意图裁决接线回退（run {run_id}）——原裁决「{original_chain}」未接线，"
                "覆写回退检索问答链（N5b 帧 note 留痕）"
            ),
        ))


def _actor_key(actor_who: str) -> str:
    """who 展示名 → 会话归属技术列（五角色 label→键；未知串原样——演示量级）。"""
    for key, profile in ROLE_REGISTRY.items():
        if profile.display == actor_who:
            return key
    return actor_who


def _wire_verdict(verdict: dict[str, Any]) -> dict[str, Any]:
    """裁决 JSON 的 wire 形（剥域内随行键——A1 裁决帧字段照抄＋source 双来源）。"""
    return {k: v for k, v in verdict.items() if not k.startswith("_")}


async def _empty_strs() -> list[str]:
    return []


async def _empty_pairs() -> list[tuple[str, str]]:
    return []


def _clarify_wire(frame: d.ClarifyFrame, subtype: str | None = None) -> dict[str, Any]:
    """clarify 帧 wire 形（A1 帧 14 冻结形状 {frame_id, question, choices}）＋
    additive `subtype` 键（P1F-06——前端分支渲染消费；缺省不带＝既有形状不变，
    additive 登记照 verdict.source 先例随 L0 合同对齐批）。挂起持久帧与下发帧
    同形——重放一致。"""
    wire: dict[str, Any] = {
        "frame_id": frame.frame_id,
        "question": frame.question,
        "choices": [
            {"value": c.value, "label": c.label, **({"primary": True} if c.primary else {})}
            for c in frame.choices
        ],
    }
    if subtype is not None:
        wire["subtype"] = subtype
    return wire


def _candidate_wire(candidate: d.Candidate) -> dict[str, Any]:
    data: dict[str, Any] = {
        "matcher": candidate.matcher, "name": candidate.name,
        "confidence": candidate.confidence, "kind": candidate.kind,
    }
    if candidate.note is not None:
        data["note"] = candidate.note
    return data


def _term_card(row: d.TermFace) -> d.TermCard:
    """术语完整行 → 词条卡（P1F-02——状态标注串走 C1 同款派生口径，domain 单源）。

    today 取 infra.clock（B14）——派生不入库不参与计算，只随卡展示。
    """
    return d.TermCard(
        term=row.term, type=row.type, def_text=row.def_text,
        status_note=d.term_card_status_note(
            status=row.status, status_key=row.status_key,
            expires_at=row.expires_at, today=now().date(),
        ),
    )


def _metric_card(metric: d.MetricFace) -> d.MetricCard:
    """指标完整行 → 指标卡（P1F-02——状态标注经 metric_card_status_note 归一
    （sem list 形态「／」join、str 原样——P-004 修复拍②），口径支行原样投影）。"""
    return d.MetricCard(
        slot_name=metric.slot_name, name=metric.name,
        calibers=list(metric.calibers),
        status_note=d.metric_card_status_note(metric.status),
    )


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


def _pending_anchors(pending: dict[str, Any]) -> list[str]:
    """挂起载荷回读 anchors（M-07 F-01——回流重装配携锚；存量帧无此键＝空表
    兜底，行为同旧；形状加防——非列表值一律按无锚处理）。"""
    value = pending.get("anchors")
    if not isinstance(value, list):
        return []
    return [str(token) for token in value]


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
