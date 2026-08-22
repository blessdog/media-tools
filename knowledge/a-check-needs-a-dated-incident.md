---
id: a-check-needs-a-dated-incident
kind: law
conflict-key: when-is-a-rule-worth-wiring-as-a-check
status: live
supersedes: []
verified-on: 2026-08-22
asked-as:
  - should we add a hook for this
  - is this harness worth building
  - someone handed me a list of best practices
  - should I add a rule about how sessions work
  - a process document says we should do X
---

> "Writing principles that are universal, like one task per session, which is so
> vague, it is pointless." — Ryan, 2026-08-22, on a harness brief written by a
> session that had never seen this repo.

**A check earns its wiring only when you can name the specific incident it would
have caught — in this repo, with a date.** No incident, no check. A principle
with nothing behind it is not a rule, it is a vibe with an exit code, and it
cannot be evaluated until the day it blocks something real.

Every gate here that works has an incident; every rule proposed from outside and
rejected has none:

| wired | the incident |
|---|---|
| stagnation gate | 2026-08-20 — four mask hypotheses and two render modes tuned inside the wrong tool |
| LIVING GATE (`compile-flight.py`) | a 31-station, 20-minute route with living cycles in ONE of five zones |
| output contract (`gpu-box --contract`) | three A100 rentals, ~$9 and 1.5 days, for a 768×512 model against a 105MP scroll |
| SHOW ME PIXELS stop hook | Ryan repeating it across sessions until it became a hook |
| `check-retrieval.py` | a store with 0 type violations that failed 44 of 44 real questions |

| refused | why |
|---|---|
| "one task per session" | no incident, and unfalsifiable |
| "small diffs", "commit at session end" | already true, so the check can only ever fire on a false positive |
| block edits to `tools/` unless HARNESS_OPEN=1 | imported from a repo where `tools/` is scaffolding. Here `tools/` IS the product — one CLI per capability — and the rule would have blocked the 2026-08-21 fix for a 583MB leak |
| Stop hook requiring a fresh render + passing flow check | 2026-08-21 produced four refutations and no render. That is a good session and it could not have ended. A check escapable only by rendering teaches rendering. |
| `PROGRESS.md` | a THIRD status surface beside a generated `STATE.md` and the store. `jobs/wang-meng/STATE.md` reached 896 append-only lines being three documents at once. |

**The asymmetry that makes this a law rather than a preference.** A check on
OUTPUT is cheap when wrong — it fails a render and you look. A check on the
SESSION is expensive when wrong — it blocks work, and the accompanying rule is
always "fix the work, not the check", so the cost is paid silently and
repeatedly by whoever hits it. Prefer checks that read artefacts; distrust checks
that restrict what a session may do.

Corollary, measured the same day: a check must be tested against text it will
actually see. `show-me-pixels-stop.sh` fired on the string `.mkv/.mov/.mp4/.webm`
appearing inside a quoted error message in a code block, and demanded a file be
opened that does not exist. See [[gates-must-survive-a-clone]] for the other half
of this — a gate that is not exercised is not known to work.
