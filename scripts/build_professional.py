#!/usr/bin/env python3
"""
build_professional.py — Build the two-column "Professional" resume (photo sidebar).

This is the third pipeline output. It is for human/networking use only and is
deliberately NOT ATS-safe (frames, images, header content) — never run it through
ats_check.py.

Nothing about the candidate is hardcoded here. Name, credentials, contact lines,
education, and certifications all come from the content JSON, which the
/tailor-resume pipeline fills in from reference/core-resume.docx and
reference/background-notes.md. The headshot is read from reference/photo.jpg
(a required user-supplied input).

Layout technique
  * The navy sidebar is a full-page-height image anchored in the page HEADER
    (behind text, positioned relative to the page). Headers repeat on every page,
    so the sidebar fills the whole height of page 1 AND page 2 — no table cell to
    stop partway down.
  * Sidebar text (photo, name, contact, expertise, certifications, education) is
    a set of positioned paragraph frames pinned to the page-1 sidebar area.
  * Main content is ordinary body text with a wide left page margin, so it flows
    onto page 2 beside the same background.

Usage:
    python scripts/build_professional.py professional_<Company>.json output/Professional_<Company>_<Date>.docx

Content JSON (see reference/professional_schema.json). Bold markup inside strings: **text**.
"""

import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import docx
from docx.enum.text import WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from lxml import etree
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PHOTO = ROOT / "reference" / "photo.jpg"

# Candidate identity fields. All of these must be supplied in the content JSON,
# sourced from reference/core-resume.docx and reference/background-notes.md.
IDENTITY_FIELDS = ("name", "contact", "education")
REQUIRED_FIELDS = IDENTITY_FIELDS + ("headline", "profile", "core_expertise", "experience")

FONT = "Calibri"
NAVY = "1B2A49"
ACCENT = "C9A24B"          # muted gold: sidebar headings + thin edge rule
SIDEBAR_TEXT = "FFFFFF"
SIDEBAR_MUTED = "C9D3E6"
MAIN_TEXT = "222222"
MAIN_MUTED = "555555"

PAGE_W, PAGE_H = 8.5, 11.0
SIDEBAR_W = 2.75           # inches, navy band
SIDEBAR_PAD = 0.28         # inset of sidebar text from page edge / band edge
SIDEBAR_TOP = 0.4          # page-1 sidebar frame top (inches from page top)
SIDEBAR_TOP_P2 = 0.5       # page-2 sidebar frame top; aligns with main-column top margin
MAIN_LEFT = SIDEBAR_W + 0.3
MAIN_RIGHT = 0.5
MAIN_W = PAGE_W - MAIN_LEFT - MAIN_RIGHT


def validate(content, required=REQUIRED_FIELDS):
    """Fail fast on missing content or photo rather than rendering a half-empty sidebar."""
    missing = [f for f in required if not content.get(f)]
    if missing:
        raise ValueError(f"content is missing required field(s): {', '.join(missing)} "
                         "(pull these from reference/core-resume.docx / background-notes.md)")
    if not PHOTO.exists():
        raise FileNotFoundError(f"photo not found at {PHOTO} — add your headshot as reference/photo.jpg")


# ---------- low-level helpers ----------

def _rgb(hex_):
    return RGBColor.from_string(hex_)


def _solid_png(hex_):
    img = Image.new("RGB", (8, 8), "#" + hex_)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    return buf


