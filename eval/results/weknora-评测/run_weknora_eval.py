#!/usr/bin/env python3
"""WeKnora 迁移评测跑批脚本。

逐题调用 weknora chat，零重试（每题只问一遍，对齐 petro 评测纪律），
逐题存原始 JSON，汇总行写入跑批结果 jsonl。

用法:
  python3 run_weknora_eval.py --tag WEK1                # 全量 81 题
  python3 run_weknora_eval.py --tag WEK1 --qid A-正1    # 单题
  python3 run_weknora_eval.py --tag WEK1 --resume       # 断点续跑（跳过已完成的）
"""
import argparse
import json
import pathlib
import re
import subprocess
import time

HERE = pathlib.Path(__file__).parent
CLI = "/Users/divh/Downloads/WeKnora/cli/weknora"
DEFAULT_KB = "3be3cd32-fac5-4369-9a21-74eac1c69137"

THINK_RE = re.compile(r"<think>.*?</think>", re.S)


def parse_envelope(stdout: str):
    """拼接 answer 事件流为完整回答；<think> 段是模型推理，从答案中剥掉但保留在 raw。"""
    envelope = json.loads(stdout)
    data = envelope.get("data") or {}
    events = data.get("events") or []
    raw = "".join(e.get("content") or "" for e in events
                  if e.get("response_type") == "answer")
    done = bool(events) and all(e.get("done") for e in events
                                if e.get("response_type") == "answer")
    refs = data.get("knowledge_references") or []
    if isinstance(refs, dict):
        refs = refs.get("chunks") or refs.get("items") or []
    answer = THINK_RE.sub("", raw).strip()
    return {
        "answer": answer,
        "answer_raw": raw,
        "n_refs": len(refs) if isinstance(refs, list) else 0,
        "references": refs if isinstance(refs, list) else [],
        "session_id": data.get("session_id"),
        "stream_done": done,
    }


def load_questions():
    rows = []
    with open(HERE / "题单-81题.jsonl", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def done_qids(tag: str) -> set:
    p = HERE / f"{tag}-跑批结果.jsonl"
    if not p.exists():
        return set()
    out = set()
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.add(json.loads(line)["qid"])
    return out


def ask_one(kb: str, question: str, timeout: int, agent: str = ""):
    t0 = time.time()
    if agent:
        cmd = [CLI, "session", "ask", "--agent", agent, "--format", "json", "--reference", question]
    else:
        cmd = [CLI, "chat", question, "--kb", kb, "--format", "json", "--reference"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    duration = round(time.time() - t0, 1)
    result = {"exit_code": proc.returncode, "stderr": proc.stderr[-500:], "duration_s": duration}
    if proc.returncode == 0 and proc.stdout.strip():
        try:
            result.update(parse_envelope(proc.stdout))
        except json.JSONDecodeError:
            result["answer"] = ""
            result["parse_error"] = proc.stdout[:500]
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--kb", default=DEFAULT_KB)
    ap.add_argument("--agent", default="", help="用指定自定义 agent 问答（session ask），不填走默认 chat")
    ap.add_argument("--qid", help="只跑指定题号")
    ap.add_argument("--sleep", type=float, default=2.0)
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    questions = load_questions()
    if args.qid:
        questions = [q for q in questions if q["qid"] == args.qid]
        if not questions:
            raise SystemExit(f"题单中没有 {args.qid}")
    if args.resume:
        done = done_qids(args.tag)
        questions = [q for q in questions if q["qid"] not in done]
        print(f"续跑：跳过已完成 {len(done)} 题，剩余 {len(questions)} 题")

    answers_dir = HERE / "answers"
    answers_dir.mkdir(exist_ok=True)
    out_path = HERE / f"{args.tag}-跑批结果.jsonl"

    for i, q in enumerate(questions, 1):
        qid = q["qid"]
        print(f"[{i}/{len(questions)}] {qid} ...", flush=True)
        try:
            result = ask_one(args.kb, q["question"], args.timeout, agent=args.agent)
        except subprocess.TimeoutExpired:
            result = {"exit_code": 124, "stderr": f"timeout after {args.timeout}s", "duration_s": args.timeout, "answer": ""}
        row = {**q, **result,
               "answer_head": (result.get("answer") or "")[:120],
               "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
        (answers_dir / f"{qid}.json").write_text(
            json.dumps(row, ensure_ascii=False, indent=1), encoding="utf-8")
        with open(out_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        head = (result.get("answer") or "")[:60].replace("\n", " ")
        print(f"    exit={result['exit_code']} {result['duration_s']}s refs={result.get('n_refs', 0)} | {head}", flush=True)
        if i < len(questions):
            time.sleep(args.sleep)

    print("完成:", out_path)


if __name__ == "__main__":
    main()
