#!/usr/bin/env python3
"""
qa_check.py — Mandatory build-time QA gate for ALL tailor-resume outputs
(ATS resume, cover letter, Professional resume).

It runs before a file is accepted as a deliverable. A failure prints the offending
sentences and exits non-zero WITHOUT saving, so it cannot be skipped by forgetting a
step. There is deliberately no bypass flag.

Everything about the candidate comes from candidate-owned files, never from this script:
  the core resume and background notes (the evidence), and the evidence rules file
  (reference/evidence_rules.json, or the legacy name reference/known_gaps.json).

Checks (any hit is a BUILD ERROR):
  1. THIRD-PERSON VOICE   candidate pronouns never appear in candidate-facing text.
  2. EVIDENCE RULES       a line presents a pattern from the rules file as the candidate's
                          experience without negating or hedging it. What happens depends on
                          the entry's "status":
       confirmed_gap      the candidate confirmed the gap. Always an error.
       recorded_boundary  recorded as not done; blocks like a confirmed gap.
       knowledge_only     acquired knowledge / tool use. Passes only in a labelled knowledge
                          context (see _knowledge_context), fails anywhere else.
       undocumented       nothing in the sources either way. This is NOT a gap. It needs an
                          evidence review: it passes only when the application's evidence map
                          has a supported row naming the term, with a recorded activity and a
                          source quote that is actually present in the sources. Otherwise the
                          error is EVIDENCE REVIEW REQUIRED (ask the candidate, or ground it).
  3. EMPLOYER SCOPE       a confirmed term recorded for specific employers appears under, or in
                          a sentence naming only, a different employer.
  4. UNSUPPORTED LINK     one sentence joins two things the candidate has not confirmed are
                          connected (e.g. an analysis and a result figure).
  5. CONFIRMED BOUNDARY   a sentence asserts something the candidate said must not be claimed.
     UNANSWERED CLAIM     a sentence claims a keyword of a requirement the evidence map records as an
                          open question or a confirmed gap. Asking a question never authorises its claim.
  6. UNSOURCED FIGURES    a dollar figure, percentage, or "N+" count that is in neither source.
  7. COVER-LETTER GAP LANGUAGE  (cover letters only) a sentence admits a gap or limitation.

Standalone use (post-hoc scan of any existing file):
    python scripts/qa_check.py [--map evidence_map_<Company>.json] file.docx [more.docx ...]
"""

import json
import re
import sys
from pathlib import Path

import docx

ROOT = Path(__file__).resolve().parent.parent
RULES_CANDIDATES = ("reference/evidence_rules.json", "reference/known_gaps.json")
DEFAULT_CORE = "reference/core-resume.docx"
DEFAULT_NOTES = "reference/background-notes.md"
DEFAULT_PRONOUNS = ("he", "him", "his", "himself", "she", "her", "hers", "herself")

LIMITS = (
    "Limits of this gate: these are pattern checks against recorded rules. They do not verify that a "
    "cited source actually supports a claim, and they do not detect every unsupported causal, ownership "
    "or scope claim (for example one worded outside the recorded patterns, or split across sentences). "
    "A pass means no recorded rule was broken, not that every statement is supported. Read each "
    "deliverable against the evidence map before sending it."
)

BLOCKING = ("confirmed_gap", "recorded_boundary")
STATUSES = BLOCKING + ("knowledge_only", "undocumented")
SUPPORTED_CLASSES = ("confirmed_activity", "supported_paraphrase", "partial_match")

NEGATION = re.compile(r"\b(not|no|never|without|lack|lacks|lacking|don't|do not|didn't|did not|haven't|have not|hasn't|has not)\b|n't\b", re.I)
# A rule term only becomes an error when the sentence ASSERTS experience: an experience verb is present,
# and the sentence is not negated or hedged (would/need to/if/role/parallels...).
# Claim verbs are recognised by FORM rather than from an enumerated list, so "Defined / Used / Implemented ..."
# cannot slip through: any regular past-tense verb (-ed; "-eed" words such as need/speed are excluded),
# plus the closed set of irregular past forms common in resume bullets.
ASSERTS = re.compile(
    r"\b(have|had|has)\s+(worked|experience|led|built|owned|managed|delivered|shipped)|\bworked (with|on|in)\b|\bexperience (in|with|of)\b|\bexpertise (in|with)\b"
    r"|\b[a-z]{2,}(?<!e)ed\b"
    r"|\b(led|built|drove|ran|wrote|grew|cut|won|oversaw|rebuilt|made|took|brought|held|set|kept|taught|sold|spoke|gave|stood up|spun up)\b",
    re.I)
