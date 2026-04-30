#!/usr/bin/env python3
"""Convert packaging/linux/simplelog.svg → a PNG at the given output path.

Usage:
    python3 packaging/make_icon.py <output.png> [size]

Requires PyQt6 (already a project dependency).
"""
import sys
from pathlib import Path

from PyQt6.QtCore import QSize
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtWidgets import QApplication

SVG_PATH = Path(__file__).parent / "linux" / "simplelog.svg"


def render(output: Path, size: int = 256) -> None:
    _app = QApplication.instance() or QApplication(sys.argv[:1])

    widget = QSvgWidget(str(SVG_PATH))
    widget.resize(QSize(size, size))

    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(0)  # transparent

    painter = QPainter(img)
    widget.render(painter)
    painter.end()

    output.parent.mkdir(parents=True, exist_ok=True)
    if not img.save(str(output)):
        sys.exit(f"ERROR: could not save PNG to {output}")
    print(f"Icon written → {output}  ({size}×{size})")


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("dist/simplelog.png")
    sz = int(sys.argv[2]) if len(sys.argv) > 2 else 256
    render(out, sz)
