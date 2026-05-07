#!/usr/bin/env python3
"""
lint_html.py — HTML 文案 lint：对中文 text node 应用全角标点 + 空格规范。

设计：
    PDF 生成时输入是 HTML,WeasyPrint 不做文案处理。
    这个工具在 build_pdf 之前跑，用 BeautifulSoup 遍历 DOM,
    只对中文 text node 应用排版规则，跳过代码、样式、属性。

跳过的标签(里面的内容不动):
    <script>, <style>, <pre>, <code>
    (代码就该是英文 ASCII，不能动)

跳过的属性(永不动):
    href, src, class, id, style, ...
    (URL、CSS 都是数据，不是文案)

用法：
    python3 lint_html.py input.html              # 仅扫描
    python3 lint_html.py input.html --fix        # 原地改
    python3 lint_html.py input.html --fix --out output.html

依赖：
    pip install pangu beautifulsoup4
"""

import sys
import re
from pathlib import Path

try:
    from bs4 import BeautifulSoup, NavigableString, Comment
except ImportError:
    print('缺少依赖：beautifulsoup4', file=sys.stderr)
    print('请先安装：pip install beautifulsoup4', file=sys.stderr)
    sys.exit(1)

# 共享 lint_punctuation 和 lint_typography 的核心规则
sys.path.insert(0, str(Path(__file__).parent))
try:
    from lint_punctuation import fix_text as fix_punctuation
    from lint_typography import fix_typography
except ImportError as e:
    print(f'缺少同目录脚本或依赖：{e}', file=sys.stderr)
    print('需要 lint_punctuation.py、lint_typography.py 同目录，'
          '以及 pangu 库：pip install pangu', file=sys.stderr)
    sys.exit(1)


# 不处理的标签：这些标签里的文本应当原样保留
SKIP_TAGS = {'script', 'style', 'pre', 'code', 'kbd', 'samp', 'tt'}


def contains_chinese(text):
    """检测字符串是否含中文字符"""
    return bool(re.search(r'[\u4e00-\u9fff]', text))


def fix_chinese_text(text):
    """对一段纯文本依次应用排版规则。

    HTML text node 经常带前后空白（代表标签后的换行+缩进），
    必须保留这些空白，否则会破坏 HTML 的视觉结构。
    """
    # 保留开头/末尾的空白；中间的中文内容修复，边界 whitespace 原样保留
    leading_m = re.match(r'^\s*', text)
    trailing_m = re.search(r'\s*$', text)
    leading = leading_m.group() if leading_m else ''
    trailing = trailing_m.group() if trailing_m else ''

    if leading or trailing:
        end = len(text) - len(trailing) if trailing else len(text)
        middle = text[len(leading):end]
    else:
        middle = text

    if not middle.strip():
        return text  # 全是空白,无内容可修

    middle = fix_typography(middle)

    # 清理 pangu 副作用：半角标点后空格 + 中文 → 紧贴
    # 但要排除"数字/字母 + 标点"这种编号或缩写(1. xxx / U.S. xxx)
    middle = re.sub(r'(?<![0-9a-zA-Z])([,.;:?!])\s+(?=[\u4e00-\u9fff\u201c\u2018])',
                    r'\1', middle)

    # 中文引号 / 破折号 周围多余空格（pangu 副作用）
    middle = re.sub(r'([\u201c\u2018])\s+', r'\1', middle)
    middle = re.sub(r'\s+([\u201d\u2019])', r'\1', middle)
    middle = re.sub(r'\s+\u2014', '\u2014', middle)
    middle = re.sub(r'\u2014\s+', '\u2014', middle)

    middle = fix_punctuation(middle)

    return leading + middle + trailing


def lint_html(html, dry_run=False):
    """处理 HTML 字符串，返回 (新 html, 修改的 text node 数量)。

    实现策略：用 BS4 解析找需要修改的 text nodes，但**不**重新序列化整个文档
    （BS4 的 html.parser 会吃掉 HTML 缩进空格）。改成在原始 HTML 字符串上做
    string-level 替换，完整保留原文格式。
    """
    soup = BeautifulSoup(html, 'html.parser')
    replacements = []  # list of (original_str, new_str)

    for node in soup.find_all(string=True):
        if isinstance(node, Comment):
            continue

        # 跳过 SKIP_TAGS 里的内容
        ancestors = []
        for a in node.parents:
            if a.name:
                ancestors.append(a.name)
        if any(tag in SKIP_TAGS for tag in ancestors):
            continue

        original = str(node)
        if not contains_chinese(original):
            continue

        fixed = fix_chinese_text(original)
        if fixed != original:
            replacements.append((original, fixed))

    if dry_run:
        return html, len(replacements)

    # 在原始字符串上替换，保留所有空白 / 缩进 / 注释格式
    # 同一文本可能在不同 text node 出现多次，每条 replacement 只替换一次
    out = html
    for original, fixed in replacements:
        out = out.replace(original, fixed, 1)

    return out, len(replacements)


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)

    in_path = Path(args[0])
    do_fix = '--fix' in args
    out_path = None
    if '--out' in args:
        out_path = Path(args[args.index('--out') + 1])
    elif do_fix:
        out_path = in_path

    if in_path.suffix.lower() not in {'.html', '.htm'}:
        print(f'⚠ {in_path.suffix} 不是 HTML 文件；只支持 .html / .htm',
              file=sys.stderr)
        sys.exit(2)

    html = in_path.read_text(encoding='utf-8')
    fixed, changed = lint_html(html, dry_run=not do_fix)

    if changed == 0:
        print(f'✓ {in_path}：无文案排版问题')
        return

    if not do_fix:
        print(f'⚠ {in_path}：有 {changed} 个 text node 需要调整')
        print('  跑 --fix 自动修复')
        sys.exit(1)

    out_path.write_text(fixed, encoding='utf-8')
    print(f'✓ {in_path} → {out_path}')
    print(f'  修复了 {changed} 个 text node')


if __name__ == '__main__':
    main()
