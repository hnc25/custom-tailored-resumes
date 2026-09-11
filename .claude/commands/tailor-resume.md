---
description: Generate an ATS-optimized, tailored resume + cover letter from a pasted job description
---

# Tailor Resume & Cover Letter

You are producing a tailored resume and cover letter for the user for the job description provided in `$ARGUMENTS`. If no argument was given, check `jobs/` for `.txt`/`.md` files first:

- **No files in `jobs/`** → ask the user to paste the JD directly.
- **One or more files in `jobs/`** → this is a batch run. For EACH file found, execute steps 1 through 9 below yourself, in this same session, one JD at a time, in a loop. Do NOT invoke `/tailor-resume` again to process the next file — slash commands can only be typed by the user, not called by you as a sub-routine. You already have the full pipeline instructions below; just repeat them inline for each file until all are processed, then give one consolidated report at the end covering every JD.

## 0. Inputs you must read first

- `reference/core-resume.docx` — primary source of truth for all facts, dates, titles, metrics. **This file does not ship with this project — the user must supply their own.** If it's missing, stop and tell the user to add it before proceeding.
- `reference/background-notes.md` — secondary source of truth, an optional extended fact bank (e.g. pulled from a LinkedIn export) that the user can supply. Contains real facts (named tools, compliance frameworks, certifications, board/leadership roles, role-level detail) that don't appear in the core resume but are still real and usable for adjacent-skill matching in step 3. Never invent experience, skills, tools, or numbers that aren't grounded in EITHER of these two files. If this file doesn't exist, proceed using `reference/core-resume.docx` alone and note in your final report that no extended background notes were supplied.
- `reference/style-examples/` — the user's own APPROVED STYLE PATTERN resumes (up to two files, any format the `docx` skill can read). These are examples of tone, structure, and framing the user wants matched — not sources of new facts. If this folder is empty, tell the user in your final report that no style examples were supplied and that you defaulted to a straightforward professional format. When style examples exist, match their approach:
  - Headline/title line rewritten to match the target role
  - Executive profile paragraph rewritten in the target role's language
  - Competencies/Core Expertise section swapped to foreground JD-relevant terms
  - Per-employer bullets reworded to emphasize the metric/angle most relevant to this JD (same underlying facts, different framing — e.g., a throughput improvement can be framed as "scaling" for a growth-focused JD or "platform reliability" for an operations-focused JD)
  - Certifications and Technology sections reordered so the most JD-relevant items lead

**Dollar-figure / metric phrasing convention:** If the user's `background-notes.md` or `core-resume.docx` defines an authoritative phrasing convention for budget/spend figures (e.g., always phrase as "$XMM in spend", not "annual business value"), follow it consistently across the resume and cover letter. Do not alter the underlying numbers when tailoring — only the phrasing may be adapted to fit sentence flow. If the user has flagged specific figures as corrected/authoritative (superseding older phrasings), always use the corrected version, even if an older phrasing resurfaces from a prior draft or output file.

**Employment status and tense:** Use past tense for any role the user's source documents mark as ended, and present tense only for a role explicitly marked current/ongoing. Check `reference/core-resume.docx` (and `background-notes.md`, if supplied) for the authoritative employment dates and status before drafting any bullet.

## 1. Classify the role bucket

Read the JD's title and responsibilities section. Classify as one of:

- **Product Management** (Sr. Product Manager / Director / VP Product Management, or equivalent) → tailor using the strategy-forward framing seen in the style-example docs.
- **Product Development** → shift framing toward execution/delivery: roadmap-to-ship velocity, technical delivery, engineering partnership, release management, hands-on build cadence. Pull the same underlying facts from the core resume but foreground delivery-oriented framing over strategic/P&L framing.

If the JD is ambiguous between the two, default to Product Management framing but note the ambiguity in your summary at the end.

