"""Assembly stage: the finished film, in 16:9 and 9:16, all in code from the storyboard.

  1. Narration track: each shot's WAV placed at its shot start (pipeline/timeline.py).
  2. Levels first: narration brought to -16 LUFS and the score to -26 LUFS, so the balance
     is a choice, not a repair.
  3. Ducking: the score is lowered under the voice with sidechaincompress
     (threshold 0.02, ratio 6, attack 300 ms, release 1500 ms), and fades out at the end.
  4. Loudness: two-pass loudnorm of the mix to -14 LUFS integrated, -1 dB true peak.
  5. Picture: the shot clips joined in order, a short fade in and out, then the AI end card.
  6. Subtitles: English, burned in (max 2 lines of ~40 characters, inside the vertical safe
     area), plus a separate subtitles_en.srt.

Run: python -m pipeline.assemble
Writes: outputs/film/mapping_home_16x9.mp4, outputs/film/mapping_home_9x16.mp4,
        outputs/film/subtitles_en.srt, outputs/film/loudness.json
"""
import json
import re
import textwrap
import wave

from pipeline.common import OUTPUTS, env, ffmpeg
from pipeline.shots import ASPECTS
from pipeline.timeline import END_CARD_S, FPS, LEAD, TAIL, shot_timeline, total_length, write_narration_track
from pipeline.validate import load_storyboard

OUT = OUTPUTS / "film"
SHOTS = OUTPUTS / "shots"
MUSIC = OUTPUTS / "music"
DUCK = "threshold=0.02:ratio=6:attack=300:release=1500"
TARGET = {"I": -14.0, "TP": -1.0, "LRA": 11.0}
FADE = 0.6
WRAP = 40


# ---------- subtitles ----------

def chunks(text, wrap=WRAP):
    """Split a line into subtitle events of at most 2 lines x `wrap` characters."""
    lines = textwrap.wrap(text, wrap)
    return [lines[i:i + 2] for i in range(0, len(lines), 2)]


def subtitle_events(sb, timeline, wrap=WRAP):
    events = []
    for shot, seg in zip(sb["shots"], timeline):
        text = shot["narration_en"].strip()
        if not text or "TODO" in text:
            continue
        if seg["speech"]:
            start, end = seg["start"] + LEAD, seg["start"] + LEAD + seg["speech"]
        else:  # no narration audio yet: show the line across the shot
            start, end = seg["start"] + LEAD, seg["start"] + seg["length"] - TAIL
        parts = chunks(text, wrap)
        total_chars = sum(len(" ".join(p)) for p in parts)
        t = start
        for p in parts:
            d = (end - start) * len(" ".join(p)) / total_chars
            events.append((t, t + d, p))
            t += d
    return events


