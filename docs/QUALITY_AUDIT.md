# Quality audit: content correctness, accessibility and design

Every check below is a script in this repo and can be re-run.

## 1. Content correctness (`eval/verify_against_source.py`)
An independent checker re-reads Kuku's **original `.txt` files with its own minimal code** (it does not use
`promo/parse.py`), then checks every output.

| Check | Result |
|---|---|
| Segment start is a real timestamp in the script | **56/56** |
| Segment end is a real timestamp in the script | **56/56** |
| No dialogue line crosses a cut | **56/56** |
| Stated duration equals the sum of segments | **40/40** |
| Total length 20–60 s | **40/40** |
| Hook text appears verbatim in its episode | **40/40** |
| Cliffhanger text appears verbatim in its episode | **40/40** |
| Every line shown in the Explorer exists in the source | **511/511** |

**Label accuracy (manual review of all 30 descriptions).** It found and fixed four mislabels: "Because he is
*marrying* me", "*poisoning*", "*arrested*" and "*sold* my men" were called plain "shocking lines" instead of
reveals (the word list missed verb forms), and "Someone is coming" was called a threat instead of an
interruption. A kind gesture (a guard passing bread) was described to beginners as "physical and shocking", so
that wording became "something dramatic happens". These labels feed explanations only; ranking metrics were
identical before and after (Recall@30 0.38, P@10 0.50).

**Judgement quality** (from `eval/RESULTS.md`, `eval/audit.md`): top 10 all-three pass rate 8/10; held-out
validation; one tuning attempt rejected for overfitting. The rater also built the tool, so an independent
editor should re-rate.

## 2. Accessibility (axe-core 4.10, WCAG 2.0/2.1/2.2 A + AA + best practice)
| | Before | After |
|---|---|---|
| Light theme | 3 violation types (23 low-contrast elements, no `main` landmark, content outside landmarks) | **0 violations, 40 rules passed** |
| Dark theme | 3 violation types (white text on light accent 2.5:1, landmarks) | **0 violations, 40 rules passed** |

Fixes: darker green, red and muted tokens in light mode; dedicated "text on accent" tokens so dark-mode buttons
and tags use dark text (≥ 4.5:1); `<main>` landmark; skip link ("Skip to the list of clips"); the detail panel
no longer re-announces everything on change, and focus moves to the selected clip's title instead; the phone
preview is a labelled region; every control is a real `<button>`; visible focus ring; `prefers-reduced-motion`
respected. Keyboard order checked: skip link → "Start here" picks → filter tabs → clip list → player.
Not automated: screen-reader listening test and real-user testing. The page does show every subtitle as text
in the script panel, so the animated preview is never the only way to read the content.

## 3. Design references and what was applied
| Reference | Convention | Applied |
|---|---|---|
| OpusClip (AI clip ranking): [Virality Score help](https://help.opus.pro/docs/article/virality-score) | Ranked list, one score per clip from hook quality and flow; framed as "a guide, not a guarantee" | Ranked list; four plain-word grades (Strong/Good/OK/Weak) with one-line definitions instead of an opaque number |
| Descript (text-based editing): [editor interface](https://help.descript.com/hc/en-us/articles/37585546799757-The-editor-interface) | The transcript is the main editing surface, beside the media | Script panel beside a phone-shaped preview; the current line is highlighted during playback |
| Google PAIR, *People + AI Guidebook*: [Explainability + Trust](https://pair.withgoogle.com/chapter/People%20+%20AI%20Guidebook%20-%20Explainability%20+%20Trust.pdf) | Explain outputs, show confidence, state limitations and mistakes, offer multiple options | "Why this clip?" sentence; "How much to trust these picks" section; "Check before posting" warnings; alternate cuts |
| Vertical-ad practice (see `analysis/ANALYSIS.md`) | 3-second hook, cut before the payoff, vertical 9:16 | 9:16 preview, hook zone shown on the progress bar, "What happens next?" reveal at the cut |

## 4. Visual explainer
`docs/poster/promo_finder_poster.png` / `.pdf` (A4, 300 dpi), drawn from real pipeline data: all 50 episodes to
scale, every scored line as a tick, the chosen clips' start (amber) and stop (red) points, one clip magnified,
and the three headline results. Design rationale: `docs/poster/measured-suspense.md`.
