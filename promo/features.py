"""Rule-based beat scoring: hook / cliffhanger / intensity / context / safety for every beat.

A "beat" is any non-CAMERA block (dialogue, action, sound FX). Camera lines describe framing,
not story, so they never decide a cut, but they still count toward duration.
Every weight here is a plain number in WEIGHTS so it can be tuned and explained.
"""
from __future__ import annotations

import re
from collections import Counter

HIGH_TONE = {
    "screaming": 1.0, "shrieking": .9, "hysterical": .9, "roaring": .9, "enraged": 1.0, "furious": .9,
    "outraged": .8, "shouting": .8, "bellowing": .8, "thunderous": .7, "booming": .6, "venomous": .8,
    "cruel": .8, "vicious": .8, "malicious": .7, "sadistic": .9, "gloating": .7, "mocking": .7,
    "taunting": .7, "threatening": .9, "menacing": .9, "deadly": .9, "lethal": .9, "dangerous": .8,
    "chilling": .8, "sinister": .8, "ominous": .6, "shocked": .8, "horrified": .8, "stunned": .6,
    "gasping": .6, "devastated": .7, "terrified": .8, "panicked": .8, "panic-stricken": .8,
    "frantic": .7, "desperate": .7, "pleading": .5, "begging": .6, "sobbing": .5, "weeping": .5,
    "wailing": .7, "heartbroken": .5, "anguished": .6, "agonized": .7, "betrayed": .7,
    "accusing": .7, "accusatory": .7, "condemning": .7, "damning": .8, "revelatory": .8,
    "incredulous": .5, "disbelieving": .5, "defiant": .6, "fierce": .6, "scornful": .6,
    "derisive": .6, "spiteful": .6, "vindictive": .7, "ruthless": .7, "callous": .6, "cold": .45,
    "smug": .5, "triumphant": .5, "alarmed": .6, "seething": .8, "dark": .4, "brutal": .8,
    "imperious": .5, "demanding": .5, "commanding": .4, "harsh": .5, "scathing": .6, "piercing": .6,
    "unhinged": .9, "denial": .6, "trembling": .4, "breathless": .4, "choked": .4, "shattered": .6,
}
CALM_TONE = {"gentle", "soft", "softly", "tender", "warm", "calm", "reassuring", "quiet", "playful",
             "teasing", "amused", "fond", "relieved", "grateful", "peaceful", "content", "comforting",
             "loving", "sweet", "smiling", "nostalgic", "reflective", "humble", "polite", "modest",
             "instructional", "knowledgeable", "lighthearted", "charming", "droll", "dry", "formal"}

STAKES = re.compile(
    r"\b(marry|marrying|married|marriage|wedding|bride|husband|wife|sister|father|mother|son|daughter|"
    r"dead|died|die|dying|alive|kill\w*|murder\w*|hang\w*|gallows|execut\w*|noose|poison\w*|arsenic|"
    r"witch\w*|arrest\w*|stole|steal|thief|traitor|betray\w*|duke|duchess|grace|impost[eo]r|lie|lying|"
    r"liar|blood|burn\w*|crawl|beg|disowned|worthless|beggar|nobody|never|enemy|prison|chains?|"
    r"invalid|lawful|title|inheritance|revoked|guards?)\b", re.I)
PHYSICAL = re.compile(
    r"\b(strikes?|struck|slap\w*|slams?|grabs?|drags?|yanks?|shoves?|throws?|flings?|hurls?|"
    r"explod\w*|explosion|detonat\w*|bursts?|kneels?|drops to (?:one|her|his) knee|collapses?|crash\w*|"
    r"lunges?|tackl\w*|chok\w*|punch\w*|whip\w*|crop|shackl\w*|seiz\w*|kiss\w*|rips?|tears? (?:off|away)|"
    r"fireball|smash\w*|blood\w*|bleeding|fire|flames?|inferno|branding|iron)\b", re.I)
SFX_STRONG = re.compile(r"(crash|slam|explosion|detonation|gasp|crack|scream|pounding|shatter|bang|"
                        r"whip|thud|clang|bursts?|violent|ear-splitting)", re.I)
CLIFF_TEXT = re.compile(
    r"(\?|\.\.\.$|—$|\b(before|tomorrow|tonight|two days|ten days|unless|or (?:your|he|she|watch)|"
    r"who are you|what is your|where did you|who gave|is coming|coming home|you will|i will|"
    r"we settle|it's beginning|i'm next|take her|arrest)\b)", re.I)
