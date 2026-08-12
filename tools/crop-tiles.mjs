// media-tools — crop-tiles: artwork scans → square training tiles. One job.
//
// Why tiles and not whole paintings:
//   1. Museum scans include what surrounds the painting — brocade mounting silk,
//      hanging rods, album mats, frame edges, colour bars. A LoRA trained on
//      whole scans learns brown silk borders as part of "ink wash". Insetting
//      before tiling removes that without anyone hand-cropping 400 images.
//   2. LTX preprocessing CENTER-CROPS to the training bucket, so feeding it a
//      6:1 handscroll yields one random middle slice. Tiling turns that same
//      scroll into a dozen honest samples.
//   3. Tiles are native resolution. A 3400px painting downscaled whole to 1280
//      loses exactly the brush granulation the LoRA is supposed to learn.
//   4. Corpus arithmetic: 400 paintings x 4 tiles is 1600 samples, comfortably
//      past the "low hundreds" a broad style needs.
//
// The one real trap: ink wash is mostly 留白 — empty paper. A tile of blank
// paper teaches nothing and dilutes the set, so tiles below --min-ink are
// dropped. That threshold is the knob worth tuning; run --explain first.
//
// Requires ImageMagick (`magick`), same dependency the contact sheets use.

import { readFileSync, writeFileSync, mkdirSync, existsSync, readdirSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { join, basename, extname } from 'node:path';

const HELP = `crop-tiles — cut artwork scans into square training tiles

usage: node crop-tiles.mjs --in RAWDIR --out TILEDIR [flags]

Reads every image in RAWDIR that has a .json sidecar beside it (the shape
fetch-artwork writes), and emits square tiles plus a sidecar per tile carrying
the parent's provenance.

flags:
  --in DIR         (required) directory of images + .json sidecars
  --out DIR        (required) where tiles land
  --size N         tile edge in pixels (default 1024)
  --inset F        fraction trimmed off EACH edge before tiling (default 0.06).
                   This is what removes mounting silk, mats and frame edges.
                   Raise to 0.10+ for collections with wide brocade mounts.
  --min-ink F      drop tiles whose pixel standard deviation is below this
                   (default 0.055, 0-1 scale). Blank paper scores near 0.
  --max-tiles N    cap tiles per painting (default 6) so one big handscroll
                   cannot dominate the corpus the way one album did
  --overlap F      fraction of tile size to overlap between neighbours (default 0)
  --explain        report the tile grid and ink scores for the first 5 images
                   and write NOTHING

example:
  node ~/projects/media-tools/tools/crop-tiles.mjs \\
    --in corpus/inkwash/raw --out corpus/inkwash/tiles --size 1024 --min-ink 0.055`;

const args = process.argv.slice(2);
if (args.includes('--help') || args.length === 0) { console.log(HELP); process.exit(0); }
const flag = (n, d) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : d; };

const inDir = flag('--in');
const outDir = flag('--out');
const explain = args.includes('--explain');
if (!inDir || (!outDir && !explain)) { console.error(HELP); process.exit(2); }
const size = parseInt(flag('--size', '1024'), 10);
const inset = parseFloat(flag('--inset', '0.06'));
const minInk = parseFloat(flag('--min-ink', '0.055'));
const maxTiles = parseInt(flag('--max-tiles', '6'), 10);
const overlap = parseFloat(flag('--overlap', '0'));

function magick(a) { return execFileSync('magick', a, { encoding: 'utf8', maxBuffer: 1 << 26 }).trim(); }

// Standard deviation over the tile, normalised 0-1. Ink on white paper has a
// wide spread; blank paper is nearly flat. Cheaper and steadier than counting
// dark pixels, which a warm paper tone alone can trip.
function inkScore(file, x, y, w, h) {
  const out = magick([file, '-crop', `${w}x${h}+${x}+${y}`, '+repage',
    '-colorspace', 'Gray', '-format', '%[fx:standard_deviation]', 'info:']);
  return parseFloat(out) || 0;
}

