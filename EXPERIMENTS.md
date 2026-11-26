# Experiments

Each entry has the form hypothesis → change → result → decision. The evidence is in `runs.jsonl`, found by
stage, model and time (UTC, 2026-11-26), and in the files under `outputs/`.

---

### E1. Let the smoke test pick the model, or pin one?
- **Hypothesis:** picking the first `flash` model the API lists keeps the code current as models move.
- **Change:** the smoke test chose `gemini-2.5-flash` from the list.
- **Result:** 404, "no longer available to new users" (`smoke`, `gemini-2.5-flash`, 00:16). The list still
  includes models that new keys can't call. With `gemini-3.8-flash` and `gemini-3.8-flash-tts` pinned in
  `.env`, all four smoke checks passed (00:18).
- **Decision:** pin the models in `.env` and use the list only to see what exists.

### E2. Can a fallback text model ride out a 503?
- **Hypothesis:** the 503 "high demand" error is specific to `gemini-3.8-flash`, so a sibling model will answer.
- **Change:** the same script run with `GEMINI_TEXT_MODEL=gemini-3.7-flash`, then `gemini-3.8-flash-lite`.
- **Result:** 3.7-flash also gave 503 after 3 attempts (`script`, 01:13). 3.8-flash-lite gave 404 because it
  isn't on my key's list (01:13). The smoke test's list shows `gemini-3.5-flash-lite` and
  `gemini-3.1-flash-lite` instead.
- **Decision:** the overload spans the Flash family. Make the script resumable (save per line) and let the
  film finish without it (`--keep-going`) rather than hop between models.

### E3. Does a style instruction help the Afaan Oromo voice?
- **Hypothesis (from the brief, Appendix B):** a short style instruction improves a voice more than switching voices.
- **Change:** the first version sent `"<style>: <line>"` as the spoken text.
- **Result:** in user test 1 an Oromo-speaking viewer heard the English instruction read aloud, and the
  10-word line ran 10.16 s.
- **Decision:** by default send the line alone. `TTS_STYLE=on` sends the documented form
  `"Say <style>: <line>"` as an A/B switch, with the style as part of the cache key so both versions
  coexist. **Pending:** compare both on s01 once Gemini answers, by duration (seconds) and by ear.

### E4. FLUX.1 schnell with a fixed seed
- **Hypothesis:** a fixed seed per shot makes keyframes reproducible, as the brief suggests.
- **Change:** `seed` added to the FLUX.1 schnell request on Workers AI.
- **Result:** 400, "Additional or unevaluated properties '/seed' not allowed" (`keyframes`, schnell). The model
  schema on Workers AI accepts only `prompt` and `steps`, and it can't take reference images either.
- **Decision:** switch keyframes to **FLUX.2 klein 4B**, which accepts a seed and up to 4 reference images,
  under Apache 2.0. Keep schnell for the smoke test only.

### E5. Is a FLUX.2 klein seed reproducible?
- **Hypothesis:** the same prompt and seed give the same image.
- **Change:** the same portrait prompt twice with seed 7 (`experiment`, `klein_seed7_a/b`).
- **Result:** the same man and the same scarf pattern, but a different background and different file bytes
  (MD5 `68838F34…` vs `2EDBFF9A…`). See `outputs/experiments/klein_seed7_a.jpg` and `_b.jpg`.
- **Decision:** on Workers AI a seed gives a *similar* image, not the same one. Reproducibility comes from
  **caching the generated file** by input hash, not from re-running the seed.

### E6. Does a reference image keep identity across shots?
- **Hypothesis:** passing the reference portrait as `input_image_0` keeps the face better than text alone.
- **Change:** "the same man standing at a chalkboard" with the seed-7 portrait as reference (`klein_ref`).
- **Result:** the identity was kept very strongly (the same face and scarf). But the model copied the
  **portrait framing** (he never stands at the board), and the chalkboard writing was garbled.
- **Decision:** use references for identity, put the shot size first in the prompt, say "shown in this
  scene, not as a portrait", and keep "no text" in the style block.

