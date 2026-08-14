// media-tools — Krea-2 ComfyUI graph, in API format.
//
// NOT invented. Every node type, every widget value and every default below was
// read out of ComfyUI's own official template on 2026-08-12:
//   comfyui_workflow_templates_json/templates/image_krea2_turbo_t2i.json
//     → definitions.subgraphs["Text to Image (Krea-2 Turbo)"]
// and every input NAME was confirmed against the live server's /object_info on
// the box. Guessing node names is how you discover a typo after a 30GB download.
//
// What the official template settled that we would otherwise have got wrong:
//   • KSampler for TURBO is steps 8, cfg 1.0, euler/simple, denoise 1.0.
//     Turbo is distilled; running it at 20 steps wastes time and changes nothing.
//   • LoRA strength in Krea's own template is 0.8, not 1.0.
//   • CLIPLoader needs type "krea2" — a plain load returns garbage conditioning.
//   • The model arrives through UNETLoader, not CheckpointLoaderSimple, so the
//     CLIP and VAE are loaded separately.
//   • Negative conditioning is ConditioningZeroOut at cfg 1.0 — meaning, exactly
//     as in the USO graph, A NEGATIVE PROMPT WOULD DO NOTHING HERE.
//
// The template also carries an optional LLM prompt-expansion chain (TextGenerate,
// StringConcatenate, switches). Deliberately omitted: it rewrites the prompt
// before rendering, which would mean judging a model on text we never wrote.

export function buildKreaGraph({
  prompt,                                     // content + trigger phrase; no medium adjectives
  lora = null,                                // filename in models/loras, or null for base
  loraStrength = 0.8,                         // Krea's own template default
  seed = 7,
  steps = 8,                                  // turbo. raw needs more — pass it in.
  cfg = 1.0,
  sampler = 'euler',
  scheduler = 'simple',
  width = 1024,
  height = 1024,
  unet = 'krea2_turbo_fp8_scaled.safetensors',
  clip = 'qwen3vl_4b_fp8_scaled.safetensors',
  vae = 'qwen_image_vae.safetensors',
  prefix = 'krea2',
} = {}) {
  const g = {
    '1': { class_type: 'UNETLoader', inputs: { unet_name: unet, weight_dtype: 'default' } },
    '2': { class_type: 'CLIPLoader', inputs: { clip_name: clip, type: 'krea2' } },
    '3': { class_type: 'VAELoader', inputs: { vae_name: vae } },
    '4': { class_type: 'CLIPTextEncode', inputs: { text: prompt, clip: ['2', 0] } },
    '5': { class_type: 'ConditioningZeroOut', inputs: { conditioning: ['4', 0] } },
    '6': { class_type: 'EmptyLatentImage', inputs: { width, height, batch_size: 1 } },
    '7': {
      class_type: 'KSampler',
      inputs: {
        model: ['1', 0],                      // rewired to the LoRA below when present
        positive: ['4', 0], negative: ['5', 0], latent_image: ['6', 0],
        seed, steps, cfg, sampler_name: sampler, scheduler, denoise: 1.0,
      },
    },
    '8': { class_type: 'VAEDecode', inputs: { samples: ['7', 0], vae: ['3', 0] } },
    '9': { class_type: 'SaveImage', inputs: { images: ['8', 0], filename_prefix: prefix } },
  };

  // A LoRA is a link in the model chain, not a different graph — which is why
  // one Krea graph serves every Krea LoRA ever published.
  if (lora) {
    g['10'] = {
      class_type: 'LoraLoaderModelOnly',
      inputs: { model: ['1', 0], lora_name: lora, strength_model: loraStrength },
    };
    g['7'].inputs.model = ['10', 0];
  }
  return g;
}