# A mention with no claim verb can still be a claim (see _is_claim): these recognise the remaining forms.
FIRST_PERSON = re.compile(r"\b(I|My|my|We|we|Our|our)\b")  # case-sensitive so "i.e." is not read as "I"
SENTENCE_END = re.compile(r"[.!?][\"')\]”’]*$")
DATE_LINE = re.compile(r"^\s*(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\s*$")
SALUTATION = re.compile(r"^\s*Dear\b")
# Acquired knowledge ("knowledge_only" entries) may appear only where it is explicitly presented as
# knowledge, never as employer experience (see _knowledge_context).
# The labels come from the rules file ("knowledge_labels" / "knowledge_phrases"); these are the defaults.
DEFAULT_KNOWLEDGE_LABELS = ("working knowledge", "AI working knowledge", "hands-on applied AI", "AI tools")
DEFAULT_KNOWLEDGE_PHRASES = ("working knowledge", "hands-on applied AI", "AI tools")
SECTION_HEADING = re.compile(
    r"^\W*(education|certifications?|licenses?|technology|technical skills|skills|core (competencies|expertise)|languages|"
    r"executive profile|professional summary|summary|profile|key results|professional experience|experience|contact)\W*$", re.I)
HEDGE = re.compile(r"\b(would|could|need to|needs to|if|require[sd]?|requirements?|role|position|open to|even though|parallels?|similar to|transfers?|interest|applying|non-negotiable|seeking|eager|learn)\b", re.I)
# Cover letters must never admit a gap/limitation — that analysis goes only in the report to the user.
GAP_ADMISSION = re.compile(
    r"\bI (do not|don't|did not|didn't|have not|haven't|have never|cannot|can't|lack|am not)\b"
    r"|\b(while|although|though) I (lack|don't|do not|haven't|have not)\b"
    r"|\bmy (experience|background|work)\b[^.]{0,60}\b(shorter|less|rather than|not)\b"
    r"|\bin the interest of candou?r\b|\bto be (candid|transparent|direct|straightforward|honest|clear)\b"
    r"|\bI (want|should|need) to be (candid|transparent|direct|straightforward|honest|clear)\b"
    r"|\b(if|whether) (that|this) (trade-?off|background)\b|\bfit\b[^.]{0,20}\bcandid\b",
    re.I)
FIGURE = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?\s?(?:MM|M|B|K)?|\d[\d,]*(?:\.\d+)?\s?%|\d[\d,]*\+")
DELIVERABLE_STEM = re.compile(r"^(?:Professional_CoverLetter|Professional|Resume)_(.+)_\d{4}-\d{2}-\d{2}$")

_ACTIVE_MAP = None  # set by use_evidence_map(); the application whose deliverables are being built


def _doc_text(d):
    """All human-visible text: body, tables, headers/footers (frames are body paragraphs)."""
    paras = [p.text for p in d.paragraphs]
    for t in d.tables:
        for row in t.rows:
            for cell in row.cells:
                paras.extend(p.text for p in cell.paragraphs)
    for s in d.sections:
        paras.extend(p.text for p in s.header.paragraphs)
        paras.extend(p.text for p in s.footer.paragraphs)
    return [p for p in paras if p.strip()]


def _sentences(paragraphs):
    for para in paragraphs:
        for s in re.split(r"(?<=[.!?])\s+|\n", para):
            if s.strip():
                yield s.strip()


def _norm(fig):
    return re.sub(r"\s+", "", fig).lower().rstrip("+")


def _flat(text):
    """Normalise text for quote lookup: markdown emphasis, curly quotes, dashes, whitespace, case."""
    text = text.replace("**", "").replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = re.sub(r"[–—]", "-", text)
    return re.sub(r"\s+", " ", text).strip().lower()


