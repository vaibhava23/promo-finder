"""Model-swappable LLM adapter.

One function, `complete_json(prompt, system)`, used by the whole pipeline. The provider is chosen
in config.yaml (or env PROMO_PROVIDER / PROMO_MODEL), so a stronger model is a one-line change:

  provider: heuristic          # offline, no model; pipeline uses rule-based scores only
  provider: openai_compatible  # Gemini, Groq, OpenRouter, Ollama, OpenAI, vLLM, most vendor APIs
  provider: anthropic          # Claude Messages API
  provider: mock               # canned responses, for tests

Keys are read from the env var named in config (api_key_env); if a proxy injects auth, leave it unset.
Responses are cached on disk by prompt hash so re-runs are free and deterministic.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path

import requests

PRESETS = {  # base URLs of OpenAI-compatible endpoints
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
    "groq": "https://api.groq.com/openai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "ollama": "http://localhost:11434/v1",
    "openai": "https://api.openai.com/v1",
}


class LLMError(RuntimeError):
    pass


def extract_json(text: str):
    """Pull the first JSON object/array out of a model reply (handles ```json fences and chatter)."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    pairs = [(text.find(o), o, c) for o, c in (("{", "}"), ("[", "]")) if text.find(o) != -1]
    for start, opener, closer in sorted(pairs):  # whichever bracket opens first is the outer value
        depth, in_str, esc = 0, False, False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                esc = (ch == "\\") and not esc
                if ch == '"' and not esc:
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    return json.loads(text[start:i + 1])
    raise LLMError(f"no JSON found in reply: {text[:200]!r}")


class LLM:
    def __init__(self, cfg: dict | None = None):
        cfg = dict(cfg or {})
        self.provider = os.getenv("PROMO_PROVIDER", cfg.get("provider", "heuristic"))
        self.model = os.getenv("PROMO_MODEL", cfg.get("model", ""))
        preset = cfg.get("preset")
        self.base_url = os.getenv("PROMO_BASE_URL", cfg.get("base_url") or PRESETS.get(preset or "", ""))
        self.api_key = os.getenv(cfg.get("api_key_env", "PROMO_API_KEY"), "")
        self.temperature = float(cfg.get("temperature", 0.2))
        self.max_tokens = int(cfg.get("max_tokens", 4096))
        self.timeout = int(cfg.get("timeout", 120))
        self.min_interval = float(cfg.get("min_interval_s", 0))  # free tiers: rate-limit politely
        self.cache_dir = Path(cfg.get("cache_dir", ".cache/llm"))
        self.mock_fn = cfg.get("mock_fn")
        self._last = 0.0
        self.calls = 0
        self.cache_hits = 0
        self.tokens_in = 0
        self.tokens_out = 0

    @property
    def enabled(self) -> bool:
        return self.provider != "heuristic"

    def describe(self) -> str:
        return self.provider if not self.enabled else f"{self.provider}:{self.model}"

    # ---- public -------------------------------------------------------------------------
    def complete_json(self, prompt: str, system: str = "", retries: int = 3):
        if not self.enabled:
            raise LLMError("heuristic provider has no model")
        key = hashlib.sha256(json.dumps([self.provider, self.model, system, prompt]).encode()).hexdigest()
        cpath = self.cache_dir / f"{key}.json"
        if cpath.exists():
            self.cache_hits += 1
            return json.loads(cpath.read_text())["parsed"]
        last_err = None
        for attempt in range(retries):
            try:
                text = self._call(prompt, system if attempt == 0 else
                                  system + "\nReturn ONLY valid JSON. No prose, no markdown fences.")
                parsed = extract_json(text)
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                cpath.write_text(json.dumps({"raw": text, "parsed": parsed}, ensure_ascii=False))
                return parsed
            except (LLMError, json.JSONDecodeError, requests.RequestException) as e:
                last_err = e
                time.sleep(min(2 ** attempt * 2, 30))
        raise LLMError(f"{self.describe()} failed after {retries} tries: {last_err}")

    # ---- providers ----------------------------------------------------------------------
    def _throttle(self):
        wait = self.min_interval - (time.time() - self._last)
        if wait > 0:
            time.sleep(wait)
        self._last = time.time()

    def _call(self, prompt: str, system: str) -> str:
        self._throttle()
        self.calls += 1
        if self.provider == "mock":
            return self.mock_fn(prompt, system)
        if self.provider == "openai_compatible":
            return self._openai(prompt, system)
        if self.provider == "anthropic":
            return self._anthropic(prompt, system)
        raise LLMError(f"unknown provider {self.provider!r}")

    def _openai(self, prompt, system):
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        body = {"model": self.model, "temperature": self.temperature, "max_tokens": self.max_tokens,
                "messages": ([{"role": "system", "content": system}] if system else []) +
                            [{"role": "user", "content": prompt}]}
        r = requests.post(f"{self.base_url.rstrip('/')}/chat/completions", json=body, headers=headers,
                          timeout=self.timeout)
        if r.status_code == 429:
            time.sleep(20)
            raise LLMError("rate limited (429)")
        if r.status_code >= 400:
            raise LLMError(f"HTTP {r.status_code}: {r.text[:300]}")
        data = r.json()
        u = data.get("usage") or {}
        self.tokens_in += u.get("prompt_tokens", 0)
        self.tokens_out += u.get("completion_tokens", 0)
        return data["choices"][0]["message"]["content"]

    def _anthropic(self, prompt, system):
        headers = {"content-type": "application/json", "anthropic-version": "2023-06-01"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        body = {"model": self.model, "max_tokens": self.max_tokens, "temperature": self.temperature,
                "messages": [{"role": "user", "content": prompt}]}
        if system:
            body["system"] = system
        base = self.base_url or "https://api.anthropic.com"
        r = requests.post(f"{base.rstrip('/')}/v1/messages", json=body, headers=headers, timeout=self.timeout)
        if r.status_code >= 400:
            raise LLMError(f"HTTP {r.status_code}: {r.text[:300]}")
        data = r.json()
        u = data.get("usage") or {}
        self.tokens_in += u.get("input_tokens", 0)
        self.tokens_out += u.get("output_tokens", 0)
        return "".join(b.get("text", "") for b in data["content"] if b.get("type") == "text")