def _portrait_crop(path, aspect=5 / 6, face_x=0.5):
    """Portrait crop (width:height = aspect) keeping full head-and-shoulders,
    horizontally centered on the face. Returns an in-memory JPEG."""
    im = Image.open(path).convert("RGB")
    w, h = im.size
    cw, ch = w, int(w / aspect)
    if ch > h:
        ch, cw = h, int(h * aspect)
    cx = int(face_x * w)
    left = min(max(cx - cw // 2, 0), w - cw)
    top = 0  # head sits at the top of the frame; trim from the bottom only
    im = im.crop((left, top, left + cw, top + ch))
    im.thumbnail((900, 1080))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=90)
    buf.seek(0)
    return buf, im.size


def _inline_to_anchor(inline, x_emu, y_emu, behind=True):
    """Convert a python-docx inline picture into a page-anchored floating one."""
    wp = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
    nsmap = inline.nsmap
    anchor = etree.SubElement(inline.getparent(), "{%s}anchor" % wp, nsmap=nsmap)
    for k, v in (("distT", "0"), ("distB", "0"), ("distL", "0"), ("distR", "0"),
                 ("simplePos", "0"), ("relativeHeight", "0"),
                 ("behindDoc", "1" if behind else "0"), ("locked", "1"),
                 ("layoutInCell", "1"), ("allowOverlap", "1")):
        anchor.set(k, v)
    sp = etree.SubElement(anchor, "{%s}simplePos" % wp)
    sp.set("x", "0"); sp.set("y", "0")
    for tag, val in (("positionH", x_emu), ("positionV", y_emu)):
        pos = etree.SubElement(anchor, "{%s}%s" % (wp, tag))
        pos.set("relativeFrom", "page")
        off = etree.SubElement(pos, "{%s}posOffset" % wp)
        off.text = str(int(val))
    anchor.append(inline.find("{%s}extent" % wp))
    ee = etree.SubElement(anchor, "{%s}effectExtent" % wp)
    for k in ("l", "t", "r", "b"):
        ee.set(k, "0")
    etree.SubElement(anchor, "{%s}wrapNone" % wp)
    anchor.append(inline.find("{%s}docPr" % wp))
    anchor.append(inline.find("{%s}cNvGraphicFramePr" % wp))
    anchor.append(inline.find("{http://schemas.openxmlformats.org/drawingml/2006/main}graphic"))
    inline.getparent().remove(inline)


def _add_band(header, hex_, x_in, width_in, height_in):
    run = header.paragraphs[0].add_run()
    run.add_picture(_solid_png(hex_), width=Inches(width_in), height=Inches(height_in))
    inline = run._r.find(".//" + qn("wp:inline"))
    _inline_to_anchor(inline, Inches(x_in), 0)


def _style_run(run, size, bold=False, italic=False, color=MAIN_TEXT, caps=False, spacing=None):
    run.font.name = FONT
    run._r.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), FONT)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = _rgb(color)
    if caps:
        run.font.all_caps = True
    if spacing is not None:
        rPr = run._r.get_or_add_rPr()
        sp = OxmlElement("w:spacing")
        sp.set(qn("w:val"), str(int(spacing * 20)))
        rPr.append(sp)
    return run


def _rich(p, text, size, color=MAIN_TEXT, bold_color=None, italic=False):
    """Add text with **bold** markup as runs."""
    for i, part in enumerate(re.split(r"\*\*", text)):
        if not part:
            continue
        _style_run(p.add_run(part), size, bold=(i % 2 == 1), italic=italic,
                   color=(bold_color or color) if i % 2 == 1 else color)


def _fmt(p, before=0, after=0, line=1.0, left=None, first=None, keep_next=False):
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = line
    if left is not None:
        pf.left_indent = Inches(left)
    if first is not None:
        pf.first_line_indent = Inches(first)
    pf.keep_with_next = keep_next
    pf.widow_control = True


def _bottom_border(p, hex_, sz=6, space=1):
    pPr = p._p.get_or_add_pPr()
    b = OxmlElement("w:pBdr")
    bt = OxmlElement("w:bottom")
    for k, v in (("val", "single"), ("sz", str(sz)), ("space", str(space)), ("color", hex_)):
        bt.set(qn("w:" + k), v)
    b.append(bt)
    pPr.append(b)


def _frame(p, y_in):
    """Pin paragraph p into the page-1 sidebar area. Paragraphs sharing identical
    framePr attributes merge into one frame, so every sidebar paragraph gets the same one."""
    pPr = p._p.get_or_add_pPr()
    fp = OxmlElement("w:framePr")
    for k, v in (("w", int((SIDEBAR_W - 2 * SIDEBAR_PAD) * 1440)), ("hSpace", 0), ("vSpace", 0),
                 ("wrap", "around"), ("vAnchor", "page"), ("hAnchor", "page"),
                 ("x", int(SIDEBAR_PAD * 1440)), ("y", int(y_in * 1440))):
        fp.set(qn("w:" + k), str(v))
    pPr.insert(0, fp)


# ---------- sidebar ----------

def _sb_para(d, y_in):
    p = d.add_paragraph()
    _frame(p, y_in)
    return p


def _sb_heading(d, y, text, first=False):
    p = _sb_para(d, y)
    _fmt(p, before=0 if first else 11, after=3, keep_next=True)
    _style_run(p.add_run(text.upper()), 9.5, bold=True, color=ACCENT, spacing=1.2)
    _bottom_border(p, ACCENT, sz=4, space=2)
    return p


