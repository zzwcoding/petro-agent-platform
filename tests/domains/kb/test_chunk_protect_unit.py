"""G-07 切块保护与无损校验单测（WeKnora 机制移植——受保护内容整块不拆＋无损自检）。"""

from app.domains.kb.domain import chunk_text, validate_chunks

PIPE_TABLE = "\n".join([
    "　　井号　　配注(m³/d)　实注(m³/d)　欠注率",
    "　W-51　　　180　　　　144　　　　20%",
    "　W-52　　　150　　　　97.5　　　　35%",
])


def _prose(seed: str, n: int = 4) -> str:
    return "\n".join(f"第{i}段叙述{seed}，说明完井工艺与施工过程。" for i in range(n))


def test_pipe_table_stays_whole_in_smart() -> None:
    text = _prose("前", 3) + "\n" + PIPE_TABLE + "\n" + _prose("后", 2)
    chunks = [c for _, c in chunk_text(text, "smart")]
    whole = [c for c in chunks if "欠注率" in c and "W-52" in c and "W-51" in c]
    assert whole, "表格行必须聚在同一片段"
    partial = [c for c in chunks if ("W-51" in c) != ("W-52" in c)]
    assert not partial, f"表格被拆散：{[c[:40] for c in partial]}"


def test_aligned_txt_rows_stay_together_in_smart() -> None:
    """空格对齐的 txt 数据行（≥2 连续数字行）成块不拆——D-诱15 根因回归。"""
    rows = "\n".join([
        "7 月　注采比 0.90　注水 13.8 万方",
        "8 月　注采比 0.91　注水 13.5 万方",
        "9 月　注采比 0.98　注水 14.1 万方",
    ])
    text = "一季度回顾。\n" + rows + "\n四季度展望。10 月配注由 180 提至 240。"
    chunks = [c for _, c in chunk_text(text, "smart")]
    together = [c for c in chunks if "0.90" in c and "0.91" in c]
    assert together, "三行数据必须同片段"
    split = [c for c in chunks if ("13.8" in c) != ("13.5" in c) and "0.90" in c]
    assert not split, "数据行被从中间拆开"


def test_oversized_table_splits_at_row_boundary() -> None:
    """超长表格：按行边界切（行绝不从中间断），每片首行是完整行。"""
    rows = "\n".join(
        f"　Y-{i:02d}　　　{i * 10}.5　　　{i * 8}.25　　　{(i * 7) % 40}%"
        for i in range(1, 25)
    )
    text = "管柱数据。\n" + rows
    chunks = [c for _, c in chunk_text(text, "smart")]
    for c in chunks:
        for line in c.splitlines():
            assert line.startswith("　Y-") or "管柱数据" in line, f"出现半个数据行：{line[:30]!r}"


def test_fixed_pipe_span_not_cut_mid_span() -> None:
    text = "前言。\n" + PIPE_TABLE + "\n" + _prose("尾", 6)
    chunks = [c for _, c in chunk_text(text, "fixed")]
    table_chunks = [c for c in chunks if "欠注率" in c]
    assert table_chunks, "表格必须出现在某一片段"
    broken = [c for c in chunks if c.count("W-51") > 0 and c.count("W-52") == 0 and "欠注率" in c]
    assert not broken, "表格行被从中间切散"


def test_validate_chunks_clean_and_violations() -> None:
    text = "第一段内容。\n第二段内容。"
    clean = validate_chunks(text, [("s1", "第一段内容。"), ("s2", "第二段内容。")])
    assert clean == []
    bad = validate_chunks(text, [("s1", "第一段内容。"), ("s2", "幻觉出来的数字 99999。")])
    assert any("非原文" in i for i in bad)
    miss = validate_chunks(text, [("s1", "第一段内容。")])
    assert any("未被任何片段覆盖" in i for i in miss)
