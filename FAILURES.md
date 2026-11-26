# Failures

What broke, what I tried, in order, and what fixed it or what I worked around. Times are UTC on
2026-11-26, and the matching lines are in `runs.jsonl`.

### F1. Python and FFmpeg "not recognized" on Windows
- **What happened:** `pip`, `python` and later `ffmpeg` were "not recognized" in PowerShell.
- **Tried:** Python 3.14 was installed but not on PATH, so `python` opened the Microsoft Store stub. I used
  the `py` launcher, which worked. I installed FFmpeg with `winget install Gyan.FFmpeg`; the installer added it
  to the user PATH, but VS Code's terminals kept the old PATH until VS Code was fully restarted.
- **Fixed:** `py -m …` everywhere, and VS Code restarted. The README now notes both.

### F2. The smoke test picked a retired model
- **What happened:** the first text model in the API's list, `gemini-2.5-flash`, returned 404, "no longer
  available to new users" (00:16).
- **Fixed:** pinned `gemini-3.8-flash` in `.env` (EXPERIMENTS.md E1). The tools moved, exactly as the brief warned.

### F3. TTS returned 200 with no audio
- **What happened:** the first TTS model (`gemini-2.5-flash-preview-tts`) answered HTTP 200 with no
  `content` in the response. The code crashed with a bare `KeyError: 'content'`, and the call was never logged.
- **Fixed:** a pinned TTS model, and `gemini_tts` now raises "200 but no audio" and logs the call either way.

### F4. Gemini 503 "high demand" all day
- **What happened:** every `pipeline.script` run failed on its first line: 6 runs on `gemini-3.8-flash` between
  01:12 and 12:19, each a 503 after 3 attempts with backoff, then a read timeout at 180 s during the first full
  film run. That timeout was not logged at the time, because the exception was raised before the log line was
  written. Timeouts are logged now.
- **Tried:** waiting and retrying; `gemini-3.7-flash` (also 503); `gemini-3.8-flash-lite` (404: not on my
  key's list, my mistake for not checking it first).
- **Worked around:** the script saves after every line, so any successful call is kept. `pipeline.film
  --keep-going` builds the film from what is cached, and timeouts are now logged too. **Still open:** there is
  no Afaan Oromo narration yet. Next: retry outside peak hours, and try `gemini-3.5-flash-lite`, which is on
  my list.

### F5. My API keys nearly went to GitHub
- **What happened:** `.gitignore` had been written with quote marks (`".env" `), so it matched nothing, and
  `git add .` committed `.env`. GitHub push protection blocked the push (a GCP API key and a Cloudflare token).
- **Fixed:** rewrote `.gitignore` as plain lines, removed `.env` from the unpushed commit (`git rm --cached`,
  amend), and pushed. The keys never left my machine. I did not use GitHub's "allow secret" link.

### F6. FLUX.1 schnell rejects a seed
- **What happened:** 400, "Additional or unevaluated properties '/seed' not allowed". On Workers AI, schnell's
  schema is only `prompt` and `steps`, so it can't be seeded or given a reference image.
- **Fixed:** keyframes moved to FLUX.2 klein 4B (multipart input with seed and reference images; E4).

### F7. A seed doesn't reproduce an image
- **What happened:** FLUX.2 klein with the same prompt and seed gave a similar but different image (E5).
- **Worked around:** reproducibility comes from caching each generated file under a hash of its inputs.
  A re-run reuses the file instead of hoping the seed repeats.

### F8. Identity and setting drift toward non-Ethiopian defaults
- **What happened:** "Ethiopian Oromo" produced South Asian-looking faces, a European fireplace, European
  colleagues and a light-skinned hand (E7, E10).
- **Fixed:** visible features in the character descriptions (skin, features, hair texture) and concrete
  settings in the shot prompts (E8, E10). This is evidence about how the model handles my people, not only my
  language: its default "person" is not Ethiopian.

### F9. Reference images forced portraits
- **What happened:** with a reference portrait as input, wide shots came back as portraits (E6, E9).
- **Fixed:** shot size first in the prompt, "shown in this scene, not as a portrait", and no references in
  extreme wide shots.

### F10. Vertical subtitles ran off the screen
- **What happened:** 40-character lines at size 46 were wider than the 720 px vertical frame (E12).
- **Fixed:** wrapping and sizing per aspect ratio, with the safe-area margin.

### F11. Wan 2.2 needs more GPU memory than Kaggle gives
- **What happened:** the Wan 2.2 README says TI2V-5B with every memory-saving flag "can run on a GPU with at
  least 24GB VRAM". Kaggle's T4 has 16 GB.
- **Worked around:** the shots stage uses a Wan clip if one exists and otherwise a Ken Burns move in FFmpeg, so
  all ten shots currently use pan and zoom in varied directions. The attempt on Kaggle is documented in
  `kaggle/wan_shots.md` (E16). *Record here what actually happens when it is tried.*
