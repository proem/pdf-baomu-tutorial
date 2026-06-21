---
name: pdf-baomu-tutorial
description: |
  生成“保姆级教程”风格的 PDF 文档。采用封面全出血灰色渐变、中文数字章节（零壹贰叁）、
  紫色“让 Claude Code 帮你”引导块、黑色圆形步骤编号、三色语义高亮框（蓝提示、黄警告、红禁止、
  紫 Claude Code）的视觉风格。
  
  当用户说“帮我做一份 PDF”、“生成教程 PDF”、“用保姆教程风格写”、“小白向教程”、“把这个变成 PDF”、
  “做成那个风格的 PDF”、“生成一份文档”、“出一份 PDF”时触发。也适用于用户提供一个主题或已有
  Markdown 草稿，希望输出成格式精美、面向小白的 PDF 教程文档的场景。即使用户只说“做个 PDF 出来”
  或“把我们刚聊的做成文档”，只要上下文涉及教程 / 指南 / 说明文档的输出，都应优先触发此 skill，
  因为这是用户已经确认满意的默认 PDF 风格。
license: MIT
---

# 保姆教程风格 PDF 生成

生成“小白向保姆教程”风格的 PDF 文档。这套风格的核心是：**技术门槛降到最低，把需要敲命令的
地方都改写成“发给 Claude Code 的中文指令”**，让用户复制粘贴即可。

## 壹 风格内核

这份风格为什么能打动人？三件事：

- **可执行** — 读者不需要理解每条命令在干嘛，看流程 + 复制 Claude Code 指令 = 跑起来
- **分层** — 封面、目录、章节、步骤、代码、引导块、警告框，每一层都有明确的视觉定位
- **克制** — 用色只有 5 种（黑、紫、蓝、黄、红），留白充足，不堆砌装饰

写作风格遵循一套固定节奏：概念 → 为什么重要 → 怎么理解 → 实际例子 → 总结。用“我们”
和“大家”拉近距离，不说教。

## 贰 工作流程

### 2.1 先搞清楚用户想要什么

在动手前，至少确认这几件事：

1. **主题是什么** — 是挂载网盘？还是部署某个服务？还是某个工具的入门？
2. **目标读者** — 纯小白？有基础但怕踩坑？工程师想要速查？
3. **有没有已有素材** — 用户可能已经给过一段 Markdown 草稿或者聊天记录，先找到它
4. **PDF 是给谁看的** — 发朋友圈？投稿知识星球？公司内部？

如果用户只给了主题没给素材，先做研究（web_search），把事实面盘清楚再动笔。

### 2.2 内容撰写

先写 HTML 正文内容（不要一上来就套模板）。内容结构遵循下面的“叁 文档结构模板”。

**写作要点**：
- 开篇有一句点题 + 一个设问
- 技术概念必须配日常比喻
- 每个 Claude Code 指令块放在关键动手步骤处
- 章节数量控制在 6-9 章为宜
- 每章不超过 2 页内容（否则拆分）

### 2.3 套用 HTML 模板

用 `templates/tutorial-template.html` 作为骨架。把它复制到工作目录，改 title 和内容。**只需要复制 HTML 一个文件**——样式表 `templates/styles.css` 会由 `build_pdf.py` / `preview_all.py` 在渲染时自动注入，用户工作目录下不需要 styles.css 或 fonts/ 副本。

**不要自己写 CSS** —— 样式表是设计系统的实现，设计规则写在 `references/design.md`（color tokens / type scale / callout taxonomy / 不允许做的事）。如果觉得现有 callout 不够用，先去看 `design.md` 的 §5 和 §7；真有合理需求，按 §8 的演化流程改 `styles.css`，而不是在文章里写一次性 inline style。

### 2.4 生成 PDF + 扫描 + contact sheet

推荐统一入口：`scripts/preview_all.py`，一条命令走完生成 + 扫描 + 拼图：

```bash
python3 /path/to/skill/scripts/preview_all.py input.html output.pdf
```

