"""Moving shots stage: one clip per shot, in both aspect ratios, cut to the narration timing.

For each shot:
  - if a Wan 2.2 clip exists at outputs/shots/wan/<shot>.mp4 (made in the Kaggle notebook,
    kaggle/wan_shots.py), it is scaled and centre-cropped to each aspect ratio and held on
    its last frame if it is shorter than the shot;
  - otherwise the keyframe gets a slow Ken Burns move (FFmpeg zoompan) in the storyboard's
    motion.direction: in, out, left, right or none. This is also the fallback when Wan fails.

Clips are cached by a hash of the keyframe, motion, length and aspect ratio, so a changed
keyframe or narration length re-renders only that shot.

Run: python -m pipeline.shots
Writes: outputs/shots/16x9/<shot>_<hash>.mp4, outputs/shots/9x16/<shot>_<hash>.mp4, manifest.json
"""
import hashlib
import json

from pipeline.common import OUTPUTS, ffmpeg, input_hash, log_call
from pipeline.timeline import FPS, shot_timeline
from pipeline.validate import load_storyboard

OUT = OUTPUTS / "shots"
KEYS = OUTPUTS / "keyframes"
WAN = OUT / "wan"
ASPECTS = {"16x9": (1280, 720), "9x16": (720, 1280)}
ZOOM = 0.12  # how far a Ken Burns move zooms over one shot


def file_digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def kenburns_filter(direction, w, h, frames):
    """Crop the square keyframe to the target aspect, upscale (stops zoompan jitter), then move."""
    n = max(frames - 1, 1)
    p = f"(on/{n})"
    z = {"in": f"1+{ZOOM}*{p}", "out": f"{1 + ZOOM}-{ZOOM}*{p}"}.get(direction, f"{1 + ZOOM / 2}")
    if direction == "none":
        z = "1"
    cx, cy = "(iw-iw/zoom)/2", "(ih-ih/zoom)/2"
    x = {"left": f"(iw-iw/zoom)*(1-{p})", "right": f"(iw-iw/zoom)*{p}"}.get(direction, cx)
    crop = f"crop='min(iw,ih*{w}/{h})':'min(ih,iw*{h}/{w})'"
    return (f"{crop},scale={w * 3}:{h * 3},"
            f"zoompan=z='{z}':x='{x}':y='{cy}':d={frames}:s={w}x{h}:fps={FPS},"
            f"format=yuv420p")


def render(shot, seg, aspect, keyframe):
    w, h = ASPECTS[aspect]
    frames = round(seg["length"] * FPS)
    wan = WAN / f"{shot['id']}.mp4"
    use_wan = shot["motion"]["type"] == "wan" and wan.exists()
    source = {"wan": file_digest(wan)} if use_wan else {"keyframe": keyframe.name}
    key = input_hash({**source, "motion": shot["motion"], "length": seg["length"], "aspect": aspect, "v": 2})
    out = OUT / aspect / f"{shot['id']}_{key}.mp4"
    if out.exists():
        log_call(stage="shots", provider="cache", model="ffmpeg", shot=shot["id"], cache_hit=True,
                 input_hash=key, output=str(out))
        return out, "cached"
    out.parent.mkdir(parents=True, exist_ok=True)
    enc = ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", FPS, "-an"]
    if use_wan:
        vf = (f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={FPS},"
              f"tpad=stop_mode=clone:stop_duration={seg['length']},format=yuv420p")
        ffmpeg(["-i", wan, "-vf", vf, "-t", f"{seg['length']:.4f}", *enc, out],
               stage="shots", shot=shot["id"], params={"source": "wan", "aspect": aspect}, output=out)
        return out, "wan"
    vf = kenburns_filter(shot["motion"]["direction"], w, h, frames)
    ffmpeg(["-loop", "1", "-framerate", FPS, "-i", keyframe, "-vf", vf, "-frames:v", frames, *enc, out],
           stage="shots", shot=shot["id"],
           params={"source": "kenburns", "direction": shot["motion"]["direction"], "aspect": aspect,
                   "length_s": seg["length"]}, output=out)
    return out, "kenburns"


def main():
    sb, _, _ = load_storyboard()
    kf_manifest = KEYS / "manifest.json"
    if not kf_manifest.exists():
        raise SystemExit("No keyframes yet: run python -m pipeline.keyframes first.")
    keyframes = json.loads(kf_manifest.read_text(encoding="utf-8"))["shots"]
    timeline = {s["id"]: s for s in shot_timeline(sb)}

    manifest = {a: {} for a in ASPECTS}
    for shot in sb["shots"]:
        kf = keyframes.get(shot["id"])
        if not kf:
            raise SystemExit(f"{shot['id']}: no keyframe. Run python -m pipeline.keyframes.")
        keyframe = KEYS / kf["file"]
        seg = timeline[shot["id"]]
        statuses = []
        for aspect in ASPECTS:
            path, status = render(shot, seg, aspect, keyframe)
            manifest[aspect][shot["id"]] = {"file": path.name, "length": seg["length"]}
            statuses.append(status)
        wan_note = "  (wan clip missing: Ken Burns fallback)" if (
            shot["motion"]["type"] == "wan" and not (WAN / f"{shot['id']}.mp4").exists()) else ""
        print(f"{shot['id']}: {seg['length']:5.2f}s  {' / '.join(statuses)}{wan_note}")

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("\nShots ready in outputs/shots/16x9 and outputs/shots/9x16.")


if __name__ == "__main__":
    main()
