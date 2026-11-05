"""Promo finder pipeline: parse -> score beats -> (optional LLM tagging) -> candidates -> rules -> rank.

Design rule: anything that must be *exactly right* (timestamps, cut boundaries, 20-60 s length) is code.
Anything that needs *understanding* (is this a reveal? would a stranger follow it?) is the LLM when one is
configured, and transparent rule-based scores when it isn't.
"""
from __future__ import annotations

import json
import re
import string
from collections import Counter, defaultdict

from . import features as F
from .llm import LLM, LLMError
from .parse import parse_dir

MIN_LEN, MAX_LEN = 20.0, 60.0
PREF_LO, PREF_HI = 25.0, 45.0
EPS = 0.05


def tc(t: float) -> str:
    return f"{int(t // 60):02d}:{t % 60:05.2f}"


# ----------------------------------------------------------------------------------- show model
class Show:
    def __init__(self, input_dir: str, llm: LLM | None = None, log=print):
        self.log = log
        self.eps = parse_dir(input_dir)
        if not self.eps:
            raise SystemExit(f"no screenplay .txt files found in {input_dir}")
        self.by_num = {e["number"]: e for e in self.eps}
        self.order = [e["number"] for e in self.eps]
        self.leads = F.lead_names(self.eps)
        self.vocab = proper_nouns(self.eps)
        self.beats = {e["number"]: F.score_beats(e, self.leads) for e in self.eps}
        self.dialogue = {e["number"]: [b for b in e["blocks"] if b["kind"] == "DIALOGUE"] for e in self.eps}
        self.llm = llm or LLM({"provider": "heuristic"})
        self.llm_tagged = 0

    # cut-boundary rules (pure code) ------------------------------------------------------
    def straddles(self, ep: int, t: float) -> bool:
        return any(d["start"] < t - EPS and d["end"] > t + EPS for d in self.dialogue[ep])

    def segment(self, ep: int, i: int, j: int):
        """Beats i..j of episode -> (start, end) snapped so no dialogue line is cut, or None."""
        bs = self.beats[ep]
        s = bs[i]["start"]
        e = max(b["end"] for b in bs[i:j + 1])
        if j + 1 < len(bs) and bs[j + 1]["kind"] == "DIALOGUE" and bs[j + 1]["start"] < e - EPS:
            last_dlg_end = max((b["end"] for b in bs[i:j + 1] if b["kind"] == "DIALOGUE"), default=s)
            if bs[j + 1]["start"] + EPS < last_dlg_end:
                return None
            e = bs[j + 1]["start"]
        if self.straddles(ep, s) or self.straddles(ep, e):
            return None
        return round(s, 2), round(e, 2)


def proper_nouns(eps) -> set[str]:
    """Names of people/places: capitalised mid-sentence at least twice and never seen in lower case."""
    c, lower = Counter(), set()
    for e in eps:
        for b in e["blocks"]:
            txt = b["text"] or ""
            lower.update(re.findall(r"\b[a-z][a-z]+\b", txt))
            if b["kind"] != "DIALOGUE":
                continue
            toks = re.findall(r"[\w']+|[.!?]", txt)
            for k, w in enumerate(toks):
                if k == 0 or toks[k - 1] in ".!?":
                    continue
                if re.fullmatch(r"[A-Z][a-z]{2,}", w) and w not in F.COMMON:
                    c[w] += 1
    return {w for w, n in c.items() if n >= 2 and w.lower() not in lower}


# ----------------------------------------------------------------------------------- LLM tagging
TAG_SYSTEM = ("You are a senior promo editor for vertical microdrama apps (ReelShort/DramaBox style). "
              "You judge screenplay beats for social-media promo potential. Reply with JSON only.")
TAG_PROMPT = """Show premise (from episode loglines): {premise}
Episode {ep} logline: {logline}

Beats (id | time | type | speaker [tone] | text):
{beats}

For EVERY beat id give integers 0-10:
- hook: would this beat, as the FIRST 3 SECONDS of a promo, stop a scrolling stranger? (slap, reveal, shocking line, physical shock, status inversion)
- cliff: if the promo CUT right after this beat, how badly would a viewer need to know what happens next? (unanswered question, threat, interruption, decision pending). Low if the beat resolves tension.
- context: how much prior-episode knowledge a stranger needs to understand this beat (0 = none).
Return JSON: {{"beats": [{{"id": "...", "hook": 0, "cliff": 0, "context": 0}}, ...]}}"""