它会：
1. 渲染 HTML 为 PDF（底层还是 WeasyPrint）
2. 从 WeasyPrint 的 box 树读每页填充率，打印出带 🚨/💡 标记的表格
3. 把所有页拼成 `<output>_sheet.png`，一次看完整份文档

纯扫描不写盘（快速迭代用）：

```bash
python3 scripts/preview_all.py input.html --scan-only
```

旧脚本 `build_pdf.py` 保留作为“只生成 PDF、不扫描”的简化入口。

**HTML 文案 lint（默认开启）**:`build_pdf.py` 在 WeasyPrint 渲染前会自动跑
`scripts/lint_html.py` 修复 HTML 中文段落的排版问题——半角标点 → 全角、
中英文之间加空格、数字与单位空格、半角引号 → 中文引号、重复标点合并等，依据 [中文文案排版指北](https://github.com/sparanoid/chinese-copywriting-guidelines)
+ 自定义规则。lint 只动 text node, 跳过 `<pre>` `<code>` `<script>` `<style>`
标签内的内容，绝不破坏代码、URL、CSS。如果不想跑 lint, 加 `--no-lint` 关闭。

也可以单独跑 lint 检查 / 修复 HTML:

```bash
python3 scripts/lint_html.py input.html              # 仅扫描
python3 scripts/lint_html.py input.html --fix        # 原地修复
```

**代码块语法高亮（默认开启，需 Node.js + shiki）**:`build_pdf.py` 在 lint 之后、
渲染之前会跑 `scripts/highlight_html.mjs`(基于 [Shiki](https://github.com/shikijs/shiki))
处理 HTML 中所有 `<pre><code class="language-X">` 代码块，加上 inline 颜色。
默认 theme 是 `github-dark`，跟 VS Code 一致。

启用前提：在 skill 根目录(例如 `~/.claude/skills/pdf-baomu-tutorial/`)跑
`npm install shiki` 装好 shiki。如果 Node.js 或 shiki 没装，会安全降级——保留
原代码块、打印一行警告，不阻塞渲染。也可以 `--no-highlight` 显式关闭。

代码块要在 markdown 里显式标语言才会被高亮:

````markdown
```bash
brew install node
```
````

支持的语言：bash / python / js / ts / json / yaml / html / css / sql / 等
[一百多种主流语言](https://shiki.style/languages)。

### 2.5 自检清单

**第一步：看 contact sheet**——`<output>_sheet.png`，一张图纵览全文。重点看：

- [ ] 视觉节奏——章节间分隔是否清晰、版面是否过于拥挤或稀疏
- [ ] 异常页——是否有只有 1-2 行内容的页（**章末残行候选**）
- [ ] 元素完整性——大 callout / 表格 / 架构图是否被怪异分页

**第二步：看填充率扫描结果**——`preview_all.py` 输出的表格。规则：

- 🚨 **章内短尾**必处理（章内误触发分页）
- 💡 **章末残行**应处理（1-2 句独占一页，删或合进上段）
- 扫描干净（“✓ 无明显可优化点”）后进入下一步

**第三步：单页高清确认**——只对前两步怀疑的页面：

```bash
pdftoppm -f 7 -l 7 -r 110 output.pdf check -png
```

然后 `view check-07.png`，确认：

- [ ] 封面灰色渐变铺满整页，没有白边
- [ ] 封面主标题下方没有继承的 h1 下划线
- [ ] 目录页序号是中文数字
- [ ] Claude Code 引导块里的指令保留了换行
- [ ] 架构图（`.arch-diagram` 类）保留了换行对齐
- [ ] Callout 框里 strong 标签没有强制换行句末标点
- [ ] 页脚显示“· 分隔符”而不是乱码方块

**注意**：contact sheet 的低分辨率会让 callout 边框产生缩放伪影（看起来像紫色细线
溢出到下一页），这不是真实问题——必须用 ≥100 DPI 单页 PNG 才能做最终判断。

详细自检见 `references/quality-checklist.md`。

## 叁 文档结构模板

每份 PDF 都遵循这个结构：

```
封面（全出血灰色渐变）
├─ 领域标识（如 "OPENLIST · 115"）
├─ 主标题（22pt 粗体）
├─ 副标题（"小白向保姆教程 · 有 Claude Code 就够了"）
└─ 三个黑色标签（定位、卖点、版本）

目录
└─ 中文数字章节号 + 章节标题

零 / 这份教程是给谁看的
├─ 建立心态（引言+读者画像）
└─ 设定预期（"你只要会复制粘贴"）

壹 / 你需要准备什么
├─ 硬件清单
└─ 软件清单

贰 / 原理解释（为什么要这样做）
└─ 讲清楚背景，让后面的操作有"道理"

叁 至 陆 / 动手步骤（每章一个主要阶段）
├─ 每个动手点嵌入"💬 让 Claude Code 帮你"紫色引导块
├─ 每个警告点嵌入"⚠️"黄色/红色警告框
└─ 每个鼓励点嵌入"💡"蓝色提示框

柒 / 出问题了怎么办
└─ 常见故障 + 通用调试咒语

捌 / 附录：常用指令速查
├─ "我想做什么 → 发给 Claude Code 的话"表格
└─ 重要地址集合
```

## 肆 视觉元素语义

这些元素有固定语义，不要乱用：

| 元素 | CSS class | 什么时候用 |
|------|-----------|----------|
| 💬 紫色 Claude Code 引导框 | `.callout.callout-cc` | 每个需要动手敲命令的地方，里面放可复制的中文指令 |
| 💡 蓝色提示框 | `.callout.callout-tip` | 给读者信心、解释原因、小贴士 |
| ⚠️ 黄色警告框 | `.callout` | 需要注意但不致命的事 |
| 🚨 红色警告框 | `.callout.callout-warn` | 严重后果（Token 泄露、重复操作导致失效等） |
| 黑色圆形步骤号 | `.step` + `.step-num` | 有序动作序列，每步一个编号 |
| 深色代码块 | `<pre>` | 终端输出、配置文件 |
| 代码字体容器 | `.arch-diagram` | ASCII 流程图、架构示意 |

## 伍 Claude Code 引导块的写法

这是整份 PDF 的灵魂。模板如下：

```html
<div class="callout callout-cc">
  <strong>简短标题：这段要做什么</strong>
  <div class="cc-prompt">请帮我做 xxx。要求：

1. 第一项要求
2. 第二项要求
3. 第三项要求
4. 最后告诉我 xxx</div>
</div>
```

**写作要点**：
- 标题用一句话描述“让 Claude Code 做什么”，别用技术术语
- 指令正文像跟人说话一样写，带上下文（“我已经部署了 OpenList，地址是 xxx”）
- 用编号列表列出具体要求，不要用自然段
- 末尾加一句“告诉我下一步是什么”——让 Claude Code 主动引导，不让小白断档
- 指令块里的换行会被保留显示（`white-space: pre-wrap`），所以排版直接按你希望看到的样子写

## 陆 步骤编号的写法

```html
<div class="step">
  <div class="step-num">1</div>
  <div class="step-content">
    <span class="step-title">步骤标题（会加粗）</span>
    步骤的详细说明。可以跨多行。
  </div>
</div>
```

- 带小标题的步骤用 `.step-title`（12 pt 加粗）
- 纯描述的步骤（比如“路径 A”那种一句话步骤）直接写内容，不要用 `.step-title`

## 柒 章节分页策略

### 默认规则：所有正文 h1 独占一页

模板里 `h1 { page-break-before: always }` 是默认行为——封面和目录的 h1
被单独豁免。**你不需要做任何事就能得到“每章另起一页”的效果**。
`.chapter-break` 类保留只是向后兼容，不再必须。

这是书、论文、严肃文档的基本排版礼仪。不要反其道而行之用“自然流”来
压页数——页数不是成本，视觉清晰才是。

### 章末留白的三种情况

每章另起一页意味着**大多数章末都会有留白**。这是预期的，不是 bug。
但**其中一类值得花文字优化去消除**——扫描器会自动识别三类：

| 情况 | 识别模式 | 处理 |
|-----|---------|-----|
| 🚨 **章内短尾** | 本页 <40%、下一页仍是本章内容 | 真问题，检查是否有误触发的 `page-break`（如某个 callout 被 `page-break-inside: avoid` 整体推下去）|
| 💡 **章末残行** | 本页 <25%、下一页是新章、且本页**首元素不是 h2** | 值得优化——通常是 1-2 句过渡文字独占一页，删掉或合进上段即可 |
| ⚪ **结构性短尾** | 本页 <25%、下一页是新章、且本页**首元素是 h2** | 不报警——整个子小节被推过来，文字优化改不动；要么接受、要么重排子小节结构 |

其他章末短尾（25%-80%）自然接受。末页短尾（即使 <25%）自然接受。

### 工作流

```bash
python3 scripts/preview_all.py input.html --scan-only
```

- 扫描输出“✓ 无明显可优化点”就放行
- 有 🚨 → 必须处理
- 有 💡 → 找到对应页的最后一两句，删除或合并进上一段、上一 block，直到扫描干净

### 原理：为什么靠扫描而不是靠字数或手感

字数和页数不线性——同样 5000 字，表格多就膨胀、短句多就紧凑。
手感更不可靠——过渡句单看觉得“有意境”，但独占一页就是浪费。

`preview_all.py` 读的是 WeasyPrint 渲染时已经算过的 box 坐标，
每页最后一个叶子 box 的底部 y 值 = 实际内容占用高度，**是精确值**。
配合“首元素是 h1 / h2 / 正文”的语义判断，区分出三类短尾。

参考：[chenglou/pretext](https://github.com/chenglou/pretext) 的核心洞察
是“排版前先测量”。我们取它的思想，但工具留在 Python/WeasyPrint 生态内。

## 捌 读者友好语言清单

这套风格面向小白，语言上：

- **禁用黑话**：不说“赋能”、“闭环”、“抓手”
- **禁用“首先/其次/最后”**：八股味重
- **禁用“众所周知”**：读者如果都众所周知就不用教程了
- **禁用 emoji 在正文**：emoji 只出现在 callout 的图标位置
- **多用“我们”、“大家”**：少用“你应该”
- **人话优先**：能说“三天两头失效”就别说“稳定性不足”

## 捌_b 结尾禁用 CTA

PDF 结语只放“金句回扣 + 评论区互动钩子 + —完—”，**不要**附加任何引流到外部平台的 CTA。

特别禁止的句式包括但不限于：
- “完整的 PDF 教程版（含 xxx）我放在了 **硅基实验室**星球里，扫码自取 👇”
- “更多内容请扫码加入星球”
- “关注公众号回复 xxx 领取”
- 任何“星球 / 扫码 / 自取 / 进群 / 领取”组合

PDF 本身就是要发到星球的成品，再在 PDF 里写“扫码进星球”是回环逻辑，读者会出戏。
引流应该在公众号文章里做（article-baomu-tutorial），而不是在 PDF 里。

## 玖 示例片段

完整示例参考 `references/example-snippet.html`，里面是 OpenList 教程里效果最好的几个片段：
- 封面
- 带 Claude Code 引导块的步骤
- 架构图
- 常见故障附录表格

## 壹拾 Checklist：交付前的最后一看

1. 跑 `scripts/preview_all.py` 一次走完（PDF + 扫描 + contact sheet）
2. 看扫描输出——🚨 必处理，💡 按情况处理
3. 看 contact sheet——检查空白页和视觉节奏
4. 对怀疑的页用 ≥100 DPI 单页 PNG 复查细节
5. 改 HTML 重新跑（不要改 CSS 模板本身）
6. 直到扫描“✓ 无明显可优化点”再交付
7. 用 `present_files` 呈现给用户

**重要**：这份风格用户已经确认“很满意”，所以**保守胜过创新**。如果用户没明确要求改风格，
不要擅自调整 CSS 或元素语义。