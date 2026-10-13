#!/usr/bin/env python3
"""
preview_docx.py — Render a .docx to PDF (LibreOffice if installed, else Microsoft Word on
Windows), then to one PNG per page. Prints the page count. Use it to look at every page of
every deliverable after the last content change.

Usage: python scripts/preview_docx.py output/Professional_Acme_2026-01-15.docx <new_dir>
"""
import shutil
import sys
import tempfile
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_professional import _to_pdf  # noqa: E402

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src = Path(sys.argv[1]).resolve()
    out = (Path(sys.argv[2]) if len(sys.argv) > 2 else src.parent / "preview").resolve()
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        pdf = out / (src.stem + ".pdf")
        shutil.copyfile(_to_pdf(src, Path(tmp)), pdf)
    with pymupdf.open(pdf) as doc:
        print("pages:", len(doc))
        for i, page in enumerate(doc, 1):
            png = out / f"{src.stem}_p{i}.png"
            page.get_pixmap(dpi=80).save(png)
            print(png)
