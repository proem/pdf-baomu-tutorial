#!/usr/bin/env python3
"""
highlight_html.py — Shiki 语法高亮的 Python wrapper。

通过 subprocess 调用同目录的 highlight_html.mjs,把 HTML 里的
<pre><code class="language-X"> 代码块替换成 Shiki 高亮版本(带 inline color)。

为什么要 Node.js: Shiki 是 JS 库,文档级保真的 TextMate grammar + VS Code
themes,Python 生态没有完全等价的库。集成代价是一次 subprocess 启动
(2-3 秒,只在含代码块的文档时才有)。

用法:
    # CLI
    python3 highlight_html.py input.html [output.html] [--theme github-dark]

    # 在 Python 里(推荐)
    from highlight_html import highlight_for_render
    with highlight_for_render(input_path, highlight=True) as render_path:
        HTML(filename=str(render_path)).write_pdf(...)

依赖:
    Node.js + npm install shiki(在 PDF skill 根目录)
    没装会安全降级到原 HTML,仅打印一行警告。
"""

import shutil
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

DEFAULT_THEME = 'github-dark'


def _find_node():
    """找 node 可执行文件;没找到返回 None"""
    return shutil.which('node')


def highlight_html(input_path, output_path=None, theme=DEFAULT_THEME):
    """对 HTML 文件应用语法高亮,返回 (输出路径, 处理的代码块数量, 错误信息)。

    错误信息为 None 表示成功。
    """
    input_path = Path(input_path)
    output_path = Path(output_path) if output_path else input_path

    node = _find_node()
    if not node:
        return output_path, 0, "Node.js not found in PATH"

    mjs_script = Path(__file__).parent / 'highlight_html.mjs'
    if not mjs_script.exists():
        return output_path, 0, f"highlight_html.mjs not found at {mjs_script}"

    try:
        result = subprocess.run(
            [node, str(mjs_script), str(input_path),
             str(output_path), theme],
            capture_output=True, text=True, timeout=60,
        )
    except subprocess.TimeoutExpired:
        return output_path, 0, "Shiki highlight timed out (60s)"
    except OSError as e:
        return output_path, 0, f"failed to invoke node: {e}"

    if result.returncode != 0:
        # node 报错(常见:shiki 未安装) — 把 stderr 提取关键信息
        err = result.stderr.strip().split('\n')[0] if result.stderr else 'unknown error'
        return output_path, 0, err

    # 解析 stdout 拿到处理数量
    out_lines = result.stdout.strip().split('\n')
    n_highlighted = 0
    for line in out_lines:
        # mjs 脚本输出格式: "✓ Highlighted N code blocks (theme: ...)"
        if 'Highlighted' in line and 'code block' in line:
            try:
                n_highlighted = int(line.split('Highlighted')[1].split('code')[0].strip())
            except (IndexError, ValueError):
                pass
            break

    return output_path, n_highlighted, None


@contextmanager
def highlight_for_render(html_path, highlight=True, theme=DEFAULT_THEME):
    """Context manager:为 PDF 渲染准备带语法高亮的 HTML。

    用法:
        with highlight_for_render(input.html, highlight=True) as render_path:
            HTML(filename=str(render_path)).write_pdf(...)

    行为:
    - highlight=False / Node.js 缺失 / shiki 缺失 → yield 原路径,不写临时文件
    - 没代码块 → yield 原路径
    - 有代码块且高亮成功 → 写到 .{stem}.highlighted.html 并 yield 该路径
    - 退出 with 块时自动删除临时文件(包括渲染抛异常时)
    """
    html_path = Path(html_path)

    if not highlight:
        yield html_path
        return

    tmp_path = html_path.parent / f'.{html_path.stem}.highlighted.html'
    out_path, n_highlighted, err = highlight_html(html_path, tmp_path, theme)

    if err:
        print(f"⚠ Highlight 跳过({err});用 --no-highlight 显式关闭",
              file=sys.stderr)
        if tmp_path.exists():
            tmp_path.unlink()
        yield html_path
        return

    if n_highlighted == 0:
        print("✓ Highlight:无代码块需要处理")
        if tmp_path.exists():
            tmp_path.unlink()
        yield html_path
        return

    print(f"✓ Highlight:{n_highlighted} 个代码块语法高亮(theme: {theme});"
          f"用 --no-highlight 关闭")

    try:
        yield tmp_path
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)

    in_path = Path(args[0])
    out_path = None
    theme = DEFAULT_THEME

    i = 1
    while i < len(args):
        if args[i] == '--theme' and i + 1 < len(args):
            theme = args[i + 1]
            i += 2
        elif not args[i].startswith('--'):
            out_path = args[i]
            i += 1
        else:
            i += 1

    out_path = out_path or in_path
    out, n, err = highlight_html(in_path, out_path, theme)

    if err:
        print(f"⚠ {err}", file=sys.stderr)
        sys.exit(1)

    print(f"✓ {n} code blocks highlighted (theme: {theme}) → {out}")


if __name__ == '__main__':
    main()
