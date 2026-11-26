"""Script stage: translate each shot's English narration into the film language.

Fills only empty `narration` fields, so your hand edits to the Oromo text are kept.
To re-translate a shot, clear its `narration` field and run again.
Lines that still contain TODO are skipped.
Each translated line is saved straight away, so if the API fails partway (e.g. 503),
running again continues from the first empty line.

Run: python -m pipeline.script
"""
import json

from pipeline.common import ROOT, env, gemini_text
from pipeline.validate import load_storyboard

# Place names in Qubee, as the family spells them (user test 1: the model misspelled them).
# CONFIRM these spellings as a native speaker before the next run.
PLACE_NAMES = {
    "Leka Dulecha": "Leeqaa Dullachaa",
    "East Wollega": "Wallagga Bahaa",
}

PROMPT = """You are translating narration for a short family film into {lang}.
Write in Qubee (Latin script). Make it natural spoken {lang}, short and warm, as a son
would say it to his family. Keep personal names exactly as given: Bulti Firissa, Tujube Regasa.
Write these place names exactly like this: {places}.
Use the official {lang} name for Cooperative Bank of Oromia if it appears.
Keep the line short enough to say in under 7 seconds.
Return only the translation, nothing else.

Full story for context:
{context}

Line to translate:
{line}"""


def main():
    sb, _, _ = load_storyboard()
    model = env("GEMINI_TEXT_MODEL", "gemini-3.8-flash")
    lang = sb["language"]["name"]
    context = "\n".join(s["narration_en"] for s in sb["shots"] if "TODO" not in s["narration_en"])
    places = "; ".join(f"{en} -> {om}" for en, om in PLACE_NAMES.items())

    changed = 0
    for shot in sb["shots"]:
        if shot["narration"].strip():
            print(f"{shot['id']}: kept      {shot['narration']}")
            continue
        if "TODO" in shot["narration_en"]:
            print(f"{shot['id']}: skipped   (English line still has TODO)")
            continue
        prompt = PROMPT.format(lang=lang, context=context, places=places, line=shot["narration_en"])
        text = gemini_text(model, prompt, stage="script", temperature=0.2)
        shot["narration"] = text
        (ROOT / "storyboard.json").write_text(json.dumps(sb, indent=2, ensure_ascii=False) + "\n",
                                              encoding="utf-8")
        changed += 1
        print(f"{shot['id']}: translated {text}")

    print(f"\n{changed} line(s) translated. Read every Oromo line and fix anything unnatural by hand.")


if __name__ == "__main__":
    main()
