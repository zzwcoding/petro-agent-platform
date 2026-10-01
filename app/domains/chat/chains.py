"""domains.chat.chains —— 三链链体（P1-08b 链体＋P1-08c 树叙事步进）。

检索问答链（D2 当前生效配置驱动全链——S 级语义照 F58/W-F21）：
  N17 检索问答（树执行节点）→ S0 身份四要素（一次确认）→ S1 显式锚定（受第 1 级
  开关管辖）→ S3 词表四级（台账精确）→ S4 双路召回（向量 topK1＋trigram topK2
  并发）→ 合并（rrf_rank k=60 固定推荐值 / concat）→ 前 N → 精排三档（fast 融合
  序放行 / llm 逐条打分 / compound 0.6/0.3/0.1＋MMR λ=0.7）→ FAQ 路（直出关——
  并入检索，扩检轮数消费）→ S5 图扩展（未启用——直通跳过）→ S6 资格裁决（4 支
  上限＋refuse_threshold 拒答判定）→ S7 权威源回读（指标台账核对）→ GEN 限定
  作答（petro-main）→ citation fail-closed（伪造/失锚引用拦截丢弃，绝不带病出帧）
  → N17 收束。命中即停：上级命中即跳过下级检索级（关＝逐级全跑）；S0/S2/S6/S7
  不受早停影响。兜底两策：检索全空/低于低分线 → fixed 文案或 free＋「未依据报告
  库」标注。
  思考树叙事（P1-08c）：链内步进＝node 帧序——执行级 state 推进 process→finish、
  跳过级 wait＋skipped:true（00 §5.3 ①）；node_line 保留为节点内内容行（扩检轮
  次/FAQ 并入/配置核对/模型第 N 次调用标注——A1 帧 8）；token 切片在全部树帧后。

FAQ 秒回链：N18 预制问答 process→finish——match_index 命中已发布 → 直出答案＋
  citation（no_model=true——「本条命中 FAQ 直出——未调用模型」）。
图谱问答链：N13 关系追溯 process→finish——graph 缝命中 → 邻域边证据（边出处回
  证据）→ GEN 生成带图谱出处 citation。

B6：LLM 只走注入 completer（生产＝GatewayService.complete，别名 petro-main）；
B1：本文件不 import fastapi/starlette/DB——链体只见注入缝。
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, replace
from typing import Any

from app.domains.chat import domain as d

LOGGER = logging.getLogger("domains.chat")

# B6 别名与 caller 归因（D1 别名 petro-main＝生成/打分默认出口；caller 落 gateway
# 记账——D5 观测按 caller 聚合）。
MAIN_ALIAS = "petro-main"
CALLER_RETRIEVAL = "chat.retrieval.answer"
CALLER_RERANK = "chat.retrieval.rerank"
CALLER_GRAPH = "chat.graph.answer"
CALLER_FALLBACK = "chat.retrieval.fallback"

GEN_SYSTEM_PROMPT = (
    "你是油田数据问答平台的回答助手。只依据给出的编号材料回答，"
    "不编造材料之外的事实。引用材料是硬性要求：每条依据都必须在句末标注其编号，"
    "格式形如 [c1]（半角方括号＋编号）；材料不足以回答时如实说明。"
)
GEN_FALLBACK_SYSTEM_PROMPT = (
    "你是油田数据问答助手。当前报告库中没有能回答该问题的材料——"
    "请基于通用知识谨慎、简短地回答，并明确说明这不是来自报告库的依据。"
)
GRAPH_GEN_USER_TEMPLATE = (
    "问题：{question}\n\n图谱关系材料（编号表）：\n{table}\n\n"
    "请沿关系回答；引用某条关系时在句末使用其编号 [cN]。"
)
RETRIEVAL_GEN_USER_TEMPLATE = (
    "问题：{question}\n\n依据材料（编号表）：\n{table}\n\n"
    "请依据材料回答；引用材料时在句末使用编号 [cN]；材料不足时如实说明。"
)
RERANK_SYSTEM_PROMPT = "你是检索相关性打分器。只输出一个 0 到 1 之间的分数，不要输出其他内容。"


@dataclass(frozen=True, slots=True)
class ChainDeps:
    """三链链体的注入缝集合（组合根装配——生产＝各域公开读面＋gateway）。"""

    config_loader: d.ConfigLoader
    metrics_loader: d.MetricsLoader
    terms_loader: d.TermsLoader
    faq_matcher: d.FaqMatcher
    faq_searcher: d.FaqSearcher
    index_searcher_dual: d.IndexSearcherDual
    graph_searcher: d.GraphSearcher
    anchor_loader: d.FragmentAnchorLoader
    completer: d.Completer | None = None


def line(key: str, mark: str, text: str) -> d.SseEvent:
    """node_line 帧（节点内内容行——A1 帧 8：NLi；含「配置核对：…」行与
    「模型第 N 次调用」标注行；S 级过程行已归位 node 帧，本帧只承载内容行）。"""
    return d.SseEvent(d.FRAME_NODE_LINE, {"key": key, "mark": mark, "text": text})


def notice(text: str, *, level: str = "info") -> d.SseEvent:
    return d.SseEvent(d.FRAME_NOTICE, {"level": level, "text": text})


# ---------- 检索问答链 ----------


async def retrieval_chain(deps: ChainDeps, ctx: d.ChainContext) -> AsyncIterator[d.SseEvent]:
    """D2 当前生效配置驱动的检索瀑布链（N17→S0–S7→GEN→N17 收束＋兜底）。

    思考树叙事（P1-08c）：链内步进＝node 帧序——S 级过程行自 node_line 归位：
    执行级 node 帧 state 推进 process→finish（note 服务端组装）、跳过级 wait＋
    skipped:true（00 §5.3 ①——早停跳过/开关关跳过/S5 未启用直通同形）；node_line
    保留为节点内内容行（FAQ 扩检轮次行/FAQ 并入行/配置核对行/模型第 N 次调用
    标注行——A1 帧 8）。token 帧切片在全部树帧之后（不交错乱序）。
    """
    cfg = await deps.config_loader()
    question = ctx.question
    evidence: list[d.Evidence] = []
    rerank_calls = 0  # 精排逐条打分的模型调用数（GEN「模型第 N 次调用」序号源）

    # —— N17 检索问答（41 树执行节点——链体包装帧）——
    yield d.node_frame("N17", state=d.NODE_PROCESS, tag="代码 · 语义瀑布逐级推进",
                       note="检索问答链开跑——S0–S7 瀑布逐级推进")

    # —— S0 身份四要素（一次确认，后面各步直接沿用）——
    yield d.node_frame("S0", state=d.NODE_PROCESS)
    yield d.node_frame(
        "S0", state=d.NODE_FINISH,
        note=f"身份四要素确认：身份={ctx.actor_who} · 会话 run={ctx.run_id} · "
             "口径版本＝当前生效配置 · 权限＝系统管理员（阶段 1 单一角色）",
    )

    # —— S1 显式锚定（检索级，受第 1 级开关管辖——关＝跳过锚定直达，从 S3 继续）——
    skip_rest = False
    anchored = [
        c for c in ctx.assembly.candidates if str(c.note or "").startswith("@ 前门直取")
    ]
    if not cfg.order_levels[0]:
        yield d.node_skip(
            "S1", "第 1 级开关关——跳过锚定直达，从 S3 继续（开关语义对第 1 级同款适用）",
        )
    elif anchored:
        evidence.extend(_anchor_evidence(anchored))
        yield d.node_frame("S1", state=d.NODE_PROCESS)
        note = (
            "锚定命中：" + "、".join(f"「{c.name}」" for c in anchored)
            + "——直接点名命中，不走后面的模糊搜索"
        )
        if cfg.early_stop:
            skip_rest = True
            note += "（命中即停——S3~S5 跳过，装配层材料、资格审、权威回读照走）"
        yield d.node_frame("S1", state=d.NODE_FINISH, note=note)
    else:
        yield d.node_frame("S1", state=d.NODE_PROCESS)
        yield d.node_frame("S1", state=d.NODE_FINISH, note="无 @ 锚定——进入下一级")

    # —— S3 词表四级（确定性查表——台账完全一致才命中，确定性先于相似度）——
    if not skip_rest:
        if not cfg.order_levels[1]:
            yield d.node_skip("S3", "第 2 级开关关——跳过词表级，直接看下一级")
        else:
            ledger_hits = [
                c for c in ctx.assembly.candidates
                if c.kind in ("metric", "term") and not str(c.note or "").startswith("@ 前门直取")
            ]
            yield d.node_frame("S3", state=d.NODE_PROCESS)
            if ledger_hits:
                evidence.extend(_ledger_evidence(ledger_hits))
                note = (
                    "台账完全一致命中：" + "、".join(f"「{c.name}」" for c in ledger_hits)
                    + "——宁可查不到，不给「差不多」的结果"
                )
                if cfg.early_stop:
                    skip_rest = True
                    note += "（命中即停——S4~S5 跳过，装配层材料、资格审、权威回读照走）"
                yield d.node_frame("S3", state=d.NODE_FINISH, note=note)
            else:
                yield d.node_frame(
                    "S3", state=d.NODE_FINISH, note="台账精确未命中——进入双路召回",
                )
    else:
        yield d.node_skip("S3", "命中即停——本级跳过（装配层材料、资格审、权威回读照走）")

    # —— S4 双路召回（两路并发）＋合并＋前 N＋精排三档＋FAQ 路扩检 ——
    if not skip_rest:
        if not cfg.order_levels[2]:
            yield d.node_skip("S4", "第 3 级开关关——跳过双路召回")
        else:
            yield d.node_frame("S4", state=d.NODE_PROCESS)
            vector_hits, keyword_hits = await deps.index_searcher_dual(
                question, cfg.semantic_top_k, cfg.keyword_top_k
            )
            if cfg.merge == "rrf_rank":
                merged = d.rrf_merge(vector_hits, keyword_hits)
                merge_note = f"合并（rrf_rank · k={d.RRF_K} 固定推荐值）"
            else:
                merged = d.concat_merge(vector_hits, keyword_hits)
                merge_note = "合并（concat——谁排前用谁）"
            top = merged[: max(1, cfg.top_n)]
            evidence.extend(await _rerank_evidence(deps, cfg, top))
            if cfg.rerank in ("llm", "compound"):
                rerank_calls = len(top)
            yield d.node_frame(
                "S4", state=d.NODE_FINISH,
                note=f"双路召回：向量 {len(vector_hits)} 条＋关键词 {len(keyword_hits)} 条"
                     f" → {merge_note} → 前 {len(top)} 进精排（{cfg.rerank}）",
            )
            # FAQ 路扩检（检索动作级——受命中即停管辖；qa_behavior.faq_expand_rounds
            # 消费）——轮次行为 S4 节点内容行（node_line，A1 帧 8）。
            if not cfg.faq_direct_hit and ctx.assembly.faq_hit is None:
                faq_evidence, faq_events = await faq_leg_evidence(deps, ctx, cfg)
                evidence.extend(faq_evidence)
                for event in faq_events:
                    yield event
    else:
        yield d.node_skip("S4", "命中即停——本级跳过（装配层材料、资格审、权威回读照走）")

    # FAQ 精确命中并入（装配层材料——六路匹配器不受 D2 开关与早停管辖，
    # D2「两级管辖边界」：faq_direct_hit 关＝秒回闸关、走检索链出答案）
    if not cfg.faq_direct_hit and ctx.assembly.faq_hit is not None:
        evidence.extend(_faq_evidence([ctx.assembly.faq_hit]))
        yield line(
            "S4", "✓",
            f"FAQ 精确命中「{ctx.assembly.faq_hit.question}」并入检索证据"
            "（faq_direct_hit=false——秒回闸关）",
        )

    # —— S5 图扩展（未启用——直通跳过；过程记录写明，D2 合同值）——
    if skip_rest:
        yield d.node_skip("S5", "命中即停——本级跳过（装配层材料、资格审、权威回读照走）")
    else:
        yield d.node_skip(
            "S5",
            "S5 图扩展未启用——请求直接跳过、不花开销（将来接入知识图谱扩展时在这里开闸）",
        )

    # —— S6 资格裁决（不受开关与早停影响）——
    evidence = _with_refs(evidence)
    yield d.node_frame("S6", state=d.NODE_PROCESS)
    if len(evidence) > d.EVIDENCE_CAP:
        overflow = len(evidence) - d.EVIDENCE_CAP
        yield notice(
            f"候选 {len(evidence)} 支，仅送前 {d.EVIDENCE_CAP} 支进生成——另有 {overflow} 支未列出。"
        )
        evidence = evidence[: d.EVIDENCE_CAP]
    best = max((e.score for e in evidence), default=0.0)
    if not evidence or best < cfg.refuse_threshold:
        reason = (
            "证据为空" if not evidence
            else f"最高证据分 {best:.2f} 低于低分线 {cfg.refuse_threshold:.2f}"
        )
        yield d.node_frame(
            "S6", state=d.NODE_FINISH,
            note=f"拒答判定：{reason}——不硬答，走兜底（搜不到不报错、更不编造）",
        )
        yield d.node_frame(
            "N17", state=d.NODE_FINISH, note="资格审未过——兜底收场（搜不到不报错、更不编造）",
        )
        yield _config_check_line(cfg)
        async for event in _fallback_answer(deps, cfg, question):
            yield event
        return
    yield d.node_frame(
        "S6", state=d.NODE_FINISH,
        note=f"资格裁决：候选 {len(evidence)} 支（上限 {d.EVIDENCE_CAP}）· 最高证据分 {best:.2f}"
             "——多候选/缺参澄清在裁决层完成（有界循环），链内直连执行",
    )

    # —— S7 权威源回读（semantics 校验——不受开关与早停影响）——
    yield d.node_frame("S7", state=d.NODE_PROCESS)
    evidence, dropped_slots = await _authoritative_readback(deps, evidence, ctx.clarified_caliber)
    for slot in dropped_slots:
        yield notice(
            f"「{slot}」不在现行指标目录，不代答"
            "（S7 权威源回读拦下——编号敲错在这里拦）。",
            level="warning",
        )
    if not evidence:
        yield d.node_frame(
            "S7", state=d.NODE_FINISH, note="权威源回读后无可用证据——不硬答，走兜底（F33）",
        )
        yield d.node_frame(
            "N17", state=d.NODE_FINISH, note="权威源回读拦下全部证据——兜底收场（F33）",
        )
        yield _config_check_line(cfg)
        async for event in _fallback_answer(deps, cfg, question):
            yield event
        return
    yield d.node_frame(
        "S7", state=d.NODE_FINISH,
        note="权威源回读：指标台账核对通过"
             + (f" · 口径＝{ctx.clarified_caliber}" if ctx.clarified_caliber
                else " · 无指标口径挂载")
             + "——已正式发布且在现行目录才放行",
    )

    # —— GEN 限定作答＋引用登记（petro-main）＋ citation fail-closed ——
    ordinal = rerank_calls + 1
    yield d.node_frame("GEN", state=d.NODE_PROCESS, tag=f"模型第 {ordinal} 次调用")
    yield line(
        "GEN", "→",
        f"模型第 {ordinal} 次调用——限定作答（只按编号材料作答，不编造材料之外的事实）",
    )
    table = "\n".join(f"{e.ref}：[{e.kind}] {e.label}——{e.snippet}" for e in evidence)
    text, error = await _complete(
        deps,
        [
            {"role": "system", "content": GEN_SYSTEM_PROMPT},
            {"role": "user",
             "content": RETRIEVAL_GEN_USER_TEMPLATE.format(question=question, table=table)},
        ],
        CALLER_RETRIEVAL,
    )
    if error or text is None:
        yield d.node_frame(
            "GEN", state=d.NODE_FINISH, note="生成不可用——走兜底（搜不到不报错、更不编造）",
        )
        yield d.node_frame("N17", state=d.NODE_FINISH, note="生成不可用——兜底收场")
        yield _config_check_line(cfg)
        async for event in _fallback_answer(deps, cfg, question):
            yield event
        return
    by_ref = {e.ref: e for e in evidence}
    kept_refs, dropped = [], 0
    for ref in d.parse_refs(text):
        candidate = by_ref.get(ref)
        if candidate is None:
            dropped += 1
            text = d.strip_ref(text, ref)
            continue
        if candidate.fragment_id is not None:
            anchor = await deps.anchor_loader(candidate.fragment_id)
            if anchor is None or (candidate.report_id and anchor.report_id != candidate.report_id):
                # 伪造/失锚引用——拦截丢弃＋notice 留痕，绝不带病出帧。
                dropped += 1
                text = d.strip_ref(text, ref)
                continue
        kept_refs.append(ref)
    if dropped:
        yield notice(d.UNANCHORED_CITATION_NOTE.format(n=dropped), level="warning")
    text = d.rewrite_citations(text, by_ref, cfg.citation_format)
    citations = [d.citation_wire(by_ref[ref]) for ref in kept_refs]
    yield d.node_frame(
        "GEN", state=d.NODE_FINISH,
        note=f"生成完成——引用登记 {len(citations)} 条"
             + (f" · 拦截 {dropped} 条失锚/伪造引用（fail-closed）" if dropped else ""),
    )
    yield d.node_frame(
        "N17", state=d.NODE_FINISH,
        note=f"检索问答收束——证据 {len(evidence)} 支 · 引用 {len(citations)} 条逐条核验通过",
    )
    yield _config_check_line(cfg)
    async for event in _stream_answer(text, citations):
        yield event


def _config_check_line(cfg: d.RetrievalConfigFace) -> d.SseEvent:
    """出口「配置核对」行（D2 行为规则 6——展示面；只列真实消费的生效配置值，
    不发明「阈值未触发」类未核对结论）。"""
    levels = "、".join(
        name for name, on in zip(("锚定", "词表", "双路"), cfg.order_levels, strict=True) if on
    ) or "全关"
    return line(
        "N17", "·",
        f"配置核对：三级顺序＝{levels} · 命中即停＝{'开' if cfg.early_stop else '关'} · "
        f"topK＝{cfg.semantic_top_k}/{cfg.keyword_top_k} · 前 N＝{cfg.top_n} · "
        f"精排＝{cfg.rerank} · 引用格式＝{cfg.citation_format} · 兜底＝{cfg.fallback_strategy}",
    )


async def _rerank_evidence(
    deps: ChainDeps, cfg: d.RetrievalConfigFace,
    merged: list[tuple[d.IndexHitFace, float]],
) -> list[d.Evidence]:
    """精排三档（F34：只重排融合池前 N）→ 证据行。

    - fast：小而快的排序模型未选型（重排模型随 embedding 选型批——P1-04 收尾
      裁决①同批）——阶段 1 按融合序放行（差异登记）；
    - llm：主力大模型逐条打分（打 N 条就是 N 次模型调用）——解析失败按原顺序
      放行，不影响整条链路（W-F34-2）；
    - compound：0.6×模型分＋0.3×检索基础分＋0.1×来源分＋MMR λ=0.7。
    """
    if not merged:
        return []
    if cfg.rerank == "llm":
        ordered = await _llm_score_order(deps, merged)
    elif cfg.rerank == "compound":
        ordered = await _compound_order(deps, merged)
    else:
        ordered = list(merged)
    return [
        d.Evidence(
            ref="", kind="报告引用",
            label=(f"{hit.report} · {hit.section}" if hit.section else hit.report)
            or hit.fragment_id,
            locator={"report": hit.report, "section": hit.section,
                     "fragment_id": hit.fragment_id},
            snippet=hit.text or hit.snippet, score=hit.score, source=hit.leg,
            fragment_id=hit.fragment_id, report_id=hit.report_id,
        )
        for hit, _fused in ordered
    ]


async def _llm_score_order(
    deps: ChainDeps, merged: list[tuple[d.IndexHitFace, float]]
) -> list[tuple[d.IndexHitFace, float]]:
    """LLM 逐条打分排序——打 N 条就是 N 次模型调用，一条都不能少（F34②）；
    任一条解析失败＝整批按原顺序放行，不影响整条链路（W-F34-2 回退原序不炸链）。"""
    scored: list[tuple[d.IndexHitFace, float | None]] = []
    failed = False
    for hit, _fused in merged:
        score = await _llm_score(deps, hit.snippet)
        if score is None:
            failed = True
        scored.append((hit, score))
    if failed:
        return list(merged)
    ordered: list[tuple[d.IndexHitFace, float]] = [
        (hit, float(score or 0.0)) for hit, score in scored
    ]
    ordered.sort(key=lambda pair: pair[1], reverse=True)
    return ordered


async def _compound_order(
    deps: ChainDeps, merged: list[tuple[d.IndexHitFace, float]]
) -> list[tuple[d.IndexHitFace, float]]:
    """复合分排序（模型分解析失败用检索基础分代偿——不炸链）＋MMR 多样性挑选。"""
    ranked: list[tuple[d.IndexHitFace, float]] = []
    for hit, _fused in merged:
        model_score = await _llm_score(deps, hit.snippet)
        ranked.append((hit, d.compound_score(
            hit.score if model_score is None else model_score, hit.score, hit.leg
        )))
    ranked.sort(key=lambda pair: pair[1], reverse=True)
    return d.mmr_select(ranked, text_of=lambda hit: hit.snippet)


async def _llm_score(deps: ChainDeps, snippet: str) -> float | None:
    """单条相关性打分（petro-main；0–1 外/解析失败返回 None）。"""
    if deps.completer is None:
        return None
    try:
        completion = await deps.completer.complete(
            MAIN_ALIAS,
            [
                {"role": "system", "content": RERANK_SYSTEM_PROMPT},
                {"role": "user", "content": f"候选片段：{snippet}\n\n只输出相关度分数："},
            ],
            caller=CALLER_RERANK,
        )
        value = float(str(completion.content).strip().split()[0])
    except Exception:  # 打分失败按合同回退，不炸链
        return None
    return value if 0.0 <= value <= 1.0 else None


# ---------- FAQ 路扩检（消费 faq_expand_rounds——证据收集面） ----------


async def faq_leg_evidence(
    deps: ChainDeps, ctx: d.ChainContext, cfg: d.RetrievalConfigFace
) -> tuple[list[d.Evidence], list[d.SseEvent]]:
    """FAQ 路扩检（精确未命中时的迭代召回——qa_behavior.faq_expand_rounds 消费）
    ＋过程行：每轮候选数翻倍（1→2→4…），命中过线即停，最多 min(配置轮数, 5) 轮
    后停——不无限空转（W-F35-4 硬顶）。"""
    events: list[d.SseEvent] = []
    rounds = min(max(1, cfg.faq_expand_rounds), d.FAQ_EXPAND_HARD_CAP)
    top_k = 1
    for round_no in range(1, rounds + 1):
        hits = await deps.faq_searcher(ctx.question, top_k)
        good = [h for h in hits if h.score >= d.FAQ_EXPAND_FLOOR]
        if good:
            events.append(line(
                "S4", "✓",
                f"FAQ 路扩检第 {round_no} 轮（候选数 ×{top_k}）："
                f"命中 {len(good)} 条相似问——并入检索证据",
            ))
            return _faq_evidence(good), events
        events.append(line(
            "S4", "○",
            f"FAQ 路扩检第 {round_no} 轮（候选数 ×{top_k}）：召回不足——候选数翻倍续检",
        ))
        top_k *= 2
    events.append(line(
        "S4", "○",
        f"FAQ 路扩检 {rounds} 轮未命中——检索执行硬顶 {d.FAQ_EXPAND_HARD_CAP} 轮后停，不无限空转",
    ))
    return [], events


def _faq_evidence(hits: list[d.FaqHitFace]) -> list[d.Evidence]:
    return [
        d.Evidence(
            ref="", kind="台账条目", label=f"FAQ「{hit.question}」",
            locator={"section": "常见问题库", "faq_id": hit.entry_id},
            snippet=hit.answer[:80], score=1.0, source="faq",
        )
        for hit in hits
    ]


# ---------- 证据与生成共用件 ----------


def _anchor_evidence(candidates: list[d.Candidate]) -> list[d.Evidence]:
    """@ 前门直取候选 → 证据（指标卡/术语→台账条目；FAQ→FAQ 条目）。"""
    out: list[d.Evidence] = []
    for candidate in candidates:
        if candidate.kind in ("metric", "term"):
            out.append(d.Evidence(
                ref="", kind="台账条目", label=f"台账「{candidate.name}」",
                locator={"section": "指标台账" if candidate.kind == "metric" else "术语台账"},
                snippet=f"@ 锚定直取：{candidate.name}", score=1.0, source="anchor",
                metric_slot=candidate.name if candidate.kind == "metric" else None,
            ))
        elif candidate.kind == "faq":
            out.append(d.Evidence(
                ref="", kind="台账条目", label=f"FAQ「{candidate.name}」",
                locator={"section": "常见问题库"}, snippet=f"@ 锚定直取：{candidate.name}",
                score=1.0, source="anchor",
            ))
    return out


def _ledger_evidence(candidates: list[d.Candidate]) -> list[d.Evidence]:
    """台账精确命中候选 → 证据（S3 确定性查表）。"""
    return [
        d.Evidence(
            ref="", kind="台账条目", label=f"台账「{candidate.name}」",
            locator={"section": "指标台账" if candidate.kind == "metric" else "术语台账"},
            snippet=f"台账精确命中：{candidate.name}", score=1.0, source="ledger",
            metric_slot=candidate.name if candidate.kind == "metric" else None,
        )
        for candidate in candidates
    ]


def _with_refs(evidence: list[d.Evidence]) -> list[d.Evidence]:
    """按序分配引用别名 c1..cN（送生成前定稿——编号表即 fail-closed 校验基准）。"""
    return [
        replace(evidence, ref=f"c{index}")
        for index, evidence in enumerate(evidence, start=1)
    ]


async def _authoritative_readback(
    deps: ChainDeps, evidence: list[d.Evidence], clarified_caliber: str | None,
) -> tuple[list[d.Evidence], list[str]]:
    """S7 权威源回读（semantics 校验）：指标证据现场回指标台账核对——不在现行
    指标目录的拦下不代答；口径经澄清锁定的校验其在账口径支。"""
    if not any(e.metric_slot is not None for e in evidence):
        return evidence, []
    metrics = {m.slot_name: m for m in await deps.metrics_loader()}
    kept: list[d.Evidence] = []
    dropped: list[str] = []
    for item in evidence:
        if item.metric_slot is None:
            kept.append(item)
            continue
        metric = metrics.get(item.metric_slot)
        if metric is None:
            dropped.append(item.metric_slot)
            continue
        caliber = clarified_caliber or metric.default_caliber
        if caliber is not None and metric.calibers:
            valid = {str(c.get("name", "")) for c in metric.calibers}
            if caliber not in valid:
                # 澄清口径不在账——按默认口径回读（不猜账外口径）。
                caliber = metric.default_caliber
        kept.append(replace(item, locator=(
            {**item.locator, "caliber": caliber} if caliber else item.locator
        )))
    return kept, dropped


async def _complete(
    deps: ChainDeps, messages: list[dict[str, str]], caller: str
) -> tuple[str | None, bool]:
    """B6 出口调用（completer 未装配/调用失败 → (None, True)——调用方走兜底不炸链）。"""
    if deps.completer is None:
        return None, True
    try:
        completion = await deps.completer.complete(MAIN_ALIAS, messages, caller=caller)
        text = str(completion.content).strip()
    except Exception:  # 生成失败走兜底（搜不到不报错、更不编造）
        LOGGER.exception("chat 链内 LLM 生成失败（caller=%s）——走兜底", caller)
        return None, True
    return (text or None), not text


async def _fallback_answer(
    deps: ChainDeps, cfg: d.RetrievalConfigFace, question: str
) -> AsyncIterator[d.SseEvent]:
    """兜底两策（D2 兜底策略卡——fixed 原样回复固定文案；free 自由回答＋标注）。"""
    if cfg.fallback_strategy == "fixed":
        yield d.SseEvent(d.FRAME_ANSWER, {
            "kind": "alert", "alert_type": "warning", "text": cfg.fallback_text,
        })
        return
    text, _error = await _complete(deps, [
        {"role": "system", "content": GEN_FALLBACK_SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ], CALLER_FALLBACK)
    body = (text or cfg.fallback_text) + d.FREE_ANSWER_TAG
    async for event in _stream_answer(body, []):
        yield event


async def _stream_answer(
    text: str, citations: list[dict[str, Any]]
) -> AsyncIterator[d.SseEvent]:
    """token 流式（切片下发）→ citation 帧（出处展开）→ answer 帧收口。"""
    for chunk in d.token_chunks(text):
        yield d.SseEvent(d.FRAME_TOKEN, {"delta": chunk})
    for citation in citations:
        yield d.SseEvent(d.FRAME_CITATION, citation)
    yield d.SseEvent(d.FRAME_ANSWER, {"kind": "text", "text": text, "citations": citations})


# ---------- FAQ 秒回链 ----------


async def faq_direct_chain(deps: ChainDeps, ctx: d.ChainContext) -> AsyncIterator[d.SseEvent]:
    """FAQ 秒回（B3——只消费已发布条目；命中即秒回、不走报告检索）。

    思考树叙事（P1-08c）：N18 预制问答节点 process→finish（秒回零内部步进——
    命中判定与直出同拍完成）；answer kind=text＋no_model=true（「本条命中 FAQ
    直出——未调用模型」标注，A1 合同冻结）；citation＝FAQ 条目出处（faq 块族——
    citation kind 四值枚举无 FAQ 专值，落台账条目族如实标注）。
    """
    yield d.node_frame("N18", state=d.NODE_PROCESS, tag="代码 · 秒回闸",
                       note="预制问答——标准问匹配（只消费已发布条目）")
    hit = ctx.assembly.faq_hit or await deps.faq_matcher(ctx.question)
    if hit is None:
        cfg = await deps.config_loader()
        yield d.node_frame(
            "N18", state=d.NODE_FINISH,
            note="FAQ 精确命中在执行前失效（索引竞变）——按兜底策略处理，不硬答",
        )
        yield notice(
            "FAQ 精确命中在执行前失效（索引竞变）——按兜底策略处理，不硬答。",
            level="warning",
        )
        yield d.SseEvent(d.FRAME_ANSWER, {
            "kind": "alert", "alert_type": "warning", "text": cfg.fallback_text,
        })
        return
    cfg = await deps.config_loader()
    evidence = _faq_evidence([hit])
    item = replace(evidence[0], ref="c1")
    marker = f"[{item.label}]" if cfg.citation_format == "page" else "[c1]"
    text = f"{hit.answer}\n\n{marker}"
    yield d.node_frame(
        "N18", state=d.NODE_FINISH,
        note=f"命中「{hit.question}」——策展答案直出（no_model——未调用模型）",
    )
    yield d.SseEvent(d.FRAME_CITATION, d.citation_wire(item))
    yield d.SseEvent(d.FRAME_ANSWER, {
        "kind": "text", "text": text, "no_model": True,
        "citations": [d.citation_wire(item)],
    })


# ---------- 图谱问答链 ----------


async def graph_chain(deps: ChainDeps, ctx: d.ChainContext) -> AsyncIterator[d.SseEvent]:
    """图谱问答链（B5——沿图遍历不翻全文；边出处回证据；生成带图谱出处 citation）。

    思考树叙事（P1-08c）：N13 关系追溯节点开跑→遍历/校验内容行（node_line）→
    GEN 限定作答→N13 收束。装配层 graph 缝已扫（候选共池）；链内取邻域边证据
    ——每条边的依据闸留存片段（source_chunk_id）经 fail-closed 校验：锚不上片段
    台账的边引用拦截丢弃＋notice 留痕，绝不带病出帧。
    """
    yield d.node_frame("N13", state=d.NODE_PROCESS, tag="代码 · 沿图走",
                       note="关系追溯——图谱邻域遍历（沿图走一步，不翻全文）")
    cfg = await deps.config_loader()
    hits = ctx.assembly.graph_hits or list(await deps.graph_searcher(ctx.question))
    if not hits:
        yield d.node_frame(
            "N13", state=d.NODE_FINISH,
            note="图谱缝未命中任何关系边——不硬答，走兜底（F33）",
        )
        async for event in _fallback_answer(deps, cfg, ctx.question):
            yield event
        return
    yield line(
        "N13", "✓",
        f"图谱邻域遍历：命中 {len(hits)} 条关系边——沿图走一步，不翻全文"
        f"（边出处回证据 {sum(1 for h in hits if h.source_chunk_id)} 条）",
    )
    evidence: list[d.Evidence] = []
    dropped = 0
    for hit in hits[: d.EVIDENCE_CAP]:
        item = d.Evidence(
            ref="", kind="图谱", label=f"图谱 {hit.entity} {hit.relation}",
            locator={"section": "关系图谱"}, snippet=hit.evidence or "",
            score=1.0, source="graph",
            fragment_id=hit.source_chunk_id or None, report_id=hit.source_report_id or None,
        )
        if item.fragment_id is not None:
            anchor = await deps.anchor_loader(item.fragment_id)
            if anchor is None:
                dropped += 1
                continue
            item = replace(item, locator={
                "section": "关系图谱", "report": anchor.report,
                "fragment_id": anchor.fragment_id,
            })
        evidence.append(item)
    if dropped:
        yield notice(d.UNANCHORED_CITATION_NOTE.format(n=dropped), level="warning")
    evidence = _with_refs(evidence)
    if not evidence:
        yield d.node_frame(
            "N13", state=d.NODE_FINISH,
            note="图谱边引用全部失锚被拦——无可用证据，走兜底",
        )
        async for event in _fallback_answer(deps, cfg, ctx.question):
            yield event
        return
    ordinal = 1  # 图谱链无精排打分——生成即首次模型调用
    yield d.node_frame("GEN", state=d.NODE_PROCESS, tag=f"模型第 {ordinal} 次调用")
    yield line(
        "GEN", "→",
        f"模型第 {ordinal} 次调用——沿关系材料限定作答（引用某条关系时在句末使用其编号）",
    )
    table = "\n".join(
        f"{e.ref}：{e.label}" + (f"（依据：{e.snippet}）" if e.snippet else "")
        for e in evidence
    )
    text, error = await _complete(deps, [
        {"role": "system", "content": GEN_SYSTEM_PROMPT},
        {"role": "user",
         "content": GRAPH_GEN_USER_TEMPLATE.format(question=ctx.question, table=table)},
    ], CALLER_GRAPH)
    if error or text is None:
        yield d.node_frame(
            "GEN", state=d.NODE_FINISH, note="生成不可用——走兜底（搜不到不报错、更不编造）",
        )
        yield d.node_frame("N13", state=d.NODE_FINISH, note="生成不可用——兜底收场")
        async for event in _fallback_answer(deps, cfg, ctx.question):
            yield event
        return
    by_ref = {e.ref: e for e in evidence}
    kept_refs = [ref for ref in d.parse_refs(text) if ref in by_ref]
    text = d.rewrite_citations(text, by_ref, cfg.citation_format)
    citations = [d.citation_wire(by_ref[ref]) for ref in kept_refs]
    yield d.node_frame(
        "GEN", state=d.NODE_FINISH,
        note=f"生成完成——引用登记 {len(citations)} 条"
             + (f" · 拦截 {dropped} 条失锚引用（fail-closed）" if dropped else ""),
    )
    yield d.node_frame(
        "N13", state=d.NODE_FINISH,
        note=f"关系追溯收束——关系边证据 {len(evidence)} 条 · 引用逐条核验通过",
    )
    async for event in _stream_answer(text, citations):
        yield event
