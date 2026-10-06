"""G-07 关键词腿 BM25 打分器单测——单元切分/IDF 方向/归一化值域/空输入。

合同锚：99 册开放问题 5 收口（落法＝应用层 BM25）；对外分数契约 0~1
（compute_confidence／refuse_threshold 均假设）。
"""

from app.domains.kb.domain import (
    alnum_tokens,
    bm25_scores,
    extract_units,
    normalize_bm25,
)


def test_extract_units_bigrams_and_alnum_tokens() -> None:
    """CJK 二字组滑窗＋字母数字 token 整取（W-33 不许被切碎）；单字不成单元。"""
    units = extract_units("W-33 井酸化措施")
    assert "W-33" in units  # 编号整 token
    assert {"井酸", "酸化", "化措", "措施"} <= set(units)  # 二字组滑窗
    assert "井" not in units  # 单字不成单元
    assert all(len(u) >= 2 for u in units)


def test_extract_units_empty_and_pure_ascii() -> None:
    assert extract_units("") == []
    assert "SCSSV" in extract_units("井下安全阀 SCSSV 功能试验")
    assert "2462" in extract_units("下深 2462.0 米") or "2462" in extract_units("下深 2462 米")


def test_alnum_tokens_codes_only() -> None:
    assert alnum_tokens("W-33 井酸化措施的效果四要素") == ["W-33"]
    assert alnum_tokens("各井日产油量是多少") == []  # 纯中文问句无编号
    assert alnum_tokens("压力计 SCSSV 与 2462") == ["SCSSV", "2462"]


def test_bm25_rare_unit_dominates_common_unit() -> None:
    """IDF 方向：问句含稀有单元（W-33，df=1）与常见单元（油田，df=2），
    各自唯一的命中文本相比——稀有单元命中者得分更高。"""
    texts = [
        "对 W-33 井实施土酸酸化增油",  # 只含稀有单元
        "油田生产运行日报汇总",  # 只含常见单元
        "油田各井生产报表",  # 抬高油田的 df——压低其 IDF
    ]
    scores = bm25_scores("W-33 井与油田日产情况", texts)
    assert scores[0] > scores[1] > 0.0  # 稀有单元命中者胜出，常见单元命中者仍得分


def test_bm25_tf_saturation_sublinear() -> None:
    """词频饱和：命中 4 次得分高于 1 次但不到 4 倍（BM25 k1 饱和）。"""
    base = "筛管下入井筒"
    four = bm25_scores("筛管", [base, "筛管筛管筛管筛管下入井筒"])
    s1, s4 = four[0], four[1]
    assert s4 > s1
    assert s4 < s1 * 4  # 饱和——不到线性 4 倍


def test_normalize_bm25_bounded_and_monotonic() -> None:
    """对外分数契约 0~1（confidence/refuse_threshold 均假设）；单调不减。"""
    assert normalize_bm25(0.0) == 0.0
    assert normalize_bm25(-1.0) == 0.0  # 负分防御
    assert 0.0 < normalize_bm25(0.5) < normalize_bm25(5.0) < normalize_bm25(50.0) < 1.0


def test_bm25_empty_inputs_safe() -> None:
    assert bm25_scores("", ["任意文本"]) == [0.0]
    assert bm25_scores("任意问句", []) == []
    assert bm25_scores("W-33 井", ["", ""]) == [0.0, 0.0]  # 问句有单元但文本无单元


# ---------- G-08：mixed 父块截断丢内容修复 ----------


def test_mixed_mode_children_cover_full_text_no_headings() -> None:
    """无章节标题 4500 字文本走 mixed：子块并集覆盖全文（原实现截断丢 44%）。"""
    from app.domains.kb.domain import chunk_text, validate_chunks

    body = "\n\n".join(
        f"第 {i} 段：渤中 34-8 油田生产运行情况说明，W-{i} 井日产油量稳定在 "
        f"{20 + i} 吨，含水率 {60 + i}%，措施增油持续见效，检泵周期延长。"
        for i in range(60)
    )
    chunks = chunk_text(body, "mixed")
    assert chunks, "应产出片段"
    parent_rows = [(p, c) for p, c in chunks if p.startswith("父块·")]
    assert all(len(c) <= 2048 for _, c in parent_rows)  # 父块行仍截断
    issues = validate_chunks(body, chunks)
    assert issues == [], f"切块应无损，违规：{issues[:3]}"
    # 尾部内容（原实现必丢）必须出现在某个子块里
    tail_marker = body[-200:]
    assert any(tail_marker[:40] in c for _, c in chunks), "末段内容不得丢失"
