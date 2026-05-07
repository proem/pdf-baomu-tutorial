# 交付前质量检查清单

每次生成完 PDF，按这个清单过一遍。发现问题改 HTML，不要改 CSS。

## 壹 视觉层

### 封面
- [ ] 灰色渐变背景铺满整个页面，**没有白色边框**
- [ ] 封面主标题下方**没有下划线**（不应继承正文 h1 的 border-bottom）
- [ ] 封面上的 eyebrow（如 "OPENLIST · 115"）字间距宽松，显得有仪式感
- [ ] 主标题两行或三行，每行文字长度接近
- [ ] 三个 tag 黑底白字，颜色均匀
- [ ] 底部“适合对象”一句话描述清晰

### 目录
- [ ] 中文数字序号（零壹贰叁肆伍陆柒捌）是粉色 `#d63384`
- [ ] 章节标题是普通黑色
- [ ] 每行之间用点状虚线分隔

### 正文排版
- [ ] 每章 h1 标题下面有 3 px 粗的黑色下划线
- [ ] h1 的中文数字前缀是粉色
- [ ] 行距是 1.75（舒适阅读）
- [ ] 中英文混排时，中英文之间有自然空格（不要强制 zero-width-space）

## 贰 元素正确性

### Callout 框
- [ ] 💡 蓝色框 = 提示 / 信心
- [ ] ⚠️ 黄色框 = 注意事项
- [ ] 🚨 红色框 = 严重警告
- [ ] 💬 紫色框 = Claude Code 引导（带 “💬 让 Claude Code 帮你” 自动标题）
- [ ] Callout 里的 `<strong>` 只在**作为第一个子元素**时才独占一行
- [ ] 句末标点（"。"）没有被挤到下一行

### Claude Code 引导块（核心！）
- [ ] 紫色框里自动显示“💬 让 Claude Code 帮你”标题
- [ ] **该标题只出现一次**——不要在 HTML 里手写 `<strong>💬 让 Claude Code 帮你</strong>`，模板的 `.callout-cc::before` 会自动生成；手写了会重复显示
- [ ] `.cc-prompt` 内部保留了所有换行（数字列表、空行等）
- [ ] 指令以“请帮我…”开头，最后一般有“告诉我下一步”
- [ ] 字体是等宽字体（SF Mono / Monaco 等）

### 步骤
- [ ] 黑色圆形序号，数字居中
- [ ] 带 `.step-title` 的步骤标题加粗 12 pt
- [ ] 无标题的步骤文字对齐正确，没有被数字撑歪

### 架构图
- [ ] ASCII 流程图保留所有换行（关键！）
- [ ] 箭头符号（→ ↓）和文字对齐
- [ ] 灰色背景淡边框，不抢戏

### 代码块
- [ ] 深色背景（#1e1e1e），浅色文字
- [ ] 普通 `<pre>` 块不跨页；但 **Claude Code 紫色引导块允许跨页**（指令可能很长）
- [ ] 行内 `<code>` 是浅灰背景 + 红色文字

### Emoji 字形（容易漏的一项）
- [ ] 任意找一个 cc 块，顶部应该是 **💬 让 Claude Code 帮你**，不是 ☐ 或乱码方块
- [ ] 蓝 / 黄 / 红 callout 标题里的 💡 / ⚠️ / 🚨 都正确显示
- [ ] 如果是 ☐：渲染机器缺 emoji 字体，按 `README.md` 装 `fonts-symbola` + `fonts-noto-color-emoji`
- [ ] 排查命令：`fc-list | grep -iE 'symbola|emoji'` 应有至少一行输出

## 叁 分页和布局

- [ ] **所有正文章节（h1）独占一页**——这是模板默认行为，不需要手动加 `chapter-break`
- [ ] **用 `scripts/preview_all.py --scan-only` 扫描**，确保输出“✓ 无明显可优化点”
  - 🚨 **章内短尾**必须处理——检查是否有 callout / 表格 / 架构图因 `page-break-inside: avoid` 被整块推到下一页
  - 💡 **章末残行**应该处理——就 1-2 句独占一页，删掉或合进上段即可
  - 章末自然留白（>25%）接受；末页留白接受；h2 起头的结构性短尾接受
- [ ] Callout（tip/warn）、Step、代码块、架构图不跨页；Claude Code 紫框允许跨页
- [ ] h1、h2 不会独占页尾（下面自然有正文跟进）
- [ ] 页脚显示页码和章节标识
- [ ] **首页（封面）没有页脚**

## 肆 语言层

### 禁止出现
- [ ] 没有 “首先…其次…最后…” 的八股三段式
- [ ] 没有 “众所周知”、“不言而喻”、“综上所述”
- [ ] 没有 “赋能”、“闭环”、“抓手”、“颗粒度” 等黑话
- [ ] emoji 只出现在 callout 的图标位置，正文里没有
- [ ] 没有 “小伙伴们”、“宝子们” 这类网络用语

