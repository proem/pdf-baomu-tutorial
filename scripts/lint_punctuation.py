#!/usr/bin/env python3
"""
lint_punctuation.py — 扫描并修复中文段落里被误用的半角标点。

中文写作规范：中文段落里的标点应该用全角(,→,  .→。  :→:  ?→?  !→!  ;→;  ()→()),
但代码块、行内代码、URL、英文术语之间应保留半角。

用法：
    # 仅扫描，不改文件，列出问题位置
    python3 lint_punctuation.py article.md

    # 自动修复（原地修改文件）
    python3 lint_punctuation.py article.md --fix

    # 写到新文件不动原文件
    python3 lint_punctuation.py article.md --fix --out article.fixed.md

实现要点：
    1. 先把代码块、行内代码、链接 URL 替换成占位符，最后再还原
    2. 中文段落里的半角标点根据"前后是否中文"来判断是否转换
    3. 全角句号(。)的检测需要和小数点、英文缩写区分
    4. 保守原则：有疑问就保留半角，不要破坏内容
"""

import sys
import re
from pathlib import Path

# CJK 字符 + 已经是全角的中文标点（用作上下文判定）
CJK_CLASS = r'[\u4e00-\u9fff,。?!;:、""\'\'()《》「」【】]'

# 占位符：替换代码块/行内代码时用
PH_OPEN = '\x00PH'
PH_CLOSE = '\x00'


def protect_code(text):
    """把代码块/行内代码/链接 URL 替换成占位符，返回修改后文本和占位符列表。

    注意：在 `>` 引用块里的 ``` 代码块不会被保护——因为 article-baomu 风格里，
    callout（尤其 💬 让 Claude Code 帮你）内嵌的代码块装的是中文指令，
    需要参与全角转换。
    """
    placeholders = []

    def make_ph(content):
        idx = len(placeholders)
        placeholders.append(content)
        return f'{PH_OPEN}{idx}{PH_CLOSE}'

    # === 第一步：按行扫描，只把"非引用块上下文里的 ``` 围栏代码"替成占位符 ===
    lines = text.split('\n')
    out_lines = []
    in_quote = False        # 是否在 `>` 引用块上下文
    in_fence_outside = False  # 是否在"非引用块的围栏代码块"里
    fence_buffer = []

    for ln in lines:
        stripped = ln.lstrip()
        is_quote_line = stripped.startswith('>')
        is_fence_line = stripped.startswith('```') or ln.lstrip(' >').startswith('```')

        # 引用块上下文判断：连续 > 行属于一个引用块，空行或非 > 行结束引用块
        if is_quote_line:
            in_quote = True
        elif not ln.strip():
            # 空行：暂时挂起判断（下一行如果还是 > 才算延续）
            pass
        else:
            in_quote = False

        # 围栏代码块边界（只识别"非引用块"的）
        if is_fence_line and not in_quote and not is_quote_line:
            if not in_fence_outside:
                # 进入围栏
                in_fence_outside = True
                fence_buffer = [ln]
            else:
                # 退出围栏 → 整段做占位符
                fence_buffer.append(ln)
                placeholder = make_ph('\n'.join(fence_buffer))
                out_lines.append(placeholder)
                in_fence_outside = False
                fence_buffer = []
            continue

        if in_fence_outside:
            fence_buffer.append(ln)
            continue

        out_lines.append(ln)

    # 收尾：如果还有未关闭的 fence，原样附加（说明 markdown 写错了）
    if fence_buffer:
        out_lines.extend(fence_buffer)

    text = '\n'.join(out_lines)

    # === 第二步：行内代码、链接 URL ===
    text = re.sub(r'`[^`\n]+`',
                  lambda m: make_ph(m.group(0)),
                  text)
    text = re.sub(r'\[([^\]]*)\]\(([^)]+)\)',
                  lambda m: f'[{m.group(1)}]({make_ph(m.group(2))})',
                  text)

    return text, placeholders


def restore_code(text, placeholders):
    """把占位符还原成原内容"""
    def restore(m):
        return placeholders[int(m.group(1))]
    return re.sub(rf'{PH_OPEN}(\d+){PH_CLOSE}', restore, text)


