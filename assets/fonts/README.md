This directory is populated by `scripts/install_fonts.py` on first build.

The fonts themselves are not committed to the repository (see `.gitignore`):
they are ~33 MB combined and we prefer to fetch them from upstream rather
than vendor them. Running `python3 scripts/install_fonts.py` or building
any PDF via `scripts/build_pdf.py` will download them automatically.

Fonts installed here:

- NotoSansCJKsc-Regular.otf  (Noto Sans CJK SC, Regular weight, OFL)
- NotoSansCJKsc-Bold.otf     (Noto Sans CJK SC, Bold weight, OFL)
- JetBrainsMono-Regular.ttf  (JetBrains Mono, Regular weight, OFL)
