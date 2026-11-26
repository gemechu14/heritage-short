# Costs

Everything here ran on free tiers, so the actual spend is **$0**. The list-price column shows what the same
work would cost on paid tiers. Measured numbers come from `runs.jsonl` (`python -m pipeline.costs` prints the
table). Prices were checked on 2026-11-26 from the official pricing pages linked below.

## Measured latency per stage

| Stage | Provider / model | Calls (ok / failed) | Mean latency | Notes |
|---|---|---:|---:|---|
| smoke | Gemini `list_models` | 3 / 0 | 1.6 s | |
| smoke | Gemini 3.8 Flash (text) | 2 / 0 | 169.7 s | one call needed 3 attempts under load (00:25) |
| smoke | Gemini 3.8 Flash TTS | 2 / 0 | 7.7 s | 10.16 s of audio for one 10-word sentence |
| smoke | FLUX.1 schnell (Workers AI) | 3 / 0 | 11.0 s | 1024×1024, 4 steps |
| script | Gemini 3.8 / 3.7 Flash, 3.8 Flash-Lite | 0 / 8 | — | 503 or 404 all day (FAILURES.md F4) |
| keyframes | FLUX.2 klein 4B (Workers AI) | 21 / 0 | **8.1 s** (5.0–13.7) | 1024×1024, 4 steps; references count as inputs |
| keyframes | FLUX.1 schnell | 0 / 1 | — | rejects `seed` (F6) |
| shots | FFmpeg zoompan, per clip | 20 / 0 | **4.6 s** (max 10.2) | 10 shots × 2 aspect ratios, CPU |
| music | FFmpeg placeholder pad | 1 / 0 | 2.9 s | until ACE-Step candidates arrive |
| radio cut | FFmpeg | 2 / 0 | 12.0 s | |
| assemble | FFmpeg: mix + 2-pass loudnorm + 2 renders | 6 per run | ~112 s per run | mix 19 s, loudnorm passes 5.5 + 0.6 + 5.5 s, render 41 s per aspect |

**A full run with nothing cached:** about 14 × 8 s of keyframes (~2 min, sequential), about 1.5 min of clips,
and about 2 min of assembly, so **5–6 minutes**, plus translation and TTS when Gemini is up. A re-run with
nothing changed makes **0 model calls**, and only assembly (~2 min) is redone.

**GPU minutes:** none used yet. ACE-Step 1.5 (music) and Wan 2.2 (optional shots) run on Kaggle. Add their
measured times from `ace_step_log.json` and the Wan runs here. Kaggle gives about 30 GPU hours a week.

## List-price equivalent

| Item | Price (paid tier) | This film | Cost |
|---|---|---|---:|
| FLUX.2 klein 4B output | $0.000287 per 512×512 output tile | 1024² = 4 tiles × 14 images (4 refs + 10 shots) | $0.0161 |
| FLUX.2 klein 4B reference input | $0.000059 per 512×512 input tile | 9 reference images × 4 tiles | $0.0021 |
| Gemini 3.8 Flash TTS | $0.00225 per 10 s of audio | ~75 s of narration | ~$0.017 |
| Gemini 3.8 Flash (translation) | $0.75 / 1M input, $3.75 / 1M output tokens | 8 lines × ~1,000 input + ~60 output tokens | ~$0.008 |
| ACE-Step 1.5 / Wan 2.2 | open weights on Kaggle's free GPU | — | $0 |
| **One full regeneration** | | | **≈ $0.04–0.05** |

The whole set of keyframe iterations so far (21 klein images plus 3 experiments) would have cost about **$0.03**.

**Free allowances that actually bind:**
- **Workers AI:** 10,000 Neurons a day. One klein keyframe is 4 × 26.05 = 104 Neurons, plus 21.5 per reference
  image, so a full set of 14 is about 1,650 Neurons, roughly 6 full sets a day.
- **Gemini:** the free tier is "free of charge", but in practice the limit today was **capacity** (503
  errors), not quota.

Sources: [Workers AI pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/),
[Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing). Gemini prices double on 2027-01-01.

## Frontier comparison
No frontier lane access (Nano Banana, Omni Flash, Lyria 3.5) was available, so there is no comparison yet.
