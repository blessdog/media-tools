---
id: merge-the-two-region-catalogues-into-one
kind: open
conflict-key: should-we-merge-the-two-region-catalogues-into-one
status: live
supersedes: []
proven: false
verified-on: 2026-08-20
asked-as:
  - why are there two region files
  - regions.json vs living-polys.json
  - which region file does the builder read
---

**This is a PLAN, not a finding. `proven: false`. Do not build against it.**

## merge the two region catalogues into one

**Why it matters:** regions.json and living-polys.json BOTH carry a class per region, and only living-polys.json is executed. On 2026-08-20 the summit revert (Ryan: 'peaks shouldnt wobble') was applied to regions.json and missed living-polys.json, so 13 gust-far summit polys stayed live and buildable for a day. check-routing.py --regions now catches the drift, but two copies of one fact is still the bug; the checker only makes it loud.

**Where it lands:** `jobs/wang-meng/living/build-zone-living.py:193 (POLYS) vs :177 (REGF)`

**First step:** living-polys.json becomes the only region list. regions.json keeps ONLY classes (the params + technique). build-native-water.py, heat-native-cycles.py and grid-crop.py read REG['regions'] for box+cycle, so they move first or the boxes migrate into the poly entries.

**Blocked on:** the native-res water pipeline is working and unrelated; do not touch it mid-foliage-build

Bookmarked 2026-08-20 at the moment of deferral, because the record of a deferral is what fails, not the decision to defer.
