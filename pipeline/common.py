"""Shared helpers for every stage: config, runs.jsonl logging, hashing, retries, provider calls.

Secrets are read from .env and never written to logs.
"""
import base64
import hashlib
import json
import os
import re
import time
import uuid
import wave
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

RUNS = ROOT / "runs.jsonl"
OUTPUTS = ROOT / "outputs"
RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]

RETRY_STATUS = {429, 500, 502, 503, 504}
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"


def env(name, default=None, required=False):
    value = os.getenv(name, default)
    if required and not value:
        raise SystemExit(f"Missing {name} in .env")
    return value


def log_call(**fields):
    """Append one line per model call to runs.jsonl."""
    record = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "run_id": RUN_ID,
        **fields,
    }
    with RUNS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def input_hash(obj):
    """Stable short hash of a stage's inputs, used as the cache key."""
    blob = json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


def request_with_retry(method, url, *, attempts=3, timeout=180, **kwargs):
    """Retry on rate limits, server errors and dropped connections, with backoff."""
    last_exc = None
    for i in range(1, attempts + 1):
        try:
            r = requests.request(method, url, timeout=timeout, **kwargs)
            if r.status_code not in RETRY_STATUS or i == attempts:
                return r, i
        except requests.RequestException as exc:
            last_exc = exc
            if i == attempts:
                raise
        time.sleep(2 ** i)
    raise RuntimeError(f"request failed: {last_exc}")


# ---------- Gemini ----------

def _gemini_headers():
    return {"x-goog-api-key": env("GEMINI_API_KEY", required=True), "Content-Type": "application/json"}


def _clean_model(name):
    return name.removeprefix("models/")


def gemini_list_models():
    t0 = time.time()
    r, tries = request_with_retry("GET", f"{GEMINI_BASE}/models", headers=_gemini_headers(), params={"pageSize": 1000})
    log_call(stage="smoke", provider="gemini", model="list_models", params={}, seed=None,
             latency_s=round(time.time() - t0, 2), attempts=tries, status=r.status_code, cost_usd=0.0,
             error=None if r.ok else r.text[:300])
    r.raise_for_status()
    return [m for m in r.json().get("models", []) if "generateContent" in m.get("supportedGenerationMethods", [])]


