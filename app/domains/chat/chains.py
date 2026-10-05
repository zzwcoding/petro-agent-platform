"""domains.chat.chains —— 四链链体（P1-08b 链体＋P1-08c 树叙事步进＋M-06 问数链）。

问数链（M-06 状态机六站链——全景树 N7.1–N7.6＋安检三闸，F7 票 94 注记）：
  N7.1 意图识别（复用 D2 slots 确定性校验——三要素齐不齐查表即判，零模型调用；
  时间窗「最近/近期」无量化＝缺参反问 askback 时间窗三选一）→ N7.2 语义检索
  （选表＝agg 星型读模型注册面——99 §2.12/D6 star_model，join 结构即合同值）→
  N7.3 SQL 生成（模板化——注册指标声明口径先行，零自由生成；台账行未绑定计量
  列＝降级解释链如实标注，不冒充审定口径）→ N7.4 执行前安检三闸：N7.4a 新鲜度
  （消费 M-05a 水位读面——超窗改绑最近可用日＋标注、全窗未出数＝拒答，照 E2
  T-1 语义）/ N7.4b 行级权限（M-01 两步缝——with_row_filter 预埋恒真形状，
  物理注入在执行缝）/ N7.4c 外表审批（问句点名外表＝越集——interrupt 挂起出
  审批卡，approve 续跑/reject 零重试，A1 端点 5 合同形状）→ N7.5 查询执行
  （只读＋行级注入已并——tool_call 帧留痕）→ N7.6 结果核验（行数/值域——0 行
  如实回报不编数）→ 血缘卡五要素（F13：口径/来源表/过滤条件含权限注入行/数据
  截至批次/收口注记——合同值逐行）＋数据证据 citation＋answer kind=table。
  审批挂起＝链内哨兵（chain_approval_signal），service._run_chain 拦截转
  interrupt_approval 挂起——恢复时整节点重跑（F7 节点幂等），N7.4c 以
  extable_decision 判别批准续跑/驳回终局。
  降级接续（W-AUX③）：出不了数三路（N7.1 无注册声明/N7.4a 全窗未出数/N7.6
  零行）自动接续检索问答链（_continue_with_retrieval——同模块函数级复用，
  检索帧紧随六站帧混排，answer 帧恒最后），答案正文前置如实标注
  DATA_CHAIN_FALLBACK_NOTE（检索结果非权威数值）；接续链仍无果才双重如实
  拒答（原拒答话术收场）。
  辅助检索＋旁注解读（W-AUX②·停线裁决 C）：N7.5 只读执行行数>0 后——原问句
  复用检索链双路召回缝（index_searcher_dual 同缝零新缝）取小窗口辅助片段
  （AUX_TOP_K=4），片段＋表格数据进 gateway.complete（caller=chat.query.narrate
  ——chat.query.rewrite 计费留痕惯例；提示词三约束：数值一律以表格为准（片段
  数值不采）/引用标注 cN/不得虚构）生成解读段，以 notice 帧并列呈现（血缘帧后、
  answer 帧前——answer 恒最后；零新帧型、answer 载荷零新增键，P2-03 状态标注
  先例）；片段引用别名自 c3 起（表卡数据证据 c1/c2 已占不撞号），fail-closed
  照 GEN 收口同款（伪造/失锚引用拦截剥除）；检索无片段/生成不可用 → 纯表格
  自然降级零报错。

检索问答链（D2 当前生效配置驱动全链——S 级语义照 F58/W-F21）：
  N17 检索问答（树执行节点）→ S0 身份四要素（一次确认）→ S1 显式锚定（受第 1 级
  开关管辖）→ S3 词表四级（台账精确）→ S4 双路召回（向量 topK1＋trigram topK2
  并发）→ 合并（rrf_rank k=60 固定推荐值 / concat）→ 前 N → 精排三档（fast 融合
  序放行 / llm 逐条打分 / compound 0.6/0.3/0.1＋MMR λ=0.7）→ FAQ 路（直出关——
  并入检索，扩检轮数消费）→ S5 图扩展（未启用——直通跳过）→ S6 资格裁决（生成
  窗分池——D2 v0.4：报告类证据上限 4 支＋台账类材料上限 2 支、两池互不占位，
  台账类＝装配层一等材料满分档〔source∈faq/anchor/ledger〕，各池内超出的截断
  并标「另有 N 支未列出」；refuse_threshold 拒答判定；低分带双重重评 P1F-06：
  0.30≤best<refuse_threshold
  不直接兜底——第一道放宽窗口重评（纯代码：topK 放宽×2＋父块家族随池回捞重算
  best，过闸照常生成不弹帧、帧注记记原分/重评分）；仍低则第二道 LLM 改写双句
  评分（仅此刻一次 gateway.complete，caller=chat.query.rewrite；同尺余弦给原句/
  优化句各算一次）——优化句过闸且澄清额度在→rewrite 澄清帧（subtype 透传，
  选是＝优化句上下文生成、选否/不选＝诚实兜底）；额度已用完→自动按优化句作答
  ＋「已按优化问法检索」标注（写死路径，不弹第二帧）；优化句也低/改写失败→诚实
  兜底＋S6 注记记三值。证据空/<0.30/用户坚持原问法（skip_rescore）→直接兜底，
  拒答克制回归）→ S7 权威源回读（指标台账核对）→ GEN 限定
  作答（petro-main）→ citation fail-closed（伪造/失锚引用拦截丢弃，绝不带病出帧）
  → N17 收束。早停（D2「命中即停」开关，v0.3 收窄语义）：仅 S1 显式锚定命中即
  跳过下级检索级（S3~S5 跳过——身份确认非意图猜测；S3/S4/S5 各出归因 skip
  注记——每级一帧）；S3 词表级命中不停下级——台账命中只作增强材料随装配进生成，报告
  检索照跑；关＝逐级全跑；S0/S2/S6/S7 不受早停影响。词条卡一等材料（P1F-02）：
  装配层 term_cards 常驻随行，生成步
  以「术语台账收录：…」材料块并入 user 消息（在证据支材料之前），定义先行规则
  在 GEN 系统提示。状态标注兜底通知（P1F-08——生成端软失败的确定性兜底）：生成
  收口判定——材料词条卡携届满/禁用类状态标注、答案正文提及该词条却未带出标注串
  → token 流前补一条 warning 级 notice「注：〈词条名〉状态标注——〈标注串原文〉」
  （不改写已流式正文——通知帧并列呈现，answer 帧合同位次不动；限语境类标注不在
  兜底范围——防过度通知）；GEN 系统提示另携禁推算约束（缺数据不得加减推算补位、
  不得虚声明材料覆盖范围）。兜底两策：检索全空/低于低分线 → fixed 文案或 free＋「未依据
  报告库」标注；fixed 前置诚实判定（P1F-02）——装配词条卡/指标卡/FAQ 命中任一
  在场 → 「台账有收录：…；报告库未检索到相关内容」，六路全空才落配置文案。
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
from datetime import date, timedelta
from typing import Any

from app.domains.chat import domain as d
from app.infra.clock import now

LOGGER = logging.getLogger("domains.chat")

# B6 别名与 caller 归因（D1 别名 petro-main＝生成/打分默认出口；caller 落 gateway
# 记账——D5 观测按 caller 聚合）。
MAIN_ALIAS = "petro-main"
CALLER_RETRIEVAL = "chat.retrieval.answer"
CALLER_RERANK = "chat.retrieval.rerank"
CALLER_GRAPH = "chat.graph.answer"
CALLER_FALLBACK = "chat.retrieval.fallback"
# 低分带第二道问句改写（P1F-06——caller 自由字符串惯例不封闭，gateway 记账按
# caller 归因聚合，费用统计可溯源）。
CALLER_REWRITE = "chat.query.rewrite"
# 问数链旁注解读段生成（W-AUX②·停线裁决 C——主路权威数出数后以检索辅助＋叙述
# 生成补解读段，呈现照既有 notice 机制并列呈现（P2-03 状态标注先例）——零合同
# 变更：无新帧型、answer 帧载荷零新增键）。
CALLER_NARRATE = "chat.query.narrate"
AUX_TOP_K = 4  # 辅助检索小窗口（票面定值——旁注材料不抢主路权威数）
AUX_REF_START = 3  # 辅助片段引用别名起始号（表卡数据证据 c1/c2 已占——不撞号）

GEN_SYSTEM_PROMPT = (
    "你是油田数据问答平台的回答助手。只依据给出的编号材料回答，"
    "不编造材料之外的事实。引用材料是硬性要求：每条依据都必须在句末标注其编号，"
    "格式形如 [c1]（半角方括号＋编号）；材料不足以回答时如实说明。"
    "问句围绕某术语且意在释义时——先给定义（状态标注必须原样带出），再给数据指引；"
    "判断不了则定义与数据指引并列给出；不得忽略已收录的词条材料。"
    "材料未直接给出某数值时，不得用其他数值加减推算补位——应如实说明该数据缺失；"
    "对材料覆盖范围不得作未核实的声明——说「材料未披露」前须确认材料中确无该内容。"
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
# 低分带第二道问句改写提示词（P1F-06——措辞可微调、语义须覆盖：去修饰保语义/
# 输出检索优化问法/只回问法本身）。
REWRITE_SYSTEM_PROMPT = (
    "你是检索问句改写器。把用户问句改写成适合报告库检索的问法："
    "去掉修饰性、口语化的词语，保留原问句的语义与问题核心，"
    "输出检索优化问法。只回问法本身，不要输出任何解释、引号或其他内容。"
)
# 问数链旁注解读段提示词（W-AUX②——票面规定三约束：数值一律以表格为准（片段
# 数值不采）／引用标注 cN／不得虚构）。
NARRATE_SYSTEM_PROMPT = (
    "你是油田数据问答平台的表格解读撰写器。权威数据表格已由平台模板化查询出数，"
    "你只写一段简短解读，帮用户读懂这张表。三条硬约束："
    "一、数值一律以表格为准——检索片段中的数值一律不采信、不得写入解读；"
    "二、提及某个检索片段的内容时，在句末标注其编号，格式形如 [c1]（半角方括号＋编号）；"
    "三、不得虚构表格与片段之外的任何事实——表格与片段都不足以支撑的判断直接不写。"
)
NARRATE_USER_TEMPLATE = (
    "用户问句：{question}\n\n"
    "权威数据表格（平台模板化查询出数——数值唯一依据）：\n{table_text}\n\n"
    "报告库辅助片段（编号表——仅作背景参考，片段中的数值一律不采）：\n{fragment_table}\n\n"
    "请写一段两三句话的解读：先用表格数值直接回答用户问句，再补一句片段提供的背景；"
    "提及片段时在句末标注其编号 [cN]；表格与片段都不支撑的判断不写。"
)
# 状态标注兜底通知判别串（P1F-08——只认届满/禁用类：term_expiry 单源展示串族
# 「<ISO>（已届满）」「—（已禁用）」；限语境类标注不在兜底范围——躺井题已由
# 生成端原样带出工作，兜底只在缺失时抬手，防过度通知）。
ANNOTATION_GUARD_MARKERS = ("已届满", "已禁用")


@dataclass(frozen=True, slots=True)
class ChainDeps:
    """四链链体的注入缝集合（组合根装配——生产＝各域公开读面＋gateway＋
    问数执行缝/水位读缝）。"""

    config_loader: d.ConfigLoader
    metrics_loader: d.MetricsLoader
    terms_loader: d.TermsLoader
    faq_matcher: d.FaqMatcher
    faq_searcher: d.FaqSearcher
    index_searcher_dual: d.IndexSearcherDual
    graph_searcher: d.GraphSearcher
    anchor_loader: d.FragmentAnchorLoader
    completer: d.Completer | None = None
    # 问数链缝（M-06——缺省未装配＝链内诚实降级，不冒充出数）：
    # query_executor＝agg 星型读模型只读执行（生产＝chat.QueryStore——99 §3 chat
    # 读声明唯一消费方）；waterline_loader＝汇总层水位（生产＝M-05a 水位读面，
    # E2 T-1 判定随面携入）。
    query_executor: d.QueryExecutor | None = None
    waterline_loader: d.WaterlineLoader | None = None


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
    extra_model_calls = 0  # 链内额外模型调用（低分带改写——P1F-06，同入 GEN 序号）
    rescored_answer = False  # 额度已用完自动按优化句作答——答案标注开关（P1F-06）

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
    # 词表级命中不停下级（P1F-03／D2 v0.3 收窄）：台账命中只作增强材料（词条卡
    # 走 P1F-02 装配层，不依赖本级跳过），S4/S5 照跑；本级 skip 决策＝第 2 级
    # 开关关或 S1 锚定早停（帧对称——P-005 修复拍审查疑点①：被跳也出归因帧，
    # 保「每级一帧」惯例，与 S4/S5 同款归因 S1）。
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
                yield d.node_frame(
                    "S3", state=d.NODE_FINISH,
                    note="台账完全一致命中：" + "、".join(f"「{c.name}」" for c in ledger_hits)
                         + "——宁可查不到，不给「差不多」的结果"
                         "（词表级命中不停下级——词条材料随装配进生成，S4/S5 照跑）",
                )
            else:
                yield d.node_frame(
                    "S3", state=d.NODE_FINISH, note="台账精确未命中——进入双路召回",
                )
    else:
        yield d.node_skip(
            "S3", "S1 锚定命中即停——本级跳过（装配层材料、资格审、权威回读照走）",
        )

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
            # FAQ 路扩检（检索动作级——受 S1 锚定早停管辖；qa_behavior.faq_expand_rounds
            # 消费）——轮次行为 S4 节点内容行（node_line，A1 帧 8）。
            if not cfg.faq_direct_hit and ctx.assembly.faq_hit is None:
                faq_evidence, faq_events = await faq_leg_evidence(deps, ctx, cfg)
                evidence.extend(faq_evidence)
                for event in faq_events:
                    yield event
    else:
        yield d.node_skip(
            "S4", "S1 锚定命中即停——本级跳过（装配层材料、资格审、权威回读照走）",
        )

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
        yield d.node_skip(
            "S5", "S1 锚定命中即停——本级跳过（装配层材料、资格审、权威回读照走）",
        )
    else:
        yield d.node_skip(
            "S5",
            "S5 图扩展未启用——请求直接跳过、不花开销（将来接入知识图谱扩展时在这里开闸）",
        )

    # —— S6 资格裁决（不受开关与早停影响；生成窗分池 D2 v0.4；低分带双重
    # 重评——P1F-06）——
    evidence = _with_refs(evidence)
    yield d.node_frame("S6", state=d.NODE_PROCESS)
    evidence, cap_notices = _cap_evidence(evidence)
    for cap_text in cap_notices:
        yield notice(cap_text)
    best = max((e.score for e in evidence), default=0.0)
    rescored_note: str | None = None  # 低分带重评过闸的 S6 收束注记（None＝未触发）
    if not evidence or best < cfg.refuse_threshold:
        # 拒答克制回归（P1F-06）：证据空／<0.30（低分带下沿之外）／用户坚持原问法
        # （rewrite 选否回流的 skip_rescore）——不重评，直接兜底。
        if (
            not evidence
            or not d.in_rescore_band(best, cfg.refuse_threshold)
            or ctx.skip_rescore
        ):
            reason = (
                "证据为空" if not evidence
                else f"最高证据分 {best:.2f} 低于低分线 {cfg.refuse_threshold:.2f}"
                     + ("（用户坚持原问法——低分带重评跳过）" if ctx.skip_rescore else "")
            )
            yield d.node_frame(
                "S6", state=d.NODE_FINISH,
                note=f"拒答判定：{reason}——不硬答，走兜底（搜不到不报错、更不编造）",
            )
            yield d.node_frame(
                "N17", state=d.NODE_FINISH, note="资格审未过——兜底收场（搜不到不报错、更不编造）",
            )
            yield _config_check_line(cfg)
            async for event in _fallback_answer(deps, cfg, question, ctx.assembly):
                yield event
            return
        # —— 第一道：放宽窗口重评（纯代码——topK 放宽＋父块家族随池回捞重算 best；
        # 过闸照常生成、不弹帧）——
        relaxed_rows, relaxed_best = await _relaxed_rescore(deps, cfg, question)
        yield line(
            "S6", "○",
            f"低分带重评（第一道·放宽窗口）：原分 {best:.2f} → 放宽重评分 {relaxed_best:.2f}"
            f"（topK ×{d.RESCORE_RELAX_FACTOR}——同父块兄弟子块随池回捞）",
        )
        if relaxed_best >= cfg.refuse_threshold:
            # 过闸截断同分池口径（D2 v0.4 生成窗分池——两池互不占位）。
            evidence, cap_notices = _cap_evidence(_with_refs(relaxed_rows))
            for cap_text in cap_notices:
                yield notice(cap_text)
            original_best = best
            best = relaxed_best
            rescored_note = (
                f"资格裁决（放宽重评过闸）：原分 {original_best:.2f} → 重评分 {best:.2f}"
                f" ≥ 低分线 {cfg.refuse_threshold:.2f}"
                f"（生成窗分池——报告类上限 {d.EVIDENCE_CAP}＋台账类上限 "
                f"{d.LEDGER_EVIDENCE_CAP}，两池互不占位）——过闸照常生成（不弹帧）"
            )
        else:
            # —— 第二道：LLM 改写＋双句评分（仅此刻一次 LLM 调用；同一把尺——
            # 与 S4 相同的余弦检索腿分给原句/优化句各算一次）——
            optimized = await _rewrite_question(deps, question)
            extra_model_calls += 1
            if optimized is None:
                yield d.node_frame(
                    "S6", state=d.NODE_FINISH,
                    note=f"拒答判定：低分带重评未过闸——原句 {best:.2f} · 放宽重评 "
                         f"{relaxed_best:.2f} · 优化句缺（改写不可用），低于低分线 "
                         f"{cfg.refuse_threshold:.2f}——不硬答，走兜底（搜不到不报错、更不编造）",
                )
                yield d.node_frame(
                    "N17", state=d.NODE_FINISH,
                    note="资格审未过——兜底收场（搜不到不报错、更不编造）",
                )
                yield _config_check_line(cfg)
                async for event in _fallback_answer(deps, cfg, question, ctx.assembly):
                    yield event
                return
            opt_rows, opt_best = await _relaxed_rescore(deps, cfg, optimized)
            yield line(
                "S6", "○",
                f"低分带重评（第二道·LLM 改写）：优化问法「{optimized}」——"
                f"原句 {best:.2f} · 放宽重评 {relaxed_best:.2f} · 优化句 {opt_best:.2f}",
            )
            if opt_best >= cfg.refuse_threshold:
                if ctx.clarify_available:
                    # 澄清额度在——弹 rewrite 澄清帧（interrupt 挂起，交出控制权等人）：
                    # 选是＝优化句上下文走生成；选否/不选＝诚实兜底。
                    yield d.node_frame(
                        "S6", state=d.NODE_FINISH,
                        note=f"改写过闸（优化句 {opt_best:.2f} ≥ 低分线 "
                             f"{cfg.refuse_threshold:.2f}）——澄清额度在，弹改写澄清帧"
                             "（按优化问法作答／坚持原问法——两跳到终态）",
                    )
                    yield d.chain_clarify_signal(
                        d.build_rewrite_clarify(optimized, frame_id=f"clarify-{ctx.run_id}"),
                        subtype="rewrite",
                        optimized_question=optimized,
                    )
                    return
                # 额度已用完（N5 已弹过一次）——不弹第二帧：自动按优化句作答＋
                # 答案标注（写死路径）。
                # 过闸截断同分池口径（D2 v0.4 生成窗分池——两池互不占位）。
                evidence, cap_notices = _cap_evidence(_with_refs(opt_rows))
                for cap_text in cap_notices:
                    yield notice(cap_text)
                original_best = best
                best = opt_best
                question = optimized
                rescored_answer = True
                rescored_note = (
                    f"资格裁决（改写过闸·澄清额度已用完——自动按优化问法作答）："
                    f"原句 {original_best:.2f} · 放宽重评 {relaxed_best:.2f} · "
                    f"优化句 {best:.2f} ≥ 低分线 {cfg.refuse_threshold:.2f}"
                    f"（生成窗分池——报告类上限 {d.EVIDENCE_CAP}＋台账类上限 "
                    f"{d.LEDGER_EVIDENCE_CAP}，两池互不占位）"
                    "——不弹第二帧（澄清帧有界循环）"
                )
            else:
                yield d.node_frame(
                    "S6", state=d.NODE_FINISH,
                    note=f"拒答判定：低分带重评未过闸——原句 {best:.2f} · 放宽重评 "
                         f"{relaxed_best:.2f} · 优化句 {opt_best:.2f}，均低于低分线 "
                         f"{cfg.refuse_threshold:.2f}——不硬答，走兜底（搜不到不报错、更不编造）",
                )
                yield d.node_frame(
                    "N17", state=d.NODE_FINISH,
                    note="资格审未过——兜底收场（搜不到不报错、更不编造）",
                )
                yield _config_check_line(cfg)
                async for event in _fallback_answer(deps, cfg, question, ctx.assembly):
                    yield event
                return
    if rescored_note is not None:
        yield d.node_frame("S6", state=d.NODE_FINISH, note=rescored_note)
    else:
        yield d.node_frame(
            "S6", state=d.NODE_FINISH,
            note=f"资格裁决：候选 {len(evidence)} 支（生成窗分池——报告类上限 "
                 f"{d.EVIDENCE_CAP}＋台账类上限 {d.LEDGER_EVIDENCE_CAP}，两池互不"
                 f"占位）· 最高证据分 {best:.2f}"
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
        async for event in _fallback_answer(deps, cfg, question, ctx.assembly):
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
    ordinal = rerank_calls + extra_model_calls + 1
    yield d.node_frame("GEN", state=d.NODE_PROCESS, tag=f"模型第 {ordinal} 次调用")
    yield line(
        "GEN", "→",
        f"模型第 {ordinal} 次调用——限定作答（只按编号材料作答，不编造材料之外的事实）",
    )
    table = "\n".join(f"{e.ref}：[{e.kind}] {e.label}——{e.snippet}" for e in evidence)
    # 词条卡材料块（P1F-02：定义先行的一等材料——在证据支材料之前并入生成窗）
    term_block = _term_card_material(ctx.assembly.term_cards)
    gen_user = (
        f"{term_block}\n\n{RETRIEVAL_GEN_USER_TEMPLATE.format(question=question, table=table)}"
        if term_block
        else RETRIEVAL_GEN_USER_TEMPLATE.format(question=question, table=table)
    )
    text, error = await _complete(
        deps,
        [
            {"role": "system", "content": GEN_SYSTEM_PROMPT},
            {"role": "user", "content": gen_user},
        ],
        CALLER_RETRIEVAL,
    )
    if error or text is None:
        yield d.node_frame(
            "GEN", state=d.NODE_FINISH, note="生成不可用——走兜底（搜不到不报错、更不编造）",
        )
        yield d.node_frame("N17", state=d.NODE_FINISH, note="生成不可用——兜底收场")
        yield _config_check_line(cfg)
        async for event in _fallback_answer(deps, cfg, question, ctx.assembly):
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
    if rescored_answer:
        # 额度已用完的自动路径（P1F-06）——答案标注「已按优化问法检索」（写死）。
        text = text + d.RESCORED_ANSWER_TAG
        yield line(
            "GEN", "✓",
            "已按优化问法检索作答（澄清额度已用完——自动路径，不弹第二帧）",
        )
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
    # 状态标注兜底通知（P1F-08）：届满/禁用类标注生成端未带出的确定性兜底——
    # 在 token 流前并列补一条 warning notice（不改写正文，answer 帧位次不动）。
    for event in _status_annotation_notices(ctx.assembly.term_cards, text):
        yield event
    if ctx.data_fallback_note:
        # 问数链降级接续（W-AUX③）：答案正文前置如实标注——在流式切片前改文，
        # token 流与答案帧同文（RESCORED_ANSWER_TAG 同款改法，不破帧形状）。
        text = f"{ctx.data_fallback_note}\n{text}"
    async for event in _stream_answer(text, citations):
        yield event


def _config_check_line(cfg: d.RetrievalConfigFace) -> d.SseEvent:
    """出口「配置核对」行（D2 行为规则 6——展示面；只列真实消费的生效配置值，
    不发明「阈值未触发」类未核对结论）。早停表述按 P1F-03 收窄语义明义：
    仅 @ 锚定级命中即跳，S3 词表级命中永不停下级。生成窗分池上限（D2 v0.4
    合同值——报告类 4＋台账类 2）与 S6 注记同口径在列。"""
    levels = "、".join(
        name for name, on in zip(("锚定", "词表", "双路"), cfg.order_levels, strict=True) if on
    ) or "全关"
    early_stop = "开（@锚定级命中即跳）" if cfg.early_stop else "关（逐级全跑）"
    return line(
        "N17", "·",
        f"配置核对：三级顺序＝{levels} · 早停＝{early_stop}，S3 命中不停下级 · "
        f"topK＝{cfg.semantic_top_k}/{cfg.keyword_top_k} · 前 N＝{cfg.top_n} · "
        f"生成窗＝报告类 {d.EVIDENCE_CAP}＋台账类 {d.LEDGER_EVIDENCE_CAP} · "
        f"精排＝{cfg.rerank} · 引用格式＝{cfg.citation_format} · 兜底＝{cfg.fallback_strategy}",
    )


async def _rerank_evidence(
    deps: ChainDeps, cfg: d.RetrievalConfigFace,
    merged: list[tuple[d.IndexHitFace, float]],
) -> list[d.Evidence]:
    """精排三档（F34：只重排融合池前 N）→ 证据行。

    - fast：排序模型无可用服务（P1-11 选型探测 2026-10-02：MiniMax 两域名
      /v1/rerank 均 404、智谱/方舟线路亦无 rerank 端点——证据记票面）——
      按融合序放行（差异登记「无可用服务」；服务出现时本档换真重排）；
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
    return _index_evidence_rows(ordered)


