"""One command for the whole film: validate -> script -> narration -> keyframes -> shots
-> music -> radio cut -> assemble.

Every stage caches by a hash of its inputs, so running this again regenerates only what
changed in storyboard.json (and makes no model calls if nothing changed).

Run: python -m pipeline.film                 (stop at the first failing stage)
     python -m pipeline.film --keep-going    (if an API stage fails, e.g. a Gemini 503,
                                              carry on with what is already cached)
"""
import argparse
import time
import traceback

from pipeline import assemble, keyframes, music, narration, radio_cut, script, shots
from pipeline.common import RUN_ID
from pipeline.validate import load_storyboard

STAGES = [
    ("script", script.main, True),       # (name, function, may be skipped with --keep-going)
    ("narration", narration.main, True),
    ("keyframes", keyframes.main, False),
    ("shots", shots.main, False),
    ("music", lambda: music.main([]), False),
    ("radio_cut", radio_cut.main, False),
    ("assemble", assemble.main, False),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep-going", action="store_true",
                    help="continue past a failing script or narration stage (API outage)")
    args = ap.parse_args()

    sb, total, todo = load_storyboard()
    print(f"run {RUN_ID}: storyboard OK, {len(sb['shots'])} shots, {total}s planned")
    if todo:
        print(f"  note: TODO lines in {', '.join(todo)} are skipped until you write them")

    summary = []
    for name, fn, skippable in STAGES:
        print(f"\n=== {name} ===")
        t0 = time.time()
        try:
            fn()
            summary.append((name, "ok", time.time() - t0))
        except SystemExit as exc:
            if exc.code not in (None, 0):
                summary.append((name, f"stopped: {exc.code}", time.time() - t0))
                break
            summary.append((name, "ok", time.time() - t0))
        except Exception as exc:
            summary.append((name, f"FAILED: {str(exc)[:120]}", time.time() - t0))
            if args.keep_going and skippable:
                print(f"{name} failed, continuing with cached results (--keep-going):\n  {exc}")
                continue
            traceback.print_exc()
            break

    print("\n=== summary ===")
    for name, status, secs in summary:
        print(f"{name:10} {secs:6.1f}s  {status}")
    print("Every call is logged in runs.jsonl; python -m pipeline.costs summarises it.")


if __name__ == "__main__":
    main()