def gemini_text(model, prompt, *, stage, temperature=0.4):
    model = _clean_model(model)
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": temperature}}
    t0 = time.time()
    try:
        r, tries = request_with_retry("POST", f"{GEMINI_BASE}/models/{model}:generateContent",
                                      headers=_gemini_headers(), json=payload)
    except requests.RequestException as exc:  # timeouts and dropped connections are logged too
        log_call(stage=stage, provider="gemini", model=model, params={"temperature": temperature}, seed=None,
                 latency_s=round(time.time() - t0, 2), attempts=3, status=None, cost_usd=0.0,
                 prompt_chars=len(prompt), error=f"{type(exc).__name__}: {str(exc)[:250]}")
        raise
    latency = round(time.time() - t0, 2)
    text = None
    if r.ok:
        parts = r.json()["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
    log_call(stage=stage, provider="gemini", model=model, params={"temperature": temperature}, seed=None,
             latency_s=latency, attempts=tries, status=r.status_code, cost_usd=0.0,
             prompt_chars=len(prompt), error=None if r.ok else r.text[:300])
    if not r.ok:
        raise RuntimeError(f"Gemini text {r.status_code}: {r.text[:300]}")
    return text


def gemini_tts(model, text, out_path, *, voice="Kore", style="", stage="narration", shot=None):
    """Generate speech and save it as a 16-bit mono WAV. Returns duration in seconds.

    By default only the narration line is sent: a style instruction in front of it was read
    aloud as part of the speech (user test 1). Pass `style` to test the "Say <style>: <text>"
    form the Gemini TTS docs recommend (see EXPERIMENTS.md).
    """
    model = _clean_model(model)
    spoken = f"Say {style}: {text}" if style else text
    payload = {
        "contents": [{"parts": [{"text": spoken}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}},
        },
    }
    t0 = time.time()
    try:
        r, tries = request_with_retry("POST", f"{GEMINI_BASE}/models/{model}:generateContent",
                                      headers=_gemini_headers(), json=payload)
    except requests.RequestException as exc:
        log_call(stage=stage, provider="gemini", model=model, shot=shot, params={"voice": voice, "style": style},
                 seed=None, latency_s=round(time.time() - t0, 2), attempts=3, status=None, cost_usd=0.0,
                 error=f"{type(exc).__name__}: {str(exc)[:250]}")
        raise
    latency = round(time.time() - t0, 2)
    duration, error = None, None
    inline = None
    if r.ok:
        try:
            inline = r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]
        except (KeyError, IndexError, ValueError):
            error = f"200 but no audio in response: {r.text[:300]}"
    else:
        error = r.text[:300]
    if inline:
        pcm = base64.b64decode(inline["data"])
        match = re.search(r"rate=(\d+)", inline.get("mimeType", ""))
        rate = int(match.group(1)) if match else 24000
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(out_path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(pcm)
        duration = round(len(pcm) / 2 / rate, 2)
    log_call(stage=stage, provider="gemini", model=model, shot=shot,
             params={"voice": voice, "style": style}, seed=None, latency_s=latency, attempts=tries,
             status=r.status_code, cost_usd=0.0, audio_s=duration,
             output=str(out_path) if error is None else None, error=error)
    if error is not None:
        raise RuntimeError(f"Gemini TTS {r.status_code}: {error}")
    return duration


# ---------- FFmpeg ----------

def ffmpeg(args, *, stage, shot=None, params=None, output=None, cwd=None, loglevel="error"):
    """Run FFmpeg, log it to runs.jsonl like a model call, and raise with its stderr on failure."""
    import shutil
    import subprocess

    exe = shutil.which("ffmpeg")
    if not exe:
        raise SystemExit("FFmpeg not found on PATH. Install it (winget install Gyan.FFmpeg) and reopen the terminal.")
    t0 = time.time()
    p = subprocess.run([exe, "-y", "-hide_banner", "-loglevel", loglevel, *map(str, args)],
                       capture_output=True, text=True, cwd=cwd)
    log_call(stage=stage, provider="ffmpeg", model="ffmpeg", shot=shot, params=params or {}, seed=None,
             latency_s=round(time.time() - t0, 2), attempts=1, status=p.returncode, cost_usd=0.0,
             output=str(output) if output and p.returncode == 0 else None,
             error=p.stderr[-300:] if p.returncode else None)
    if p.returncode:
        raise RuntimeError(f"ffmpeg failed ({stage} {shot or ''}): {p.stderr[-800:]}")
    return p


# ---------- Cloudflare Workers AI ----------

def cf_image_klein(model, prompt, out_path, *, seed=None, refs=(), width=1024, height=1024, steps=4,
                   stage="keyframes", shot=None):
    """FLUX.2 klein on Workers AI: multipart input, seed, and up to 4 reference images.

    Reference images (input_image_0..3) carry a character's identity from the reference sheet
    into every shot. Note: the same seed gives a similar, not identical, image (EXPERIMENTS.md).
    """
    account = env("CLOUDFLARE_ACCOUNT_ID", required=True)
    token = env("CLOUDFLARE_API_TOKEN", required=True)
    url = f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model}"
    fields = {"prompt": prompt, "width": str(width), "height": str(height), "steps": str(steps)}
    if seed is not None:
        fields["seed"] = str(seed)
    files = {f"input_image_{i}": (Path(p).name, Path(p).read_bytes(), "image/jpeg") for i, p in enumerate(refs[:4])}
    t0 = time.time()
    r, tries = request_with_retry("POST", url, headers={"Authorization": f"Bearer {token}"},
                                  data=fields, files=files or {"_": (None, "")})
    latency = round(time.time() - t0, 2)
    try:
        ok = r.ok and r.json().get("success", False)
    except ValueError:
        ok = False
    if ok:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(base64.b64decode(r.json()["result"]["image"]))
    log_call(stage=stage, provider="cloudflare", model=model, shot=shot,
             params={"steps": steps, "width": width, "height": height,
                     "refs": [Path(p).name for p in refs[:4]]},
             seed=seed, latency_s=latency, attempts=tries, status=r.status_code, cost_usd=0.0,
             prompt_chars=len(prompt), output=str(out_path) if ok else None,
             error=None if ok else r.text[:300])
    if not ok:
        raise RuntimeError(f"Cloudflare {r.status_code}: {r.text[:300]}")
    return out_path


def cf_image(model, prompt, out_path, *, steps=4, seed=None, stage="keyframes", shot=None):
    """Text-to-image on Workers AI. Saves a JPEG and returns its path."""
    account = env("CLOUDFLARE_ACCOUNT_ID", required=True)
    token = env("CLOUDFLARE_API_TOKEN", required=True)
    url = f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model}"
    payload = {"prompt": prompt, "steps": steps}
    if seed is not None:
        payload["seed"] = seed
    t0 = time.time()
    r, tries = request_with_retry("POST", url, headers={"Authorization": f"Bearer {token}"}, json=payload)
    latency = round(time.time() - t0, 2)
    ok = r.ok and r.json().get("success", False)
    if ok:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(base64.b64decode(r.json()["result"]["image"]))
    log_call(stage=stage, provider="cloudflare", model=model, shot=shot,
             params={"steps": steps}, seed=seed, latency_s=latency, attempts=tries,
             status=r.status_code, cost_usd=0.0, prompt_chars=len(prompt),
             output=str(out_path) if ok else None, error=None if ok else r.text[:300])
    if not ok:
        raise RuntimeError(f"Cloudflare {r.status_code}: {r.text[:300]}")
    return out_path
