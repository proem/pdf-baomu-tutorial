#!/usr/bin/env python3
"""
preview_all.py — 生成完整的 PDF 预览工具：contact sheet + 填充率扫描。

用法：
    python3 preview_all.py input.html output.pdf
        → 生成 PDF、输出填充率报告、生成 contact sheet

    python3 preview_all.py input.html --scan-only
        → 只做填充率扫描，不写盘（快速迭代用）

    python3 preview_all.py input.pdf --contact-sheet sheet.png
        → 只对已有 PDF 生成 contact sheet

输出：
    - <output>.pdf                    PDF 文件
    - <output>_sheet.png              所有页面拼成的 contact sheet
    - <output>_pages/pN.png           每页的单独高清 PNG（按需）
    - 控制台：填充率表格 + 溢出 hint

原理（路径 3 / WeasyPrint box tree）：
    不靠像素扫描猜填充率。直接读 WeasyPrint 渲染时已经算过的 box 坐标——
    每页最后一个叶子 box 的底部 y = 实际内容占用高度。

溢出 hint 启发式：
    - 填充率 < 40% 且不是最后一页 → 本页末尾留白过大（"短尾"候选）
    - 连续两页：前页 > 85% 且后页 < 15% → 后页只是前页溢出的少量孤行
    （这两种都是"回到 HTML 做微调，就能省掉一页"的信号）
"""

import sys
import argparse
from pathlib import Path


# ----------- 填充率扫描 -----------

def _walk_leaves(box):
    """枚举正文 box 树里所有叶子的 (bottom_y, class_name, text)。跳过 MarginBox（页眉页脚）。"""
    cls = type(box).__name__
    if cls == 'MarginBox':
        return
    children = getattr(box, 'children', []) or []
    if not children:
        y = getattr(box, 'position_y', None)
        h = getattr(box, 'height', None)
        if y is not None and h is not None:
            text = ""
            if hasattr(box, 'text') and box.text:
                text = str(box.text)[:60]
            yield (y + h, cls, text)
        return
    for c in children:
        yield from _walk_leaves(c)


def scan_density(document):
    """对 weasyprint Document 做填充率扫描。

    返回每页一个 dict：{page, fill_pct, usable_h, used_h, last_text, last_cls}
    """
    reports = []
    for i, page in enumerate(document.pages, 1):
        pb = page._page_box

        # 找正文根（跳过 MarginBox）
        root = None
        for c in pb.children:
            if type(c).__name__ == 'BlockBox':
                root = c
                break
        if root is None:
            reports.append({
                'page': i, 'fill_pct': 100.0,
                'usable_h': 0, 'used_h': 0,
                'last_text': '', 'last_cls': 'Cover',
            })
            continue

        usable_top = pb.content_box_y()
        # pb.height 已经是正文区高度（不含页眉页脚 margin box）
        avail_h = pb.height

        leaves = list(_walk_leaves(root))
        if not leaves:
            reports.append({
                'page': i, 'fill_pct': 0.0,
                'usable_h': avail_h, 'used_h': 0,
                'last_text': '', 'last_cls': 'Empty',
            })
            continue

        last_bottom, last_cls, last_text = max(leaves, key=lambda x: x[0])
        used_h = last_bottom - usable_top
        fill = used_h / avail_h * 100 if avail_h > 0 else 0
        reports.append({
            'page': i, 'fill_pct': fill,
            'usable_h': avail_h, 'used_h': used_h,
            'last_text': last_text, 'last_cls': last_cls,
        })
    return reports


def _first_element_on_page(page):
    """返回本页正文区的第一个语义元素（h1/h2/p 等），用于判断这页是不是新章起点。"""
    pb = page._page_box
    root = None
    for c in pb.children:
        if type(c).__name__ == 'BlockBox':
            root = c
            break
    if root is None:
        return None

    def dive(box, depth=0):
        if depth > 6:
            return None
        for child in getattr(box, 'children', []) or []:
            if type(child).__name__ == 'MarginBox':
                continue
            tag = getattr(child, 'element_tag', None)
            if tag and tag not in ('body', 'div'):
                return child
            if tag in ('body', 'div'):
                r = dive(child, depth + 1)
                if r is not None:
                    return r
        return None
    return dive(root)


def _page_starts_chapter(page):
    """本页是不是新章的起点（第一个元素是正文 h1，不含封面/目录/总结块）。"""
    el = _first_element_on_page(page)
    if el is None:
        return False
    if getattr(el, 'element_tag', None) != 'h1':
        return False
    # 排除封面和目录的 h1（字号明显不同）
    fs = float(el.style['font_size']) if el.style else 0
    # 正文 h1 约 29pt；封面 h1 约 42pt；目录 h1 约 26pt
    return 27.0 < fs < 35.0


