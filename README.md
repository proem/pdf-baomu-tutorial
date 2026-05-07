<p align="center">
<img src="docs/images/logo.png" alt="pdf-baomu-tutorial" width="330">
</p>
<h1 align="center">pdf-baomu-tutorial</h1>

> 📄 保姆级 PDF 教程，让复杂变简单

<p align="center">
<a href="https://skills.sh/proem/pdf-baomu-tutorial"><img src="https://skills.sh/b/proem/pdf-baomu-tutorial?v=2" alt="skills.sh"></a>
</p>

Claude Code skill —— 生成“小白向保姆教程”风格的中文 PDF 文档。

## 安装

推荐用 [`skills`](https://www.npmjs.com/package/skills) CLI 一键安装（自动适配 Claude Code、Cursor、Codex 等任何主流 agent）：

```bash
npx skills add proem/pdf-baomu-tutorial
```

或者手动 clone 到 Claude Code 的 skills 目录：

```bash
git clone https://github.com/proem/pdf-baomu-tutorial.git ~/.claude/skills/pdf-baomu-tutorial
```

重启 Claude Code 会话生效。

![封面页](docs/images/01_cover.png)

视觉风格：封面全出血灰色渐变、中文数字章节（零壹贰叁）、紫色“让 Claude Code 帮你”引导块、黑色圆形步骤编号、三色语义高亮框（蓝提示 / 黄警告 / 红禁止 / 紫 Claude Code）。

![核心视觉元素一览](docs/images/02_elements.png)

完整 6 页鸟瞰：

![全文鸟瞰图](docs/images/03_overview.png)

## 触发词

“帮我做一份 PDF”、“生成教程 PDF”、“用保姆教程风格写”、“小白向教程”、“把这个变成 PDF”、“做成那个风格的 PDF”、“出一份 PDF” 等。

## 目录结构

```
pdf-baomu-tutorial/
├── SKILL.md                            # 风格说明 + 写作流程
├── references/
│   ├── writing-guide.md                # 写作准则
│   ├── quality-checklist.md            # 完稿前自检清单
│   └── example-snippet.html            # HTML 片段范例
├── templates/
│   └── tutorial-template.html          # 主模板（含 CSS）
└── scripts/
    ├── build_pdf.py                    # HTML → PDF（WeasyPrint）
    └── preview_all.py                  # 渲染 + 填充率扫描 + contact sheet 三合一
```

## 依赖

### Python 包

```bash
pip install weasyprint pillow pypdf pangu beautifulsoup4
```

> `pangu` 和 `beautifulsoup4` 是 PDF 渲染前**HTML 文案 lint** 用的——自动修复中文段落里的半角标点、中英文空格、半角引号等 (依据 [中文文案排版指北](https://github.com/sparanoid/chinese-copywriting-guidelines))。如果不想用，渲染时加 `--no-lint` 关闭即可。

### Node.js + Shiki（可选，代码块语法高亮）

```bash
# 在 skill 根目录(~/.claude/skills/pdf-baomu-tutorial/ 等)
npm install shiki
```

> [Shiki](https://github.com/shikijs/shiki) 是 VS Code 同款的语法高亮器(TextMate grammar + 主题)，给 PDF 里的 `<pre><code>` 代码块加 inline 颜色。默认 theme 是 `github-dark`。如果没装 Node.js 或 shiki，渲染时会自动跳过高亮 (代码块仍按模板的纯色显示)。也可以用 `--no-highlight` 显式关闭。

### 系统字体（关键）

WeasyPrint 在渲染时需要字形可用，否则会输出空方块 ☐。**CJK + emoji 两类字体都要装**：

```bash
# Debian / Ubuntu
sudo apt install -y \
  libpangoft2-1.0-0 libpango-1.0-0 libpangocairo-1.0-0 \
  libharfbuzz0b libfontconfig1 libcairo2 \
  fonts-noto-cjk \
  fonts-symbola fonts-noto-color-emoji \
  poppler-utils
```

| 字体包 | 解决什么 |
|---|---|
| `fonts-noto-cjk` | 中文字符（章标题、正文） |
| **`fonts-symbola`** | **模板里的 💬 / 💡 / ⚠️ / 🚨 等 emoji 图标（这是核心视觉元素，缺了灯泡/对话气泡都会变 ☐）** |
| `fonts-noto-color-emoji` | emoji 兜底（彩色，部分场景 WeasyPrint 会回退到它） |
| `poppler-utils` | 提供 `pdftoppm`，给 contact sheet 生成和单页高清 PNG 检查用 |

### 平台说明

- **Linux / Docker**：上面一行 apt 即可
- **macOS**：`brew install weasyprint pango cairo`，emoji 走系统自带的 Apple Color Emoji
- **Windows**：原生 WeasyPrint 装起来麻烦（要 MSYS2 GTK），推荐 SSH 到 Linux 服务器渲染，或者用 WSL2

### Windows → 远程 Linux 渲染套路

如果你在 Windows 写文档但有一台可 SSH 的 Linux 机器（云主机、家里的 NAS、WSL），用这个 4 步流水线：

```bash
# 1. 上传 HTML 和渲染脚本
tar czf /tmp/build.tar.gz output.html
scp /tmp/build.tar.gz user@host:/tmp/
scp ~/.claude/skills/pdf-baomu-tutorial/scripts/preview_all.py user@host:/tmp/

# 2. 远端解压 + 渲染
ssh user@host "mkdir -p /tmp/build && cd /tmp/build && \
  tar xzf /tmp/build.tar.gz && \
  python3 /tmp/preview_all.py output.html output.pdf"

# 3. 拉回产物
scp user@host:/tmp/build/output.pdf .
scp user@host:/tmp/build/output_sheet.png .

# 4. 清理远程临时文件（重要：尤其 PDF 含敏感信息时）
ssh user@host "rm -rf /tmp/build /tmp/build.tar.gz /tmp/preview_all.py"
```

**首次需要在远端装好依赖**（Python 包 + 上面那串 apt 字体包）。装一次永久受益。