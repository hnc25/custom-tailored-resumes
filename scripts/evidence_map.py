#!/usr/bin/env python3
"""
evidence_map.py — Evidence review for one application, done BEFORE drafting, plus a
consistency check of the candidate's evidence rules.

An evidence map (evidence_map_<Company>.json, worked synthetic example: tests/fixtures/evidence_map_AcmeFreight.json)
has one row per important JD requirement:

    requirement      the requirement, in the JD's words
    importance       "must" or "nice"
    jd_meaning       what the JD means by it in context (not just the keyword)
    classification   one of:
        confirmed_activity    the candidate did this; the source says so in these terms
        supported_paraphrase  professional wording for a recorded activity that the source
                              describes in other words (the exact keyword need not be there)
        partial_match         a recorded activity covers part of the requirement
        open_question         the sources say nothing either way: ask the candidate
        confirmed_gap         the candidate confirmed they do not have this
    source           where the evidence is recorded (file and section)
    source_quote     words copied from the source (checked: must be present in the sources)
    activity         what the candidate actually did
    claim            the wording proposed for the deliverables
    boundary         what the evidence does not establish (required for partial_match)
    question         the question for the candidate (required for open_question)
    keywords         JD keywords this row covers
    keyword_only     keywords that may match the resume text in a different sense from the
                     requirement; they never count as substantive coverage
    reviewed_terms   undocumented rule terms this row grounds in the recorded activity
    gap_label        for confirmed_gap: the label of the confirmed entry in the rules file

Usage:
    python scripts/evidence_map.py evidence_map_<Company>.json [keywords_<Company>.json]
    python scripts/evidence_map.py evidence_map_<Company>.json --questions
    python scripts/evidence_map.py --store      # consistency of the evidence rules file
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from qa_check import BLOCKING, STATUSES, SUPPORTED_CLASSES, Gate, default_gate  # noqa: E402

CLASSES = SUPPORTED_CLASSES + ("open_question", "confirmed_gap")

LIMITS = (
    "Limits of this review: the map is checked for completeness and for source quotes that are really "
    "present in the sources. That does not establish that a quote supports the claim built on it, that "
    "the JD meaning was read correctly, or that the claim is factually right. Those are judgements for "
    "the candidate and the reviewer."
)


def _has(row, field):
    v = row.get(field)
    return bool(v.strip()) if isinstance(v, str) else bool(v)


def validate_map(emap, keywords=None, gate=None):
    """Return a list of error strings. Empty means the map is complete enough to draft from."""
    gate = gate or default_gate()
    errors = []
    rows = emap.get("rows", [])
    if not rows:
        return ["the evidence map has no rows: map each important JD requirement before drafting"]
    confirmed = {g["label"] for g in gate.gaps if gate.status(g) == "confirmed_gap"}
    by_label = {g["label"]: g for g in gate.gaps}
    for n, r in enumerate(rows, 1):
        tag = f"row {n} ({r.get('requirement', 'no requirement')[:50]})"
        cls = r.get("classification")
        for f in ("requirement", "jd_meaning"):
            if not _has(r, f):
                errors.append(f"{tag}: '{f}' is missing. State what the JD means by the requirement in context")
        if cls not in CLASSES:
            errors.append(f"{tag}: classification must be one of {', '.join(CLASSES)}")
            continue
        if cls in SUPPORTED_CLASSES:
            for f in ("source", "source_quote", "activity", "claim"):
                if not _has(r, f):
                    errors.append(f"{tag}: a {cls} needs '{f}'. An approved label does not replace the activity behind it")
            if _has(r, "source_quote") and not gate.quote_in_sources(r["source_quote"]):
                errors.append(f"{tag}: source_quote is not in the candidate's sources. Record the candidate's confirmation in the evidence store first, or reclassify as open_question")
            if cls == "partial_match" and not _has(r, "boundary"):
                errors.append(f"{tag}: a partial_match needs 'boundary' (what the evidence does not establish)")
        elif cls == "open_question":
            if not _has(r, "question"):
                errors.append(f"{tag}: an open_question needs the 'question' to ask the candidate")
            if _has(r, "claim"):
                errors.append(f"{tag}: an open_question cannot carry a claim. Nothing is claimed until the candidate answers")
        elif cls == "confirmed_gap":
            if _has(r, "claim"):
                errors.append(f"{tag}: a confirmed_gap cannot carry a claim")
            label = r.get("gap_label")
            if label and label in by_label and label not in confirmed:
                errors.append(f"{tag}: '{label}' has status '{gate.status(by_label[label])}' in the rules file, not confirmed_gap. Missing documentation is an open_question")
            elif not (label in confirmed or (_has(r, "source_quote") and gate.quote_in_sources(r["source_quote"]))):
                errors.append(f"{tag}: nothing shows the candidate confirmed this gap (no confirmed rules entry, no quote in the sources). Missing terminology or documentation is an open_question, not a gap")
    if keywords:
        mapped = {k.lower() for r in rows for k in r.get("keywords", []) + r.get("keyword_only", [])}
        for k in keywords.get("must_have", []):
            if k.lower() not in mapped:
                errors.append(f"must-have keyword '{k}' is not covered by any row: map the requirement it comes from")
    return errors


def open_questions(emap):
    return [(r["requirement"], r.get("question", "")) for r in emap.get("rows", []) if r.get("classification") == "open_question"]


def role_fit(emap):
    """Requirement-level fit, kept separate from keyword coverage."""
    out = {}
    for imp in ("must", "nice"):
        rows = [r for r in emap.get("rows", []) if r.get("importance", "must") == imp]
        out[imp] = {c: [r["requirement"] for r in rows if r.get("classification") == c] for c in CLASSES}
        out[imp]["total"] = len(rows)
    return out


def keyword_support(emap):
    """For each mapped keyword: 'supported', 'partial', 'keyword_only' or 'unsupported'."""
    rank = {"unsupported": 0, "keyword_only": 1, "partial": 2, "supported": 3}
    out = {}
    for r in emap.get("rows", []):
        cls = r.get("classification")
        level = "supported" if cls in ("confirmed_activity", "supported_paraphrase") else "partial" if cls == "partial_match" else "unsupported"
        for k, lv in [(k, level) for k in r.get("keywords", [])] + [(k, "keyword_only") for k in r.get("keyword_only", [])]:
            k = k.lower()
            if lv == "keyword_only" or k not in out or (out[k] != "keyword_only" and rank[lv] > rank[out[k]]):
                out[k] = lv
    return out


def render(emap):
    lines = [f"EVIDENCE MAP — {emap.get('company', '?')} — {emap.get('role', '')}".rstrip(" —"), ""]
    for r in emap.get("rows", []):
        lines.append(f"[{r.get('importance', 'must')}] {r.get('requirement', '')}")
        lines.append(f"    JD meaning: {r.get('jd_meaning', '')}")
        lines.append(f"    Class:      {r.get('classification', '')}")
        for label, f in (("Source", "source"), ("Activity", "activity"), ("Claim", "claim"), ("Boundary", "boundary"), ("Question", "question")):
            if _has(r, f):
                lines.append(f"    {label + ':':<11} {r[f]}")
        if r.get("keyword_only"):
            lines.append(f"    Keyword only (different meaning): {', '.join(r['keyword_only'])}")
    fit = role_fit(emap)
    lines.append("")
    for imp, name in (("must", "Must-have"), ("nice", "Nice-to-have")):
        f = fit[imp]
        if f["total"]:
            lines.append(f"{name} requirements: {f['total']} — confirmed {len(f['confirmed_activity'])}, supported paraphrase {len(f['supported_paraphrase'])}, "
                         f"partial {len(f['partial_match'])}, open questions {len(f['open_question'])}, confirmed gaps {len(f['confirmed_gap'])}")
    return "\n".join(lines)


def check_store(gate=None):
    """Consistency of the evidence rules file. Catches an old restriction that still blocks a term the
    candidate has since confirmed, and entries whose status is not backed by a recorded confirmation."""
    gate = gate or default_gate()
    errors = []
    if not gate.rules_path:
        return ["no evidence rules file found (reference/evidence_rules.json)"]
    for g in gate.gaps:
        label = g.get("label", "?")
        try:
            re.compile(g["claim"])
        except (re.error, KeyError) as e:
            errors.append(f"gap '{label}': bad or missing claim regex ({e})")
            continue
        status = g.get("status")
        if status not in STATUSES:
            errors.append(f"gap '{label}': status must be one of {', '.join(STATUSES)}")
        elif status in ("confirmed_gap", "knowledge_only"):
            for f in ("source", "confirmed_on"):
                if not _has(g, f):
                    errors.append(f"gap '{label}': a {status} needs '{f}' (who confirmed it, and when)")
            if status == "confirmed_gap" and not gate.quote_in_sources(g.get("source_quote")):
                errors.append(f"gap '{label}': a confirmed_gap needs a source_quote that is present in the sources")
        elif status == "undocumented" and _has(g, "confirmed_on"):
            errors.append(f"gap '{label}': an undocumented entry cannot have 'confirmed_on'")
    for t in gate.confirmed_terms:
        term = t.get("term", "?")
        for f in ("source", "confirmed_on"):
            if not _has(t, f):
                errors.append(f"confirmed term '{term}': needs '{f}'")
        if not gate.quote_in_sources(t.get("source_quote")):
            errors.append(f"confirmed term '{term}': source_quote is not present in the sources. Save the candidate's full answer in the notes first")
        for e in t.get("employers", []):
            if e not in gate.employers:
                errors.append(f"confirmed term '{term}': employer '{e}' is not in the 'employers' list")
        for g in gate.gaps:
            if gate.status(g) in BLOCKING + ("undocumented",) and re.search(g["claim"], term, re.I):
                errors.append(f"stale restriction: gap '{g['label']}' still blocks confirmed term '{term}'. Narrow the entry to what the confirmation did not resolve")
    for kind, items, fields in (("unlinked claim", gate.unlinked, ("a", "b")), ("boundary", gate.boundaries, ("claim",))):
        for u in items:
            for f in fields + ("source", "confirmed_on", "note"):
                if not _has(u, f):
                    errors.append(f"{kind} '{u.get('label', '?')}': needs '{f}'")
    return errors


def require(map_path, keywords=None, gate=None, questions_asked=False):
    """Used by the build runner. Stops the build when the map is missing or incomplete, or when open
    questions have not yet been put to the candidate."""
    p = Path(map_path)
    if not p.exists():
        sys.exit(f"Evidence map not found: {p}. Map the JD requirements to evidence before drafting (worked example: tests/fixtures/evidence_map_AcmeFreight.json).")
    emap = json.loads(p.read_text(encoding="utf-8"))
    errors = validate_map(emap, keywords, gate)
    if errors:
        sys.exit("Evidence map is incomplete:\n  - " + "\n  - ".join(errors) + f"\n\n{LIMITS}")
    qs = open_questions(emap)
    if qs and not questions_asked:
        sys.exit("Open questions for the candidate (ask them together, record the full answers, then rerun; "
                 "or pass --questions-asked to build with these left unclaimed):\n  - "
                 + "\n  - ".join(f"{req}: {q}" for req, q in qs))
    return emap


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    if args[0] == "--store":
        errs = check_store()
        print("Evidence rules: " + ("consistent" if not errs else f"{len(errs)} problem(s)"))
        for e in errs:
            print(f"  - {e}")
        print(f"\n{LIMITS}")
        sys.exit(1 if errs else 0)
    emap = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    if "--questions" in args:
        for req, q in open_questions(emap):
            print(f"- {req}: {q}")
        sys.exit(0)
    kw = json.loads(Path(args[1]).read_text(encoding="utf-8")) if len(args) > 1 else None
    print(render(emap))
    errs = validate_map(emap, kw)
    print("\nMap check: " + ("complete" if not errs else f"{len(errs)} problem(s)"))
    for e in errs:
        print(f"  - {e}")
    print(f"\n{LIMITS}")
    sys.exit(1 if errs else 0)
