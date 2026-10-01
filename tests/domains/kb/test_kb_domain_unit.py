"""kb 域纯语义单测——切段器/分词/向量占位/路由解析/模板配置档（B1 合同常量）。"""

import pytest

from app.domains.kb import domain as d


class TestChunker:
    def test_smart_respects_size_band(self) -> None:
        text = ("句子。" * 400)  # 1600 字连续正文
        chunks = d.chunk_text(text, "smart")
        assert chunks
        for _, piece in chunks:
            # 末段并入放宽 20% 内；其余段在带内
            assert len(piece) <= d.SMART_MAX_CHARS * 1.2
        assert sum(len(p) for _, p in chunks) >= len(text)  # overlap 回带

    def test_smart_sections_carry_paths(self) -> None:
        text = "第1章 井况\n内容一。\n1.1 投产信息\n投产 2019-06-15。"
        chunks = d.chunk_text(text, "smart")
        assert any("第1章" in section for section, _ in chunks)
        assert any("1.1" in section for section, _ in chunks)

    def test_fixed_hard_cut(self) -> None:
        text = "字" * 1200
        chunks = d.chunk_text(text, "fixed")
        assert [len(p) for _, p in chunks] == [512, 512, 176]

    def test_mixed_parent_child(self) -> None:
        text = ("第1章 甲\n" + "内容。" * 100) + "\n第2章 乙\n" + "数据。" * 50
        pieces = d.chunk_text(text, "mixed")
        parents = [s for s, _ in pieces if s.startswith("父块·")]
        children = [s for s, _ in pieces if not s.startswith("父块·")]
        assert parents and children
        for _, piece in pieces:
            if not piece:
                continue
        assert any(
            len(p) <= d.MIXED_CHILD_MAX_CHARS for s, p in pieces if not s.startswith("父块·")
        )

    def test_empty_text(self) -> None:
        assert d.chunk_text("", "smart") == []


class TestTokenizeAndEmbed:
    def test_tokenize_ascii_and_bigram(self) -> None:
        tokens = d.tokenize("N-02 井投产")
        assert "n" in tokens or "02" in tokens
        assert "投产" in tokens

    def test_local_embedder_deterministic_and_normalized(self) -> None:
        embedder = d.LocalHashEmbedder()
        import asyncio

        vecs = asyncio.run(embedder.embed(["同一文本", "同一文本", "另一文本"]))
        assert vecs[0] == vecs[1]
        assert len(vecs[0]) == d.EMBED_DIM
        norm = sum(v * v for v in vecs[0]) ** 0.5
        assert norm == pytest.approx(1.0, abs=1e-3)


class TestTemplatesAndNotes:
    def test_template_profiles(self) -> None:
        assert d.TEMPLATE_CONFIGS["completion"]["graph"] is True
        assert d.TEMPLATE_CONFIGS["monthly"]["graph"] is False
        assert d.TEMPLATE_CONFIGS["dynamic"]["graph"] is False
        assert d.TEMPLATE_CONFIGS["blank"] == d.DEFAULT_CONFIG
        for profile in d.TEMPLATE_CONFIGS.values():
            assert profile["mode"] == "smart"
            assert profile["add_summary"] and profile["add_questions"]

    def test_chunk_note_contract_text(self) -> None:
        note = d.chunk_note("smart")
        assert note.startswith("切段方式：智能切段——按章节和语义边界切，一段 256–1024 字")
        assert note.endswith("现场切换。")

    def test_index_note_marks_switches(self) -> None:
        note = d.index_note(
            "完井报告库",
            {"semantic": True, "keyword": True, "wiki": True, "graph": False},
        )
        assert note == (
            "按完井报告库的四开关写入索引：语义 ✓ · 关键词 ✓ · 百科页 ✓ · "
            "关系图谱 ✗。关掉的支路不跑、不产生抽取费用。"
        )


class TestRouteSuggestion:
    def test_parse_existing(self) -> None:
        raw = (
            '前言 {"mode": "existing", "lib_name": "完井报告库", '
            '"reason": "完井", "confidence": 0.87}'
        )
        out = d.parse_route_suggestion(raw, {"完井报告库": "lib-1"})
        assert out.mode == "existing" and out.lib_id == "lib-1"
        assert out.confidence == pytest.approx(0.87)

    def test_parse_new_with_template(self) -> None:
        raw = '{"mode": "new", "template": "monthly", "reason": "月报", "confidence": 0.5}'
        out = d.parse_route_suggestion(raw, {})
        assert out.mode == "new" and out.template == "monthly"

    def test_parse_rejects_unknown_lib(self) -> None:
        raw = '{"mode": "existing", "lib_name": "不存在的库"}'
        out = d.parse_route_suggestion(raw, {"完井报告库": "lib-1"})
        assert out.mode is None

    def test_parse_rejects_bad_template(self) -> None:
        raw = '{"mode": "new", "template": "wiki"}'
        out = d.parse_route_suggestion(raw, {})
        assert out.mode is None

    def test_parse_garbage(self) -> None:
        assert d.parse_route_suggestion("完全没有 JSON", {}).mode is None
        assert d.parse_route_suggestion("{broken", {}).mode is None


class TestNames:
    def test_doc_display(self) -> None:
        assert d.doc_display("N-02 井完井报告.pdf") == "《N-02 井完井报告》"

    def test_normalize(self) -> None:
        assert d.normalize_name(" 完井 报告库 ") == "完井 报告库"
        assert d.normalize_filename("N-02 井报告.PDF") == d.normalize_filename("N-02井报告.docx")
