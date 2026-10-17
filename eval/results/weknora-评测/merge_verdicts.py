#!/usr/bin/env python3
"""汇总 4 组评卷结果 + 16 道排除题 → weknora-判分.jsonl（97 行，格式对齐 Q17）。

用法: python3 merge_verdicts.py
"""
import json
import pathlib

HERE = pathlib.Path(__file__).parent
EVAL = pathlib.Path("/Users/divh/Downloads/petro-agent-platform/eval/results")

GROUPS = [
    "判分-组1-问答组A与系统级.jsonl",
    "判分-组2-问答组BC.jsonl",
    "判分-组3-D组诱导.jsonl",
    "判分-组4-新语料.jsonl",
]


def load_jsonl(p: pathlib.Path):
    rows = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main():
    # Q17 基准（petro-agent 冻结点成绩）
    q17 = {}
    for f in EVAL.glob("Q17-判分-V2-*.jsonl"):
        for r in load_jsonl(f):
            q17[r["qid"]] = r.get("verdict") or r.get("q17_verdict") or ""

    verdicts = {}
    for g in GROUPS:
        p = HERE / g
        rows = load_jsonl(p)
        for r in rows:
            assert r["qid"] not in verdicts, f"qid 重复: {r['qid']}"
            verdicts[r["qid"]] = r
    print(f"判分题数: {len(verdicts)}")

    # 题单：81 主考 + 16 排除
    out = []
    for src in ("题单-81题.jsonl", "排除题单-问数组.jsonl"):
        for r in load_jsonl(HERE / src):
            qid = r["qid"]
            if qid in verdicts:
                v = verdicts[qid]
                out.append({
                    "qid": qid, "group": r["group"],
                    "verdict": v["verdict"], "key_points": v.get("key_points", ""),
                    "note": v.get("note", ""), "source": "weknora-WEK2",
                    "q17_verdict": q17.get(qid, ""),
                })
            else:
                out.append({
                    "qid": qid, "group": r["group"],
                    "verdict": "excluded", "key_points": "WeKnora 无数据库查询能力，该题剔除",
                    "note": "", "source": "weknora-WEK2",
                    "q17_verdict": q17.get(qid, ""),
                })
    out.sort(key=lambda x: x["qid"])
    with open(HERE / "weknora-判分.jsonl", "w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    total = {}
    judged = [r for r in out if r["verdict"] != "excluded"]
    for r in judged:
        total[r["verdict"]] = total.get(r["verdict"], 0) + 1
    print(f"总账: {total} | 判 {len(judged)} + 排除 {len(out) - len(judged)} = {len(out)} 行")


if __name__ == "__main__":
    main()