def _index_evidence_rows(
    ordered: list[tuple[d.IndexHitFace, float]],
) -> list[d.Evidence]:
    """报告索引命中 → 证据行（kind=报告引用；Evidence.score 恒原始腿分——精排
    只重排不改分，S4 与低分带重评同尺）。"""
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


def _report_diversify(report: list[d.Evidence], cap: int) -> list[d.Evidence]:
    """报告池多样性（G-06 检索质量第一刀——通用多文档机制，非题面适配）。

    多报告语料下向量腿会饱和：A 报告片段对任意油田问句普遍高分（Q3 探针实证
    0.85~0.95），按分直取会整窗挤满单报告、其余报告相关片段全出局（五题检索
    miss 共因）。此处窗口内**同报告至多 2 支**：按报告分组轮询各取首支，余量再
    按原序补齐——只改入选构成、不改相对序，不做任何语义判断（分池 v0.4 同族
    思路：台账/报告互不占位 → 报告内多报告互不挤占）。
    """
    if len(report) <= cap:
        return report
    per_report_cap = max(1, cap // 2)
    by_report: dict[str, list[d.Evidence]] = {}
    order: list[str] = []
    for e in report:
        key = e.report_id or e.report or "?"
        if key not in by_report:
            by_report[key] = []
            order.append(key)
        if len(by_report[key]) < per_report_cap:
            by_report[key].append(e)
    picked: list[d.Evidence] = []
    seen: set[int] = set()
    while len(picked) < cap:
        progressed = False
        for key in order:
            if by_report[key]:
                e = by_report[key].pop(0)
                picked.append(e)
                seen.add(id(e))
                progressed = True
                if len(picked) >= cap:
                    break
        if not progressed:
            break
    for e in report:
        if len(picked) >= cap:
            break
        if id(e) not in seen:
            picked.append(e)
            seen.add(id(e))
    return picked


def _cap_evidence(evidence: list[d.Evidence]) -> tuple[list[d.Evidence], list[str]]:
    """S6 送生成上限截断（D2 v0.4 生成窗分池——两池互不占位）。

    按材料 source 分类：台账类（source∈LEDGER_EVIDENCE_SOURCES＝faq/anchor/
    ledger——装配层一等材料满分档：词条卡/指标卡/@ 锚定直取/FAQ 精确命中并入）
    上限 LEDGER_EVIDENCE_CAP；其余＝报告类（S4/S5 检索片段证据）上限
    EVIDENCE_CAP。各池内原排序不动、各自截各自上限，送生成序列保持分池前全局
    序（只丢不重排）。返回截断后行与溢出提示行——每池超出各自标「另有 N 支
    未列出」（两池都有超出时两行，固定报告类在前），notice 由调用方按序发。
    """
    ledger = [e for e in evidence if e.source in d.LEDGER_EVIDENCE_SOURCES]
    report_all = [e for e in evidence if e.source not in d.LEDGER_EVIDENCE_SOURCES]
    report = _report_diversify(report_all, d.EVIDENCE_CAP)
    kept_report = report[: d.EVIDENCE_CAP]
    kept_ledger = ledger[: d.LEDGER_EVIDENCE_CAP]
    kept_ids = {id(e) for e in [*kept_report, *kept_ledger]}
    notices: list[str] = []
    if len(report_all) > len(kept_report):
        notices.append(
            f"报告类证据 {len(report_all)} 支，仅送前 {d.EVIDENCE_CAP} 支进生成"
            f"——另有 {len(report_all) - len(kept_report)} 支未列出。"
        )
    if len(ledger) > len(kept_ledger):
        notices.append(
            f"台账类材料 {len(ledger)} 支，仅送前 {d.LEDGER_EVIDENCE_CAP} 支进生成"
            f"——另有 {len(ledger) - len(kept_ledger)} 支未列出。"
        )
    return [e for e in evidence if id(e) in kept_ids], notices


async def _relaxed_rescore(
    deps: ChainDeps, cfg: d.RetrievalConfigFace, question: str,
) -> tuple[list[d.Evidence], float]:
    """低分带第一道——放宽窗口重评（P1F-06，纯代码零模型调用）。

    topK 放宽（max(semantic_top_k, keyword_top_k)×RESCORE_RELAX_FACTOR，封顶
    RESCORE_RELAX_MAX_TOPK）重走双路召回，按 cfg.merge 同策合并——放宽后同父块
    家族（同报告兄弟子块）随池回捞，best 分在放宽池上重算。照链内既有读面
    （index_searcher_dual，与 S4 同尺：证据分恒原始腿分），不私加缝；重评路不
    触发精排打分（llm/compound 档的逐条模型分不在此刻——链内唯一额外模型调用
    留给第二道问句改写）。"""
    relaxed_k = min(
        max(cfg.semantic_top_k, cfg.keyword_top_k) * d.RESCORE_RELAX_FACTOR,
        d.RESCORE_RELAX_MAX_TOPK,
    )
    vector, keyword = await deps.index_searcher_dual(question, relaxed_k, relaxed_k)
    merged = (
        d.rrf_merge(vector, keyword) if cfg.merge == "rrf_rank"
        else d.concat_merge(vector, keyword)
    )
    rows = _index_evidence_rows(merged)
    return rows, max((row.score for row in rows), default=0.0)


async def _rewrite_question(deps: ChainDeps, question: str) -> str | None:
    """低分带第二道——LLM 问句改写（P1F-06）：仅此刻一次 LLM 调用，caller 归因
    chat.query.rewrite（gateway 记账溯源）。提示词＝去修饰保语义/输出检索优化
    问法/只回问法本身；调用失败/空输出/解析坏（首行剥引号后为空）返回 None——
    调用方诚实兜底，不炸链。"""
    text, error = await _complete(deps, [
        {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
        {"role": "user", "content": f"原问句：{question}\n\n只输出检索优化问法："},
    ], CALLER_REWRITE)
    if error or text is None:
        return None
    first_line = text.strip().splitlines()[0].strip() if text.strip() else ""
    cleaned = first_line.strip("\"“”「」『』'").strip()
    return cleaned or None


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


def _term_card_material(term_cards: list[d.TermCard]) -> str:
    """词条卡材料块（P1F-02——「术语台账收录：〈term〉〈type〉〈def〉（状态标注）」
    逐卡一行；空卡清单返回空串＝本块不进生成窗）。状态标注缺省时不挂空括号。"""
    lines = [
        f"术语台账收录：{card.term} {card.type} {card.def_text}"
        + (f"（{card.status_note}）" if card.status_note else "")
        for card in term_cards
    ]
    return "\n".join(lines)


def _annotation_segments(status_note: str) -> list[str]:
    """标注串拆语义承载段（滤单字符占位段——「—」是禁用词的空期占位，单查无义）：
    「2026-06-30（已届满）」→ [「2026-06-30」,「已届满」]；「—（已禁用）」→
    [「已禁用」]。"""
    parts = status_note.replace("）", "（").split("（")
    return [part.strip() for part in parts if len(part.strip()) >= 2]


def _free_occurrence(
    answer_text: str, needle: str, occupied: list[tuple[int, int]],
) -> int:
    """needle 在答案中的首个未占用出现位（字符偏移；无空闲出现 → -1）。

    R4b 按卡隔离判定的基元：occupied 是先到卡已消费的标注出现位区间，同显式
    串双卡时甲卡消费过的位置不得再豁免乙卡。"""
    start = 0
    while True:
        pos = answer_text.find(needle, start)
        if pos < 0:
            return -1
        end = pos + len(needle)
        if not any(pos < e and s < end for s, e in occupied):
            return pos
        start = pos + 1


def _annotation_carried(
    status_note: str, answer_text: str, occupied: list[tuple[int, int]],
) -> tuple[bool, list[tuple[int, int]]]:
    """逐卡判定该卡标注是否被带出（R4b——每卡独立判定，先到卡消费的出现位不
    豁免后卡）：标注串原文整体在场，或全部语义承载段各自在场（括注次序无关
    ——「已届满（2026-06-30）」倒装同样算带出），且各出现位均不落在先前卡的
    occupied 区间内。判定成立时一并返回本卡消费区间，由调用方沿卡序传递。"""
    pos = _free_occurrence(answer_text, status_note, occupied)
    if pos >= 0:
        return True, [(pos, pos + len(status_note))]
    segments = _annotation_segments(status_note)
    if not segments:
        return False, []
    spans: list[tuple[int, int]] = []
    for seg in segments:
        pos = _free_occurrence(answer_text, seg, occupied)
        if pos < 0:
            return False, []
        spans.append((pos, pos + len(seg)))
    return True, spans


def _status_annotation_notices(
    term_cards: list[d.TermCard], answer_text: str,
) -> list[d.SseEvent]:
    """状态标注兜底通知（P1F-08——生成端软失败的确定性兜底，主修）。

    判定（只认届满/禁用类——ANNOTATION_GUARD_MARKERS）：词条卡 status_note 携
    判别串、答案正文提及该词条、但未带出标注串（原文与全部语义承载段均不在）
    → 每卡一条 warning 级 notice：「注：〈词条名〉状态标注——〈标注串原文〉」。
    带出判定逐卡隔离（R4b——审查发现：同显式串双卡时答案级一次判定会让甲卡
    带出豁免乙卡、漏掉乙的通知）：答案中一处标注出现只豁免先到的卡，occupied
    沿卡序消费——甲卡带出不构成乙卡豁免，乙仍须自携出现位才算带出。
    不改写已流式答案正文——notice 帧在 token 流前并列呈现（链缝合同：answer 帧
    必须最后出现）。free/fixed 兜底分支不接（非检索链生成路径）。
    """
    out: list[d.SseEvent] = []
    occupied: list[tuple[int, int]] = []
    for card in term_cards:
        note = card.status_note
        if not note or not any(marker in note for marker in ANNOTATION_GUARD_MARKERS):
            continue
        if card.term not in answer_text:
            continue
        carried, spans = _annotation_carried(note, answer_text, occupied)
        if carried:
            occupied.extend(spans)
            continue
        out.append(notice(f"注：{card.term}状态标注——{note}", level="warning"))
    return out


def _ledger_entries(assembly: d.AssemblyResult, *, include_faq: bool = True) -> list[str]:
    """兜底诚实文案的台账收录清单（P1F-02——词条名＋定义/口径摘要＋状态标注，
    多卡逐条列出；六路全空返回空清单＝仍走 D2 fallback_text 原样）。

    include_faq=False 供 N18 内联兜底（P-004 修复拍③）——FAQ 链走到拒答时
    faq_hit 从未命中或已失效（索引竞变），复述其内容不可靠，只计台账卡。
    """
    entries: list[str] = []
    for term_card in assembly.term_cards:
        note = f"，状态：{term_card.status_note}" if term_card.status_note else ""
        entries.append(f"「{term_card.term}」{term_card.def_text}{note}")
    for metric_card in assembly.metric_cards:
        calibers = "／".join(
            str(c.get("name", "")) for c in metric_card.calibers if c.get("name")
        )
        caliber_part = f"，口径：{calibers}" if calibers else ""
        note = f"，状态：{metric_card.status_note}" if metric_card.status_note else ""
        entries.append(f"「{metric_card.slot_name}」{caliber_part}{note}")
    if include_faq and assembly.faq_hit is not None:
        entries.append(
            f"FAQ「{assembly.faq_hit.question}」{assembly.faq_hit.answer[:80]}"
        )
    return entries


def _ledger_alert_text(entries: list[str]) -> str:
    """「台账有收录」收场话术（fixed 兜底与 N18 内联兜底共用一句——单源）。"""
    return f"台账有收录：{'；'.join(entries)}；报告库未检索到相关内容。"


async def _fallback_answer(
    deps: ChainDeps, cfg: d.RetrievalConfigFace, question: str, assembly: d.AssemblyResult,
) -> AsyncIterator[d.SseEvent]:
    """兜底两策（D2 兜底策略卡——fixed 原样回复固定文案；free 自由回答＋标注）。

    fixed 分支前置判定（P1F-02 兜底诚实性）：装配词条卡/指标卡/FAQ 命中任一在
    场 → 不说「没有找到」，改报「台账有收录：…；报告库未检索到相关内容」——
    台账有据不谎称全无；六路全空才落 cfg.fallback_text 原样（D2 配置值不动）。
    free 分支不加判定（维持原语义）。
    """
    if cfg.fallback_strategy == "fixed":
        entries = _ledger_entries(assembly)
        if entries:
            yield d.SseEvent(d.FRAME_ANSWER, {
                "kind": "alert", "alert_type": "warning",
                "text": _ledger_alert_text(entries),
            })
            return
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


# ---------- 问数链（状态机六站链——M-06：N7.1–N7.6＋安检三闸） ----------

def _metric_card_for_plan(ctx: d.ChainContext) -> tuple[str, str, str] | None:
    """装配层指标卡 → 模板可用声明（slot/name/def）——未绑定计量列＝None（降级）。"""
    for card in ctx.assembly.metric_cards:
        if d.resolve_measure(card.slot_name) is not None:
            def_text = "；".join(
                str(c.get("name", "")) for c in card.calibers if c.get("name")
            ) or ""
            return card.slot_name, card.name, def_text
    return None


async def query_chain(deps: ChainDeps, ctx: d.ChainContext) -> AsyncIterator[d.SseEvent]:
    """状态机六站链（M-06——用户数据型问题：模板装配出数，主路零模型调用）。

    站序与节点行照全景树 N7 节＋A1 行为规则 3（链内节点行内容照抄各源合同值）：
    F7 三要素校验/F14 LIMIT 收口与外表审批/F13 血缘五要素/E2 新鲜度 T-1 语义/
    M-01 行级注入两步缝。审批挂起走链内哨兵（connection 不占着——恢复整节点
    重跑，F7 节点幂等）。
    辅助检索＋旁注解读（W-AUX②·停线裁决 C）：出数（行数>0）后原问句复用双路
    召回缝取辅助片段，gateway.complete（caller=chat.query.narrate）生成解读段
    以 notice 帧并列呈现（主路唯一模型调用）；降级接续（W-AUX③）：出不了数的
    三路（N7.1 无注册声明／N7.4a 全窗未出数/N7.6 零行）自动接续检索问答链
    （_continue_with_retrieval，同模块函数级复用），答案正文前置如实标注（非
    权威数值）；接续链仍无果才双重如实拒答（原拒答话术收场）。
    """
    question = ctx.question
    today = _today()

    # —— N7.1 意图识别（复用 D2 slots 确定性校验——零模型调用，缺参才反问）——
    yield d.node_frame("N7.1", state=d.NODE_PROCESS, tag="校验三要素 · 零模型调用",
                       note="意图识别——复用意图裁决阶段解析结果，仅做缺参校验（F7 票 94 注记）")
    declared = _metric_card_for_plan(ctx)
    if declared is None:
        # 降级解释链（不冒充审定口径）：装配层无可绑定计量列的注册指标——
        # 不自由生成 SQL、不出数；接续检索问答链（报告库辅助）消二选一漏答。
        yield d.node_frame(
            "N7.1", state=d.NODE_FINISH,
            note="指标槽位未命中可出数的注册声明（模板只认绑定 agg 计量列的指标）"
                 "——降级解释链：不自由生成 SQL（不冒充审定口径）"
                 "——接续检索问答链（报告库检索结果作辅助）",
        )
        yield d.node_frame("N7.2", state=d.NODE_WAIT, skipped=True,
                           note="降级——不选表、不生成、不执行")
        yield notice(
            "该问法没有命中可出数的注册指标声明——平台不做自由生成冒充审定口径。"
            "出路：在指标台账（C1）登记可绑定计量列的指标，或走语义修订提案池（C2）补登记后再问。",
            level="warning",
        )
        async for event in _continue_with_retrieval(deps, ctx, refusal_answer={
            "kind": "alert", "alert_type": "warning",
            "text": (
                "未命中注册指标声明——不冒充审定口径出数。"
                "请先在指标台账登记（或走 C2 提案），再来查。"
            ),
        }):
            yield event
        return
    metric_slot, metric_name, def_text = declared
    status, window = d.parse_time_window(question, today=today)
    if status == "vague":
        # 缺参反问（askback 时间窗三选一照抄——缺的是用户事实，无默认项）。
        yield d.node_frame(
            "N7.1", state=d.NODE_FINISH,
            note="时间窗缺参：「最近/近期」为模糊时间词，无法确定时间窗（近 3 天/近 30 天/"
                 "本月的数完全不同——不猜数）——澄清反问挂起",
        )
        yield d.chain_clarify_signal(
            d.build_askback_time_clarify(frame_id=f"clarify-{ctx.run_id}"),
            subtype=d.MISSING_SUBTYPE,
            optimized_question="",
        )
        return
    if status == "missing" or window is None:
        window = d.default_time_window(today=today)  # 无显式时间——默认窗＋标注
    plan = d.build_query_plan(
        metric_slot=metric_slot, metric_name=metric_name, question=question,
        window=window, today=today, actor=ctx.actor_who,
    )
    yield d.node_frame(
        "N7.1", state=d.NODE_FINISH,
        note=f"三要素齐：指标＝{metric_slot}（台账「{metric_name}」）· "
             f"时间＝{plan.window.label} · 条数＝{plan.limit_effective}"
             + ("（默认窗——问句无显式时间）" if plan.window.is_default else "")
             + "——确定性校验通过，未额外调用模型",
    )

    # —— N7.2 语义检索（选表＝agg 星型读模型注册面——join 结构即合同值）——
    yield d.node_frame("N7.2", state=d.NODE_PROCESS, tag="选表",
                       note="语义检索——注册读模型选表（白名单判据）")
    yield line("N7.2", "✓", f"选表：{d.STAR_SOURCE_NOTE}")
    if plan.external_tables:
        yield line(
            "N7.2", "○",
            "外表 " + "、".join(plan.external_tables) + " 不在本轮选表命中集"
            "——交下一站执行前表引用比对（F14）",
        )
    yield d.node_frame(
        "N7.2", state=d.NODE_FINISH,
        note="选表落定：agg 星型三表（99 册 §2.12 注册——事实表组合 PK 挂两维 PK 连）",
    )

    # —— N7.3 SQL 生成（模板化——注册指标声明口径先行，零自由生成）——
    yield d.node_frame("N7.3", state=d.NODE_PROCESS, tag="模板装配 · 零模型调用",
                       note="SQL 生成——模板化（注册指标声明口径先行）")
    yield line("N7.3", "→", "模板装配 SQL：\n" + d.render_plan_sql(plan))
    yield d.node_frame(
        "N7.3", state=d.NODE_FINISH,
        note=f"模板装配完成（{plan.metric_slot} → agg.{plan.measure_column}，"
             f"LIMIT {plan.limit_effective}"
             + (f"——问句显式 {plan.limit_requested}" if plan.limit_requested is not None
                else "——没写补默认 50")
             + "）——零自由生成",
    )

    # —— N7.4 执行前安检（三闸：新鲜度/行级/外表——F14）——
    yield d.node_frame("N7.4", state=d.NODE_PROCESS, tag="执行前安检 · 三闸",
                       note="执行前安检——新鲜度（N7.4a）→ 行级权限（N7.4b）→ 外表审批（N7.4c）")

    # N7.4a 新鲜度闸（消费 M-05a 水位读面——超窗改绑/全窗未出数拒答，照 E2 T-1 语义）
    yield d.node_frame("N7.4a", state=d.NODE_PROCESS, tag="出数前比对批次水位")
    waterline = await deps.waterline_loader() if deps.waterline_loader is not None else None
    if waterline is None:
        yield d.node_frame("N7.4a", state=d.NODE_FINISH, note=d.FRESHNESS_UNKNOWN_NOTE)
    elif plan.window.start > waterline.data_date:
        # 查询窗整体在水位之后——无已出数数据：闸拦停（不返回空数冒充）；
        # 接续检索问答链（W-AUX③——不再以拒答收场，消二选一漏答）。
        tag = waterline.tag
        yield d.node_frame(
            "N7.4a", state=d.NODE_FINISH,
            note=f"比对：查询窗「{plan.window.label}」整体晚于数据水位 "
                 f"{waterline.data_date.isoformat()}（{tag}）——拦停，不出空数"
                 "——接续检索问答链（报告库检索结果作辅助）",
        )
        yield d.node_frame(
            "N7.4", state=d.NODE_FINISH,
            note="新鲜度闸拦停——问数不出数，接续检索问答链（报告库辅助，非权威数值）",
        )
        reject_text = d.FRESHNESS_REJECT_TEMPLATE.format(
            data_date=waterline.data_date.isoformat(), tag=tag, label=plan.window.label,
        )
        async for event in _continue_with_retrieval(
            deps, ctx,
            refusal_notice=reject_text,
            refusal_answer={"kind": "alert", "alert_type": "warning", "text": reject_text},
        ):
            yield event
        return
    elif plan.window.end - timedelta(days=1) > waterline.data_date:
        # 窗口后半段未出数——改绑最近可用日＋标注（照 E2「落后 N 天 · 超期」语义）。
        plan = d.clamp_plan_window(plan, d.TimeWindow(
            start=plan.window.start, end=waterline.data_date + timedelta(days=1),
            label=plan.window.label, is_default=plan.window.is_default,
        ))
        yield d.node_frame(
            "N7.4a", state=d.NODE_FINISH,
            note=d.FRESHNESS_CLAMP_NOTE_TEMPLATE.format(
                data_date=waterline.data_date.isoformat(), tag=waterline.tag,
            ),
        )
    else:
        yield d.node_frame(
            "N7.4a", state=d.NODE_FINISH,
            note=f"比对通过：数据水位 {waterline.data_date.isoformat()} 覆盖查询窗"
                 f"（承诺 {waterline.promise} · {waterline.tag}）",
        )

    # N7.4b 行级权限闸（预埋恒真形状——物理注入在执行缝两步走，M-01/M-02 同款）
    yield d.node_frame("N7.4b", state=d.NODE_PROCESS, tag="权限层自动改写")
    yield d.node_frame(
        "N7.4b", state=d.NODE_FINISH,
        note=f"行级权限：{d.ROW_FILTER_PREEMBEDDED_NOTE}"
             f"（actor＝{ctx.actor_who} · 落点 agg.fct_daily_metering——谓词随执行并语句）",
    )

    # N7.4c 外表审批闸（越集比对——interrupt 挂起；恢复整节点重跑，F7 节点幂等）
    yield d.node_frame("N7.4c", state=d.NODE_PROCESS, tag="表引用比对")
    if plan.external_tables:
        ext_names = "、".join(plan.external_tables)
        if ctx.extable_decision == "approve":
            yield d.node_frame(
                "N7.4c", state=d.NODE_FINISH,
                note=f"表引用比对：外表 {ext_names} 已批准（审批留痕单号 "
                     f"{ctx.extable_approval_id or '—'}，可回溯）——只读续跑，生产库未动",
            )
        elif ctx.extable_decision == "reject":
            yield d.node_frame(
                "N7.4c", state=d.NODE_FINISH, tag="权限拒绝 · 零重试",
                note=f"✗ 不予执行，且不自动改写 SQL 重试（外表 {ext_names}——权限拒答终局）",
            )
            yield d.node_frame("N7.4", state=d.NODE_FINISH, note="外表审批驳回——链路终局（零重试）")
            yield notice(
                d.EXTABLE_REJECT_NOTICE_TEMPLATE.format(table=ext_names), level="warning",
            )
            yield d.SseEvent(d.FRAME_ANSWER, {
                "kind": "extable",
                "decision": "rejected",
                "reject_notice": d.EXTABLE_REJECT_NOTICE_TEMPLATE.format(table=ext_names),
                **({"audit_no": ctx.extable_approval_id} if ctx.extable_approval_id else {}),
            })
            return
        else:
            # 首跑越集——审批 interrupt 挂起（模型与流程都无权自批，A1 行为规则 7）。
            approval_id = f"APP-{_today():%m%d}-{ctx.run_id.removeprefix('run-')[:6]}"
            payload = d.build_extable_approval(plan, run_id=ctx.run_id, approval_id=approval_id)
            yield d.node_frame(
                "N7.4c", state=d.NODE_FINISH, tag="暂停 · 等待人工处理",
                note=f"✓ 执行前表引用比对：SQL 引用选表命中集之外的外表 {ext_names}"
                     " → 已触发人工审批（模型与流程都无权自批）",
            )
            yield d.node_frame(
                "N7.4", state=d.NODE_FINISH, note="外表审批挂起（interrupt——连接不占着）",
            )
            yield d.chain_approval_signal(payload)
            return
    else:
        yield d.node_frame(
            "N7.4c", state=d.NODE_FINISH,
            note="表引用比对：查询仅引用选表命中集内三表——越集未触发，不设审批放行",
        )
    yield d.node_frame("N7.4", state=d.NODE_FINISH, note="执行前安检三闸走完——放行执行")

    # —— N7.5 查询执行（只读＋行级注入已并——tool_call 帧留痕）——
    yield d.node_frame("N7.5", state=d.NODE_PROCESS, tag="只读执行")
    if deps.query_executor is None:
        # 执行缝未装配＝不冒充出数（诚实降级——生产组合根装配 QueryStore）。
        yield d.node_frame(
            "N7.5", state=d.NODE_FINISH, note="查询执行缝未装配——不出数（不假跑）",
        )
        yield d.SseEvent(d.FRAME_ANSWER, {
            "kind": "alert", "alert_type": "warning",
            "text": "查询执行通道未装配——本次不出数。请稍后再试或联系平台运维。",
        })
        return
    result = await deps.query_executor(plan)
    yield d.SseEvent(d.FRAME_TOOL_CALL, {
        "name": "sql_query.readonly",
        "args_summary": (
            f"时间＝{plan.window.label} · 指标＝{plan.metric_slot} · "
            f"条数＝{plan.limit_effective}"
        ),
        "tables_hit": list(d.STAR_TABLES),
        "rows_returned": len(result.rows),
        "readonly": True,
    })
    yield d.node_frame(
        "N7.5", state=d.NODE_FINISH,
        note=f"只读账号执行完成（行级注入谓词 {result.row_filter_predicates} 条已并语句；"
             f"生产库未动）——返回 {len(result.rows)} 行",
    )

    # —— N7.6 结果核验（行数/值域——0 行如实回报不编数）——
    yield d.node_frame("N7.6", state=d.NODE_PROCESS, tag="行数 / 值域 / 口径")
    if not result.rows:
        yield d.node_frame(
            "N7.6", state=d.NODE_FINISH,
            note=f"结果核验：0 行（时间窗「{plan.window.label}」内查无数据）——如实回报，"
                 "不编数——接续检索问答链（报告库检索结果作辅助）",
        )
        yield line(
            "N7.6", "→",
            "接续检索问答链——报告库检索结果仅作辅助参考（非权威数值，零报错降级）",
        )
        async for event in _continue_with_retrieval(deps, ctx, refusal_answer={
            "kind": "alert", "alert_type": "info",
            "text": (
                f"查询执行成功但无数据行（时间窗「{plan.window.label}」内查无数据）"
                "——如实回报，不编数。"
            ),
        }):
            yield event
        return
    yield d.node_frame(
        "N7.6", state=d.NODE_FINISH,
        note=f"结果核验通过：{len(result.rows)} 行 · 列 {len(result.columns)} 列"
             f"（LIMIT {plan.limit_effective} 收口内）",
    )

    # —— 血缘卡五要素（F13——合同值逐行）＋数据证据出处＋答案表卡 ——
    caliber_line = d.lineage_caliber_line(
        plan, def_text=def_text, clarified_caliber=ctx.clarified_caliber,
    )
    watermark_line = d.lineage_watermark_line(
        data_date=waterline.data_date if waterline else None,
        promise=waterline.promise if waterline else None,
        tag=waterline.tag if waterline else None,
        batch_id=result.batch_id,
    )
    lineage = [
        {"key": d.LINEAGE_KEY_CALIBER, "value": caliber_line},
        {"key": d.LINEAGE_KEY_SOURCE, "value": d.lineage_source_line()},
        {"key": d.LINEAGE_KEY_FILTER, "value": d.lineage_filter_line(plan)},
        {"key": d.LINEAGE_KEY_PERMISSION, "value": d.ROW_FILTER_PREEMBEDDED_NOTE},
        {"key": d.LINEAGE_KEY_WATERMARK, "value": watermark_line},
        {"key": d.LINEAGE_KEY_CLOSING, "value": d.lineage_closing_line(plan)},
    ]
    yield d.SseEvent(d.FRAME_LINEAGE, {"items": lineage})
    table = {
        "columns": [{"dataIndex": key, "title": title} for key, title in result.columns],
        "rows": result.rows,
    }
    if plan.external_tables and ctx.extable_decision == "approve":
        # 批准支出数（A1 answer kind=extable——核对表格＋审批留痕；外表联查列产出
        # 随 D3 白名单数据面批——本轮按批准引用＋白名单内主查询出数，不伪造外表列；
        # R2：answer 撤合同外 lineage 键——血缘卡由上方专帧承载，不重复内嵌）。
        yield notice(
            "外表联查列产出待数据 Owner 白名单数据面接线——本轮按批准引用＋白名单内"
            "主查询出数（不伪造外表列）。",
            level="info",
        )
        yield d.SseEvent(d.FRAME_ANSWER, {
            "kind": "extable",
            "decision": "approved",
            "table": table,
            "footnote": d.EXTABLE_APPROVED_FOOTNOTE_TEMPLATE.format(
                approval_id=ctx.extable_approval_id or "—",
            ),
            **({"audit_no": ctx.extable_approval_id} if ctx.extable_approval_id else {}),
        })
        return
    # —— 辅助检索＋旁注解读段（W-AUX②·停线裁决 C——notice 帧并列呈现）——
    cfg = await deps.config_loader()
    aux = await _aux_retrieval_fragments(deps, cfg, question)
    if aux:
        yield line(
            "N7.6", "→",
            f"辅助检索：报告库双路召回 {len(aux)} 支片段——旁注解读材料"
            "（片段数值不采，数值一律以表格为准）",
        )
        narration, cited, dropped = await _narrate_table(deps, question, table, aux)
        if narration is not None:
            for fragment in cited:
                yield d.SseEvent(d.FRAME_CITATION, d.citation_wire(fragment))
            if dropped:
                yield notice(
                    d.UNANCHORED_CITATION_NOTE.format(n=dropped), level="warning",
                )
            yield notice(narration, level="info")
    sample = _sample_row_line(result.rows[0])
    citations = [
        d.citation_wire(d.Evidence(
            ref="c1", kind="数据证据", label="出处 1 · 日产计量表样本行",
            locator={"section": "agg.fct_daily_metering", "sample": sample},
            snippet=sample, score=1.0, source="ledger",
        )),
        d.citation_wire(d.Evidence(
            ref="c2", kind="数据证据", label="出处 2 · 连表合法性（agg 星型模型注册）",
            locator={
                "section": "Join 白名单",
                "tables": "fct_daily_metering ⋈ dim_well/dim_date（PK 连）",
                "source": "99 册 §2.12/D6 star_model",
            },
            snippet="事实表组合 PK 挂两维 PK 连——join 结构即注册合同值",
            score=1.0, source="ledger",
        )),
    ]
    yield d.SseEvent(d.FRAME_ANSWER, {
        "kind": "table",
        **table,
        "source_note": "数据来源：agg 汇总层「日产计量表」（数据面管道直写 · 批次水位随血缘卡④）",
        "citations": citations,
        "lineage": lineage,
    })


async def _aux_retrieval_fragments(
    deps: ChainDeps, cfg: d.RetrievalConfigFace, question: str,
) -> list[d.Evidence]:
    """辅助检索（W-AUX②——主路权威数出数后的报告库旁注材料）。

    同域函数级复用检索链双路召回缝（deps.index_searcher_dual——S4 同一注入缝，
    零新缝）与合并策略（cfg.merge——_relaxed_rescore 同款），小窗口取前
    AUX_TOP_K 支；引用别名自 AUX_REF_START 起编（表卡数据证据 c1/c2 已占——
    同一 run 内全局不撞号）。报告库空 → 空清单＝纯表格自然降级（零帧零报错）。
    """
    vector, keyword = await deps.index_searcher_dual(question, AUX_TOP_K, AUX_TOP_K)
    merged = (
        d.rrf_merge(vector, keyword) if cfg.merge == "rrf_rank"
        else d.concat_merge(vector, keyword)
    )
    rows = _index_evidence_rows(merged[:AUX_TOP_K])
    return [
        replace(row, ref=f"c{AUX_REF_START + ordinal}")
        for ordinal, row in enumerate(rows)
    ]


async def _narrate_table(
    deps: ChainDeps, question: str, table: dict[str, Any], fragments: list[d.Evidence],
) -> tuple[str | None, list[d.Evidence], int]:
    """旁注解读段生成（W-AUX②——gateway.complete 单点，caller=chat.query.narrate
    计费留痕照 chat.query.rewrite 惯例；提示词三约束见 NARRATE_SYSTEM_PROMPT：
    数值一律以表格为准（片段数值不采）／引用标注 cN／不得虚构）。

    返回 (解读文本, 存续引用片段, 拦截数)：文本 None＝生成不可用（completer 未
    装配/调用失败/空输出）——调用方纯表格自然降级零报错；引用 fail-closed 照
    检索链 GEN 收口同款（parse_refs→锚校验→strip_ref——伪造/失锚引用拦截剥除，
    绝不带病出帧）。
    """
    table_text = "\n".join(
        "；".join(f"{col['title']}={row.get(col['dataIndex'])}" for col in table["columns"])
        for row in table["rows"]
    )
    fragment_table = "\n".join(
        f"{f.ref}：[{f.kind}] {f.label}——{f.snippet}" for f in fragments
    )
    text, error = await _complete(deps, [
        {"role": "system", "content": NARRATE_SYSTEM_PROMPT},
        {"role": "user", "content": NARRATE_USER_TEMPLATE.format(
            question=question, table_text=table_text, fragment_table=fragment_table,
        )},
    ], CALLER_NARRATE)
    if error or text is None or not text.strip():
        return None, [], 0
    by_ref = {f.ref: f for f in fragments}
    cited: list[d.Evidence] = []
    dropped = 0
    for ref in d.parse_refs(text):
        candidate = by_ref.get(ref)
        if candidate is None:
            dropped += 1
            text = d.strip_ref(text, ref)
            continue
        if candidate.fragment_id is not None:
            anchor = await deps.anchor_loader(candidate.fragment_id)
            if anchor is None or (
                candidate.report_id and anchor.report_id != candidate.report_id
            ):
                dropped += 1
                text = d.strip_ref(text, ref)
                continue
        cited.append(candidate)
    return text, cited, dropped


async def _continue_with_retrieval(
    deps: ChainDeps, ctx: d.ChainContext, *,
    refusal_answer: dict[str, Any], refusal_notice: str | None = None,
) -> AsyncIterator[d.SseEvent]:
    """问数链出不了数 → 自动接续检索问答链（W-AUX③——消二选一漏答）。

    同模块函数级复用 retrieval_chain（零新缝）：原问句走报告检索瀑布，答案正文
    前置如实标注（ctx.data_fallback_note——检索结果非权威数值，token 流与答案
    帧同文）。token/citation 缓冲随终局分派：接续链真出检索答案（kind=text 且
    引用非空）→ 按原序放行；接续链兜底收场（fixed 告警卡／free 无引用——检索
    无果或生成不可用）→ 双重如实拒答：丢弃缓冲流，回落问数链原拒答话术
    （refusal_notice＋refusal_answer）收场。
    """
    yield notice(d.DATA_CHAIN_FALLBACK_NOTICE, level="info")
    continued = replace(ctx, data_fallback_note=d.DATA_CHAIN_FALLBACK_NOTE)
    buffered: list[d.SseEvent] = []
    final: d.SseEvent | None = None
    async for event in retrieval_chain(deps, continued):
        if event.event in (d.FRAME_TOKEN, d.FRAME_CITATION):
            buffered.append(event)  # 终局未定前不外放——双重无果时不留半截流
            continue
        if event.event == d.FRAME_ANSWER:
            final = event
            continue
        yield event
    answer = dict(final.data) if final is not None else None
    succeeded = bool(
        answer is not None
        and answer.get("kind") == "text"
        and answer.get("citations")
    )
    if succeeded:
        assert final is not None
        for event in buffered:
            yield event
        yield final
        return
    if refusal_notice is not None:
        yield notice(refusal_notice, level="warning")
    yield d.SseEvent(d.FRAME_ANSWER, refusal_answer)


def _today() -> date:
    """链内今日（B14——infra.clock 单点；问数链确定性解析的时间基准）。"""
    return now().date()


def _sample_row_line(row: dict[str, Any]) -> str:
    """首行结果 → 样本行展示串（数据证据出处 1——「证明去重/折算」的样本行族）。"""
    return " | ".join(f"{key}={row[key]}" for key in row if row.get(key) is not None)


# ---------- FAQ 秒回链 ----------



async def faq_direct_chain(deps: ChainDeps, ctx: d.ChainContext) -> AsyncIterator[d.SseEvent]:
    """FAQ 秒回（B3——只消费已发布条目；命中即秒回、不走报告检索）。

    思考树叙事（P1-08c）：N18 预制问答节点 process→finish——命中判定与直出
    同拍完成：执行前复测 match_index（装配命中不豁免——索引竞变在此现形，
    P1F-02），命中 → 直出答案＋citation（no_model=true——「本条命中 FAQ 直出
    ——未调用模型」标注，A1 合同冻结）；未命中按装配阶段有无命中分叉注记
    （复测未命中≠竞变失效——两情形不再同标「索引竞变」），answer 接兜底诚实
    判定——只计 term_cards/metric_cards（P-004 修复拍③：FAQ 链走到拒答即
    faq_hit 未命中或已失效，不复述其内容），有卡报「台账有收录」、无卡走
    D2 fallback_text。citation＝FAQ 条目出处（faq 块族——citation kind 四值
    枚举无 FAQ 专值，落台账条目族如实标注）。
    """
    yield d.node_frame("N18", state=d.NODE_PROCESS, tag="代码 · 秒回闸",
                       note="预制问答——标准问匹配（只消费已发布条目）")
    hit = await deps.faq_matcher(ctx.question)  # 执行前复测（装配命中不豁免——竞变现形）
    if hit is None:
        annotation = (
            "装配命中已失效（索引竞变）" if ctx.assembly.faq_hit is not None
            else "执行前复测未命中（装配阶段即无命中）"
        )
        cfg = await deps.config_loader()
        yield d.node_frame(
            "N18", state=d.NODE_FINISH,
            note=f"FAQ 精确命中：{annotation}——按兜底策略处理，不硬答",
        )
        yield notice(
            f"FAQ 精确命中：{annotation}——按兜底策略处理，不硬答。",
            level="warning",
        )
        entries = _ledger_entries(ctx.assembly, include_faq=False)  # 只计台账卡——不复述 FAQ
        yield d.SseEvent(d.FRAME_ANSWER, {
            "kind": "alert", "alert_type": "warning",
            "text": _ledger_alert_text(entries) if entries else cfg.fallback_text,
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
        async for event in _fallback_answer(deps, cfg, ctx.question, ctx.assembly):
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
        async for event in _fallback_answer(deps, cfg, ctx.question, ctx.assembly):
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
        async for event in _fallback_answer(deps, cfg, ctx.question, ctx.assembly):
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