# 全角标点（用 Unicode escape 确保不会被误打成半角）
FW_COMMA     = '\uff0c'  # ,
FW_PERIOD    = '\u3002'  # 。
FW_COLON     = '\uff1a'  # :
FW_SEMICOLON = '\uff1b'  # ;
FW_QUESTION  = '\uff1f'  # ?
FW_EXCLAIM   = '\uff01'  # !
FW_LPAREN    = '\uff08'  # (
FW_RPAREN    = '\uff09'  # )


# ============================================================
# 修复规则
# ============================================================
def fix_text(text):
    """对已经去掉代码占位符的纯文本应用半角→全角转换。

    规则：逗号、冒号、分号、问号、感叹号、括号——只要前后任一侧是中文，
    就转成全角。这覆盖中英混排的所有常见情况。
    """
    # CN 范围包括中文字符 + 中文标点(让"中文标点 + 半角符号 + 中文"也能匹配)
    CN = r'[\u4e00-\u9fff\u201c\u201d\u2018\u2019\uff0c\u3002\uff01\uff1f\uff1a\uff1b\u3001\uff08\uff09]'

    # 双向规则模板：左侧或右侧是中文 → 转全角
    pairs = [
        (',',  FW_COMMA),
        (':',  FW_COLON),
        (';',  FW_SEMICOLON),
        (r'\?', FW_QUESTION),
        ('!',  FW_EXCLAIM),
    ]
    for half, full in pairs:
        # 前侧是中文 → 全角
        text = re.sub(rf'(?<={CN}){half}', full, text)
        # 后侧是中文 → 全角
        text = re.sub(rf'{half}(?={CN})', full, text)

    # 圆括号：括号内有中文字符 → 转全角（连里面的英文一起包起来）
    def maybe_full_paren(m):
        inner = m.group(1)
        if re.search(CN, inner):
            return f'{FW_LPAREN}{inner}{FW_RPAREN}'
        return m.group(0)
    text = re.sub(r'\(([^()]{1,200})\)', maybe_full_paren, text, flags=re.DOTALL)

    # 句号：中文 + . + 行尾（避免误伤数字小数点和英文缩写）
    text = re.sub(rf'({CN})\.(\s*\n)', rf'\1{FW_PERIOD}\2', text)
    text = re.sub(rf'({CN})\.$', rf'\1{FW_PERIOD}', text, flags=re.MULTILINE)

    # 清理：再走一次"标点配对" — 因为前面的空格被处理后,
    # 可能出现新的"中文 + 半角标点 + 中文"匹配机会
    pairs2 = [
        (',',   FW_COMMA),
        (':',   FW_COLON),
        (';',   FW_SEMICOLON),
        (r'\?', FW_QUESTION),
        ('!',   FW_EXCLAIM),
    ]
    for half, full in pairs2:
        text = re.sub(rf'(?<={CN}){half}', full, text)
        text = re.sub(rf'{half}(?={CN})', full, text)

    # 全形标点周围不应有空格(指北规则:全形标点与其他字符之间不加空格)
    # 这条放在最后,清理 pangu 误加的空格
    FW_PUNCT_CLASS = r'[\uff0c\u3002\uff01\uff1f\uff1b\uff1a\u3001' \
                     r'\u201c\u201d\u2018\u2019\uff08\uff09]'
    text = re.sub(rf'({FW_PUNCT_CLASS}) +', r'\1', text)
    text = re.sub(rf' +({FW_PUNCT_CLASS})', r'\1', text)

    return text


def fix_text_safe(text):
    """fix_text 的安全版：只改逗号 / 冒号 / 分号 / 问号 / 感叹号，
    不改括号、不改句号。

    用于 Python 字符串字面量——里面的 () 和 . 可能是正则元字符，
    不能盲改全角(否则破坏正则)。
    """
    # CN 范围包括中文字符 + 中文标点(让"中文标点 + 半角符号 + 中文"也能匹配)
    CN = r'[\u4e00-\u9fff\u201c\u201d\u2018\u2019\uff0c\u3002\uff01\uff1f\uff1a\uff1b\u3001\uff08\uff09]'
    pairs = [
        (',',   FW_COMMA),
        (':',   FW_COLON),
        (';',   FW_SEMICOLON),
        (r'\?', FW_QUESTION),
        ('!',   FW_EXCLAIM),
    ]
    for half, full in pairs:
        text = re.sub(rf'(?<={CN}){half}', full, text)
        text = re.sub(rf'{half}(?={CN})', full, text)
    return text