def _sb_line(d, y, text, size=9, color=SIDEBAR_TEXT, bold=False, after=2.5, bullet=False):
    p = _sb_para(d, y)
    if bullet:
        _fmt(p, after=after, left=0.14, first=-0.14)
        _style_run(p.add_run("▪ "), size - 1, color=ACCENT)
    else:
        _fmt(p, after=after)
    _rich(p, text, size, color=color, bold_color=color) if not bold else _style_run(
        p.add_run(text), size, bold=True, color=color)
    return p


def _sb_education(d, y, c, first=False):
    _sb_heading(d, y, "Education", first=first)
    for e in c["education"]:
        p = _sb_para(d, y)
        _fmt(p, after=0)
        _style_run(p.add_run(e["degree"]), 9, bold=True, color=SIDEBAR_TEXT)
        p = _sb_para(d, y)
        _fmt(p, after=4)
        _style_run(p.add_run(e["school"]), 8.5, color=SIDEBAR_MUTED)


def _sb_certifications(d, y, c):
    if not c.get("certifications"):
        return
    _sb_heading(d, y, "Certifications")
    for item in c["certifications"]:
        _sb_line(d, y, item, size=9, bullet=True, after=2)


def build_sidebar_page1(d, c, include_edu_certs):
    """Page-1 sidebar (body frame): photo, name, contact, core expertise.
    When the resume is a single page, education and certifications follow here too."""
    y = SIDEBAR_TOP
    buf, (pw, ph) = _portrait_crop(PHOTO)
    width_in = SIDEBAR_W - 2 * SIDEBAR_PAD
    p = _sb_para(d, y)
    _fmt(p, after=7)
    p.add_run().add_picture(buf, width=Inches(width_in), height=Inches(width_in * ph / pw))

    p = _sb_para(d, y)
    _fmt(p, after=0, line=0.95)
    _style_run(p.add_run(c["name"].upper()), 19, bold=True, color=SIDEBAR_TEXT, spacing=0.5)
    if c.get("credentials"):
        p = _sb_para(d, y)
        _fmt(p, after=4)
        _style_run(p.add_run(c["credentials"]), 10.5, color=ACCENT, bold=True, spacing=1)

    _sb_heading(d, y, "Contact")
    for line in c["contact"]:
        _sb_line(d, y, line, size=9, color=SIDEBAR_TEXT)

    _sb_heading(d, y, "Core Expertise")
    for item in c["core_expertise"]:
        _sb_line(d, y, item, size=9, bullet=True, after=2)

    if include_edu_certs:
        _sb_education(d, y, c)
        _sb_certifications(d, y, c)


def build_sidebar_page2(header, c):
    """Page-2 sidebar: education, then certifications. Lives in the header used for
    pages after the first (different-first-page header), pinned to the same left column,
    because Word frames never flow onto the next page."""
    y = SIDEBAR_TOP_P2
    _sb_education(header, y, c, first=True)
    _sb_certifications(header, y, c)


# ---------- main column ----------

def _main_heading(d, text):
    p = d.add_paragraph()
    _fmt(p, before=9, after=4, keep_next=True)
    _style_run(p.add_run(text.upper()), 11, bold=True, color=NAVY, spacing=1.2)
    _bottom_border(p, ACCENT, sz=8, space=2)


def build_main(d, c):
    p = d.add_paragraph()
    _fmt(p, after=1, line=0.95, keep_next=True)
    _style_run(p.add_run(c["headline"]), 15, bold=True, color=NAVY)
    if c.get("tagline"):
        p = d.add_paragraph()
        _fmt(p, after=2, keep_next=True)
        _style_run(p.add_run(c["tagline"]), 9.5, italic=True, color=MAIN_MUTED)

    _main_heading(d, "Executive Profile")
    for para in c["profile"]:
        p = d.add_paragraph()
        _fmt(p, after=4, line=1.05)
        _rich(p, para, 9.5, bold_color=NAVY)

    _main_heading(d, "Professional Experience")
    for job in c["experience"]:
        p = d.add_paragraph()
        _fmt(p, before=5, after=0, keep_next=True)
        p.paragraph_format.tab_stops.add_tab_stop(Inches(MAIN_W), WD_TAB_ALIGNMENT.RIGHT)
        _style_run(p.add_run(job["company"].upper()), 10.5, bold=True, color=NAVY)
        _style_run(p.add_run("\t" + job["dates"]), 9, color=MAIN_MUTED)
        p = d.add_paragraph()
        _fmt(p, after=2, keep_next=True)
        _style_run(p.add_run(job["title"]), 9.5, italic=True, bold=True, color=MAIN_MUTED)
        for b in job["bullets"]:
            p = d.add_paragraph()
            _fmt(p, after=2, line=1.03, left=0.17, first=-0.17)
            _style_run(p.add_run("▪  "), 8, color=ACCENT)
            _rich(p, b, 9.5, bold_color=NAVY)


