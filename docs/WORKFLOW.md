# Working agreements (Build Map T0.6)

## Daily loop

```powershell
.\tasks.ps1 check                  # before every commit: lint, unit tests, secret scan, claims scan
.\tasks.ps1 test-int               # when touching the database or the pipeline (needs db-up)
npm --prefix frontend test         # when touching the web app
```

## Commits

- One topic per commit; start the message with the Build Map task ID, for example
  `T5.3: BolnaVoiceProvider against the documented contract`.
- Never commit `.env`, real phone numbers, real transcripts, `data/businesses.local.yaml`, or raw
  spike captures. `scripts\check_no_secrets.py` is the safety net, not the plan.
- If a Bible fact changes (a VERIFIED or ASSUMPTION), update the register in the same commit.

## Tests

- Pure logic gets unit tests; anything touching the database gets an integration test against real
  PostgreSQL, never a mock of the database.
- Every safety rule has a test that fails if the rule is broken: consent re-check, no double dial,
  forged webhook ignored, silence never worded as unavailable.
- Provider payload shapes come from **captured** responses once they exist. Until then they are
  labelled assumptions in `app/providers/bolna.py` and in the tests.

## Fixtures from real calls

1. Capture with the spike scripts (`spikes/bolna/`). Captures stay local (git-ignored).
2. Redact: `python scripts\redact_fixture.py CAPTURE backend\tests\fixtures\bolna\NAME.json`.
3. **Read the result before committing.** Transcripts can contain names or addresses, and a real
   shopkeeper's speech needs their consent.

## Decisions

Add a row to the decision log in `SONAR_BIBLE_v2.md` (section 43) for anything that changes a rule.
Amend, never delete: mark the old row as amended and say by which decision.

## Claims

Run `python scripts\check_claims.py` whenever you touch the business documents. A number goes in
only if we measured it or can source it.
