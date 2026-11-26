"""Call each provider once, log every call, and report which models your key can use.

Run: python -m pipeline.smoke_test
Outputs: outputs/smoke/translation.txt, outputs/smoke/tts.wav, outputs/smoke/flux.jpg
"""
from pipeline.common import OUTPUTS, cf_image, env, gemini_list_models, gemini_text, gemini_tts

SAMPLE_EN = "I was born in 1998, in Leka Dulecha, East Wollega."
SKIP = ("tts", "image", "live", "audio", "embedding", "native")


def main():
    out = OUTPUTS / "smoke"
    out.mkdir(parents=True, exist_ok=True)
    results = {}

    # 1. Which Gemini models does this key see?
    try:
        names = [m["name"].removeprefix("models/") for m in gemini_list_models()]
        text_models = [n for n in names if "flash" in n and not any(s in n for s in SKIP)]
        tts_models = [n for n in names if "tts" in n]
        print("Gemini text models:", ", ".join(text_models) or "(none with 'flash')")
        print("Gemini TTS models: ", ", ".join(tts_models) or "(none)")
        results["list_models"] = "OK"
    except Exception as exc:
        print("list_models FAILED:", exc)
        text_models, tts_models = [], []
        results["list_models"] = "FAILED"

    text_model = env("GEMINI_TEXT_MODEL") or (text_models[0] if text_models else None)
    tts_model = env("GEMINI_TTS_MODEL") or (tts_models[0] if tts_models else None)

    # 2. Text: translate one narration line into Afaan Oromo.
    oromo = None
    if text_model:
        try:
            oromo = gemini_text(
                text_model,
                "Translate into Afaan Oromo, written in Qubee (Latin script). "
                f"Return only the translation, nothing else:\n\n{SAMPLE_EN}",
                stage="smoke",
            )
            (out / "translation.txt").write_text(f"{SAMPLE_EN}\n{oromo}\n", encoding="utf-8")
            print(f"Text   OK  [{text_model}]  {oromo}")
            results["text"] = "OK"
        except Exception as exc:
            print(f"Text   FAILED [{text_model}]: {exc}")
            results["text"] = "FAILED"
    else:
        results["text"] = "SKIPPED (no model)"

    # 3. TTS: speak the Oromo line.
    if tts_model:
        try:
            secs = gemini_tts(tts_model, oromo or SAMPLE_EN, out / "tts.wav",
                              style="Speak warmly and unhurriedly", stage="smoke")
            print(f"TTS    OK  [{tts_model}]  {secs}s -> outputs/smoke/tts.wav")
            results["tts"] = "OK"
        except Exception as exc:
            print(f"TTS    FAILED [{tts_model}]: {exc}")
            results["tts"] = "FAILED"
    else:
        results["tts"] = "SKIPPED (no model)"

    # 4. Image: one FLUX keyframe on Cloudflare.
    image_model = env("CF_IMAGE_MODEL", "@cf/black-forest-labs/flux-1-schnell")
    try:
        cf_image(image_model,
                 "rolling green hills of East Wollega at dawn, mist in the valleys, small thatched house, "
                 "warm hand-painted illustration, soft golden light, no text",
                 out / "flux.jpg", stage="smoke")
        print(f"Image  OK  [{image_model}]  -> outputs/smoke/flux.jpg")
        results["image"] = "OK"
    except Exception as exc:
        print(f"Image  FAILED [{image_model}]: {exc}")
        results["image"] = "FAILED"

    print("\nSummary:", results)
    print("Every call above is logged in runs.jsonl.")
    if text_model and tts_model:
        print(f"\nAdd to .env to pin these models:\nGEMINI_TEXT_MODEL={text_model}\nGEMINI_TTS_MODEL={tts_model}")


if __name__ == "__main__":
    main()