CLIFF_CUE = re.compile(r"(cliffhanger|sting|freez|cut(?:s|ting)? (?:sharply |abruptly )?to black|holds? on|"
                       r"unresolved|abrupt|ominous)", re.I)
INTERRUPT = re.compile(r"(door|latch|hinges|footsteps|pounding|knock|burst|bells? (?:begin|toll))", re.I)
RESOLVE_TEXT = re.compile(r"\b(thank you|i've got you|are you hurt|i'm here|i am here|i have come home|you're safe|you are safe|it's over|it is over|"
                          r"you saved|saved him|saved her|i accept|let us proceed|we are leaving|"
                          r"fever.{0,10}breaking|we begin again|rest now)\b", re.I)
# comfort / union images close the tension instead of opening it
RESOLVE_ACTION = re.compile(r"\b(gaze[sd]? (?:deeply )?into each other|embrace|embraces|holds? her (?:safe|close|tight)|"
                            r"rests? (?:her|his) (?:head|cheek)|smil(?:es|ing) (?:softly|warmly)|sinks into|"
                            r"bond forming|fade[sd]? (?:out|to black)|foreheads? pressed)\b", re.I)
GORE = re.compile(r"\b(blood\w*|bleeding|gash\w*|lacerat\w*|flesh|branding|searing|scald\w*|"
                  r"torture\w*|corpse|slicing|torn fingers|wounds?)\b", re.I)
SEXUAL = re.compile(r"\b(naked|shirtless|bare skin|carnal|seductive|illicit|forbidden entanglement|"
                    r"passionate embrace|lying flat on his back|in this bed)\b", re.I)
CONTINUES = re.compile(r"^(\.\.\.|…|and |but |then |so )", re.I)

WEIGHTS = {
    # beat-level
    "tone": 0.45, "stakes": 0.12, "stakes_cap": 0.30, "punchy": 0.10, "exclaim": 0.06,
    "physical_action": 0.70, "sfx_strong": 0.50, "calm_penalty": 0.25,
    "cliff_question": 0.30, "cliff_text": 0.20, "cliff_cue": 0.45, "interrupt": 0.30,
    "ep_end": 0.35, "payoff_next": 0.35, "resolve_penalty": 0.45, "continued_penalty": 0.35,
    # window-level
    "w_hook": 0.34, "w_cliff": 0.34, "w_body": 0.12, "w_standalone": 0.20,
    "segment_penalty": 0.04, "gore_penalty": 0.10, "sexual_penalty": 0.35,
    "unknown_name_penalty": 0.06, "no_lead_penalty": 0.25, "early_bonus": 0.04,
    "generic_factor": 0.45, "reveal": 0.18, "logline": 0.30,
}

STOP = set("""a an the and or but of to in on at for with from by as is are was were be been being it its this that
these those he she they them his her their him you your i me my we our us who whom whose which what when where why
how not no so if then than too very can could will would shall should may might must do does did done have has had
having into onto over under after before about against between through during without within upon only just also
even still yet again once all any each every some such own same other more most much many few one two three
her herself himself themselves itself yourself myself ourselves there here out up down off""".split())

REVEAL = re.compile(r"\b(?:is|are|was|am|were|be)\s+(?:my|your|his|her|the|a|no|not|never|already|being)?\s*"
                    r"(?:lost |rightful |true |lawful |late |real )?(?:son|duke|duchess|wife|husband|dead|alive|"
                    r"marrying|poison\w*|witch|traitor|imposter|lie|thief|innocent|condemned|executed|arrested)\b"
                    r"|\byour grace\b|\bsomeone (?:is|has been) \w+ing\b|\bunder arrest\b|\bit'?s you\b|"
                    r"\b(?:they|he|she) (?:condemned|arrested|poisoned|framed|stole|took)\b", re.I)


def content_words(text: str) -> set[str]:
    return {stem(w) for w in re.findall(r"[a-z']+", (text or "").lower()) if len(w) > 2 and w not in STOP}


def stem(w: str) -> str:
    for suf in ("ing", "ed", "es", "s", "ly"):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[: -len(suf)]
    return w


def tone_score(tone: str) -> tuple[float, bool]:
    words = [w.strip(" .").lower() for w in re.split(r"[,/;]| and ", tone or "") if w.strip()]
    hi = [HIGH_TONE[w] for w in words if w in HIGH_TONE]
    calm = any(w in CALM_TONE for w in words) and not hi
    return (max(hi) if hi else 0.0), calm


