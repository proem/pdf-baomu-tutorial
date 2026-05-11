#!/usr/bin/env python3
"""
build_pdf.py - 把模板填好的 HTML 转换成保姆教程风格的 PDF。

用法：
    python3 build_pdf.py input.html output.pdf

需要：
    pip install weasyprint --break-system-packages

说明：
    - 使用 Noto Sans CJK 字体（Linux/容器环境默认有）
    - 输出 A4，对中文、emoji、CSS 渐变、全出血封面支持完整
"""

import sys
import os
from pathlib import Path


def _ensure_fonts(skill_root: Path) -> None:
    """Verify bundled fonts are present; auto-download via install_fonts.py if not.

    Renders still work without bundled fonts (each @font-face declaration
    starts with local() entries pointing at system installs), but for a
    consistent look across machines we want the OTF/TTF on disk.
    """
    sys.path.insert(0, str(skill_root / "scripts"))
    try:
        import install_fonts  # type: ignore
    except ImportError:
        # install_fonts.py is part of the skill, so this only happens on
        # a broken checkout. Don't crash the render — fall back silently.
        print("⚠ install_fonts.py 未找到，使用系统字体兜底", file=sys.stderr)
        return

    if install_fonts.check_installed():
        return

    print("· 首次渲染：正在下载捆绑字体到 assets/fonts/ ...")
    try:
        install_fonts.install(force=False)
    except SystemExit as exc:
        # install_fonts.py raises SystemExit on download failure. Don't
        # take the whole build down — system font fallback is still good.
        print(f"⚠ 字体下载失败({exc})，本次使用系统字体兜底", file=sys.stderr)


def build(input_html: str, output_pdf: str, *,
          lint: bool = True, highlight: bool = True) -> None:
    """把 HTML 文件转成 PDF。

    Args:
        input_html:  输入 HTML 文件路径
        output_pdf:  输出 PDF 文件路径
        lint:        是否在渲染前跑 HTML lint(默认 True)
                     lint 会修中文段落里的半角标点 / 中英文空格 / 引号等
                     依据中文文案排版指北 + 自定义规则
        highlight:   是否对代码块跑 Shiki 语法高亮(默认 True)
                     需要 Node.js + npm install shiki(在 skill 根目录)
                     没装会安全降级到原 HTML
    """
    try:
        from weasyprint import HTML, CSS
        from weasyprint.text.fonts import FontConfiguration
    except ImportError:
        print("错误：需要先安装 weasyprint", file=sys.stderr)
        print("运行：pip install weasyprint --break-system-packages", file=sys.stderr)
        sys.exit(1)

    input_path = Path(input_html).resolve()
    output_path = Path(output_pdf).resolve()

    if not input_path.exists():
        print(f"错误：输入文件不存在：{input_path}", file=sys.stderr)
        sys.exit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Skill root: <skill>/scripts/build_pdf.py → <skill>
    skill_root = Path(__file__).resolve().parent.parent
    styles_css = skill_root / "templates" / "styles.css"

    # Make sure bundled fonts exist before we render. If install_fonts.py
    # has never been run (or was wiped), download them now. We fall back
    # to system fonts via the local() clauses in @font-face if download
    # fails for any reason — render still succeeds, just less self-contained.
    _ensure_fonts(skill_root)

    # 嵌套 context manager:lint_for_render → highlight_for_render → render
    # 都失败安全降级(yield 原路径),自动清理临时文件
    sys.path.insert(0, str(Path(__file__).parent))
    from contextlib import contextmanager

    try:
        from lint_html import lint_for_render
    except ImportError:
        @contextmanager
        def lint_for_render(p, lint=True):  # type: ignore
            print("⚠ Lint 跳过(缺依赖);用 --no-lint 显式关闭",
                  file=sys.stderr)
            yield Path(p)

    try:
        from highlight_html import highlight_for_render
    except ImportError:
        @contextmanager
        def highlight_for_render(p, highlight=True):  # type: ignore
            print("⚠ Highlight 跳过(缺依赖);用 --no-highlight 显式关闭",
                  file=sys.stderr)
            yield Path(p)

    with lint_for_render(input_path, lint=lint) as linted_path:
        with highlight_for_render(linted_path, highlight=highlight) as render_path:
            print(f"正在生成 PDF:{render_path.name} → {output_path.name}")
            font_config = FontConfiguration()
            # Inject styles.css explicitly with base_url at the skill's
            # templates/ dir, so the relative url("../assets/fonts/...")
            # inside @font-face resolves to the bundled fonts regardless
            # of where the user's filled HTML lives.
            stylesheet = CSS(filename=str(styles_css), font_config=font_config)
            HTML(filename=str(render_path)).write_pdf(
                str(output_path),
                stylesheets=[stylesheet],
                font_config=font_config,
            )

    size_kb = output_path.stat().st_size / 1024
    print(f"✓ 完成,大小 {size_kb:.1f} KB,路径:{output_path}")

    # 输出页数
    try:
        from pypdf import PdfReader
        pages = len(PdfReader(str(output_path)).pages)
        print(f"  共 {pages} 页")
    except ImportError:
        pass


def preview_pages(pdf_path: str, pages: str = "1,3,-1") -> None:
    """用 pdftoppm 抽取指定页为 PNG 用于检查排版。

    pages 格式： "1,3,-1" (首页、第3页、末页)
    """
    import subprocess
    from pypdf import PdfReader

    pdf = Path(pdf_path).resolve()
    total = len(PdfReader(str(pdf)).pages)
    out_dir = pdf.parent / "_preview"
    out_dir.mkdir(exist_ok=True)

    page_nums = []
    for p in pages.split(","):
        p = int(p.strip())
        if p < 0:
            p = total + p + 1
        page_nums.append(p)

    for p in page_nums:
        prefix = out_dir / f"page-{p:02d}"
        subprocess.run([
            "pdftoppm", "-f", str(p), "-l", str(p),
            "-r", "80", "-png",
            str(pdf), str(prefix),
        ], check=True)
        print(f"  预览：{prefix}-{p:02d}.png")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    do_lint = "--no-lint" not in sys.argv
    do_highlight = "--no-highlight" not in sys.argv
    build(sys.argv[1], sys.argv[2], lint=do_lint, highlight=do_highlight)

    # 可选：加 --preview 参数自动抽几页看
    if "--preview" in sys.argv:
        preview_pages(sys.argv[2])
