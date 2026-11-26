"""Radio cut: narration over quiet placeholder music on a black screen, for the first user test.

Shot lengths come from pipeline/timeline.py, the same rule the finished film uses:
max(storyboard duration, narration length + lead + tail). Also writes English subtitles.

Needs FFmpeg on your PATH. Run: python -m pipeline.radio_cut
Writes: outputs/radio_cut/radio_cut.mp4, narration_full.wav, subtitles_en.srt
"""
from pipeline.common import OUTPUTS, ffmpeg
from pipeline.timeline import LEAD, shot_timeline, total_length, write_narration_track
from pipeline.validate import load_storyboard

OUT = OUTPUTS / "radio_cut"


def srt_time(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def main():
    sb, _, _ = load_storyboard()
    OUT.mkdir(parents=True, exist_ok=True)
    timeline = shot_timeline(sb)
    t = total_length(timeline)

    full = write_narration_track(timeline, OUT / "narration_full.wav")
    srt = []
    for shot, seg in zip(sb["shots"], timeline):
        if seg["speech"]:
            a, b = seg["start"] + LEAD, seg["start"] + LEAD + seg["speech"]
            srt.append(f"{len(srt) + 1}\n{srt_time(a)} --> {srt_time(b)}\n{shot['narration_en']}\n")
    (OUT / "subtitles_en.srt").write_text("\n".join(srt), encoding="utf-8")

    pad = "0.02*sin(2*PI*220*t)+0.015*sin(2*PI*277.18*t)+0.015*sin(2*PI*329.63*t)"
    out = OUT / "radio_cut.mp4"
    ffmpeg(["-f", "lavfi", "-i", f"color=c=black:s=1280x720:r=24:d={t:.2f}",
            "-i", full,
            "-f", "lavfi", "-i", f"aevalsrc={pad}:s=48000:d={t:.2f}",
            "-filter_complex", "[1:a]aresample=48000[v];[v][2:a]amix=inputs=2:duration=first,volume=2[a]",
            "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            "-shortest", out],
           stage="radio_cut", params={"duration_s": round(t, 2)}, output=out)

    for shot, seg in zip(sb["shots"], timeline):
        print(f"{seg['id']}: {seg['length']:5.2f}s (planned {shot['duration_s']}s)")
    print(f"\nTotal: {t:.1f}s -> outputs/radio_cut/radio_cut.mp4")
    if t > 90:
        print("Over 90s: shorten some narration lines.")


if __name__ == "__main__":
    main()