# ---------- entry point ----------

def _construct(c, two_page):
    """Build the document. two_page=True splits the sidebar: page 1 (photo, name, contact,
    core expertise) in a body frame, page 2 (education, certifications) in the header for
    pages after the first. two_page=False keeps all sidebar content together on page 1."""
    d = docx.Document()
    d.styles["Normal"].font.name = FONT
    d.styles["Normal"].font.size = Pt(9.5)
    s = d.sections[0]
    s.page_width, s.page_height = Inches(PAGE_W), Inches(PAGE_H)
    s.left_margin, s.right_margin = Inches(MAIN_LEFT), Inches(MAIN_RIGHT)
    s.top_margin, s.bottom_margin = Inches(0.5), Inches(0.5)
    s.header_distance = Inches(0.2)
    s.different_first_page_header_footer = two_page

    # Page-level background: an image anchored in the header, so it spans the full page height.
    # With a different-first-page header, both headers carry the band.
    headers = [s.header]
    if two_page:
        headers.insert(0, s.first_page_header)
    for h in headers:
        h.is_linked_to_previous = False
        h.paragraphs[0].paragraph_format.space_after = Pt(0)
        _add_band(h, NAVY, 0, SIDEBAR_W, PAGE_H)
        _add_band(h, ACCENT, SIDEBAR_W, 0.05, PAGE_H)
    if two_page:
        build_sidebar_page2(s.header, c)  # s.header = pages 2+

    build_sidebar_page1(d, c, include_edu_certs=not two_page)
    build_main(d, c)
    first = d.paragraphs[0]
    if not first.text and first._p.find(".//" + qn("w:drawing")) is None and first._p.find(qn("w:pPr")) is None:
        first._p.getparent().remove(first._p)
    return d


def _to_pdf(docx_path, out_dir):
    """Render docx -> PDF with LibreOffice if on PATH, else Microsoft Word (Windows only)."""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if soffice:
        subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), str(docx_path)],
                       check=True, capture_output=True, timeout=120)
        return out_dir / (Path(docx_path).stem + ".pdf")
    if sys.platform == "win32":
        pdf = out_dir / "pagecount.pdf"
        ps = ("$w=New-Object -ComObject Word.Application;$w.Visible=$false;"
              f"$d=$w.Documents.Open('{docx_path}',$false,$true);"
              f"$d.ExportAsFixedFormat('{pdf}',17);$d.Close($false);$w.Quit()")
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True, capture_output=True, timeout=120)
        return pdf
    raise RuntimeError("no renderer (LibreOffice or Word) available")


def _page_count(path):
    """Rendered page count via LibreOffice or Word + pymupdf. Returns None if unavailable,
    in which case the caller falls back to a text-length estimate."""
    try:
        import pymupdf
        with tempfile.TemporaryDirectory() as tmp:
            pdf = _to_pdf(Path(path).resolve(), Path(tmp))
            with pymupdf.open(pdf) as doc:
                return len(doc)
    except Exception as e:  # renderer/pymupdf missing
        print(f"warning: could not render to count pages ({e.__class__.__name__}); estimating from text length", file=sys.stderr)
        return None


def _estimate_pages(c):
    chars = sum(len(t) for t in c["profile"]) + sum(len(b) + 12 for j in c["experience"] for b in j["bullets"])
    return 1 if chars < 3800 else 2


def build(content, out_path):
    validate(content)
    c = dict(content)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    # Word frames cannot flow across pages, so the sidebar layout depends on page count.
    # Pass 1: lay out as two pages and measure. If it fits on one page, rebuild with the
    # whole sidebar (incl. education and certifications) together on that page.
    d = _construct(c, two_page=True)
    tmp = Path(str(out_path) + ".pagecount.tmp.docx")
    d.save(tmp)
    try:
        pages = _page_count(tmp) or _estimate_pages(c)
    finally:
        tmp.unlink(missing_ok=True)
    if pages < 2:
        d = _construct(c, two_page=False)
    d.save(out_path)
    return pages


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    n = build(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")), sys.argv[2])
    print(f"Saved {sys.argv[2]} ({n} page{'s' if n != 1 else ''}; sidebar {'split across pages' if n > 1 else 'on one page'})")
