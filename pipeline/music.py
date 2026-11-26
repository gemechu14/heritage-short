"""Music stage: prepare the ACE-Step job, then pick the score.

ACE-Step 1.5 needs a GPU, so it runs on Kaggle (kaggle/ace_step_score.py). This stage:
  1. writes outputs/music/ace_step_job.json from the storyboard's music cues: one caption,
     the film's real length, three seeds -> three candidates;
  2. once the candidates are copied into outputs/music/candidates/, records which one you
     chose and why (outputs/music/choice.json) and copies it to outputs/music/score.wav;
  3. with no candidates yet, renders a quiet placeholder pad in FFmpeg, so the pipeline still
     runs end to end (clearly marked as a placeholder).

Run: python -m pipeline.music
     python -m pipeline.music --choose candidate_2.wav --why "warmest strings, quiet enough under the voice"
"""
import argparse
import json
import shutil

from pipeline.common import OUTPUTS, ffmpeg, log_call
from pipeline.timeline import END_CARD_S, shot_timeline, total_length
from pipeline.validate import load_storyboard

OUT = OUTPUTS / "music"
CANDIDATES = OUT / "candidates"
SCORE = OUT / "score.wav"
SEEDS = [11, 22, 33]
AUDIO = (".wav", ".flac", ".mp3", ".ogg", ".opus")


def build_job(sb, seconds):
    cues = sb["music"]["cues"]
    structure = "; then ".join(c["description"] for c in cues)
    caption = (f"instrumental film score for a short family documentary, East African feel, "
               f"warm and gentle, quiet enough to sit under a spoken voice, no lead vocals. "
               f"Structure: {structure}.")
    return {
        "caption": caption,
        "lyrics": "[Instrumental]",
        "instrumental": True,
        "duration": round(seconds),
        "seeds": SEEDS,
        "model": "acestep-v15-turbo",
        "inference_steps": 8,
        "cues": cues,
    }


def placeholder(seconds):
    """A soft three-note pad that shifts with each cue: a temp track, not the score."""
    pad = ("0.05*sin(2*PI*220*t)+0.035*sin(2*PI*277.18*t)+0.035*sin(2*PI*329.63*t)"
           "+0.02*sin(2*PI*110*t)")
    tmp = OUT / "placeholder.wav"
    ffmpeg(["-f", "lavfi", "-i", f"aevalsrc={pad}:s=48000:d={seconds:.2f}",
            "-af", f"afade=t=in:d=2,afade=t=out:st={max(seconds - 3, 0):.2f}:d=3,tremolo=f=0.2:d=0.3",
            "-ac", "2", tmp], stage="music", params={"source": "placeholder"}, output=tmp)
    shutil.copyfile(tmp, SCORE)
    (OUT / "choice.json").write_text(json.dumps({"file": None, "placeholder": True,
                                                 "why": "no ACE-Step candidates yet"}, indent=2),
                                     encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--choose", help="file name in outputs/music/candidates/ to use as the score")
    ap.add_argument("--why", default="", help="why you chose it (goes into choice.json)")
    args = ap.parse_args(argv)

    sb, _, _ = load_storyboard()
    seconds = total_length(shot_timeline(sb)) + END_CARD_S
    OUT.mkdir(parents=True, exist_ok=True)
    CANDIDATES.mkdir(exist_ok=True)
    job = build_job(sb, seconds)
    (OUT / "ace_step_job.json").write_text(json.dumps(job, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"ACE-Step job written: outputs/music/ace_step_job.json ({job['duration']}s, seeds {SEEDS})")

    candidates = sorted(p for p in CANDIDATES.iterdir() if p.suffix.lower() in AUDIO)
    choice_file = OUT / "choice.json"
    choice = json.loads(choice_file.read_text(encoding="utf-8")) if choice_file.exists() else {}

    if args.choose:
        chosen = CANDIDATES / args.choose
        if not chosen.exists():
            raise SystemExit(f"{chosen} not found. Candidates: {', '.join(p.name for p in candidates) or 'none'}")
        if not args.why:
            raise SystemExit('Say why you chose it: --why "..." (it goes into choice.json and EXPERIMENTS.md)')
        choice = {"file": chosen.name, "placeholder": False, "why": args.why,
                  "candidates": [p.name for p in candidates]}
        choice_file.write_text(json.dumps(choice, indent=2, ensure_ascii=False), encoding="utf-8")
        log_call(stage="music", provider="choice", model="ace-step-1.5", params={"chosen": chosen.name},
                 seed=None, why=args.why)

    if choice.get("file") and (CANDIDATES / choice["file"]).exists():
        src = CANDIDATES / choice["file"]
        ffmpeg(["-i", src, "-ar", "48000", "-ac", "2", SCORE], stage="music",
               params={"source": "ace-step", "file": src.name}, output=SCORE)
        print(f"Score: {src.name} -> outputs/music/score.wav  (why: {choice['why']})")
    elif candidates:
        print("Candidates found:", ", ".join(p.name for p in candidates))
        print('Listen under the narration, then: python -m pipeline.music --choose <file> --why "..."')
        if not SCORE.exists():
            placeholder(seconds)
            print("Using a placeholder pad until you choose.")
    else:
        placeholder(seconds)
        print("No ACE-Step candidates yet: placeholder pad written to outputs/music/score.wav.")
        print("Run kaggle/ace_step_score.py on Kaggle and copy the results into outputs/music/candidates/.")


if __name__ == "__main__":
    main()
