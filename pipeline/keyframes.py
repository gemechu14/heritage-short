"""Keyframes stage: a reference sheet first, then one keyframe per shot conditioned on it.

Model: FLUX.2 klein 4B on Cloudflare Workers AI (Apache 2.0). We first tried FLUX.1 schnell,
but on Workers AI it rejects a seed and cannot take reference images (FAILURES.md).

Consistency comes from three things sent every time:
  1. the reference portrait of each character in the shot, as input images (identity),
  2. the character's exact description from storyboard.json,
  3. the shared style_block, and the shot's fixed seed.
Generate the references, look at them, and only then make the shots: the references are the
golden references every keyframe is checked against.

Each image is cached by a hash of its prompt, seed, model, size and reference images, so
changing one shot's image_prompt regenerates only that shot; changing a character's
description regenerates its reference and every shot it appears in.

Run: python -m pipeline.keyframes            (references + all shots)
     python -m pipeline.keyframes refs       (references only: approve these first)
     python -m pipeline.keyframes s03 s06    (references + only these shots)
Writes: outputs/keyframes/refs/<character>_<hash>.jpg, outputs/keyframes/<shot>_<hash>.jpg,
        outputs/keyframes/manifest.json
"""
import json
import sys

from pipeline.common import OUTPUTS, cf_image_klein, env, input_hash, log_call
from pipeline.validate import load_storyboard

OUT = OUTPUTS / "keyframes"
STEPS = 4
SIZE = 1024       # square, subject centred: both 16:9 and 9:16 are cropped from it
REF_SEED = 7      # one seed for every reference portrait, so they share a look
SHOT_WORDS = {"extreme_wide": "extreme wide shot", "wide": "wide shot", "medium": "medium shot",
              "medium_close_up": "medium close-up", "close_up": "close-up", "extreme_close_up": "extreme close-up",
              "insert": "close-up insert shot"}
NO_REF_SIZES = {"extreme_wide"}


def ref_prompt(sb, name):
    return (f"character reference portrait of {sb['characters'][name]['description']}, "
            f"head and shoulders, facing the viewer, plain warm background, {sb['style_block']}")


def shot_prompt(sb, shot):
    parts = [f"{SHOT_WORDS[shot['shot_size']]}: {shot['image_prompt']}"]
    if shot["shot_size"] in NO_REF_SIZES:
        if shot["characters"]:
            parts.append("the figure is " + "; ".join(sb["characters"][c]["description"] for c in shot["characters"]))
        parts.append(sb["style_block"])
        return ". ".join(parts)
    for i, name in enumerate(shot["characters"], 1):
        parts.append(f"the person from reference image {i} is {sb['characters'][name]['description']}, "
                     f"keep the same face, hair and clothes, shown in this scene, not as a portrait")
    parts.append(sb["style_block"])
    return ". ".join(parts)


def generate(model, prompt, seed, stem, *, refs=(), shot):
    ref_hashes = [r.stem for r in refs]
    key = input_hash({"prompt": prompt, "seed": seed, "model": model, "steps": STEPS, "size": SIZE,
                      "refs": ref_hashes})
    path = OUT / f"{stem}_{key}.jpg"
    if path.exists():
        log_call(stage="keyframes", provider="cache", model=model, shot=shot, cache_hit=True,
                 input_hash=key, seed=seed, output=str(path))
        return path, key, "cached   "
    cf_image_klein(model, prompt, path, seed=seed, refs=list(refs), width=SIZE, height=SIZE, steps=STEPS,
                   stage="keyframes", shot=shot)
    return path, key, "generated"


def main(only=None):
    sb, _, _ = load_storyboard()
    model = env("KEYFRAME_MODEL", "@cf/black-forest-labs/flux-2-klein-4b")
    (OUT / "refs").mkdir(parents=True, exist_ok=True)
    old = OUT / "manifest.json"
    manifest = json.loads(old.read_text(encoding="utf-8")) if old.exists() else {"refs": {}, "shots": {}}
    generated = cached = 0

    # 1. Reference sheet: one portrait per character.
    refs = {}
    for name in sb["characters"]:
        path, key, status = generate(model, ref_prompt(sb, name), REF_SEED, f"refs/{name}", shot=f"ref:{name}")
        refs[name] = path
        manifest["refs"][name] = {"file": path.relative_to(OUT).as_posix(), "hash": key}
        generated += status == "generated"
        cached += status != "generated"
        print(f"ref {name:14} {status} {path.name}")

    # 2. One keyframe per shot, conditioned on the references of the people in it.
    if only != {"refs"}:
        for shot in sb["shots"]:
            if only and shot["id"] not in only:
                continue
            # In an extreme wide shot the person is a tiny figure, and a reference portrait pulls
            # the frame into a close portrait (EXPERIMENTS.md), so only the description is used.
            shot_refs = [] if shot["shot_size"] in NO_REF_SIZES else [refs[c] for c in shot["characters"]]
            path, key, status = generate(model, shot_prompt(sb, shot), shot["seed"], shot["id"],
                                         refs=shot_refs, shot=shot["id"])
            manifest["shots"][shot["id"]] = {"file": path.name, "hash": key, "seed": shot["seed"],
                                             "refs": [r.name for r in shot_refs]}
            generated += status == "generated"
            cached += status != "generated"
            print(f"{shot['id']}  {status} {path.name}")

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\n{generated} generated, {cached} from cache. Check faces and hands before animating.")


if __name__ == "__main__":
    main(set(sys.argv[1:]) or None)
