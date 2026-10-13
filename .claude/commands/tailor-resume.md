---
description: Generate an ATS-optimized tailored resume, plus visual Professional resume + cover letter versions, from a pasted job description
---

# Tailor Resume & Cover Letter

You are producing three tailored documents for the user (a plain ATS-safe resume, a visual "Professional" resume, and a matching Professional cover letter) for the job description provided in `$ARGUMENTS`. If no argument was given, check `jobs/` for `.txt`/`.md` files first:

- **No files in `jobs/`** → ask the user to paste the JD directly.
- **One or more files in `jobs/`** → this is a batch run. For EACH file found, execute steps 1 through 9 below (including 3a, 3b and 8c) yourself, in this same session, one JD at a time, in a loop. Do NOT invoke `/tailor-resume` again to process the next file — slash commands can only be typed by the user, not called by you as a sub-routine. You already have the full pipeline instructions below; just repeat them inline for each file until all are processed, then give one consolidated report at the end covering every JD.

## 0. Inputs you must read first

- `reference/core-resume.docx` — primary source of truth for all facts, dates, titles, metrics. **This file does not ship with this project — the user must supply their own.** If it's missing, stop and tell the user to add it before proceeding.
- `reference/background-notes.md` — secondary source of truth, an optional extended fact bank (e.g. pulled from a LinkedIn export) that the user can supply. Contains real facts (named tools, compliance frameworks, certifications, board/leadership roles, role-level detail) that don't appear in the core resume but are still real and usable for adjacent-skill matching in step 3. Never invent experience, skills, tools, or numbers that aren't grounded in EITHER of these two files. If this file doesn't exist, proceed using `reference/core-resume.docx` alone and note in your final report that no extended background notes were supplied.
- `reference/evidence_rules.json` — optional, user-owned evidence rules (shape: `reference/evidence_rules.example.json`, which describes a fictional candidate). It records what the user has confirmed: gaps, knowledge-only terms, terms confirmed for specific employers, links and claims they said must not be made. If it doesn't exist, the QA gate still checks voice and figures; create it the first time the user confirms something worth keeping (step 3b).
- `reference/style-examples/` — the user's own APPROVED STYLE PATTERN resumes (up to two files, any format the `docx` skill can read). These are examples of tone, structure, and framing the user wants matched — not sources of new facts, and never evidence. If this folder is empty, tell the user in your final report that no style examples were supplied and that you defaulted to a straightforward professional format. When style examples exist, match their approach:
  - Headline/title line rewritten to match the target role
  - Executive profile paragraph rewritten in the target role's language
  - Competencies/Core Expertise section swapped to foreground JD-relevant terms
  - Per-employer bullets reworded to emphasize the metric/angle most relevant to this JD (same underlying facts, different framing — e.g., a throughput improvement can be framed as "scaling" for a growth-focused JD or "platform reliability" for an operations-focused JD)
  - Certifications and Technology sections reordered so the most JD-relevant items lead
- `reference/photo.jpg` — the user's headshot, used by the two Professional outputs in step 8b. **Required; does not ship with this project.** If it's missing, stop and tell the user to add it (see `reference/PUT_YOUR_PHOTO_HERE.md`) before proceeding.
- Node.js + `npm install` — the Professional cover letter renders via `scripts/build_cover_letter.js` (docx-js). If `node_modules/` doesn't exist in the project root, run `npm install` once before step 8b.

**Dollar-figure / metric phrasing convention:** If the user's `background-notes.md` or `core-resume.docx` defines an authoritative phrasing convention for budget/spend figures (e.g., always phrase as "$XMM in spend", not "annual business value"), follow it consistently across the resume and cover letter. Do not alter the underlying numbers when tailoring — only the phrasing may be adapted to fit sentence flow. If the user has flagged specific figures as corrected/authoritative (superseding older phrasings), always use the corrected version, even if an older phrasing resurfaces from a prior draft or output file.