class Gate:
    """The candidate's sources and evidence rules, loaded from candidate-owned files under `root`."""

    def __init__(self, root=ROOT, rules_path=None):
        self.root = Path(root)
        if rules_path is None:
            rules_path = next((self.root / c for c in RULES_CANDIDATES if (self.root / c).exists()), None)
        self.rules_path = Path(rules_path) if rules_path else None
        self.rules = json.loads(self.rules_path.read_text(encoding="utf-8")) if self.rules_path else {}
        src = self.rules.get("sources", {})
        self.core = self.root / src.get("core", DEFAULT_CORE)
        self.notes = self.root / src.get("notes", DEFAULT_NOTES)
        self.gaps = self.rules.get("gaps", [])
        self.confirmed_terms = self.rules.get("confirmed_terms", [])
        self.unlinked = self.rules.get("unlinked_claims", [])
        self.boundaries = self.rules.get("boundaries", [])
        self.employers = self.rules.get("employers", [])
        pronouns = self.rules.get("candidate_pronouns", DEFAULT_PRONOUNS)
        self.third_person = re.compile(r"\b(" + "|".join(re.escape(p) for p in pronouns) + r")\b", re.I)
        labels = "|".join(re.escape(x) for x in self.rules.get("knowledge_labels", DEFAULT_KNOWLEDGE_LABELS))
        phrases = "|".join(re.escape(x) for x in self.rules.get("knowledge_phrases", DEFAULT_KNOWLEDGE_PHRASES))
        self.knowledge_line = re.compile(r"^\W*(" + labels + r")\b[^:]{0,40}:", re.I)
        self.knowledge_phrase = re.compile(r"\b(" + phrases + r")\b", re.I)
        self._source = None

    def source_text(self):
        if self._source is None:
            if not self.core.exists():
                sys.exit(f"QA gate: core resume not found at {self.core}. It is the primary evidence source; add it before building.")
            parts = [" ".join(_doc_text(docx.Document(str(self.core))))]
            if self.notes.exists():
                parts.append(self.notes.read_text(encoding="utf-8"))
            self._source = "\n".join(parts)
        return self._source

    def quote_in_sources(self, quote):
        q = _flat(quote or "")
        return len(q) >= 12 and q in _flat(self.source_text())

    def employers_in(self, text):
        return {e for e in self.employers if re.search(r"\b" + re.escape(e) + r"\b", text, re.I)}

    def status(self, entry):
        return entry.get("status") or ("knowledge_only" if entry.get("knowledge_ok") else "confirmed_gap")


_DEFAULT_GATE = None


def default_gate():
    global _DEFAULT_GATE
    if _DEFAULT_GATE is None:
        _DEFAULT_GATE = Gate()
    return _DEFAULT_GATE


def use_evidence_map(path):
    """Name the evidence map for the application being built (None clears it)."""
    global _ACTIVE_MAP
    _ACTIVE_MAP = load_map(path) if path else None


def load_map(path_or_map):
    if path_or_map is None or isinstance(path_or_map, dict):
        return path_or_map
    return json.loads(Path(path_or_map).read_text(encoding="utf-8"))


def map_for(out_path, root=ROOT):
    """The evidence map that belongs to a deliverable, found from its file name."""
    m = DELIVERABLE_STEM.match(Path(out_path).stem)
    p = Path(root) / f"evidence_map_{m.group(1)}.json" if m else None
    return load_map(p) if p and p.exists() else None


def _address_block(paragraphs):
    """Indexes of a letter's address block: the date line through the "Dear ..." line. Those lines name
    the employer and the role applied for, so a rule term there is not a candidate claim."""
    for i, p in enumerate(paragraphs):
        if DATE_LINE.match(p):
            for j in range(i, min(i + 8, len(paragraphs))):
                if SALUTATION.match(paragraphs[j]):
                    return set(range(i, j + 1))
    return set()


def _is_claim(s, letter, in_address):
    """Does a sentence that names a rule term present it as the candidate's own experience?"""
    if in_address or NEGATION.search(s) or HEDGE.search(s):
        return False
    if ASSERTS.search(s):
        return True
    if not letter:
        return True  # a resume has no lines about anyone else: skill lists, sidebar items, present tense
    return bool(FIRST_PERSON.search(s)) or not SENTENCE_END.search(s)


def _knowledge_context(s, letter, gate):
    """Is this an explicitly labelled knowledge context? A line that begins with a knowledge label
    ("AI Working Knowledge:", "Hands-on Applied AI:", "AI Tools:"), or, in a cover letter, a sentence that
    carries one of those phrases. Never when the line names an employer."""
    if gate.employers_in(s):
        return False
    return bool(gate.knowledge_line.match(s)) or (letter and bool(gate.knowledge_phrase.search(s)))


