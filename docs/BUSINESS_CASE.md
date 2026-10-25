# Sonar: business case (hypotheses, not claims)

**Status: nothing here is measured.** Every row is a hypothesis with the cheapest test that could
prove or kill it. The pitch may state a hypothesis only as a hypothesis. No market-size, savings or
revenue figure appears in this file unless it is sourced or measured by us (checked by
`scripts/check_claims.py`).

Written to support Bible sections 46 and 47 and Build Map tasks T13.1 and T13.2.

---

## 1. The thesis in three sentences

Many businesses hold facts people need right now (do you have this, can you do this today, what
would it cost) and have no way to publish them. The only way to get them is to phone. Sonar phones
a small set of consenting businesses with an automated, honest voice agent, validates what each
said, and returns a time-stamped answer with the evidence.

The one-line positioning: **Sonar turns phone calls into a queryable, time-stamped,
evidence-backed record of the offline world.**

## 2. The product ladder (what is real today)

| Level | What the user gets | Status |
|---|---|---|
| L1 Stock check | "Does anyone near me have exactly this, now?" | **Built and tested on the simulator.** Not yet run against a real provider. |
| L2 Capacity and quote | "Can you do this today, and for how much?" | The same engine, a different category configuration. Configured, not tested live. |
| L3 Standing watch | "Tell me when someone reports it in stock." | Designed only. |
| L4 Shop line | Shopkeepers update their own stock by phone. | Designed only; depends on an unverified Bolna capability. |
| L5 Phone as API | One request returns answers from businesses that have no API. | Designed only. |

What is genuinely built, and can be shown honestly: consent-gated calling, an answer validator that
refuses to claim what it cannot evidence, "silence is never unavailable" wording, an early-stop
rule that skips calls once enough shops confirm, and a live-progress interface.

## 3. Hypotheses and their cheapest tests

Thresholds below are **proposals** we set before looking, so the result cannot be bent afterwards.
Change a threshold only by writing down why, before the test.

### H-1: Someone needs this and pays for it today (in time or money)

- **Claim:** businesses that need store-level facts but have no API (for example a pharmacy
  aggregator verifying stock, a distributor auditing shelves, a clinic checking another clinic's
  slots, a repair marketplace checking capacity) currently solve it by phoning, and that costs them
  something they can name.
- **Cheapest test (T13.2):** three conversations, 20 minutes each, with people who plausibly feel
  it. Ask about the **last time** they needed this, not whether they would like a product.
- **Pass:** at least two of three describe a real, recent, recurring instance **and** name what it
  cost (staff time, a lost sale, a delayed order).
- **Kill:** none of the three can name a recent instance. Then reframe the pitch around the
  consumer impact story and say plainly that the business model is unproven.
- **Result:** _not run_

### H-2: The pricing unit is an answer, not a call

- **Claim:** buyers care about a validated answer, so the natural price is per useful result.
- **Cheapest test:** compute our **measured** cost per useful result (total reported call cost
  divided by validated positive or negative answers) from `scripts/metrics_report.py` once real calls
  exist. In the H-1 interviews, ask what the manual version costs them per query.
- **Pass:** our measured cost per useful result is clearly below what interviewees say the manual
  version costs them. "Clearly" is defined before looking: at most half of the lowest figure quoted.
- **Kill:** we cost more than the manual way.
- **Result:** _not run_ (needs the first real calls; the early-stop rule is the main cost lever)

### H-3: The data compounds into a moat

- **Claim:** the asset is a freshness-stamped record of offline reality plus per-shop knowledge
  (who picks up, when, how reliably they say yes), and a business that has to be called again and
  again benefits from that history.
- **Cheapest test:** after at least 30 live calls, show that history-ordered dispatch reaches a
  confirmation in fewer calls than nearest-first ordering, with no meaningful loss of coverage
  (paired runs in `THOROUGH` and `FAST`, Build Map T17.5).
- **Pass:** fewer calls per useful result with history, on the same queries, with the sample size
  reported.
- **Kill:** no difference. Then the moat is only "we can phone people", which is weak, and we should
  say so.
