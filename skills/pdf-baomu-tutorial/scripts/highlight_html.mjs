#!/usr/bin/env node
/**
 * highlight_html.mjs — 用 Shiki 给 HTML 里的代码块加语法高亮。
 *
 * 用法:
 *   node highlight_html.mjs input.html [output.html] [theme]
 *
 * 默认 theme: github-dark
 * 默认 output: 原地覆盖 input
 *
 * 处理:
 *   <pre><code class="language-X">...</code></pre>  → Shiki 高亮版
 *
 * 没 language class 的 <pre><code>...</code></pre>:
 *   保持原样,不做高亮(避免误判)
 *
 * 实现策略(跟 lint_html.py 同款):
 *   - 用 regex 找代码块,但**不**重新序列化 HTML
 *   - string-level 替换,完整保留原文格式
 *   - HTML entities (&lt; &gt; &amp; &quot; &#39;) 在喂给 Shiki 前 decode
 *
 * 依赖:
 *   npm install shiki
 */

import { readFile, writeFile } from 'node:fs/promises';
import { codeToHtml } from 'shiki';

const args = process.argv.slice(2);
if (args.length === 0) {
  console.error('Usage: node highlight_html.mjs input.html [output.html] [theme]');
  process.exit(1);
}

const inputPath = args[0];
const outputPath = args[1] || inputPath;
const theme = args[2] || 'github-dark';

// HTML entity decode(只处理这 5 个 mistune 会输出的)
function decodeEntities(s) {
  return s
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&amp;/g, '&');  // 必须最后,避免双重 decode
}

const html = await readFile(inputPath, 'utf-8');

// 匹配 <pre><code class="language-X">...</code></pre>
// 用 [\s\S] 跨行匹配, 非贪婪
const pattern = /<pre><code class="language-([a-z0-9+#-]+)">([\s\S]*?)<\/code><\/pre>/g;
const replacements = [];

for (const m of html.matchAll(pattern)) {
  const [fullMatch, lang, encodedCode] = m;
  const code = decodeEntities(encodedCode);

  try {
    const highlighted = await codeToHtml(code, { lang, theme });
    replacements.push([fullMatch, highlighted]);
  } catch (e) {
    // 不支持的语言或解析错误,保持原样并报告
    console.error(`[highlight] skip lang=${lang}: ${e.message}`);
  }
}

if (replacements.length === 0) {
  console.log('  No code blocks to highlight');
  if (inputPath !== outputPath) {
    await writeFile(outputPath, html);
  }
  process.exit(0);
}

// string-level 替换(每条 replacement 只替换一次,避免重复)
let out = html;
for (const [orig, fixed] of replacements) {
  out = out.replace(orig, fixed);
}

await writeFile(outputPath, out);
console.log(`✓ Highlighted ${replacements.length} code blocks (theme: ${theme})`);
