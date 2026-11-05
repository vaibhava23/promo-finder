# Promo Finder: find the best 20–60 s promos in a microdrama screenplay

Kuku AI Generalist assignment, **Problem 1: Find the Promos**.

It reads a folder of timestamped screenplays (one `.txt` per episode) and returns ranked promo cuts. Each one
gives the episode and the start and end of every segment, the hook, the cliffhanger, one line on why it works,
the funnel stage, safety flags and alternate cuts. Cut points always land between lines and every promo is
20–60 s. That part is code, not AI, so it is always exactly right.

## Run it (2 minutes)
```bash
pip install -r requirements.txt
python run.py --input "path/to/show_folder" --out outputs/my_show
```
Open **`outputs/my_show/explorer.html`** in a browser: click any promo to see its script lines, hook zone, cliffhanger,
what's withheld after the cut, and scores. `review.html` is the editor's ✓/✗ sheet with CSV export. Other outputs:
`promos.json` (full detail), `promos.csv` (spreadsheet), `promos.md` (readable list).

Try it without the confidential pack on the included synthetic show:
```bash
python run.py --input tests/fixtures/mini_show --out outputs/mini_show_demo
```

## Swap the model (one line)
By default it runs **offline with no model**, using transparent rule-based scores. To add an LLM, edit
`config.yaml` or pass flags:
```bash
export GEMINI_API_KEY=...        # free key from https://aistudio.google.com/apikey
python run.py --input SHOW --out outputs/gemini --provider openai_compatible --preset gemini --model gemini-2.0-flash
```
Supported providers: any **OpenAI-compatible API** (presets: `gemini`, `groq`, `openrouter`, `ollama` for local,
`openai`; or `--base-url` for anything else, e.g. an API Kuku provides) and **Anthropic**. The LLM is used for two
things only. It tags every beat for hook, cliffhanger and how much context it needs (50 calls per show), and it
judges the shortlist (60 calls). Its scores are blended with the rule scores, never trusted alone. Replies are
cached, so re-runs are free.

## How it works
```
screenplays ─► 1 PARSE (code) ─► 2 SCORE BEATS (rules, + LLM if on) ─► 3 CANDIDATES (code) ─► 4 RANK ─► outputs
                timestamps,        hook / cliffhanger / intensity /       ~1,400 cuts, all valid    quality score,
                speakers,          context / safety per line, using       by construction:          diversity,
                tones, loglines    tone tags, reveal patterns, the        single, pruned 2-part,    LLM judge (opt.),
                                   episode logline, "cut right before     cross-episode             posting order
                                   the payoff", resolution penalties
```
- **Code**: parsing, timing, snapping cuts to line boundaries, 20–60 s, dedupe, overlap, outputs.
- **AI (optional)**: meaning. Is this line a reveal? Would a stranger follow it? Writing the "why".
- **Human**: an editor approves the shortlist in `review.html` (minutes, not watching 100 minutes of footage).

## Quality
See [`eval/RESULTS.md`](eval/RESULTS.md) and [`eval/audit.md`](eval/audit.md). In short: 40/40 outputs pass
the independent boundary and length check. A blind audit puts **8 of the top 10** past all three of the brief's
checks (hook in 3 s, unresolved ending, makes sense alone), and 20 of the top 30. Tuning was checked against
held-out episodes, and one tuning attempt was rejected for overfitting.

```bash
python tests/test_pipeline.py                                   # unit + end-to-end tests (incl. mock LLM)
python eval/run_eval.py "path/to/input_pack"                     # recall vs gold set, tune/test split
python eval/check_segments.py analysis/parsed.json eval/gold_promos.json
python eval/cost_estimate.py "path/to/input_pack"                # LLM call/token count per show
```

## Repo map
| Path | What |
|---|---|
| `run.py` | CLI + output writers (json/csv/md/html) |
| `config.yaml` | model/provider settings, posting-order weight |
| `promo/parse.py` | screenplay parser (robust to casing, O.S./V.O., CRLF, alias hints) |
| `promo/features.py` | beat-level scoring rules (all weights in one dict) |
| `promo/pipeline.py` | candidates, pruning, cross-episode, ranking, LLM tag/judge, explanations |
| `promo/llm.py` | provider adapter (OpenAI-compatible, Anthropic, mock), JSON extraction, cache |
| `eval/` | gold set, evaluator, tuning, ablations, audit, cost estimate, results |
| `analysis/ANALYSIS.md` | research and data analysis behind the design |
| `outputs/mini_show_demo/` | example outputs on the synthetic show (real-show raw outputs are shared separately because they quote Kuku's scripts) |
| `docs/solution.pdf` | the 2-page solution doc |

**Confidentiality:** the input pack is Kuku's content. It and the real-show outputs (which quote script lines)
are git-ignored. Regenerate them with the command above, or use the raw-outputs link in the submission.
