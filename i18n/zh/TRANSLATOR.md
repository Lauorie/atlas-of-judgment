# 翻译任务说明（每个分块一份）

你负责把一个分块文件译成简体中文。分块在 `i18n/zh/chunks/chunk-NN.json`，格式：

```json
{ "s3f9a1c2d0e": { "en": "原文（可能含 HTML 标签或 ${...} 占位符）", "ctx": "所在页面 · 类型 · 位置" }, ... }
```

输出写到 `i18n/zh/chunks/chunk-NN.zh.json`，格式：

```json
{ "s3f9a1c2d0e": "译文", ... }
```

键与输入完全一致，一条不漏，不多不少。值为字符串。

## 流程

1. 通读 `i18n/zh/glossary.md`，术语与译名以它为准。
2. 读入分块，逐条翻译。ctx 里的 `block`/`run`/`attr` 是页面正文，`js`/`tpl` 是脚本里的界面文字（tooltip、坐标轴标题、图注、按钮），`island` 是数据岛里的标签与定义。
3. 用 Write 工具写出 `.zh.json`（必须是合法 JSON：字符串内的双引号写成 `\"`，换行写成 `\n`）。
4. 运行 `python3 scripts/zh/validate.py chunk-NN`。所有 `FAIL` 必须修到零；`warn` 逐条看一眼，属于误报（如数字改成中文数字、实体被合理改写）可放行，属于漏译要补。
5. 只改这一个 `.zh.json` 文件。不要改分块源文件、术语表、脚本或任何页面。
6. 最后回报：条数、FAIL 数（应为 0）、warn 数，以及你拿不准的译法（不超过 5 条）。

## 必须保留、原样照抄

- 所有 HTML 标签和它们的属性（`class`、`id`、`href`、`data-*`、`style`……）。例外：`title=""`、`aria-label=""`、`alt=""`、`placeholder=""` 的值是给读者看的，要翻译。
- `${...}` 占位符，包括内部的 JS 表达式，一个字符都不能动；顺序不能变。可以移动占位符在句中的位置以符合中文语序，但内容不变。
- HTML 实体：`&nbsp;` `&amp;` `&#8212;` `&thinsp;` 等。
- `<code>…</code>`、`<kbd>`、`<var>` 内部的内容。
- 数字、百分号、年份、罗马数字、小数、千分位（`1,009,592`）、统计量（κ、ICC、AUC、CI、SE、OR、σ、pp）。
- 文件名、URL、路径、标识符（`plate-xi#11-extend-leads`、`unit-taxonomy-2026-v1`、`review-logic-qwen-2026-full`）。
- 模型与工具名：DeepSeek、Qwen、Haiku、GPT、HDBSCAN、SQLite、OpenReview、ICLR、Hugging Face。
- 论文标题、审稿人代号、forum id、作者名。
- 审稿原句引语（英文引号 “…” 或 ‘…’ 内、`<q>`、`class="sq"`、`blockquote` 内的审稿原文）保留英文。引语外的说明文字译成中文。
- 标签里作为分隔符的 ` — `（前后有空格的破折号）和 ` · `，保留，位置对应。
- 箭头和符号：`→ ← ↔ ↗ ✓ × ≥ ≤ ± ▼ ①②③`。

## 译文风格

- 读者是中文 AI 工程师，熟悉 ICLR/OpenReview 审稿流程。
- 忠实、准确、短句、直接。不增删信息，不加解释性括注。
- 中文全角标点（，。；：？！）。中文与英文、数字之间留一个半角空格。
- 全大写的图内标签译成简短中文，保留符号：`POSITION IN THE REVIEW, CUT INTO FIFTHS →` → `评审中的位置，五等分 →`。
- 图表短标签控制在 2–6 个汉字。
- 编号：`Fig. 14b` → `图 14b`；`Plate XI` → `图版 XI`；`ACT III` → `第三幕`；`App. II` → `附录 II`；`§10` 保留。
- 拉丁文题词（如 `Vertebra prima, quae Atlas dicitur`、`theatrum judicii`）保留拉丁文，不译。
- 法律与解剖学隐喻（法则、裁决、判例、量刑表、控罪单、标本、解剖剧场）按术语表译，不要改成平铺直叙。
- 不用「不是……而是……」式套话，不堆副词，不总结情绪。
- 遇到片段式原文（如 `rated `、`'S DOCKET`、` · accepted <b>${pct(g.accept)}</b>`），它们会与其他片段拼接，译成同样可拼接的短片段，保留首尾空格与分隔符。