def _review_row(entry, s, emap, gate):
    """An undocumented term needs an evidence review, not a blanket rejection. Return the evidence-map
    row that grounds EVERY match of this entry in the sentence, or None. A row grounds a match when it
    is a supported class, records an activity, names the term in "reviewed_terms", and its source quote
    is really present in the candidate's sources. Whether the quote supports the claim is a human call."""
    rows = [r for r in (emap or {}).get("rows", [])
            if r.get("classification") in SUPPORTED_CLASSES and r.get("activity", "").strip()
            and gate.quote_in_sources(r.get("source_quote"))]
    found = None
    for m in re.finditer(entry["claim"], s, re.I):
        hit = m.group(0).lower()
        row = next((r for r in rows for t in r.get("reviewed_terms", [])
                    if re.search(entry["claim"], t, re.I) and (hit in t.lower() or t.lower() in hit)), None)
        if row is None:
            return None
        found = row
    return found


def _unanswered_keywords(emap):
    """Keywords of requirements the evidence map leaves as an open question or a confirmed gap, and
    that no supported row also covers. They may not be claimed, whether or not the question was asked.
    A row's "keyword_only" terms are not included: those may appear in their own, different sense."""
    rows = (emap or {}).get("rows", [])
    supported = {k.lower() for r in rows if r.get("classification") in SUPPORTED_CLASSES for k in r.get("keywords", [])}
    return {k: r for r in rows if r.get("classification") in ("open_question", "confirmed_gap")
            for k in r.get("keywords", []) if k.lower() not in supported}


def check_paragraphs(paragraphs, letter=False, gate=None, evidence_map=None, notices=None):
    """Return a list of (rule, sentence, detail) errors. `notices` (a list, optional) receives the
    undocumented terms that were allowed through on the strength of an evidence-map row."""
    gate = gate or default_gate()
    emap = load_map(evidence_map) if evidence_map is not None else _ACTIVE_MAP
    errors = []
    paragraphs = list(paragraphs)
    letter = letter or any(SALUTATION.match(p) for p in paragraphs)
    address = _address_block(paragraphs)
    src_figs = {_norm(m) for m in FIGURE.findall(gate.source_text())}
    # tolerate the "$150MM" == "$150M" spelling difference
    src_figs |= {f.replace("mm", "m") for f in src_figs}
    employer = None  # the employer block a resume line sits under
    unanswered = _unanswered_keywords(emap)

    for i, para in enumerate(paragraphs):
        if not letter:
            named = gate.employers_in(para)
            if named and len(para) <= 120 and (para.isupper() or not SENTENCE_END.search(para.strip())):
                employer = sorted(named)[0]
            elif SECTION_HEADING.match(para) or gate.knowledge_line.match(para):
                employer = None
        for s in _sentences([para]):
            claim = _is_claim(s, letter, i in address)
            m = gate.third_person.search(s)
            if m:
                errors.append(("THIRD-PERSON VOICE", s, f"'{m.group(0)}' — candidate-facing text must be first person (I/my/me) or pronoun-free"))
            for g in gate.gaps:
                if not (re.search(g["claim"], s, re.I) and claim):
                    continue
                status = gate.status(g)
                if status == "knowledge_only":
                    if not _knowledge_context(s, letter, gate):
                        errors.append(("KNOWLEDGE-ONLY TERM", s, f"presents '{g['label']}' as experience; it is acquired knowledge and may appear only in a labelled knowledge line: {g['note']}"))
                elif status == "undocumented":
                    row = _review_row(g, s, emap, gate)
                    if row is None:
                        errors.append(("EVIDENCE REVIEW REQUIRED", s, f"'{g['label']}' is undocumented in the sources (not a confirmed gap). Ground it in a recorded activity through a supported evidence-map row, or ask the candidate: {g['note']}"))
                    elif notices is not None:
                        notices.append((g["label"], s, f"allowed by evidence-map row '{row.get('requirement', '?')}' (source quote found in sources; whether it supports the claim was not checked automatically)"))
                else:
                    kind = "KNOWN-GAP CONTRADICTION" if status == "confirmed_gap" else "RECORDED BOUNDARY"
                    errors.append((kind, s, f"asserts '{g['label']}', a {status.replace('_', ' ')}: {g['note']}"))
            for kw, row in unanswered.items():
                if claim and re.search(r"(?<!\w)" + re.escape(kw) + r"(?!\w)", s, re.I):
                    kind = "an open question" if row.get("classification") == "open_question" else "a confirmed gap"
                    errors.append(("UNANSWERED CLAIM", s, f"'{kw}' belongs to requirement '{row.get('requirement', '?')}', which the evidence map records as {kind}. Asking the question does not authorise the claim: it stays out until the candidate's answer is recorded and the row is reclassified"))
            present = gate.employers_in(s) or ({employer} if employer else set())
            for t in gate.confirmed_terms:
                allowed = set(t.get("employers", []))
                rx = t.get("regex") or r"\b" + re.escape(t["term"]) + r"\b"
                if allowed and present and not (present & allowed) and re.search(rx, s, re.I):
                    errors.append(("EMPLOYER SCOPE", s, f"'{t['term']}' is recorded for {', '.join(sorted(allowed))} only, but this line is about {', '.join(sorted(present))}: {t.get('boundary', '')}"))
            for u in gate.unlinked:
                if re.search(u["a"], s, re.I) and re.search(u["b"], s, re.I):
                    errors.append(("UNSUPPORTED LINK", s, f"{u['label']}: {u['note']}"))
            for b in gate.boundaries:
                if re.search(b["claim"], s, re.I) and claim:
                    errors.append(("CONFIRMED BOUNDARY", s, f"{b['label']}: {b['note']}"))
            for f in FIGURE.findall(s):
                n = _norm(f)
                if n not in src_figs and n.replace("mm", "m") not in src_figs:
                    errors.append(("UNSOURCED FIGURE", s, f"'{f.strip()}' is not in the core resume or the background notes"))
    return errors


