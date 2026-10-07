---
description: Generate an ATS-optimized tailored resume, plus visual Professional resume + cover letter versions, from a pasted job description
---

# Tailor Resume & Cover Letter

You are producing three tailored documents for the user (a plain ATS-safe resume, a visual "Professional" resume, and a matching Professional cover letter) for the job description provided in `$ARGUMENTS`. If no argument was given, check `jobs/` for `.txt`/`.md` files first:

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
- `reference/photo.jpg` — the user's headshot, used by the two Professional outputs in step 8b. **Required; does not ship with this project.** If it's missing, stop and tell the user to add it (see `reference/PUT_YOUR_PHOTO_HERE.md`) before proceeding.
- Node.js + `npm install` — the Professional cover letter renders via `scripts/build_cover_letter.js` (docx-js). If `node_modules/` doesn't exist in the project root, run `npm install` once before step 8b.

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

## 4a. Credentials in the Executive Profile / summary

This step governs one decision: whether a degree or certification is mentioned in the **Executive Profile / summary** of the two resumes (ATS and Professional). It does not govern cover-letter content, and it never changes the Education or Certifications sections.

**Principle:** a degree or certification appears in the Executive Profile only when it materially adds value for this specific candidate and this specific target role. This applies to every credential of every level and type: bachelor's, master's, MBA, doctorate, professional certification, license, or any other. None of them belongs in the summary merely because the user has it.

Evaluate each credential against the JD and the user's source files:

- Does the JD require a degree or certification, prefer one, mention one as optional, or say nothing?
- Does the user meet, exceed, or fall short of what the JD states?
- Is the credential's field relevant to the role?
- Does it demonstrate meaningful domain knowledge, technical or business capability, breadth, or differentiation?
- Does mentioning it contribute something the user's experience does not already demonstrate more strongly?
- Would the limited summary space be better used for accomplishments, scope, leadership, or outcomes?

Decision rules:

- Never include a credential simply because the user has it.
- Never include a credential simply because the JD mentions education or certification.
- **Meeting a requirement and deserving summary space are not the same thing.** Meeting a minimum education requirement, or holding a certification the JD requires, does not by itself make the credential valuable summary content.
- **Preserve factual gaps.** If the user's credential is below what the JD requires (e.g., the JD requires a master's and the user holds a bachelor's), never frame the lower credential as though it satisfies the requirement. Report the shortfall as a genuine gap in step 9.
- If the JD says no degree is required, do not automatically suppress education. A relevant degree may still be included when it independently strengthens the positioning.
- If the JD states no education requirement at all, make the same value-based determination.
- Do not inventory multiple degrees or certifications in the summary.
- If a credential is included, connect it to the specific capability or differentiation it helps demonstrate for this role. Do not merely name it. Derive that connection from this JD and the user's real experience each time; do not reuse a fixed sentence across JDs.
- Institution names generally belong in the Education section, not the summary, unless there is an exceptional, defensible, role-specific reason.
- If no credential adds meaningful positioning value, omit credentials from the summary entirely.

The shape to avoid is a standalone list ("Holds a [degree] in [field], a [second degree], and [certification]."). The shape to use, when a credential earns its place, is a sentence in which it supports a capability the JD prioritizes ("[Capability the role needs], grounded in a [degree] in [relevant field]."). These are shapes, not wording to copy.

**Source files are facts, not a pattern.** The user's `reference/core-resume.docx` or style examples may themselves list credentials in the summary. Treat that as a source of facts about what the user holds, not as phrasing to carry into the tailored profile.

Whatever this step decides, Education and Certifications stay complete and accurate in their own sections of both resumes. Carry the decision into step 9 as the "Credentials in summary" line.

## 5. Draft the tailored resume

Using `reference/core-resume.docx` as the base and any supplied `reference/style-examples/` docs as the style pattern, write a new tailored resume. Follow the `docx` skill (`/mnt/skills/public/docx/SKILL.md`) for creation mechanics — build with docx-js, US Letter page size, no tables/text boxes/multi-column layouts, no header/footer content, standard fonts only (Calibri, Arial, Georgia, or Cambria). This is a hard requirement — the ATS format check in step 7 will fail the resume otherwise.

**Avoid cross-section repetition:** Several JD-relevant points — comfort with ambiguity/fast-moving environments is a common recurring one, but the same risk applies to any other point (e.g., cross-functional influence, data-driven decision-making) that naturally fits the Executive Profile, a Key Results bullet, and a per-role bullet — legitimately belong in more than one section. When a point needs to appear more than once in the same document, vary the phrasing each time; never reuse the same sentence or near-identical wording twice within a single document. Before finalizing, scan the full draft for repeated multi-word phrases across the Executive Profile, Key Results, Core Competencies, and per-role bullets, and reword every repeat so each instance reads distinctly.

## 6. Draft the cover letter

