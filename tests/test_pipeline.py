"""Run: python -m pytest -q   (or: python tests/test_pipeline.py)
Uses the real input pack if PROMO_INPUT points at it; otherwise a synthetic 3-episode show in tests/fixtures."""
import json, os, re, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from promo.llm import LLM, extract_json
from promo.parse import parse_dir
from promo.pipeline import run

FIX = Path(__file__).parent / "fixtures" / "mini_show"
INPUT = os.getenv("PROMO_INPUT", str(FIX))


def assert_valid(res, input_dir):
    eps = {e["number"]: e for e in parse_dir(input_dir)}
    for p in res["promos"] + res.get("variants", []):
        total = sum(s["end_s"] - s["start_s"] for s in p["segments"])
        assert 20 - 1e-6 <= total <= 60 + 1e-6, (p["id"], total)
        assert abs(total - p["duration_s"]) < 0.05
        for s in p["segments"]:
            e = eps[s["episode"]]
            assert 0 <= s["start_s"] < s["end_s"] <= e["duration"] + 0.5
            for b in e["blocks"]:
                if b["kind"] != "DIALOGUE":
                    continue
                for t in (s["start_s"], s["end_s"]):
                    assert not (b["start"] < t - 0.05 and b["end"] > t + 0.05), (p["id"], "cuts line", b["text"])
        assert p["hook"] and p["cliffhanger"] and p["why"]
    ranks = [p["rank"] for p in res["promos"]]
    assert ranks == list(range(1, len(ranks) + 1))


def test_extract_json_variants():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Sure! Here you go: {"a": {"b": "x}y"}} hope that helps') == {"a": {"b": "x}y"}}
    assert extract_json('[{"id": 1}]') == [{"id": 1}]


def test_heuristic_run_obeys_rules():
    res = run(INPUT, LLM({"provider": "heuristic"}), top_k=30, log=lambda m: None)
    assert res["promos"], "no promos found"
    assert_valid(res, INPUT)


def test_llm_path_with_mock_model():
    """Exercises the full LLM path (tagging + judging + caching) with a fake model, including junk replies."""
    calls = {"n": 0}

    def fake(prompt, system):
        calls["n"] += 1
        if "For EVERY beat id" in prompt:
            ids = re.findall(r"^(E\d+-B\d+) \|", prompt, re.M)
            if calls["n"] == 1:
                return "I think these are great beats!"  # invalid -> must retry
            return "```json\n" + json.dumps({"beats": [{"id": i, "hook": 7 if "!" in prompt else 4,
                                                          "cliff": 5, "context": 2} for i in ids]}) + "\n```"
        return json.dumps({"hook_3s": 8, "cliffhanger": 7, "standalone": 6, "trope_clarity": 7,
                           "hook": "A slap", "cliffhanger_text": "A door bursts open", "why": "Because.",
                           "ad_safe": True})

    with tempfile.TemporaryDirectory() as td:
        llm = LLM({"provider": "mock", "mock_fn": fake, "cache_dir": td})
        res = run(INPUT, llm, top_k=10, log=lambda m: None)
        assert_valid(res, INPUT)
        assert res["stats"]["llm_tagged_episodes"] >= 1
        assert all("llm" in p for p in res["promos"])
        n_first = llm.calls
        llm2 = LLM({"provider": "mock", "mock_fn": fake, "cache_dir": td})
        run(INPUT, llm2, top_k=10, log=lambda m: None)
        assert llm2.calls == 0 and llm2.cache_hits >= n_first - 1, "second run should be fully cached"


def test_format_variants_parse():
    """Uppercase headers, missing logline, (O.S.) and (V.O.) tags, CRLF line endings."""
    txt = ("EPISODE NUMBER: Episode 1\r\n\r\n--- SCRIPT START ---\r\nSCENE 01\r\nSCENE HEADING: INT. ROOM - DAY\r\n"
           "SCENE START: 00:00.00\r\nSCENE END: 00:30.00\r\n\r\n**ACTION:**\r\nStart: (00:00.00) | End: (00:02.00)\r\n"
           "She slaps him.\r\n\r\n**JOHN (V.O.) (Furious):**\r\nStart: (00:02.00) | End: (00:04.00)\r\n\"How dare you!\"\r\n")
    with tempfile.TemporaryDirectory() as td:
        Path(td, "episode-001-x.txt").write_text(txt)
        eps = parse_dir(td)
        assert len(eps) == 1 and len(eps[0]["blocks"]) == 2
        d = eps[0]["blocks"][1]
        assert d["speaker"] == "JOHN" and d["offscreen"] and d["tone"] == "Furious" and d["text"] == "How dare you!"
        assert eps[0]["duration"] == 30.0


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("ok", name)
