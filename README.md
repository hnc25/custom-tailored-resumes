# Custom Tailored Resumes — Claude Code Project

Generates ATS-optimized tailored resumes, plus visual resume + cover letter versions, from job descriptions, using your own core resume as the source of truth. This is a fully generic, bring-your-own-content pipeline — no example data or personal information ships with this repo.

## Setup (one-time)

1. Clone or unzip this project into a folder on your machine — this becomes its own Claude Code project.
2. Open a terminal in that folder and run `claude` to start Claude Code there.
3. Install the Python dependencies: `pip install python-docx pillow pymupdf --break-system-packages` (skip any already installed). `pymupdf` is only used to measure the Professional resume's page count; without it the script falls back to an estimate.
4. **Install Node.js (required).** Get Node.js 18 or newer (which includes npm) from [nodejs.org](https://nodejs.org), then run this once in the project folder:
   ```
   npm install
   ```
   This installs `docx` (docx-js), which renders the Professional cover letter. The pipeline won't produce all three outputs without it.
5. Supply your own content in `reference/` (none of this is included — you provide it):
   - **`reference/core-resume.docx`** (required) — your actual resume: every real job, title, date range, and metric. This is the single source of truth the pipeline will never contradict or fabricate beyond. Your name, contact info, education, and credentials for the Professional sidebar are also pulled from here.
   - **`reference/photo.jpg`** (required) — your headshot, used in the sidebar of the two Professional outputs. Portrait, head-and-shoulders, face roughly centered. It's auto-cropped to 5:6. This file is gitignored so it never gets committed.
   - **`reference/background-notes.md`** (optional but recommended) — an extended fact bank: named tools, certifications, compliance frameworks, board/leadership roles, and role-level detail that didn't make it into the core resume but are still real and usable for adjacent-skill matching. A LinkedIn profile export is a good source for this.
   - **`reference/style-examples/`** (optional but recommended) — up to two resumes you've already written (or like the tone/structure of) that represent the style you want tailored output to match. These are style references only — the pipeline pulls no new facts from them.

**Custom colors (optional):** the two Professional outputs default to a navy sidebar (`#1B2A49`) with muted gold accents (`#C9A24B`). To use your own colors, add a `colors` object to the content JSONs (`professional_<Company>.json` and `cover_professional_<Company>.json`), or ask Claude to include it when running `/tailor-resume`:
```json
"colors": { "sidebar": "#2F4F3A", "accent": "#D98C5F" }
```
- `sidebar` fills the sidebar band and colors main-column headings, company names, and bold text.
- `accent` colors sidebar headings, the resume's sidebar bullets, divider rules, and the thin edge stripe.

Values are 6-digit hex, with or without `#`. If you leave out `colors` or either key, the default is used. An invalid value (like `"green"` or `"#12345"`) prints a warning and falls back to the default, so the build doesn't fail. Sidebar text is white, so pick a dark sidebar color. Use the same colors in both files so the resume and cover letter match. The format is in `reference/professional_schema.json`.

**Keeping `background-notes.md` current:** if you supply one, its usefulness depends on staying current. If your background changes meaningfully (new role, new certs, new board positions), update the file — the tailoring pipeline is only as good as this file staying accurate.

## Usage

**Single JD:**
```
/tailor-resume
```
Claude Code will ask you to paste the job description if you don't pass it directly. Or pass it inline:
```
/tailor-resume <paste the full JD text here>
```

**Batch mode (multiple JDs at once):**
Drop each job description as its own `.txt` file into `jobs/` (e.g., `jobs/Acme_Director_PM.txt`, `jobs/Globex_VP_Product.txt`), then run:
```
/tailor-resume
```
with no arguments — the command will find and process every file in `jobs/` independently, one at a time, and give you one consolidated report at the end.

**Marking a JD as applied:** once you've submitted an application, move its `.txt` file from `jobs/` into `jobs/applied/` to keep the active batch queue clean. `jobs/applied/` is just an archive — nothing reads from it automatically.

## What comes out

For each JD processed, three files land in `output/`:
- **`Resume_<Company>_<Date>.docx`** — the ATS-optimized resume: single column, standard fonts, no tables/images. Scored by `ats_check.py`. **Upload this one to application portals.**
- **`Professional_<Company>_<Date>.docx`** — a visual two-column version of the same tailored resume: a navy sidebar with your photo, name, contact, core expertise, education, and certifications, plus the profile and experience in the main column. Expands to two pages automatically when needed.
- **`Professional_CoverLetter_<Company>_<Date>.docx`** — the tailored cover letter, in the same visual layout as the Professional resume. This is the only cover letter the pipeline produces. No separate plain version is saved.

The Professional resume reuses the exact tailored content from the ATS resume. Nothing is redrafted. The two Professional files are **not ATS-checked**, on purpose: photos, positioned frames, and multi-column layouts break ATS parsers. Use them where a human reads the document directly, such as networking, emailing a hiring manager, a portal's cover-letter upload, or bringing a printed copy to an interview.

Plus a summary in the chat covering:
- Role bucket classification (e.g., Product Management vs. Product Development framing) and why
- **Domain fit** — whether the JD's industry/domain is a direct match to your real background, or which adjacent domain was used to bridge the gap (the pipeline is instructed to never claim direct domain experience you don't have)
- **Credentials in summary** — what the JD says about education and certifications, whether you meet it, and whether a degree or certification was mentioned in the Executive Profile (and what capability it supports) or left out (and why)
- The final ATS composite score and keyword coverage
- Role fit from the evidence map, reported separately from the keyword score
- Open questions (things your sources don't say either way) and confirmed gaps, kept apart and surfaced honestly — the pipeline is instructed never to fabricate skills or experience to close a gap

**Cover letters never mention gaps.** Gap analysis appears only in the chat summary above, never in the cover letter. Where a real gap exists, the letter doesn't acknowledge it ("I don't have experience in X," "while I lack…," "to be candid…"). It leads with the closest real, transferable strength from your background instead, still without claiming anything your source files don't support.

## How the ATS score works

`scripts/ats_check.py` runs an objective, non-LLM check — the same categories a real ATS (Workday, Taleo, iCIMS, etc.) evaluates:

- **Keyword match (55% of score)** — must-have terms weighted higher than nice-to-have
- **Format compliance (30%)** — flags tables, text boxes, images, multi-column layouts, header/footer content, and non-standard fonts, all of which commonly break real ATS parsers
- **Section structure (15%)** — checks for standard, ATS-recognized section headers (Experience, Education, Skills, Summary)

You can run it manually any time on any resume:
```
python3 scripts/ats_check.py output/Resume_Acme_2026-09-06.docx keywords_Acme.json
```

**The score is keyword coverage, not role fit.** It counts whether a term appears in the text, whatever it means there. Pass `--map evidence_map_<Company>.json` and the report adds a separate **Role Fit** section from your evidence map: how many requirements are confirmed, supported, partial, open questions or confirmed gaps, and which matched keywords do not actually cover the requirement behind them.

**The revision loop:** a composite of 80 and must-have coverage of 90% are targets, not requirements. Below target, the pipeline adds a missing term only where your evidence supports the requirement behind it, re-checks up to 3 times, then stops and reports the score as it stands, explained by your confirmed gaps and open questions. It does not add unsupported claims to reach a score.

## How evidence is handled

The pipeline separates what you did from how it is worded, and it asks instead of guessing.

1. **Evidence map first.** Before drafting, each important JD requirement is mapped to your evidence in `evidence_map_<Company>.json` and put in one of five classes:
   - **confirmed activity**: your sources say it in these terms;
   - **supported paraphrase**: your sources record the activity in other words, and the JD term is standard wording for it;
   - **partial match**: your evidence covers part of the requirement, with the boundary written down;
   - **open question**: your sources say nothing either way;
   - **confirmed gap**: you have said you don't have it.

   A term missing from your resume is an open question, not a gap. Only your own statement makes a gap.
2. **Questions together.** Open questions that would change a claim are put to you in one message before anything is built.
3. **Answers are kept.** Your full answer is saved, dated, in `reference/background-notes.md`, and the rule it resolves is updated in `reference/evidence_rules.json`. A confirmation lifts only the restriction it actually resolves, and you are not asked the same thing for the next application.
4. **One definition, three documents.** `scripts/build_application.py` renders the ATS resume, the Professional resume and the cover letter from a single `application_<Company>.json`.
5. **QA gate.** `scripts/qa_check.py` blocks third-person voice, figures that are in neither source file, cover-letter gap admissions, confirmed gaps stated as experience, a confirmed term placed under the wrong employer, and links or claims you said must not be made.
6. **Final inspection.** After the last content change, every page of all three documents is rendered and looked at, and the text is read against the evidence map.

`reference/evidence_rules.example.json` shows the rules format, and `tests/fixtures/` holds a complete worked example. Both describe a fictional candidate.

**What the automated checks cannot tell you.** They are pattern and completeness checks. A complete evidence map does not establish that a quoted source really supports the claim built on it, or that the claim is correct. The gate does not detect every unsupported causal or ownership claim: one worded outside your recorded rules, or split across two sentences, passes. Each tool prints these limits when it runs. Read the final documents yourself before sending them.

## Your data stays yours

Your resume, notes, evidence rules, photo, style examples, job descriptions, keyword files, evidence maps, application definitions and outputs are all excluded by `.gitignore`. The repository itself contains only reusable logic, neutral instructions and the synthetic example. If you fork it, run the tests before you push:

```
python3 -m unittest discover -s tests
```

They exercise the workflow on the synthetic candidate and fail if candidate-owned files or real-looking contact details would be published. They read text files only, so check binary files yourself.

## Editing the tailoring logic

The full pipeline instructions live in `.claude/commands/tailor-resume.md` — edit that file directly if you want to change:
- How the role-bucket framing axis is defined (the default is Product Management vs. Product Development — swap this for whatever axis fits your own field)
- The evidence rules (currently: five evidence classes; a supported paraphrase of a recorded activity is allowed; a missing term is a question for you, not a gap; no fabrication)
- The revision loop targets (currently: up to 3 revisions toward a composite of 80 and must-have coverage of 90%, adding only supported terms)
- The domain-framing rule (currently: never claim direct experience in a domain you haven't worked in — bridge honestly via the closest true adjacent domain instead)
- The credentials-in-summary rule (currently: a degree or certification appears in the Executive Profile only when it materially strengthens your positioning for that specific role; meeting a JD requirement is assessed separately and does not by itself earn summary space; your Education and Certifications sections always stay complete)
- The cross-section repetition guardrail (currently: never reuse the same sentence or near-identical phrasing twice within one document)
- The cover-letter gap rule (currently: no gap/limitation language in the letter; gaps are reported only in the chat summary)

## Folder structure

```
custom-tailored-resumes/
├── .claude/commands/tailor-resume.md   ← the pipeline definition (slash command)
├── reference/
│   ├── core-resume.docx                ← YOU SUPPLY THIS — source of truth
│   ├── photo.jpg                       ← YOU SUPPLY THIS — headshot for the Professional outputs (gitignored)
│   ├── PUT_YOUR_PHOTO_HERE.md          ← placeholder note for photo.jpg
│   ├── background-notes.md             ← YOU SUPPLY THIS (optional) — extended facts for adjacent-skill matching
│   ├── style-examples/                 ← YOU SUPPLY THESE (optional) — up to two style-pattern resumes
│   ├── evidence_rules.json             ← YOURS (optional, gitignored) — what you have confirmed: gaps, scoped terms, limits
│   ├── evidence_rules.example.json     ← rules format, for a fictional candidate
│   ├── keywords_schema.json            ← format for the per-JD keyword extraction file
│   └── professional_schema.json        ← content format for the two Professional outputs
├── scripts/
│   ├── build_application.py            ← one application definition → all three documents, with the checks below
│   ├── evidence_map.py                 ← evidence-map check, open questions, evidence-rules consistency
│   ├── qa_check.py                     ← QA gate: voice, figures, evidence rules
│   ├── build_docx.py                   ← ATS resume builder
│   ├── preview_docx.py                 ← render every page to PNG for inspection
│   ├── ats_check.py                    ← objective ATS scoring, plus role fit with --map
│   ├── build_professional.py           ← Professional (two-column, photo) resume builder
│   ├── build_cover_letter_professional.py  ← Professional cover letter builder (calls the .js renderer)
│   └── build_cover_letter.js           ← docx-js renderer for the Professional cover letter
├── tests/                              ← regression tests and a complete synthetic example (tests/fixtures)
├── package.json                        ← Node dependency (docx); run `npm install` once
├── jobs/                               ← drop JD .txt files here for batch mode
│   └── applied/                        ← move a JD's .txt file here once you've applied
└── output/                             ← the three tailored documents land here
```

## Credit

Created by Horacio Carpio — [github.com/hnc25](https://github.com/hnc25)
