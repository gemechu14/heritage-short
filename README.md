# Mapping Home — a heritage short, made by a pipeline

A 60–90 second film about my family — my father Bulti Firissa, a geography and history teacher in
Leka Dulecha, East Wollega, my mother Tujube Regasa, and the son who learned to map systems — narrated in
**Afaan Oromo** with English subtitles, in vertical (9:16) and horizontal (16:9).

The film is not edited by hand. One file, [`storyboard.json`](storyboard.json), describes every shot,
and a pipeline of small stages turns it into keyframes, moving shots, narration, music and a finished
edit. Change one line in the storyboard, run one command, and only that shot is regenerated.

## Run it

```bash
git clone https://github.com/gemechu14/heritage-short.git
cd heritage-short
python -m pip install -r requirements.txt      # Windows: py -m pip install -r requirements.txt
cp .env.example .env                           # then add your keys (see below)
python -m pipeline.film --keep-going           # or: make film
```

You also need **FFmpeg** on your PATH (`winget install Gyan.FFmpeg`, `brew install ffmpeg`, `apt install ffmpeg`).

The film lands in `outputs/film/mapping_home_16x9.mp4` and `outputs/film/mapping_home_9x16.mp4`.
Running it again with no changes makes **no model calls**: every stage is cached by a hash of its inputs.
`--keep-going` lets the film finish from cached results when the translation or voice API is down.

### Keys (`.env`, never committed)

| Variable | Where to get it | Used by |
|---|---|---|
| `GEMINI_API_KEY` | Google AI Studio (free tier) | script (translation), narration (TTS) |
| `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN` | Cloudflare dashboard → Workers AI (free daily allowance) | keyframes |

Music (ACE-Step 1.5) and optional moving shots (Wan 2.2) need a GPU, so they run on Kaggle:
see [`kaggle/ace_step_score.py`](kaggle/ace_step_score.py) and [`kaggle/wan_shots.md`](kaggle/wan_shots.md).
Without them the pipeline uses a placeholder score and FFmpeg pan-and-zoom shots, and still finishes.

## What it does

| Stage | Command | Model / tool | Output |
|---|---|---|---|
| validate | `python -m pipeline.validate` | JSON Schema | fails fast on a bad storyboard |
| script | `python -m pipeline.script` | Gemini 3.8 Flash | Afaan Oromo `narration` lines, written into storyboard.json |
| narration | `python -m pipeline.narration` | Gemini 3.8 Flash TTS | one WAV per shot |
| keyframes | `python -m pipeline.keyframes` | FLUX.2 klein 4B (Workers AI) | reference sheet, then one keyframe per shot |
| shots | `python -m pipeline.shots` | FFmpeg zoompan, or Wan 2.2 clips | one clip per shot per aspect ratio |
| music | `python -m pipeline.music` | ACE-Step 1.5 on Kaggle | `outputs/music/score.wav` and the reason it was chosen |
| radio cut | `python -m pipeline.radio_cut` | FFmpeg | narration over placeholder music on black, for user tests |
| assemble | `python -m pipeline.assemble` | FFmpeg | ducked, subtitled, −14 LUFS films with the AI end card |
| costs | `python -m pipeline.costs` | — | latency and call counts from `runs.jsonl` |

Other useful commands:
- `python -m pipeline.smoke_test` — calls each provider once and lists the models your key can use.
- `python -m pipeline.keyframes refs` — make only the character reference sheet, to approve it first.
- `python -m pipeline.keyframes s03` — regenerate one shot's keyframe.
- `python -m pipeline.music --choose candidate_seed22.wav --why "..."` — pick the score and record why.

## What it costs

Measured: a full run takes about 4 minutes of local time plus API latency, and costs **$0** on the free
tiers. At paid list prices one full regeneration would cost about **$0.05**. Details in [COSTS.md](COSTS.md).

## The documents

- [DESIGN.md](DESIGN.md) — audience, intent, user tests and what they changed
- [ARCHITECTURE.md](ARCHITECTURE.md) — stages, contracts, caching, failure handling
- [EXPERIMENTS.md](EXPERIMENTS.md) — hypothesis → change → result
- [FAILURES.md](FAILURES.md) — what broke and what fixed it
- [COSTS.md](COSTS.md) — measured latency, GPU time, list-price equivalent
- [ETHICS.md](ETHICS.md) — consent, licences, labelling

`runs.jsonl` has one line per model or FFmpeg call (model, parameters, seed, latency, attempts, status,
cost), including every failure. `outputs/` keeps the generated files so a run can be inspected.

Built with Claude as a coding partner: it wrote most of the stage code under my direction. I chose the
story, ran and judged every stage, checked the Afaan Oromo, and made the decisions recorded here.
