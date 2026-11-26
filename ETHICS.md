# Ethics: consent, licences, labelling

## Consent

The film depicts three real people as AI-generated illustrations: my father, my mother and me. No real
photograph or recording of anyone is used as input; the images are generated from text descriptions. No one's
real voice is cloned: the narration uses a stock Gemini TTS voice ("Kore").

> **To complete before the film is published.** For each person, record who gave consent, when, how
> (written message, voice note, in person), and to what exactly: being depicted in AI-generated images, being
> named, and the specific narration lines said about them. Their words in the film must be words they agreed
> to. If someone does not consent, remove them from the storyboard (their character and shots) before release.

| Person | Shown / named / voiced | Consent given by | Date | How | What they agreed to |
|---|---|---|---|---|---|
| Gemechu Bulti (me) | shown (s03, s05–s07, s09, s10), narrator's words | myself | 2026-11-26 | — | all of it |
| Bulti Firissa (father) | shown (s02, s09), named (s02) | *to fill* | | | |
| Tujube Regasa (mother) | shown (s04, s09), named (s04) | *to fill* | | | |

The colleagues in s07 and the farmer's hand in s08 are generated, not real people.

## Private data sent to free endpoints

Free tiers may use what they receive to train their models. What was sent: the English narration lines
(names, birthplace, employer), character descriptions and shot prompts. No photos, ID numbers, addresses or
other family details were sent. My parents' names appear in two narration lines, with their consent recorded
above.

## Licences

| Component | Licence / terms | Use here |
|---|---|---|
| FLUX.2 klein 4B (Black Forest Labs), on Cloudflare Workers AI | Apache 2.0 (the 9B variant is non-commercial and is **not** used) | all keyframes |
| FLUX.1 schnell, on Workers AI | Apache 2.0 | smoke test only |
| Gemini 3.8 Flash and Flash TTS (Google) | Gemini API Terms of Service; outputs may be used, free-tier data may be used by Google | translation and narration |
| ACE-Step 1.5 | MIT; trained on licensed, royalty-free and synthetic data; outputs usable commercially | score |
| Wan 2.2 TI2V-5B | Apache 2.0 | optional moving shots |
| FFmpeg (Gyan build) | GPL (full build), used as a tool; not distributed in this repository | editing |
| This repository's code | yours to choose (e.g. MIT) | |

Style prompts describe qualities (warm, hand-painted, soft golden light, film grain) and never name a living
artist.

## Labelling

- **In the film:** a 3-second end card reading "Made with AI", with credits listing every model used. The
  credits are generated from what actually made that cut.
- **When posting:** switch on the platform's AI-content disclosure (YouTube "altered or synthetic content",
  TikTok "AI-generated", Meta "AI info"), and say in the post itself that the images, voice and music are
  AI-generated.
- **Provenance:** files are exported straight from the pipeline with no step that strips metadata. Any
  watermarks or provenance data from the providers are left as they are.
