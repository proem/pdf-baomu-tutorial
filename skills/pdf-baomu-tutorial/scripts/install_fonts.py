#!/usr/bin/env python3
"""
install_fonts.py — download the fonts used by pdf-baomu-tutorial into
`assets/fonts/`, so PDF rendering does not depend on system-wide font
packages.

Usage::

    python3 scripts/install_fonts.py            # download missing fonts
    python3 scripts/install_fonts.py --force    # re-download even if present
    python3 scripts/install_fonts.py --check    # exit 0 if installed, 1 if not

Downloads are idempotent. Files already on disk with a non-empty size
are skipped unless --force is given. Total payload is ~34 MB; expect
~10-30 s on a normal connection, longer behind GFW.

This script never installs anything system-wide and never asks for sudo.
It only writes into `<repo>/assets/fonts/`.
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
import urllib.error
from pathlib import Path

# Resolve repo root from this file's location:
# <repo>/scripts/install_fonts.py -> <repo>
REPO_ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = REPO_ROOT / "assets" / "fonts"

# Upstream font sources. Each entry: (filename, url, expected min size in bytes).
# Pinning to raw.githubusercontent.com because GitHub's `/raw/` redirect
# strips off the User-Agent header in some clients, and direct raw URLs
# behave more predictably.
FONTS: list[tuple[str, str, int]] = [
    (
        "NotoSansCJKsc-Regular.otf",
        "https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf",
        15_000_000,
    ),
    (
        "NotoSansCJKsc-Bold.otf",
        "https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Bold.otf",
        15_000_000,
    ),
    (
        "JetBrainsMono-Regular.ttf",
        "https://raw.githubusercontent.com/JetBrains/JetBrainsMono/master/fonts/ttf/JetBrainsMono-Regular.ttf",
        200_000,
    ),
]


def _ok(path: Path, min_size: int) -> bool:
    return path.exists() and path.stat().st_size >= min_size


def check_installed() -> bool:
    """Return True if every required font is present and large enough."""
    return all(_ok(FONTS_DIR / name, size) for name, _, size in FONTS)


def _download(url: str, dest: Path, min_size: int) -> None:
    print(f"  · fetching {dest.name} ({min_size // 1_000_000} MB-ish) ...", flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": "pdf-baomu-tutorial/install_fonts"})
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp, open(tmp, "wb") as fh:
            while True:
                chunk = resp.read(64 * 1024)
                if not chunk:
                    break
                fh.write(chunk)
    except urllib.error.URLError as exc:
        if tmp.exists():
            tmp.unlink()
        raise SystemExit(
            f"  ! download failed: {exc}\n"
            f"  ! url: {url}\n"
            f"  ! check network (GFW may require a proxy for raw.githubusercontent.com)"
        )

    actual = tmp.stat().st_size
    if actual < min_size:
        tmp.unlink()
        raise SystemExit(
            f"  ! download too small ({actual} < {min_size} bytes); "
            f"upstream may have returned an HTML error page. Aborting."
        )
    tmp.replace(dest)
    print(f"  · saved {dest.name} ({actual // 1024} KB)")


def install(force: bool = False) -> None:
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"target dir: {FONTS_DIR}")

    needed = 0
    for name, url, min_size in FONTS:
        dest = FONTS_DIR / name
        if not force and _ok(dest, min_size):
            print(f"  · {name} already present, skip")
            continue
        _download(url, dest, min_size)
        needed += 1

    if needed == 0:
        print("all fonts already installed.")
    else:
        print(f"installed {needed} font file(s).")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Install fonts used by pdf-baomu-tutorial.")
    p.add_argument("--force", action="store_true",
                   help="Re-download even if files exist.")
    p.add_argument("--check", action="store_true",
                   help="Exit 0 if all fonts are installed, 1 otherwise. Do not download.")
    args = p.parse_args(argv)

    if args.check:
        ok = check_installed()
        print("installed" if ok else "missing")
        return 0 if ok else 1

    install(force=args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
