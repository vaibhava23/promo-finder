# Kuku Assignment — Problem 1 (Find the Promos): Full Analysis

*Show analysed: "I Married a Broken Soldier. He was a Duke", episodes 1–50. Input pack is confidential and must not be published.*

---

## 1. What the brief actually demands (requirements checklist)

| # | Requirement (from brief) | Implication for the build |
|---|---|---|
| R1 | Promo = **20–60 s** clip from the show | Hard rule, enforce in code |
| R2 | Usually one continuous stretch, **may join several moments, same or different episodes** | Support multi-segment promos |
| R3 | **Hook in first 3 s** (slap, reveal, shocking line) | Score the *first 3 s window* specifically, not the clip in general |
| R4 | **Ends on a cliffhanger**, cut at an unresolved moment | Score the *final beat*; cut *before* resolution |
| R5 | **Makes sense on its own** to a stranger | Needs show context (loglines) to judge; penalise unexplained names |
| R6 | Output per promo: **episode + start/end of every segment in order, hook, cliffhanger, one line why** | Fixed JSON/CSV schema |
| R7 | **Rank** them; say which to post first and why | Ranking step + rationale |
| R8 | **Check quality**: where does the tool pick badly? | Eval set + honest failure list |
| R9 | **Re-runnable on a new show** in the interview; **model easy to swap** | CLI + config-driven model provider |
| R10 | Free tiers only | Gemini free / Groq / local Ollama; cheap token budget |
| R11 | Raw outputs on **full input pack**, unedited | Run all 50 eps, save as-is |
| R12 | Doc ≤ 2 pages: choice, assumptions, how it works, scale, quality & failures, AI tools used + one place AI got it wrong | Keep notes throughout |
| R13 | Grading: framing, approach & scale (AI vs rules vs human, cost), quality checking, prototype, communication | Every design choice must be justifiable on these five |

---

## 2. What the industry research says (what a "good promo" really is)

Sources are mostly practitioner/vendor material; hard ad-performance data is private. Treat as heuristics.

