// media-tools — plan-planes: a painting → its depth planes, reasoned by a VLM.
//
// It PLANS. It writes a points.json and cuts nothing; segment-points does the
// cutting. Keeping them apart is what lets the plan be reviewed, corrected and
// re-run without paying for segmentation again.
//
// WHY A LANGUAGE MODEL AND NOT A DEPTH MODEL (2026-08-13, three failures deep).
//   Depth-Anything-V2 Large on Wang Meng's 葛稚川移居圖 → a top-to-bottom ramp
//     with one tree cut out. Same at native resolution on a square crop. It is
//     trained on photographs and reads perspective, defocus and haze, none of
//     which a Yuan hanging scroll contains.
//   SAM automatic → forty objects along the ink contours, 66% of the frame
//     unclaimed. 4x the sample density recovered three points. Tiling made it
//     worse. It finds objects; it never finds planes.
//
// The conclusion I drew from those two was wrong: that a human must click. The
// missing capability was never perception, it was SEMANTIC REASONING ABOUT
// OCCLUSION. "The pine is in front of the cliff, the cliff is in front of the
// peaks" is a sentence about a scene, not a measurement of pixels — and Wang
// Meng drew every one of those occlusions as an explicit ink contour, so the
// evidence is right there on the surface for anything that can read a picture.
//
// A hanging scroll also has a known grammar the model can use: it is read
// bottom to top, near to far, with bands of bare paper (留白) separating the
// planes. That prior is worth more here than any amount of pixel statistics.
//
// usage:
//   plan-planes.mjs --image IN --out points.json [flags]
//
//   --image PATH     the master image
//   --out PATH       points.json, in the schema segment-points consumes
//   --planes N       how many to aim for (default 12). The painting decides the
//                    real number; this is a target, not a quota.
//   --model M        vision model via OpenRouter (default ${DEFAULT_MODEL})
//   --slices N       also send N vertical slices (default 3). A 1:2.4 scroll
//                    sent whole arrives at the model as a thumbnail; slices are
//                    how the lower half gets seen at all.
//   --review DIR     REVIEW MODE. Reads DIR/overlay.png and DIR/layers.json
//                    from a previous cut, shows the model what its own plan
//                    produced, and writes a corrected points.json. This is the
//                    loop that makes it self-fixing rather than one-shot.
//   --notes TEXT     extra direction ("keep the waterfall its own plane")
//
// JSON on stdout. Progress on stderr.
//
// example:
//   node tools/plan-planes.mjs --image corpus/grabs/wang-meng.png \
//     --out jobs/wang-meng/points.json --planes 14

import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { dirname, basename } from 'node:path';
import { execFileSync } from 'node:child_process';
import { envKey } from './_env.mjs';

const OPENROUTER_CHAT_URL = 'https://openrouter.ai/api/v1/chat/completions';
const DEFAULT_MODEL = 'anthropic/claude-opus-4-5';

const HELP = `plan-planes — a painting → its depth planes, reasoned by a vision model

usage: node plan-planes.mjs --image IN --out points.json [flags]

  --image PATH     the master image (full resolution; it is downscaled to send)
  --out PATH       where points.json lands
  --planes N       target number of planes (default 12)
  --model M        vision model via OpenRouter (default ${DEFAULT_MODEL})
  --slices N       vertical slices sent alongside the whole image (default 3)
  --review DIR     read DIR/overlay.png + DIR/layers.json from a previous cut
                   and write a CORRECTED plan
  --notes TEXT     extra direction for the model

Writes points.json: { image, points: [{ id, x, y, depth, window, name, pick }] }
  x,y     normalised 0..1 on the master
  depth   0 = farthest, 9 = nearest
  window  native px around the point handed to SAM; a mask cannot exceed it
  pick    whole | best | tight

example:
  node ~/projects/media-tools/tools/plan-planes.mjs \\
    --image corpus/grabs/wang-meng.png --out jobs/wang-meng/points.json`;

const args = process.argv.slice(2);
if (args.includes('--help') || args.length === 0) { console.log(HELP); process.exit(0); }
const flag = (n, d) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : d; };

const image = flag('--image');
const out = flag('--out');
if (!image || !out) { console.error(HELP); process.exit(2); }
if (!existsSync(image)) { console.error(`no such image: ${image}`); process.exit(1); }
const model = flag('--model', DEFAULT_MODEL);
const planes = parseInt(flag('--planes', '12'), 10);
const slices = parseInt(flag('--slices', '3'), 10);
const review = flag('--review');
const notes = flag('--notes', '');