(This classification is illustrative of one common axis — Product Management vs. Product Development. If the user's background is in a different field entirely, replace this step's two buckets with whatever framing axis makes sense for their target roles, using the same logic: pick the framing that most closely matches the JD's emphasis.)

## 2. Extract keywords from the JD

Read the JD closely and produce a `keywords_<Company>.json` (must_have / nice_to_have) — see `reference/keywords_schema.json` for the format. Name it per-company (not a shared `keywords.json`) so a batch run never has one JD's file overwritten by the next before it's used. Must-have = explicitly required qualifications/skills stated in the JD ("required," "must have," or listed under a core requirements section). Nice-to-have = "preferred," "bonus," or implied-but-not-required skills.

## 3. Match keywords against the user's real background

For each keyword, check BOTH `reference/core-resume.docx` and `reference/background-notes.md` (if supplied). Matching rules:

- **Direct match**: term or a clear synonym appears in either source → use as-is.
- **Reasonable adjacent match**: the JD term is a plausible near-neighbor of something the user has actually done, in either source (e.g., JD says "stakeholder management," core resume says "cross-functional leadership"; or JD says "regulatory compliance," background-notes.md has named compliance frameworks) → this is allowed and should be reflected using the JD's terminology, since the underlying capability is real.
- **No match in either file**: do not fabricate. Note it in the gap summary instead of stretching the resume to claim it.

## 4. Domain framing (Executive Profile / summary)

This is separate from step 3 — step 3 matches individual skills/tools/keywords; this step governs how the **Executive Profile / summary section** handles industry/domain language specifically. It is a stricter version of the no-fabrication rule, applied to industry/domain claims:

- Identify the JD's specific industry/domain (e.g., EdTech, FinTech, PropTech, AdTech, healthcare).
- Check the user's real background (`reference/core-resume.docx` + `reference/background-notes.md`) for direct experience in that exact domain.
- **Direct domain experience exists** → name it normally in the Executive Profile, as usual.
- **Direct domain experience does NOT exist** → do not state or imply direct experience in that domain, in the Executive Profile or anywhere else. Instead, bridge via the closest genuinely-true adjacent domain or business model from the user's real background (e.g., consumer mobile products, subscription/freemium business models, data-driven engagement products, B2B SaaS at scale) — using only domains/models the user has actually worked in. Never state or imply industry expertise the user doesn't have, even loosely or in passing.

Carry the result of this step into step 9 (Report back) as the "Domain fit" line — required for every JD, every run.

## 5. Draft the tailored resume

Using `reference/core-resume.docx` as the base and any supplied `reference/style-examples/` docs as the style pattern, write a new tailored resume. Follow the `docx` skill (`/mnt/skills/public/docx/SKILL.md`) for creation mechanics — build with docx-js, US Letter page size, no tables/text boxes/multi-column layouts, no header/footer content, standard fonts only (Calibri, Arial, Georgia, or Cambria). This is a hard requirement — the ATS format check in step 7 will fail the resume otherwise.

**Avoid cross-section repetition:** Several JD-relevant points — comfort with ambiguity/fast-moving environments is a common recurring one, but the same risk applies to any other point (e.g., cross-functional influence, data-driven decision-making) that naturally fits the Executive Profile, a Key Results bullet, and a per-role bullet — legitimately belong in more than one section. When a point needs to appear more than once in the same document, vary the phrasing each time; never reuse the same sentence or near-identical wording twice within a single document. Before finalizing, scan the full draft for repeated multi-word phrases across the Executive Profile, Key Results, Core Competencies, and per-role bullets, and reword every repeat so each instance reads distinctly.

## 6. Draft the cover letter

Generate a fresh, professional cover letter (not reused from any fixed template) — proper business letter heading (the user's contact info, date, hiring company/manager if named in the JD, salutation), 3-4 paragraphs: opening hook tied to the specific role, 1-2 paragraphs connecting the user's real background to the JD's top priorities, closing with a call to action. Same docx formatting constraints as the resume. The domain-framing decision from step 4 applies here too — never claim or imply direct domain experience the Executive Profile doesn't claim.

## 7. Run the ATS check

```bash
python3 scripts/ats_check.py output/Resume_<Company>_<Date>.docx keywords_<Company>.json
```

If the composite score is below 80, or must-have keyword coverage is below 90%, revise the resume (reweave missing must-have terms into existing bullets/competencies where truthfully supportable) and re-run the check. Do not loop more than 3 times — if you can't close the gap without fabricating, stop and report the genuine gaps to the user instead.

## 8. Save outputs

Save to the flat `output/` folder using this naming convention:

- `output/Resume_<Company>_<YYYY-MM-DD>.docx`
- `output/CoverLetter_<Company>_<YYYY-MM-DD>.docx`

Use today's date and the company name extracted from the JD (sanitize for filesystem: no spaces → underscores, no special characters).

## 9. Report back

For each JD processed, summarize:
- Role bucket classification (and why)
- **Domain fit** — always include this line, every JD, every run: either "Direct domain match" (name the domain) or the adjacent domain/business model used to bridge the gap (per step 4). Never omit this line, even when the gap is small.
- Final ATS composite score + must-have/nice-to-have coverage
- Any genuine gaps (JD requirements with no real match in the user's background) — surfaced honestly, not papered over
- File paths of the two output documents