1. **Open on conflict, not context.** First 3 s should be a confrontation, betrayal or shocking line — never a logo or slow setup. ([Growthtrait](https://www.growthtrait.com/en/blog/short-drama-ads), [Palai](https://palai.media/en/articles/iak-pratsiuie-format-short-drama))
2. **Cut at peak unresolved tension — earlier than feels safe.** Editors' "comfortable" cut is typically 2–4 s too late; cut at the *setup for* the completion, not the completion. ([AxisAI – trailers](https://www.axisaistudios.com/blog/what-makes-a-vertical-drama-trailer-convert-in-2026), [AxisAI – pacing](https://www.axisaistudios.com/blog/editing-vertical-dramas-pacing-and-cut-rhythm))
3. **Stakes must land fast** — if emotional stakes aren't clear by ~second 8 the trailer is too slow for paid acquisition. (AxisAI)
4. **Works without sound** — overplayed performance so the plot reads muted (Palai). → Prefer hooks that are *visual* (strike, kneel, explosion) or carry on-screen reaction, not only dialogue.
5. **Proven tropes need no explanation**: revenge, hidden wealth/identity, mistaken identity, romance. This show *is* the "hidden Duke husband" trope — the title itself sells it. ([Insightrackr](https://blog.insightrackr.com/en/docs/May25TopShortDrama), Palai)
6. **Platforms scale one precise hook**, not a genre: one DramaBox hook took 75.5% of its US Top-10 ads. ([AdMapix](https://www.admapix.com/blog/ad-intelligence/dramabox-ad-strategy-2026)) → Rank should favour the *single sharpest premise hook*, and produce **variants** of it.
7. **Creative fatigue is fast**; apps run thousands of variants/month ([Naavik](https://naavik.co/digest/the-microdrama-volume-vs-value-paradox/), [Liftoff](https://liftoff.ai/?p=35846)) → a tool that yields *many* good candidates per show is valuable, not just a top 3.
8. **Funnel logic**: first ~10–15 episodes are free; paywall after ([eMarketer](https://www.emarketer.com/content/faq-on-microdramas--mobile-video-format-outpacing-netflix-daily-engagement)). A promo from the early free episodes sends a new viewer straight to content they can watch now.
9. **Length**: TikTok's Creative Center sweet spot for in-feed ads is ~21–34 s ([AdManage](https://admanage.ai/blog/tiktok-ad-specs)); Reels tolerate 45–60 s. → Within 20–60 s, *prefer ~25–45 s*.
10. **Academic precedent — HIVE (EMNLP 2025 Industry)** ([arXiv 2507.02790](https://arxiv.org/abs/2507.02790)): short-drama → ad-clip editing split into **(a) highlight detection, (b) opening/ending selection, (c) pruning**, with LLM scoring by genre/audience rules. Ablation: **opening/ending selection mattered most for ad metrics**. This validates scoring the *first 3 s* and *last beat* separately from the middle.
11. **LLM-as-judge reliability**: single-run scores are noisy; pairwise flips ~14% of the time; use explicit rubrics, multiple trials, position-swapping, and validate against human labels. ([arXiv 2606.13685](https://arxiv.org/pdf/2606.13685), [arXiv 2602.02219](https://arxiv.org/abs/2602.02219v1))

---

## 3. What the data actually looks like (minute analysis)

### 3.1 Structure
- 50 episodes, **102.7 min** total; episodes 70–201 s (mean 123 s); 1–8 scenes each.
- **3,727 timestamped blocks**: 1,754 CAMERA · 1,487 DIALOGUE · 372 ACTION · 114 SOUND FX. Parser recovers 100% (verified against raw `Start:` count).
- Every dialogue line has **speaker + emotion tag** (e.g. `Outraged, Accusing`) — a free, strong intensity signal.
- Every episode has a **logline** and **continuity notes** — free context for the "makes sense alone" judgement.
- Speech rate: median 2.4 words/s (p95 3.9) → a 3-second hook ≈ **7–10 words max**. Useful rule-check.

### 3.2 Quirks a robust tool must handle
| Quirk | Example | Handling |
|---|---|---|
| Header casing differs | E06 uses `SCENE START:` | Case-insensitive parsing ✅ |
| Speaker parentheticals vary | `THE FORMER GROOM (Off-screen) (Dismissive)`, `LORD ASHCROFT (O.S. / Continues)`, `BLOND NOBLEMAN (Rupert) (Cold)` | Parse all groups; extract off-screen flag + alias hints ✅ |
| **Same character, many names** | Clarissa = LADY IN GOLD GOWN; Gerald = THE FORMER GROOM; Alexander = THE BEARDED STRANGER / MYSTERIOUS BEARDED MAN / SCARRED BEARDED MAN; stepmother = MATRIARCH / NOBLE MATRIARCH / LADY ASHCROFT / OFF-SCREEN VOICE; Rupert = BLOND NOBLEMAN; Dowager = ALEXANDER'S MOTHER / LADY ASHBOURNE; High Priest ≈ Father Thomas | Character bible built by LLM once per show |
| **Alias collision** | In E02 "BLOND NOBLEMAN" is Juliana's *father*; from E09 on it's *Rupert* | Aliases must be per-episode, not global |
| **Continuity errors (AI-generated scripts)** | The Duke's estate is called **11 different names**: Ashbury, Ashburg, Ashbourne, Ashburton, Ashburn, Ashburgh, Ashbridge, Ashwood, Ashworth, Ashbrook (+ Ashcroft for her family). Alexander's surname: Ashwin/Ashburn/Ashburton. E46 says the marriage was "three years" ago (it was days). "Clarisse" once. | Flag multi-segment promos that splice two spellings in one clip (viewer confusion) |
| Overlapping/parallel timing | Camera, action and dialogue run in parallel; 8 out-of-order starts; 10 overlapping dialogue pairs | Cut points must snap to *dialogue* boundaries |
| **Hand-picked cuts still clip lines** | 9 of my own 24 hand-labelled cuts initially ended mid-line ("There it is. Ha!") | Boundary snapping must be **code**, never left to the LLM |
| Keywords don't find hooks | "slap/explosion/strike" appear ~15 times in all 50 eps; most hooks are spoken reveals | Semantic scoring (LLM) needed; keywords only as a weak feature |
| Brand-safety content | Blood/torture (E13 briars, E31–32 branding iron at the eye), sex scene (E50) | Ad-policy flag (Meta/TikTok restrict graphic violence & sexual content) |

### 3.3 Story / beat map (promo potential per stretch)
| Eps | Beat | Promo value |
|---|---|---|
| 1–2 | Jilted at altar; sister steals groom; family sides with her | ★★★ premise hook, free eps |
| 3–5 | Scarred stranger defends her, proposes, they wed; disowned; ledger thrown in mud | ★★★ premise payoff + cliff |
| 6–10 | Cottage life; ex mocks; husband's silent menace; "resembles the late Duke" rumour; romance | ★★ mystery/romance |
| 11–14 | Planted watch → "crawl through the briars or he hangs" → bloody hands | ★★★ sacrifice (gore flag) |
| 15–18 | Thugs, fight, Gerald unmasked, cottage set on fire, ledger rescue | ★★ action |
| 19 | **"Your Grace."** — husband secretly the presumed-dead Duke | ★★★ core trope reveal |
| 20–25 | Villains' plot; Juliana undercover as maid; finds arsenic poisoning; whipped | ★★ |
| 26–28 | Duchess recognises the ducal ring; Juliana framed as poisoner; identity exposed | ★★★ |
| 29–34 | Dungeon; branding iron; coerced witness; witch trial | ★★★ (violence flag) |
| 35–39 | Mother escapes, reunion; "their dead Duke is coming home"; transformation | ★★★ |
| 40–45 | Villains' wedding; Juliana paraded in chains; **cathedral explodes**; Duke returns; guards refuse; traitors exposed; "You're the Duke?"; marriage declared invalid | ★★★ biggest payoffs (spoilers) |
| 46–50 | Ten-day trial; villain becomes scullery maid; priest conspiracy; affair witnessed | ★★ (E50 sexual content) |

---

## 4. Human "gold" promo set (24 promos, verified)

Hand-picked after reading all 50 episodes; every segment validated by `eval/check_segments.py` (20–60 s total, no line cut at either edge). Full timestamps in `eval/gold_promos.json`.

| Rank | ID | Segments (Ep: start–end) | Len | Hook (first 3 s) | Cliffhanger (final beat) | Why it works |
|---|---|---|---|---|---|---|
| 1 | G01 | E1 0:35.4–0:43.1 → E3 0:58.2–1:25.6 → E3 2:13.2–2:23.0 | 45 s | "Why are you holding her hand?" / "Because he is marrying me." | Scarred stranger kneels: "Lady Juliana… accept my hand." | Whole premise (betrayal → mysterious saviour) in 45 s; points to free Ep 1 |
| 2 | G06 | E12 0:44.0–1:24.7 | 41 s | "I want to see you crawl, sister." | "Tell me where the garden is." | Villain line is a scroll-stopper; clear stakes (husband hangs); decision cliff |
| 3 | G10 | E19 0:43.0–1:29.0 | 46 s | Stranger bows to the "beggar": "Your Grace." | "Then Ashburg will remember who it belongs to." | The title's trope in one line; mystery + revenge promise |
| 4 | G22 | E45 0:12.5–0:29.6 → 1:14.8–1:21.5 → 1:26.5–1:53.0 | 50 s | "Your eyes… It's you." | "You are not his lawful wife." | Reveal + immediate reversal; double emotional whiplash |
| 5 | G20 | E41 1:21.0–1:29.0 → E42 0:01.0–0:34.0 | 41 s | Cathedral doors explode | "You cannot be him. Alexander died!" | Strongest visual hook in the show; works muted |
| 6 | G13 | E26 1:36.0–1:56.0 → E27 0:17.2–0:52.2 | 55 s | "Your hand… Let me see your hand." | "What is your husband's name?" + doors burst open | Classic recognition beat, interrupted at the peak |
| 7 | G18 | E36 2:12.2–2:43.2 → 3:02.0–3:17.0 | 46 s | "They condemned her." | "…their dead Duke is coming home." | Deadline + vow; pure revenge anticipation |
| 8 | G02 | E1 0:33.7–1:19.0 | 45 s | "Gerald? Why are you holding her hand?" | "…he was never going to marry you." | Single continuous cut of the premise; simplest to produce |
| 9 | G16 | E34 2:22.4–3:10.0 | 48 s | "If you wish to save yourself, renounce these practices." | Judge: "Lady Juliana Ashcroft…" (verdict unspoken) | Defiance under maximum stakes; verdict withheld |
| 10 | G21 | E44 0:25.2–1:11.0 | 46 s | "Alexander… I thought you had died." | "Her?!" | Love-triangle jealousy; satisfying rejection |
| 11 | G03 | E3 0:58.2–1:25.6 → 1:50.9–2:23.0 | 60 s | "Guards! Remove her!" (bride dragged) | "Accept my hand." | Physical hook + rescue; at the 60 s limit |
| 12 | G15 | E31 1:38.5–2:33.0 | 55 s | "I have beauty, money, family, status! What do you have?" | Branding iron stops inches from her eye | Great exchange — **ad-policy risk** |
| 13 | G14 | E28 1:10.8–1:56.0 | 45 s | Locket ripped from her neck | "Do not speak about my husband!" | Humiliation + identity exposure |
| 14 | G04 | E7 1:05.6–1:31.5 → E9 1:32.1–1:52.0 | 46 s | "I have enough influence to make a beggar disappear." | "Impossible." (villain hears Duke rumour) | Builds the hidden-identity mystery early (free eps) |
| 15 | G19 | E38 1:04.5–1:22.0 → E39 0:56.5–1:08.5 → 1:25.5–1:38.0 | 42 s | Execution bells toll | "And I am bringing my wife home." | Cross-cut rescue tension |
| 16 | G17 | E35 0:37.0–0:59.0 → 2:14.0–2:31.0 | 39 s | "Alexander!" "Mother?" "I buried you." | "…same men ruling Ashwood now." | Reunion + conspiracy |
| 17 | G07 | E13 0:45.8–1:28.8 | 43 s | She kneels before frozen thorns; "Juliana, stop!" | Still searching, bleeding | Sacrifice — **gore flag** |
| 18 | G08 | E15 0:44.8–1:24.0 | 39 s | Thug shoves her down | "You want to fight us, veteran?" | Clean fight cliff |
| 19 | G23 | E47 0:56.8–1:41.5 | 45 s | "You dare show your face…?" | "As a scullery maid." | Face-slap payoff (weaker cliff) |
| 20 | G09 | E18 0:56.2–1:29.0 | 33 s | "The ledger!" / "Leave it!" | Beam crashes where she stood | Action peril |
| 21 | G05 | E11 0:16.8–0:25.2 → 1:21.3–1:46.6 | 34 s | "Your husband stole my gold pocket watch!" | "There it is. Ha!" | Frame-up |
| 22 | G11 | E23 1:10.5–1:28.0 → 1:52.2–2:11.5 | 37 s | "I have seen these symptoms before." | "Someone is coming." | Mystery; weaker hook |
| 23 | G12 | E24 0:27.0–0:48.0 → 1:18.6–1:29.8 | 32 s | "Then let her suffer." + riding-crop strike | "You cannot stop the healer." | The show's only true "slap" beat; weak cliff |
| 24 | G24 | E10 1:03.9–1:34.0 | 30 s | "Why do you look at me like that?" | "Your touch is the only medicine…" | Romance; no cliff, use for romance-audience variant |

### Ranking logic (what to post first and why)
1. **Premise first, from free episodes** (G01, G06, G02, G04): new viewers land on Ep 1–12, which they can watch immediately; no spoilers; the trope is instantly legible.
2. **Then the core trope reveal** (G10 "Your Grace") — the title already promises "He was a Duke", so this confirms rather than spoils.
3. **Big payoff clips** (G20, G22, G13, G18) have the strongest hooks but spoil late arcs → best for **retargeting** viewers who already started, or as a second wave once early creatives fatigue.
4. **Ad-policy-risky clips** (G07, G15, E50 material) are ranked down regardless of drama score.

---

## 5. Where an automated picker will predictably fail (to test & report honestly)
1. **Mid-line cuts** — even a careful human made this error 9/24 times. Must be enforced in code.
2. **Hook that's not in the first 3 s** — e.g. a great scene whose punch line arrives at second 6 (G01-alt "You should turn around" takes 28 s to pay off).
3. **Resolution leakage** — clip runs 2–4 s too long and resolves the cliff ("I've got you" after the beam).
4. **Context-dependent clips** — villains-only plotting scenes (E20, E30, E48–49) are dramatic but meaningless to a stranger.
5. **Name confusion** — clips that name "Rupert", "Sterling", "Ashburg" with no setup; multi-segment promos mixing estate spellings.
6. **Alias errors** — "BLOND NOBLEMAN" = father in E02, Rupert later; a naive character bible merges them.
7. **Emotion-tag over-trust** — every line is tagged "Furious/Screaming"; tags inflate intensity uniformly (melodrama), so they don't discriminate much alone.
8. **Spoilers** — model happily picks the E42 reveal as #1; needs a spoiler/funnel policy.
9. **Brand safety** — gore/torture/sexual content scores high on "drama" but is unpostable.
10. **Script ≠ screen** — we judge text; actual performance, faces and music are unseen. A 3-second hook in text may be 5 seconds on screen.

---

## 6. Recommended solution design

```
screenplays/*.txt
   │  1. PARSE (code)            → blocks, scenes, timings, speakers, tones, loglines
   │  2. SHOW BIBLE (LLM, once)  → characters + per-episode aliases, premise, spoiler milestones
   │  3. BEAT TAGGING (LLM, per episode, ~2k tokens each)
   │       label each dialogue/action block: hook-worthy? (reveal/slap/threat/shock),
   │       cliff-worthy? (unresolved question), resolves-what?, needs-context?, safety flags
   │  4. CANDIDATE GENERATION (code)
   │       single windows: start on a hook-worthy block, end on a cliff-worthy block,
   │       20–60 s, snapped to dialogue boundaries, trimmed so nothing resolves after the cliff
   │       multi-segment: hook from ep A + escalation + cliff from ep B (same storyline)
   │  5. RULE CHECKS (code)  length · first-3s has hook block · last block unresolved ·
   │       no mid-line cuts · word budget in 3 s · name/alias consistency · safety flags
   │  6. JUDGE & RANK (LLM, rubric) hook / cliffhanger / standalone / trope clarity /
   │       funnel position / spoiler level → weighted score; pairwise tie-break with order swap
   │  7. OUTPUT  promos.json + promos.csv + promos.md (episode, segments, hook, cliff, why, rank)
   └─ 8. HUMAN-IN-LOOP  editor approves/rejects top-N in a simple review sheet → feedback for weights
```

**What goes to AI vs code vs human** (graded lens):
- **Code**: parsing, timing, boundary snapping, length/word budgets, dedupe, overlap, output formats — deterministic, free, testable.
- **AI**: understanding *meaning* — which line is a reveal, whether a moment is unresolved, whether a stranger would follow it, writing the "why".
- **Human**: final pick per week (5 min instead of watching 100 min), safety sign-off.

**Model-swappable**: one `config.yaml` (`provider: gemini|groq|ollama|openai-compatible|anthropic`, `model: …`) and a single `llm.complete(prompt, schema)` adapter (OpenAI-compatible HTTP covers Groq, Ollama, OpenRouter, most providers Kuku might plug in). JSON-schema output + retry on invalid JSON.

**Cost at scale** (rough): whole show ≈ 23k words without camera lines ≈ 35k tokens. Beat tagging ≈ 50 calls × ~2k in/0.5k out; judging ≈ 60 candidates × ~1.5k. ≈ **200k tokens/show** → cents on a paid flash-tier model; **free** on Gemini/Groq free tiers. Weekly new shows → trivial cost; the bottleneck is human review, which the tool shrinks.

---

## 7. Evaluation plan ("how you know it's good")
1. **Gold set**: the 24 hand-labelled promos above.
2. **Recall@K**: of the gold promos, how many does the tool find (≥50% time-overlap on hook & cliff segments) in its top 10 / 25?
3. **Precision by audit**: blind-rate the tool's top 15 on 3 binary checks (hook in 3 s? unresolved end? understandable alone?).
4. **Rule pass rate**: 100% must pass length/boundary checks (code guarantees).
5. **Stability**: run twice (and on two different models) — overlap of top-10 lists.
6. **Ablation**: rules-only baseline (emotion tags + SFX "cliffhanger" cues) vs LLM pipeline → shows what the AI adds.
7. **In production (after real team use)**: editor acceptance rate of top-10, time saved per show, and ad metrics on posted promos — 3-second hook rate (3 s views / impressions), completion rate, CTR, install/CPI vs editor-picked promos.

---

## 8. Assumptions (to state in the doc)
1. Script timestamps ≈ final cut timestamps (scripts are "detailed screenplays with timestamps").
2. Promo audience = US social users who have never seen the show.
3. Spoilers of the title premise ("he's a Duke") are acceptable; later twists are retargeting-only.
4. Multi-segment promos only splice within one storyline and keep chronological order.
5. Visual-only hooks (from ACTION/SFX lines) count as hooks — vertical ads are often watched muted.
6. "Best" = would stop a scroll and drive to Ep 1; no access to real performance data, so ranking is a judgement proxy.
7. Brand-safety follows typical Meta/TikTok ad policy (no graphic gore/sexual content).

---

## 9. Next steps
1. Build `promo/llm.py` (provider adapter + JSON schema), `promo/tag.py`, `promo/candidates.py`, `promo/rank.py`, `run.py` CLI.
2. Run on all 50 episodes → `outputs/` (raw, unedited).
3. Evaluate vs gold set; write failures honestly.
4. 2-page PDF doc + optional 3-min video.
5. Keep a log of "where AI got it wrong" — already have one: **AI-written scripts in the pack contain 11 spellings of the same estate**, and my first hand-made cut list clipped lines 9 times.
