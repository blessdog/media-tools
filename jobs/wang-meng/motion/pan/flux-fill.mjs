// GATE — fill the disocclusion holes with Flux 1 Fill, then hard-composite.
//
// Composition script, not a tool: it wires render output into _replicate.mjs.
//
// THE HARD COMPOSITE IS THE POINT. Whatever the model returns, only the pixels
// INSIDE our mask are kept; everything else is copied back from our own render,
// byte-exact. That is what makes this safe where the Wan gate was not — the
// model physically cannot repaint the horse, because the horse never survives
// the composite. A model asked to behave will eventually not; a model whose
// output is discarded outside 9% of the frame cannot misbehave there at all.
//
// THE PROMPT NAMES THE REAL TECHNIQUE. Ryan, 2026-08-17, distinguishing 山水
// (genre) / 水墨 (loose ink-wash) / 工笔 (fine line). Our styles/inkwash string
// describes WESTERN watercolour — cold-press rag, blooms, backruns, granulation
// — and this painting is dry-brush 解索皴 texture strokes plus flat mineral
// colour on xuan paper. Prompting a fill with the inkwash string would aim the
// model at the wrong picture. Positive description only: naming a forbidden
// thing summons it (the negation trap, styles/inkwash/style.json).
import { readFileSync, writeFileSync } from 'node:fs';
import { basename } from 'node:path';
import { predictModel, fetchBytes } from '../../../../tools/_replicate.mjs';
import { envKey } from '../../../../tools/_env.mjs';

const MODEL = 'black-forest-labs/flux-fill-pro';
const PROMPT = 'A Yuan dynasty Chinese shan shui landscape painting on aged '
  + 'xuan paper. Dense dry-brush texture strokes build the rock and earth: fine '
  + 'repeated hair-like linear strokes layered over pale grey ink wash, with '
  + 'muted earth-toned mineral colour. Continue the surrounding brushwork and '
  + 'the tone of the aged paper exactly.';

const a = process.argv.slice(2);
const arg = (n, d) => { const i = a.indexOf(n); return i >= 0 ? a[i + 1] : d; };
const IMAGE = arg('--image', 'fill/holed.png');
const MASK = arg('--mask', 'fill/mask.png');
const OUT = arg('--out', 'fill/flux-raw.png');
const P = arg('--prompt', PROMPT);
const GUID = parseFloat(arg('--guidance', '30'));

const tok = envKey('REPLICATE_API_TOKEN');

async function upload(path, mime = 'image/png') {
  const body = new FormData();
  body.append('content', new Blob([readFileSync(path)], { type: mime }), basename(path));
  const r = await fetch('https://api.replicate.com/v1/files', {
    method: 'POST', headers: { Authorization: `Bearer ${tok}` }, body,
  });
  const j = await r.json();
  if (!r.ok) throw new Error(`upload ${r.status}: ${JSON.stringify(j).slice(0, 300)}`);
  return j?.urls?.get;
}

console.error(`flux-fill: ${MODEL}  guidance ${GUID}`);
console.error(`prompt: ${P}`);
const [image, mask] = await Promise.all([upload(IMAGE), upload(MASK)]);
const url = await predictModel(MODEL, {
  image, mask, prompt: P,
  steps: 50, guidance: GUID, seed: 42, output_format: 'png',
}, { token: tok, label: 'flux-fill', interval: 4000, maxPolls: 200 });

writeFileSync(OUT, await fetchBytes(url));
console.log(JSON.stringify({ out: OUT, model: MODEL, url }));
