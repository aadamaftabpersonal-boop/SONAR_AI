# Consent script, version 2 (`consent_script_v2`)

For asking a shop or business whether Sonar may phone it. **No real business is ever called by
Sonar until the consent is recorded** (Bible D-004). Record the version of this script in the
business's `consent_note`.

Written for Build Map tasks T0.7 and T13.3. It needs a native speaker's review before use in Hindi,
Kannada or any language other than English; do not translate it by machine and use it as is.

---

## 1. Rules for the person asking

1. **Be truthful about everything**, including that the caller is an AI and that calls are
   transcribed.
2. **Make "no" easy.** Never pressure, never follow up more than once, and never imply a benefit that
   does not exist.
3. **Offer nothing we have not built.** Do not promise customers, money, a listing, a partnership
   with anyone, or the digest (variant B) unless it works today.
4. **Ask once, in your own words.** The script is a guide to the facts, not words to recite.
5. **Record the consent** straight after (see section 6).

## 2. Variant A: the plain script (use this now)

> "Hello, I'm [NAME] from a small student project called Sonar. Sonar helps people find out which
> local shops have a particular item, or can do a particular job, right now.
>
> With your permission, our system would phone you occasionally and ask one short question, for
> example, *'Do you have Paracetamol 500 mg in stock right now?'* The caller is an **AI assistant**,
> and it says so at the start of every call. It will not buy, reserve or promise anything, and it
> will not give advice.
>
> The call is **transcribed** so we can record your exact answer, and [our voice provider may also keep
> a recording: *confirm this after spike S-9 and say it plainly*]. We show people what you said and
> when. We do not claim it is guaranteed.
>
> We would call at most [4] times a day and only between [AGREED HOURS]. You can **say stop at any
> time, on a call or to me, and we will not call again**. If you want, we will also delete what we
> have recorded about your shop.
>
> This is free, and there is nothing you have to do. Is that okay with you?"

## 3. Variant B: digest-first (only once it exists)

**Do not use this variant until the demand digest page works.** Telling a shop it will receive
something we have not built is a false statement. When the digest exists, replace the second
paragraph of variant A with:

> "In return, once a week we can show you what people near you searched for, for example *'12
> searches for Paracetamol near you this week'*, so you can see what is in demand. It only counts
> searches, and it shows no one's identity."

Run A and B as a fair comparison (hypothesis H-4): ask each shop with **one** script only, alternate
between them, and log the result per arm in `docs/DISCOVERY_LOG.md`.

## 4. Answers to likely questions (say only what is true today)

| They ask | Say |
|---|---|
| "Is this a robot?" | "Yes. It is an AI assistant, and it tells you so at the start of every call." |
| "What will you do with my answers?" | "Show them to people searching, with the time you said it. We do not guarantee them, and we label them as what you reported." |
| "Will it cost me anything?" | "No." |
| "Will you sell my number or my data?" | Answer only with a decision the team has actually made, for example: "No, we have no plan to; this is a student project." **Confirm with your teammate before saying it.** |
| "How often will you call?" | "At most [4] times a day, never twice within [15] minutes, only in the hours we agree." |
| "Can I stop it later?" | "Yes, at any time, by telling the caller or telling us at [TEAM CONTACT]. It takes effect straight away." |
| "Are you with Bolna / a company?" | The truth: "We are a student team building this for a hackathon. Bolna provides the voice technology." Do not imply an official partnership. |
| "Will this bring me customers?" | "We can't promise that. Right now it only helps people find out who has an item." |
| "Why do you need my permission?" | "Because it would be wrong to phone a business with an automated system without asking first." |
| "What if the AI says something wrong?" | "It only asks one factual question and records what you say. If anything is wrong, tell us and we will remove it." |

## 5. If they say no, or hesitate

- Thank them. Do not ask again, and do not leave a "just in case" request.
- Record `DECLINED` (or `INVITED` if they said "maybe later" and asked you to come back).
- Never call them with the system. Never add them to the seed file with a callable status.

## 6. Recording the consent

Immediately after a yes, add the business to `data/businesses.local.yaml` (git-ignored) with:

| Field | Value |
|---|---|
| `participation_status` | `CONSENTED` |
| `consent_recorded_at` | the date and time you got the yes, with the timezone offset |
| `consent_note` | **how** (in person, phone, message), **who** asked, which **language**, and `consent_script_v2` variant A or B |
| `best_call_window` | the hours they agreed, for example `10:00-13:00 IST` |
| `latitude`, `longitude` | the shop's location |

The seed loader refuses to load a callable business without a consent time and a note, and the
system re-checks consent right before every call.

Two more things a business can agree to later. These fields are added to the data model when the
features that need them are built, so **do not record them yet**:
- the weekly digest (digest opt-in)
- letting an audience watch or hear a demo call (demo audio consent); this must be explicit, and
  the call's opening line must say so.

## 7. Opt-out handling

If a business asks to stop, at any time or by any route:
1. Tell it that you will stop immediately.
2. Mark it `OPTED_OUT` in the seed file, and ask a teammate to confirm it is excluded from search.
   A business that says "do not call again" **during a call** is excluded automatically.
3. Delete our records about it if it asks. The deletion tool is planned (Build Map T9.7); until it
   exists, the team deletes the rows by hand and notes it in the log.
4. Never re-add an opted-out business. The seed loader will not revive it.

## 8. What not to say (a checklist)

- "It's guaranteed" or "it's always accurate."
- "You'll get more customers" or any figure about customers or money.
- "We're partnered with Bolna / Sarvam / Plivo / anyone."
- "It's just a quick survey" when it is automated calls. Always say AI assistant.
- Anything about the digest before it exists.
- Any claim that the call is not recorded, unless spike S-9 confirmed that it is not.

## 9. Open items (resolve before the first real shop call)

| Item | Why | Owner |
|---|---|---|
| What does the voice provider record and keep, and for how long? (spike S-9) | The script must describe it truthfully. | |
| Team contact number or message route for opt-outs | Shops need a way to reach us. | |
| Call hours and daily cap to quote | They must match `BUSINESS_DAILY_CALL_CAP` and the agreed window. | |
| Native-speaker review of the Hindi and Kannada versions | A translation error here is a consent error. | |
| Advice on the rules for automated calls to businesses (B-05) | We have not verified the legal position. This script does not make a compliance claim. | |
