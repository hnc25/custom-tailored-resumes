# Custom Tailored Resumes — Claude Code Project

Generates ATS-optimized, tailored resumes + cover letters from job descriptions, using your own core resume as the source of truth. This is a fully generic, bring-your-own-content pipeline — no example data or personal information ships with this repo.

## Setup (one-time)

1. Clone or unzip this project into a folder on your machine — this becomes its own Claude Code project.
2. Open a terminal in that folder and run `claude` to start Claude Code there.
3. Confirm `python-docx` is available: `pip install python-docx --break-system-packages` (if not already installed).
4. Supply your own content in `reference/` (none of this is included — you provide it):
   - **`reference/core-resume.docx`** (required) — your actual resume: every real job, title, date range, and metric. This is the single source of truth the pipeline will never contradict or fabricate beyond.
   - **`reference/background-notes.md`** (optional but recommended) — an extended fact bank: named tools, certifications, compliance frameworks, board/leadership roles, and role-level detail that didn't make it into the core resume but are still real and usable for adjacent-skill matching. A LinkedIn profile export is a good source for this.
   - **`reference/style-examples/`** (optional but recommended) — up to two resumes you've already written (or like the tone/structure of) that represent the style you want tailored output to match. These are style references only — the pipeline pulls no new facts from them.

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

For each JD processed, two files land in `output/`:
- `Resume_<Company>_<Date>.docx`
- `CoverLetter_<Company>_<Date>.docx`

Plus a summary in the chat covering:
- Role bucket classification (e.g., Product Management vs. Product Development framing) and why
- **Domain fit** — whether the JD's industry/domain is a direct match to your real background, or which adjacent domain was used to bridge the gap (the pipeline is instructed to never claim direct domain experience you don't have)
- The final ATS composite score and keyword coverage
- Any real gaps between the JD's requirements and your actual background, surfaced honestly — the pipeline is instructed never to fabricate skills or experience to close a gap

## How the ATS score works

`scripts/ats_check.py` runs an objective, non-LLM check — the same categories a real ATS (Workday, Taleo, iCIMS, etc.) evaluates:

- **Keyword match (55% of score)** — must-have terms weighted higher than nice-to-have
- **Format compliance (30%)** — flags tables, text boxes, images, multi-column layouts, header/footer content, and non-standard fonts, all of which commonly break real ATS parsers
- **Section structure (15%)** — checks for standard, ATS-recognized section headers (Experience, Education, Skills, Summary)

You can run it manually any time on any resume:
```
python3 scripts/ats_check.py output/Resume_Acme_2026-09-06.docx keywords_Acme.json
```

**The revision loop:** if the composite score comes back below 80, or must-have keyword coverage is below 90%, the pipeline will automatically revise the resume (reweaving missing must-have terms into existing bullets/competencies where truthfully supportable) and re-check, up to 3 times. If it still can't close the gap without fabricating, it stops and reports the genuine gap to you instead of papering over it.

## Editing the tailoring logic

The full pipeline instructions live in `.claude/commands/tailor-resume.md` — edit that file directly if you want to change:
- How the role-bucket framing axis is defined (the default is Product Management vs. Product Development — swap this for whatever axis fits your own field)
- The keyword-matching strictness (currently: adjacent/reasonable inference allowed, no fabrication)
- The revision loop threshold (currently: revise up to 3 times if ATS composite score is below 80 or must-have coverage is below 90%)
- The domain-framing rule (currently: never claim direct experience in a domain you haven't worked in — bridge honestly via the closest true adjacent domain instead)
- The cross-section repetition guardrail (currently: never reuse the same sentence or near-identical phrasing twice within one document)

## Folder structure

```
custom-tailored-resumes/
├── .claude/commands/tailor-resume.md   ← the pipeline definition (slash command)
├── reference/
│   ├── core-resume.docx                ← YOU SUPPLY THIS — source of truth
│   ├── background-notes.md             ← YOU SUPPLY THIS (optional) — extended facts for adjacent-skill matching
│   ├── style-examples/                 ← YOU SUPPLY THESE (optional) — up to two style-pattern resumes
│   └── keywords_schema.json            ← format for the per-JD keyword extraction file
├── scripts/ats_check.py                ← objective ATS scoring
├── jobs/                               ← drop JD .txt files here for batch mode
│   └── applied/                        ← move a JD's .txt file here once you've applied
└── output/                             ← tailored resumes + cover letters land here
```

## Credit

Created by Horacio Carpio — [github.com/hnc25](https://github.com/hnc25)
