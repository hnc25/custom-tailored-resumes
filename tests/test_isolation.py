#!/usr/bin/env python3
"""
This repository ships reusable logic, neutral instructions and synthetic examples only.
These tests fail if candidate-owned files, or anything that looks like a real person's
contact details, would be published.

Limit: text files only. Binary files (docx, pdf, pptx, images) are not read, and a
paraphrase of someone's evidence cannot be recognised by a pattern. Review what you stage.
"""

import re
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CREDIT_LINE = re.compile(r"^(Copyright \(c\)|Created by) ")  # the author credit in LICENSE and README
CREDIT_FILES = ("LICENSE", "README.md")
BINARY = (".docx", ".pdf", ".pptx", ".jpg", ".jpeg", ".png", ".zip", ".ico")
CANDIDATE_OWNED = [
    "output/Resume_X_2025-01-01.docx", "jobs/x.txt", "jobs/applied/x.txt", "keywords_X.json", "professional_X.json",
    "cover_professional_X.json", "evidence_map_X.json", "application_X.json", "reference/background-notes.md",
    "reference/core-resume.docx", "reference/identity.json", "reference/evidence_rules.json", "reference/photo.jpg",
    "reference/style-examples/my-resume.docx",
]
# Reserved example values are fine: example.com / example.org addresses and 555-01xx numbers.
EMAIL = re.compile(r"[\w.+-]+@(?!example\.(com|org)\b)[\w-]+(\.[\w-]+)*\.[a-z]{2,}\b", re.I)
PHONE = re.compile(r"\b\d{3}[-.]\d{3}[-.]\d{4}\b")
SESSION_ID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)


def git(*args):
    return subprocess.run(["git", "-C", str(REPO), "-c", "core.quotepath=off", *args], capture_output=True, text=True, encoding="utf-8").stdout


def publishable():
    """Tracked files plus untracked files that .gitignore does not exclude."""
    return sorted(set(git("ls-files").splitlines() + git("ls-files", "--others", "--exclude-standard").splitlines()))


class Isolation(unittest.TestCase):
    def test_candidate_owned_paths_are_ignored(self):
        self.assertEqual(sorted(git("check-ignore", *CANDIDATE_OWNED).split()), sorted(CANDIDATE_OWNED))

    def test_placeholders_stay_tracked(self):
        for keep in ("jobs/.gitkeep", "jobs/applied/.gitkeep", "output/.gitkeep", "reference/style-examples/.gitkeep"):
            self.assertEqual(git("check-ignore", keep).strip(), "", keep)

    def test_no_contact_details_or_session_ids_in_text_files(self):
        hits = []
        for rel in publishable():
            if rel.lower().endswith(BINARY):
                continue
            try:
                lines = (REPO / rel).read_text(encoding="utf-8").splitlines()
            except (UnicodeDecodeError, FileNotFoundError):
                continue
            for n, line in enumerate(lines, 1):
                if rel in CREDIT_FILES and CREDIT_LINE.match(line):
                    continue
                hits += [(rel, n, kind) for kind, rx in (("email", EMAIL), ("phone", PHONE), ("session id", SESSION_ID)) if rx.search(line)]
        self.assertEqual(hits, [])

    def test_shipped_example_is_the_tested_synthetic_fixture(self):
        self.assertEqual((REPO / "reference" / "evidence_rules.example.json").read_text(encoding="utf-8"),
                         (REPO / "tests" / "fixtures" / "evidence_rules.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