# ============================================================
# 扫描模式（只报告）
# ============================================================
def scan(text):
    """返回各类问题的位置列表[(line_no, column, snippet, kind), ...]

    规则：任一侧是中文字符的半角标点都视为问题。
    """
    issues = []
    lines = text.split('\n')
    CN = r'[\u4e00-\u9fff]'

    # 每条规则都用两个正则捕捉"左中文"或"右中文"
    rules = [
        ('半角逗号',  [rf'(?<={CN}),', rf',(?={CN})']),
        ('半角冒号',  [rf'(?<={CN}):(?=\s|$|{CN})', rf':(?={CN})']),
        ('半角分号',  [rf'(?<={CN});', rf';(?={CN})']),
        ('半角问号',  [rf'(?<={CN})\?(?=\s|$|{CN}|"|\))',
                      rf'\?(?={CN})']),
        ('半角感叹号',[rf'(?<={CN})!(?=\s|$|{CN}|"|\))',
                      rf'!(?={CN})']),
        ('半角括号',  [r'\(([^()]{1,200}[\u4e00-\u9fff][^()]{0,200})\)']),
        ('半角句号',  [rf'({CN})\.(\s*\n|$)']),
    ]

    in_code_block = False
    in_quote = False
    in_quote_fence = False  # 是否在引用块内的 ``` 围栏里

    for i, line in enumerate(lines, 1):
        stripped = line.lstrip()
        is_quote = stripped.startswith('>')
        is_fence = stripped.startswith('```') or line.lstrip(' >').startswith('```')

        if is_quote:
            in_quote = True
        elif not line.strip():
            pass  # 空行不切换 quote 上下文（让 fence 检测能跨行）
        else:
            in_quote = False

        # 非引用块的 ``` 切换代码块状态
        if is_fence and not in_quote and not is_quote:
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        # 引用块内的 ``` 不切代码块状态——里面的中文需要扫

        # 屏蔽行内代码、URL 部分
        clean = re.sub(r'`[^`]+`',
                       lambda m: ' ' * len(m.group(0)), line)
        clean = re.sub(r'\]\([^)]+\)',
                       lambda m: ' ' * len(m.group(0)), clean)

        for kind, pats in rules:
            for pat in pats:
                for m in re.finditer(pat, clean):
                    snippet = line[max(0, m.start()-10):m.end()+10]
                    issues.append((i, m.start(), snippet, kind))

    # 去重（同一位置可能被多条规则命中）
    seen = set()
    unique = []
    for it in issues:
        key = (it[0], it[1])
        if key not in seen:
            seen.add(key)
            unique.append(it)
    return unique


# ============================================================
# Python 文件的安全 fix：只改注释和字符串字面量
# ============================================================
def fix_python_file(text):
    """对 Python 文件做安全的标点修复：只改注释和字符串字面量，不动代码语法。

    用 tokenize 模块识别 token，只对 COMMENT 和 STRING 类型应用 fix_text。
    """
    import tokenize
    import io

    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except tokenize.TokenizeError:
        return None  # 解析失败，放弃自动修复

    lines = text.split('\n')

    def offset_of(row, col):
        return sum(len(lines[i]) + 1 for i in range(row - 1)) + col

    # Python 3.12+ 把 f-string 拆成 FSTRING_START/MIDDLE/END，需要专门处理
    safe_types = {tokenize.COMMENT, tokenize.STRING}
    fstring_middle = getattr(tokenize, 'FSTRING_MIDDLE', None)
    if fstring_middle is not None:
        safe_types.add(fstring_middle)

    changes = []
    for tok in tokens:
        if tok.type == tokenize.COMMENT:
            # 注释：用完整 fix_text（包括括号转换）
            old = tok.string
            new = fix_text(old)
        elif tok.type in safe_types:
            # 字符串字面量：用安全版，不动括号/句号
            # (避免破坏正则字面量，例如 r'^（[零壹]）\s*(/)')
            old = tok.string
            new = fix_text_safe(old)
        else:
            continue

        if new != old:
            start = offset_of(tok.start[0], tok.start[1])
            end = offset_of(tok.end[0], tok.end[1])
            changes.append((start, end, new))

    if not changes:
        return text

    # 从后往前应用替换，避免位置偏移
    changes.sort(reverse=True)
    out = text
    for start, end, new in changes:
        out = out[:start] + new + out[end:]
    return out


