"""真装配冒烟（KB_SMOKE=1 门控）——演示文本真传走完五步→台账/任务/向量可查。

P1-02b 增拍：wiki 支路真跑（真 LLM 百科页落库）→修正一片段→三联动真跑
（索引重建＋问题块重生＋wiki v+1 重铸）→回滚＋B12 审计留痕。
P1-05 增拍⑫：graph 支路真跑（抽取设置保存→confirm 定型 extract_snapshot→
真 LLM 逐 chunk 抽三元组→铁律三闸→过闸入图＋拦边留痕→整图可查；对号强
校拒存 400 带对号明细实证＋LLM 起草真跑＋B1 活动流/B12 审计）。

跑法（tickets/phase1/README.md P1-02a 验收）：
    KB_SMOKE=1 uv run pytest tests/test_kb_smoke_real.py -q

真装配含义：main.py lifespan 真起（真实 primary PG@5433 演示库＋ensure_kb_tables
含 pgvector 扩展）＋真 MinIO（compose reports 桶——presigned PUT 经 HTTP 真传，
平台不经手文件字节）＋真 gateway.complete（petro-main→MiniMax 线路，摘要/问题
块真生成——B6 唯一出口）。素材＝设定书 §A.1 井档案样本既有事实文本，零发明。
门控：环境变量 KB_SMOKE=1 未设即 skip（不进常规门禁——打真实 LLM 花钱）。
"""

import os
import time
import uuid

import pytest

pytestmark = [
    pytest.mark.skipif(
        os.environ.get("KB_SMOKE") != "1",
        reason="真装配冒烟需 KB_SMOKE=1（真实 PG/MinIO/LLM——不进常规门禁）",
    )
]

# 素材（设定书 §A.1 N-02 井档案样本＋§A.2 样本行既有事实——逐句注源，零发明）
DEMO_TEXT = """N-02 井完井报告（演示文本）

1 井基本情况
N-02 井（渤中28-1-N2）位于渤南区块 CEP-A 平台，井别采油（EW），
2019-06-15 投产，当前状态生产中。

2 完井段
完井段详见射孔与防砂参数表；防砂方式筛管完井。

3 投产信息
本井 2019-06-15 投产后维持自喷生产，日产油约 48.6 吨（§A.2 样本行）。
"""


def _wait_done(client: object, task_id: str, *, timeout: float = 180) -> dict:
    deadline = time.monotonic() + timeout
    last: dict = {}
    while time.monotonic() < deadline:
        last = client.get(f"/api/kb/tasks/{task_id}").json()  # type: ignore[attr-defined]
        if last["state"] in ("done", "failed", "stuck"):
            return last
        time.sleep(1.0)
    raise TimeoutError(f"任务未在 {timeout}s 内终态：{last}")


