"""retrieval 服务单测——种子自动落库/版本推进链/via 回链/在途 409/失败零写。

sqlite 底座（tests/domains/retrieval/conftest.py）＋ freeze 时钟（B14——单号
日期序与版本时刻确定性）；B12 审计由 api 层编排，本文件不涉 security。
"""

import asyncio
from typing import Any

import pytest

from app.domains.retrieval import (
    ChangeRequestReceipt,
    ConfigSnapshot,
    RetrievalConflictError,
    RetrievalParamError,
    default_config_dict,
)
from app.domains.retrieval.store import RetrievalConfigRow
from app.infra.clock import freeze
from app.infra.db import ConnectionManager
from tests.domains.retrieval.conftest import version_rows

AQIANG = "阿强 · 平台运维"


async def _pointer(db: ConnectionManager) -> RetrievalConfigRow:
    async with db.readonly() as session:
        pointer = await session.get(RetrievalConfigRow, "singleton")
    assert pointer is not None
    return pointer


class TestSeedOnFirstRead:
    async def test_first_read_seeds_contract_defaults(self, service: Any) -> None:
        with freeze("2026-10-02 12:00:00"):
            snapshot = await service.effective_config()
        assert snapshot.version.no == "v1"
        assert snapshot.version.via is None  # 种子非变更产生（via 空）
        assert snapshot.version.updated_by == "系统"
        assert snapshot.version.updated_at.strftime("%Y-%m-%d %H:%M") == "2026-10-02 12:00"
        assert snapshot.sections_dict() == default_config_dict()  # 七节默认值全对
        qa = snapshot.qa_behavior
        assert qa.faq_direct_hit is True
        assert qa.refuse_threshold == 0.4
        assert qa.clarify_strategy == "ask_missing"
        assert (qa.confidence_thresholds.high, qa.confidence_thresholds.low) == (0.8, 0.4)
        assert qa.faq_expand_rounds == 3

    async def test_seed_idempotent(self, service: Any, retrieval_db: ConnectionManager) -> None:
        await service.effective_config()
        await service.effective_config()
        rows = await version_rows(retrieval_db)
        assert [r.version_no for r in rows] == ["v1"]  # 重读零写入
        pointer = await _pointer(retrieval_db)
        assert pointer.current_version_no == "v1"


