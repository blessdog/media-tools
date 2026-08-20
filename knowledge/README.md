# The knowledge store

One claim per file, typed, checked by `tools/check-knowledge.py`.

**Every claim is one of five shapes**, and each shape demands different fields —
a `verdict` cannot be written without a `scope`, a `refuted` cannot be written
without a `mechanism`, an `open` is structurally marked unproven. The illegal
states are not rejected; they are unwritable.

**At most one LIVE claim per `conflict-key`.** Superseding means moving the old
file into `archive/`, setting `status: superseded`, and naming it in the new
claim's `supersedes:`. Never edit a claim in place to change its verdict.
Measured: append-only memory scores *worse than no memory at all* under a
reversal (0.210 vs 0.309); revocation scores 0.950.

**The body is the RAW trace**, not a summary. Agents reliably condition on raw
experience and frequently disregard condensed experience. The distilled line
goes in the frontmatter; what actually happened goes in the body.
