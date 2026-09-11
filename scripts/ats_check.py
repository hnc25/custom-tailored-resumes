#!/usr/bin/env python3
"""
ats_check.py — Objective ATS-compatibility and keyword-match scoring for a .docx resume.

Usage:
    python3 ats_check.py <resume.docx> <keywords.json> [--json]

keywords.json format:
{
  "must_have": ["product strategy", "roadmap", "stakeholder management"],
  "nice_to_have": ["SQL", "Agile", "AI"]
}

Outputs a human-readable report (or raw JSON with --json) covering:
  1. Keyword density  — must-have / nice-to-have term coverage, weighted
  2. Format compliance — tables, text boxes, headers/footers, columns,
     images, non-standard fonts, embedded objects (all things that break
     or scramble parsing in real ATS engines like Workday/Taleo/iCIMS)
  3. Section headers   — presence of standard, ATS-recognized section names
  4. Composite score   — 0-100

This script does NOT decide what the keywords should be or rewrite content —
that judgment call belongs to whoever (or whatever) is tailoring the resume.
It only measures the result objectively, the same way a real ATS would.
"""

import sys
import json
import re
import zipfile
import argparse
from pathlib import Path

try:
    import docx
except ImportError:
    print("ERROR: python-docx is required. Install with: pip install python-docx --break-system-packages", file=sys.stderr)
    sys.exit(1)

STANDARD_SECTIONS = [
    "professional experience", "experience", "work experience",
    "education", "certifications", "certification",
    "skills", "core competencies", "core expertise", "technical skills",
    "summary", "professional summary", "executive profile", "profile",
]

ATS_SAFE_FONTS = {
    "arial", "calibri", "times new roman", "georgia", "cambria",
    "garamond", "verdana", "tahoma", "helvetica", "book antiqua",
}


def load_docx_text(path):
    d = docx.Document(path)
    paras = [p.text for p in d.paragraphs]
    for table in d.tables:
        for row in table.rows:
            for cell in row.cells:
                paras.append(cell.text)
    return "\n".join(paras), d


def check_format(docx_path, doc):
    """Structural checks that mirror what real ATS parsers choke on."""
    issues = []
    points_lost = 0

    # Tables (ATS parsers frequently misread or skip table content entirely)
    if len(doc.tables) > 0:
        issues.append(f"Contains {len(doc.tables)} table(s) — many ATS parsers skip or scramble table content. Prefer plain paragraphs/bullets.")
        points_lost += 10

    # Headers/footers holding content (name, contact info in header is a classic ATS failure)
    for section in doc.sections:
        header_text = " ".join(p.text for p in section.header.paragraphs).strip()
        footer_text = " ".join(p.text for p in section.footer.paragraphs).strip()
        if header_text:
            issues.append(f"Header contains text ('{header_text[:50]}...') — some ATS engines never read headers/footers. Move contact info into the document body.")
            points_lost += 15
        if footer_text:
            issues.append(f"Footer contains text ('{footer_text[:50]}...') — move any content here into the body.")
            points_lost += 5

    # Text boxes / embedded shapes / images (detected via raw XML — python-docx doesn't expose these directly)
    with zipfile.ZipFile(docx_path) as z:
        xml = z.read("word/document.xml").decode("utf-8", errors="ignore")
        textbox_count = len(re.findall(r"<w:txbxContent>", xml))
        image_count = len(re.findall(r"<w:drawing>", xml))
        column_break = "w:cols" in xml and re.search(r'<w:cols[^>]*w:num="[2-9]"', xml)

    if textbox_count:
        issues.append(f"Contains {textbox_count} text box(es) — text inside text boxes is often invisible to ATS parsers entirely.")
        points_lost += 20
    if image_count:
        issues.append(f"Contains {image_count} image(s)/graphic(s) — any text rendered as an image is invisible to ATS. Purely decorative images are lower risk but still flagged.")
        points_lost += 5
    if column_break:
        issues.append("Document uses multi-column layout — column layouts frequently cause ATS parsers to read content out of order.")
        points_lost += 15

    # Fonts
    non_standard_fonts = set()
    for p in doc.paragraphs:
        for run in p.runs:
            if run.font.name and run.font.name.lower() not in ATS_SAFE_FONTS:
                non_standard_fonts.add(run.font.name)
    if non_standard_fonts:
        issues.append(f"Uses non-standard font(s): {', '.join(sorted(non_standard_fonts))}. Stick to Arial, Calibri, Times New Roman, Georgia, or Cambria for guaranteed parsing.")
        points_lost += 5

    return issues, max(0, 100 - points_lost)