// ffmpeg rather than a decode library: the master is 105MP and only a small
// JPEG ever needs to exist in memory.
const TMP = process.env.TMPDIR || '/tmp';
function jpeg(src, filter, tag) {
  const p = `${TMP}/planplan-${tag}-${process.pid}.jpg`;
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', src, '-vf', filter, '-q:v', '4', p]);
  return `data:image/jpeg;base64,${readFileSync(p).toString('base64')}`;
}
const size = (src) => {
  const o = execFileSync('ffprobe', ['-v', 'error', '-select_streams', 'v:0',
    '-show_entries', 'stream=width,height', '-of', 'csv=p=0:s=x', src], { encoding: 'utf8' }).trim();
  const [w, h] = o.split('x').map(Number);
  return { w, h };
};

const { w: W, h: H } = size(image);
console.error(`  ${basename(image)}  ${W}x${H}  model=${model}`);

const SYSTEM = `You separate a painting into DEPTH PLANES for a 2.5D parallax animation, where a
virtual camera moves through the scene and each plane shifts at its own rate.

What you are looking at is usually a Chinese hanging scroll. Its grammar matters and you should use it:
it is read bottom to top as a journey from near to far, its planes are separated by bands of bare paper
(留白) that read as mist or water, and — decisively — EVERY occlusion is drawn as an explicit ink contour.
Where one form passes in front of another the painter said so with a line. Read those lines. That is the
depth information, and it is the only reliable kind in this material: there is no linear perspective, no
defocus, and no photographic haze gradient to measure.

A PLANE is a region that would move as one rigid piece if the camera shifted sideways. A near boulder and
the cliff behind it are two planes. Three trees on the same ledge are one plane. Do not separate things by
subject matter, colour or interest — only by distance from the viewer.

For each plane return:
  name    short kebab-case, e.g. far-peaks, mid-cliff-left, foreground-pine
  x, y    a point NORMALISED 0..1 that lands SQUARELY INSIDE that plane, well away from its edges and
          not on top of anything nearer. This point is handed to a segmentation model as a prompt, so
          it must be in the meatiest, most unambiguous part of the region.
  depth   integer 0..9. 0 = farthest, 9 = nearest. Reuse a number when two regions are genuinely at the
          same distance. Do not spread them evenly for the sake of it.
  window  the crop in NATIVE PIXELS handed to the segmenter around that point. THE MASK CANNOT EXTEND
          BEYOND THIS WINDOW, so it must comfortably contain the whole plane — err large. A whole
          mountain mass on this image wants 5000-9000; a single figure wants 1000-1500.
  pick    "whole" almost always. "tight" only for a small distinct object inside a bigger form.
  why     one short clause naming the ink contour or overlap that puts it at that depth.

Return ONLY a JSON object: {"planes":[...]} — no prose, no markdown fence.`;

const content = [];
let user;