def build_beats(ep: dict) -> list[dict]:
    beats = [dict(b) for b in ep["blocks"] if b["kind"] != "CAMERA"]
    beats.sort(key=lambda b: (b["start"], b["end"]))
    return beats


def lead_names(eps: list[dict], k: int = 2) -> list[str]:
    """Protagonists = most frequent dialogue speakers after folding titles (LADY JULIANA -> JULIANA)."""
    c = Counter()
    for e in eps:
        for b in e["blocks"]:
            if b["kind"] == "DIALOGUE":
                c[fold_name(b["speaker"])] += 1
    return [n for n, _ in c.most_common(k)]


def fold_name(name: str) -> str:
    n = re.sub(r"^(LADY|LORD|SIR|THE|MR\.?|MRS\.?|MISS|DUKE|DUCHESS)\s+", "", (name or "").upper()).strip()
    return n


def score_beats(ep: dict, leads: list[str]) -> list[dict]:
    W = WEIGHTS
    beats = build_beats(ep)
    dur = ep["duration"]
    log_words = content_words(ep.get("logline", "")) - {stem(l.lower()) for l in leads}
    for b in beats:
        text = b["text"] or ""
        t, calm = tone_score(b.get("tone", ""))
        stakes = min(len(STAKES.findall(text)) * W["stakes"], W["stakes_cap"])
        words = len(text.split())
        intensity, hook, cliff = 0.0, 0.0, 0.0
        cw = content_words(text)
        sal = len(cw & log_words) / max(min(len(cw), 6), 1) if log_words else 0.0
        b["logline_sal"] = round(min(sal, 1.0), 3)
        if b["kind"] == "DIALOGUE":
            reveal = W["reveal"] if REVEAL.search(text) else 0.0
            # a shout with no information ("Silence!", "Alexander!") is not a hook on its own
            generic = len(cw) <= 1 and not stakes and not reveal
            intensity = W["tone"] * t + stakes + reveal + (W["exclaim"] if "!" in text else 0)
            if generic:
                intensity *= W["generic_factor"]
            hook = intensity + (W["punchy"] if 0 < words <= 9 and not generic else 0)
            if calm:
                hook -= W["calm_penalty"]
                intensity -= W["calm_penalty"] / 2
            if text.rstrip().endswith("?"):
                cliff += W["cliff_question"]
            if CLIFF_TEXT.search(text):
                cliff += W["cliff_text"]
            cliff += 0.5 * intensity
        elif b["kind"] == "ACTION":
            phys = len(PHYSICAL.findall(text))
            intensity = min(phys, 2) * W["physical_action"] / 2 + stakes / 2
            hook = intensity
            cliff = 0.4 * intensity + (W["cliff_cue"] if CLIFF_CUE.search(text) else 0)
        else:  # SOUND FX
            intensity = W["sfx_strong"] if SFX_STRONG.search(text) else 0.05
            hook = intensity
            cliff = (W["cliff_cue"] if CLIFF_CUE.search(text) else 0) + \
                    (W["interrupt"] if INTERRUPT.search(text) else 0)
        if b["kind"] != "SOUND FX" and INTERRUPT.search(text) and re.search(r"burst|open|pound|coming", text, re.I):
            cliff += W["interrupt"]
        b["resolves"] = bool((b["kind"] == "ACTION" and RESOLVE_ACTION.search(text)) or RESOLVE_TEXT.search(text))
        if b["kind"] == "ACTION" and RESOLVE_ACTION.search(text):
            cliff -= W["resolve_penalty"]
        if RESOLVE_TEXT.search(text):
            cliff -= W["resolve_penalty"]
            intensity -= 0.1
        boost = W["logline"] * b["logline_sal"]
        intensity, hook, cliff = intensity + boost / 2, hook + boost, cliff + boost / 2
        b["intensity"] = round(max(intensity, 0.0), 3)
        b["hook"] = round(max(hook, 0.0), 3)
        b["cliff_base"] = cliff
        b["gore"] = bool(GORE.search(text))
        b["sexual"] = bool(SEXUAL.search(text))
        upper = text.upper()
        b["has_lead"] = any(fold_name(b.get("speaker") or "") == l or re.search(rf"\b{re.escape(l)}\b", upper)
                            for l in leads)
        b["continues_prev"] = bool(CONTINUES.match(text.strip()))
    # context-dependent cliff features
    for i, b in enumerate(beats):
        if b["kind"] == "SOUND FX":
            # a music sting cannot turn a resolved moment into a cliffhanger
            prev = next((p for p in reversed(beats[:i]) if p["kind"] != "SOUND FX"), None)
            if prev is not None and prev.get("resolves"):
                b["cliff_base"] -= W["resolve_penalty"] + W["cliff_cue"]
        nxt = beats[i + 1:i + 3]
        payoff = max((n["intensity"] for n in nxt), default=0.0)
        # cutting right before a payoff only builds suspense if this beat is itself tense or a question
        tension = min(1.0, b["intensity"] / 0.3 + (0.6 if (b["text"] or "").rstrip().endswith("?") else 0))
        cliff = b["cliff_base"] + W["payoff_next"] * payoff * tension
        if dur - b["end"] <= 8:
            cliff += W["ep_end"]
        # a line that a later beat continues ("...") is a mid-thought cut
        if nxt and nxt[0]["kind"] == "DIALOGUE" and nxt[0]["continues_prev"] \
                and nxt[0].get("speaker") == b.get("speaker"):
            cliff -= W["continued_penalty"]
        b["cliff"] = round(max(cliff, 0.0), 3)
        b["hook_type"] = hook_type(b)
        b["cliff_type"] = cliff_type(b, dur)
        if b["continues_prev"]:
            b["hook"] = round(max(b["hook"] - W["continued_penalty"], 0.0), 3)
    return beats