Generate a fresh, professional cover letter (not reused from any fixed template) — proper business letter heading (the user's contact info, date, hiring company/manager if named in the JD, salutation), 3-4 paragraphs: opening hook tied to the specific role, 1-2 paragraphs connecting the user's real background to the JD's top priorities, closing with a call to action. This step drafts the letter **content** only (recipient, salutation, paragraphs, closing). It is not saved as its own plain `.docx` and is not ATS-checked. Step 8b renders it as the Professional cover letter. The domain-framing decision from step 4 applies here too — never claim or imply direct domain experience the Executive Profile doesn't claim.

**Strengths-forward only — never write gap language into the letter.** The letter must not contain any gap or limitation sentence: no "I don't have experience in X," "while I lack…," "I have not owned…," "to be candid about fit," "my experience is shorter than the N years listed," or a closing like "if that trade-off works for your team." When step 3 found a genuine gap:
- Say nothing about the gap itself. Do not name the missing skill, tool, domain, or years requirement in a negative or hedged way.
- Use that paragraph for the closest real, transferable experience from the user's source files, stated positively and confidently (e.g., for a missing domain, the adjacent domain or business model from step 4; for a missing tool, the real capability the tool serves).
- Never overcorrect into claiming the gap. The no-fabrication rule still applies, so the transferable strength must be true as written.
- The honest gap analysis goes into the step 9 report ONLY.

Before moving on, reread the drafted letter and remove any sentence that admits a gap or limitation.

## 7. Run the ATS check

```bash
python3 scripts/ats_check.py output/Resume_<Company>_<Date>.docx keywords_<Company>.json
```

If the composite score is below 80, or must-have keyword coverage is below 90%, revise the resume (reweave missing must-have terms into existing bullets/competencies where truthfully supportable) and re-run the check. Do not loop more than 3 times — if you can't close the gap without fabricating, stop and report the genuine gaps to the user instead.

**Credentials and the score are separate decisions:**

- Keep education and certification information accurately represented in its own resume sections.
- Evaluate a JD education or certification requirement accurately during the step 2–3 fit and keyword analysis: establish from the source files whether the user meets, exceeds, or falls short of it. When the JD explicitly requires a certification the user holds, list it clearly in the Certifications section and recognize the requirement as met. An unmet requirement is a genuine gap for step 9, not something to reword around.
- Do not insert a degree or certification into the Executive Profile solely to increase keyword coverage or the ATS score.
- Whether a credential belongs in the Executive Profile is decided independently, in step 4a, by whether it materially strengthens the user's positioning for this specific role.

## 8. Save outputs

Save to the flat `output/` folder using this naming convention (all three are required, every JD):

- `output/Resume_<Company>_<YYYY-MM-DD>.docx`
- `output/Professional_<Company>_<YYYY-MM-DD>.docx`
- `output/Professional_CoverLetter_<Company>_<YYYY-MM-DD>.docx`

Use today's date and the company name extracted from the JD (sanitize for filesystem: no spaces → underscores, no special characters).

## 8b. Build the Professional (visual) versions

After the ATS resume has passed (or exhausted) the step 7 loop, build the two visual "Professional" documents: a two-column layout with a navy photo sidebar. **Do not redraft anything.** Both reuse the final, already-tailored content from steps 5–7:

- **Identity/sidebar fields** (`name`, `credentials`, `contact`, `education`, `certifications`): pull these from `reference/core-resume.docx` (and `reference/background-notes.md` for certifications, if supplied). Use exactly what the user's source files say. Never invent or embellish. Omit `credentials`/`certifications` if the user has none; the scripts drop those sidebar sections when they're empty. These fields stay complete regardless of the step 4a decision: leaving a credential out of the Executive Profile never removes it from the sidebar or from the Education and Certifications sections.
- **Professional resume content** (`headline`, `tagline`, `profile`, `core_expertise`, `experience`): copy the final headline, Executive Profile, Core Competencies, and per-role bullets from the ATS resume as finalized in step 7. If there are more than ~12 competencies, keep the most JD-relevant ~12 for the sidebar. `**bold**` markup may highlight metrics.
- **Professional cover letter content** (`date`, `recipient`, `salutation`, `paragraphs`, `closing`): copy verbatim from the step 6 cover letter draft. Use the same `core_expertise` list as the Professional resume.

Write the content to `professional_<Company>.json` and `cover_professional_<Company>.json` in the project root (format: `reference/professional_schema.json`), then run:

```bash
python3 scripts/build_professional.py professional_<Company>.json output/Professional_<Company>_<Date>.docx
python3 scripts/build_cover_letter_professional.py cover_professional_<Company>.json output/Professional_CoverLetter_<Company>_<Date>.docx
```

**These two files are NOT ATS-checked. Never run them through `ats_check.py`.** They intentionally use images, positioned frames, header-anchored background bands, and a table layout, all of which break ATS parsers. They are for human readers: networking, direct email to a hiring manager, in-person handoffs, and any portal cover-letter upload field. The ATS resume remains the resume to upload to application portals. The no-fabrication, domain-framing, and repetition rules already applied to the source content carry over unchanged.

If either script fails, fix the content JSON (a missing required field is the usual cause) and re-run. Don't skip the output.

## 9. Report back

For each JD processed, summarize:
- Role bucket classification (and why)
- **Domain fit** — always include this line, every JD, every run: either "Direct domain match" (name the domain) or the adjacent domain/business model used to bridge the gap (per step 4). Never omit this line, even when the gap is small.
- **Credentials in summary** (step 4a) — always include this line: what the JD states about education and certifications (required, preferred, optional, not required, or not mentioned), whether the user meets, exceeds, or falls short of it, and the summary decision: either the credential included and the capability it supports, or that credentials were omitted from the summary and why.
- Final ATS composite score + must-have/nice-to-have coverage
- Any genuine gaps (JD requirements with no real match in the user's background) — surfaced honestly, not papered over. This report is the ONLY place gap language belongs; the cover letter never contains it. For each gap, name the transferable strength the cover letter used in its place.
- File paths of all three output documents (ATS resume, Professional resume, Professional cover letter), noting that the two Professional files are not ATS-checked
