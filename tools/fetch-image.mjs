// media-tools — fetch-image: one image from anywhere → the library, with its
// provenance attached. One job.
//
// The sibling of fetch-artwork, for everything fetch-artwork refuses.
// fetch-artwork speaks to museum APIs only, on purpose: the open web in 2026 is
// saturated with AI-generated ink wash, and scraping it feeds another model's
// output back into ours. That rule is right for a corpus sweep and wrong for a
// single deliberate grab — Wang Meng's 葛稚川移居圖 lives in the Palace Museum,
// Beijing, which publishes no open-access API, so the choice is "grab it with a
// record" or "grab it into ~/Downloads with no record at all".
//
// So this tool grabs it and LABELS it. Every sidecar carries:
//
//   provenance: "verified" | "asserted" | "unknown"
//
//   verified  a rights string from an institution — fetch-artwork's output
//   asserted  you told us who made it; nobody checked
//   unknown   a file with no story
//
// Six weeks from now that field is the difference between conditioning on a
// 14th-century hanging scroll and conditioning on somebody's pastiche of one.
// A grab with a caveat beats a grab with amnesia; both beat refusing to grab.
//
// It does NOT crop, convert, upscale or filter. crop-tiles does tiles,
// restyle-image does looks. A fetcher that starts editing is a pipeline.

import { writeFileSync, mkdirSync, existsSync, readFileSync, readdirSync } from 'node:fs';
import { join, basename, extname } from 'node:path';
import { createHash } from 'node:crypto';

const HELP = `fetch-image — one image + provenance sidecar into the library

usage: node fetch-image.mjs (--url URL | --file PATH) --out DIR [metadata]

source (exactly one):
  --url URL        download it
  --file PATH      adopt a file you already grabbed (it is copied, not moved —
                   the original stays where it is)

required:
  --out DIR        where the image and its .json sidecar land

metadata (all optional; each one you supply raises provenance to "asserted"):
  --title T        "Ge Zhichuan Moving to the Mountains"
  --artist A       "Wang Meng (Chinese, c. 1308-1385)"
  --date D         "c. 1360"
  --culture C      "China, Yuan dynasty (1271-1368)"
  --medium M       "Hanging scroll; ink and colour on paper"
  --holder H       the institution that holds the ORIGINAL work
  --source-page U  the page you found it on (not the image URL — the page)
  --rights R       a rights string if you have one
  --note TEXT      anything else worth remembering
  --provenance P   force verified|asserted|unknown instead of deriving it

other:
  --name STEM      filename stem; default is derived from --title, else the URL
  --force          overwrite an existing file of the same name
  --explain        print what WOULD be written, download nothing

Notes:
  The extension comes from the file's MAGIC BYTES, not from the URL. Hugging
  Face serves JPEGs named .png and that has already cost this project an hour.
  Dimensions are read from the header for PNG / JPEG / WebP / GIF; other
  formats record 0 rather than guess.
  The image is SHA-256'd into 'imageHash' — the same join key rectum uses for
  clips. An identical hash already in --out is reported and NOT re-written.

example:
  node ~/projects/media-tools/tools/fetch-image.mjs \\
    --file ~/Downloads/wang-meng_ge-zhichuan-moving-to-the-mountains.webp \\
    --out corpus/inkwash/found \\
    --title "Ge Zhichuan Moving to the Mountains" \\
    --artist "Wang Meng (Chinese, c. 1308-1385)" \\
    --date "c. 1360" --culture "China, Yuan dynasty (1271-1368)" \\
    --medium "Hanging scroll; ink and colour on paper" \\
    --holder "Palace Museum, Beijing"`;

const args = process.argv.slice(2);
if (args.includes('--help') || args.length === 0) { console.log(HELP); process.exit(0); }
const flag = (n, d) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : d; };

const url = flag('--url');
const file = flag('--file');
const out = flag('--out');
const explain = args.includes('--explain');
const force = args.includes('--force');

if (!url === !file) { console.error('need exactly one of --url or --file\n'); console.error(HELP); process.exit(2); }
if (!out) { console.error('--out is required\n'); console.error(HELP); process.exit(2); }

const META = {
  title: flag('--title', ''),
  artist: flag('--artist', ''),
  date: flag('--date', ''),
  culture: flag('--culture', ''),
  medium: flag('--medium', ''),
  holder: flag('--holder', ''),
  sourcePage: flag('--source-page', ''),
  rights: flag('--rights', ''),
  note: flag('--note', ''),
};

