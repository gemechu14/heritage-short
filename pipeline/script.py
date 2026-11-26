"""Script stage: translate each shot's English narration into the film language.

Fills only empty `narration` fields, so your hand edits to the Oromo text are kept.
To re-translate a shot, clear its `narration` field and run again.
Lines that still contain TODO are skipped.

Run: python -m pipeline.script
"""
import json

from pipeline.common import ROOT, env, gemini_text
from pipeline.validate import load_storyboard

PROMPT = """You are translating narration for a short family film into {lang}.
Write in Qubee (Latin script). Make it natural spoken {lang}, short and warm, as a son
would say it to his family. Keep personal names exactly as given: Bulti Firissa, Tujube Regasa.
Use the official {lang} name for Cooperative Bank of Oromia if it appears.
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

    changed = 0
    for shot in sb["shots"]:
        if shot["narration"].strip():
            print(f"{shot['id']}: kept      {shot['narration']}")
            continue
        if "TODO" in shot["narration_en"]:
            print(f"{shot['id']}: skipped   (English line still has TODO)")
            continue
        text = gemini_text(model, PROMPT.format(lang=lang, context=context, line=shot["narration_en"]),
                           stage="script", temperature=0.2)
        shot["narration"] = text
        changed += 1
        print(f"{shot['id']}: translated {text}")

    if changed:
        (ROOT / "storyboard.json").write_text(json.dumps(sb, indent=2, ensure_ascii=False) + "\n",
                                              encoding="utf-8")
    print(f"\n{changed} line(s) translated. Read every Oromo line and fix anything unnatural by hand.")


if __name__ == "__main__":
    main()
