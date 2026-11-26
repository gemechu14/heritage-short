# Architecture

## One contract, many stages

```
storyboard.json ──validate──┬─ script ──────► storyboard.json (narration, Afaan Oromo)
 (schema/…json)             ├─ narration ───► outputs/narration/<shot>_<hash>.wav + manifest.json
                            ├─ keyframes ───► outputs/keyframes/refs/*.jpg → <shot>_<hash>.jpg + manifest.json
                            ├─ shots ───────► outputs/shots/{16x9,9x16}/<shot>_<hash>.mp4 + manifest.json
                            ├─ music ───────► outputs/music/score.wav + choice.json   (ACE-Step on Kaggle)
                            ├─ radio_cut ───► outputs/radio_cut/radio_cut.mp4
                            └─ assemble ────► outputs/film/mapping_home_{16x9,9x16}.mp4
                                                         every call ─► runs.jsonl
```

`storyboard.json` is the only thing a person edits. It holds the title, audience and intent, the
language, the voice, a **style block** added to every image prompt, the **characters** (one fixed
description each), the **music cues** with timecodes, and 8–12 **shots**. Each shot has an id, a
duration, a shot size, a stated reason, the characters in it, an image prompt, a motion type and
direction, a motion prompt, the English line, the Afaan Oromo line and a seed.

`pipeline/validate.py` checks it against [`schema/storyboard.schema.json`](schema/storyboard.schema.json)
(JSON Schema 2020-12) plus cross-field rules: unique ids, known characters, 60–90 s total, cue end after
start. Every stage calls `load_storyboard()`, so no stage runs on an invalid storyboard.

## Stage contracts

| Stage | Reads | Writes | Cache key |
|---|---|---|---|
| script | `narration_en` | `narration` (only if empty, saved after every line) | the field itself: a filled line is never overwritten |
| narration | `narration`, `voice` | `outputs/narration/<shot>_<hash>.wav`, `manifest.json` (file, seconds) | text, voice, model, style |
| keyframes | `characters`, `style_block`, `image_prompt`, `shot_size`, `seed` | `refs/<character>_<hash>.jpg`, `<shot>_<hash>.jpg`, `manifest.json` | full prompt, seed, model, steps, size, reference-image hashes |
| shots | keyframe manifest, narration manifest, `motion` | `<aspect>/<shot>_<hash>.mp4`, `manifest.json` (file, length) | keyframe file, motion, shot length, aspect (or the Wan clip's content hash) |
| music | `music.cues`, total length | `ace_step_job.json`, `score.wav`, `choice.json` | the chosen candidate |
| assemble | all manifests, `narration_en`, `title` | the two films, `subtitles_en.srt`, `loudness.json` | not cached (about 2 minutes of FFmpeg) |

Because each output file name contains the hash of its inputs, a changed input produces a new file and an
unchanged one is found on disk. Changing one shot's `image_prompt` regenerates one keyframe and two clips;
changing a character's description regenerates that character's reference and every shot it appears in.
The manifests point each stage at the current file, so old files stay as a record of earlier iterations.

## Timing: picture cut to the voice

[`pipeline/timeline.py`](pipeline/timeline.py) is the single source of timing. A shot lasts
`max(duration_s, narration seconds + 0.5 s lead + 0.3 s tail)`, rounded to whole frames at 24 fps. The radio
cut, the shots stage and the assembly stage all call it, so a longer Oromo line lengthens its shot
everywhere, and the shots stage re-renders only that shot's clips.

## Consistency

1. **Reference sheet first.** One portrait per character (`python -m pipeline.keyframes refs`), all with the
   same seed and style block. These are the golden references.
2. **Reference images in every shot.** FLUX.2 klein takes up to four input images; each shot sends the
   reference portraits of the characters in it, plus their exact descriptions and the style block.
3. **Except extreme wide shots,** where a reference portrait pulled the frame into a close portrait
   (EXPERIMENTS.md E9), so only the description is sent.
4. **Square keyframes, subject centred,** so both 16:9 and 9:16 are crops of the same image.

## Assembly

1. The narration WAVs are joined on the timeline (silence between lines).
2. Levels first: narration is normalised to −16 LUFS, the score to −26 LUFS.
3. Ducking: `sidechaincompress=threshold=0.02:ratio=6:attack=300:release=1500`, with the voice as the key.
   The score fades in over 1.5 s and out over 3.5 s.
4. Loudness: two-pass `loudnorm` to −14 LUFS integrated and −1 dBTP, with the measured result saved to
   `outputs/film/loudness.json`.
5. Picture: the clips are joined in order with a 0.6 s fade in and out, then a 3 s end card with the title,
   "Made with AI" and credits built from what actually made this cut.
6. Subtitles: English ASS subtitles burned in, at most 2 lines (40 characters in 16:9, 26 in 9:16), with the
   vertical version raised 22% from the bottom to stay clear of phone buttons. A separate `subtitles_en.srt` is
   written too.
7. Export: H.264 (CRF 20) and AAC 192k at 24 fps, with `+faststart`.

## Failure handling

- **Retries.** Every HTTP call goes through `request_with_retry`: 3 attempts with backoff of 2 s and 4 s on
  429/500/502/503/504 and dropped connections.
- **Everything is logged, including failures.** Each Gemini, Cloudflare and FFmpeg call appends a line to
  `runs.jsonl` with stage, provider, model, parameters, seed, latency, attempts, status, cost and error. Cache
  hits are logged too, with `cache_hit: true`. Timeouts are logged before they are re-raised.
- **Resumable work.** The script stage saves after every line, so a 503 halfway keeps what was translated.
- **Graceful degradation.** `python -m pipeline.film --keep-going` continues past a failing script or narration
  stage (an API outage) with what is cached. A missing Wan clip falls back to a Ken Burns move, and missing
  ACE-Step candidates fall back to a labelled placeholder pad. The end card's credits say which was used.
- **Clear errors.** A 200 response with no audio raises "200 but no audio" instead of a bare `KeyError`. A
  missing FFmpeg, keyframe or out-of-date clip stops with the command to run.
- **Secrets.** Keys live only in `.env`, which is git-ignored, and are never logged.
