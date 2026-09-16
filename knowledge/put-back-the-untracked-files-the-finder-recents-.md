---
id: put-back-the-untracked-files-the-finder-recents-
kind: open
conflict-key: should-we-put-back-the-untracked-files-the-finder-recents-
status: live
supersedes: []
proven: false
verified-on: 2026-09-16
asked-as:
  - Put back the untracked files the Finder Recents drag left in ~/Desktop/Recent
  - put back the untracked files the finder recents 
  - why is  (THE-RISE.mp4 is confirmed there by the 2026-09-05 STATE.md); other files -> their original repos (rantrecorder, media-tools, write-on, yobs, promptshark, anselman) like this
---

**This is a PLAN, not a finding. `proven: false`. Do not build against it.**

## Put back the untracked files the Finder Recents drag left in ~/Desktop/Recent

**Why it matters:** The 2026-09-15 git restore only put back TRACKED files. Untracked deliverables moved by the 2026-09-14 20:20 Finder Recents drag are still in ~/Desktop/Recent (THE-RISE.mp4 253MB, RISE-z1.mp4, ONESHOT-42.mp4 seen 2026-09-16), so media-tools STATE.md now lists no film deliverables and the THE-RISE Desktop symlink is gone. Those renders exist nowhere else, so deleting or emptying ~/Desktop/Recent would lose them.

**Where it lands:** `~/Desktop/Recent -> jobs/wang-meng/film/ (THE-RISE.mp4 is confirmed there by the 2026-09-05 STATE.md); other files -> their original repos (rantrecorder, media-tools, write-on, yobs, promptshark, anselman)`

**First step:** List ~/Desktop/Recent files that git does not track. For each one, find where it came from using that folder's old STATE.md deliverable lists, git log mentions and the Finder RecentMoveAndCopyDestinations list. Move back only files whose origin is certain, confirm each move with ls on both sides (a-copy-tools-exit-code-is-not-proof-of-a-move), recreate the ~/Desktop/THE-RISE.mp4 symlink, then regenerate STATE.md

Bookmarked 2026-09-16 at the moment of deferral, because the record of a deferral is what fails, not the decision to defer.