### 应该出现
- [ ] 多处使用 “我们”、“大家”
- [ ] 每个动手点都有对应的 Claude Code 引导块
- [ ] 关键 warning 有 ⚠️ 图标吸引注意
- [ ] 附录的“速查表”把“我想干什么 → 发给 Claude Code 的话”配对好

## 伍 自动化抽检命令

**主入口**——一条命令走完生成 + 扫描 + contact sheet：

```bash
python3 scripts/preview_all.py input.html output.pdf
```

**快速迭代**——只扫描不写盘：

```bash
python3 scripts/preview_all.py input.html --scan-only
```

**单页高清复查**（contact sheet 上发现的可疑页）：

```bash
pdftoppm -f 7 -l 7 -r 110 output.pdf check -png
# 然后用 view 工具查看 check-07.png
```

> 注意：contact sheet 里看到的“紫色细线溢出到下一页”往往是低分辨率缩放伪影，
> 必须用 ≥100 DPI 单页 PNG 才能判断。

## 陆 对外发布前的脱敏扫描（critical）

如果 PDF 要外发（朋友圈、公众号、知识星球、客户、博客），交付前**必须**做这一步：

### 1. 列出“绝对不能出现”的字符串

写 PDF 时容易把用户**真实**部署里的值当成“示例”嵌进去——要事先列清单：

| 类别 | 来源 | 示例（替换成你自己的） |
|------|------|---------------------|
| 密钥 / 公钥 /token | API token、JWT secret、加密公钥 | `aBcDeF123...` |
| 服务器 IP | 云主机公网 IP | `203.0.113.42` |
| 自有域名 | 个人 / 公司域名及子域名 | `example.com` `*.example.com` |
| 内部主机名 | 内网 / VPN hostname | `host-a` `host-b` |
| 邮箱 / 用户名 | 个人邮箱、SSH 用户名 | `you@example.com` |

### 2. 扫描 PDF 二进制

```bash
python3 -c "
pdf = open('output.pdf','rb').read()
patterns = [b'aBcDeF', b'203.0.113.42', b'example.com']  # 改成你的清单
hits = [p.decode() for p in patterns if p in pdf]
print('LEAKS:', hits if hits else 'NONE — clean')
"
```

不能假设“二进制看不出来”——PDF 文本流就是明文，搜得出。

### 3. 扫描中间产物

`*_sheet.png` / 单页高清 PNG 也包含可读文本（OCR 友好）。删除或一并替换。

### 4. 清理远程渲染机器

如果你借用别的机器（如 host-a）渲染过 PDF，那台机器的 `/tmp` 也要 `rm` 掉相应目录和 tarball。

### 5. 默认占位化

最稳的做法是**写 PDF 时就用占位符**：`example.com` / `你的服务器IP` / `aBcDeF123...=`。等读者看教程时各自替换成自己的值。这比交付前补救安全得多。

## 柒 常见问题和解决

| 问题现象 | 原因 | 改法 |
|---------|------|------|
| 封面底部有白边 | `@page :first` 没去 margin | 确认模板里的 `@page :first { margin: 0 }` |
| 封面主标题下有横线 | 继承了正文 h1 的 `border-bottom` | 确认模板的 `.cover-title` 有 `border:none; padding:0;` |
| 架构图压成一行 | `.arch-diagram` 没有 `white-space: pre-wrap` | 用模板里的原版 CSS |
| “不要选”和句号分家 | `.callout strong` 全部 display:block | 用 `:first-child` 选择器限制 |
| cc-prompt 指令挤成一段 | `.cc-prompt` 没有 `white-space: pre-wrap` | 用模板里的原版 CSS |
| Claude Code 紫框独占整页、后续 prompt 被挤到下一页 | `.callout-cc` 的 `page-break-inside: avoid` 推动了整块 | 确认模板里 `.callout-cc` 是 `page-break-inside: auto` |
| 某页只有 1-3 行，上一页已满 | 孤行溢出 | `preview_all.py` 会标 🚨（若章内）或 💡（若章末残行）——删掉该行或合并进上一段 |
| 章末留白 25-80% | 章末自然短尾（预期） | 不用处理——这是“每章独占一页”的代价，视觉清晰 > 压页数 |
| 章末就 1-2 句独占一页 | 章末残行 | `preview_all.py` 标 💡——删掉过渡句或合进上段 |
| 某章的 h2 小节整块独占新页 | 结构性短尾 | 通常不必改；若一定要改，要重排该子小节结构（合并或提前） |
| 章内某页突然半空，下一页继续本章 | callout / 表格 / 大图被 `page-break-inside: avoid` 推过去了 | `preview_all.py` 标 🚨——检查并移除那个元素的 avoid 约束 |
| 页脚是方块 / 乱码 | 字体不支持该字符 | 避开 ×，用 · 或 / 代替 |