class TestSubmitChangeRequest:
    async def test_submit_advances_version_with_via_backlink(
        self, service: Any, retrieval_db: ConnectionManager
    ) -> None:
        with freeze("2026-10-02 12:00:00"):
            receipt = await service.submit_change_request(
                {
                    "params": {
                        "semantic_top_k": 10,
                        "keyword_top_k": 20,
                        "merge": "rrf_rank",
                        "top_n": 20,
                    }
                },
                updated_by=AQIANG,
            )
        assert isinstance(receipt, ChangeRequestReceipt)
        assert receipt.change_request_id == "#CFG-20261002-01"
        assert receipt.state == "pending"  # 合同字面（A3 形态值——生效性由 via 回链承载）
        assert receipt.sections == ("params",)
        assert receipt.version.no == "v2"
        assert receipt.version.via == "#CFG-20261002-01"  # via＝本单号（生效回链）
        assert receipt.version.updated_by == AQIANG
        assert receipt.config.params.semantic_top_k == 10
        # GET 恒返回生效值（提交即生效——端点 1 读到新版本）
        snapshot = await service.effective_config()
        assert snapshot.version.no == "v2"
        assert snapshot.version.via == "#CFG-20261002-01"
        assert snapshot.params.semantic_top_k == 10
        assert snapshot.sections_dict()["qa_behavior"] == default_config_dict()["qa_behavior"]

    async def test_two_submissions_serial_ids_and_via_chain(
        self, service: Any, retrieval_db: ConnectionManager
    ) -> None:
        with freeze("2026-10-02 12:00:00"):
            first = await service.submit_change_request({"rerank": "llm"}, updated_by=AQIANG)
            second = await service.submit_change_request(
                {"citation_format": "code"}, updated_by=AQIANG
            )
        assert (first.version.no, first.change_request_id) == ("v2", "#CFG-20261002-01")
        assert (second.version.no, second.change_request_id) == ("v3", "#CFG-20261002-02")
        rows = await version_rows(retrieval_db)
        assert [r.version_no for r in rows] == ["v1", "v2", "v3"]  # append-only 版本轴
        assert [r.via for r in rows] == [None, "#CFG-20261002-01", "#CFG-20261002-02"]
        snapshot = await service.effective_config()
        assert (snapshot.rerank, snapshot.citation_format) == ("llm", "code")  # 两节叠加生效
        assert snapshot.sections_dict()["params"] == default_config_dict()["params"]

    async def test_invalid_patch_400_leaves_store_untouched(
        self, service: Any, retrieval_db: ConnectionManager
    ) -> None:
        with pytest.raises(RetrievalParamError) as ei:
            await service.submit_change_request(_bad_rounds_patch(), updated_by=AQIANG)
        assert ("patch.qa_behavior.faq_expand_rounds", "1–5") in ei.value.violations
        assert await version_rows(retrieval_db) == []  # 失败路径零写（种子也不落）
        async with retrieval_db.readonly() as session:
            assert await session.get(RetrievalConfigRow, "singleton") is None

    async def test_conflict_gate_released_after_submit(
        self, service: Any, retrieval_db: ConnectionManager
    ) -> None:
        with freeze("2026-10-02 12:00:00"):
            await service.submit_change_request({"rerank": "llm"}, updated_by=AQIANG)
            again = await service.submit_change_request({"rerank": "fast"}, updated_by=AQIANG)
        assert again.version.no == "v3"  # 在途窗口随受理结束释放——串行受理畅通
        assert len(await version_rows(retrieval_db)) == 3

    async def test_concurrent_submits_one_409(
        self, service: Any, retrieval_db: ConnectionManager
    ) -> None:
        results = await asyncio.gather(
            service.submit_change_request({"rerank": "llm"}, updated_by=AQIANG),
            service.submit_change_request({"rerank": "compound"}, updated_by=AQIANG),
            return_exceptions=True,
        )
        receipts = [r for r in results if isinstance(r, ChangeRequestReceipt)]
        conflicts = [r for r in results if isinstance(r, RetrievalConflictError)]
        assert len(receipts) == 1 and len(conflicts) == 1
        assert "在途" in str(conflicts[0])
        rows = await version_rows(retrieval_db)
        assert [r.version_no for r in rows] == ["v1", "v2"]  # 只受理一单——版本轴无重复推进
        snapshot = await service.effective_config()
        assert snapshot.version.via == receipts[0].change_request_id
        assert isinstance(snapshot, ConfigSnapshot)

    async def test_submit_on_empty_db_seeds_then_applies(
        self, service: Any, retrieval_db: ConnectionManager
    ) -> None:
        with freeze("2026-10-02 12:00:00"):
            receipt = await service.submit_change_request({"rerank": "compound"}, updated_by=AQIANG)
        rows = await version_rows(retrieval_db)
        assert [r.version_no for r in rows] == ["v1", "v2"]  # 种子 v1 先落再叠加 patch
        assert rows[0].config["rerank"] == "fast"  # 种子为合同默认值
        assert rows[1].config["rerank"] == "compound"
        pointer = await _pointer(retrieval_db)
        assert pointer.current_version_no == "v2"
        assert receipt.config.rerank == "compound"


def _bad_rounds_patch() -> dict[str, object]:
    return {
        "qa_behavior": {
            "faq_direct_hit": True,
            "refuse_threshold": 0.4,
            "clarify_strategy": "ask_missing",
            "confidence_thresholds": {"high": 0.8, "low": 0.4},
            "faq_expand_rounds": 6,  # 越界（合同域 1–5）
        }
    }
