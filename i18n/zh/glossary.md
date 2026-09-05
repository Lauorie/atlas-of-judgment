# 术语表与翻译规范（Atlas of Judgment 中文版）

读者：中文 AI 工程师与研究者，熟悉 ICLR / OpenReview 的审稿流程。
目标：忠实、精确、短句、直接。不增删信息，不加解释性括注。保留原文的法律与解剖学隐喻，按下表统一译名。

## 一、硬性规则

1. 完全保留：HTML 标签与属性、`${...}` 占位符、HTML 实体（`&nbsp;` `&amp;` `&thinsp;` 等）、数字、百分号、年份、罗马数字、代码、文件名、URL、标识符（如 `plate-xi#11-extend-leads`）、模型名（DeepSeek、Qwen、Haiku、GPT）、ICLR、OpenReview、统计缩写（AUC、ICC、κ、CI、SE、OR）。
2. 英文引号内的审稿原句引语保留英文原文，不译。例：“we respectfully disagree” 原样保留；引语外的说明文字译成中文。
3. 论文标题、作者名、审稿人代号、forum id 不译。
4. 中文正文用全角标点（，。；：？！）。中文与英文、数字之间留一个半角空格。原文中的 `·` `—` `→` `↔` `×` 等符号保留。
5. 全大写的图内标签（如 `POSITION IN THE REVIEW, CUT INTO FIFTHS →`）译为简短中文，保留箭头等符号，不要全角化箭头。
6. 罗马数字图版编号保留：Plate XI → 图版 XI；ACT III → 第三幕；App. II → 附录 II。
7. 单词级标签（图表短标签）译成同样短的中文，控制在 2–6 个汉字。
8. 不要翻译 JSON 键名、CSS 类名、元素 id。
9. 译文里不要出现「不是……而是……」式套话，不要加副词堆砌，不要总结情绪。
10. 输出 JSON 的键必须与输入完全一致，值为译文字符串。

## 二、站名与结构

| 英文 | 中文 |
|---|---|
| Atlas of Judgment | 评判图谱（首次可写「评判图谱 · Atlas of Judgment」） |
| How a Paper is Judged | 一篇论文是如何被评判的 |
| plate | 图版 |
| figure | 图 |
| caption | 图注 |
| act | 幕 |
| coda | 尾声 |
| interlude | 间奏 |
| appendix | 附录 |
| reader's note | 读者须知 |
| the course | 导览路线 |
| the long rule（导航条） | 长标尺 |
| the machine reader / Machine Reader API | 机读接口 |
| deposition（每张图版的机读断言记录） | 存证 |
| claim | 断言 |
| derivation | 推导 |
| provenance | 溯源 |
| provenance door | 溯源入口 |
| corrections / correction record | 更正记录 |
| data island | 数据岛 |
| specimen | 标本 |
| storeroom | 库房 |
| cabinet | 陈列柜 |
| theatre / anatomical theatre / theatrum | 解剖剧场 |
| officina | 工坊 |
| About | 关于 |
| Method | 方法 |
| Resources | 资源 |

## 三、幕与图版标题

| 英文 | 中文 |
|---|---|
| I · The Instrument | 第一幕 · 仪器 |
| II · One Hand | 第二幕 · 一人之手 |
| III · The Law | 第三幕 · 法则 |
| IV · The Tariff | 第四幕 · 量刑表 |
| V · The Encounter | 第五幕 · 交锋 |
| VI · The Higher Court | 第六幕 · 上级法庭 |
| VII · The Measure | 第七幕 · 尺度 |
| VIII · Eras & Territories | 第八幕 · 时代与疆域 |
| Coda · The Archive | 尾声 · 档案 |
| Appendices | 附录 |
| I The Anatomy | 解剖 |
| II The Grammar | 语法 |
| III The Rhetoric | 修辞 |
| IV The Syntax | 句法 |
| V The Itinerary | 行程 |
| VI The Early Verdict | 早判 |
| VII The Elements | 要件 |
| VIII The Combination Clause | 组合条款 |
| IX The Unnamed Precedent | 无名判例 |
| X The Formulary | 套语集 |
| XI The Repair Manual | 修复手册 |
| XII The Verdicts | 裁决 |
| XIII The Charge Sheet | 控罪单 |
| XIV The Price | 代价 |
| XV The Consequence | 后果 |
| XVI The Shapes of Talk | 对话的形状 |
| XVII The Rebuttal | Rebuttal |
| XVIII The Moves | 招式 |
| XIX The Fate of an Objection | 一条异议的命运 |
| XX The Panel | 评审组 |
| XXI The Deliberation | 合议 |
| XXII The Higher Court | 上级法庭 |
| XXIII The Borrowed Verdict | 借来的裁决 |
| XXIV The Ladder | 阶梯 |
| XXV The Measurement | 度量 |
| XXVI The Drift | 漂移 |
| XXVII The Unamended Code | 未修订的法典 |
| XXVIII The Oracle | 神谕 |
| XXIX The Watermark | 水印 |
| XXX The Specimens | 标本 |
| App. I The Lexicon | 词汇表 |
| App. II Provenance & Method | 溯源与方法 |
| App. III The Null Cabinet | 零假设陈列柜 |