def llm_tag(show: Show, premise: str):
    for e in show.eps:
        ep = e["number"]
        bs = show.beats[ep]
        lines = "\n".join(f"{b['id']} | {tc(b['start'])} | {b['kind']} | {(b.get('speaker') or '')}"
                          f"{' [' + b['tone'] + ']' if b.get('tone') else ''} | {b['text']}" for b in bs)
        try:
            out = show.llm.complete_json(TAG_PROMPT.format(premise=premise, ep=ep, logline=e["logline"],
                                                           beats=lines), TAG_SYSTEM)
        except LLMError as err:
            show.log(f"  ! LLM tagging failed for E{ep}: {err} (keeping rule scores)")
            continue
        got = {str(x.get("id")): x for x in (out.get("beats", []) if isinstance(out, dict) else out)}
        for b in bs:
            x = got.get(b["id"])
            if not x:
                continue
            h, c, ctx = (_num(x.get(k)) for k in ("hook", "cliff", "context"))
            b["hook_rule"], b["cliff_rule"] = b["hook"], b["cliff"]
            if h is not None:
                b["hook"] = round(0.35 * b["hook"] + 0.65 * h / 10, 3)
            if c is not None:
                b["cliff"] = round(0.35 * b["cliff"] + 0.65 * c / 10, 3)
            if ctx is not None:
                b["context_llm"] = ctx / 10
        show.llm_tagged += 1


def _num(v):
    try:
        return max(0.0, min(10.0, float(v)))
    except (TypeError, ValueError):
        return None


# ----------------------------------------------------------------------------------- scoring
def window_score(show: Show, segs: list[tuple[int, int, int, float, float]]) -> dict:
    """segs: (episode, i, j, start, end) in playback order."""
    W = F.WEIGHTS
    ep0, i0, _, s0, _ = segs[0]
    first = show.beats[ep0]
    hook_beats = [b for b in first[i0:] if b["start"] < s0 + 3.0]
    hook_b = max(hook_beats, key=lambda b: b["hook"] * (1 - 0.08 * (b["start"] - s0)), default=None)
    hook = hook_b["hook"] * (1 - 0.08 * (hook_b["start"] - s0)) if hook_b else 0.0
    epL, _, jL, _, _ = segs[-1]
    cliff_b = show.beats[epL][jL]
    cliff = cliff_b["cliff"]
    inside = [b for (ep, i, j, s, e) in segs for b in show.beats[ep][i:j + 1]]
    body = sum(b["intensity"] for b in inside) / max(len(inside), 1)
    lead_frac = sum(b["has_lead"] for b in inside) / max(len(inside), 1)
    words = " ".join(b["text"] or "" for b in inside if b["kind"] == "DIALOGUE")
    # surnames right after a lead's name introduce the lead ("Lady Juliana Ashcroft"), so they are not unknown
    lead_re = "|".join(l.title() for l in show.leads)
    intro = set(re.findall(rf"\b(?:{lead_re})\s+([A-Z][a-z]+)", words)) if lead_re else set()
    unknown = sorted({w for w in re.findall(r"\b[A-Z][a-z]{2,}\b", words) if w in show.vocab}
                     - {l.title() for l in show.leads} - intro)
    ctx_llm = [b["context_llm"] for b in inside if "context_llm" in b]
    standalone = 1.0 - min(len(unknown), 4) * W["unknown_name_penalty"] / 0.25 * 0.25
    if lead_frac == 0:
        standalone -= W["no_lead_penalty"] / 0.25 * 0.5
    if ctx_llm:
        standalone = 0.5 * standalone + 0.5 * (1 - sum(ctx_llm) / len(ctx_llm))
    standalone = max(standalone, 0.0)
    length = sum(e - s for (_, _, _, s, e) in segs)
    if length < PREF_LO:
        lpref = 1 - 0.4 * (PREF_LO - length) / (PREF_LO - MIN_LEN)
    elif length > PREF_HI:
        lpref = 1 - 0.4 * (length - PREF_HI) / (MAX_LEN - PREF_HI)
    else:
        lpref = 1.0
    joint_pen = sum(W["continued_penalty"] for (ep, i, j, s, e) in segs[1:] if show.beats[ep][i]["continues_prev"])
    # pruning must not cut out the setup the ending depends on: penalise dropping logline-central beats
    dropped_sal = 0.0
    for (ep_a, _, j_a, _, _), (ep_b, i_b, _, _, _) in zip(segs, segs[1:]):
        if ep_a == ep_b:
            dropped_sal = max([dropped_sal] + [b["logline_sal"] for b in show.beats[ep_a][j_a + 1:i_b]])
    gore = sum(b["gore"] for b in inside)
    sexual = any(b["sexual"] for b in inside)
    eps_used = sorted({ep for ep, *_ in segs})
    pos = show.order.index(eps_used[0]) / max(len(show.order) - 1, 1)
    score = (W["w_hook"] * min(hook, 1.2) + W["w_cliff"] * min(cliff, 1.2) + W["w_body"] * min(body, 1.0)
             + W["w_standalone"] * standalone) * lpref
    score -= W["segment_penalty"] * (len(segs) - 1) + joint_pen * 0.2 + W.get("dropped_setup", 0.15) * dropped_sal
    score -= W["gore_penalty"] * (gore >= 2) + W["sexual_penalty"] * sexual
    score += W["early_bonus"] * (1 - pos)
    return {
        "score": round(score, 4), "hook": round(hook, 3), "cliff": round(cliff, 3), "body": round(body, 3),
        "standalone": round(standalone, 3), "length": round(length, 2), "hook_beat": hook_b, "cliff_beat": cliff_b,
        "unknown_names": unknown, "gore_beats": gore, "sexual": sexual, "lead_frac": round(lead_frac, 2),
        "position": round(pos, 3),
    }