// ─── style reference: an IMAGE drives the look, not a trigger phrase ─────────
//
// Read out of ComfyUI's official template on 2026-08-12:
//   templates/image_krea2_turbo_int8_image_style_reference.json
//     → definitions.subgraphs["Image Style Reference (Krea-2 Turbo)"]
// Input names confirmed against the live server's /object_info.
//
// This is a materially different graph from the t2i one, not a flag on it:
//   • krea2_style_reference.safetensors is REQUIRED — the reference channel does
//     not exist without it. It is not a style LoRA; it is the mechanism.
//   • TextEncodeQwenImageEditPlus takes the reference IMAGE and the prompt
//     together, and needs the VAE.
//   • FluxKontextMultiReferenceLatentMethod 'index_timestep_zero' — the same
//     family of node the USO graph uses for its identity channel.
//   • Sampling is the SamplerCustomAdvanced chain (RandomNoise + CFGGuider +
//     KSamplerSelect + BasicScheduler), not a plain KSampler, and the model
//     passes through ModelSamplingFlux(1.15, 0.5) first.
//
// `styleLora` stacks a SECOND LoRA on top of the reference mechanism — Ryan's
// "reference image + LoRA" hypothesis. Chaining is legal because
// LoraLoaderModelOnly takes a model and returns one.
export function buildKreaStyleRefGraph({
  prompt,
  refImages = [],                             // 1-3 server-side filenames (already uploaded)
  seed = 7,
  steps = 8,
  cfg = 1.0,
  width = 1024,
  height = 1024,
  unet = 'krea2_turbo_fp8_scaled.safetensors',
  clip = 'qwen3vl_4b_fp8_scaled.safetensors',
  vae = 'qwen_image_vae.safetensors',
  refLora = 'krea2_style_reference.safetensors',
  refLoraStrength = 1.0,
  styleLora = null,                           // optional second LoRA, stacked
  styleLoraStrength = 0.8,
  prefix = 'krea2-ref',
} = {}) {
  if (!refImages.length) throw new Error('buildKreaStyleRefGraph: refImages is empty — that is the whole point of this graph');

  const g = {
    '1': { class_type: 'UNETLoader', inputs: { unet_name: unet, weight_dtype: 'default' } },
    '2': { class_type: 'CLIPLoader', inputs: { clip_name: clip, type: 'krea2' } },
    '3': { class_type: 'VAELoader', inputs: { vae_name: vae } },
    // the reference mechanism itself
    '4': { class_type: 'LoraLoaderModelOnly', inputs: { model: ['1', 0], lora_name: refLora, strength_model: refLoraStrength } },
  };

  let modelSrc = ['4', 0];
  if (styleLora) {
    g['5'] = { class_type: 'LoraLoaderModelOnly', inputs: { model: modelSrc, lora_name: styleLora, strength_model: styleLoraStrength } };
    modelSrc = ['5', 0];
  }

  // reference images in, up to three
  const imgInputs = {};
  refImages.slice(0, 3).forEach((name, i) => {
    const id = String(20 + i);
    g[id] = { class_type: 'LoadImage', inputs: { image: name } };
    imgInputs[`image${i + 1}`] = [id, 0];
  });

  g['6'] = { class_type: 'TextEncodeQwenImageEditPlus', inputs: { clip: ['2', 0], prompt, vae: ['3', 0], ...imgInputs } };
  g['7'] = { class_type: 'FluxKontextMultiReferenceLatentMethod', inputs: { conditioning: ['6', 0], reference_latents_method: 'index_timestep_zero' } };
  g['8'] = { class_type: 'ConditioningZeroOut', inputs: { conditioning: ['6', 0] } };
  g['9'] = { class_type: 'ModelSamplingFlux', inputs: { model: modelSrc, max_shift: 1.15, base_shift: 0.5, width, height } };
  g['10'] = { class_type: 'CFGGuider', inputs: { model: ['9', 0], positive: ['7', 0], negative: ['8', 0], cfg } };
  g['11'] = { class_type: 'KSamplerSelect', inputs: { sampler_name: 'euler' } };
  g['12'] = { class_type: 'BasicScheduler', inputs: { model: ['9', 0], scheduler: 'simple', steps, denoise: 1.0 } };
  g['13'] = { class_type: 'RandomNoise', inputs: { noise_seed: seed } };
  g['14'] = { class_type: 'EmptyLatentImage', inputs: { width, height, batch_size: 1 } };
  g['15'] = { class_type: 'SamplerCustomAdvanced', inputs: { noise: ['13', 0], guider: ['10', 0], sampler: ['11', 0], sigmas: ['12', 0], latent_image: ['14', 0] } };
  g['16'] = { class_type: 'VAEDecode', inputs: { samples: ['15', 0], vae: ['3', 0] } };
  g['17'] = { class_type: 'SaveImage', inputs: { images: ['16', 0], filename_prefix: prefix } };
  return g;
}