## 四、分类体系（12 审视对象 × 12 推理标准）

| 英文 | 中文 |
|---|---|
| logic unit / unit of evaluative logic | 逻辑单元 / 评价逻辑单元 |
| atomic unit | 原子单元 |
| object of scrutiny / inspected object | 审视对象 |
| reasoning standard | 推理标准 |
| valence / verdict (of a unit) | 判向 / 判定 |
| inference form | 推断形式 |
| taxonomy | 分类体系 |
| induced (taxonomy) | 归纳得到的 |
| Empirical scope & generalizability | 实证范围与泛化性 |
| Baselines & ablations | 基线与消融 |
| Theory, assumptions & guarantees | 理论、假设与保证 |
| Method design rationale | 方法设计依据 |
| Compute cost & scalability | 计算成本与可扩展性 |
| Clarity & presentation | 清晰度与表述 |
| Novelty & contribution | 新颖性与贡献 |
| Related work & citations | 相关工作与引用 |
| Statistical rigor & metrics | 统计严谨性与指标 |
| Robustness & sensitivity | 鲁棒性与敏感性 |
| Reproducibility & code | 可复现性与代码 |
| Problem framing & motivation | 问题界定与动机 |
| Novelty standard | 新颖性标准 |
| Claim-evidence scope matching | 主张与证据范围匹配 |
| Fair comparison norm | 公平比较规范 |
| Statistical identifiability | 统计可辨识性 |
| Confound / alternative explanation | 混杂因素 / 替代解释 |
| Design justification demand | 设计论证要求 |
| Robustness norm | 鲁棒性规范 |
| Practical cost-benefit | 实际成本收益 |
| Measurement construct validity | 测量构念效度 |
| Reproducibility norm | 可复现性规范 |
| Presentation as trust signal | 表述即信任信号 |
| Merit recognition | 价值认可 |
| 短标签：novelty / claim↔evid. / fair comp. / design / cost-benefit / confound / robustness / presentation / repro. / statistics / validity / merit | 新颖性 / 主张↔证据 / 公平比较 / 设计 / 成本收益 / 混杂 / 鲁棒性 / 表述 / 复现 / 统计 / 效度 / 价值 |
| 短标签：empirical scope / baselines / theory / method design / compute cost / clarity / novelty / related work / stats & metrics / robustness / reproducib. / framing | 实证范围 / 基线 / 理论 / 方法设计 / 计算成本 / 清晰度 / 新颖性 / 相关工作 / 统计与指标 / 鲁棒性 / 可复现 / 问题界定 |
| negative / uncertain / mixed / conditional / positive | 否定 / 存疑 / 混合 / 有条件 / 肯定 |
| norm / can't-verify / precedent / scope / rival-cause / on-balance（六种推断形式） | 规范 / 无法核验 / 判例 / 范围 / 竞争解释 / 权衡 |
| ground / warrant / demand | 依据 / 理据 / 要求 |
| GROUND · WHAT WAS SEEN | 依据 · 所见 |
| WARRANT · THE RULE INVOKED | 理据 · 所援引的规则 |
| DEMAND · WHAT WAS ASKED | 要求 · 所求 |
| observation / reasoning / judgment / suggested improvement | 观察 / 推理 / 判断 / 改进建议 |
| remedy：articulate / evidence / method / report / none | 修复：阐明 / 补证据 / 改方法 / 补报告 / 无 |
| WORK OF RESEARCH — SUBSTANTIATE | 研究之工 — 实证 |
| WORK OF WRITING — ARTICULATE | 写作之工 — 阐明 |
| WORK OF DISCLOSURE — DISCLOSE | 披露之工 — 披露 |

