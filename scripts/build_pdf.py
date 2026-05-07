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


def build(input_html: str, output_pdf: str, *, lint: bool = True) -> None:
    """把 HTML 文件转成 PDF。

    Args:
        input_html:  输入 HTML 文件路径
        output_pdf:  输出 PDF 文件路径
        lint:        是否在渲染前跑 HTML lint(默认 True)
                     lint 会修中文段落里的半角标点 / 中英文空格 / 引号等
                     依据中文文案排版指北 + 自定义规则
    """
    try:
        from weasyprint import HTML
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

    # 用 lint_html 的 context manager:自动跑 lint(默认),失败安全降级
    sys.path.insert(0, str(Path(__file__).parent))
    try:
        from lint_html import lint_for_render
    except ImportError:
        from contextlib import contextmanager

        @contextmanager
        def lint_for_render(p, lint=True):  # type: ignore
            print("⚠ Lint 跳过(缺依赖);用 --no-lint 显式关闭",
                  file=sys.stderr)
            yield Path(p)

    with lint_for_render(input_path, lint=lint) as render_path:
        print(f"正在生成 PDF:{render_path.name} → {output_path.name}")
        HTML(str(render_path)).write_pdf(str(output_path))

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
    build(sys.argv[1], sys.argv[2], lint=do_lint)

    # 可选：加 --preview 参数自动抽几页看
    if "--preview" in sys.argv:
        preview_pages(sys.argv[2])
