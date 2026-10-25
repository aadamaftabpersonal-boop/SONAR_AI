# Sponsors: access and status (Build Map SP-1)

Sonar's baseline is **Bolna only** (Bible D-023). This file records what we know about the other
sponsors so we never claim an integration we did not build. Status uses the Bible's vocabulary
(section 0.1). **Nothing here has been verified by running anything.**

| Sponsor | Possible role (only through Bolna's configuration) | Status | What we do not know |
|---|---|---|---|
| Bolna | Voice agent platform: calls, webhooks, extraction | `VERIFIED_NOT_IMPLEMENTED` against live Bolna. The provider is written and tested over mocked HTTP; it has not touched the real service. | Real payload shapes, cost, number rules, retention (spikes S-4 to S-10) |
| Sarvam | Indic speech or language option inside the agent configuration, if spike S-8 shows the default is weak on Hindi or Kannada | `PROPOSED` | Whether Bolna exposes it for our plan; whether credits are available |
| Deepgram | Alternative speech-to-text inside the agent configuration | `PROPOSED` | Same |
| Cartesia | Alternative voice inside the agent configuration | `PROPOSED` | Same |
| Plivo, Exotel | Telephony route connected through Bolna's supported-provider setup | `PROPOSED`, `BLOCKED` until an India-registered business and KYC are confirmed (B-07) | Whether the team has such an entity |

## Rules for mentioning a sponsor

- Say only what is true at the level reached: "documented" or "proposed" is not "integrated".
- A logo or an installed library is not evidence.
- Never route one real call through several providers to show them all.
- If we have no access, the honest status is `NOT_MEASURED`; never fill numbers from marketing text.

## Open actions

- [ ] Ask the organisers which partner credits are available to participants (the credits form
      mentions partner credits).
- [ ] After spike S-8, decide whether any partner is actually needed. If not, say so and keep the
      baseline Bolna-only.
