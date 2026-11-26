# Design

## Audience and intent (written before anything was generated)

- **Who watches:** my family and Oromo friends at home and in the diaspora.
- **Where:** on their phones, so vertical (9:16) comes first.
- **What they should feel at the end:** pride in where they come from, and the sense that a teacher's
  lessons travel forward into his son's work.
- **Define:** *How might I show my parents, and the family who live far from Leka Dulecha, that what my
  father taught about our land is what I now do in my work?*
- **Why Afaan Oromo:** it is my family's language and I speak it natively, so I can judge the translation and
  the voice myself. The brief could not confirm that the models handle Oromo, which made it worth testing.

Logline (in `storyboard.json`): *A teacher's son from Leka Dulecha grows up learning the map of his land, and
becomes the engineer who connects it.*

## Every shot has a reason

| Shot | Size | Reason |
|---|---|---|
| s01 | extreme wide | Establishes home: the hills where everything begins. |
| s02 | medium | Introduces the father, the teacher whose lessons shape the film. |
| s03 | close-up | The boy receiving the lesson the whole film is built on. |
| s04 | medium | Introduces the mother and the warmth of home. |
| s05 | wide | The journey begins: leaving home to study. |
| s06 | close-up | The motif: the father's map becomes the son's systems. |
| s07 | medium | Where he is now: the work itself. |
| s08 | insert | Why the work matters: it reaches families like his. |
| s09 | medium | The emotional core: back home with his parents. |
| s10 | extreme wide | Returns to the opening hills to close the circle. |

The structure is a circle (hills → home → away → work → home → hills). The motif is **mapping**: the chalk
map in s02, then "My father mapped the land. I learned to map systems" in s06. The music follows the same
shape: m1 sparse, m2 adds percussion as he leaves, m3 brings back the opening theme, warmer.

## User test 1: the smoke-test sample (prototype)

**What I showed:** the one fully produced shot, the Oromo line *"Ani bara 1998tti, Wallagga Bahaa, Leeqaa
Dullachaatti dhaladhe."*, its 10.16 s voice clip and the first FLUX keyframe of the hills. Viewers are
described by their relation to me only.

| Viewer | What I showed them | What they said | What changed |
|---|---|---|---|
| 1 (family) | The keyframe with the voice playing | "Looks like home, but the voice feels cold." | Kept the hills as the opening image (s01). The voice became the first thing to fix (E3). |
| 2 (Oromo speaker) | The Oromo sentence as text, then the voice | "It reads the English instruction aloud, and the place name sounds wrong." | The TTS call sends only the line, with style now an A/B switch (E3). The script prompt fixes the Qubee spellings **Leeqaa Dullachaa** and **Wallagga Bahaa** (`pipeline/script.py`). |
| 3 (colleague) | The voice with the English line as a subtitle | "Too long for one sentence." | A 7 s target per line: the script prompt asks for it, and the narration stage flags any clip over 7 s or longer than its shot (`pipeline/narration.py`). |

## User test 2: the radio cut

**What I showed:** `outputs/radio_cut/radio_cut.mp4`, 74 s across 10 shots. Because Gemini returned 503 all
day (FAILURES.md F4), this cut had **no voice**: placeholder music on black at the planned shot lengths.

| Viewer | What I showed them | What they said | What changed |
|---|---|---|---|
| 1 | The music-only radio cut | "Just music on black. I felt nothing." | The radio cut only works with the voice. The test will be repeated once narration exists, and English subtitles were added to the assembled cut so the story reads even before the voice is in. |
| 2 | The same cut | "The music never changes." | Kept as a placeholder. The real score follows the three cues m1–m3 from ACE-Step (`pipeline/music.py`), and the placeholder now shifts with fades. |
| 3 | The same cut | "Long, but I could feel the rhythm." | Kept the 74 s plan. Shot lengths are recomputed from the real narration (`pipeline/timeline.py`). |

## How the storyboard changed, and why

| Change | Cause |
|---|---|
| Fixed Qubee spellings of place names in the script prompt | User test 1, viewer 2 |
| A 7 s target per spoken line | User test 1, viewer 3 |
| Shot length = max(planned, narration + 0.8 s) | User test 2, viewer 3; the voice sets the cut |
| Characters described with skin tone, features and hair texture | Keyframe tests E7–E8: "Ethiopian Oromo" alone gave non-Ethiopian faces |
| s04 hearth → charcoal brazier in a round mud-walled house; s07 "Ethiopian colleagues"; s08 "dark-skinned hand" | E10: generic words gave European settings |
| s10 "a tiny distant figure … seen from behind" | E9: the reference portrait pulled the wide shot into a portrait |

## User test 3: the near-final cut

*To do after narration and the score are in:* show `outputs/film/mapping_home_9x16.mp4` to at least three
people from the audience, on their phones. Ask what they felt at the end, which line was unclear or sounded
wrong, and what felt too slow or too fast. Record it here in the same table form, with the storyboard change
each answer caused.

| Viewer | What I showed them | What they said | What changed |
|---|---|---|---|
| | | | |
