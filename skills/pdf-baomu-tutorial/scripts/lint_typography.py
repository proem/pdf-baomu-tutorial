#!/usr/bin/env python3
"""
lint_typography.py — 中文排版 lint:中英文之间空格、数字与单位空格、重复标点等。

基于「中文文案排版指北」(github.com/sparanoid/chinese-copywriting-guidelines)
核心规则,用 pangu 库做主力空格处理,叠加自定义规则。

用法:
    # 仅扫描,显示会做的修改
    python3 lint_typography.py article.md

    # 自动修复(原地)
    python3 lint_typography.py article.md --fix

    # 写到新文件
    python3 lint_typography.py article.md --fix --out article.fixed.md

处理的规则:
    1. 中英文之间增加空格(pangu)
    2. 中文与数字之间增加空格(pangu)
    3. 数字与英文单位(2+ 字母)之间增加空格(自定义,如 10Gbps → 10 Gbps)
    4. 度数 ° / 百分比 % 与数字之间不加空格(pangu 默认行为)
    5. 重复标点合并(pangu 处理 !!! → !,??? → ?)
    6. 半角标点 → 全角(pangu 部分支持,本工具不重复 lint_punctuation 的工作)

保护区:代码块、行内代码、URL — 跟 lint_punctuation 一致。
"""

import sys
import re
from pathlib import Path

try:
    import pangu
except ImportError:
    print('缺少依赖:pangu', file=sys.stderr)
    print('请先安装:', file=sys.stderr)
    print('    pip install pangu', file=sys.stderr)
    sys.exit(1)

# 复用 lint_punctuation 里的代码块保护逻辑
sys.path.insert(0, str(Path(__file__).parent))
from lint_punctuation import protect_code, restore_code


# ============================================================
# Typography 专用的额外保护(pangu 会破坏这些)
# ============================================================
PH_OPEN = '\x00MD'
PH_CLOSE = '\x00'


def protect_typography_extras(text):
    """保护 pangu 会误处理的字符:
    - markdown 强调 **...** 和 *...*(pangu 会在 ** 前后加空格)
    - 中文破折号 ——(pangu 会当成英文 dash 加空格)
    - markdown 删除线 ~~...~~
    - 中文引号 "..." '...' 包围的整段(pangu 会在引号前后加空格)
    - HTML 标签属性(pangu 会破坏 align="center" 这类双引号)
    """
    placeholders = []

    def stash(m):
        idx = len(placeholders)
        placeholders.append(m.group(0))
        return f'{PH_OPEN}{idx}{PH_CLOSE}'

    # HTML 标签整段保护(包括属性的双引号)
    # 例如 <p align="center">、<img src="..." width="...">
    text = re.sub(r'<[a-zA-Z][a-zA-Z0-9]*\b[^<>]*?>', stash, text)
    text = re.sub(r'</[a-zA-Z][a-zA-Z0-9]*>', stash, text)

    # 强调 / 加粗 / 删除线 — 允许跨行
    text = re.sub(r'\*\*[^*]{1,500}\*\*', stash, text, flags=re.DOTALL)
    text = re.sub(r'(?<![*])\*[^*]{1,500}\*(?![*])', stash, text, flags=re.DOTALL)
    text = re.sub(r'~~[^~]{1,500}~~', stash, text, flags=re.DOTALL)

    # 中文破折号:连续 2+ 个 EM DASH(U+2014)
    text = re.sub(r'\u2014{2,}', stash, text)

    # 中文中点 ·(U+00B7) — pangu 在某些上下文下会把它改成片假名中点 ・(U+30FB)
    # 中文写作惯用 ·,需要保护
    text = re.sub(r'\u00b7', stash, text)

    # 中文引号包围的整段(允许跨行):双引号 \u201c \u201d、单引号 \u2018 \u2019
    text = re.sub(r'\u201c[^\u201c\u201d]{1,500}\u201d', stash, text, flags=re.DOTALL)
    text = re.sub(r'\u2018[^\u2018\u2019]{1,500}\u2019', stash, text, flags=re.DOTALL)

    return text, placeholders


def restore_typography_extras(text, placeholders):
    """还原占位符。注意:占位符可能嵌套(例如中点 · 被先 protect,
    然后包含它的中文引号段又被 protect),所以循环替换直到稳定。"""
    pattern = rf'{PH_OPEN}(\d+){PH_CLOSE}'
    def restore(m):
        return placeholders[int(m.group(1))]
    # 最多循环 5 次足以处理常见嵌套深度
    for _ in range(5):
        new_text = re.sub(pattern, restore, text)
        if new_text == text:
            break
        text = new_text
    return text


# ============================================================
# 自定义排版规则
# ============================================================
def fix_number_unit(text):
    """数字 + 英文单位(2+ 字母) 之间加空格。

    会改:  10Gbps → 10 Gbps,  20TB → 20 TB,  5km → 5 km
    不改:  5G(网络代号,单字母),  MP3(数字在英文后),  iPhone15(数字在英文后)
    """
    # 数字前不能是字母(避免 iPhone15 这种)
    # 数字后必须是 >=2 个字母(避免 5G, 4G 这种网络代号)
    return re.sub(r'(?<![a-zA-Z])(\d+)([a-zA-Z]{2,})\b',
                  r'\1 \2', text)