- **Honest caveat:** answers go stale within hours, so the dataset decays. The durable part, if any,
  is the per-shop behaviour and the consent relationships, not the answers.
- **Result:** _not run_

### H-4: Shops say yes more often when they get something back

- **Claim:** a small shop is more willing to consent if Sonar gives them useful information, for
  example a weekly note on what nearby people searched for.
- **Cheapest test (T13.2):** ask shops with two scripts and record the result per arm. Script A is
  plain. Script B leads with the digest. **Script B may only be used once the digest page actually
  exists**, because promising something we have not built is a false statement. See
  `docs/CONSENT_SCRIPT.md`.
- **Pass:** a higher yes rate for B than A, reported as yes of asked per arm (for example 6 of 10
  against 3 of 10). With samples this small, treat it as a signal, never as proof.
- **Kill:** no difference, or B is worse. Then drop the digest from the pitch.
- **Result:** _not run_

### H-5: The timing is right

- **Claim:** voice agents can now hold a natural call at a usable latency and cost, including in
  Indian languages.
- **Cheapest test:** the Phase 1 spike. Measure pickup-to-first-word latency, transcription accuracy
  on product names and prices in Hindi and Kannada (spike S-8, reported as n of N correct), and cost
  per call.
- **Pass:** a shopkeeper can complete the exchange without repeating themselves in most test calls,
  and cost per call is known.
- **Kill:** accuracy is too poor to extract a price reliably. Then the product is a calling tool
  that still needs a human check.
- **Result:** _not run_ (blocked on the Bolna key)

## 4. What would make us stop or change direction

| If this happens | Then |
|---|---|
| Real shops refuse or hang up at a high rate | The consent model is the bottleneck. Move to shops that benefit directly, or to clinics and service businesses with a booking motive. |
| Transcription cannot reliably capture a price | Narrow to availability only, which is a weaker product. |
| No interviewee names a cost | The business case is unproven; lead with the impact story and say so. |
| Calling rules for automated calls to businesses turn out to be restrictive | Compliance question B-05 is unresolved. Keep the consent-only model and take advice before any scale-up. |

## 5. What this document deliberately does not do

- It states no market size, growth rate, revenue forecast or percentage. <!-- claim-ok -->
- It names no competitor with a claim about them. Honest framing only: AI calling agents exist,
  directories and listings exist, marketplaces exist. Our difference is a validated evidence model,
  a consent-only policy and an early-stop rule. Whether that is enough is exactly what H-1 to H-3 test.
- It does not assume the buyer. The most likely first paying users are businesses that already
  phone around today, and we have not yet spoken to one.

## 6. Customer discovery guide (T13.2)

Ask about **past behaviour**, never about hypothetical interest. Do not describe Sonar until the
last five minutes. Record exact words in `docs/DISCOVERY_LOG.md`.

**Buyer-side questions**
1. Tell me about the last time you needed to know whether another business had something, or could
   do something today. What did you do?
2. How long did it take, and who did it? What happened if you could not find out?
3. How often does that happen in a typical week?
4. What have you tried to make it easier? What did you stop using, and why?
5. If that could be done for you, what would the answer need to include for you to rely on it?
6. Who else is involved in deciding to pay for something like this?

**Shop-side questions** (separate from the consent ask)
1. How many calls a day do you get that are only asking "do you have X"?
2. What do you do with them now, and what do they cost you?
3. Would you want to know what people nearby are asking for? Why, or why not?

Stop and thank them if they are not interested. Do not argue.

## 7. What the pitch may and may not say

| May say | May not say |
|---|---|
| "Sonar reports what each shop said, when, with the evidence." | "Sonar knows what is in stock." |
| A measured cost per useful result, with the number of calls behind it. | A saving or speed-up we did not measure. |
| "In our rehearsal, X of N answers matched what we found in person." | A bare accuracy percentage. |
| "We have not yet tested whether businesses will pay." (if true) | "Businesses want this." |
| Any hypothesis, clearly labelled as one. | A market size or growth figure of any kind. | <!-- claim-ok -->

