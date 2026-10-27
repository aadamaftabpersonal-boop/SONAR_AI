# Operations runbook

For running Sonar for a demo or a pilot. Everything here is a procedure to follow, not a claim
about performance. Cost figures come from `scripts/metrics_report.py`, never from assumptions.

## 1. Before every deployment

```powershell
python scripts\check_prod_env.py --env-file .env.prod     # must print "production config: ok"
npm --prefix frontend run build
python scripts\check_bundle.py                            # must print "bundle check: clean"
.\tasks.ps1 check
```

Generate secrets with `python -c "import secrets; print(secrets.token_urlsafe(32))"`. Never reuse the
local development values.

## 2. Start, stop, restart

```powershell
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build   # start / update
docker compose -f docker-compose.prod.yml logs -f app                          # read logs
docker compose -f docker-compose.prod.yml restart app                          # restart
docker compose -f docker-compose.prod.yml down                                 # stop (keeps data)
```

Migrations run as a separate `migrate` step that must succeed before the app starts.

A restart is safe at any moment: calls that were being dialed become "status unknown" and are
**never redialed automatically**; calls in flight are recovered by asking the provider for their
record. If a restart happens during a live demo, say so and check the results page.

## 3. Live calling (Bolna)

1. Set `BOLNA_API_KEY` and `BOLNA_AGENT_ID_<CATEGORY>`. Without both, live calling stays off and
   only demo mode works.
2. The webhook URL is `https://<your host>/api/webhooks/bolna/<WEBHOOK_SECRET_TOKEN>`. Paste it in
   the agent's Webhook Configuration, press **Send test**, and check that the event appears in the
   `provider_events` table.
3. Optionally set `WEBHOOK_ALLOWED_IPS=13.203.39.153,13.126.9.249,13.202.133.53`. Behind a proxy,
   confirm the real source address first or you will block Bolna.
4. Place one test call to a **team phone** before any shop (`spikes/bolna/README.md`).

### Wallet and cost

- Check the Bolna wallet balance before every demo. If it runs out mid-call the provider rejects
  further calls, Sonar pauses dispatching, and the page shows those calls as failed.
- `GLOBAL_DAILY_CALL_BUDGET` (default 40) caps live calls per day. Past it, calls fail with
  "budget exceeded" **without contacting Bolna**.
- Real spend: `python scripts\metrics_report.py` ("cost per useful result", with its sample size).

## 4. Opt-outs and deleting data

A business that says "stop" on a call is excluded automatically and permanently.

If a business asks you directly, in any channel:

1. Mark it `OPTED_OUT` in `data/businesses.local.yaml` (re-seeding never revives an opt-out), **or**
   have it press the button on its digest page.
2. If it asks for its data to be deleted:
   ```powershell
   backend\.venv\Scripts\python scripts\delete_business_data.py BUSINESS_ID          # preview
   backend\.venv\Scripts\python scripts\delete_business_data.py BUSINESS_ID --yes    # do it
   ```
   This removes its answers, raw events and history, and keeps the business row and its opt-out.

Raw provider events are deleted after `RETENTION_EVENT_DAYS` (30) and old call excerpts are cleared
after `RETENTION_RESPONSE_DAYS` (90), automatically every hour.

## 5. Rolling back

1. Redeploy the previous image: `docker compose ... up -d` with the earlier tag.
2. Migrations are additive. Do **not** downgrade the database during a live event; an older app
   version runs fine against a newer schema.
3. To switch a Wave 2 feature off without redeploying code, set its flag false and restart:
   `FEATURE_STOP_RULE`, `FEATURE_HISTORY`, `FEATURE_DIGEST`.

## 6. When something goes wrong

| Symptom | Likely cause | What to do |
|---|---|---|
| `Live calling is not configured` | No Bolna key or no agent for that category | Use demo mode, or set `BOLNA_API_KEY` and the agent id |
| Calls stuck "Ringing" | Webhook not arriving | The reconciler asks the provider after 90 s; check the webhook URL and "Send test" |
| Shop shows "Status unknown" | A request may have reached Bolna with no clear answer | Check Bolna's own call list before doing anything; Sonar will not redial it |
| `PROVIDER_REJECTED` on every call | Number not verified on a trial plan, or a bad `from` number | Read the exact message in the attempt's `failure_reason`; see FEASIBILITY.md S-1 |
| Everything fails with "balance" | Out of credit | Top up, restart; dispatching resumes |
| Results page says "Connection lost" | Server restarting or network | The last results stay on screen and it retries |
| `/health/ready` fails | Database unreachable | Check the `db` container; the app recovers by itself |

## 7. Pre-flight on the day

See `docs/DEMO_SCRIPT.md`. In addition: confirm `FEATURE_*` flags are set exactly as rehearsed,
the daily budget is what you can afford, and a dated backup recording exists.

## Inviting a shop (FEATURE_OPT_IN)

1. Make sure the shop is in the directory: found by discovery (`FEATURE_DISCOVERY`, the map's shops
   marked "Not joined yet"), added from the seed file as `INVITED`, or listed by
   `scripts\approve_opt_in.py` after it asked to join at `/join`.
2. For a public request, **check the number belongs to the shop** (call it yourself or visit) before
   anything else.
3. Create the link: `backend\.venv\Scripts\python scripts\invite_shop.py --phone "<shop number>" --by "<your name>"`
   (or `scripts\approve_opt_in.py <business-id> --by "<your name>"` for a public request). Set
   `PUBLIC_BASE_URL` so the printed link points at the deployed site.
4. Hand the link over yourself: in person, on paper, or by WhatsApp to the shop's own number. It is
   single use and expires after `OPT_IN_TOKEN_DAYS` days.
5. The shop opens it, reads what Sonar does, ticks two boxes and agrees. Only then is it callable.
   It receives a private stop link, which works even if the feature is turned off.
6. Never re-invite a shop that said no or opted out; the tool refuses anyway.
