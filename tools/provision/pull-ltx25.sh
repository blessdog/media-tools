#!/usr/bin/env bash
# Pull the LTX 2.5 dev bf16 model set onto a provisioned ComfyUI box.
#
# Runs ALONGSIDE the normal provisioner rather than replacing it: that script
# installs ComfyUI, the LTXVideo custom nodes and the kornia patch, all of which
# we still want. It also pulls the 2.3 checkpoints, which we do not — but
# killing it mid-download is exactly what corrupted the model set on
# 2026-08-12, so it is left alone to finish.
#
# THE HARDENING THAT MATTERS: every file lands as <name>.part and is renamed
# only after curl exits 0 AND the size matches. A container stop mid-download
# used to leave a truncated file at the FINAL name, so the next run saw it,
# skipped it, and ComfyUI failed later with an unreadable shape/size error that
# looked like a model bug rather than a broken download.
set -uo pipefail

COMFY="${COMFY:-/opt/ComfyUI}"
REPO="Lightricks/LTX-2.5"
BASE="https://huggingface.co/${REPO}/resolve/main"
TOKEN="${HF_TOKEN:-}"

# path-in-repo                                              dest-dir            bytes
FILES=(
  "diffusion_models/ltx-2.5-22b-dev-transformer-bf16.safetensors|diffusion_models|41994569184"
  "text_encoders/gemma4-12b-with-proj-ltx-2.5-bf16.safetensors|text_encoders|26340958208"
  "vae/ltx-2.5-video-vae-bf16.safetensors|vae|1509949440"
  "vae/ltx-2.5-audio-vae-bf16.safetensors|vae|419430400"
)

hdr=()
[ -n "$TOKEN" ] && hdr=(-H "Authorization: Bearer ${TOKEN}")

pull() {
  local path="$1" dir="$2" want="$3"
  local name; name="$(basename "$path")"
  local out="${COMFY}/models/${dir}/${name}"
  mkdir -p "${COMFY}/models/${dir}"

  if [ -f "$out" ]; then
    local have; have=$(stat -c%s "$out" 2>/dev/null || echo 0)
    # A file that is present but the wrong size is the truncation bug. Re-pull it.
    if [ "$have" -gt 1000000 ] && { [ "$want" = "0" ] || [ "$have" -ge $((want - want/100)) ]; }; then
      echo "have  $name ($((have/1000000)) MB)"; return 0
    fi
    echo "REPULL $name — on disk $((have/1000000)) MB, expected ~$((want/1000000)) MB"
    rm -f "$out"
  fi

  echo "pull  $name"
  # --continue-at resumes a partial .part across retries instead of restarting 42GB.
  if curl -sSL --fail --retry 5 --retry-delay 5 --continue-at - "${hdr[@]}" \
        -o "${out}.part" "${BASE}/${path}"; then
    local got; got=$(stat -c%s "${out}.part" 2>/dev/null || echo 0)
    if [ "$want" != "0" ] && [ "$got" -lt $((want - want/100)) ]; then
      echo "SHORT $name — got $((got/1000000)) MB of ~$((want/1000000)) MB, leaving .part"
      return 1
    fi
    mv -f "${out}.part" "$out"          # rename ONLY on success — the whole point
    echo "ok    $name ($((got/1000000)) MB)"
  else
    echo "FAIL  $name (curl $?) — .part kept for resume"
    return 1
  fi
}

echo "=== LTX 2.5 pull -> ${COMFY}/models ==="
pids=()
for f in "${FILES[@]}"; do
  IFS='|' read -r path dir want <<<"$f"
  pull "$path" "$dir" "$want" &
  pids+=($!)
done
fail=0
for p in "${pids[@]}"; do wait "$p" || fail=1; done

echo "=== done (fail=$fail) ==="
ls -la "${COMFY}/models/diffusion_models" "${COMFY}/models/text_encoders" "${COMFY}/models/vae" 2>/dev/null
[ "$fail" = "0" ] && touch /var/log/ltx25.marker && echo "LTX25_DONE"
exit $fail
