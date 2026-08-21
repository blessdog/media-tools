---
id: verdict-tier-1-hardening
kind: pending
conflict-key: verdict-on-is-tier-1-of-the-hardening-audit-a-go-vendor-the
status: superseded
supersedes: []
question: >
  is Tier 1 of the hardening audit a go — vendor the tools, in-repo hooks, make check, push the knowledge repo, add CI?
blocks: >
  Tier 2 and 3 entirely, and meanwhile every gate is silently not running on any machine that is not this one
awaiting: Ryan
verified-on: 2026-08-20
evidence:
  - docs/reports/2026-08-20-hardening-the-knowledge-store.html
asked-as:
  - what is Ryan deciding
  - is Tier 1 of the hardening audit a go — vendor the tools, in-repo hook
  - pending verdict
---

**AWAITING RYAN. Do not guess this and do not build past it.**

## is Tier 1 of the hardening audit a go — vendor the tools, in-repo hooks, make check, push the knowledge repo, add CI?

**Blocks:** Tier 2 and 3 entirely, and meanwhile every gate is silently not running on any machine that is not this one

**The choices:**

- go
- go but skip CI for now
- not yet

**Look at:**

- `docs/reports/2026-08-20-hardening-the-knowledge-store.html`

Recorded at the moment the question was asked, because a question asked
near the end of a session dies with the session — the evidence scrolls
away, the window closes, the context compacts, and what is lost is a
decision that was one sentence from being made.

Settle it with `knowledge-ask.py --answer verdict-tier-1-hardening --verdict "..."`, then
write the claim the answer justifies. The verdict is not the knowledge;
the rule it establishes is.

## Answered 2026-08-21 by Ryan

> GO. Ryan 2026-08-21: 'hardenign looks good as far as i can tell glancing over it'. Tier 1 approved: vendor the tools, in-repo .claude/settings.json hooks, one 'make check' entry point, push ~/.claude/knowledge to a private remote with a pre-push gate, GitHub Action running make check.
