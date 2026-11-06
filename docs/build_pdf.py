"""Builds docs/solution.pdf (2 pages). Edit TEXT below, then: python docs/build_pdf.py"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether

ACC = colors.HexColor("#8a3324")
H = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=11, leading=13.5, textColor=ACC, spaceBefore=5, spaceAfter=1.5)
B = ParagraphStyle("b", fontName="Helvetica", fontSize=9.3, leading=11.9, spaceAfter=1.5)
BL = ParagraphStyle("bl", parent=B, leftIndent=8, bulletIndent=0)
T = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=16, leading=19)
S = ParagraphStyle("s", fontName="Helvetica", fontSize=8.2, leading=10, textColor=colors.HexColor("#555555"))
C = ParagraphStyle("c", fontName="Helvetica", fontSize=8.3, leading=10.2)
CB = ParagraphStyle("cb", parent=C, fontName="Helvetica-Bold")


def p(t, st=B): return Paragraph(t, st)
def bl(items): return [Paragraph(i, BL, bulletText="•") for i in items]
def table(rows, widths, head=True):
    data = [[Paragraph(str(c), CB if (head and r == 0) else C) for c in row] for r, row in enumerate(rows)]
    t = Table(data, colWidths=[w * mm for w in widths])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
                           ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3eee6") if head else colors.white),
                           ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 1.6),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6), ("LEFTPADDING", (0, 0), (-1, -1), 3)]))
    return t


story = [
    p("Promo Finder: finding the best promos in a microdrama, automatically", T),
    p("Kuku AI Generalist Assignment · Problem 1 · Vaibhav Arya · 231112 · B.Tech Civil Engineering · "
      "Prototype: [GitHub link] · Raw outputs: [Drive link] · Video: [link]", S),

    p("1. Why this problem", H),
    p("Promos are how microdrama apps buy every new viewer. Editors currently watch each episode to pick them, and Kuku "
      "releases shows weekly, so this is a daily, repeated cost on the business's main growth lever. It also has real data "
      "(50 timestamped episodes), an output that can be checked against timestamps, and it matches the interview test "
      "(re-run on a new show). Problem 2 had no data and a high risk of invented law; Problem 3 needed proof of the problem first."),

    p("2. Assumptions (the brief was silent)", H),
    *bl(["Script timestamps ≈ final-cut timestamps. Audience: US social users who have never seen the show.",
         "'He was a Duke' is in the title, so the premise is not a spoiler; later twists are retargeting-only.",
         "Visual beats (strikes, explosions) count as hooks, since vertical ads are often watched muted. Multi-part edits keep playback order.",
         "Graphic violence and sexual content are flagged for typical Meta/TikTok ad policy, not silently dropped. "
         "No access to real ad performance, so 'best' = the brief's three tests plus posting strategy."]),

    p("3. How it works", H),
    p("<b>Parse → score every beat → generate cuts → rank → editor reviews.</b> "
      "(1) <b>Parse</b> 3,727 timed blocks; camera lines count for time but never decide a cut. "
      "(2) <b>Score each line/action</b> for hook, cliffhanger, intensity, context-need and safety, using the script's own "
      "emotion tags, identity-reveal patterns ('he is marrying me', 'your grace'), physical actions, "
      "<b>overlap with the episode logline</b> (the writer's own summary of the key beat; this was the biggest single gain), "
      "<b>'cut right before the payoff'</b>, and penalties for endings that resolve (an embrace, 'Are you hurt?'), "
      "even when the script labels them 'cliffhanger'. "
      "(3) <b>Generate ~1,400 cuts</b>: continuous, 'pruned' (strong hook + strong ending with the weak middle removed, as an editor "
      "would) and cross-episode. Every cut is snapped to line boundaries and kept within 20–60 s <i>by code</i>, so timestamps are never "
      "an AI guess. (4) <b>Rank</b> with diversity (one promo per hook moment; the rest become A/B 'alternate cuts'), then a "
      "<b>posting plan</b>: wave 1 = early free episodes (a new viewer can start now, nothing spoiled), wave 2 = mid-story, "
      "wave 3 = late payoffs for retargeting. (5) An editor approves the shortlist in a review page."),
    table([["Kept as code", "Given to AI (optional, one config line)", "Human in the loop"],
           ["Parsing, timing, line-boundary snapping, 20–60 s, dedupe, safety flags, outputs. Free, exact, testable.",
            "Meaning: is this a reveal? does it resolve? would a stranger follow it? Beat tagging (50 calls) + shortlist judge "
            "(60 calls), blended with the rule scores. OpenAI-compatible (Gemini/Groq/Ollama/any vendor API) or Anthropic.",
            "Editor approves ~10 picks in review.html (minutes instead of 100 min of footage); checks flagged "
            "multi-part edits and ad-policy flags."]], [56, 70, 52]),
    p("<b>Runs offline with no key</b> (rule mode, ~3 s for 50 episodes). With a model, the measured cost is ~150k tokens per show: "
      "about $0.03 on a Flash-class model, free within Gemini's free tier, and cached so re-runs are free. Scale: 10 shows a week ≈ 1,100 calls; "
      "the editor's review is the bottleneck, not compute.", B),
]

page2 = [
    p("4. What it found and what I'd post first", H),
    table([["Wave", "Promo (tool output)", "Hook (first 3 s)", "Cliffhanger", "Why it works"],
           ["1", "E3 01:24.0–01:38.5 + 02:13.2–02:25.8 (27 s)", "Scarred stranger drops a guard dragging the bride",
            "He kneels with a ring; her answer withheld", "Whole premise, free episode, works muted"],
           ["1", "E12 00:44.0–01:27.2 (43 s)", "'I want to see you crawl, sister.'", "'Tell me where the garden is' (freeze)",
            "Cruel ultimatum, clear stakes, a decision left hanging"],
           ["1", "E1 00:39.1–01:14.3 (35 s)", "'Because he is marrying me.'", "'How long?'", "Altar betrayal, episode 1, no context needed"],
           ["2", "E24 00:32.5–01:08.0 (36 s)", "Riding-crop strike", "Crop turned on her friend", "The show's only true 'slap' beat"],
           ["2", "E23 01:19.0–02:04.0 (45 s)", "'Someone is poisoning her.'", "'Someone is coming.'", "Reveal, then an interruption at the peak"]],
          [11, 45, 41, 40, 41]),
    p("Full ranked list (30 promos, alternate cuts, 10 cross-episode variants, the posting plan) is in the raw outputs.", S),

    p("5. How I know it's good, and where it fails", H),
    table([["Check", "Result"],
           ["Hard rules (independent re-check of 40 outputs)", "40/40 within 20–60 s, no line cut at any edge; deterministic across runs"],
           ["Blind audit of top 30 against the brief's 3 tests", "<b>8/10 of the top 10</b> and 20/30 overall pass all three (hook 27, cliffhanger 28, standalone 24)"],
           ["Gold set: 24 promos I picked by reading all 50 eps", "Generator finds 22/24 (92%); top-30 recall 0.38; top-10 precision ≥ 0.50"],
           ["Overfitting guard: tune on eps 1–25, test on 26–50", "Kept only changes that held up on test. A 150-trial weight search raised tune recall 0.31→0.54 "
                                                                   "but <b>dropped test 0.36→0.27, so I rejected it</b>."]],
          [62, 116]),
    p("<b>Where it picks badly:</b>", B),
    *bl(["<b>Context-heavy clips</b> (6/30): names like Sterling or 'the council' mean nothing to a stranger. Rules catch names, not plot.",
         "<b>Quiet twists</b>: 'Your Grace.' said to the 'beggar' husband is the show's core reveal, but rules score it low because it's calm; "
         "'Mother.' slipped in as a hook. Payoffs ('This is my son… the rightful Duke!') can pass for cliffhangers.",
         "<b>Cross-episode edits</b>: only ~4/10 usable without an editor or LLM check, so they're kept out of the main ranking in rule mode.",
         "<b>Text ≠ screen</b>: acting, faces and music are invisible; the gold set and audit come from one rater. Next step: an editor re-rates "
         "and the posted promos' 3-second hook rate, completion and CPI are compared with editor-picked promos. That's how we'd know it works in production."]),
    p("The LLM layer's 'context' and 'resolves' scores target the first two failures, and measuring it is the first thing to do with a key.", B),

    p("6. AI tools used, and where they got it wrong", H),
    p("Claude (Claude Code) for research, script reading, coding and tests. Where it got things wrong:", B),
    *bl(["Its first list of 24 hand-picked cuts <b>clipped dialogue mid-line 9 times</b> ('There it is. Ha!'), which is why cut points are now code, never model output.",
         "The scripts themselves: the Duke's estate is spelled <b>11 different ways</b> (Ashburg, Ashbourne, Ashburton…), a marriage of a few days "
         "is called 'three years', and a romantic embrace is labelled 'cliffhanger'. The tool had to stop trusting those labels.",
         "Its suggested weight tuning <b>overfit</b> (above), and tests caught a JSON parser it wrote that misread array replies."]),
    p("7. Scaling to every show", H),
    p("Same format means no per-show setup: leads, names and aliases are inferred from the scripts. The weekly flow is "
      "script → run (seconds) → editor approves in review.html → export. Approve/reject decisions are logged and become new gold labels "
      "for re-tuning and per-genre weights. Next steps: add the LLM judge, learn weights from real ad metrics, and generate several A/B cuts per hook.", B),
]

doc = SimpleDocTemplate("docs/solution.pdf", pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
                        topMargin=11 * mm, bottomMargin=10 * mm, title="Promo Finder: Solution", author="Vaibhav Arya")
from reportlab.platypus import PageBreak
doc.build(story + page2)
print("built docs/solution.pdf")