## 五、评审流程

| 英文 | 中文 |
|---|---|
| review | 评审 / 评审意见 |
| reviewer | 审稿人 |
| author | 作者 |
| rebuttal | rebuttal（保留英文，作名词用） |
| author response | 作者回应 |
| area chair / AC | 领域主席（AC） |
| program chair | 程序主席 |
| meta-review | 元评审 |
| decision | 录用决定 |
| accept / reject | 接收 / 拒稿 |
| Accept (Poster) / Spotlight / Oral | 保留英文 |
| score / rating | 评分 |
| confidence | 置信度 |
| forum（OpenReview 上一篇论文的讨论页） | forum（保留英文） |
| review-level track | 评审级轨道 |
| forum-level track | forum 级轨道 |
| panel | 评审组 |
| tribunal | 评审庭 |
| docket | 案卷 |
| deliberation | 合议 |
| the bench | 法官席 |
| overrule | 推翻 |
| mercy | 宽宥 |
| softening / entrenchment / reversal / split verdict / unanimity | 软化 / 固守 / 反转 / 分歧裁决 / 一致 |
| held / clarified / weakened / strengthened / reversed | 维持 / 澄清 / 减弱 / 加强 / 反转 |
| objection | 异议 |
| charge | 指控 |
| criticism / praise | 批评 / 称许 |
| verdict | 裁决 |
| precedent | 判例 |
| jurisprudence | 判例法 |
| the law / a law（作为推理标准的隐喻） | 法则 |
| rule（如 the breadth rule） | 规则（如：广度规则） |
| clause | 条款 |
| code（法典义） | 法典 |
| tariff | 量刑表 |
| price / cost（of an objection） | 代价 |
| repair / prescribed repair | 修复 / 指定修复 |
| boilerplate | 套话 |
| formulary | 套语集 |
| fate（of an objection） | 命运 |
| move（rebuttal 中的招式） | 招式 |
| The contest / clarification / promissory note / concession / courtesy / amended manuscript / delivered experiment | 争辩 / 澄清 / 承诺 / 让步 / 致谢 / 修订稿 / 补做的实验 |

## 六、方法与统计

| 英文 | 中文 |
|---|---|
| pipeline | 流水线 |
| three-layer pipeline | 三层流水线 |
| memo（DeepSeek analytic memo） | 分析备忘 |
| schema-constrained structuring | 模式约束的结构化 |
| classifier | 分类器 |
| cross-validated | 交叉验证的 |
| null / null model / null test | 零假设 / 零模型 / 零检验 |
| failed its null | 未通过零检验 |
| mirage | 幻象 |
| retired（analysis） | 撤下 |
| pre-registration / pre-registered | 预注册 |
| frozen（plan） | 冻结 |
| reliability | 信度 |
| aptness | 贴切性 |
| carving | 切分 |
| drift | 漂移 |
| hardening | 趋严 |
| era | 时代 |
| territory | 疆域 |
| archipelago / island（主题群岛） | 群岛 / 岛 |
| sky / galaxy（星空图） | 星空 |
| oracle | 神谕 |
| watermark | 水印 |
| vocabulary signature | 词汇指纹 |
| LLM-era | LLM 时代 |
| co-review wording converges | 同稿评审用语趋同 |
| corpus-level only | 仅在语料层面 |
| intraclass correlation | 组内相关系数 |
| effect size | 效应量 |
| odds ratio | 优势比 |
| decile / quintile / fifths | 十分位 / 五分位 / 五等分 |
| error bars | 误差棒 |
| significance | 显著性 |
| seed | 随机种子 |
| ground truth | 真值 |
| machine reading | 机器读取 |
| overclaim | 过度声称 |
| GPU-hours | GPU 小时 |