def _page_starts_with_h2(page):
    """本页首元素是不是 h2（整个子小节被推到新页，属结构性短尾）。"""
    el = _first_element_on_page(page)
    if el is None:
        return False
    return getattr(el, 'element_tag', None) == 'h2'


def analyze_hints(reports, pages=None):
    """基于填充率报告产出"微调 hint"。

    前提假设：所有正文 h1 强制另起一页（模板默认行为）。规则：
    - 章内短尾（下一页不是新章但本页 <40%）→ 🚨 真问题，可能是误触发的 page-break
    - 章末残行（下一页是新章且本页 <25%）→ 💡 值得优化（就一两句话独占一页，显得啰嗦）
    - 章末自然短尾（下一页是新章且本页 >=25%）→ 不报警（预期行为）
    - 末页短尾 → 不报警
    - 首页（封面/目录）→ 不报警
    """
    hints = []
    total = len(reports)
    for idx, r in enumerate(reports):
        p = r['page']
        is_first = (p == 1)
        is_last = (p == total)
        if is_first or is_last:
            continue

        next_page = pages[idx + 1] if pages and idx + 1 < len(pages) else None
        next_starts_chapter = _page_starts_chapter(next_page) if next_page else False

        # 规则 1：章内短尾——本页 <40% 且下一页不是新章
        # 下一页还是本章的延续却只塞了半页，说明本章内部有误触发的 page-break
        # 或者有过大的 page-break-inside:avoid 元素把内容推到了下一页
        if r['fill_pct'] < 40 and not next_starts_chapter:
            hints.append({
                'page': p,
                'severity': 'high',
                'type': 'intra_chapter_short',
                'msg': f"P{p} 填充率仅 {r['fill_pct']:.0f}%，下一页仍是本章内容——章内出现意外分页，检查是否有 page-break 元素被误触发"
            })
            continue

        # 规则 2：章末残行——本页 <25%、下一页是新章、且**本页不是 h2 起头**
        # （h2 起头说明整个子小节被推到这一页，是结构性短尾，文字优化改不动）
        if r['fill_pct'] < 25 and next_starts_chapter:
            page_obj = pages[idx] if pages else None
            if page_obj and _page_starts_with_h2(page_obj):
                continue  # 结构性短尾，跳过
            hints.append({
                'page': p,
                'severity': 'medium',
                'type': 'chapter_tail_residue',
                'msg': f"P{p} 只有 {r['fill_pct']:.0f}%（最后一块：「{r['last_text']}」）——就一两句话独占一页，考虑优化文字让内容回流到前页"
            })
    return hints


def print_report(reports, hints):
    """打印填充率表格 + hint。"""
    print()
    print("=" * 70)
    print(f"{'页':>3} {'填充率':>8} {'状态':>6}  最后一个 block")
    print("-" * 70)
    for r in reports:
        fill = r['fill_pct']
        if fill < 30:
            status = "⚠️ 低"
        elif fill < 60:
            status = "  中"
        elif fill < 90:
            status = "  良"
        else:
            status = "✓ 满"
        text = r['last_text'][:40]
        print(f"P{r['page']:>2} {fill:>6.1f}%   {status}   {text}")
    print("=" * 70)

    if hints:
        print()
        print("发现 {} 处可优化：".format(len(hints)))
        for h in hints:
            icon = "🚨" if h['severity'] == 'high' else "💡"
            print(f"  {icon} {h['msg']}")
    else:
        print()
        print("✓ 无明显可优化点。")


# ----------- Contact sheet -----------

