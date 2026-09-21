"""Minimal provider clients (stdlib only). Each returns (text, tokens_in, tokens_out)."""
import json, os, urllib.request

def _post(url, headers, body, timeout=60):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

def call(provider, model, system, prompt, max_tokens):
    if provider == "anthropic":
        d = _post("https://api.anthropic.com/v1/messages",
                  {"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"},
                  {"model": model, "max_tokens": max_tokens, "system": system,
                   "messages": [{"role": "user", "content": prompt}]})
        return d["content"][0]["text"].strip(), d["usage"]["input_tokens"], d["usage"]["output_tokens"]
    if provider == "openai":
        d = _post("https://api.openai.com/v1/chat/completions",
                  {"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"]},
                  {"model": model, "max_completion_tokens": max_tokens, "reasoning_effort": "minimal",
                   "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]})
        return d["choices"][0]["message"]["content"].strip(), d["usage"]["prompt_tokens"], d["usage"]["completion_tokens"]
    if provider == "gemini":
        d = _post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key=" + os.environ["GEMINI_API_KEY"], {},
                  {"systemInstruction": {"parts": [{"text": system}]},
                   "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                   "generationConfig": {"maxOutputTokens": max_tokens, "thinkingConfig": {"thinkingBudget": 0}}})
        u = d.get("usageMetadata", {})
        text = "".join(p.get("text", "") for p in d["candidates"][0]["content"]["parts"])
        return text.strip(), u.get("promptTokenCount", 0), u.get("candidatesTokenCount", 0) + u.get("thoughtsTokenCount", 0)
    raise ValueError(f"unknown provider {provider}")
