"""Shared timing: how long each shot really lasts, and the joined narration track.

A shot lasts max(storyboard duration, narration length + LEAD + TAIL), so the picture is cut
to the voice, the way professional editors work. The radio cut, the shots stage and the
assembly stage all use this one function, so their timings always agree.
"""
import json
import wave

from pipeline.common import OUTPUTS

NARR = OUTPUTS / "narration"
LEAD = 0.5   # silence before each line
TAIL = 0.3   # breath after each line before the cut
END_CARD_S = 3.0
FPS = 24


def load_manifest():
    path = NARR / "manifest.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def shot_timeline(sb, manifest=None):
    """Return one dict per shot: id, start, length, speech seconds, narration file (or None)."""
    manifest = load_manifest() if manifest is None else manifest
    t, out = 0.0, []
    for shot in sb["shots"]:
        entry = manifest.get(shot["id"])
        speech = entry["seconds"] if entry else 0.0
        length = max(float(shot["duration_s"]), speech + LEAD + TAIL if entry else 0.0)
        length = round(round(length * FPS) / FPS, 4)  # whole frames
        out.append({"id": shot["id"], "start": round(t, 4), "length": length, "speech": speech,
                    "file": (NARR / entry["file"]) if entry else None})
        t += length
    return out


def total_length(timeline):
    return round(sum(s["length"] for s in timeline), 4)


def write_narration_track(timeline, out_path, rate=24000):
    """Join each shot's narration WAV, placed LEAD seconds into its shot, padded with silence."""
    frames = bytearray()
    for s in timeline:
        speech = b""
        if s["file"]:
            with wave.open(str(s["file"]), "rb") as w:
                if w.getframerate() != rate:
                    raise SystemExit(f"{s['id']}: sample rate {w.getframerate()} != {rate}, cannot join")
                speech = w.readframes(w.getnframes())
        lead = int(LEAD * rate) * 2 if speech else 0
        total = int(round(s["length"] * rate)) * 2
        frames += b"\x00" * lead + speech + b"\x00" * max(0, total - lead - len(speech))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))
    return out_path
