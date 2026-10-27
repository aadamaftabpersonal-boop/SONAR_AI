# Outreach kit: consenting shops and team test lines (blocker B-01)

The goal is the minimum the demo needs: **at least 2 verified team test lines (3 to show the stop
rule)** and, if possible, **3 consenting shops in one category**. The consent conversation itself
follows `docs/CONSENT_SCRIPT.md` (variant A). This file adds the first-contact messages, the record
templates, and the role-play cards for teammates.

Ground rules (from the consent script): a person asks, never the AI; one follow-up at most; say
"AI assistant" and "transcribed" every time; promise nothing that is not built.

---

## 1. First contact

**In person (best).** Go at a quiet hour, ask for the owner, use variant A in your own words. Take
two minutes, not ten.

**WhatsApp or SMS to a number the shop itself published** (only to start a conversation; the yes
must come from the owner, and never by the AI):

> Hello, I'm [NAME], a student in [CITY]. We're building Sonar, a small project that helps people
> find which nearby shops have an item in stock right now. We'd like your permission for an
> automated AI assistant to occasionally call and ask one short question like "Do you have
> Paracetamol 500 mg?". It always says it is an AI, calls are transcribed, it's free, and you can
> stop it at any time. Could I explain in two minutes, by phone or in person? If not, no problem,
> and we won't message again.

**One follow-up, only if they did not reply, after 2 days:**

> Hello again from Sonar. Just checking once whether you'd be open to a two-minute chat about the
> question-call idea. If not, no reply needed, and we won't contact you again.

After that, stop. Log every ask in `docs/DISCOVERY_LOG.md` section 2 (date, type, outcome).

## 2. Records (in `data/businesses.local.yaml`, git-ignored)

A consenting shop, straight after the yes:

```yaml
  - name: "<shop name>"
    phone_e164: "+91XXXXXXXXXX"        # the number they agreed to be called on
    category: pharmacy
    kind: REAL_BUSINESS
    participation_status: CONSENTED
    consent_recorded_at: "2026-10-28T11:20:00+05:30"
    consent_note: "In person, owner, asked by <teammate>, English, consent_script_v2 variant A"
    best_call_window: "10:00-13:00 IST"
    latitude: 12.97xx
    longitude: 77.59xx
    address: "<street, area>"
```

A team phone acting as a shop (always shown as "Team test line (role-play)"):

```yaml
  - name: "Test line: <teammate first name>"
    phone_e164: "+91XXXXXXXXXX"        # must also be verified in the Bolna dashboard (trial plan)
    category: pharmacy
    kind: TEAM_TEST_LINE
    participation_status: TEST_LINE
    consent_recorded_at: "2026-10-28T09:00:00+05:30"
    consent_note: "Team member plays a shopkeeper. Always labelled role-play."
    latitude: 12.97xx                  # spread test lines 0.3 to 2 km apart so the map reads well
    longitude: 77.59xx
```

Then run `backend\.venv\Scripts\python scripts\seed_businesses.py data\businesses.local.yaml` and
update `docs/EXTERNAL_ITEMS.md` row 4 or 5.

A shop that said no: record it as `DECLINED` (or `INVITED` for "maybe later"), never with a callable
status.

## 3. Test-line checklist (per teammate phone)

- [ ] Number verified in the Bolna dashboard (trial plan calls verified numbers only)
- [ ] Added to `data/businesses.local.yaml` as above and seeded
- [ ] Phone charged, ringer on, Do Not Disturb off during rehearsal and demo
- [ ] The teammate has read their role card below and `docs/agent/ACCEPTANCE_CALLS.md`

## 4. Role cards for teammates playing a shopkeeper

Play it like a real, busy counter: short answers, background noise, sometimes impatient. Never read
the card aloud. Each card says what Sonar should then show, so the room can see it behave honestly.

| Card | Persona | What you say | Sonar should show |
|---|---|---|---|
| A | **Helpful** | "Haan, yes, we have it." / "Yes, exactly that one." / "Twenty-eight rupees." | Reported available, ₹28 |
| B | **Hedger** | "Wait, let me see... maybe, I think so, not sure... call later." | Uncertain, with "This does not mean the item is unavailable." |
| C | **Interrupter** | Cut in during the question: "What? Which one? 500? Yes yes, we have, exactly 500." | Reported available if you clearly said yes to the exact item, else Uncertain |
| D | **Wrong strength** | "500 is finished. We have 650 only." | Has an alternative: 650, no price shown as the 500's price |
| E | **Switches language** | "Haan bhaiya, hai. Bees rupaye." | Reported available or Uncertain; price only if the transcript has it |
| F | **Refuser** | "Don't call this number again." | Declined, opt-out recorded, never called again |
| G | **Silent** | Let it ring out, or pick up and say nothing | No answer, never "unavailable" |

For the live demo use **A** on one line and **B** or **D** on another: one clean answer and one
honest non-answer make the point better than two clean answers.
