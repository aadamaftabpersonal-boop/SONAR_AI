# Limitations and honest claims

What Sonar does not do, does not know, or has not yet proven. Keep the pitch consistent with this
file. Last updated with the build state described in `README.md`.

## What is proven, and what is not

Last checked 2026-10-27.

| Claim | Status |
|---|---|
| The pipeline (search, consent-gated calls, validation, results) works | Proven on the **simulator** and on **mocked** Bolna HTTP. |
| Bolna can place the call and return a usable record | **Shown on 4 test calls** to team phones (2026-10-25), placed with the spike scripts: the call connects, the AI disclosure is spoken, the item is filled in, and the execution record carries a transcript and structured answers. Four role-played calls are not a sample. |
| The full live path through Sonar works | **Not proven.** No live call has yet gone from a search in Sonar, through the webhook, to a result on screen (milestone M1). Webhooks have not been received from Bolna at all (spikes S-3, S-5). |
| Answers are accurate | **Not measured.** No answer has been checked against reality. The tool for it exists (`scripts/ground_truth.py`); the number does not. |
| Speech-to-text understands shopkeepers | **Not shown.** On a clear English test call it heard "milligrams" as "millie gills". An Indian-English transcriber with keywords is planned and untested. |
| Shopkeepers will agree to take these calls | **Not tested.** No business has been asked. |
| Businesses will pay | **Not tested.** See `docs/BUSINESS_CASE.md`: every hypothesis is "not run". |
| The early stop saves calls | Shown on the simulator. **No measured saving on real calls.** |
| Hindi or Kannada works for shopkeepers | **Not tested** (spike S-8). |
| Cost per call | **Not known.** Bolna reports a cost field (3.0 per started 30 s on our calls), but its unit is not confirmed. |

## What the first live calls showed

- **The speech-to-text can mishear units and product words.** One call turned "500 milligrams" into
  "millie gills". The agent then treated the answer as a different product and never got a price.
  What changed: units are spoken in full, the agent asks once more when an answer is unclear, and
  the validator now records such a call as **Uncertain**, never as "different" or "unavailable".
  What is still open: transcriber keywords, an Indian-English transcriber and voice, and a re-test.
- **The agent can drift off-script** (it explained a word instead of re-asking). A guard was added to
  the prompt; whether it holds is untested.
- **Voicemail detection hung up on a real person** who was listening quietly (two calls, about 10 s
  in). It is off for tests. With it off, voicemail is caught only by the extraction (`call_outcome`),
  which is a model's judgement.
- **The trial plan calls verified numbers only.** Calling any real shop needs a paid plan or
  per-number verification.
- **The agent configuration lives in Bolna's dashboard,** not in this repository. The prompt in
  `docs/agent/` must be pasted in by hand; nothing checks that the two match.

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

## The map

- **Tiles come from OpenStreetMap's public servers**, which allow light use with visible
  attribution, offer no uptime guarantee, and can block heavy use without notice. That is fine for a
  demo. For real traffic, switch provider by setting `VITE_TILE_URL` (see `frontend/src/tiles.ts`).
- **Using the map tells the tile server roughly what area the viewer is looking at**, and their IP
  address, as any web map does. The Radar tab sends nothing to any map service.
- **There is no address search.** You choose a place by clicking the map, using your location, or the
  demo locality. Address search would need a geocoding service with its own usage rules.
- **Shop positions are straight-line distance and compass direction** from the search point, not
  driving routes.

## Safety limits

- **Medical content is blocked conservatively, not completely.** The blocked-terms list is a
  starter set and has **not been reviewed by a pharmacist**. It must be reviewed before any real
  pharmacy pilot. Sonar gives no medical advice and says so.
- **A prompt-injection check exists but is a second layer, not a guarantee.** Item text is limited
  to a character whitelist, a word count and a few instruction-like phrases. A determined attacker
  with the access key is out of scope.
- **Legal position on automated calls to businesses is unresolved** (B-05). We have no legal
  advice. The consent-only policy and the AI disclosure are choices, not a compliance claim.
- **Recording and retention** by the voice provider are not settled (spike S-9). Our test calls
  produced a recording, so assume calls are recorded: never tell a business otherwise.

## Things that will need real data to settle

- Webhook fields, status order and redelivery (spike S-5). The extraction shape is now known (S-7).
- What unit Bolna's `total_cost` is in.
- What caller number shops see, and whether calls are marked spam. The default number reached the
  team's Indian phones; pickup by real shops is untested.
- Pickup rate, answer accuracy, the time a search takes, and the saving from stopping early.

## Built, with limits

- **Live ticker** (`FEATURE_LIVE_TICKER`): on simulated calls it replays the script line by line. On
  real calls it shows whatever transcript Bolna returns while the call is in progress; whether Bolna
  returns any text before the call ends is not yet known (spike S-13). If it does not, the panel
  says "No live text yet" rather than inventing anything. A real shop's words are never shown live.
- **Reuse of recent answers** (`FEATURE_CACHE_REUSE`): a shop's answer from the last hour (price
  within 24 hours) to the same question is shown as "Earlier call, HH:MM (not called again)". The
  shop may have sold out since; the time is always shown.
- **Browser end-to-end test** (`e2e/`): demo mode only; it has not been run yet.

## Not built

Inbound shop line, audio replay, voice input, race clock, evidence replay with context, question
compiler, standing watches, a developer API wrapper, and the sponsor benchmark (deferred: the team
plans to keep Wave 2 to the ticker). See `README.md` for the build state.
