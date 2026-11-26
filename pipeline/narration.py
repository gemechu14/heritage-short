"""Narration stage: one WAV per shot, cached by a hash of its inputs.

Change one narration line and re-run: only that shot calls the TTS model again.

Run: python -m pipeline.narration
Writes: outputs/narration/<shot>_<hash>.wav and outputs/narration/manifest.json
"""
import json
import re
import wave

from pipeline.common import OUTPUTS, env, gemini_tts, input_hash, log_call
from pipeline.validate import load_storyboard

OUT = OUTPUTS / "narration"
TARGET_S = 7.0  # user test 1: one spoken line should stay under 7 seconds


def wav_seconds(path):
    with wave.open(str(path), "rb") as w:
        return round(w.getnframes() / w.getframerate(), 2)


def main():
    sb, _, _ = load_storyboard()
    model = env("GEMINI_TTS_MODEL", "gemini-3.8-flash-tts")
    voice = sb["voice"]["name"]
    # TTS_STYLE=on sends the storyboard's style as "Say <style>: <line>" (an A/B experiment);
    # off (default) sends the line alone. The choice is part of the cache key.
    style = ""
    if env("TTS_STYLE", "off") == "on":
        style = re.sub(r"^(speak|say)\s+", "", sb["voice"]["style"].strip().rstrip("."), flags=re.I)
    OUT.mkdir(parents=True, exist_ok=True)

    manifest, generated, cached = {}, 0, 0
    for shot in sb["shots"]:
        text = shot["narration"].strip()
        if not text:
            print(f"{shot['id']}: no narration yet (run python -m pipeline.script)")
            continue
        key = input_hash({"text": text, "voice": voice, "model": model, **({"style": style} if style else {})})
        path = OUT / f"{shot['id']}_{key}.wav"
        if path.exists():
            cached += 1
            log_call(stage="narration", provider="cache", model=model, shot=shot["id"], cache_hit=True,
                     input_hash=key, output=str(path))
            status = "cached   "
        else:
            gemini_tts(model, text, path, voice=voice, style=style, stage="narration", shot=shot["id"])
            generated += 1
            status = "generated"
        secs = wav_seconds(path)
        manifest[shot["id"]] = {"file": path.name, "seconds": secs, "hash": key}
        if secs > shot["duration_s"]:
            warn = "  <-- longer than shot!"
        elif secs > TARGET_S:
            warn = f"  <-- over {TARGET_S:.0f}s target, shorten the line"
        else:
            warn = ""
        print(f"{shot['id']}: {status} {secs:5.2f}s / shot {shot['duration_s']}s{warn}")

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    over = [k for k, v in manifest.items() if v["seconds"] > TARGET_S]
    print(f"\n{generated} generated, {cached} from cache.")
    if over:
        print(f"Over {TARGET_S:.0f}s: {', '.join(over)}. Shorten these before the radio cut.")


if __name__ == "__main__":
    main()