def ts(t, sep=","):
    cs = int(round(t * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h:02}:{m:02}:{s:02}{sep}{cs * 10:03}" if sep == "," else f"{h}:{m:02}:{s:02}.{cs:02}"


def write_srt(events, path):
    blocks = [f"{i}\n{ts(a)} --> {ts(b)}\n" + "\n".join(lines) + "\n" for i, (a, b, lines) in enumerate(events, 1)]
    path.write_text("\n".join(blocks), encoding="utf-8")


def write_ass(events, path, w, h, body_s, title, credits):
    vertical = h > w
    size = 40 if vertical else 36
    margin_v = int(h * 0.22) if vertical else 48  # keep clear of phone UI in 9:16
    esc = lambda s: s.replace("{", "(").replace("}", ")")
    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {w}", f"PlayResY: {h}", "WrapStyle: 2", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Alignment, "
        "MarginL, MarginR, MarginV, BorderStyle, Outline, Shadow",
        f"Style: Sub,Arial,{size},&H00FFFFFF,&H00000000,&H80000000,0,2,60,60,{margin_v},1,2.5,1",
        f"Style: Card,Arial,{size + 10},&H00FFFFFF,&H00000000,&H00000000,1,5,60,60,0,1,0,0",
        f"Style: Small,Arial,{size - 12},&H00C8C8C8,&H00000000,&H00000000,0,5,60,60,0,1,0,0",
        "", "[Events]", "Format: Layer, Start, End, Style, Text",
    ]
    for a, b, text_lines in events:
        lines.append(f"Dialogue: 0,{ts(a, '.')},{ts(b, '.')},Sub," + r"\N".join(esc(l) for l in text_lines))
    a, b = ts(body_s, "."), ts(body_s + END_CARD_S, ".")
    lines.append(rf"Dialogue: 0,{a},{b},Card,{{\fad(400,0)\pos({w // 2},{int(h * 0.42)})}}{esc(title)}")
    lines.append(rf"Dialogue: 0,{a},{b},Small,{{\fad(400,0)\pos({w // 2},{int(h * 0.52)})}}Made with AI")
    credit = r"\N".join(textwrap.wrap(credits, 34 if vertical else 70))
    lines.append(rf"Dialogue: 0,{a},{b},Small,{{\fad(400,0)\pos({w // 2},{int(h * 0.62)})\fs{size - 18}}}{esc(credit)}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------- audio ----------

def narration_rate(timeline):
    for s in timeline:
        if s["file"]:
            with wave.open(str(s["file"]), "rb") as w:
                return w.getframerate()
    return 24000


def mix_audio(timeline, seconds):
    narr = write_narration_track(timeline, OUT / "narration.wav", rate=narration_rate(timeline))
    score = MUSIC / "score.wav"
    if not score.exists():
        raise SystemExit("No score yet: run python -m pipeline.music first.")
    raw = OUT / "mix_raw.wav"
    fc = (f"[0:a]aresample=48000,aformat=channel_layouts=stereo,loudnorm=I=-16:TP=-2,"
          f"aresample=48000,apad=whole_dur={seconds:.3f},asplit=2[voice][key];"
          f"[1:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{seconds:.3f},asetpts=N/SR/TB,"
          f"loudnorm=I=-26:TP=-6,aresample=48000,afade=t=in:d=1.5,"
          f"afade=t=out:st={max(seconds - 3.5, 0):.3f}:d=3.5[music];"
          f"[music][key]sidechaincompress={DUCK}[ducked];"
          f"[voice][ducked]amix=inputs=2:duration=first:normalize=0[mix]")
    ffmpeg(["-i", narr, "-stream_loop", "-1", "-i", score, "-filter_complex", fc, "-map", "[mix]",
            "-t", f"{seconds:.3f}", "-ar", "48000", raw],
           stage="assemble", params={"step": "mix", "duck": DUCK}, output=raw)

    # Two-pass loudness normalisation to -14 LUFS / -1 dBTP.
    target = f"I={TARGET['I']}:TP={TARGET['TP']}:LRA={TARGET['LRA']}"
    p = ffmpeg(["-i", raw, "-af", f"loudnorm={target}:print_format=json", "-f", "null", "-"],
               stage="assemble", params={"step": "loudnorm pass 1"}, loglevel="info")
    m = json.loads(re.findall(r"\{[^{}]*\"input_i\"[^{}]*\}", p.stderr)[-1])
    final = OUT / "mix.wav"
    ffmpeg(["-i", raw, "-af",
            f"loudnorm={target}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
            f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:"
            f"linear=true:print_format=json", "-ar", "48000", final],
           stage="assemble", params={"step": "loudnorm pass 2", **TARGET}, output=final)
    check = ffmpeg(["-i", final, "-af", f"loudnorm={target}:print_format=json", "-f", "null", "-"],
                   stage="assemble", params={"step": "loudness check"}, loglevel="info")
    after = json.loads(re.findall(r"\{[^{}]*\"input_i\"[^{}]*\}", check.stderr)[-1])
    loud = {"before": {k: m[k] for k in ("input_i", "input_tp", "input_lra")},
            "after": {k: after[k] for k in ("input_i", "input_tp", "input_lra")}, "target": TARGET}
    (OUT / "loudness.json").write_text(json.dumps(loud, indent=2), encoding="utf-8")
    return final, loud


def build_credits(timeline):
    """End-card credits from what actually made this cut, read from the stage manifests."""
    images = env("KEYFRAME_MODEL", "@cf/black-forest-labs/flux-2-klein-4b").split("/")[-1]
    wan_used = any((SHOTS / "wan" / f"{s['id']}.mp4").exists() for s in timeline)
    motion = "Wan 2.2 + FFmpeg" if wan_used else "FFmpeg pan and zoom"
    choice_file = MUSIC / "choice.json"
    choice = json.loads(choice_file.read_text(encoding="utf-8")) if choice_file.exists() else {}
    music = "placeholder (FFmpeg)" if choice.get("placeholder", True) else "ACE-Step 1.5"
    voice = "Gemini TTS" if any(s["speech"] for s in timeline) else "none yet"
    return f"Images: {images} · Motion: {motion} · Narration: {voice} · Music: {music} · Edit: FFmpeg"


# ---------- picture ----------

def render(aspect, clips, body_s, seconds, audio, ass_name):
    w, h = ASPECTS[aspect]
    listing = OUT / f"shots_{aspect}.txt"
    listing.write_text("".join(f"file '{c.as_posix()}'\n" for c in clips), encoding="utf-8")
    out = OUT / f"mapping_home_{aspect}.mp4"
    fc = (f"[0:v]fade=t=in:d={FADE},fade=t=out:st={body_s - FADE:.3f}:d={FADE},setsar=1[body];"
          f"[1:v]setsar=1[card];[body][card]concat=n=2:v=1:a=0,ass={ass_name},format=yuv420p[v]")
    ffmpeg(["-f", "concat", "-safe", "0", "-i", listing.name,
            "-f", "lavfi", "-i", f"color=c=black:s={w}x{h}:r={FPS}:d={END_CARD_S}",
            "-i", audio.name, "-filter_complex", fc, "-map", "[v]", "-map", "2:a",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", FPS,
            "-c:a", "aac", "-b:a", "192k", "-t", f"{seconds:.3f}", "-movflags", "+faststart", out.name],
           stage="assemble", params={"step": "render", "aspect": aspect}, output=out, cwd=OUT)
    return out


def main():
    sb, _, todo = load_storyboard()
    shots_manifest = SHOTS / "manifest.json"
    if not shots_manifest.exists():
        raise SystemExit("No shots yet: run python -m pipeline.shots first.")
    clips = json.loads(shots_manifest.read_text(encoding="utf-8"))
    timeline = shot_timeline(sb)
    body_s = total_length(timeline)
    seconds = body_s + END_CARD_S
    OUT.mkdir(parents=True, exist_ok=True)

    for seg in timeline:
        for aspect in ASPECTS:
            c = clips[aspect].get(seg["id"])
            if not c or abs(c["length"] - seg["length"]) > 1 / FPS:
                raise SystemExit(f"{seg['id']} {aspect}: clip missing or out of date. Run python -m pipeline.shots.")

    audio, loud = mix_audio(timeline, seconds)

    credits = build_credits(timeline)
    write_srt(subtitle_events(sb, timeline), OUT / "subtitles_en.srt")

    outputs = []
    for aspect, (w, h) in ASPECTS.items():
        ass = OUT / f"subtitles_{aspect}.ass"
        events = subtitle_events(sb, timeline, wrap=26 if h > w else WRAP)
        write_ass(events, ass, w, h, body_s, sb["title"], credits)
        paths = [SHOTS / aspect / clips[aspect][seg["id"]]["file"] for seg in timeline]
        outputs.append(render(aspect, paths, body_s, seconds, audio, ass.name))

    narrated = sum(1 for s in timeline if s["speech"])
    print(f"Film: {seconds:.1f}s ({body_s:.1f}s + {END_CARD_S:.0f}s end card), "
          f"{narrated}/{len(timeline)} shots narrated")
    print(f"Loudness: {loud['after']['input_i']} LUFS, true peak {loud['after']['input_tp']} dBTP "
          f"(target {TARGET['I']} / {TARGET['TP']})")
    for o in outputs:
        print(" ->", o.relative_to(OUTPUTS.parent).as_posix())
    if todo:
        print(f"Note: {', '.join(todo)} still have TODO lines; they have no subtitles or narration.")
    if not (60 <= seconds <= 90):
        print(f"WARNING: {seconds:.1f}s is outside 60-90s.")


if __name__ == "__main__":
    main()