def make_contact_sheet(pdf_path: Path, output_path: Path, dpi: int = 55, cols: int = 5):
    """把 PDF 所有页面渲染为 PNG，拼成 contact sheet。"""
    import subprocess
    import tempfile
    try:
        from PIL import Image
    except ImportError:
        print("警告：未安装 Pillow，跳过 contact sheet 生成", file=sys.stderr)
        print("  pip install Pillow --break-system-packages", file=sys.stderr)
        return

    # 先拿总页数
    try:
        from pypdf import PdfReader
        n_pages = len(PdfReader(str(pdf_path)).pages)
    except ImportError:
        # 退路：用 pdfinfo
        out = subprocess.check_output(["pdfinfo", str(pdf_path)]).decode()
        n_pages = int([l for l in out.split("\n") if l.startswith("Pages:")][0].split()[1])

    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        subprocess.run(
            ["pdftoppm", "-r", str(dpi), str(pdf_path), str(tmpdir / "p"), "-png"],
            check=True, capture_output=True,
        )
        files = sorted(tmpdir.glob("p-*.png"))
        if not files:
            print("错误：pdftoppm 没有产生任何页图", file=sys.stderr)
            return

        imgs = [Image.open(f) for f in files]
        w, h = imgs[0].size
        rows = (len(imgs) + cols - 1) // cols
        sheet = Image.new("RGB", (w * cols, h * rows), "#eeeeee")
        for i, img in enumerate(imgs):
            r, c = divmod(i, cols)
            sheet.paste(img, (c * w, r * h))

        # 适度缩放，避免文件过大
        sheet.thumbnail((2400, 3200))
        sheet.save(str(output_path))
        print(f"✓ Contact sheet: {output_path}  ({sheet.size[0]}×{sheet.size[1]}, {len(imgs)} 页)")


# ----------- 主入口 -----------

def main():
    ap = argparse.ArgumentParser(description="PDF 预览 + 填充率扫描")
    ap.add_argument("input", help="输入 HTML 或 PDF 文件")
    ap.add_argument("output", nargs="?", help="输出 PDF 路径（输入是 HTML 时必填）")
    ap.add_argument("--scan-only", action="store_true", help="只做填充率扫描，不写盘")
    ap.add_argument("--no-sheet", action="store_true", help="不生成 contact sheet")
    ap.add_argument("--no-lint", action="store_true",
                    help="跳过 HTML 文案 lint（默认会跑：修中文标点/空格/引号）")
    ap.add_argument("--no-highlight", action="store_true",
                    help="跳过代码块语法高亮（默认会跑 Shiki，需 Node.js + shiki）")
    ap.add_argument("--sheet-dpi", type=int, default=55, help="contact sheet 每页 DPI（默认 55）")
    args = ap.parse_args()

    inp = Path(args.input).resolve()
    if not inp.exists():
        print(f"错误：输入文件不存在：{inp}", file=sys.stderr)
        sys.exit(1)

    if inp.suffix.lower() == ".html":
        try:
            from weasyprint import HTML
        except ImportError:
            print("错误:需要 weasyprint", file=sys.stderr)
            sys.exit(1)

        # 嵌套 context manager(与 build_pdf 一致):lint → highlight → render
        sys.path.insert(0, str(Path(__file__).parent))
        from contextlib import contextmanager

        try:
            from lint_html import lint_for_render
        except ImportError:
            @contextmanager
            def lint_for_render(p, lint=True):
                print("⚠ Lint 跳过(缺依赖)", file=sys.stderr)
                yield Path(p)

        try:
            from highlight_html import highlight_for_render
        except ImportError:
            @contextmanager
            def highlight_for_render(p, highlight=True):
                print("⚠ Highlight 跳过(缺依赖)", file=sys.stderr)
                yield Path(p)

        with lint_for_render(inp, lint=not args.no_lint) as linted_path:
            with highlight_for_render(linted_path,
                                      highlight=not args.no_highlight) as render_path:
                print(f"渲染 {render_path.name}...")
                doc = HTML(filename=str(render_path)).render()
                reports = scan_density(doc)
                hints = analyze_hints(reports, pages=list(doc.pages))
                print_report(reports, hints)

                if not args.scan_only:
                    if not args.output:
                        print("错误:HTML 输入需要指定 output 路径", file=sys.stderr)
                        sys.exit(1)
                    out = Path(args.output).resolve()
                    out.parent.mkdir(parents=True, exist_ok=True)
                    doc.write_pdf(str(out))
                    size_kb = out.stat().st_size / 1024
                    print(f"\n✓ PDF: {out}  ({size_kb:.1f} KB, {len(reports)} 页)")
                    if not args.no_sheet:
                        sheet = out.with_name(out.stem + "_sheet.png")
                        make_contact_sheet(out, sheet, dpi=args.sheet_dpi)
    elif inp.suffix.lower() == ".pdf":
        # 只做 contact sheet
        if args.no_sheet:
            print("错误：PDF 输入且禁用 sheet，无事可做", file=sys.stderr)
            sys.exit(1)
        sheet = Path(args.output) if args.output else inp.with_name(inp.stem + "_sheet.png")
        make_contact_sheet(inp, sheet, dpi=args.sheet_dpi)
    else:
        print(f"错误：不认识的输入类型 {inp.suffix}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
