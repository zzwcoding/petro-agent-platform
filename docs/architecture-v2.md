# 架构图 · Petro Data Agent V2

> 阶段 2 产物。图＝specs/modules.md 的可视投影；卡为准，图为导览。
> 审图纪律：用户逐节点过图，决策当场落盘；过审记 ADR。

```mermaid
flowchart TB
    subgraph 外部["V1 资产（只经数据面共享，双向禁引）"]
        V1APP[app/ V1 瀑布链<br/>端点不动·转归档候选]
        ONTO[ontology/ 本体真源<br/>导出物 sem_*]
        DATAPLANE[(共享数据面<br/>PG agg+sem+kb / Neo4j / MinIO)]
    end

    subgraph APPV2["appv2/（本版本唯一新建面）"]
        subgraph L4["api（薄端点）"]
            API["/api/v2/chat/*<br/>asks · resume · runs"]
        end
        subgraph L3["runtime（Harness 编排层·任务语义持有者）"]
            LOOP["有界 agent loop<br/>understand→plan→tool→<br/>observe→verify→answer"]
            CB["Context Builder<br/>确定性编译＋Manifest"]
            VS["Verifier 核验步<br/>断言↔Observation"]
            ST[("run / step 状态<br/>外置可恢复")]
            LOOP --> CB --> LOOP
            LOOP --> VS --> LOOP
            LOOP --> ST
        end
        subgraph L2["tools（受控行动唯一接触面·全只读）"]
            TR["ToolRegistry<br/>descriptors 渐进披露 / call"]
        end
        subgraph L1["engines（确定性能力）"]
            KNO["knowledge<br/>sem_* → Knowledge Evidence"]
            QEN["query<br/>六站链 Skill：校验/装配/<br/>三闸/血缘/新鲜度/降级"]
            REN["retrieval<br/>双路召回/精排/矛盾同窗/图谱"]
        end
        subgraph L0["infra（V1 复制·纪律原样）"]
            INFRA["config · db(只读) ·<br/>llm_client/gateway(B6) ·<br/>clock · security.audit"]
        end
        API --> LOOP
        LOOP --> TR
        TR --> KNO & QEN & REN
        KNO & QEN & REN --> INFRA
        QEN -. Evidence .-> KNO
    end

    WEB["web/ A1 问一问<br/>（本期只改事件渲染：loop 步视图）"]
    USER(["用户 · X-Dev-User"])

    USER --> WEB --> API
    INFRA --> GATEWAY[[LLM Gateway<br/>petro-main 单模型]]
    KNO & QEN & REN --> DATAPLANE
    ONTO --> DATAPLANE

    classDef safety fill:#fde,stroke:#c33;
    classDef new fill:#e8f6ff,stroke:#08c;
    class VS safety
    class LOOP,TR,KNO,QEN,REN new
```

## 节点说明（导览用）

1. **用户→web→api**：身份桩进 resolve_actor；api 薄，不持有编排语义。
2. **runtime**：唯一的"任务语义持有者"。loop 每步落 step；模型每轮所见经 Context Builder
   确定性编译并生成 Manifest（来源/版本/信任级/token——Q11 "判断依据里没有本体"的根治点）。
3. **tools**：agent 与世界的唯一接触面（书 6.1 受控行动链的工具侧）：参数 schema 校验、
   只读声明、错误分类（可重试|修参|拒答）、ASK 帧。INV-2 在此机器化。
4. **knowledge**：本体利用率的主战场——sem_* 台账读成 Evidence（含绑定状态/届满），
   别名八键、族标注全要素进 agent 语境。
5. **query**：V1 六站链原样移植为 Skill——三闸、新鲜度改绑、未绑定降级、缺参反问、
   越集审批全保留；输出权威表＋血缘卡。
6. **retrieval**：双路召回＋精排；供给策略本体化——**矛盾来源同窗并立**、截断显式
   （"召回 N/送窗 M"写进 window_note，治 Q11 的"材料未披露"虚答）。
7. **Verifier**：交付前核验步——每个断言必须有 Observation 支撑，无支撑→如实"未找到"。
   这是 INV-1/INV-4 在 loop 侧的落点；citation fail-closed 校验（确定性）在引擎侧不动。
8. **infra**：V1 复制层，B6 单出口/只读/审计纪律原样——appv2 不引入第二条 LLM 通路。
9. **共享边界**：V1↔V2 双向禁引；ontology 经导出物入数据面；web 只走 /api/v2 HTTP。
