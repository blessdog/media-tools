# Voyager gate — morning report (overnight 2026-08-17→18)

## TL;DR
**The gate test did not run.** No Voyager verdict exists — the boundary we hit
was operational (box environment), not scientific (the model was never
reached). Two provisioning attempts, both killed by the pre-registered
45-minute criterion. **Spent: ~$2.20 of the $5 cap. Box destroyed, $0
burning** (`destroy confirmed: 47992868`). No slop was produced because
nothing was produced.

## What happened, mechanism by mechanism
1. **Attempt 1 (died at minute 1, caught at minute 45):** the Vast box image
   lacks `python3-venv` — venv creation failed instantly, script exited, and
   the default LTX/flux manifest's downloader (respawned by supervisord) ate
   bandwidth in the background. Fix applied: `apt install python3.12-venv`,
   supervisor stopped, junk purged.
2. **Attempt 2 (killed at minute 45, still in deps):** two tar pits —
   (a) repo pins (pandas et al.) have no python-3.12 wheels → source builds
   fail; (b) my flash-attn "wheel-first" trick pointed `--find-links` at a
   GitHub releases *page*, which is not a pip index, so it silently fell
   through to a source compile (30–60+ min). The 60GB weights download had
   not even started. Projected completion busted the $5 cap → destroyed.

## What checkpoint A already banked (no box needed)
- `input-bridge.png` — the 1280×720 landscape bridge crop, approved
  composition, committed with provenance sidecar.
- Recon: Voyager force-resizes to 1280×720; conditions always come from MoGe
  depth (no injection flag — swap happens by editing `create_input.py`);
  camera presets include the pure-forward dolly; output 49 frames ~512×768.

## Attempt 3 — corrected, one command, ~$1.30 projected
The two tar pits are both removed by renting differently, not retrying:
1. **Rent with a PyTorch docker image** (`pytorch/pytorch:2.4.0-cuda12.4-
   cudnn9-devel`): torch, CUDA toolchain, python 3.11 preinstalled — kills
   the venv problem AND the py3.12 wheel mismatch at the root.
2. **Exact flash-attn wheel by URL** (cp311/torch2.4/cu12 build from the
   flash-attention releases), `wget` + `pip install ./file.whl` — 30 seconds,
   deterministic, no compile.
3. **Weights first, in parallel:** start `huggingface-cli download` the
   moment ssh opens (needs no env), so the 60GB long pole overlaps deps.
Target: provisioned in ~15 min; conditions + checkpoint B; 32-min inference;
pull; destroy. ~1h box time ≈ $1.30 → total ≈ $3.50, inside the cap.
`provision-voyager-v3.sh` is committed and ready. **Fires on Ryan's word.**

## Meanwhile, everything real is intact
Z1 world data finished and verified; tilted-cards flythrough watchable
(`FLY-S1-4-DEEP.mp4`, `PUSH-GE-TILT.mp4`); warp verdict recorded; rangefinder
committed with the journey ladder (z 1.0 → 2.02 → 3.03); dossier published.
The Voyager question is still worth its $1.30 — but it was never load-bearing.