def check_sections(text):
    lower = text.lower()
    found = [s for s in STANDARD_SECTIONS if s in lower]
    # Collapse to unique canonical categories so we don't double-credit synonyms
    has_experience = any(s in found for s in ["professional experience", "experience", "work experience"])
    has_education = "education" in found
    has_skills = any(s in found for s in ["skills", "core competencies", "core expertise", "technical skills"])
    has_summary = any(s in found for s in ["summary", "professional summary", "executive profile", "profile"])

    missing = []
    if not has_experience:
        missing.append("Experience")
    if not has_education:
        missing.append("Education")
    if not has_skills:
        missing.append("Skills/Competencies")
    if not has_summary:
        missing.append("Summary/Profile")

    score = 100 - (25 * len(missing))
    return missing, max(0, score)


def normalize(s):
    return re.sub(r"\s+", " ", s.lower().strip())


def check_keywords(text, keywords):
    text_norm = normalize(text)
    must_have = keywords.get("must_have", [])
    nice_to_have = keywords.get("nice_to_have", [])

    def find_matches(terms):
        matched, missing = [], []
        for term in terms:
            t = normalize(term)
            count = len(re.findall(r"\b" + re.escape(t) + r"\b", text_norm))
            if count > 0:
                matched.append((term, count))
            else:
                missing.append(term)
        return matched, missing

    must_matched, must_missing = find_matches(must_have)
    nice_matched, nice_missing = find_matches(nice_to_have)

    must_pct = (len(must_matched) / len(must_have) * 100) if must_have else 100
    nice_pct = (len(nice_matched) / len(nice_to_have) * 100) if nice_to_have else 100

    # Must-haves weighted 70%, nice-to-haves 30% — matches how real ATS
    # scoring engines and recruiter keyword screens typically weight requirements
    weighted_score = round(must_pct * 0.7 + nice_pct * 0.3)

    return {
        "must_have_matched": must_matched,
        "must_have_missing": must_missing,
        "nice_to_have_matched": nice_matched,
        "nice_to_have_missing": nice_missing,
        "must_have_pct": round(must_pct),
        "nice_to_have_pct": round(nice_pct),
        "weighted_score": weighted_score,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("resume", help="Path to tailored resume .docx")
    parser.add_argument("keywords", help="Path to keywords.json (must_have / nice_to_have arrays)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of a report")
    args = parser.parse_args()

    resume_path = Path(args.resume)
    keywords_path = Path(args.keywords)

    if not resume_path.exists():
        print(f"ERROR: {resume_path} not found", file=sys.stderr)
        sys.exit(1)
    if not keywords_path.exists():
        print(f"ERROR: {keywords_path} not found", file=sys.stderr)
        sys.exit(1)

    keywords = json.loads(keywords_path.read_text())
    text, doc = load_docx_text(resume_path)

    kw_result = check_keywords(text, keywords)
    format_issues, format_score = check_format(resume_path, doc)
    missing_sections, section_score = check_sections(text)

    # Composite: keyword match matters most for "will a recruiter's ATS surface this",
    # format compliance is a hard gate (bad format tanks even a perfect keyword match),
    # section structure is a smaller but real factor
    composite = round(kw_result["weighted_score"] * 0.55 + format_score * 0.30 + section_score * 0.15)

    result = {
        "composite_score": composite,
        "keyword_match": kw_result,
        "format": {"score": format_score, "issues": format_issues},
        "sections": {"score": section_score, "missing": missing_sections},
    }

    if args.json:
        print(json.dumps(result, indent=2))
        return

    print(f"\n{'='*60}")
    print(f"ATS SCORE REPORT — {resume_path.name}")
    print(f"{'='*60}")
    print(f"\nCOMPOSITE SCORE: {composite}/100\n")

    print(f"Keyword Match: {kw_result['weighted_score']}/100  (must-have {kw_result['must_have_pct']}%, nice-to-have {kw_result['nice_to_have_pct']}%)")
    if kw_result["must_have_missing"]:
        print(f"  MISSING must-have terms: {', '.join(kw_result['must_have_missing'])}")
    if kw_result["nice_to_have_missing"]:
        print(f"  Missing nice-to-have terms: {', '.join(kw_result['nice_to_have_missing'])}")

    print(f"\nFormat Compliance: {format_score}/100")
    for issue in format_issues:
        print(f"  - {issue}")
    if not format_issues:
        print("  No formatting issues detected.")

    print(f"\nSection Structure: {section_score}/100")
    if missing_sections:
        print(f"  Missing standard sections: {', '.join(missing_sections)}")
    else:
        print("  All standard sections present.")
    print()


if __name__ == "__main__":
    main()
