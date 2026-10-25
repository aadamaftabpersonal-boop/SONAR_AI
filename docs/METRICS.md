# Metrics

**Status: not measured.** No live call has been placed, so there is nothing to report. Do not put a
number in this file by hand. Generate it:

```powershell
backend\.venv\Scripts\python scripts\metrics_report.py --write docs\METRICS.md
```

The report shows live calls only (simulated runs prove nothing about reality), every figure with its
denominator, and `n/a` where there is no data. Rehearsal numbers are not a benchmark: say how many
runs they come from.

## What the report will contain

| Metric | Meaning |
|---|---|
| Call connection rate | completed calls out of calls dispatched |
| Structured answers valid | answers that passed every validation rule, out of completed calls |
| Exact match confirmed | responses where the shop confirmed exactly the requested item |
| Uncertain | responses the validator could not confirm |
| Time to first useful result | median seconds, with the number of searches behind it |
| Time to complete a search | median seconds, with the number of searches |
| Cost per useful result | reported call cost divided by useful answers |
| Searches with a validated useful answer in time | out of searches that started |
| Calls avoided by the stop rule | out of calls planned, for searches that used it |
| Human review agreed | answers a reviewer confirmed matched their transcript |
| **Ground-truth agreement** | answers an independent check confirmed, out of those checked (excluding inconclusive) |

## How to produce the accuracy figure honestly

1. After real calls, list the unchecked answers: `scripts\ground_truth.py list`.
2. Verify each one independently (visit the shop, or place a second human call).
3. Record it: `scripts\ground_truth.py check ID --checker NAME --method IN_PERSON --outcome AGREE`.
4. Report it as **"X of N checked answers matched reality"**, with the inconclusive count. Never a
   bare percentage, and never extrapolate from a small N.
5. List every disagreement in `docs/LIMITATIONS.md`. A wrong "available" is the most important
   failure to publish.
