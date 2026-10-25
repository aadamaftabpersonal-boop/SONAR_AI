# Demo script (about 3 minutes)

Rehearse three times from a clean browser profile and log it in `docs/REHEARSAL_LOG.md`. Every
sentence must be something the screen is actually showing. If a feature is not built or not working
on the day, skip its beat.

## Before you start (pre-flight)

- [ ] Backend and frontend running; `/health/ready` is OK.
- [ ] You know which mode you are in. **Demo mode** shows an amber SIMULATED banner. Say so out loud.
- [ ] Access key at hand (type it; it is never stored).
- [ ] Two team phones charged and in range if you are doing a live test-line call.
- [ ] If live: Bolna wallet balance covers the plan; the agent prompt matches `docs/agent/prompt_v1.md`;
      the webhook URL is public HTTPS and "Send test" arrived; `scripts/check_prod_env.py` passes.
- [ ] A dated screen recording of a good run exists as a backup.
- [ ] Browser zoom and window size set; notifications off.

## The beats

| # | Say | Show |
|---|---|---|
| 1 | "Listings tell you a shop exists. They do not tell you whether it has what you need right now." | A normal listing, or just the Sonar title. |
| 2 | "Sonar phones a few shops that agreed to be called, asks one question, and shows exactly what each said." | Fill in the form: Paracetamol 500 mg. Point at the demo-mode checkbox and the disclaimer. |
| 3 | "In demo mode nobody is phoned. Every result is marked simulated." | Press **Search by phone**. The amber banner appears. |
| 4 | "Here are the shops, nearest first. This is each shop's real distance and bearing." | The **Around you** radar and the call list: Ringing, In call. |
| 5 | "Answers arrive as calls finish. I do not wait for the slowest shop." | The first result card appears while others are still calling. |
| 6 | "Two shops confirmed, so Sonar stopped. It skipped the rest instead of bothering them." | The "Stopped early" note and the "Not called" shops. Mention "Ask every shop" turns it off. |
| 7 | "Every answer comes with its evidence: the quote, the time, and whether it is fresh." | Open **Evidence** on one result. |
| 8 | "What a shop did not say, Sonar does not claim." | A silent or hedging shop under "No answer yet", and **What Sonar chose not to claim**. Read the line: "This does not mean the item is unavailable." |
| 9 | "I can also have it read the results back." | **Read results aloud** (only if the browser supports it). |
| 10 | Close with what is real and what is not. | Say: "This is a working pipeline. Real calls to real shops are the next test, and we have not claimed any accuracy figure we have not measured." |

## Optional: a live test-line call (only once the Bolna key works)

1. Hand a judge a team test phone and tell them to play a difficult shopkeeper: hedge, interrupt,
   switch language.
2. Run a **non-demo** search. The test line is labelled **Team test line (role-play)** everywhere.
3. A graceful "Uncertain" is a success. Say so.

## If something breaks

| Problem | Do this |
|---|---|
| A call does not connect | Say "silence is not a no, and the page says so". It is a feature to show. |
| The provider is down | Switch to demo mode **visibly**, and say you did. Never switch silently. |
| The page cannot reach the server | The last results stay on screen with "Connection lost, retrying". Wait. |
| Nothing works | Play the dated backup recording and say that is what it is. |

## Never say

- That a simulated result is a real call, or that a role-played test line is an independent shop.
- A time-saved, accuracy or market-size figure we have not measured and shown with its denominator.
- That a skipped, silent or hedging shop does not have the item.
- That the digest, the inbound line or any unbuilt feature exists.
- That we are partnered with Bolna or any sponsor, beyond using Bolna's technology.

## Claim check

Before presenting, tick each claim to a screen or a test: `docs/LIMITATIONS.md` lists what is and
is not proven.
