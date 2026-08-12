// media-tools — HunyuanVideo 1.5 image-to-video graph builder.
//
// Wiring extracted verbatim from ComfyUI's shipped template
// `video_hunyuan_video_1.5_720p_i2v.json` (read off the box 2026-08-12), the
// same way _uso.mjs was extracted from the flux USO template. Do not "improve"
// the wiring from memory — re-read the template if it needs to change.
//
// Deliberate difference from the template: EasyCache is NOT wired in. It is a
// speed/quality trade and this renderer exists because cheap motion models
// produce slop (CLAUDE.md). Full precision, full sampling, every time.
//
// Model set on the box:
//   diffusion_models/hunyuanvideo1.5_720p_i2v_fp16.safetensors   (16.6 GB, fp16)
//   text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors + byt5_small_glyphxl_fp16
//   vae/hunyuanvideo15_vae_fp16.safetensors
//   clip_vision/sigclip_vision_patch14_384.safetensors  (shared with the USO stack)

export function buildHunyuanI2VGraph({
  startImage,               // server-side filename of the still (LoadImage)
  prompt,                   // motion description — what MOVES, not what the frame is
  negative = '',
  seed = 7,
  width = 1280,
  height = 720,
  length = 121,             // frames; 121 @ 24fps ≈ 5s. Node step is 4.
  fps = 24,
  steps = 20,
  cfg = 6,                  // the template's value for the NON-distilled model
  shift = 7,                // ModelSamplingSD3
  prefix = 'hunyuan',
  unet = 'hunyuanvideo1.5_720p_i2v_fp16.safetensors',
  vae = 'hunyuanvideo15_vae_fp16.safetensors',
  clipVision = 'sigclip_vision_patch14_384.safetensors',
  textEncoder = 'qwen_2.5_vl_7b_fp8_scaled.safetensors',
  glyphEncoder = 'byt5_small_glyphxl_fp16.safetensors',
}) {
  return {
    1: { class_type: 'UNETLoader', inputs: { unet_name: unet, weight_dtype: 'default' } },
    2: { class_type: 'DualCLIPLoader', inputs: { clip_name1: textEncoder, clip_name2: glyphEncoder, type: 'hunyuan_video_15', device: 'default' } },
    3: { class_type: 'VAELoader', inputs: { vae_name: vae } },
    4: { class_type: 'CLIPVisionLoader', inputs: { clip_name: clipVision } },
    5: { class_type: 'LoadImage', inputs: { image: startImage } },
    6: { class_type: 'CLIPVisionEncode', inputs: { clip_vision: ['4', 0], image: ['5', 0], crop: 'center' } },
    7: { class_type: 'CLIPTextEncode', inputs: { clip: ['2', 0], text: prompt } },
    8: { class_type: 'CLIPTextEncode', inputs: { clip: ['2', 0], text: negative } },
    // Emits positive, negative AND the seeded latent — all three feed forward.
    9: { class_type: 'HunyuanVideo15ImageToVideo', inputs: {
      positive: ['7', 0], negative: ['8', 0], vae: ['3', 0],
      width, height, length, batch_size: 1,
      start_image: ['5', 0], clip_vision_output: ['6', 0],
    } },
    10: { class_type: 'ModelSamplingSD3', inputs: { model: ['1', 0], shift } },
    11: { class_type: 'CFGGuider', inputs: { model: ['10', 0], positive: ['9', 0], negative: ['9', 1], cfg } },
    12: { class_type: 'RandomNoise', inputs: { noise_seed: seed } },
    13: { class_type: 'KSamplerSelect', inputs: { sampler_name: 'euler' } },
    14: { class_type: 'BasicScheduler', inputs: { model: ['1', 0], scheduler: 'simple', steps, denoise: 1 } },
    15: { class_type: 'SamplerCustomAdvanced', inputs: {
      noise: ['12', 0], guider: ['11', 0], sampler: ['13', 0], sigmas: ['14', 0], latent_image: ['9', 2] } },
    16: { class_type: 'VAEDecode', inputs: { samples: ['15', 0], vae: ['3', 0] } },
    17: { class_type: 'CreateVideo', inputs: { images: ['16', 0], fps } },
    18: { class_type: 'SaveVideo', inputs: { video: ['17', 0], filename_prefix: prefix, format: 'auto', codec: 'h264' } },
  };
}