**Employment status and tense:** Use past tense for any role the user's source documents mark as ended, and present tense only for a role explicitly marked current/ongoing. Check `reference/core-resume.docx` (and `background-notes.md`, if supplied) for the authoritative employment dates and status before drafting any bullet.

## 0a. Source precedence

When sources disagree, the higher one governs what may be claimed about the user:

1. **The user's current, confirmed statements**: what they say in this session, and dated "user-confirmed" entries in `reference/background-notes.md`. The most recent statement on a point wins.
2. `reference/core-resume.docx` and the rest of `reference/background-notes.md`.
3. `reference/evidence_rules.json`, which must agree with 1 and 2. It records them; it does not overrule them.
4. Earlier reports, earlier content files and old output files. These are never evidence. Neither are style examples or any reasoning framework.

**A clarification supersedes only the restriction it actually resolves.** When the user confirms one thing, lift exactly that: the same employer, the same activity, the same scope they stated. Everything they did not address stays as it was.

If an older note or rule conflicts with a newer statement, say so in the report, follow the newer statement, and propose the correction to the older item.

## 1. Classify the role bucket

Read the JD's title and responsibilities section. Classify as one of:

- **Product Management** (Sr. Product Manager / Director / VP Product Management, or equivalent) → tailor using the strategy-forward framing seen in the style-example docs.
- **Product Development** → shift framing toward execution/delivery: roadmap-to-ship velocity, technical delivery, engineering partnership, release management, hands-on build cadence. Pull the same underlying facts from the core resume but foreground delivery-oriented framing over strategic/P&L framing.

If the JD is ambiguous between the two, default to Product Management framing but note the ambiguity in your summary at the end.

