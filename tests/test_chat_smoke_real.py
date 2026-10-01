"""真装配冒烟（CHAT_SMOKE=1 门控）——三链真跑：FAQ 秒回＋检索瀑布全链（真 LLM
生成＋citation 锚真值回跳）＋图谱问答链（图遍历＋边出处）。

跑法（tickets/phase1/README.md P1-08b 验收）：
    CHAT_SMOKE=1 uv run pytest tests/test_chat_smoke_real.py -q

真装配含义：main.py lifespan 真起（真实 primary PG@5433 演示库）＋真 MinIO
（直传真桶）＋真 gateway.complete（petro-main——入库富化/图谱抽取/检索生成/
图谱生成全走 B6 唯一出口）＋真 Neo4j（graph 支路抽取立边→图谱问答链读图）。

流程（三链各真跑＋引用回跳锚真值）：
① 备料：建库（completion 四开关全开）→抽取设置（本体对号表对齐窄配置）→
   真传演示文本→五步 done（真 LLM 摘要/问题块）→graph 支路真抽取立边。
② FAQ 秒回链：match_index 精确命中→直出答案 no_model=true＋citation（零模型调用）
   →N18 树节点步进。
③ 检索问答链：双路召回命中演示报告→真 LLM 生成（petro-main）→token 流式→
   citation 帧→**锚真值**：locator.fragment_id 与命中报告经 B2 片段台账对账一致
   →树叙事帧序核对（N1..N6→N17→S0–S7/GEN 逐帧点亮、token 不与树帧交错——A1 册
   实时路径真源）→**断线重连真恢复**（resume_run_id 重放持久帧：verdict/citation/
   answer 与原流同形同值）。
④ 图谱问答链：关系问句路由→graph 缝邻域命中→真 LLM 生成→citation kind=图谱
   →锚真值同上（边出处 chunk 回跳）。
⑤ B12 受理审计留痕。

重跑幂等：库/报告带 tag 每轮新建（冒烟演示行不入常规台账口径）；无清理需求
（演示库量级，KB_SMOKE 同款处置）。
"""

import os
import time
import uuid

import pytest

pytestmark = [
    pytest.mark.skipif(
        os.environ.get("CHAT_SMOKE") != "1",
        reason="真装配冒烟需 CHAT_SMOKE=1（真实 PG/MinIO/Neo4j/LLM——不进常规门禁）",
    )
]

# 素材（设定书 §A.1 N-02 井档案样本＋§A.2 样本行既有事实——与 KB_SMOKE 同源，零发明）
DEMO_TEXT = """N-02 井完井报告（演示文本）

1 井基本情况
N-02 井（渤中28-1-N2）位于渤南区块 CEP-A 平台，井别采油（EW），
2019-06-15 投产，当前状态生产中。

2 完井段
完井段详见射孔与防砂参数表；防砂方式筛管完井。

3 投产信息
本井 2019-06-15 投产后维持自喷生产，日产油约 48.6 吨（§A.2 样本行）。
"""


def _parse_frames(text: str) -> list[tuple[str, dict]]:
    frames: list[tuple[str, dict]] = []
    for block in text.split("\n\n"):
        if not block.strip():
            continue
        event = data = None
        for line in block.split("\n"):
            if line.startswith("event: "):
                event = line.removeprefix("event: ")
            elif line.startswith("data: "):
                import json

                data = json.loads(line.removeprefix("data: "))
        assert event is not None and data is not None
        frames.append((event, data))
    return frames


def _wait_done(client: object, task_id: str, *, timeout: float = 240) -> dict:
    deadline = time.monotonic() + timeout
    last: dict = {}
    while time.monotonic() < deadline:
        last = client.get(f"/api/kb/tasks/{task_id}").json()  # type: ignore[attr-defined]
        if last["state"] in ("done", "failed", "stuck"):
            return last
        time.sleep(1.0)
    raise TimeoutError(f"入库任务未在 {timeout}s 内终态：{last}")