### E7. Does "Ethiopian Oromo" alone produce an Ethiopian face?
- **Hypothesis:** naming the ethnicity is enough.
- **Change:** reference sheet v1 used the original descriptions.
- **Result:** v0 (E5) and the father in v1 read as South Asian, as did the boy. With "dark brown skin, East
  African features" added (v1), the adult son and the mother were right, but the father and the boy still had
  straight hair (`outputs/keyframes/refs/*_0721…`, `*_82ba…`).
- **Decision:** describe visible features, not only an identity word.

### E8. Hair texture
- **Hypothesis:** the remaining drift comes from hair.
- **Change:** "short tightly curled black/greying hair" for the son, the boy and the father (v2).
- **Result:** all four references read as East African and share one painted style
  (`refs/father_51e7…`, `gemechu_adult_012c…`, `gemechu_child_a253…`, `mother_4e35…`). The mother's
  reference was **cached**, because her description didn't change.
- **Decision:** v2 is the golden reference sheet. *To confirm with my family that they recognise themselves.*

### E9. Reference images in an extreme wide shot
- **Hypothesis:** the reference keeps the son recognisable even when he is small in the frame.
- **Change:** s10 ("a young man standing small on a ridge") generated with his reference portrait.
- **Result:** the model returned a **portrait** of him in front of the hills (`s10_0934…`). s05 drifted the
  same way. Without the reference, and with "a tiny distant figure … seen from behind", s10 became a true
  extreme wide shot (`s10_d4f4…`).
- **Decision:** no reference images for `extreme_wide` shots, where identity isn't visible anyway
  (`NO_REF_SIZES` in `pipeline/keyframes.py`).

### E10. Setting words versus generic words
- **Hypothesis:** generic words ("hearth", "colleagues", "a farmer's hand") pull in the model's default,
  non-Ethiopian setting.
- **Change:** s04 → "a small charcoal brazier … inside a traditional round Ethiopian mud-walled house";
  s07 → "two Ethiopian colleagues … in Addis Ababa"; s08 → "an Ethiopian farmer's dark-skinned weathered hand".
- **Result:** v1 had a European stone fireplace (s04), European-looking colleagues (s07) and a light-skinned
  hand (s08). In v2 all three are right. s08 drifted toward a photographic look, away from the painted style.
- **Decision:** name the place and people concretely. *Open:* s08's style drift; try adding "hand-painted"
  at the start of its prompt.

### E11. Does the cache regenerate only what changed?
- **Hypothesis:** with keys hashed from inputs, editing four image prompts touches only those four shots.
- **Change:** E9 and E10 edited s04, s07, s08 and s10, then `python -m pipeline.keyframes` was run again.
- **Result:** "4 generated, 10 from cache" (4 references and 6 shots). A full `python -m pipeline.film` right
  after made **0** image calls (14 cache hits), and the shots stage re-rendered only clips whose keyframe changed.
- **Decision:** this is the live demo for the walkthrough: change one line, rerun, show one new call in
  `runs.jsonl`.

### E12. Subtitles in the vertical frame
- **Hypothesis:** the brief's 40 characters per line works for both aspect ratios.
- **Change:** the first assembly used 40 characters at font size 46 in both.
- **Result:** in 9:16 (720 px wide) the line ran off both edges.
- **Decision:** 26 characters at size 40 in 9:16, raised 22% from the bottom (safe area), and 40 characters
  in 16:9. Long lines are split into timed parts.

### E13. Does two-pass loudnorm hit the platform target?
- **Hypothesis:** two-pass `loudnorm` lands within 0.5 LU of −14 LUFS.
- **Change:** pass 1 measures the mix and pass 2 applies the measured values (`linear=true`). A third pass
  only measures.
- **Result:** −14.01 LUFS integrated, true peak −5.70 dBTP (`outputs/film/loudness.json`). This cut has
  music only and no voice yet.
- **Decision:** keep two-pass. Re-check once narration is in, since speech peaks will raise the true peak.

---

### Planned, once the APIs and the GPU allow
- **E14. ACE-Step candidates:** three seeds (11, 22, 33) from one caption. Listen under the narration, choose
  one and say why (`python -m pipeline.music --choose … --why …`).
- **E15. TTS style A/B:** E3's comparison.
- **E16. Wan 2.2 on a T4:** does TI2V-5B fit in 16 GB at 704×1280 with every offload flag? (The README says 24 GB.)
