# Submission checklist (what's done, what you still need to do)

| Item | Status | Where |
|---|---|---|
| Solution doc (PDF, ≤ 2 pages) | ✅ built (fill in name/roll/branch/links, then rebuild with `python docs/build_pdf.py`) | `docs/solution.pdf` |
| Prototype | ✅ runnable repo with run steps | push this folder to GitHub (see below) |
| Raw outputs on the full input pack | ✅ unedited run | `deliverables/raw_outputs_full_input_pack.zip`: upload to Drive, "anyone with the link" |
| Walkthrough video (optional) | ⬜ record (script below) | Loom / unlisted YouTube / Drive |

## Push to GitHub
Create an empty repo on github.com (e.g. `promo-finder`), then run:
```bash
git remote add origin https://github.com/<you>/promo-finder.git
git push -u origin main
```
The repo excludes Kuku's scripts and the real-show outputs (`.gitignore`). `analysis/ANALYSIS.md`, `eval/audit.md`
and `eval/gold_promos.json` quote a few short lines. If you want zero script text in a public repo, delete those
three before pushing, or make the repo private and share the link.

## Before submitting, make it yours
The brief says the decisions must be yours and they'll be discussed in the interview. Read `docs/solution.pdf`,
`eval/RESULTS.md` and `eval/audit.md` and change anything you disagree with. Be ready to explain:
1. why cut points are code and never AI (the 9 clipped lines);
2. why the tuned weights were rejected (the held-out test split);
3. why the posting plan puts early episodes first (free episodes, no spoilers);
4. what the LLM would fix (context and quiet twists like "Your Grace.") and how you'd measure it;
5. how you'd know it works in production (editor acceptance, 3-second hook rate, CPI vs editor picks).

## Interview: run on a new show
```bash
python run.py --input "path/to/new_show" --out outputs/new_show
```
Open `outputs/new_show/review.html`. If they give you an API, add `--provider openai_compatible --base-url <their url> --model <name>`
(key in an env var named in `config.yaml`), or `--provider anthropic --model <name>`.

## 3-minute video script
- **0:00–0:20.** "Problem 1. Editors watch every episode to find promos; I built a tool that reads the screenplays and returns ranked, ready-to-cut promos in seconds."
- **0:20–0:50.** Run `python run.py ...` live; show it finish in ~3 s; open `review.html`.
- **0:50–1:40.** Walk through 2–3 promos (E12 "crawl, sister", E1 altar, E3 stranger): segments, hook, cliffhanger, why, flags, alternate cuts, posting plan.
- **1:40–2:20.** How it works: code does timestamps and 20–60 s rules; scores use tone tags, reveals, the episode logline, "cut before the payoff"; the LLM is one config line.
- **2:20–3:00.** Honest quality: 8/10 of the top 10 pass all three tests; it fails on context-heavy clips and quiet twists; the tuning I rejected for overfitting; next step is the LLM judge plus real ad metrics.
