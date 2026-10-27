# Sponsors: access and status (Build Map SP-1)

Sonar's baseline is **Bolna only** (Bible D-023). This file records what we know about the other
sponsors so we never claim an integration we did not build. Status uses the Bible's vocabulary
(section 0.1). **Nothing here has been verified by running anything.**

| Sponsor | Possible role (only through Bolna's configuration) | Status (2026-10-27) | What we do not know |
|---|---|---|---|
| Bolna | Voice agent platform: calls, execution records, extraction | Calls and execution pulls **work on 4 test calls** to team phones (spike scripts, 2026-10-25), and the parser is tested against the captured extraction shape. Sonar's own live path (search to result, with webhooks) has **not** run yet (M1). | Webhook behaviour (S-5), cost unit, retention (S-9), caller ID |
| Sarvam | Indian-English voice (Bulbul) and Indian-English or Hindi speech-to-text (Saaras), chosen in the agent's settings | `PROPOSED`, **planned trial** (D-056). Credits being requested | Whether it transcribes shopkeepers better than the current setup; whether our own key can be used in Bolna |
| Deepgram | Speech-to-text, the comparison arm for Sarvam (with keywords) | `PROPOSED`, **planned trial** (D-056). Credits being requested. It may already be the default transcriber: check the agent's settings | Which transcriber the agent uses today |
| Cartesia | Alternative voice | `PROPOSED`, backup only: tried only if no Sarvam voice is clear enough | Indian-English voice range |
| Plivo, Exotel | Telephony route connected through Bolna's supported-provider setup | `BLOCKED` until an India-registered business and KYC are confirmed (B-07). Not requested for the buildathon | Whether the team has such an entity |

A sponsor moves from `PROPOSED` only after a recorded call through it, logged in
`docs/FEASIBILITY.md` (S-8) with the date.

## Rules for mentioning a sponsor

- Say only what is true at the level reached: "documented" or "proposed" is not "integrated".
- A logo or an installed library is not evidence.
- Never route one real call through several providers to show them all.
- If we have no access, the honest status is `NOT_MEASURED`; never fill numbers from marketing text.

## Open actions

- [ ] Ask the organisers which partner credits are available to participants (the credits form
      mentions partner credits).
- [ ] Run the comparison in `docs/agent/VOICE_AND_TRANSCRIBER.md`, then keep one transcriber and
      one voice. If neither partner beats the current setup, say so and keep the baseline.
