// media-tools — image-to-video: one still + a motion prompt → one clip. One job.
//
// Salvaged from cutwork/tools/quick-i2v.mjs 2026-08-11. The model adapter table
// and its hard-won settings are unchanged: upload-not-data-URI, and
// seedance-1-lite as the working default since wan-2.5-i2v-fast fails
// server-side with an opaque E002 (verified 2026-08-05). Normalized to the tool
// contract: repo-rooted secrets, --help, progress on stderr, JSON on stdout.

import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, basename } from 'node:path';
import { envKey } from './_env.mjs';
import { predictModel, fetchBytes } from './_replicate.mjs';

const HELP = `image-to-video — animate one still into one motion clip via Replicate

usage: node image-to-video.mjs --image still.png --prompt "..." --out clip.mp4 [flags]

flags:
  --image PATH     (required) source still
  --prompt TEXT    (required) motion description ("mist drifts, water ripples")
  --out PATH       (required) output clip
  --duration N     seconds (default 5)
  --resolution R   480p | 720p | 1080p (default 720p)
  --model M        bytedance/seedance-1-lite (default)
                   | bytedance/seedance-1-pro
                   | wan-video/wan-2.5-i2v-fast  (BROKEN server-side: E002)
  --moving         let the camera move (default: camera holds)

example:
  node ~/projects/media-tools/tools/image-to-video.mjs \\
    --image stills/01.png --prompt "slow drift, mist rolls left" --out clips/01.mp4`;

const args = process.argv.slice(2);
if (args.includes('--help') || args.length === 0) { console.log(HELP); process.exit(0); }
const flag = (n, d) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : d; };
const image = flag('--image');
const prompt = flag('--prompt');
const out = flag('--out');
if (!image || !prompt || !out) { console.error(HELP); process.exit(2); }
const duration = parseInt(flag('--duration', '5'), 10);
const resolution = flag('--resolution', '720p');
const model = flag('--model', 'bytedance/seedance-1-lite');
const fixed = !args.includes('--moving');

// Same three adapters i2v-replicate.mjs proved; wan-2.5-i2v-fast kept for
// reference only — it fails server-side (E002) as of 2026-08-05, do not
// default to it without re-verifying.
const MODELS = {
  'bytedance/seedance-1-lite': ({ url, prompt, duration, resolution, fixed }) => ({
    image: url, prompt, duration, resolution, fps: 24, camera_fixed: fixed,
  }),
  'bytedance/seedance-1-pro': ({ url, prompt, duration, resolution, fixed }) => ({
    image: url, prompt, duration, resolution, fps: 24, camera_fixed: fixed,
  }),
  'wan-video/wan-2.5-i2v-fast': ({ url, prompt, duration, resolution }) => ({
    image: url, prompt, duration, resolution,
    negative_prompt: 'text, lettering, writing, watermark, signature, photographic, glossy, 3d render, camera shake, jump cut, flicker, morphing, warping',
    enable_prompt_expansion: false,
  }),
};
const build = MODELS[model];
if (!build) throw new Error(`unknown --model '${model}' (known: ${Object.keys(MODELS).join(', ')})`);

// Wan/Seedance fetch `image` server-side and reject data: URIs with a bare
// "E002" that names nothing (i2v-replicate.mjs, verified) — upload first.
async function uploadImage(path, tok) {
  const body = new FormData();
  body.append('content', new Blob([readFileSync(path)], { type: 'image/png' }), basename(path));
  const r = await fetch('https://api.replicate.com/v1/files', {
    method: 'POST', headers: { Authorization: `Bearer ${tok}` }, body,
  });
  const j = await r.json();
  if (!r.ok) throw new Error(`upload ${r.status}: ${JSON.stringify(j).slice(0, 300)}`);
  const url = j?.urls?.get;
  if (!url) throw new Error('upload succeeded but returned no URL');
  return url;
}

const tok = envKey('REPLICATE_API_TOKEN');
console.error(`image-to-video: ${model} · ${resolution} ${duration}s · camera_fixed=${fixed} → ${out}`);
console.error(`prompt: ${prompt}`);
const imageUrl = await uploadImage(image, tok);
const input = build({ url: imageUrl, prompt, duration, resolution, fixed });
const url = await predictModel(model, input, { token: tok, label: 'quick-i2v', interval: 4000, maxPolls: 300 });
const bytes = await fetchBytes(url);
mkdirSync(dirname(out), { recursive: true });
writeFileSync(out, bytes);
console.log(JSON.stringify({ out, bytes: bytes.length, model, duration, resolution, camera_fixed: fixed }));