# ============================================================
# 入口
# ============================================================
def scan_python(text):
    """Python 文件的扫描:只扫 token 类型为 COMMENT / STRING / FSTRING_MIDDLE 的内容。

    与 fix_python_file 的行为对齐:
    - COMMENT 用完整规则扫(fix 时也用完整 fix_text)
    - STRING / FSTRING_MIDDLE 跳过括号和句号(fix 时用 fix_text_safe 不会修这些,
      避免 false positive)
    """
    import tokenize, io
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except tokenize.TokenizeError:
        return []

    safe_types = {tokenize.COMMENT, tokenize.STRING}
    fstring_middle = getattr(tokenize, 'FSTRING_MIDDLE', None)
    if fstring_middle is not None:
        safe_types.add(fstring_middle)

    # fix_text_safe 不处理的问题种类(扫描字符串字面量时要过滤掉这些)
    SKIP_FOR_STRINGS = {'半角括号', '半角句号'}

    issues = []
    for tok in tokens:
        if tok.type not in safe_types:
            continue
        sub_issues = scan(tok.string)
        for sub in sub_issues:
            kind = sub[3]
            # 字符串字面量里跳过 fix 不会修的种类
            if tok.type != tokenize.COMMENT and kind in SKIP_FOR_STRINGS:
                continue
            issues.append((tok.start[0] + sub[0] - 1, sub[1], sub[2], kind))

    seen = set()
    unique = []
    for it in issues:
        key = (it[0], it[1], it[3])
        if key not in seen:
            seen.add(key)
            unique.append(it)
    return unique


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

    # 文件类型保护：fix 模式按文件类型走不同路径
    SAFE_EXTS = {'.md', '.markdown', '.txt'}
    PYTHON_EXTS = {'.py'}

    raw = in_path.read_text(encoding='utf-8')

    if do_fix and in_path.suffix in PYTHON_EXTS:
        # Python 文件：只 fix 注释和字符串字面量
        fixed = fix_python_file(raw)
        if fixed is None:
            print(f'拒绝修复：{in_path} 无法被 tokenize 解析（语法错误？）',
                  file=sys.stderr)
            sys.exit(2)

        # 二次验证：fix 后语法仍然有效
        import ast
        try:
            ast.parse(fixed)
        except SyntaxError as e:
            print(f'拒绝写回：fix 后 Python 语法被破坏： {e}', file=sys.stderr)
            sys.exit(2)

        out_path.write_text(fixed, encoding='utf-8')
        print(f'✓ {in_path} → {out_path}（Python 注释/字符串字面量已修复）')
        return

    if do_fix and in_path.suffix not in SAFE_EXTS:
        print(f'拒绝修复：{in_path.suffix} 不是已知安全的文件类型',
              file=sys.stderr)
        print(f'  支持： {", ".join(sorted(SAFE_EXTS | PYTHON_EXTS))}',
              file=sys.stderr)
        sys.exit(2)

    if not do_fix:
        # 仅扫描：Python 文件走 token 扫描，markdown 走通用扫描
        if in_path.suffix in PYTHON_EXTS:
            issues = scan_python(raw)
        else:
            issues = scan(raw)
        if not issues:
            print(f'✓ {in_path}：无中文标点问题')
            return
        print(f'⚠ {in_path}：发现 {len(issues)} 处问题')
        from collections import Counter
        kinds = Counter(i[3] for i in issues)
        for k, c in kinds.most_common():
            print(f'    {k}: {c} 处')
        print()
        for i, (line_no, col, snippet, kind) in enumerate(issues[:20]):
            print(f'  {in_path}:{line_no}: [{kind}] ...{snippet.strip()}...')
        if len(issues) > 20:
            print(f'  ... 另有 {len(issues) - 20} 处省略')
        sys.exit(1)

    # 修复模式
    protected, phs = protect_code(raw)
    fixed = fix_text(protected)
    fixed = restore_code(fixed, phs)

    # 检查修复效果
    after_issues = len(scan(fixed))
    before_issues = len(scan(raw))

    out_path.write_text(fixed, encoding='utf-8')
    print(f'✓ {in_path} → {out_path}')
    print(f'  修复前： {before_issues} 处 → 修复后： {after_issues} 处')
    if after_issues > 0:
        print(f'  ⚠ 仍有 {after_issues} 处未修（可能是边界情况，需手动检查）')


if __name__ == '__main__':
    main()
