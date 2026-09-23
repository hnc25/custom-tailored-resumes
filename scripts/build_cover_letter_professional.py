#!/usr/bin/env python3
"""
build_cover_letter_professional.py — Build the visually-designed "Professional"
cover letter (navy photo sidebar + letter body), matching the Professional resume's
look. Third pipeline output and the only cover letter the pipeline saves. Like the
Professional resume, it is for human reading and is NOT ATS-checked.

Rendering is delegated to scripts/build_cover_letter.js (docx-js) because docx-js
handles a shaded full-height table sidebar more simply than python-docx for a
single-page document. This module is the content/orchestration layer:
  * validates the content JSON (the same identity fields build_professional.py
    requires: name, contact, education; plus optional credentials/certifications),
    so the two Professional documents stay visually consistent
  * crops reference/photo.jpg with the same helper build_professional.py uses
  * shells out to Node to render the .docx (requires `npm install` to have been run)

Nothing about the candidate is hardcoded. Identity and sidebar content come from the
content JSON, which the /tailor-resume pipeline fills in from reference/core-resume.docx
and reference/background-notes.md, and the letter paragraphs are the ones drafted in
/tailor-resume step 6.

Usage:
    python scripts/build_cover_letter_professional.py cover_professional_<Company>.json \
        output/Professional_CoverLetter_<Company>_<Date>.docx

Content JSON — required: name, contact, education, core_expertise, date, salutation, paragraphs.
Optional: credentials, certifications, recipient, closing (default "Sincerely,"),
closing_name (default: name). See reference/professional_schema.json.
"**bold**" markup is allowed inside paragraph/sidebar strings.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_professional import IDENTITY_FIELDS, PHOTO, _portrait_crop, validate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RENDERER = Path(__file__).resolve().parent / "build_cover_letter.js"

REQUIRED_FIELDS = IDENTITY_FIELDS + ("core_expertise", "date", "salutation", "paragraphs")


def build(content, out_path):
    validate(content, REQUIRED_FIELDS)
    c = {"credentials": "", "certifications": [], "closing": "Sincerely,",
         "closing_name": content["name"], **content}

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        photo_buf, (pw, ph) = _portrait_crop(PHOTO)
        photo_path = tmp / "photo.jpg"
        photo_path.write_bytes(photo_buf.read())
        c["photo"] = str(photo_path)
        c["photo_aspect"] = pw / ph

        content_path = tmp / "content.json"
        content_path.write_text(json.dumps(c, indent=2, ensure_ascii=False), encoding="utf-8")

        try:
            result = subprocess.run(
                ["node", str(RENDERER), str(content_path), str(out_path.resolve())],
                cwd=ROOT, capture_output=True, text=True,
            )
        except FileNotFoundError:
            raise RuntimeError("Node.js not found on PATH — install Node.js, then run `npm install` in the project root")
        if result.returncode != 0:
            sys.stderr.write(result.stderr)
            hint = " (did you run `npm install`?)" if "Cannot find module 'docx'" in result.stderr else ""
            raise RuntimeError(f"node build_cover_letter.js failed (exit {result.returncode}){hint}")

    return out_path


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    content = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    print(f"Saved {build(content, sys.argv[2])}")
