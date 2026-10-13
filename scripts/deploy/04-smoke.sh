#!/usr/bin/env bash
# 云上冒烟：三题真打 :8001（台账/检索×2），判定四件（首帧/收场/答案/引标）。
# 用法（ECS 或任何可达机器）：bash 04-smoke.sh [host:port]
set -euo pipefail
BASE="${1:-http://127.0.0.1:8001}"
command -v python3 >/dev/null || { echo "需要 python3"; exit 1; }
python3 - "$BASE" <<'PYEOF'
import json, sys, time, urllib.request
base = sys.argv[1]
QUESTIONS = [
    ("smoke-1-台账", "什么是躺井？"),
    ("smoke-2-检索", "本井射孔总厚度、孔密、设计总孔数各是多少？"),
    ("smoke-3-检索", "8 月躺井多少井次？躺井率多少？按什么口径？"),
]
def run_one(qid, q):
    body = json.dumps({"question": q}).encode()
    req = urllib.request.Request(base + "/api/v2/chat/asks", data=body,
        headers={"Content-Type": "application/json", "X-Dev-User": "aqiang"})
    t0 = time.time(); answer, cites, run_id, status, err = [], 0, "", "", None
    et = ""
    with urllib.request.urlopen(req, timeout=180) as resp:
        for line in resp:
            s = line.decode("utf-8", "replace").strip()
            if s.startswith("event:"): et = s[6:].strip(); continue
            if not s.startswith("data:"): continue
            try: d = json.loads(s[5:])
            except Exception: continue
            if et == "session": run_id = str(d.get("run_id", ""))
            elif et == "text": answer.append(str(d.get("content", "")))
            elif et == "citation": cites += 1
            elif et == "verdict" and d.get("subtype") == "final": status = str(d.get("status", ""))
            elif et == "ask":
                print(f"  {qid} 挂起澄清（设计内）——resume 用 {{\"kind\":\"clarify\",\"choice\":\"<选项>\"}}")
                return {"qid": qid, "run_id": run_id, "suspended": True}
            elif et == "error": err = json.dumps(d, ensure_ascii=False)[:200]
    text = "".join(answer)
    ok = status == "completed" and len(text) >= (1 if qid.endswith("台账") else 100) and cites >= (0 if qid.endswith("台账") else 1)
    print(f"  {qid} {round(time.time()-t0,1)}s status={status} {len(text)}字 引标{cites} → {'✅' if ok else '❌'} | {text[:60]}")
    if err: print("   error帧:", err)
    return {"qid": qid, "run_id": run_id, "status": status, "pass": ok, "error": err}
rows = [run_one(q, t) for q, t in QUESTIONS]
print("SMOKE", "PASS" if all(r.get("pass") or r.get("suspended") for r in rows) else "FAIL")
PYEOF
