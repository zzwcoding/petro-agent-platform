#!/usr/bin/env python3
"""从 petro-agent 评测题单提取 WeKnora 迁移评测的题单。

产出（写入本目录）：
- 题单-81题.jsonl   问答组 51 + 新语料 30（WeKnora 可答的纯文档知识题）
- 排除题单-16题.jsonl 问数/数据库题（DATA 组，WeKnora 无数据库查询能力，剔除）

题干原样照抄，不改写（判分纪律）。
"""
import importlib.util
import json
import pathlib

TOOLS = pathlib.Path("/Users/divh/Downloads/petro-agent-platform/eval/results/tools")
OUT = pathlib.Path("/Users/divh/Downloads/petro-agent-platform/eval/results/weknora-评测")
OUT.mkdir(parents=True, exist_ok=True)


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    q3 = load("suites_q3")
    q6 = load("suites_q6")

    keep, excluded = [], []
    for qid, group, question in q3.QA_SUITE:
        keep.append({"qid": qid, "group": group, "question": question, "source": "suites_q3.QA_SUITE"})
    for suite in (q6.COMPLETION_SUITE, q6.DYNAMIC_SUITE, q6.MONTHLY_SUITE):
        for qid, group, question in suite:
            keep.append({"qid": qid, "group": group, "question": question, "source": "suites_q6"})
    for qid, group, question in q3.DATA_SUITE:
        excluded.append({
            "qid": qid, "group": group, "question": question,
            "source": "suites_q3.DATA_SUITE",
            "excluded_reason": "需数据库查询（Text-to-SQL），WeKnora 无此能力",
        })

    with open(OUT / "题单-81题.jsonl", "w", encoding="utf-8") as f:
        for row in keep:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    with open(OUT / "排除题单-问数组.jsonl", "w", encoding="utf-8") as f:
        for row in excluded:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    groups = {}
    for row in keep:
        groups[row["group"]] = groups.get(row["group"], 0) + 1
    print(f"主考题: {len(keep)} 题  分组: {groups}")
    print(f"排除题: {len(excluded)} 题  qid: {[r['qid'] for r in excluded]}")


if __name__ == "__main__":
    main()