// Derived, not asked for: if you bothered to name the artist, that is an
// assertion. Only a rights string from a holder earns "verified", and this tool
// cannot check one — so it never derives it. Pass --provenance to override.
//
// Note which fields count. A --source-page is a LEAD, not an attribution: it
// says where the file was found, not who made it, and a button-press grab fills
// it in automatically. Letting it raise the tier would mark every drive-by grab
// "asserted" and the field would stop meaning anything. Same for --note.
const CLAIMS = ['title', 'artist', 'date', 'culture', 'medium', 'holder'];
const asserted = CLAIMS.some((k) => META[k]);
const provenance = flag('--provenance', asserted ? 'asserted' : 'unknown');
if (!['verified', 'asserted', 'unknown'].includes(provenance)) {
  console.error(`--provenance must be verified|asserted|unknown, got "${provenance}"`); process.exit(2);
}

// A browser User-Agent, and not as a courtesy. comuseum.com returns 403 to a
// custom agent and 200 to this one for the IDENTICAL image URL — measured
// 2026-08-13, after the first real Stream Deck press failed on exactly that.
// It is bot-blocking, not a licence gate. When a source page is known it also
// rides along as the Referer, which is what unlocks hotlink-protected CDNs.
const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36';
const headers = (referer) => ({
  'User-Agent': UA,
  Accept: 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
  ...(referer ? { Referer: referer } : {}),
});

// ─── what IS this file ──────────────────────────────────────────────────────
// Magic bytes, never the URL. A .png that is really a JPEG breaks every loader
// downstream in a way that reads as a model failure.
function sniff(buf) {
  if (buf.length < 12) return { format: 'unknown', ext: '.bin' };
  const a = buf.subarray(0, 12);
  if (a[0] === 0x89 && a[1] === 0x50 && a[2] === 0x4e && a[3] === 0x47) return { format: 'png', ext: '.png' };
  if (a[0] === 0xff && a[1] === 0xd8 && a[2] === 0xff) return { format: 'jpeg', ext: '.jpg' };
  if (a.toString('latin1', 0, 3) === 'GIF') return { format: 'gif', ext: '.gif' };
  if (a.toString('latin1', 0, 4) === 'RIFF' && a.toString('latin1', 8, 12) === 'WEBP') return { format: 'webp', ext: '.webp' };
  if (a.toString('latin1', 4, 8) === 'ftyp') {
    const brand = a.toString('latin1', 8, 12);
    if (brand.startsWith('avi')) return { format: 'avif', ext: '.avif' };
    if (brand.startsWith('hei') || brand.startsWith('mif')) return { format: 'heic', ext: '.heic' };
  }
  if (a[0] === 0x49 && a[1] === 0x49 && a[2] === 0x2a) return { format: 'tiff', ext: '.tif' };
  if (a[0] === 0x4d && a[1] === 0x4d && a[3] === 0x2a) return { format: 'tiff', ext: '.tif' };
  return { format: 'unknown', ext: '.bin' };
}

// Dimensions from the header. No ImageMagick, no sharp — one dependency for a
// number that is sitting in the first 32 bytes is a bad trade.
function imageSize(buf, format) {
  try {
    if (format === 'png') return { width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) };
    if (format === 'gif') return { width: buf.readUInt16LE(6), height: buf.readUInt16LE(8) };
    if (format === 'jpeg') {
      let i = 2;
      while (i < buf.length - 9) {
        if (buf[i] !== 0xff) { i++; continue; }
        const m = buf[i + 1];
        // SOF0-SOF15 carry the frame size; C4/C8/CC are tables, not frames.
        if (m >= 0xc0 && m <= 0xcf && ![0xc4, 0xc8, 0xcc].includes(m)) {
          return { height: buf.readUInt16BE(i + 5), width: buf.readUInt16BE(i + 7) };
        }
        i += 2 + buf.readUInt16BE(i + 2);
      }
      return { width: 0, height: 0 };
    }
    if (format === 'webp') {
      // RIFF container, three possible payloads. Ryan's first grab is one of
      // these, so getting all three right is not optional.
      const chunk = buf.toString('latin1', 12, 16);
      if (chunk === 'VP8X') {                       // extended: 24-bit canvas, minus one
        return { width: buf.readUIntLE(24, 3) + 1, height: buf.readUIntLE(27, 3) + 1 };
      }
      if (chunk === 'VP8 ') {                       // lossy: after the 9d 01 2a start code
        if (buf[23] === 0x9d && buf[24] === 0x01 && buf[25] === 0x2a) {
          return { width: buf.readUInt16LE(26) & 0x3fff, height: buf.readUInt16LE(28) & 0x3fff };
        }
      }
      if (chunk === 'VP8L') {                       // lossless: 14+14 bits packed after 0x2f
        const bits = buf.readUInt32LE(21);
        return { width: (bits & 0x3fff) + 1, height: ((bits >> 14) & 0x3fff) + 1 };
      }
    }
  } catch { /* a truncated header is a 0, not a crash */ }
  return { width: 0, height: 0 };                   // avif/heic/tiff: say nothing rather than lie
}