def fix_quotes(text):
    """半角双引号 → 中文双引号。

    重要约束:只在确认是"中文段落里的引号"时才转。
    判定:配对的 "..." 中,内部、左侧 1 字符、右侧 1 字符任一有中文 → 转中文引号;
    否则保留半角(可能是 HTML 属性 align="center"、英文引用、代码片段等)。
    """
    CN = '\u4e00-\u9fff'

    def replace_pair(m):
        before = text[max(0, m.start() - 1):m.start()]
        inside = m.group(1)
        after = text[m.end():m.end() + 1]
        # 任一侧或内部含中文字符 → 视为中文段落里的引号
        if any(re.search(f'[{CN}]', s) for s in (before, inside, after)):
            return '\u201c' + inside + '\u201d'
        # HTML 属性、英文引用、代码 - 保留半角
        return m.group(0)

    # 段内闭合的 "..." (不跨行)
    return re.sub(r'"([^"\n]*?)"', replace_pair, text)


def fix_repeated_punct(text):
    """重复的中文标点合并成一个。

    pangu 会处理半角的 !!! ??? 但不动已经全角的。
    我们补齐:!!! → !,??? → ?,。。。 → 。

    注意:用 Unicode escape 写全角字符,避免"半角看起来像全角"的坑。
    """
    text = re.sub(r'\uff01{2,}', '\uff01', text)  # !!! → !
    text = re.sub(r'\uff1f{2,}', '\uff1f', text)  # ??? → ?
    text = re.sub(r'\u3002{2,}', '\u3002', text)  # 。。。 → 。
    return text


def fix_typography(text):
    """主修复函数:protect → pangu → 自定义规则 → restore。"""
    # 第一层保护:代码块、行内代码、URL
    protected, code_phs = protect_code(text)

    # 0. 先转半角引号为中文引号("..." → "...") — 必须在 protect_extras 之前
    #    这样 protect_extras 才能把"完整的中文引号段"保护起来,pangu 才看不到
    protected = fix_quotes(protected)

    # 第二层保护:markdown 强调、破折号、中文引号包围的内容
    protected, extra_phs = protect_typography_extras(protected)

    # 1. pangu 主力:中英文/中数字空格、半角→全角等
    protected = pangu.spacing_text(protected)

    # 2. 数字 + 英文单位空格(pangu 漏)
    protected = fix_number_unit(protected)

    # 3. 重复中文标点合并(pangu 不处理已是全角的)
    protected = fix_repeated_punct(protected)

    # 还原:倒着还原
    protected = restore_typography_extras(protected, extra_phs)
    return restore_code(protected, code_phs)


# ============================================================
# 扫描模式:跑一次 fix,diff 出问题位置
# ============================================================
def scan_diff(text):
    """返回 (line_no, before_snippet, after_snippet) 列表,展示会做的修改。"""
    fixed = fix_typography(text)
    if fixed == text:
        return []

    raw_lines = text.split('\n')
    fixed_lines = fixed.split('\n')

    diffs = []
    # 简单逐行对比(假设 fix 不会改变行数)
    if len(raw_lines) == len(fixed_lines):
        for i, (a, b) in enumerate(zip(raw_lines, fixed_lines), 1):
            if a != b:
                diffs.append((i, a, b))
    else:
        # 行数变了(罕见),给个粗略提示
        diffs.append((0, '<整体修改>', '<跑 --fix 查看>'))
    return diffs


# ============================================================
# 入口
# ============================================================
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

    SAFE_EXTS = {'.md', '.markdown', '.txt'}
    if do_fix and in_path.suffix not in SAFE_EXTS:
        print(f'拒绝修复:{in_path.suffix} 不是 markdown 文件',
              file=sys.stderr)
        print(f'仅支持:{", ".join(sorted(SAFE_EXTS))}',
              file=sys.stderr)
        sys.exit(2)

    raw = in_path.read_text(encoding='utf-8')

    if not do_fix:
        diffs = scan_diff(raw)
        if not diffs:
            print(f'✓ {in_path}:无排版问题')
            return
        print(f'⚠ {in_path}:发现 {len(diffs)} 行需要调整')
        print()
        for line_no, before, after in diffs[:15]:
            print(f'  L{line_no}:')
            print(f'    -  {before}')
            print(f'    +  {after}')
            print()
        if len(diffs) > 15:
            print(f'  ... 另有 {len(diffs) - 15} 行省略')
        sys.exit(1)

    fixed = fix_typography(raw)
    out_path.write_text(fixed, encoding='utf-8')

    diffs_before = len(scan_diff(raw))
    print(f'✓ {in_path} → {out_path}')
    print(f'  调整了 {diffs_before} 行')


if __name__ == '__main__':
    main()
