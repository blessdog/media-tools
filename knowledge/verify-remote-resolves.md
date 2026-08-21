---
id: verify-remote-resolves
kind: open
conflict-key: should-we-verify-remote-resolves
status: live
supersedes: []
proven: false
verified-on: 2026-08-20
asked-as:
  - verify the remote RESOLVES, not just that it exists
  - verify remote resolves
  - why is state-report.py like this
---

**This is a PLAN, not a finding. `proven: false`. Do not build against it.**

## verify the remote RESOLVES, not just that it exists

**Why it matters:** having an origin is not the same as being backed up. Measured 2026-08-20: 8 repos had a remote pointing at a GitHub repo deleted in the 188->20 portfolio cleanup, so they reported themselves pushed while being completely unbacked. state-report.py's gate only checks that origin is CONFIGURED, which is exactly the check that missed all 8.

**Where it lands:** `~/.claude/knowledge/bin/state-report.py:129`

**First step:** gh repo view <slug from origin url> --json name; non-zero exit means treat it as NO REMOTE. Cache briefly so the Stop hook does not hit the network every turn.

Bookmarked 2026-08-20 at the moment of deferral, because the record of a deferral is what fails, not the decision to defer.