def test_real_assembly_smoke() -> None:

    from fastapi.testclient import TestClient

    from app.main import app

    tag = uuid.uuid4().hex[:6]
    with TestClient(app) as client:  # lifespan 真起——真 PG 建表＋真 MinIO/LLM 装配
        assert client.get("/health").json() == {"status": "ok"}

        # ① 建库（completion 完井报告类——四开关全开含图谱）
        lib = client.post(
            "/api/kb/libs",
            json={"lib_name": f"冒烟·完井报告库-{tag}", "biz_template": "completion"},
        )
        assert lib.status_code == 201, lib.text
        lib_id = lib.json()["lib_id"]

        # ①' 库配置保存（B12 裁决指令①——api 层写口真跑一次；同值保存不改定型语义）
        saved = client.put(
            f"/api/kb/libs/{lib_id}/config",
            json={"switches": {"semantic": True, "keyword": True, "wiki": True,
                               "graph": True},
                  "mode": "smart", "add_summary": True, "add_questions": True},
        )
        assert saved.status_code == 200, saved.text
        assert saved.json()["hint"].startswith("已保存——")

        # ①'' 抽取设置保存（B5 端点 3——P1-05）：对号强校通过值（本体对号表
        # 对齐的窄配置——只放行 隶属/受效，为 ⑫ 拦边实证留口）；confirm 时刻
        # 定型入 extract_snapshot（B9 组合根注入装载）；同事务记 B1 活动流。
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
                    {"sentence": "N-02 井隶属渤南区块。",
                     "triple": "N-02 —隶属→ 渤南"},
                    # 少量示例噪声：few-shot 携带清单外关系「投产」（真实运维中
                    # 配置漂移的常见形态）——诱导抽取尝试越出标签清单，由类型闸
                    # 拦下（合同演示被拦边「取样自」同族——拦下的边正是图在执
                    # 法的证据，F55 B）。
                    {"sentence": "本井 2019-06-15 投产后维持自喷生产，日产油约 48.6 吨。",
                     "triple": "N-02 —投产→ 2019-06-15"},
                ],
                "custom_instructions": "关系必须原文有依据；拿不准宁可跳过，不许创造新类型",
            },
        )
        assert ext_saved.status_code == 200, ext_saved.text
        assert ext_saved.json()["hint"] == "已保存——设置在下次入库时生效。"
        ext_view = client.get("/api/graph/extract-config",
                              params={"lib_id": lib_id}).json()
        assert ext_view["entity_types"] == ["井", "区块", "平台"]
        assert ext_view["saved_by"]  # who 服务端解析

        # ② 直传受理（两拍第一拍）——presigned PUT 真凭证
        up = client.post(
            "/api/kb/uploads",
            json={
                "filename": f"N-02 井完井报告（冒烟 {tag}）.txt",
                "size": len(DEMO_TEXT.encode("utf-8")),
                "lib_id": lib_id,
            },
        )
        assert up.status_code == 200, up.text
        receipt = up.json()
        assert receipt["bucket"] == "报告原文"

        # ③ 客户端直传对象存储（平台不经手文件字节——HTTP PUT 打真 MinIO）
        import httpx

        put_resp = httpx.put(receipt["put_url"], content=DEMO_TEXT.encode("utf-8"))
        assert put_resp.status_code == 200, put_resp.text

        # ④ 确认入库（两拍第二拍——config_snapshot 定型）→ 五步真跑
        confirm = client.post(f"/api/kb/uploads/{receipt['upload_id']}/confirm")
        assert confirm.status_code == 200, confirm.text
        confirm_body = confirm.json()
        assert confirm_body["state"] == "running"
        snapshot = confirm_body["config_snapshot"]
        final = _wait_done(client, confirm_body["task_id"])
        assert final["state"] == "done", final
        assert [n["key"] for n in final["nodes"]] == [
            "parse", "chunk", "embed", "index", "enrich",
        ]
        assert all(n["state"] == "finish" for n in final["nodes"])
        assert snapshot == final["config_snapshot"]  # 定型快照全程不变

        # ⑤ 产物两卡（真 LLM 生成——富化子任务失败不阻塞整卷（F32），
        # 故摘要/问题允许缺卡；缺卡即 LLM 子任务失败，管线仍 done）
        adds = client.get(f"/api/kb/tasks/{confirm_body['task_id']}/additions").json()
        if adds["summary"] is not None:
            assert adds["summary"]["type"] == "摘要块"
        if adds["questions"] is not None:
            assert adds["questions"]["items"]

        # ⑥ 台账/详情/任务/活动流
        reports = client.get(
            "/api/kb/reports", params={"keyword": tag}
        ).json()
        assert reports["total"] == 1
        report = reports["items"][0]
        assert report["status"] == "已入库" and report["refs"] > 0
        detail = client.get(f"/api/kb/reports/{report['id']}").json()
        assert detail["fragments"]
        tasks = client.get("/api/kb/tasks", params={"source": "上传入库"}).json()
        assert any(t["id"] == confirm_body["task_id"] for t in tasks["items"])
        acts = client.get(f"/api/kb/libs/{lib_id}/activities").json()
        actions = {a["action"] for a in acts["items"]}
        assert {"新建库", "上传报告", "入库完成"} <= actions

        # ⑦ 向量真库可查（pgvector——演示库直查）
        import asyncio

        from sqlalchemy import text

        from app.infra.config import load_database_specs
        from app.infra.db import ConnectionManager

        async def _count_vectors() -> int:
            manager = ConnectionManager(load_database_specs())
            try:
                async with manager.readonly() as session:
                    row = await session.execute(
                        text(
                            "SELECT count(*) FROM kb_fragment f "
                            "JOIN kb_report r ON r.id = f.report_id "
                            "WHERE r.id = :rid AND f.embedding IS NOT NULL"
                        ),
                        {"rid": report["id"]},
                    )
                    return int(row.scalar_one())
            finally:
                await manager.dispose()

        embedded = asyncio.run(_count_vectors())
        assert embedded > 0, "向量半边未落库（pgvector）"

        # ⑧ wiki 支路真跑（P1-02b）：IngestCompleted→真 LLM 重写→wiki 页落库 v1
        page_id = None
        for _ in range(240):
            pages = client.get("/api/wiki/pages", params={"keyword": tag}).json()
            if pages["total"] >= 1:
                page_id = pages["items"][0]["id"]
                break
            time.sleep(1.0)
        assert page_id, "百科页未在超时内生成"
        page = client.get(f"/api/wiki/pages/{page_id}").json()
        assert page["slug"] == page_id  # slug 稳定性＝id 承载
        assert page["source_report"]["id"] == report["id"]
        assert page["generation_source"] == "自动重建"
        assert page["operator"] == "系统（入库管线）"
        assert page["content"].strip()  # 真 LLM 自由 markdown 全文（所见皆完整版）
        assert "<!--WIKI-END-->" not in page["content"]  # 哨兵不入库
        versions = client.get(f"/api/wiki/pages/{page_id}/versions").json()
        assert versions["total"] == 1
        assert versions["items"][0]["task_no"] == confirm_body["task_id"]
        assert versions["items"][0]["desc"] == "首次生成（报告入库自动建页）"

        # ⑨ 修正一片段→三联动真跑：记版＋索引重建（重嵌）＋问题块重生＋wiki v+1
        frag = detail["fragments"][0]
        revise = client.post(
            f"/api/kb/reports/{report['id']}/fragments/{frag['id']}/revisions",
            json={"base_version": frag["version"],
                  "text": frag["text"] + "（勘误：补状态注记，注源 §A.1）"},
        )
        assert revise.status_code == 200, revise.text
        revise_body = revise.json()
        assert revise_body["versions"][-1]["note"] == "人工修正"  # v1 原始不可变
        rebuild = _wait_done(client, revise_body["task_id"], timeout=300)
        assert rebuild["source"] == "片段修正" and rebuild["state"] == "done"
        # FragmentRevised→重铸队列→复用生成管线→版本+1 来源「自动重建」
        recast_v = None
        for _ in range(300):
            versions = client.get(f"/api/wiki/pages/{page_id}/versions").json()
            if versions["total"] >= 2:
                recast_v = versions["items"][-1]
                break
            time.sleep(1.0)
        assert recast_v, "百科重铸未在超时内落版本"
        assert recast_v["source"] == "自动重建"
        assert recast_v["task_no"] == revise_body["task_id"]
        assert recast_v["desc"] == "片段修正后自动重建"
        # B1 台账 wiki 字段与 B4 current_version 同源同值
        reports = client.get("/api/kb/reports", params={"keyword": tag}).json()
        assert reports["items"][0]["wiki"] == f"v{recast_v['v']}"
        # 活动流：修正＋触发百科重铸
        acts = client.get(f"/api/kb/libs/{lib_id}/activities").json()
        assert any("修正片段" in a["action"] and "触发百科重铸" in a["target"]
                   for a in acts["items"])

        # ⑩ 回滚真跑（追加「回滚」来源新版本——可再滚回）
        rollback = client.post(
            f"/api/wiki/pages/{page_id}/rollback", json={"target_version": 1}
        )
        assert rollback.status_code == 200, rollback.text
        rb = rollback.json()
        assert rb["new_version"]["source"] == "回滚"
        assert rb["new_version"]["task_no"] is None  # 回滚无经由单号
        assert "内容恢复自 v1" in rb["banner"]
        audit = client.get("/api/security/audit-logs", params={"pageSize": 50}).json()
        audit_actions = {a["action"] for a in audit["items"]}
        assert {"kb.lib.created", "kb.config.saved", "kb.fragment.revised",
                "wiki.page.rolled_back"} <= audit_actions  # B12 补齐（裁决指令①）

        # ⑪ B2 质检复核队列闭环真跑（P1-04）：标记→409→驳回（理由必填）→重标
        # （旧单转已销记）→确认转修正流；活动流「标记问题片段」＋B12 审计
        frag_b2 = client.get(f"/api/kb/reports/{report['id']}").json()["fragments"][1]
        mark = client.post(f"/api/kb/fragments/{frag_b2['id']}/issue-reports")
        assert mark.status_code == 200, mark.text
        issue = mark.json()
        assert issue["state"] == "待质检复核"
        assert issue["hint"].startswith("已标记 · 待质检复核")
        dup = client.post(f"/api/kb/fragments/{frag_b2['id']}/issue-reports")
        assert dup.status_code == 409 and dup.json()["code"] == "kb_issue_duplicate"
        assert client.post(
            f"/api/kb/issue-reports/{issue['id']}/review", json={"action": "reject"}
        ).status_code == 400  # 驳回空理由 400
        rejected = client.post(
            f"/api/kb/issue-reports/{issue['id']}/review",
            json={"action": "reject", "reason": "冒烟驳回：片段与台账出入，请核对后重标"},
        )
        assert rejected.status_code == 200 and rejected.json()["state"] == "已驳回"
        remark = client.post(f"/api/kb/fragments/{frag_b2['id']}/issue-reports")
        assert remark.status_code == 200  # 重新标记＝新单入队、旧驳回单转已销记
        issue2 = remark.json()
        confirm = client.post(
            f"/api/kb/issue-reports/{issue2['id']}/review", json={"action": "confirm"}
        )
        assert confirm.status_code == 200 and confirm.json()["state"] == "已修正"
        assert client.get("/api/kb/issue-reports").json()["total"] == 0  # 队列零悬挂
        acts = client.get(f"/api/kb/libs/{lib_id}/activities").json()
        assert any(a["action"] == "标记问题片段" for a in acts["items"])  # F62 同事务
        audit = client.get("/api/security/audit-logs", params={"pageSize": 50}).json()
        assert {"kb.fragment.marked", "kb.issue.reviewed"} <= {
            a["action"] for a in audit["items"]
        }

        # ⑫ graph 支路真跑（P1-05）：confirm 定型 extract_snapshot→逐 chunk 真
        # LLM 抽三元组→铁律三闸→过闸入图＋拦边留痕；强校拒存实证＋起草真跑。
        net = None
        for _ in range(180):
            resp = client.get("/api/graph/net", params={"lib_id": lib_id})
            assert resp.status_code == 200, resp.text
            net = resp.json()
            if net["stats"]["edges"] >= 1:
                break
            time.sleep(1.0)
        assert net["stats"]["edges"] >= 1, "图谱支路未在超时内产出过闸边（真 LLM 抽取）"
        assert net["stats"]["nodes"] >= 2
        assert any(e["evidence_chunk_id"] and e["report_id"] for e in net["edges"])
        # 类型闸：节点类型＝该库 ExtractConfig 投影（窄配置——非配置类型不入图）
        assert {lg["type"] for lg in net["legend"]} <= {"井", "区块", "平台"}
        # 拦边留痕（配置只放行 隶属/受效——「位于 CEP-A 平台」承载类抽取必被
        # 类型闸拦下；被拦边不进图、只进对账镜像）
        blocked = None
        for _ in range(60):
            resp = client.get("/api/graph/blocked-edges", params={"lib_id": lib_id})
            assert resp.status_code == 200, resp.text
            blocked = resp.json()
            if blocked["stats"]["blocked"] >= 1:
                break
            time.sleep(2.0)
        assert blocked["stats"]["blocked"] >= 1, "被拦边清单无记录（三道闸未拦下任何抽取尝试）"
        assert {b["reason_code"] for b in blocked["blocked_edges"]} <= {
            "type_mismatch", "no_evidence", "uncertain",
        }
        assert all(b["report_id"] == report["id"] and b["reason"]
                   for b in blocked["blocked_edges"])
        # 强校拒存实证（接线后——对不上拒存 400 带对号明细）
        reject = client.put(
            "/api/graph/extract-config",
            json={
                "lib_id": lib_id,
                "entity_types": ["井", "机灵鬼"],
                "relation_tags": [{"rel": "管辖着", "example": "", "desc": ""}],
                "custom_instructions": "",
            },
        )
        assert reject.status_code == 400, reject.text
        assert reject.json()["code"] == "graph_ontology_mismatch"
        mismatches = reject.json()["detail"]["mismatches"]
        assert {m["value"] for m in mismatches} == {"机灵鬼", "管辖着"}
        assert all(m["nearest"] for m in mismatches)  # 最接近台账词条逐项带出
        # LLM 起草真跑（示例三源③——真 gateway.complete 统一出口）
        draft = client.post(
            "/api/graph/extract-config/draft-example",
            json={"lib_id": lib_id, "rel": "作用于"},
        )
        assert draft.status_code == 200, draft.text
        assert draft.json()["sentence"] and "→" in draft.json()["triple"]
        # F62 跨页留痕（保存同事务记 B1 活动流）＋B12 平台审计
        acts = client.get(f"/api/kb/libs/{lib_id}/activities").json()
        assert any(a["action"] == "修改抽取设置" for a in acts["items"])
        audit = client.get("/api/security/audit-logs", params={"pageSize": 50}).json()
        assert "graph.extract_config.saved" in {a["action"] for a in audit["items"]}