if (review) {
  const ov = `${review}/overlay.png`;
  const lj = `${review}/layers.json`;
  if (!existsSync(ov) || !existsSync(lj)) { console.error(`--review needs ${ov} and ${lj}`); process.exit(1); }
  const prev = JSON.parse(readFileSync(lj, 'utf8'));
  const summary = (prev.planeList || []).map((p) => ({
    name: p.name, depth: p.depth, point: p.point, window: p.window,
    clippedByWindow: p.clippedByWindow, windowFraction: p.windowFraction, areaFinal: p.areaFinal,
  }));
  user = `This is your previous plan, CUT and rendered as a colour overlay. Second image is the overlay,
first is the original painting.

Per-plane results:
${JSON.stringify(summary, null, 1)}

${prev.unclaimedFraction != null ? `${(prev.unclaimedFraction * 100).toFixed(0)}% of the frame is still unclaimed.\n` : ''}
Judge your own work against the overlay and fix it. Specifically:
- clippedByWindow:true means the mask ran into the edge of its crop and has a STRAIGHT ARTIFICIAL
  BOUNDARY. Raise that plane's window until it contains the whole form.
- A plane covering far more or far less than you intended means the point landed in the wrong place.
  Move it into the middle of the region you actually meant.
- Large unclaimed areas mean planes are missing. Add them.
- Two planes that came back as the same region means one point is redundant. Drop it.

Return the CORRECTED full plan, same schema. Keep what worked, unchanged.`;
  content.push({ type: 'text', text: user });
  content.push({ type: 'image_url', image_url: { url: jpeg(image, 'scale=-2:1400', 'orig') } });
  content.push({ type: 'image_url', image_url: { url: jpeg(ov, 'scale=-2:1400', 'ov') } });
} else {
  user = `This painting is ${W} x ${H} native pixels, aspect ${(W / H).toFixed(3)}.
Separate it into about ${planes} depth planes.

You are given the whole image first, then ${slices} vertical slices from top to bottom at higher
magnification — the whole image alone arrives as a thumbnail on a scroll this tall, and the lower
half is where most of the near planes are. Coordinates you return must be normalised against the
WHOLE image, not against a slice: slice k of ${slices} covers y from ${'{'}k/${slices}${'}'} to ${'{'}(k+1)/${slices}${'}'}.

Remember the window field is in native pixels of a ${W} x ${H} image.${notes ? `\n\nAlso: ${notes}` : ''}`;
  content.push({ type: 'text', text: user });
  content.push({ type: 'image_url', image_url: { url: jpeg(image, 'scale=-2:1500', 'whole') } });
  for (let k = 0; k < slices; k++) {
    const f = `crop=iw:ih/${slices}:0:ih*${k}/${slices},scale=-2:1200`;
    content.push({ type: 'text', text: `Slice ${k + 1} of ${slices}: y from ${(k / slices).toFixed(3)} to ${((k + 1) / slices).toFixed(3)}.` });
    content.push({ type: 'image_url', image_url: { url: jpeg(image, f, `s${k}`) } });
  }
}

console.error(`  sending ${content.filter((c) => c.type === 'image_url').length} images…`);
const key = envKey('OPENROUTER_API_KEY');
const r = await fetch(OPENROUTER_CHAT_URL, {
  method: 'POST',
  headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
  body: JSON.stringify({
    model,
    messages: [{ role: 'system', content: SYSTEM }, { role: 'user', content }],
    max_tokens: 8000,
  }),
});
const j = await r.json();
if (!r.ok) { console.error(`openrouter ${r.status}: ${JSON.stringify(j).slice(0, 400)}`); process.exit(1); }
const text = j?.choices?.[0]?.message?.content?.trim() || '';

// Models fence JSON even when told not to. Take the outermost object.
const raw = text.replace(/^```(?:json)?\s*|\s*```$/g, '');
let parsed;
try {
  parsed = JSON.parse(raw.slice(raw.indexOf('{'), raw.lastIndexOf('}') + 1));
} catch (e) {
  console.error(`could not parse the model's reply: ${e.message}`);
  console.error(text.slice(0, 600));
  process.exit(1);
}

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const points = (parsed.planes || parsed.points || []).map((p, i) => ({
  id: i + 1,
  x: +clamp(Number(p.x), 0, 1).toFixed(5),
  y: +clamp(Number(p.y), 0, 1).toFixed(5),
  depth: clamp(Math.round(Number(p.depth) || 0), 0, 9),
  // A window bigger than the image is pointless, and one under 600px cannot
  // hold anything a plane would be.
  window: clamp(Math.round(Number(p.window) || 2500), 600, Math.max(W, H)),
  name: String(p.name || `plane-${i + 1}`).replace(/[^\w-]+/g, '-').toLowerCase(),
  pick: ['whole', 'best', 'tight'].includes(String(p.pick)) ? String(p.pick) : 'whole',
  why: String(p.why || '').slice(0, 200),
}));

if (!points.length) { console.error('the model returned no planes'); process.exit(1); }

mkdirSync(dirname(out), { recursive: true });
writeFileSync(out, JSON.stringify({
  image, size: [W, H], model, planned: points.length,
  mode: review ? 'review' : 'initial', notes: notes || null,
  note: 'x,y normalised 0..1. depth 0 = farthest. window in native px; a mask cannot exceed it.',
  points,
}, null, 2));

for (const p of points.slice().sort((a, b) => a.depth - b.depth)) {
  console.error(`    ${String(p.depth).padStart(2)}  ${p.name.padEnd(22)} @${p.x.toFixed(3)},${p.y.toFixed(3)}  win=${String(p.window).padStart(5)}  ${p.why}`);
}
console.log(JSON.stringify({ tool: 'plan-planes', out, model, planes: points.length, mode: review ? 'review' : 'initial' }, null, 2));
