// Bongpot — USO dual-channel graph builder (the keyframe renderer that won 2026-06-09).
//
// One graph, three separated channels, sampled at FULL denoise:
//   identity = photoreal plate → scale(512) → VAEEncode → ReferenceLatent
//              → FluxKontextMultiReferenceLatentMethod('uxo/uno')   [conditioning, NOT latent]
//   style    = face-free texture swatch → CLIPVisionEncode(sigclip) → USOStyleReference
//   scene    = content-only text → CLIPTextEncode
//
// Wiring extracted from ComfyUI's shipped flux1_dev_uso_reference_image_gen template.
// Shots with no character subject (inserts, empty rooms) drop the identity chain and
// keep style + text. This module is the graph SSOT — uso-probe.mjs and
// generate-stills.mjs both build from here.

export function buildUsoGraph({
  plateImage = null,        // server-side filename of the identity plate (LoadImage), or null
  swatchImage,              // server-side filename of the style swatch (LoadImage)
  prompt,                   // content-only scene text
  seed = 7,
  lora = 1.0,               // USO dit-lora strength
  guidance = 3.5,
  width = 768,
  height = 1024,
  steps = 20,
  prefix = 'uso',           // SaveImage filename_prefix (keep legible — Ryan peeks at the box)
  ckpt = 'flux1-dev-fp8.safetensors',
}) {
  const g = {
    1: { class_type: 'CheckpointLoaderSimple', inputs: { ckpt_name: ckpt } },
    2: { class_type: 'LoraLoaderModelOnly', inputs: { model: ['1', 0], lora_name: 'uso-flux1-dit-lora-v1.safetensors', strength_model: lora } },
    3: { class_type: 'ModelPatchLoader', inputs: { name: 'uso-flux1-projector-v1.safetensors' } },
    4: { class_type: 'CLIPVisionLoader', inputs: { clip_name: 'sigclip_vision_patch14_384.safetensors' } },
    // style channel
    5: { class_type: 'LoadImage', inputs: { image: swatchImage } },
    6: { class_type: 'CLIPVisionEncode', inputs: { clip_vision: ['4', 0], image: ['5', 0], crop: 'center' } },
    7: { class_type: 'USOStyleReference', inputs: { model: ['2', 0], model_patch: ['3', 0], clip_vision_output: ['6', 0] } },
    // scene channel
    11: { class_type: 'CLIPTextEncode', inputs: { clip: ['1', 1], text: prompt } },
    15: { class_type: 'ConditioningZeroOut', inputs: { conditioning: ['11', 0] } },
    16: { class_type: 'EmptySD3LatentImage', inputs: { width, height, batch_size: 1 } },
    18: { class_type: 'VAEDecode', inputs: { samples: ['17', 0], vae: ['1', 2] } },
    19: { class_type: 'SaveImage', inputs: { images: ['18', 0], filename_prefix: prefix } },
  };
  // identity channel (conditioning-side, so denoise stays 1.0)
  let positiveFrom = ['11', 0];
  if (plateImage) {
    g[8] = { class_type: 'LoadImage', inputs: { image: plateImage } };
    g[9] = { class_type: 'ImageScaleToMaxDimension', inputs: { image: ['8', 0], upscale_method: 'area', largest_size: 512 } };
    g[10] = { class_type: 'VAEEncode', inputs: { pixels: ['9', 0], vae: ['1', 2] } };
    g[12] = { class_type: 'ReferenceLatent', inputs: { conditioning: ['11', 0], latent: ['10', 0] } };
    g[13] = { class_type: 'FluxKontextMultiReferenceLatentMethod', inputs: { conditioning: ['12', 0], reference_latents_method: 'uxo/uno' } };
    positiveFrom = ['13', 0];
  }
  g[14] = { class_type: 'FluxGuidance', inputs: { conditioning: positiveFrom, guidance } };
  g[17] = {
    class_type: 'KSampler',
    inputs: {
      model: ['7', 0], positive: ['14', 0], negative: ['15', 0], latent_image: ['16', 0],
      seed, steps, cfg: 1.0, sampler_name: 'euler', scheduler: 'simple', denoise: 1.0,
    },
  };
  return g;
}
