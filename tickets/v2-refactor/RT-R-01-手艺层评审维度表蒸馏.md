# RT-R-01 · 手艺层评审维度表蒸馏（阶段 5/7 工序挂接素材票）

状态: **草案（待主窗派工）** ｜ 类型: 工序侧票——**不属 17 块模块票册、不入五波序**，与 W1–W5 并行零冲突
所属工序: `docs/runtime-refactor/规划.md` §五 步骤 4（阶段 5 code-review 手艺层检查节）＋步骤 6（阶段 7 块粒度反过度工程审视）

## 任务

新建仓内文档 `docs/runtime-refactor/craft-rubric.md`（手艺层评审维度表），内容＝两部分：

**第一部分·反过度工程四问＋Key Questions 三问**（逐字稿①，英文原文逐字在场）——阶段 7 体检的块粒度审视维度。

**第二部分·手艺层检查项 10 条**（逐字稿②，英文原文逐字在场）——阶段 5 code-review 新增检查节的素材；每条之下的「仓内落法」小节只许引用仓内既有规矩（B1–B16／裸字面值治理先例／DEBT 标签挂法），外文例只许出现在逐字稿展示位，不得进落法。

> 逐字稿载体（AGENTS.md 6b）：本票任务所引「反过度工程四问」「Key Questions 三问」「手艺层检查项 10 条」三段英文原文，均以引用块逐字照抄于下文「逐字稿载体」节（来源＝外部 skill nathankim0/clean-architecture-skills，MIT，2026-10-16 主窗选段）；施工子代理对逐字稿只许照抄，偏离即停报 L0，不自行裁量。

先读: `docs/runtime-refactor/规划.md` §五；AGENTS.md 硬纪律 6b（逐字稿纪律）；`docs/runtime-refactor/eng/02-规格防漂移要求.md`（定位：十节版式规格钉「块做什么」，本表补规格层以下的手艺层）；`tools/debt_markers.py`（DEBT 标签挂法先例）；`tools/importlinter_v2.toml`（B1–B16 机检契约面）

框架红线: 无（纯文档票，零代码零框架零依赖）
边界红线: ① 本票只产 `docs/runtime-refactor/craft-rubric.md` 一份新文档，不触碰 `specs/`、`appv2/`、`tools/`、测试树；② 逐字稿条目只许照抄；「仓内落法」每条规矩必须有引用形（引用块／文件:行），新造条目＝停笔停报 L0；③ 本票不改 `规划.md`——两处挂接行已由主窗随票落库

> 逐字稿载体（AGENTS.md 6b）：以下三段均为外部 skill 原文逐字照抄（来源 [nathankim0/clean-architecture-skills](https://github.com/nathankim0/clean-architecture-skills)，MIT，2026-10-16 主窗选段）；施工子代理对逐字稿只许照抄，偏离即停报 L0，不自行裁量。

### 逐字稿①：反过度工程四问＋Key Questions 三问（clean-architecture SKILL.md「Important Notes」节原文）

> ### Practical Verification
>
> Ask yourself if you're really benefiting from Clean Architecture:
> - Is it the layer separation that helps, or just IDE auto-refactoring?
> - Is a Repository interface with only one implementation really necessary?
> - Are you over-abstracting for a 0.001% chance of future change?
> - Can you rename a class in outer modules without affecting inner modules?

> Always consider these questions during review:
> - "Does this separation actually provide benefits?"
> - "Is the dependency rule truly being followed?"
> - "Is the impact scope minimized when changes occur?"

### 逐字稿②：手艺层检查项 10 条（kent-beck-style SKILL.md 原文）

1. > **Always replace magic numbers with named constants.**

   同节示例（原文展示位）：

   > ```typescript
   > // Good: Named constants
   > const MIN_PASSWORD_LENGTH = 8;
   > if (password.length < MIN_PASSWORD_LENGTH) { ... }
   > ```

2. Naming Guidelines（原文）：

   > - **Variables**: Nouns describing what they hold
   > - **Functions**: Verbs describing what they do
   > - **Booleans**: Questions that can be answered yes/no
   > - **Classes**: Nouns describing what they represent

3. > #### Replace Nested Conditional with Guard Clauses
   > Use early returns to reduce nesting.

4. > #### Comments (as smell)
   > - Comments explaining what code does (instead of why)
   > - Often indicates code that should be clearer

   同卡另句（原文）：

   > Code should express its intent without comments.

5. > #### Dead Code
   > - Unreachable or unused code
   > - **Refactoring**: Remove Dead Code

6. > #### Duplicate Code
   > - Same code structure in multiple places

7. > #### Long Method
   > - Methods doing too many things

   对应技法（原文）：

   > **Extract Method** — The most important refactoring. Turn code fragments into methods with intention-revealing names.

8. > #### Primitive Obsession
   > - Overuse of primitives instead of small objects

9. > #### Feature Envy
   > - Method uses another class's data more than its own

10. 简单设计四规则（原文，优先级序）：

    > 1. **Passes the Tests** - Code must work correctly
    > 2. **Reveals Intent** - Code should clearly express its purpose
    > 3. **No Duplication** - DRY (Don't Repeat Yourself)
    > 4. **Fewest Elements** - Minimize classes, methods, and code

### 仓内落法的引用规矩（逐条检查项的「仓内落法」小节只许引以下来源）

- B1–B16 边界规则：`AGENTS.md` 硬纪律 2–4 ＋ `tools/importlinter_v2.toml` 契约面（引用块或文件:行）；
- 裸字面值治理先例：`docs/runtime-refactor/eng/04a-应钉行为清单.md` 中 D-L1a-12 相关行（文件:行引用）；
- DEBT 短语挂法：`tools/debt_markers.py` 的判定规则（文件:行引用）。

验收: 以下判据逐条全绿为过——
- `docs/runtime-refactor/craft-rubric.md` 在场，含「反过度工程四问」＋「Key Questions 三问」＋手艺层 10 条，英文原文逐条在场且与逐字稿逐字一致（13 组逐字比对：四问＋三问＋10 条）；
- 每条手艺层检查项带「仓内落法」小节，小节内每条规矩有引用形（引用块／文件:行）；
- 文档正文零 TS/Java 落法（外文例只许出现在逐字稿展示位）；
- `git status` 显示除该新文档外零触碰（`specs/`、`appv2/`、`tools/`、测试树均无改动）；
- `.venv/bin/python tools/ticket_shape_check.py tickets/v2-refactor/RT-R-01-手艺层评审维度表蒸馏.md` 绿。

回报: 完成后回主窗——「RT-R-01 完成，产物 docs/runtime-refactor/craft-rubric.md，偏差: 有/无（有则逐条列），逐字比对: 13/13 过」。对逐字稿任何一行偏离即停笔停报 L0，不落盘。
