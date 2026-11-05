# Evaluation results

All numbers are from the offline (heuristic) mode on the full 50-episode pack. No LLM key was available during
the build, so LLM mode is tested end to end with a mock model (`tests/`) but **not yet measured for quality**.

## 1. What is measured
| Metric | How | Why |
|---|---|---|
| **Rule pass rate** | Independent checker (`eval/check_segments.py`) re-reads the parsed script: total 20–60 s, no dialogue line cut at any segment edge | The brief's hard constraints. Code guarantees them, and the check proves it |
| **Recall@K** | Share of the 24 hand-labelled gold promos (`eval/gold_promos.json`) the tool surfaces in its top K. Match = ≥50% shared seconds | "Does it find what an editor would pick?" |
| **Precision@K** | Share of the tool's top K that match *any* gold promo. A **lower bound**: gold is not exhaustive | |
| **Pool recall** | Is the gold promo anywhere among the ~1,400 generated candidates? | Separates *generation* failures from *ranking* failures |
| **Held-out split** | Gold promos from episodes 1–25 were used for tuning; **26–50 were never tuned on** | Catches overfitting to a small gold set |
| **Blind audit** | Every top-30 pick rated on the brief's three checks (hook in 3 s / unresolved end / standalone) | Gold can't see good picks it doesn't contain |

## 2. Final numbers
| | Value |
|---|---|
| Rule pass rate (30 promos + 10 variants) | **40/40** |
| Deterministic (two runs identical) | **yes** |
| Runtime, 50 episodes (4-core cloud container) | **~3 s** |
| Pool recall | **0.92** (22/24; misses: G05 two-cut frame-up, G24 romance clip with no cliffhanger) |
| Recall@10 / @20 / @30 (all gold) | **0.21 / 0.33 / 0.38** |
| Held-out (eps 26–50) Recall@30 | **0.27** (tuning split 0.46) |
| Precision@10 (lower bound) | **0.50** |
| **Blind audit, all three checks** | **20/30 (67%)**, top 10: **8/10** |
| Audit per check | hook 27/30 · cliffhanger 28/30 · standalone 24/30 |

## 3. Iteration log (what changed, what it did)
| Version | Change | R@30 all | tune / **test** | P@10 | Kept? |
|---|---|---|---|---|---|
| v0 | Tone + keywords + episode-end prior | 0.25 | 0.31 / **0.18** | 0.10 | — |
| v1 | Empty shouts ("Silence!") damped; identity-reveal patterns; **episode-logline salience** | 0.42 | 0.46 / **0.36** | 0.20 | ✅ biggest gain, generalised |
| v2 | Visual hooks weighted up (muted viewing); proper-noun list fixed | 0.33 | 0.31 / **0.36** | 0.30 | ✅ precision up |
| — | **Random weight search (150 trials) on tune split** | 0.42 | **0.54 / 0.27** | 0.30 | ❌ **overfit**: test fell; rejected |
| v3 | Rule-only cross-episode edits moved to a separate "variants" list | 0.42 | 0.46 / **0.36** | 0.30 | ✅ |
| v4 | One promo per hook moment (others become alternate cuts); posting order adds a funnel bonus | 0.38 | 0.46 / **0.27** | **0.50** | ✅ top-10 quality over raw recall |
| v5 | Endings that resolve (embrace, "Are you hurt?") penalised, even with a "cliffhanger" music cue; pruning may not drop logline-central setup | 0.38 | 0.46 / **0.27** | 0.50 | ✅ audit 57% → **67%** |

Reading this honestly: with 24 gold promos, one promo = 0.04–0.09 recall, so differences under ~0.1 are noise.
The audit is the more meaningful signal for top-of-list quality; the held-out split is the guard against
overfitting.

## 4. Ablations (v3 code, each feature removed in turn)
| Variant | R@30 all | tune | test |
|---|---|---|---|
| Full | 0.42 | 0.46 | 0.36 |
| − logline salience | 0.38 | 0.46 | 0.27 |
| − "cut right before the payoff" | 0.29 | 0.31 | 0.27 |
| − cliffhanger term (hook only) | 0.29 | 0.46 | **0.09** |
| − hook term (cliffhanger only) | 0.29 | 0.23 | 0.36 |
| − standalone term | 0.38 | 0.31 | 0.46 |

The hook and cliffhanger terms are both necessary. Standalone is noisy at this gold size: removing it helped the
test split and hurt the tuning split. I kept it because the brief requires it and the audit's main failures are standalone ones.

## 5. Where it picks badly (from the audit and the misses)
1. **Context-dependent clips** (6/30 fail standalone): names like Sterling, Ashwood, "the council" mean nothing to a stranger. Rules only catch names, not plot.
2. **Hooks that need meaning, not volume**: "Your Grace." said to a "beggar" is the show's central twist, but it scores low because it's quiet. Conversely "Mother." got in as a hook.
3. **Resolutions that look like climaxes**: E42's "This is my son… the rightful Duke!" is a payoff, not a cliffhanger.
4. **Two-segment edits** can still break the logic of a scene; flagged for an editor.
5. **Cross-episode edits**: only ~4/10 are usable without an LLM or editor check.
6. **Script ≠ screen**: we judge text. Performance, faces and music are invisible.
7. **Ad policy**: violence and sexual content are flagged, not removed (blood, branding iron, the E50 scene).

All of 1–3 are what the LLM layer (beat tagging + judge with a `context` score) is designed for; the hooks are
in place (`promo/pipeline.py: llm_tag, llm_judge`) and would be the first thing to measure with a key.

## 6. Cost & scale
- Offline mode: free, ~3 s per 50-episode show.
- LLM mode, measured by dry run with real prompts: **110 calls (50 tagging + 60 judging), ~113k input + ~35k output tokens per show**, roughly $0.03 on a Flash-class model and free within Gemini's free tier (~8 min at free-tier rate limits). Responses are cached, so re-runs cost nothing.
- 10 new shows a week means about 1,100 calls a week. The bottleneck is the editor's review (~5–10 min per show using `review.html`), not compute.
