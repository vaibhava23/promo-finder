"""Dry-run the LLM path with a counting mock: real prompts, fake answers -> exact call count & token estimate."""
import json, re, sys, tempfile
sys.path.insert(0, ".")
from promo.llm import LLM
from promo.pipeline import run
stats = {"tag_calls": 0, "judge_calls": 0, "chars_in": 0, "chars_out": 0}
def fake(prompt, system):
    stats["chars_in"] += len(prompt) + len(system)
    if "For EVERY beat id" in prompt:
        stats["tag_calls"] += 1
        ids = re.findall(r"^(E\d+-B\d+) \|", prompt, re.M)
        out = json.dumps({"beats": [{"id": i, "hook": 5, "cliff": 5, "context": 3} for i in ids]})
    else:
        stats["judge_calls"] += 1
        out = json.dumps({"hook_3s": 6, "cliffhanger": 6, "standalone": 6, "trope_clarity": 6, "hook": "x" * 60,
                          "cliffhanger_text": "x" * 60, "why": "x" * 140, "ad_safe": True})
    stats["chars_out"] += len(out)
    return out
with tempfile.TemporaryDirectory() as td:
    run(sys.argv[1], LLM({"provider": "mock", "mock_fn": fake, "cache_dir": td}), top_k=30, log=lambda m: None)
tin, tout = stats["chars_in"] / 4, stats["chars_out"] / 4
print(json.dumps({**stats, "est_tokens_in": int(tin), "est_tokens_out": int(tout)}, indent=1))
# public list prices per 1M tokens (in/out), for scale only; check current pricing before relying on them
for name, pin, pout in [("Gemini Flash-class (free tier available)", 0.10, 0.40), ("GPT-4o-mini-class", 0.15, 0.60),
                        ("Claude Sonnet-class", 3.0, 15.0)]:
    print(f"{name:42s} ~${(tin * pin + tout * pout) / 1e6:.3f} per show")
