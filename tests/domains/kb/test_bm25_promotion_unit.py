"""G-07 编号保送通道单测——promote_entity_hits 纯函数直锁逻辑＋接线冒烟。"""

from types import SimpleNamespace

import pytest

from app.domains.kb.domain import promote_entity_hits


def _frag(fid: str, hit_text: str) -> SimpleNamespace:
    return SimpleNamespace(id=fid, hit_text=hit_text)


def _scored(frags: list[SimpleNamespace], scores: list[float]):
    return list(zip(frags, scores, strict=True))


def test_promotion_appends_unranked_token_hit() -> None:
    """编号逐字命中而未进榜的片段 → 保送队尾（占尾席）。"""
    f1, f2, f3 = _frag("f1", "油田统计"), _frag("f2", "油田日报"), _frag("f3", "W-33 井酸化")
    ranked = [(f1, 0.9), (f2, 0.8)]
    scored = _scored([f1, f2, f3], [0.9, 0.8, 0.4])
    out = promote_entity_hits(
        ranked, scored, ["W-33"], top_k=3, hit_text_of=lambda f: f.hit_text
    )
    assert [f.id for f, _ in out] == ["f1", "f2", "f3"]  # f3 保送队尾


def test_promotion_cap_four() -> None:
    """上限 4：六个候选编号片段只保送四个（多编号问句不把窗占满）。"""
    frags = [_frag(f"p{i}", f"W-{i} 井记录") for i in range(6)]
    fillers = [_frag(f"f{i}", f"油田统计{i}") for i in range(4)]
    ranked = [(f, 0.9 - i * 0.1) for i, f in enumerate(fillers)]  # 榜上全是普通片段
    scored = _scored(frags + fillers, [0.5] * 6 + [0.9, 0.8, 0.7, 0.6])
    out = promote_entity_hits(
        ranked, scored, ["W-0", "W-1", "W-2", "W-3", "W-4", "W-5"],
        top_k=6, hit_text_of=lambda f: f.hit_text,
    )
    promoted = [f.id for f, _ in out if f.id.startswith("p")]
    assert len(promoted) == 4  # 上限 4
    assert len(out) == 6  # 总长恒 = top_k
    assert all(f.id.startswith("f") for f, _ in out[:2])  # 榜首普通片段不被挤出


def test_promotion_skips_already_ranked() -> None:
    """榜上已有的编号片段不重复保送；非编号片段不由保送强塞（那是 BM25 的职责）。"""
    f1, f2, f3 = _frag("f1", "W-33 井酸化"), _frag("f2", "油田统计"), _frag("f3", "W-33 井完井")
    ranked = [(f1, 0.9)]  # W-33 片段已自然在榜
    scored = _scored([f1, f2, f3], [0.9, 0.5, 0.4])
    out = promote_entity_hits(
        ranked, scored, ["W-33"], top_k=2, hit_text_of=lambda f: f.hit_text
    )
    ids = [f.id for f, _ in out]
    assert ids == ["f1", "f3"]  # f1 不重复保送；f3（含编号）保送占尾席；f2 不受保送影响


def test_promotion_no_tokens_noop() -> None:
    """纯中文问句无编号 token——原榜原样返回。"""
    f1, f2 = _frag("f1", "油田统计"), _frag("f2", "W-33 井酸化")
    ranked = [(f1, 0.9), (f2, 0.5)]
    scored = _scored([f1, f2], [0.9, 0.5])
    out = promote_entity_hits(
        ranked, scored, [], top_k=2, hit_text_of=lambda f: f.hit_text
    )
    assert out == ranked


@pytest.mark.parametrize("top_k", [1, 2, 5])
def test_promotion_total_len_le_topk(top_k: int) -> None:
    """返回总长恒 ≤ top_k（保送占尾席不扩窗）。"""
    frags = [_frag(f"p{i}", f"W-{i} 井记录") for i in range(8)]
    scored = _scored(frags, [0.4] * 8)
    out = promote_entity_hits([], scored, ["W-0", "W-1"], top_k=top_k,
                              hit_text_of=lambda f: f.hit_text)
    assert len(out) <= top_k
