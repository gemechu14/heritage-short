"""Validate storyboard.json against the schema plus a few cross-field rules.

Run: python -m pipeline.validate
"""
import json

from jsonschema import Draft202012Validator

from pipeline.common import ROOT


def load_storyboard(path=ROOT / "storyboard.json"):
    storyboard = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads((ROOT / "schema" / "storyboard.schema.json").read_text(encoding="utf-8"))

    errors = [f"{'/'.join(map(str, e.path)) or '(root)'}: {e.message}"
              for e in Draft202012Validator(schema).iter_errors(storyboard)]

    shots = storyboard.get("shots", [])
    ids = [s.get("id") for s in shots]
    if len(ids) != len(set(ids)):
        errors.append("shot ids must be unique")
    known = set(storyboard.get("characters", {}))
    for s in shots:
        for c in s.get("characters", []):
            if c not in known:
                errors.append(f"{s.get('id')}: unknown character '{c}'")
    total = sum(s.get("duration_s", 0) for s in shots)
    if not 60 <= total <= 90:
        errors.append(f"total duration {total}s is outside 60-90s")
    for cue in storyboard.get("music", {}).get("cues", []):
        if cue["end_s"] <= cue["start_s"]:
            errors.append(f"music cue {cue['id']}: end_s must be after start_s")

    if errors:
        print("storyboard.json is INVALID:")
        for e in errors:
            print("  -", e)
        raise SystemExit(1)

    warnings = [s["id"] for s in shots if "TODO" in s["narration_en"]]
    return storyboard, total, warnings


if __name__ == "__main__":
    sb, total, todo = load_storyboard()
    print(f"storyboard.json OK: {len(sb['shots'])} shots, {total}s total")
    if todo:
        print(f"  note: narration still has TODO in {', '.join(todo)}")
