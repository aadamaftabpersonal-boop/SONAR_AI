# Voice and transcriber: setup and comparison (D-056)

Goal: an Indian-English voice that sounds natural to shopkeepers, and a transcriber that does not
mishear units and product names ("500 milligrams" came out as "millie gills" on 2026-10-25). Both
are chosen in the Bolna agent's settings; no Sonar code changes. The AI disclosure stays word for
word: the voice may sound Indian, the agent still says it is an automated assistant.

Settings below are from Bolna's provider docs, read 2026-10-27
(<https://www.bolna.ai/docs/sarvam-voice.md>, <https://www.bolna.ai/docs/providers/transcriber/sarvam.md>).
Check the dashboard: names and models change.

## 1. Before you change anything

Write down the current settings in `docs/FEASIBILITY.md` (S-8): voice provider, voice, transcriber
provider and model, language. If the transcriber is Deepgram, that is the setup that misheard the
unit, and it becomes arm A of the comparison.

## 2. Voice (synthesizer)

| Setting | Value | Note |
|---|---|---|
| Provider | Sarvam | |
| Model | `bulbul:v3` | 16 voices that work in every language, so the same voice carries over to Hindi |
| Language | `en` | Bolna maps it to Indian English (`en-IN`). Required |
| Voice | try `shubh`, `rahul`, `amit`, `manan` (male, lower); `kavya`, `ritu`, `shreya` (female) | Sarvam on Bolna has **no pitch control**; pick a lower voice instead |
| Speed | 0.9 to 1.0 | slower makes prices and strengths clearer |

Pick by ear: place one short call per candidate voice (case 1 of `ACCEPTANCE_CALLS.md`) and have
someone who did not set it up rate it 1 to 5 for clarity and naturalness. Keep the highest; record
the ratings in S-8.

## 3. Transcriber: compare two, keep one

Run the same acceptance calls (`ACCEPTANCE_CALLS.md`) on each arm, with the same voice, prompt and
model. Change nothing else between arms, or the comparison means nothing.

| Arm | Provider and model | Language | Keywords |
|---|---|---|---|
| A | Deepgram (the newest model the dashboard offers) | English (India) if offered | the list below |
| B | Sarvam `saaras:v4` | `en` | the list below (v4 is the only Sarvam model that accepts keywords) |

Keywords: `Paracetamol, milligrams, milligram, mg, rupees, tablet, strip, available, stock`
(add each demo item's name).

Score per arm, from the transcripts: number of calls with a misheard item, unit or price out of the
calls made. Keep the arm with fewer, as "x of N". With so few calls this is a signal, not a
benchmark; say so.

## 4. After choosing

1. Record the chosen voice, transcriber and the two scores in `docs/FEASIBILITY.md` (S-8).
2. Amend D-056 in the Bible decision log with the winner.
3. Move the chosen sponsor in `docs/SPONSORS.md` from `PROPOSED` to used, citing the calls.
4. Then, and only then, say it in the pitch.
