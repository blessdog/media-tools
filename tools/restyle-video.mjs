// media-tools — restyle-video: existing clip + style → restyled clip. One job.
//
// Model schemas verified live against the Replicate API 2026-08-11:
//   luma/modify-video            ≤30s / 100MB · mode dial adhere_1..reimagine_3
//                                · first_frame style anchor          ← default
//   wan-video/wan-2.7-videoedit  2-10s · audio_setting=origin keeps source audio
//   kwaivgi/kling-v3-omni-video  reference_video 3-10s · up to 4 reference_images
//   runwayml/gen4-aleph          <16MB and ONLY the first 5s is used
//
// The first_frame anchor is the point of this tool: restyle ONE frame with
// restyle-image, approve it by eye, then hand that approved frame here so the
// look comes from a picture Ryan signed off on rather than prompt roulette.
// Iteration then happens at image cost, not video cost.

import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join, basename, extname } from 'node:path';
import { envKey, repoRoot } from './_env.mjs';
import { predictModel, fetchBytes } from './_replicate.mjs';

const HELP = `restyle-video — restyle an existing clip, preserving its motion

usage: node restyle-video.mjs --video in.mp4 --out out.mp4 [flags]

flags:
  --video PATH        (required) source clip
  --out PATH          (required) output clip
  --style KEY         style from styles/KEY/style.json (default: inkwash)
  --prompt TEXT       extra direction appended after the style
  --raw               no style; --prompt verbatim
  --model M           luma/modify-video (default)
                      | wan-video/wan-2.7-videoedit
                      | kwaivgi/kling-v3-omni-video
                      | runwayml/gen4-aleph
  --mode M            luma only: adhere_1|2|3 flex_1|2|3 reimagine_1|2|3 (default flex_2)
  --first-frame PATH  luma only: pre-styled frame 1 as the style anchor
  --keep-audio        wan only: audio_setting=origin

limits: luma ≤30s/100MB · wan 2-10s · kling 3-10s · aleph <16MB, first 5s only

example:
  node ~/projects/media-tools/tools/restyle-video.mjs --video slice.mp4 \\
    --style inkwash --mode flex_2 --first-frame anchor.png --out slice-inkwash.mp4`;

const args = process.argv.slice(2);
if (args.includes('--help') || args.length === 0) { console.log(HELP); process.exit(0); }
const flag = (n, d) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : d; };
const video = flag('--video');
const out = flag('--out');
if (!video || !out) { console.error(HELP); process.exit(2); }

const raw = args.includes('--raw');
const styleKey = flag('--style', 'inkwash');
const extra = flag('--prompt', '');
let stylePrompt = '';
if (!raw) {
  const p = join(repoRoot(), 'styles', styleKey, 'style.json');
  try { stylePrompt = JSON.parse(readFileSync(p, 'utf8')).prompt; }
  catch { console.error(`unknown --style '${styleKey}' (no ${p})`); process.exit(2); }
}
// Edit models need an INSTRUCTION verb, not a bare style noun-phrase — proven
// on restyle-image 2026-08-11, where the noun-phrase alone returned the source.
const prompt = raw
  ? extra
  : `Repaint every frame of this video in the following style, keeping the exact same motion, composition, subjects and framing. ${stylePrompt}${extra ? ' ' + extra : ''}`;
if (!prompt.trim()) { console.error('need --style or --prompt'); process.exit(2); }

const model = flag('--model', 'luma/modify-video');
const tok = envKey('REPLICATE_API_TOKEN');
const MIME = { '.mp4': 'video/mp4', '.mov': 'video/quicktime', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg' };

// Replicate fetches these server-side and rejects data: URIs with a bare E002
// that names nothing (proven in the i2v path) — upload the file first.
async function uploadFile(path) {
  const mime = MIME[extname(path).toLowerCase()] || 'application/octet-stream';
  const body = new FormData();
  body.append('content', new Blob([readFileSync(path)], { type: mime }), basename(path));
  const r = await fetch('https://api.replicate.com/v1/files', {
    method: 'POST', headers: { Authorization: `Bearer ${tok}` }, body,
  });
  const j = await r.json();
  if (!r.ok || !j?.urls?.get) throw new Error(`upload ${r.status}: ${JSON.stringify(j).slice(0, 300)}`);
  return j.urls.get;
}

const videoUrl = await uploadFile(video);
const firstFrame = flag('--first-frame');
const MODELS = {
  'luma/modify-video': async () => ({
    video: videoUrl, prompt, mode: flag('--mode', 'flex_2'),
    ...(firstFrame ? { first_frame: await uploadFile(firstFrame) } : {}),
  }),
  'wan-video/wan-2.7-videoedit': async () => ({
    video: videoUrl, prompt, resolution: '1080p',
    ...(args.includes('--keep-audio') ? { audio_setting: 'origin' } : {}),
  }),
  'kwaivgi/kling-v3-omni-video': async () => ({
    prompt: `restyle <<<video_1>>>: ${prompt}`, reference_video: videoUrl, video_reference_type: 'base',
  }),
  'runwayml/gen4-aleph': async () => ({ video: videoUrl, prompt }),
};
if (!MODELS[model]) { console.error(`unknown --model '${model}' (known: ${Object.keys(MODELS).join(', ')})`); process.exit(2); }

console.error(`restyle-video: ${model}${firstFrame ? ` · anchored on ${basename(firstFrame)}` : ''} → ${out}`);
const url = await predictModel(model, await MODELS[model](), { token: tok, label: 'restyle-video', interval: 5000, maxPolls: 360 });
const bytes = await fetchBytes(url);
mkdirSync(dirname(out), { recursive: true });
writeFileSync(out, bytes);
console.log(JSON.stringify({ out, bytes: bytes.length, model, style: raw ? null : styleKey, anchored: !!firstFrame }));
