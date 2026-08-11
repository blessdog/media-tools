#!/bin/bash
# Bongpot LTX-2.3 LipDub rig — ai-dock/comfyui PROVISIONING_SCRIPT
# ─────────────────────────────────────────────────────────────────────────────
# This is fetched by ai-dock's init (set env PROVISIONING_SCRIPT=<raw url of this>).
# ai-dock already gives us: ComfyUI under supervisord (stays up; `supervisorctl
# restart comfyui`), a real venv ($COMFYUI_VENV_PIP — no PEP-668), sshd from
# SSH_PUBKEY, and a persistent /workspace volume. We add: the LTX node pack, the
# kornia `pad` patch (upstream PR #498, still unmerged), and the LipDub model set.
#
# WHY a custom script and not default.sh's arrays: LTX needs model folders ai-dock
# doesn't map (text_encoders, latent_upscale_models, loras/ltxv/ltx2). So we
# download to the PERSISTENT volume and SYMLINK into /opt/ComfyUI/models ourselves
# — guaranteed correct regardless of ai-dock's stock symlink set, and a restart
# re-pulls nothing (downloads live on /workspace; /opt/ComfyUI does not persist).
#
# CHECKPOINT VARIANT (the one real trade-off, see report):
#   fp8  → fits the L40S 48GB on-GPU (fast, ~30s/clip) BUT needs a separate audio
#          VAE (community unsloth re-host, known metadata issue #99 — validate it).
#   bf16 → audio VAE bundled in the checkpoint (zero drama) BUT 46GB weights force
#          heavy RAM offload on 48GB (slow). Flip VARIANT=bf16 if fp8 audio fails.
VARIANT="${LTX_VARIANT:-fp8}"

# GATED: the LipDub IC-LoRA needs HF_TOKEN *and* a one-time license click-through
# accepted on https://huggingface.co/Lightricks/LTX-2.3-22b-IC-LoRA-LipDub by the
# account that owns HF_TOKEN. Without that acceptance it 403s even with a token.

NODES=(
    "https://github.com/Lightricks/ComfyUI-LTXVideo"
)

# ── ai-dock plumbing (mirrors config/provisioning/default.sh) ────────────────
function provisioning_start() {
    if [[ ! -d /opt/environments/python ]]; then export MAMBA_BASE=true; fi
    source /opt/ai-dock/etc/environment.sh
    source /opt/ai-dock/bin/venv-set.sh comfyui

    PERSIST="${WORKSPACE}/storage/ltx"          # persistent model store
    COMFY="/opt/ComfyUI"

    provisioning_print_header
    provisioning_get_nodes
    provisioning_patch_kornia                    # PR #498 — must run before comfy starts
    provisioning_get_ltx_models
    provisioning_restart_comfyui
    provisioning_print_end
}

function pip_install() {
    if [[ -z $MAMBA_BASE ]]; then "$COMFYUI_VENV_PIP" install --no-cache-dir "$@"
    else micromamba run -n comfyui pip install --no-cache-dir "$@"; fi
}

function provisioning_get_nodes() {
    for repo in "${NODES[@]}"; do
        dir="${repo##*/}"; path="/opt/ComfyUI/custom_nodes/${dir}"
        req="${path}/requirements.txt"
        if [[ -d $path ]]; then
            ( cd "$path" && git pull )
        else
            printf "Cloning node: %s\n" "${repo}"
            git clone "${repo}" "${path}" --recursive
        fi
        [[ -e $req ]] && pip_install -r "$req"
    done
}

# Upstream PR #498: the pack imports `pad` from kornia.geometry.transform.pyramid,
# which kornia >=0.8.3 removed → whole pack fails to import, no LTX-2.3 nodes
# register. `pad` is just torch.nn.functional.pad; import it from torch instead.
# Idempotent: only edits if the broken import is still present.
function provisioning_patch_kornia() {
    local f="/opt/ComfyUI/custom_nodes/ComfyUI-LTXVideo/pyramid_blending.py"
    [[ -f $f ]] || { printf "WARN: %s missing, skip patch\n" "$f"; return; }
    if grep -qE "^[[:space:]]*pad,[[:space:]]*$" "$f"; then
        sed -i "/^[[:space:]]*pad,[[:space:]]*$/d" "$f"
        sed -i "/^from torch import Tensor/a from torch.nn.functional import pad" "$f"
        printf "PATCHED kornia pad import (PR #498) in pyramid_blending.py\n"
    else
        printf "kornia pad import already patched / not present\n"
    fi
}