// Grid the inset region. Tiles are square and never scaled up: an image whose
// short edge is under `size` simply yields one tile at its own scale.
function planTiles(w, h) {
  const dx = Math.round(w * inset), dy = Math.round(h * inset);
  const iw = w - 2 * dx, ih = h - 2 * dy;
  const edge = Math.min(size, iw, ih);
  const step = Math.max(1, Math.round(edge * (1 - overlap)));
  const cols = Math.max(1, Math.floor((iw - edge) / step) + 1);
  const rows = Math.max(1, Math.floor((ih - edge) / step) + 1);
  // Spread the leftover so tiles sit evenly instead of bunching at the origin.
  const padX = cols > 1 ? (iw - edge - step * (cols - 1)) / (cols - 1) : 0;
  const padY = rows > 1 ? (ih - edge - step * (rows - 1)) / (rows - 1) : 0;
  const tiles = [];
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      tiles.push({
        x: Math.round(dx + c * (step + padX)),
        y: Math.round(dy + r * (step + padY)),
        w: edge, h: edge,
      });
    }
  }
  return { tiles, edge, cols, rows, inset: { dx, dy } };
}

const images = readdirSync(inDir)
  .filter((f) => /\.(jpe?g|png|tiff?)$/i.test(f))
  .filter((f) => existsSync(join(inDir, basename(f, extname(f)) + '.json')))
  .sort();

if (!images.length) { console.error(`no image+sidecar pairs in ${inDir}`); process.exit(2); }
console.error(`crop-tiles: ${images.length} paintings · ${size}px tiles · inset ${inset} · min-ink ${minInk} · max ${maxTiles}/painting`);

if (explain) {
  const report = [];
  for (const f of images.slice(0, 5)) {
    const file = join(inDir, f);
    const [w, h] = magick([file, '-format', '%w %h', 'info:']).split(' ').map(Number);
    const plan = planTiles(w, h);
    const scored = plan.tiles.map((t) => ({ ...t, ink: +inkScore(file, t.x, t.y, t.w, t.h).toFixed(4) }));
    report.push({
      file: f, source: `${w}x${h}`, tileEdge: plan.edge, grid: `${plan.cols}x${plan.rows}`,
      wouldKeep: scored.filter((t) => t.ink >= minInk).length, tiles: scored,
    });
  }
  console.log(JSON.stringify({ tool: 'crop-tiles', size, inset, minInk, maxTiles, overlap,
    paintings: images.length, spent: 'nothing', sample: report }, null, 2));
  process.exit(0);
}

mkdirSync(outDir, { recursive: true });
let written = 0, blank = 0, done = 0;

for (const f of images) {
  const file = join(inDir, f);
  const stem = basename(f, extname(f));
  const meta = JSON.parse(readFileSync(join(inDir, stem + '.json'), 'utf8'));
  let w, h;
  try { [w, h] = magick([file, '-format', '%w %h', 'info:']).split(' ').map(Number); }
  catch { console.error(`\n  unreadable: ${f}`); continue; }

  const { tiles, edge } = planTiles(w, h);
  // Rank by ink and keep the densest, so the cap never keeps a blank corner
  // over a tile full of brushwork.
  const scored = tiles.map((t) => ({ ...t, ink: inkScore(file, t.x, t.y, t.w, t.h) }))
    .sort((a, b) => b.ink - a.ink);

  let n = 0;
  for (const t of scored) {
    if (n >= maxTiles) break;
    if (t.ink < minInk) { blank++; continue; }
    const outName = `${stem}-t${n}.png`;
    magick([file, '-crop', `${t.w}x${t.h}+${t.x}+${t.y}`, '+repage', join(outDir, outName)]);
    writeFileSync(join(outDir, `${stem}-t${n}.json`), JSON.stringify({
      ...meta, tile: { index: n, x: t.x, y: t.y, edge, ink: +t.ink.toFixed(4),
        parent: f, parentSize: `${w}x${h}`, inset, minInk },
      file: join(outDir, outName), croppedBy: 'media-tools/crop-tiles',
    }, null, 2));
    n++; written++;
  }
  done++;
  process.stderr.write(`\r  ${done}/${images.length} paintings · ${written} tiles`);
}

process.stderr.write('\n');
console.log(JSON.stringify({ tool: 'crop-tiles', in: inDir, out: outDir, size, inset, minInk,
  maxTiles, paintings: done, tiles: written, blankTilesDropped: blank }, null, 2));
