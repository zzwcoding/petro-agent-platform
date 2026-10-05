# W-B4 审查拍（T1 关票前审查——只产发现清单，零修复动作）

任务：对主仓 `fix/wire-b4` 单 commit `0b573a4`（4 文件 +898/−210——B4 页面数据源切真后端两端点＋api/b4.js 新建＋测试）做关票前独立审查〔来源：票面 W-B4 审查节点节"T1"〕。注意：派发期间 master 前移三 commit（dev 自报全限 tickets 文档面）——本节核实无冲突面。

审查六节：

1. **diff 全量嗅探**：4 文件逐块定性（api/b4.js 新建/页面改写/两测试）；PAGES/EVIDENCE/CLAIMS/GLOSSARY/正文快照/CUR_VER/本地筛选/statusTagOf 退役零残留（grep）；零夹带。
2. **数据源切真核验**：两端点消费形状 vs 后端实装（master app/api/wiki.py——目录参数化/total/status 服务端字段/全文 content/claims/glossary_terms/related_objects）；snake→camel 折回正确性（wells.js 先例同构核对）。
3. **R-WIRE §3 逐条处置复核**：B4-1~B4-11 处置表逐条比对（重点：证据弹层懒加载未展开零请求＋无锚/锚失效 fail-closed 双层；`[[…]]` 五族标记解析器原样保留）。
4. **测试咬合力**：api 13 例＋页面 8 例——撤字段应红（反证抽 2）；空态（目录空）渲染断言；pages/__tests__/ 惯例位合规（Shell glob 红线）。
5. **curl 取证真实性**：dev 回报 curl 输出与后端当前实况复核（/api/wiki/pages 空态、404 wiki_not_found、fragments 404 探针——只读复核）。
6. **派发中 master 前移合规**：d7cac8e/824dd32/4b03ae7 三 commit 全限 tickets 文档面核实（-- web/ 零输出的独立复核）；rebase 无冲突面。

先读：dev 回报 `dispatch/results/W-B4.dev.md`；R-WIRE §3（差异清单真源）；teach B4 v0.4；主仓 `git show 0b573a4`＋master 现状。

框架红线：无。

边界红线：全程只读＋独立复跑（web 三连：eslint/vitest 266 基线/build），主树分支零写入；零修复动作；全新实例。

验收：以下全达才算过。
1. 六节结论逐项（通过/发现）。
2. 发现清单每条带 file:line＋影响评级＋建议处置。
3. 独立复跑数字附回报。
4. "零修复动作已执行"声明在末节。

回报：按 PROTOCOL 写 `dispatch/results/W-B4.rev.md`。
