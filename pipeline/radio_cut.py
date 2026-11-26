"""Radio cut: narration over quiet placeholder music on a black screen, for the first user test.

Each shot lasts max(storyboard duration, narration length + 0.5s), so you can hear the real timing.
Also writes English subtitles (SRT) from the same timings.

Needs FFmpeg on your PATH. Run: python -m pipeline.radio_cut
Writes: outputs/radio_cut/radio_cut.mp4, narration_full.wav, subtitles_en.srt
"""
import json
import subprocess
import time
import wave

from pipeline.common import OUTPUTS, log_call
from pipeline.validate import load_storyboard

NARR = OUTPUTS / "narration"
OUT = OUTPUTS / "radio_cut"
LEAD = 0.5  # silence before each line


def srt_time(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def main():
    sb, _, _ = load_storyboard()
    manifest = json.loads((NARR / "manifest.json").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)

    frames, rate, t, srt, timing = bytearray(), None, 0.0, [], []
    for i, shot in enumerate(sb["shots"], 1):
        entry = manifest.get(shot["id"])
        speech, secs = b"", 0.0
        if entry:
            with wave.open(str(NARR / entry["file"]), "rb") as w:
                rate = rate or w.getframerate()
                if w.getframerate() != rate:
                    raise SystemExit(f"{shot['id']}: sample rate differs, cannot join")
                speech = w.readframes(w.getnframes())
                secs = w.getnframes() / rate
        rate = rate or 24000
        length = max(shot["duration_s"], secs + LEAD)
        lead = int(LEAD * rate) * 2
        total = int(length * rate) * 2
        frames += b"\x00" * lead + speech + b"\x00" * max(0, total - lead - len(speech))
        if entry:
            srt.append(f"{len(srt) + 1}\n{srt_time(t + LEAD)} --> {srt_time(t + LEAD + secs)}\n{shot['narration_en']}\n")
        timing.append(f"{shot['id']}: {length:5.2f}s (planned {shot['duration_s']}s)")
        t += length

    full = OUT / "narration_full.wav"
    with wave.open(str(full), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))
    (OUT / "subtitles_en.srt").write_text("\n".join(srt), encoding="utf-8")

    pad = "0.02*sin(2*PI*220*t)+0.015*sin(2*PI*277.18*t)+0.015*sin(2*PI*329.63*t)"
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", f"color=c=black:s=1280x720:r=24:d={t:.2f}",
        "-i", str(full),
        "-f", "lavfi", "-i", f"aevalsrc={pad}:s=48000:d={t:.2f}",
        "-filter_complex", "[1:a]aresample=48000[v];[v][2:a]amix=inputs=2:duration=first,volume=2[a]",
        "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
        "-shortest", str(OUT / "radio_cut.mp4"),
    ]
    t0 = time.time()
    subprocess.run(cmd, check=True)
    log_call(stage="radio_cut", provider="ffmpeg", model="ffmpeg", params={"duration_s": round(t, 2)},
             seed=None, latency_s=round(time.time() - t0, 2), cost_usd=0.0,
             output=str(OUT / "radio_cut.mp4"))

    print("\n".join(timing))
    print(f"\nTotal: {t:.1f}s -> outputs/radio_cut/radio_cut.mp4")
    if t > 90:
        print("Over 90s: shorten some narration lines.")


if __name__ == "__main__":
    main()