# ----------------------------------------------------------------------------------- candidates
def candidates(show: Show, per_episode: int = 25) -> list[dict]:
    out = []
    for ep in show.order:
        bs = show.beats[ep]
        if not bs:
            continue
        hook_cut = sorted((b["hook"] for b in bs), reverse=True)[min(len(bs) - 1, max(6, len(bs) // 3))]
        cliff_cut = sorted((b["cliff"] for b in bs), reverse=True)[min(len(bs) - 1, max(6, len(bs) // 3))]
        starts = [i for i, b in enumerate(bs) if b["hook"] >= hook_cut and b["hook"] > 0]
        ends = [j for j, b in enumerate(bs) if b["cliff"] >= cliff_cut and b["cliff"] > 0]
        local = []
        # 1) single continuous windows
        for i in starts:
            for j in ends:
                if j < i:
                    continue
                seg = show.segment(ep, i, j)
                if not seg or not (MIN_LEN <= seg[1] - seg[0] <= MAX_LEN):
                    continue
                local.append(make(show, [(ep, i, j, *seg)], "single"))
        # 2) pruned two-segment windows: great hook + great cliff too far apart -> drop the weakest middle
        top_h = sorted(starts, key=lambda i: -bs[i]["hook"])[:8]
        top_c = sorted(ends, key=lambda j: -bs[j]["cliff"])[:8]
        for i in top_h:
            for j in top_c:
                if j <= i + 2 or bs[j]["end"] - bs[i]["start"] <= MAX_LEN * 0.9:
                    continue
                best = None
                for k in range(i, j - 1):
                    s1 = show.segment(ep, i, k)
                    if not s1 or not (4 <= s1[1] - s1[0] <= 30):
                        continue
                    for m in range(k + 2, j + 1):
                        s2 = show.segment(ep, m, j)
                        if not s2 or not (6 <= s2[1] - s2[0] <= 45) or s2[0] < s1[1]:
                            continue
                        total = (s1[1] - s1[0]) + (s2[1] - s2[0])
                        if not (MIN_LEN <= total <= MAX_LEN):
                            continue
                        c = make(show, [(ep, i, k, *s1), (ep, m, j, *s2)], "pruned")
                        if best is None or c["score"] > best["score"]:
                            best = c
                if best:
                    local.append(best)
        local.sort(key=lambda c: -c["score"])
        out.extend(local[:per_episode])
    out.extend(cross_episode(show))
    return out


def cross_episode(show: Show, span: int = 2) -> list[dict]:
    """Hook moment from episode A + escalation/cliff from episode B (A < B <= A+span), same storyline."""
    hooks, cliffs = {}, {}
    for ep in show.order:
        bs = show.beats[ep]
        hs, cs = [], []
        for i in sorted(range(len(bs)), key=lambda i: -bs[i]["hook"])[:5]:
            for k in range(i, len(bs)):
                seg = show.segment(ep, i, k)
                if seg and 5 <= seg[1] - seg[0] <= 20:
                    hs.append((ep, i, k, *seg))
                    break
        for j in sorted(range(len(bs)), key=lambda j: -bs[j]["cliff"])[:5]:
            for m in range(j, -1, -1):
                seg = show.segment(ep, m, j)
                if seg and 10 <= seg[1] - seg[0] <= 40:
                    cs.append((ep, m, j, *seg))
                    break
        hooks[ep], cliffs[ep] = hs, cs
    out = []
    for a_idx, a in enumerate(show.order):
        for b in show.order[a_idx + 1:a_idx + 1 + span]:
            for h in hooks[a]:
                for c in cliffs[b]:
                    total = (h[4] - h[3]) + (c[4] - c[3])
                    if not (MIN_LEN <= total <= MAX_LEN):
                        continue
                    if not storyline_link(show, h, c):
                        continue
                    out.append(make(show, [h, c], "cross-episode"))
    out.sort(key=lambda c: -c["score"])
    return out[: 3 * len(show.order)]


def storyline_link(show, h, c) -> bool:
    def people(seg):
        ep, i, j = seg[:3]
        names = set()
        for b in show.beats[ep][i:j + 1]:
            if b.get("speaker"):
                names.add(F.fold_name(b["speaker"]))
            for l in show.leads:
                if re.search(rf"\b{l}\b", (b["text"] or "").upper()):
                    names.add(l)
        return names
    return bool(people(h) & people(c))


def make(show: Show, segs, kind: str) -> dict:
    sc = window_score(show, segs)
    return {"kind": kind, "segments": [{"episode": ep, "start": s, "end": e, "beat_from": show.beats[ep][i]["id"],
                                        "beat_to": show.beats[ep][j]["id"]} for (ep, i, j, s, e) in segs], **sc}


# ----------------------------------------------------------------------------------- selection
def overlap(a: dict, b: dict) -> float:
    ov = 0.0
    for x in a["segments"]:
        for y in b["segments"]:
            if x["episode"] == y["episode"]:
                ov += max(0.0, min(x["end"], y["end"]) - max(x["start"], y["start"]))
    return ov / max(min(a["length"], b["length"]), 1e-6)


def select(cands: list[dict], k: int = 40, max_per_ep: int = 3, max_overlap: float = 0.35) -> list[dict]:
    """Greedy diversity selection (non-maximum suppression over time overlap)."""
    cands = sorted(cands, key=lambda c: -c["score"])
    chosen, per_ep = [], Counter()
    for c in cands:
        if len(chosen) >= k:
            break
        eps = {s["episode"] for s in c["segments"]}
        if any(per_ep[e] >= max_per_ep for e in eps):
            continue
        if any(overlap(c, o) > max_overlap for o in chosen):
            continue
        # one promo per hook moment: variants that reuse the same opening beat are near-duplicates
        if any(c["segments"][0]["beat_from"] == o["segments"][0]["beat_from"] for o in chosen):
            continue
        chosen.append(c)
        for e in eps:
            per_ep[e] += 1
    return chosen


# ----------------------------------------------------------------------------------- LLM judge
JUDGE_SYSTEM = TAG_SYSTEM
JUDGE_PROMPT = """Show premise: {premise}

Candidate promo ({length:.0f}s), segments in playback order:
{transcript}

Score 0-10 each, strictly:
- hook_3s: do the first 3 seconds stop a scrolling stranger?
- cliffhanger: does the final beat leave an unresolved question (not a resolution)?
- standalone: does it make sense to someone who never saw the show?
- trope_clarity: is the show's appeal (betrayal, hidden identity, revenge, romance) instantly legible?
Also: "hook": the hook moment in <=12 words, "cliffhanger": the final unresolved beat in <=12 words,
"why": ONE sentence on why it works, "ad_safe": false if graphic gore or sexual content.
JSON: {{"hook_3s":0,"cliffhanger":0,"standalone":0,"trope_clarity":0,"hook":"","cliffhanger_text":"","why":"","ad_safe":true}}"""


def llm_judge(show: Show, chosen: list[dict], premise: str):
    for c in chosen:
        try:
            out = show.llm.complete_json(JUDGE_PROMPT.format(premise=premise, length=c["length"],
                                                             transcript=transcript(show, c)), JUDGE_SYSTEM)
        except LLMError as err:
            show.log(f"  ! LLM judge failed: {err}")
            continue
        vals = [_num(out.get(k)) for k in ("hook_3s", "cliffhanger", "standalone", "trope_clarity")]
        if None in vals:
            continue
        llm_score = (0.32 * vals[0] + 0.32 * vals[1] + 0.2 * vals[2] + 0.16 * vals[3]) / 10
        c["llm"] = {k: out.get(k) for k in out}
        c["rule_score"] = c["score"]
        c["score"] = round(0.4 * c["score"] + 0.6 * llm_score - (0.3 if out.get("ad_safe") is False else 0), 4)


def transcript(show: Show, c: dict) -> str:
    lines = []
    for s in c["segments"]:
        lines.append(f"[Episode {s['episode']} {tc(s['start'])}-{tc(s['end'])}]")
        for b in show.beats[s["episode"]]:
            if b["start"] >= s["start"] - EPS and b["start"] < s["end"]:
                who = f"{b['speaker']} ({b['tone']})" if b["kind"] == "DIALOGUE" else b["kind"]
                lines.append(f"  {tc(b['start'] - s['start'] + 0)} {who}: {b['text']}")
    return "\n".join(lines)


# ----------------------------------------------------------------------------------- explanation
def next_beat(show: Show, c: dict):
    last = c["segments"][-1]
    for b in show.beats[last["episode"]]:
        if b["start"] >= last["end"] - EPS:
            return b
    return None


def short(b, n=7):
    words = (b["text"] or "").split()
    t = " ".join(words[:n]) + ("..." if len(words) > n else "")
    return f'"{t}"' if b["kind"] == "DIALOGUE" else f"[{t}]"


def describe(show: Show, c: dict) -> dict:
    hb, cb = c["hook_beat"], c["cliff_beat"]
    llm = c.get("llm") or {}

    def say(b):
        if not b:
            return "(no beat in first 3 s)"
        if b["kind"] == "DIALOGUE":
            return f'{string.capwords(b["speaker"].lower())}: "{b["text"]}"'
        return f"[{b['kind'].lower()}] {b['text']}"

    hook = llm.get("hook") or say(hb)
    story_end = cb
    if cb["kind"] == "SOUND FX":  # a music sting isn't the cliffhanger; the last story beat before it is
        last = c["segments"][-1]
        prior = [b for b in show.beats[last["episode"]]
                 if b["kind"] != "SOUND FX" and last["start"] - EPS <= b["start"] < cb["start"]]
        if prior:
            story_end = prior[-1]
    cliff = llm.get("cliffhanger_text") or (say(story_end) + (" (+ music sting)" if story_end is not cb else ""))
    if llm.get("why"):
        why = llm["why"]
    else:
        s0 = c["segments"][0]["start"]
        bits = [f"{hb['hook_type']} in the first {max(hb['start'] - s0, 0) + 1:.0f}s ({short(hb)})" if hb
                else "no clear hook in 3 s"]
        nxt = next_beat(show, c)
        tail = f"ends on {cb['cliff_type']}"
        if nxt and nxt["intensity"] >= 0.35:
            tail += f", cut just before {short(nxt)}"
        bits.append(tail)
        if c["unknown_names"]:
            bits.append(f"but names a stranger may not know ({', '.join(c['unknown_names'][:3])})")
        elif c["lead_frac"] >= 0.5:
            bits.append("stays on the leads, so no backstory is needed")
        why = "; ".join(bits)
        why = why[0].upper() + why[1:] + "."
    flags = []
    if c["gore_beats"] >= 2:
        flags.append("graphic violence/blood: check ad policy")
    if c["sexual"]:
        flags.append("sexual content: likely not ad-safe")
    if c["unknown_names"]:
        flags.append("unintroduced names: " + ", ".join(c["unknown_names"]))
    if len(c["segments"]) > 1:
        flags.append(f"{len(c['segments'])}-segment edit: check visual continuity at the join")
    stage = "acquisition (early/free episodes, no big spoilers)" if c["position"] <= 0.3 else \
        ("mid-funnel" if c["position"] <= 0.6 else "retargeting (late-arc payoff, spoils twists)")
    return {"hook": hook, "cliffhanger": cliff, "why": why, "flags": flags, "funnel": stage}


# ----------------------------------------------------------------------------------- run
def premise_of(show: Show) -> str:
    return " ".join(e["logline"] for e in show.eps[:3])[:900]


def run(input_dir: str, llm: LLM, top_k: int = 30, log=print, funnel_weight: float = 0.08) -> dict:
    show = Show(input_dir, llm, log)
    log(f"parsed {len(show.eps)} episodes, {sum(len(b) for b in show.beats.values())} beats; leads={show.leads}")
    premise = premise_of(show)
    if llm.enabled:
        log(f"LLM beat tagging with {llm.describe()} ...")
        llm_tag(show, premise)
    cands = candidates(show)
    log(f"{len(cands)} candidate promos generated (all pass length + boundary rules by construction)")
    # Rules cannot verify that two clips from different episodes tell one story, so without an LLM judge
    # cross-episode edits go to a separate 'variants' list instead of competing in the main ranking.
    main_pool = cands if llm.enabled else [c for c in cands if c["kind"] != "cross-episode"]
    chosen = select(main_pool, k=max(top_k * 2 if llm.enabled else top_k, top_k))
    variants = [] if llm.enabled else select([c for c in cands if c["kind"] == "cross-episode"], k=10)
    if llm.enabled:
        log(f"LLM judging {len(chosen)} shortlisted promos ...")
        llm_judge(show, chosen, premise)
        chosen = sorted(chosen, key=lambda c: -c["score"])[:top_k]
    # Posting order = quality score + funnel bonus: promos from early (free) episodes send a new viewer to
    # content they can watch right away and spoil nothing, so they go out first. Kept separate from quality.
    for c in chosen:
        c["quality"] = c["score"]
        c["post_score"] = round(c["score"] + funnel_weight * (1 - c["position"]), 4)
    chosen.sort(key=lambda c: -c["post_score"])
    by_hook = defaultdict(list)
    for c in sorted(main_pool, key=lambda c: -c["score"]):
        by_hook[c["segments"][0]["beat_from"]].append(c)
    for c in chosen:
        c["alternates"] = [a for a in by_hook[c["segments"][0]["beat_from"]]
                           if a is not c and overlap(a, c) < 0.95][:2]
    promos = [package(show, c, rank, "P") for rank, c in enumerate(chosen, 1)]
    variant_list = [package(show, c, rank, "V") for rank, c in enumerate(variants, 1)]
    stats = {"episodes": len(show.eps), "candidates": len(cands), "provider": llm.describe(),
             "llm_calls": llm.calls, "llm_cache_hits": llm.cache_hits,
             "tokens_in": llm.tokens_in, "tokens_out": llm.tokens_out, "llm_tagged_episodes": show.llm_tagged}
    return {"promos": promos, "variants": variant_list, "stats": stats, "show": show, "all_candidates": cands}


def seg_out(segs):
    return [{"episode": s["episode"], "start": tc(s["start"]), "end": tc(s["end"]),
             "start_s": s["start"], "end_s": s["end"]} for s in segs]


def package(show: Show, c: dict, rank: int, prefix: str) -> dict:
    d = describe(show, c)
    return {
        "rank": rank, "id": f"{prefix}{rank:02d}", "score": c.get("post_score", c["score"]),
        "quality": c.get("quality", c["score"]), "kind": c["kind"],
        "duration_s": c["length"], "segments": seg_out(c["segments"]),
        "hook": d["hook"], "cliffhanger": d["cliffhanger"], "why": d["why"],
        "funnel": d["funnel"], "flags": d["flags"],
        "components": {k: c[k] for k in ("hook", "cliff", "body", "standalone")},
        # same hook, different ending/length: ready-made A/B variants for the editor
        "alternate_cuts": [{"duration_s": a["length"], "quality": a["score"], "segments": seg_out(a["segments"]),
                            "cliffhanger": describe(show, a)["cliffhanger"]} for a in c.get("alternates", [])],
        **({"llm": c["llm"]} if "llm" in c else {}),
    }