def hook_type(b: dict) -> str:
    t = b["text"] or ""
    if b["kind"] in ("ACTION", "SOUND FX") and (PHYSICAL.search(t) or SFX_STRONG.search(t)):
        return "physical moment"
    if re.search(r"\b(marr(?:y|ying|ied|iage)|dead|died|alive|poison\w*|arsenic|duke|grace|witch\w*|arrest\w*|"
                 r"stole|steal\w*|sold|betray\w*|lie|liar|son|ring|imposter|traitor|condemn\w*)\b", t, re.I):
        return "reveal / accusation"
    if re.search(r"\b(hang|kill|crawl|burn|disappear|gallows|execut)", t, re.I):
        return "threat"
    if t.strip().endswith("?"):
        return "loaded question"
    return "shocking line"


def cliff_type(b: dict, dur: float) -> str:
    t = b["text"] or ""
    if (INTERRUPT.search(t) and b["kind"] != "DIALOGUE") or re.search(r"\b(someone is coming|who goes there|"
                                                                          r"they're here|open the door)\b", t, re.I):
        return "interruption"
    if t.strip().endswith("?"):
        return "unanswered question"
    if re.search(r"\b(hang|gallows|execut|kill|before|tomorrow|days|coming|will)\b", t, re.I):
        return "threat / vow with a deadline"
    if dur - b["end"] <= 8:
        return "episode-ending sting"
    return "unresolved moment"


UNKNOWN_NAME = re.compile(r"\b([A-Z][a-z]{3,})\b")
COMMON = set("""Your Grace Lady Lord Father Mother Sister Duke Duchess God Please Then There This That What When
Where Why Who How Look Stop Enough Yes Good Come Leave Take Give Tell Keep Let Not Now Perhaps Because Every Today
Tomorrow Before After Only Even Still Just Some None Nothing Never Always Once Here Help Wait Show Read Bring
Send Guards Your Grace Crown Majesty King Queen Sir Madam Ma'am Honor Captain Miss Darling Dear Oh Ah Ahh Ahhh No
Gentlemen Ladies Everyone Anyone Someone People Without Into Over Under Since Until While Whatever However""".split())


def unknown_names(beats: list[dict], leads: list[str]) -> set[str]:
    """Proper names a stranger meets without introduction (excluding leads and common words)."""
    names = set()
    leadset = {l.title() for l in leads}
    for b in beats:
        if b["kind"] != "DIALOGUE":
            continue
        words = (b["text"] or "").split()
        for m in UNKNOWN_NAME.finditer(b["text"] or ""):
            w = m.group(1)
            if w in COMMON or w in leadset:
                continue
            # skip sentence-initial capitalised ordinary words
            if words and words[0].strip("\"'.,!?") == w and w.lower() in COMMON_LOWER:
                continue
            names.add(w)
    return names


COMMON_LOWER = {w.lower() for w in COMMON} | set(
    "they you she he it we our my his her their those these which whose about after again against all also "
    "already another because been being both cannot could did does doing done down each either else enough "
    "ever every first from have having into just like made make many maybe more most much must myself "
    "next none once only other ours ourselves over same should since some such than that their them then "
    "there these they this those through together under until upon very want was were what when where "
    "which while whom whose will with without would yours yourself".split())
