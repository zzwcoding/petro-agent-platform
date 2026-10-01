"""wiki 域语义单测——拼回去重/截断纪律/claims fail-closed/台账挂接/状态派生。

纯 domain.py 语义（B1：零 IO）；合同锚见模块 docstring（B4 v0.3/PRD F50/F51/F52）。
"""

from app.domains.derivatives import domain as d

# ---------- 拼回全文（F50：重叠去重＋图片回读） ----------


def test_reconstruct_dedupes_adjacent_overlap() -> None:
    """相邻重叠去重：smart 切段 10–20% 回带在拼回时剥除（F50）。"""
    chunks = [
        ("原文块", "章节 01", "N-02 井位于渤南区块 CEP-A 平台，井别采油，2019-06-15 投产。"),
        ("原文块", "章节 01", "2019-06-15 投产。完井段详见射孔与防砂参数表。"),
        ("原文块", "章节 02", "防砂方式筛管完井。"),
    ]
    text = d.reconstruct_content(chunks)
    assert text.count("2019-06-15 投产。") == 1  # 重合前缀剥除、不重复
    assert "完井段详见射孔与防砂参数表" in text
    assert "防砂方式筛管完井" in text


def test_reconstruct_reads_image_blocks_with_caption() -> None:
    """图片块连图注回读（F36——否则纯图片文档产出空内容）。"""
    chunks = [
        ("原文块", "章节 01", "正文一段。"),
        ("图片说明块", "章节 03", "图 3-7 岩性柱状图：按深度展示岩性分布。"),
        ("图片文字块", "章节 03", "图内表格文字。"),
    ]
    text = d.reconstruct_content(chunks)
    assert "插图说明：图 3-7 岩性柱状图" in text
    assert "插图文字：图内表格文字" in text


def test_truncate_for_wiki_cuts_at_paragraph_boundary() -> None:
    """32K 截断（F50/WeKnora maxContentForWiki）：超限在段落边界截断。"""
    text = "\n".join("x" * 100 for _ in range(400))  # 40K
    out = d.truncate_for_wiki(text)
    assert len(out) <= d.WIKI_SOURCE_MAX_CHARS
    assert out[-1] == "x" and not out.endswith("\n" + "x" * 99 + "\nxx")


# ---------- 截断纪律（续写 3 轮、未完放弃——半页不落库） ----------


def test_sentinel_discipline() -> None:
    assert d.looks_unfinished("正文未写完")
    assert not d.looks_unfinished(f"正文\n{d.WIKI_END_MARKER}")
    stripped = d.strip_sentinel(f"# 标题\n正文\n{d.WIKI_END_MARKER}\n")
    assert d.WIKI_END_MARKER not in stripped
    assert stripped.startswith("# 标题\n正文")


def test_continue_prompt_carries_sentinel_rule() -> None:
    prompt = d.build_continue_prompt("已有正文片段")
    assert d.WIKI_END_MARKER in prompt
    assert "无缝续写" in prompt


# ---------- 论断回链（claims[]——fail-closed） ----------


def test_extract_claims_fail_closed_drops_fake_anchor() -> None:
    """伪造/失效锚被拦：[[claim:f999]]（不在片段集）剥除不渲染 [证]、不伪造回链。"""
    content = (
        "井别采油，2019-06-15 投产[[claim:f1]]。\n"
        "平台是 CEP-Z[[claim:f999]]。\n"
        "全部失效[[claim:f998]][[claim:f997]]。\n"
    )
    out, claims = d.extract_claims(content, {"f1", "f2"})
    assert "[[claim:f999]]" not in out
    assert "[[claim:f998]]" not in out
    assert "平台是 CEP-Z" in out  # 文本保留，标记剥除
    assert "全部失效" in out
    assert [c.claim_id for c in claims] == ["c1"]  # 无锚论断不进 claims[]
    assert claims[0].evidence_chunk_ids == ["f1"]


def test_extract_claims_multi_anchor_and_plain_text() -> None:
    content = "投产日期 2019-06-15[[claim:f1]][[claim:f2]]，状态生产中。"
    out, claims = d.extract_claims(content, {"f1", "f2"})
    assert len(claims) == 1
    assert claims[0].evidence_chunk_ids == ["f1", "f2"]
    assert claims[0].text == "投产日期 2019-06-15，状态生产中。"
    assert out == content


# ---------- 台账挂接（glossary_terms[]——无账不挂、单字不挂） ----------


def _registry() -> d.GlossaryRegistry:
    reg = d.GlossaryRegistry()
    reg.words["综合含水率"] = d.GlossaryCard(
        kind="metric", ref_id=5,
        card={"slot_name": "综合含水率", "unit": "%"},
    )
    reg.words["递减增油"] = d.GlossaryCard(
        kind="term", ref_id=7, card={"type": "术语"},
    )
    reg.words["水"] = d.GlossaryCard(kind="term", ref_id=9, card={})  # 单字——不挂
    return reg


def test_linkify_skips_unregistered_and_single_char() -> None:
    """台账无账不挂（裸词「含水率」不挂、「综合含水率」挂）；单字不挂链。"""
    content = "本月综合含水率上升，含水率 30%，涉及递减增油措施与单字水。"
    out, terms = d.linkify_glossary(content, _registry())
    assert "[[term:综合含水率]]" in out
    assert "[[term:递减增油]]" in out
    assert "[[term:水]]" not in out
    plain = out.replace("[[term:综合含水率]]", "综合含水率")
    assert "含水率 30%" in plain and "[[term:含水率]]" not in out
    assert [t["word"] for t in terms] == ["综合含水率", "递减增油"]
    metric = next(t for t in terms if t["word"] == "综合含水率")
    assert metric["kind"] == "metric" and metric["ref_id"] == 5
    assert metric["card"]["unit"] == "%"


def test_linkify_does_not_nest_markers() -> None:
    """已有 [[…]] 标记内不嵌套挂接。"""
    content = "本井 [[well:N-02]] 综合含水率正常。"
    out, _terms = d.linkify_glossary(content, _registry())
    assert "[[well:N-02]]" in out  # 既有标记不被破坏
    assert "[[term:综合含水率]]" in out


# ---------- 状态派生/slug/digest/横幅 ----------


def test_page_status_derives_from_flag_marker() -> None:
    assert d.page_status_of("平台 CEP-B[[flag:与井档案不符，待核对]]") == d.STATUS_PENDING
    assert d.page_status_of("正常正文无修订提示") == d.STATUS_OK


def test_page_slug_stable_per_report() -> None:
    assert d.page_slug_for_report("rpt-n02-completion") == "wiki-n02-completion"
    assert d.page_slug_for_report("RPT X/9") == "wiki-rpt-x-9"


def test_derive_digest_takes_first_plain_sentence() -> None:
    content = (
        "# 概述\n\nN-02 井完井报告：渤南区块 CEP-A 平台，2019-06-15 投产。后续句。\n\n## 完井段\n"
    )
    assert (
        d.derive_digest(content) == "N-02 井完井报告：渤南区块 CEP-A 平台，2019-06-15 投产。"
    )


def test_rollback_banner_follows_contract_template() -> None:
    banner = d.rollback_banner(4, 2)
    assert "已回滚：当前版 = v4（内容恢复自 v2）" in banner
    assert "回滚本身也记成一次新提交（可再滚回）" in banner