# Download $1(url) → persistent $2(dir)/$fname, symlink into $3(comfy dir).
# Deterministic target name ($4 rename, else URL basename); skip if already on the
# persistent volume so a restart re-pulls nothing.
function provisioning_fetch() {
    local url="$1" pdir="$2" cdir="$3" rename="$4"
    local fname="${rename:-$(basename "${url%%\?*}")}"
    local target="$pdir/$fname"
    mkdir -p "$pdir" "$cdir"
    if [[ ! -f $target ]]; then
        local auth=()
        [[ -n $HF_TOKEN && $url =~ huggingface\.co ]] && auth=(--header="Authorization: Bearer $HF_TOKEN")
        printf "↓ %s\n" "$fname"
        wget "${auth[@]}" --show-progress -O "$target" "$url" \
            || { rm -f "$target"; printf "FAILED: %s\n" "$url"; return 1; }
    else
        printf "✓ cached %s\n" "$fname"
    fi
    ln -sf "$target" "$cdir/$fname"
    printf "  → %s/%s\n" "$cdir" "$fname"
}

function provisioning_get_ltx_models() {
    local C="/opt/ComfyUI/models"
    local P="${WORKSPACE}/storage/ltx"

    # 1. main checkpoint (fp8 default; bf16 carries bundled audio VAE)
    if [[ $VARIANT == "bf16" ]]; then
        provisioning_fetch \
          "https://huggingface.co/Lightricks/LTX-2.3/resolve/main/ltx-2.3-22b-dev.safetensors" \
          "$P/checkpoints" "$C/checkpoints"
    else
        provisioning_fetch \
          "https://huggingface.co/Lightricks/LTX-2.3-fp8/resolve/main/ltx-2.3-22b-dev-fp8.safetensors" \
          "$P/checkpoints" "$C/checkpoints"
        # fp8 needs the standalone audio VAE (community unsloth re-host — VALIDATE it loads)
        provisioning_fetch \
          "https://huggingface.co/unsloth/LTX-2.3-GGUF/resolve/main/vae/ltx-2.3-22b-dev_audio_vae.safetensors" \
          "$P/checkpoints" "$C/checkpoints"
    fi

    # 2. Gemma-3-12B text encoder (Comfy-Org repackage, UNGATED). fp8_scaled to fit VRAM.
    #    Renamed to the exact string the workflow's loader widget holds.
    provisioning_fetch \
      "https://huggingface.co/Comfy-Org/ltx-2/resolve/main/split_files/text_encoders/gemma_3_12B_it_fp8_scaled.safetensors" \
      "$P/text_encoders" "$C/text_encoders" "comfy_gemma_3_12B_it.safetensors"

    # 3. spatial upscaler — LTX node reads models/latent_upscale_models (NOT upscale_models)
    provisioning_fetch \
      "https://huggingface.co/Lightricks/LTX-2.3/resolve/main/ltx-2.3-spatial-upscaler-x2-1.1.safetensors" \
      "$P/latent_upscale_models" "$C/latent_upscale_models"

    # 4. distilled strengthening LoRA — workflow nests it under loras/ltxv/ltx2/
    provisioning_fetch \
      "https://huggingface.co/Lightricks/LTX-2.3/resolve/main/ltx-2.3-22b-distilled-lora-384-1.1.safetensors" \
      "$P/loras/ltxv/ltx2" "$C/loras/ltxv/ltx2"

    # 5. LipDub IC-LoRA — GATED (HF_TOKEN + license acceptance) — the lipsync brain
    provisioning_fetch \
      "https://huggingface.co/Lightricks/LTX-2.3-22b-IC-LoRA-LipDub/resolve/main/ltx-2.3-22b-ic-lora-lipdub-0.9.safetensors" \
      "$P/loras/ltxv/ltx2" "$C/loras/ltxv/ltx2"
}

function provisioning_restart_comfyui() {
    printf "Restarting ComfyUI to register patched nodes + new models...\n"
    supervisorctl restart comfyui 2>/dev/null || true
}

function provisioning_print_header() { printf "\n===== Bongpot LTX-2.3 LipDub provisioning (variant=%s) =====\n\n" "$VARIANT"; }
function provisioning_print_end() {
    printf "\n===== Provisioning complete =====\n"
    printf "Validate FIRST: load example_workflows/2.3/LTX-2.3_ICLoRA_Lipdub_Two_Stage_Distilled.json\n"
    printf "and confirm LTXVAudioVAELoader loads the audio VAE (the fp8 risk point).\n\n"
}

provisioning_start
