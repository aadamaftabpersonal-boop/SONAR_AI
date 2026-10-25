# Limitations and honest claims

What Sonar does not do, does not know, or has not yet proven. Keep the pitch consistent with this
file. Last updated with the build state described in `README.md`.

## What is proven, and what is not

| Claim | Status |
|---|---|
| The pipeline (search, consent-gated calls, validation, results) works | Proven on the **simulator** and on **mocked** Bolna HTTP. |
| It works with the real Bolna API | **Not proven.** No real call has been placed. The Bolna field names are taken from documentation, not from captured responses. |
| Answers are accurate | **Not measured.** No answer has been checked against reality. The tool for it exists (`scripts/ground_truth.py`); the number does not. |
| Shopkeepers will agree to take these calls | **Not tested.** No business has been asked. |
| Businesses will pay | **Not tested.** See `docs/BUSINESS_CASE.md`: every hypothesis is "not run". |
| The early stop saves calls | Shown on the simulator. **No measured saving on real calls.** |
| Hindi or Kannada works for shopkeepers | **Not tested** (spike S-8). |

## How the product behaves, by design

- **Reported, not verified.** Every answer is what a business said on a call, with the time and
  a quote. It is not independently verified, and answers go stale within hours.
- **Consenting businesses only.** Sonar never calls a business without a recorded yes. That makes
  it a pilot-scale tool, not a search engine for every shop.
- **Silence is never "no".** A shop that did not answer, failed, declined, hedged or was skipped is
  never shown as unavailable.
- **Cancel stops new calls, not the call in progress.** No stop-call endpoint was found in Bolna's
  documentation, so a call already dialing finishes and is recorded.
- **One process.** The call scheduler runs inside a single API process (one worker). It is not built
  for many users at once.
- **No user accounts.** Access is a shared demo key. Anyone with the key can start searches.
- **Search counts are searches, not people.** The shop digest counts searches because Sonar has no
  searcher identity.
- **Early stop can skip a better shop.** It calls the likeliest shops first and stops at two
  confirmations, so the nearest or cheapest uncalled shop may never be asked. "Ask every shop"
  turns it off. How often this matters is not yet measured.
- **Shop history is small.** With few calls per shop, ordering by history is close to ordering by
  distance. It needs real volume to mean anything.

## Safety limits

- **Medical content is blocked conservatively, not completely.** The blocked-terms list is a
  starter set and has **not been reviewed by a pharmacist**. It must be reviewed before any real
  pharmacy pilot. Sonar gives no medical advice and says so.
- **A prompt-injection check exists but is a second layer, not a guarantee.** Item text is limited
  to a character whitelist, a word count and a few instruction-like phrases. A determined attacker
  with the access key is out of scope.
- **Legal position on automated calls to businesses is unresolved** (B-05). We have no legal
  advice. The consent-only policy and the AI disclosure are choices, not a compliance claim.
- **Recording and retention** by the voice provider are unknown (spike S-9). Until confirmed, do not
  tell businesses a call is not recorded.

## Things that will need real data to settle

- The extraction shape, status strings and webhook fields (spike S-5, S-6, S-7).
- Cost per call and what Bolna's `total_cost` means.
- Whether the default caller number works for Indian recipients, and whether calls are marked spam.
- Pickup rate, answer accuracy, the time a search takes, and the saving from stopping early.

## Not built

Inbound shop line, live transcript and audio, voice input, question compiler, standing watches,
a developer API wrapper, reuse of recent answers, an automated browser test, and the sponsor
benchmark. See `README.md` for the build state.