// \p{L}\p{N} and not \w. \w is [A-Za-z0-9_], so a CJK title was stripped to
// nothing and a percent-encoded CJK filename left its hex behind — a grab of
// 葛稚川移居圖.jpg landed as `e8919be7a89ae5b79de7a7bbe5b185e59c96.jpg`
// (2026-08-13). Chinese painting titles are the whole point of this library;
// they have to survive the filename.
const slug = (s) => String(s).toLowerCase()
  .replace(/[^\p{L}\p{N}\s-]+/gu, '').trim().replace(/[\s_]+/g, '-').replace(/-+/g, '-').slice(0, 70);

function stemFrom() {
  const explicit = flag('--name');
  if (explicit) return slug(explicit);
  if (META.artist && META.title) return `${slug(META.artist.split('(')[0])}_${slug(META.title)}`;
  if (META.title) return slug(META.title);
  // Percent-decode first, or %E8%91%9B… is what gets slugged.
  let base = url ? basename(new URL(url).pathname) : basename(file);
  try { base = decodeURIComponent(base); } catch { /* malformed escapes: use it raw */ }
  return slug(base.replace(extname(base), '')) || 'image';
}

if (explain) {
  console.log(JSON.stringify({
    tool: 'fetch-image', wouldFetch: url || file, out, stem: stemFrom(),
    provenance, ...META, spent: 'nothing',
  }, null, 2));
  process.exit(0);
}

// ─── get the bytes ──────────────────────────────────────────────────────────
let buf;
if (url) {
  process.stderr.write(`fetching ${url.slice(0, 100)}…\n`);
  // Five minutes, not two: a museum's full scan is the point of this tool and
  // they run to hundreds of megabytes (the Palace Museum's Wang Meng is 172MB).
  const res = await fetch(url, { headers: headers(META.sourcePage), redirect: 'follow', signal: AbortSignal.timeout(300000) });
  if (!res.ok) { console.error(`HTTP ${res.status} ${res.statusText}`); process.exit(1); }
  buf = Buffer.from(await res.arrayBuffer());
} else {
  if (!existsSync(file)) { console.error(`no such file: ${file}`); process.exit(1); }
  buf = readFileSync(file);
}
if (buf.length < 1024) { console.error(`suspiciously small (${buf.length}B) — probably an error page, not an image`); process.exit(1); }

const { format, ext } = sniff(buf);
if (format === 'unknown') { console.error(`not a recognised image (first bytes: ${buf.subarray(0, 8).toString('hex')})`); process.exit(1); }
const { width, height } = imageSize(buf, format);
const imageHash = createHash('sha256').update(buf).digest('hex');

mkdirSync(out, { recursive: true });

// Same bytes already here under any name? Say so and stop. Two names for one
// painting is how a reference set silently double-weights it.
for (const f of readdirSync(out).filter((f) => f.endsWith('.json'))) {
  try {
    const prior = JSON.parse(readFileSync(join(out, f), 'utf8'));
    if (prior.imageHash === imageHash) {
      console.error(`already in the library as ${prior.file}`);
      console.log(JSON.stringify({ tool: 'fetch-image', status: 'duplicate', imageHash, existing: prior.file, sidecar: join(out, f) }, null, 2));
      process.exit(0);
    }
  } catch { /* a sidecar we cannot parse is not a match */ }
}

const stem = stemFrom();
const imgPath = join(out, stem + ext);
const metaPath = join(out, stem + '.json');
if (existsSync(imgPath) && !force) {
  console.error(`${imgPath} exists (different bytes) — pass --force to overwrite or --name to rename`);
  process.exit(1);
}

const record = {
  source: url ? 'web' : 'local',
  provenance,
  ...META,
  sourceUrl: url || null,
  originalPath: file || null,
  imageHash,
  format,
  width,
  height,
  aspect: width && height ? +(width / height).toFixed(3) : null,
  bytes: buf.length,
  file: imgPath,
  fetchedAt: new Date().toISOString(),
  fetchedBy: 'media-tools/fetch-image',
};

writeFileSync(imgPath, buf);
writeFileSync(metaPath, JSON.stringify(record, null, 2));

process.stderr.write(`  ${format} ${width}x${height} ${(buf.length / 1e6).toFixed(2)}MB  provenance=${provenance}\n`);
if (provenance === 'unknown') {
  process.stderr.write('  WARNING: no attribution given. This image cannot be told apart from AI output later.\n');
}
console.log(JSON.stringify({ tool: 'fetch-image', status: 'written', ...record }, null, 2));