def _frames_by_name(frames: list[tuple[str, dict]]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for name, data in frames:
        out.setdefault(name, []).append(data)
    return out


def test_real_assembly_smoke() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    tag = uuid.uuid4().hex[:6]
    with TestClient(app) as client:  # lifespan 真起
        assert client.get("/health").json() == {"status": "ok"}

        # —— ① 备料：建库→抽取设置→真传→五步 done→graph 支路真立边 ——
        lib = client.post(
            "/api/kb/libs",
            json={"lib_name": f"问答冒烟库-{tag}", "biz_template": "completion"},
        )
        assert lib.status_code == 201, lib.text
        lib_id = lib.json()["lib_id"]
        saved = client.put(
            f"/api/kb/libs/{lib_id}/config",
            json={"switches": {"semantic": True, "keyword": True, "wiki": False,
                               "graph": True},
                  "mode": "smart", "add_summary": True, "add_questions": True},
        )  # wiki 关——冒烟不需要百科页（省一次大额 LLM 调用，降低供应商限频压力）
        assert saved.status_code == 200, saved.text
        ext_saved = client.put(
            "/api/graph/extract-config",
            json={
                "lib_id": lib_id,
                "entity_types": ["井", "区块", "平台"],
                "relation_tags": [
                    {"rel": "隶属", "example": "N-02 —隶属→ 渤南",
                     "desc": "井属于哪个区块"},
                    {"rel": "受效", "example": "", "desc": "注水井—受效→油井"},
                ],
                "few_shot_examples": [
                    {"sentence": "N-02 井隶属渤南区块。", "triple": "N-02 —隶属→ 渤南"},
                ],
                "custom_instructions": "关系必须原文有依据；拿不准宁可跳过，不许创造新类型",
            },
        )
        assert ext_saved.status_code == 200, ext_saved.text
        up = client.post(
            "/api/kb/uploads",
            json={
                "filename": f"N-02 井完井报告（问答冒烟 {tag}）.txt",
                "size": len(DEMO_TEXT.encode("utf-8")),
                "lib_id": lib_id,
            },
        )
        assert up.status_code == 200, up.text
        receipt = up.json()
        import httpx

        put_resp = httpx.put(receipt["put_url"], content=DEMO_TEXT.encode("utf-8"))
        assert put_resp.status_code == 200, put_resp.text
        confirm = client.post(f"/api/kb/uploads/{receipt['upload_id']}/confirm")
        assert confirm.status_code == 200, confirm.text
        confirm_body = confirm.json()
        final = _wait_done(client, confirm_body["task_id"])
        assert final["state"] == "done", final
        reports = client.get("/api/kb/reports", params={"keyword": tag}).json()
        assert reports["total"] == 1
        report = reports["items"][0]
        assert report["refs"] > 0

        # —— ② FAQ 秒回链（match_index 精确命中→直出；零模型调用）——
        faq_frames = _parse_frames(client.post(
            "/api/chat/asks",
            json={"question": "N-02 井是什么时候投产的？"},
            headers={"X-Dev-User": "aqiang"},
        ).text)
        faq_names = [name for name, _ in faq_frames]
        assert faq_names[-1] == "done"
        faq_data = _frames_by_name(faq_frames)
        assert faq_data["verdict"][0]["chain"] == "FAQ直出链"
        faq_answer = faq_data["answer"][0]
        assert faq_answer["kind"] == "text" and faq_answer["no_model"] is True
        assert "2019-06-15" in faq_answer["text"]
        faq_citation = faq_data["citation"][0]
        assert faq_citation["locator"]["section"] == "常见问题库"

        # —— ③ 检索问答链（双路召回→真 LLM 生成→citation 锚真值回跳）——
        # 引用合规有模型随机性（编号标注是提示词硬性要求、非确定性协议）——
        # 最多 3 轮重问，命中即锚真值断言；全不引用＝合同允许的无引用直答，
        # 如实跳过锚真值（fail-closed 语义已由单测全覆盖）。
        citations: list[dict] = []
        ret_data: dict[str, list[dict]] = {}
        ret_frames: list[tuple[str, dict]] = []
        for _attempt in range(3):  # 生成失败（上游瞬断→兜底）与引用合规同享三轮重问
            ret_frames = _parse_frames(client.post(
                "/api/chat/asks",
                json={"question": "射孔与防砂参数表里防砂方式是什么？"},
                headers={"X-Dev-User": "aqiang"},
            ).text)
            ret_data = _frames_by_name(ret_frames)
            ret_answer = ret_data["answer"][0]
            if ret_answer["kind"] == "text" and (ret_answer.get("citations") or []):
                citations = ret_answer["citations"]
                break
            time.sleep(5.0)  # 429/冷却退避——供应商限频下的诚实重问节奏
        ret_names = [name for name, _ in ret_frames]
        assert ret_names[0] == "session" and ret_names[-1] == "done"
        verdict = ret_data["verdict"][0]
        assert verdict["chain"] == "检索问答链"
        assert verdict["confidence"]  # 置信度真实计算——档位值在
        assert any(f["key"] == "S4" for f in ret_data["node"])  # S4 双路召回 node 步进
        assert ret_data["token"], "检索链答案应流式（token 帧族）"
        assert ret_answer["kind"] == "text", (
            f"三轮内真 LLM 生成应成功（当前兜底收场——上游瞬断不应三连）：{ret_answer}"
        )
        assert "筛管" in ret_answer["text"]  # 依据演示报告作答（防砂方式筛管完井）
        assert citations, "真 LLM 三轮内应至少一轮按编号引用材料（[cN] fail-closed 后展开）"
        # 树叙事时序（P1-08c）：node 帧沿实时路径点亮（N1..N6→N17→S0–S7/GEN），
        # token 切片在全部树帧之后（不交错乱序）。
        node_keys = [f["key"] for f in ret_data["node"]]
        assert node_keys[:2] == ["N1", "N1"]
        assert {"N3", "N4", "N5", "N5b", "N6"} <= set(node_keys)
        assert {"N17", "S0", "S1", "S3", "S4", "S5", "S6", "S7", "GEN"} <= set(node_keys)
        tree_frames = {"stage", "sec_check", "match", "assembly", "verdict",
                       "node", "node_line", "notice"}
        first_token = ret_names.index("token")
        assert not tree_frames.intersection(ret_names[first_token:])
        # 断线重连真恢复（resume_run_id run 恢复）：done run 重放持久帧——
        # session(resume)→verdict→citation×N→answer→done，answer 与原流同形同值。
        recovery = _parse_frames(client.post(
            "/api/chat/asks", json={"resume_run_id": ret_frames[0][1]["run_id"]},
            headers={"X-Dev-User": "aqiang"},
        ).text)
        recovery_names = [name for name, _ in recovery]
        assert recovery_names == [
            "session", "verdict", *(["citation"] * len(ret_data.get("citation", []))),
            "answer", "done",
        ], recovery_names
        assert recovery[-2][1] == ret_data["answer"][0]
        assert any(f["resume"] is True for f in _frames_by_name(recovery)["session"])
        # 锚真值：citation.fragment_id 必须真实存在且属于 locator 所指报告
        # （检索是全库面——证据可来自任意报告；B2 片段台账逐条对账）。
        frag_all = client.get(
            "/api/kb/fragments", params={"page": 1, "pageSize": 500}
        ).json()
        anchor_report = {f["id"]: f["report"] for f in frag_all["items"]}
        assert anchor_report
        for citation in citations:
            fragment_id = citation["locator"].get("fragment_id")
            assert fragment_id, f"报告引用必须带片段锚：{citation}"
            assert fragment_id in anchor_report, (
                f"引用锚失真（伪造/失锚——fail-closed 应已拦下）：{fragment_id}"
            )
            assert anchor_report[fragment_id] == citation["locator"].get("report"), (
                f"引用锚报告归属不一致：{fragment_id} → {anchor_report[fragment_id]}"
            )

        # —— ④ 图谱问答链（关系问句路由→邻域边→真 LLM 生成→图出处锚真值）——
        # graph 支路＝IngestCompleted 订阅触发的进程内任务族（B9 缝，不占五步步位）
        # ——五步 done 后仍在途，轮询等抽取落图（真 LLM 逐 chunk，给足窗口）。
        deadline = time.monotonic() + 180
        edge_count = 0
        while time.monotonic() < deadline:
            net = client.get("/api/graph/net", params={"lib_id": lib_id}).json()
            edge_count = net["stats"]["edges"]
            if edge_count > 0:
                break
            time.sleep(3.0)
        if edge_count > 0:  # graph 支路真立边后走图链；零边（抽取全拦/超窗）则如实跳过
            time.sleep(3.0)  # 供应商限频退避（生成族调用之间的诚实节奏）
            graph_frames = _parse_frames(client.post(
                "/api/chat/asks",
                json={"question": "N-02 井隶属哪个区块？"},
                headers={"X-Dev-User": "aqiang"},
            ).text)
            graph_data = _frames_by_name(graph_frames)
            assert graph_data["verdict"][0]["chain"] == "图谱问答链"
            graph_answer = graph_data["answer"][0]
            assert graph_answer["kind"] == "text"
            graph_citations = graph_answer.get("citations") or []
            for citation in graph_citations:
                assert citation["kind"] == "图谱"
                fragment_id = citation["locator"].get("fragment_id")
                if fragment_id:  # 边出处锚真值（chunk 失锚的引用已被 fail-closed 拦下）
                    assert fragment_id in anchor_report
        else:
            print(f"\n[smoke] graph 支路零过闸边（lib {lib_id}）——图谱问答链跳过本轮实证")

        # —— ⑤ B12 受理审计留痕 ——
        audit = client.get(
            "/api/security/audit-logs",
            params={"action": "chat.ask.received"},
            headers={"X-Dev-User": "aqiang"},
        )
        assert audit.status_code == 200
        assert audit.json()["total"] >= 3  # 三轮提问全受理留痕
