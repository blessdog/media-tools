---
id: checks-start-in-observation
kind: law
conflict-key: when-is-a-rule-worth-wiring-as-a-check
status: live
supersedes: [a-check-needs-a-dated-incident]
verified-on: 2026-08-22
asked-as:
  - should we add a hook for this
  - is this harness worth building
  - someone handed me a list of best practices
  - should I make this rule blocking
  - a process document says we should do X
  - this check keeps firing on the wrong thing
---

> "Instead of a hard rule, can we just run the checks? And then once it either
> validates or disproves, it can then litigate." — Ryan, 2026-08-22

**A check is never born blocking. It runs in OBSERVATION first — it evaluates,
it logs, it always exits 0 — and it earns the right to block from its own log.**
This is shadow mode, the pattern firewalls use before they are allowed to drop
packets and linters use when a rule ships as a warning before an error.

Three states, and a check must be in exactly one:

| state | behaviour | leaves by |
|---|---|---|
| **observing** | evaluates, writes one line per firing, exits 0 always | promotion or deletion — never by staying |
| **blocking** | non-zero exit, refuses the action | a false positive sends it back to observing |
| **deleted** | — | it never fired, or it fired wrong more than once |

**Why this beats requiring an incident up front** (which is what the retired
[[a-check-needs-a-dated-incident]] demanded): that rule could only ever guard a
failure already suffered, and its evidence was whatever anyone remembered. An
observing check costs nothing to add, guards nothing yet, and MANUFACTURES the
incident record — after twenty sessions the log is the evidence, measured rather
than recalled. Speculative checks become safe to write.

**THE EXPIRY IS NOT OPTIONAL.** Advisory checks that nobody promotes become the
four hundred warnings every codebase has and nobody reads, and a rule that is
neither enforced nor removed is worse than either, because it looks like
coverage. So every observing check carries a deadline, and "still observing" is
not an available answer past it:

- fired ≥3 times with 0 false positives → **promote to blocking**
- fired 0 times in 20 sessions → **delete**; it is decorative
- fired with >1 false positive → **fix the matcher or delete**, never promote

**What still holds from the retired claim.** Prefer checks that read ARTEFACTS
over checks that RESTRICT THE SESSION. The asymmetry is in what a wrong check
costs: an artefact check that is wrong fails a render and you look at it, while a
session check that is wrong blocks work — and the rule shipped alongside it is
always "fix the work, not the check", so the cost is paid silently and repeatedly
by whoever hits it. Observation removes most of that risk but not the asymmetry.

**Measured the day this was written.** `show-me-pixels-stop.sh`, a check we wrote
ourselves and armed immediately, fired on the string `.mkv/.mov/.mp4/.webm`
sitting inside a quoted error message in a code block, and demanded that a file
which does not exist be opened. In observation that is one log line and a matcher
fix; armed, it was a blocked turn and a rule saying it must not be touched. See
[[gates-must-survive-a-clone]].
