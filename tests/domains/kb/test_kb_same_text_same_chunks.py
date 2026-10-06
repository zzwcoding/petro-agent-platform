"""DE-05 同文同切铁律——双跑全等断言（票面验收②：含 C 样例＋跨进程独立调用）。

- 同 fixture 连续两次切块→切片列表全等（含章节路径与顺序；C 报告裁剪样例
  ＝DE-04 fixture 复用为固定考题）；
- 跨进程两次独立调用全等：独立 Python 进程＋独立 sqlite 库＋不同
  PYTHONHASHSEED，敌意两翼（stub LLM 应答「合法子集图」vs「LLM 不可用」——
  若切块边界仍由 LLM 供给，这两跑必分歧，定位记录实验 C 实证于
  tickets/phase3/reports/DE-05.收尾.md）；修复后 chunk 步不查 LLM，
  两跑必须与进程内纯规则基线三方全等。

红线：桩 LLM 永不触网（B6）；子进程 _same_text_child.py 只用内存桩。
"""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from app.domains.kb import domain as d

FIXTURE_C = (
    Path(__file__).parents[2] / "fixtures" / "report_C_heading双样式裁剪.txt"
).read_text(encoding="utf-8")
CHILD = Path(__file__).parent / "_same_text_child.py"


def _pieces_sha(text: str, mode: str) -> str:
    """进程内纯规则基线指纹（生产链＝chunk_text 缺省供给规则图）。"""
    pieces = d.chunk_text(text, mode)
    return hashlib.sha256(
        json.dumps(pieces, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _run_child(scenario: str, tmp_dir: Path, hash_seed: str) -> dict[str, Any]:
    """起独立进程独立库入库一次（PYTHONHASHSEED 按参注入），倾泻切片指纹。"""
    env = dict(os.environ, PYTHONHASHSEED=hash_seed)
    db = tmp_dir / f"{scenario}-{hash_seed}.db"
    proc = subprocess.run(
        [sys.executable, str(CHILD), scenario, str(db)],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
        check=False,
    )
    assert proc.returncode == 0, f"子进程失败：{proc.stderr[-2000:]}"
    return json.loads(proc.stdout.strip().splitlines()[-1])


class TestSameTextSameChunks:
    def test_double_chunk_identical_fixture_c(self) -> None:
        # 同 fixture 连续两次切块→切片列表全等（含章节路径与顺序；三模式）
        for mode in ("smart", "mixed", "fixed"):
            assert d.chunk_text(FIXTURE_C, mode) == d.chunk_text(FIXTURE_C, mode), mode
        # 生产链缺省供给＝显式规则图供给同形（smart/mixed 消费图的两模式）
        for mode in ("smart", "mixed"):
            assert d.chunk_text(FIXTURE_C, mode) == d.chunk_text(
                FIXTURE_C, mode, structure=d.rule_structure_map(FIXTURE_C)
            ), mode

    def test_chunk_entry_docstring_carries_iron_law(self) -> None:
        # 铁律落 docstring（票面交付物④的测试引用面）：kb 切块入口一句话约束
        assert d.chunk_text.__doc__ is not None
        assert "同文同切" in d.chunk_text.__doc__

    def test_cross_process_two_environments_identical(self, tmp_path: Any) -> None:
        """跨进程两次独立调用全等（票面验收②后半——不只同进程内存态）。

        两跑＝独立进程＋独立 sqlite 库＋不同哈希种子＋敌意 stub 应答两翼
        （合法子集图 / LLM 不可用）：任何一路若仍影响切片，指纹必分叉。
        """
        run_a = _run_child("llm_subset", tmp_path, hash_seed="0")
        run_b = _run_child("llm_down", tmp_path, hash_seed="4242")
        assert run_a["n_pieces"] > 0
        assert run_b["n_pieces"] > 0
        assert run_a["sha256"] == run_b["sha256"]
        # 与进程内纯规则基线三方全等
        assert run_a["sha256"] == _pieces_sha(FIXTURE_C, "smart")
        assert run_a["n_pieces"] == run_b["n_pieces"]
