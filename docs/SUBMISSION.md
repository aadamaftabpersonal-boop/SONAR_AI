# Submission checklist

## What we know about the event (and how well)

From a summary of the event page read on 2026-10-24 by a fetch tool, **not read in a browser**.
Confirm each date and rule on the page and with the organisers before relying on it.

| Item | What the page said |
|---|---|
| Event | Bolna Buildathon at Symphony. Build phase is fully virtual. |
| Application and build window | 15 to 31 October 2026 |
| Submission deadline | **31 October 2026** |
| Shortlist | 3 November, by email |
| Interviews | 5 to 7 November |
| Finalists announced | 8 November |
| Grand finale | 20 November, Bengaluru; only the top 3 teams travel |
| Team size | Solo, or teams of 2, 3 or 4 |
| Prizes | Total cash pool of 1.2 lakh rupees; first place also gets an interview with a YC partner |
| Judging criteria | **Not published** on the page we read |
| Credits | A separate request form exists (Bolna credits and partner credits) |

## What only you can do

- [ ] Submit the application form (fields: team size, name, email, WhatsApp number, city, college
      or company, LinkedIn or GitHub, project name, start date, idea description, how voice AI is
      used). **Confirm it is submitted and save the confirmation.**
- [ ] Submit the credits form.
- [ ] Ask the organisers for the judging criteria and the exact submission format.
- [ ] Commit and push this repository to the place the submission asks for.
- [ ] Get the Bolna key, then run the Phase 1 spike (`spikes/bolna/README.md`).
- [ ] Ask shops for consent (`docs/CONSENT_SCRIPT.md`); do the three buyer conversations
      (`docs/DISCOVERY_LOG.md`).

## Application text (edit before submitting)

**Project name:** Sonar

**Idea description:**
Sonar is a voice agent that searches the real world by calling it. Listings tell you a shop exists,
but not whether it has what you need right now. Sonar phones a few shops that agreed to be called,
asks one short factual question, and shows exactly what each shop said, when, with the evidence.
It never treats silence as "no", never calls a business without recorded consent, and labels every
simulated result as simulated. To avoid bothering shops, it stops calling once two shops have
confirmed.

**How voice AI is used:**
The agent is an automated assistant that discloses it is an AI at the start of every call, asks the
question in the shopkeeper's language, handles refusals and "stop calling me" by recording an
opt-out, and hands the call record to a validator that accepts a "yes" only if the shop's own words
in the transcript support it. Voice is essential because the facts we want exist only in shopkeepers'
heads and are reachable by phone, not by any website or API.

## Final checks (run in order, record the result)

| Check | Command | Result |
|---|---|---|
| Lint, unit tests, secrets, claims | `.\tasks.ps1 check` | |
| Database tests | `.\tasks.ps1 test-int` | |
| Frontend tests, lint, build | `npm --prefix frontend test` and `npm --prefix frontend run build` | |
| No secret in the web bundle | `.\tasks.ps1 check-bundle` | |
| Production config (if deploying) | `python scripts\check_prod_env.py --env-file .env.prod` | |
| Clean-clone run from the README | follow `README.md` on a fresh machine | |
| Demo rehearsed three times | `docs/REHEARSAL_LOG.md` | |
| Every pitch claim maps to a screen or a measurement | `docs/DEMO_SCRIPT.md` "Never say" and `docs/LIMITATIONS.md` | |

## Repository hygiene before submitting

- [ ] `git status` is clean; nothing from `data/businesses.local.yaml`, `.env` or
      `spikes/bolna/captures/` is committed.
- [ ] `python scripts\check_no_secrets.py` is clean. If a real key was ever committed, **rotate it**.
- [ ] A licence is chosen and added (not yet decided).
- [ ] `docs/FEASIBILITY.md` is either filled in with real captures or clearly says "not run".