(This classification is illustrative of one common axis — Product Management vs. Product Development. If the user's background is in a different field entirely, replace this step's two buckets with whatever framing axis makes sense for their target roles, using the same logic: pick the framing that most closely matches the JD's emphasis.)

## 2. Extract keywords from the JD

Read the JD closely and produce a `keywords_<Company>.json` (must_have / nice_to_have) — see `reference/keywords_schema.json` for the format. Name it per-company (not a shared `keywords.json`) so a batch run never has one JD's file overwritten by the next before it's used. Must-have = explicitly required qualifications/skills stated in the JD ("required," "must have," or listed under a core requirements section). Nice-to-have = "preferred," "bonus," or implied-but-not-required skills.

## 3. Classify the evidence for each requirement

Work from JD **requirements**, not from keywords. For each important requirement, first state what the JD means by it in context, then classify the evidence into exactly one of five classes:

| Class | Meaning | What may be written |
|---|---|---|
| **Confirmed activity** | The sources say the user did this, in these terms | The claim, in source wording |
| **Supported paraphrase** | The sources record the activity in other words; the JD term is standard professional wording for that same activity | The JD term, tied to the recorded activity, with the activity stated |
| **Partial match** | A recorded activity covers part of the requirement | Only the part that is recorded; the boundary is written down |
| **Open question** | The sources say nothing either way | Nothing, until the user answers |
| **Confirmed gap** | The user has said they do not have this | Nothing, ever. Report it |

Rules that follow from this:

- **Missing terminology does not establish missing experience.** If a term is not in the sources, look for the activity under other words before concluding anything. If the activity is there, it is a supported paraphrase. If nothing is there, it is an open question, not a gap. Only the user's own statement makes a confirmed gap.
- **Do not withhold a standard term by applying a narrower definition of your own** to the user's account. If the label might fit, ask whether it does.
- **Approval of a label does not replace the activity.** When the user approves a term, the claim still has to name what they did, and the activity has to be recorded with it.
- **A paraphrase preserves meaning.** It may not add a capability, a domain, a tool, an employer, a scope of ownership, or a causal link that the recorded activity does not contain. Those are new claims and need the user's confirmation.
- **Adjacent is not the same.** A near-neighbour of something the user has done is a partial match and must be written as what it actually is, with its boundary, not relabelled in the JD's words.
- **Knowledge is not experience.** Something the user has studied or used personally may appear only in a labelled knowledge line (for example "Working Knowledge: ..."), never in an employer bullet.

## 3a. Evidence map — complete it before drafting

Write `evidence_map_<Company>.json` (worked synthetic example: `tests/fixtures/evidence_map_AcmeFreight.json`; fields are documented at the top of `scripts/evidence_map.py`). One row per important requirement: every must-have, and the nice-to-haves that would change what gets written. Each row records the requirement, what the JD means by it, the class from step 3, the source, a quote from the source, the activity, the proposed claim, and the remaining boundary or question.

Keep it short enough to use every time: one line per field, about 10 to 20 rows. Group requirements that rest on the same evidence into one row.

**Read each requirement in context.** A keyword is not coverage when its meaning differs from the requirement: "pipeline" in a sales JD is not a data pipeline, and "experimentation" in a growth JD is not testing model versions. When a JD keyword could match the resume text in a different sense, list it under the row's `keyword_only`. It may still appear in the resume where it is true in its own sense, but it never counts as coverage of that requirement.

Check the map: `python3 scripts/evidence_map.py evidence_map_<Company>.json keywords_<Company>.json`. It verifies that every must-have keyword belongs to a row, that supported rows have a source, an activity and a claim, that each source quote is really present in the user's sources, that open questions carry no claim, and that nothing is called a confirmed gap without the user's confirmation.

**What that check does not establish:** that the quote supports the claim, that the JD meaning was read correctly, or that the claim is correct. Those remain judgement. Show the user the map (the script prints a one-screen review) so they can check them.

## 3b. Consolidated discovery — ask once, before drafting

Collect every open question from the map (`python3 scripts/evidence_map.py evidence_map_<Company>.json --questions`) and put the material ones to the user **together, in one message, before building anything.** A question is material when the answer would change a claim in the documents. Ask about the activity (what they did, where, with what, how often, what came of it), not just "do you have X?". In a batch run, ask the questions for all JDs at once.

When the user answers:

1. **Save the full answer** in `reference/background-notes.md`, in their words, with the date and what prompted it. Record the boundaries they state.
2. **Update the classifications and the rules in the same change**: the evidence-map rows, and `reference/evidence_rules.json` (narrow or reclassify the entry the answer resolves; add a `confirmed_terms` entry with its employer scope and source quote; add an `unlinked_claims` or `boundaries` entry for any limit they set).
3. Run `python3 scripts/evidence_map.py --store`. It fails if an old restriction still blocks a term the user has now confirmed, or if a confirmation is recorded without its source, date and saved quote.
4. Only then draft. If the user chooses not to answer a question now, leave it open: claim nothing, and list it in the report.

Never edit the notes or the rules on inference. Once recorded, a confirmation is available to every later application; do not ask the user to establish it again.

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

**One shared definition.** Define the application once and render all three documents from it, so they cannot drift apart. Write `application_<Company>.json` (worked synthetic example: `tests/fixtures/application_AcmeFreight.json`) holding the identity, headline, profile, competencies, experience bullets, certifications, keywords, and the cover letter, then run:

```bash
python3 scripts/build_application.py application_<Company>.json [--questions-asked] --preview <new_folder>
```

It requires the evidence map (step 3a), stops while open questions are unasked (step 3b), runs the QA gate on the content before rendering, calls the three builders, runs the ATS check with role fit, and renders every page into a new folder. The individual builder commands in steps 7 and 8b still work on their own.

**Choose evidence by role relevance.** For each role, lead with the evidence that answers this JD's most important requirements, taken from the evidence map.

**When the document is too long, cut in this order:** (1) shorten repetitive wording; (2) merge bullets that make the same point; (3) drop the competencies and bullets least relevant to this JD; (4) only last, remove a distinctive achievement, example or figure. Never drop a distinctive achievement to make room for a keyword. List every cut in the report.

**Avoid cross-section repetition:** Several JD-relevant points — comfort with ambiguity/fast-moving environments is a common recurring one, but the same risk applies to any other point (e.g., cross-functional influence, data-driven decision-making) that naturally fits the Executive Profile, a Key Results bullet, and a per-role bullet — legitimately belong in more than one section. When a point needs to appear more than once in the same document, vary the phrasing each time; never reuse the same sentence or near-identical wording twice within a single document. Before finalizing, scan the full draft for repeated multi-word phrases across the Executive Profile, Key Results, Core Competencies, and per-role bullets, and reword every repeat so each instance reads distinctly.

## 6. Draft the cover letter

Generate a fresh, professional cover letter (not reused from any fixed template) — proper business letter heading (the user's contact info, date, hiring company/manager if named in the JD, salutation), 3-4 paragraphs: opening hook tied to the specific role, 1-2 paragraphs connecting the user's real background to the JD's top priorities, closing with a call to action. This step drafts the letter **content** only (recipient, salutation, paragraphs, closing). It is not saved as its own plain `.docx` and is not ATS-checked. Step 8b renders it as the Professional cover letter. The domain-framing decision from step 4 applies here too — never claim or imply direct domain experience the Executive Profile doesn't claim.

**Strengths-forward only — never write gap language into the letter.** The letter must not contain any gap or limitation sentence: no "I don't have experience in X," "while I lack…," "I have not owned…," "to be candid about fit," "my experience is shorter than the N years listed," or a closing like "if that trade-off works for your team." When step 3 found a confirmed gap or left an open question:
- Say nothing about the gap itself. Do not name the missing skill, tool, domain, or years requirement in a negative or hedged way.
- Use that paragraph for the closest real, transferable experience from the user's source files, stated positively and confidently (e.g., for a missing domain, the adjacent domain or business model from step 4; for a missing tool, the real capability the tool serves).
- Never overcorrect into claiming the gap. The no-fabrication rule still applies, so the transferable strength must be true as written.
- The honest gap analysis goes into the step 9 report ONLY.

Before moving on, reread the drafted letter and remove any sentence that admits a gap or limitation.

## 7. Run the QA gate and the ATS check; report role fit separately

**QA gate.** `scripts/qa_check.py` checks every document before it counts as a deliverable (`build_application.py` runs it for you; to scan a saved file: `python3 scripts/qa_check.py <file.docx>`). It rejects third-person candidate pronouns, figures that are in neither source file, cover-letter gap admissions, and, from `reference/evidence_rules.json`: confirmed gaps asserted as experience, knowledge-only terms outside a labelled knowledge line, confirmed terms used under the wrong employer, sentences that join two things the user said must not be connected, and claims the user said must not be made. An entry with status `undocumented` is **not a gap**: it raises EVIDENCE REVIEW REQUIRED until the evidence map grounds the term in a recorded activity with a quote that is really in the sources, or the user answers the question.

When the gate fails, stop. Do not edit the gate, the rules or the source files to make it pass. Find the recorded activity and map it, or ask the user.

**Limits of the gate, which it prints on every run.** These are pattern checks against recorded rules. They do not verify that a cited source supports a claim, and they do not detect every unsupported causal, ownership or scope claim: one worded outside the recorded patterns, or split across two sentences, passes. A pass means no recorded rule was broken, not that every statement is supported. Step 8c is the check for that.

**ATS check.**

```bash
python3 scripts/ats_check.py output/Resume_<Company>_<Date>.docx keywords_<Company>.json --map evidence_map_<Company>.json
```

The report has two separate parts that answer different questions:

- **Keyword score** (composite, must-have and nice-to-have coverage): whether the terms appear in the text, whatever they mean there.
- **Role fit** (from the evidence map): how many requirements are confirmed, supported by paraphrase, partial, open, or confirmed gaps; the share of must-have keywords that are matched **and** backed by a supported requirement; and the matched keywords that are keyword-only or sit on an open question or gap.

Targets for the keyword score are a composite of 80 and must-have coverage of 90%. They are targets, not requirements. If the score is below target, add a missing term only where the evidence map has a confirmed activity or supported paraphrase behind it. Do not add a term that is keyword-only, an open question or a confirmed gap. Stop after at most 3 revisions and report the score as it stands, explained by its confirmed gaps and open questions. A lower score with every claim supported is the correct result.

**Credentials and the score are separate decisions:**

- Keep education and certification information accurately represented in its own resume sections.
- Evaluate a JD education or certification requirement accurately during the step 2–3 fit and keyword analysis: establish from the source files whether the user meets, exceeds, or falls short of it. When the JD explicitly requires a certification the user holds, list it clearly in the Certifications section and recognize the requirement as met. An unmet requirement is a confirmed shortfall for step 9, not something to reword around.
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

## 8c. Final validation — after the LAST content change

A rebuild invalidates every earlier check. After the final change to the content, and before reporting:

1. **Rebuild all three documents** from the one definition, so none is left on older content.
2. **Render every page of every document** into a new folder (`--preview <new_folder>`, or `python3 scripts/preview_docx.py <file.docx> <new_folder>`; needs LibreOffice or Microsoft Word) and look at each page: page count, sidebar band full height, nothing cut off. Do not delete or overwrite earlier previews or outputs.
3. **Read the documents against the evidence map**, sentence by sentence, for what the gate cannot see: every claim traces to a supported row and says no more than the recorded activity; no causal link the source does not state, including one made across two sentences; ownership matches the source (led, helped, contributed; who built it; who decided); each tool, method and figure sits under the employer it is recorded for; the three documents agree with each other.
4. **Check the scores last**, from the final ATS file.

If step 3 finds a problem, fix it and start this step again.

## 9. Report back

For each JD processed, summarize:
- Role bucket classification (and why)
- **Domain fit** — always include this line, every JD, every run: either "Direct domain match" (name the domain) or the adjacent domain/business model used to bridge the gap (per step 4). Never omit this line, even when the gap is small.
- **Credentials in summary** (step 4a) — always include this line: what the JD states about education and certifications (required, preferred, optional, not required, or not mentioned), whether the user meets, exceeds, or falls short of it, and the summary decision: either the credential included and the capability it supports, or that credentials were omitted from the summary and why.
- **Evidence review**: the evidence map summary (counts by class), each supported paraphrase with the activity it rests on, and each undocumented term the gate allowed on the strength of a map row
- **Keyword score**: final ATS composite + must-have/nice-to-have coverage, stated as keyword coverage, not as fit
- **Role fit**, separately: requirement counts by class, and any matched keywords that are keyword-only or sit on an open question or confirmed gap
- **Open questions** still unanswered, kept apart from confirmed gaps. Never report missing documentation as a gap
- **Confirmed gaps**, with what was written in their place. Explain a score below target by its confirmed gaps and open questions
- **Cuts** made for length, and any conflict found between older notes or rules and the user's current statements
- **Limits**: the gate and the map check are pattern and completeness checks; say what was verified by reading (step 8c) rather than by a script
- **Final-page inspection** (step 8c): the preview folder, and confirmation that every page was looked at after the last content change
- This report is the ONLY place gap language belongs; the cover letter never contains it. For each confirmed gap or open question, name the transferable strength the cover letter used in its place.
- File paths of all three output documents (ATS resume, Professional resume, Professional cover letter), noting that the two Professional files are not ATS-checked

## 10. Keep the user's data out of version control

Everything about the user is theirs and stays local: the core resume, background notes, evidence rules, identity, photo, style examples, job descriptions, keyword files, evidence maps, application definitions and outputs. `.gitignore` excludes all of them. This project ships only reusable logic, neutral instructions and a synthetic example (`tests/fixtures`). Never copy a real person's evidence, outputs, contact details or session identifiers into a tracked file. `python3 -m unittest discover -s tests` checks this for text files; it cannot read binary files or recognise a paraphrase, so read what you stage.

## 11. Optional reasoning frameworks

If the user has a separate reasoning framework or methodology library and asks you to use it, treat it as read-only help with how to reason (for example, how to read a requirement or structure a positioning argument). It is optional and nothing here depends on one. It never supplies facts about the user: nothing found in it may be cited as evidence in an evidence map, written into the notes or rules, or claimed in a document.