def check_cover_letter(paragraphs, gate=None, evidence_map=None, notices=None):
    """All standard checks plus the cover-letter-only ban on gap/limitation language."""
    errors = check_paragraphs(paragraphs, letter=True, gate=gate, evidence_map=evidence_map, notices=notices)
    for s in _sentences(paragraphs):
        m = GAP_ADMISSION.search(s)
        if m:
            errors.append(("COVER-LETTER GAP LANGUAGE", s, f"'{m.group(0)}' — cover letters never acknowledge gaps; lead with the closest transferable strength and put gap analysis in the report only"))
    return errors


def report(errors, label):
    print(f"\nQA BUILD ERROR — {label}: {len(errors)} problem(s). File NOT saved.\n", file=sys.stderr)
    for rule, sent, detail in errors:
        print(f"  [{rule}] {detail}\n    > {sent}\n", file=sys.stderr)
    print(f"  {LIMITS}\n", file=sys.stderr)


def report_notices(notices, label):
    for term, sent, detail in notices:
        print(f"QA NOTE — {label}: undocumented term '{term}' {detail}\n    > {sent}")


def enforce(d, out_path):
    """Called by every builder just before d.save(). Exits without saving on any error."""
    notices = []
    emap = _ACTIVE_MAP if _ACTIVE_MAP is not None else map_for(out_path)
    errors = check_paragraphs(_doc_text(d), evidence_map=emap, notices=notices)
    if errors:
        report(errors, str(out_path))
        sys.exit(1)
    report_notices(notices, str(out_path))


if __name__ == "__main__":
    args = sys.argv[1:]
    emap = None
    if "--map" in args:
        i = args.index("--map")
        emap = load_map(args[i + 1])
        del args[i:i + 2]
    if not args:
        sys.exit(__doc__)
    bad = 0
    for f in args:
        is_letter = re.search(r"CoverLetter|_CL\b", Path(f).stem, re.I)
        notices = []
        errs = (check_cover_letter if is_letter else check_paragraphs)(
            _doc_text(docx.Document(f)), evidence_map=emap if emap is not None else map_for(f), notices=notices)
        print(f"{'FAIL' if errs else 'PASS'}  {f}")
        report_notices(notices, f)
        if errs:
            bad += 1
            for rule, sent, detail in errs:
                print(f"   [{rule}] {detail}\n     > {sent}")
    print(f"\n{LIMITS}")
    sys.exit(1 if bad else 0)
