// media-tools — fetch-artwork: pull open-access museum images + metadata. One job.
//
// It DOWNLOADS. It does not crop, caption, or filter for quality — those are
// separate tools, and conflating them is how a fetcher turns into a pipeline.
//
// Why museums and not the open web: we are building a training corpus, and the
// Chinese internet in 2026 is saturated with AI-generated ink wash. Scraping
// image search for 水墨画 feeds another model's output back into ours. Museum
// open-access collections are guaranteed human-made, high resolution, licensed
// CC0 or public domain, and carry real metadata (date, dynasty, artist,
// technique) that writes better captions than any auto-captioner.
//
// Every download writes a .json sidecar with the record and its rights string.
// Keep those: they are the provenance chain for anything trained on this.

import { writeFileSync, mkdirSync, existsSync, readFileSync } from 'node:fs';
import { join, extname } from 'node:path';
import { envKey } from './_env.mjs';

const HELP = `fetch-artwork — download open-access museum images + metadata sidecars

usage: node fetch-artwork.mjs --source S --out DIR [flags]

sources (no API key needed unless noted):
  cleveland     Cleveland Museum of Art — CC0, 561 Chinese paintings, 3400px JPEGs.
                The best single source: nearly all ink, clean scans, rich metadata.
  met           The Metropolitan Museum of Art via its live search API. Works,
                but the search returns bare IDs in no useful order, so reaching
                the Chinese material costs thousands of object calls and the Met
                starts returning 403. Prefer met-csv.
  met-csv       The Met's published collection dump — 423 Chinese public-domain
                ink-on-paper paintings, filtered locally with ZERO search calls,
                then one object call each to resolve the image URL. Titles are
                bilingual (中文|English), which writes better captions.
                  curl -L -o MetObjects.csv https://media.githubusercontent.com/\\
                    media/metmuseum/openaccess/master/MetObjects.csv
                then pass --csv MetObjects.csv
  aic           Art Institute of Chicago — IIIF. Small Chinese holding (~28).
  smithsonian   National Museum of Asian Art (Freer|Sackler) — needs a free key
                from api.data.gov as SMITHSONIAN_API_KEY in .env.

flags:
  --source S       (required) one of the above
  --out DIR        (required) where images and .json sidecars land
  --query TEXT     free-text search (source default is chosen for ink painting)
  --culture TEXT   keep only records whose culture/place mentions this (e.g. China)
  --medium REGEX   keep only records whose medium/technique matches (e.g. 'ink').
                   Museum "Painting" classifications include painted clamshells,
                   lacquer and mineral pigment on silk — filter or you will teach
                   the model things that are not ink wash.
  --max-per-series N  keep at most N leaves from any one album (default 5).
                   Museum albums run 50+ leaves by one hand; unchecked, a single
                   album became 22% of a 236-record pull and the LoRA would learn
                   that painter, not the medium. The album key is the ACCESSION
                   stem (1964.371.* = one album) — titles are unreliable because
                   every leaf of "Twelve Views of Tiger Hill" is titled
                   differently and a title-based cap leaked all 13.
  --max-per-artist N  keep at most N works by one hand (default 8). Matters more
                   than the album cap for a style corpus: the target is the
                   medium, and any single painter's mannerisms are noise.
  --max-aspect F   skip records wider/taller than this ratio (default 3.0).
                   Handscrolls run 6:1 and beyond; LTX preprocessing CENTER-CROPS
                   to the bucket, so a scroll becomes a random middle slice.
                   Scrolls are not junk — they need tiling, which is another tool.
                   Checked from the record when the source publishes dimensions,
                   otherwise from the downloaded file's own header.
  --csv PATH       met-csv only: path to MetObjects.csv
  --limit N        stop after N downloads (default 100)
  --min-width N    skip images narrower than this (default 1200 — training needs
                   at least the bucket width, and upscaling invents detail)
  --skip-existing  do not re-download files already in --out (default on)
  --explain        print the resolved query and the first page of records as
                   JSON, download NOTHING

Downloads are throttled and identify themselves. Sidecars carry the rights
string; if a record has no clear public-domain/CC0 marker it is SKIPPED.

example:
  node ~/projects/media-tools/tools/fetch-artwork.mjs \\
    --source cleveland --culture China --limit 400 --out corpus/inkwash/raw`;

const args = process.argv.slice(2);
if (args.includes('--help') || args.length === 0) { console.log(HELP); process.exit(0); }
const flag = (n, d) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : d; };

const source = flag('--source');
const out = flag('--out');
const explain = args.includes('--explain');
// --explain inspects the query without writing anything, so it needs no --out.
if (!source || (!out && !explain)) { console.error(HELP); process.exit(2); }
const limit = parseInt(flag('--limit', '100'), 10);
const minWidth = parseInt(flag('--min-width', '1200'), 10);
const culture = flag('--culture', '');
const medium = flag('--medium', '');
const maxAspect = parseFloat(flag('--max-aspect', '3.0'));
const maxPerSeries = parseInt(flag('--max-per-series', '5'), 10);
const maxPerArtist = parseInt(flag('--max-per-artist', '8'), 10);
// Prefer the accession stem an adapter supplies (1964.371.5 -> 1964.371); fall
// back to a title stem only when there is no accession structure to key on.
const seriesOf = (r) => (r.seriesKey
  || String(r.title || '').split(/\s*[:(]|,\s*Leaf/)[0].trim()).toLowerCase();
const artistOf = (r) => String(r.artist || '').split('(')[0].trim().toLowerCase();
const accStem = (acc) => String(acc || '').split('.').slice(0, 2).join('.');
const UA = { 'User-Agent': 'media-tools/0.1 (research corpus; contact via github.com/blessdog)' };

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Streaming RFC4180 CSV reader. The Met dump is 300MB with quoted fields that
// contain commas, newlines and doubled quotes — split(',') shreds it, and
// building every row up front exhausts the heap (485k rows x 54 columns OOMs
// node at its 4GB default). So: parse incrementally, yield one row at a time,
// and never hold more than the current chunk.
async function* streamCsv(path) {
  const { createReadStream } = await import('node:fs');
  let head = null, row = [], field = '', quoted = false;
  for await (const chunk of createReadStream(path, { encoding: 'utf8', highWaterMark: 1 << 20 })) {
    for (let i = 0; i < chunk.length; i++) {
      const c = chunk[i];
      if (quoted) {
        if (c !== '"') { field += c; continue; }
        // A doubled quote is a literal quote. It can straddle a chunk boundary,
        // so when we are at the very end, defer by staying in quoted state.
        if (i + 1 < chunk.length) {
          if (chunk[i + 1] === '"') { field += '"'; i++; } else quoted = false;
        } else quoted = false;
        continue;
      }
      if (c === '"') quoted = true;
      else if (c === ',') { row.push(field); field = ''; }
      else if (c === '\n') {
        row.push(field); field = '';
        if (!head) head = row;
        else yield Object.fromEntries(head.map((h, j) => [h, row[j] ?? '']));
        row = [];
      } else if (c !== '\r') field += c;
    }
  }
  if (head && (field || row.length)) {
    row.push(field);
    yield Object.fromEntries(head.map((h, j) => [h, row[j] ?? '']));
  }
}

// Pixel dimensions straight out of the file header — no ImageMagick dependency.
// Sources that publish dimensions let us skip a doomed download; sources that
// do not (the Met) get checked here instead.
function imageSize(buf) {
  if (buf[0] === 0x89 && buf[1] === 0x50) {                      // PNG
    return { width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) };
  }
  if (buf[0] === 0xff && buf[1] === 0xd8) {                      // JPEG: walk to SOFn
    let i = 2;
    while (i < buf.length - 9) {
      if (buf[i] !== 0xff) { i++; continue; }
      const marker = buf[i + 1];
      // SOF0-SOF15 carry the frame size; C4/C8/CC are tables, not frames.
      if (marker >= 0xc0 && marker <= 0xcf && ![0xc4, 0xc8, 0xcc].includes(marker)) {
        return { height: buf.readUInt16BE(i + 5), width: buf.readUInt16BE(i + 7) };
      }
      i += 2 + buf.readUInt16BE(i + 2);
    }
  }
  return { width: 0, height: 0 };
}
async function getJson(url) {
  const r = await fetch(url, { headers: UA, signal: AbortSignal.timeout(60000) });
  if (!r.ok) throw new Error(`${r.status} ${url.slice(0, 120)}`);
  return r.json();
}

// ─── source adapters ────────────────────────────────────────────────────────
// Each yields a NORMALIZED record. Nothing downstream may know which museum a
// record came from except by reading .source.

const SOURCES = {
  // Cleveland: one paged endpoint, images pre-derived at three sizes.
  cleveland: {
    defaultQuery: '',
    async *records({ query, limit }) {
      const page = 100;
      for (let skip = 0; skip < 5000; skip += page) {
        const u = 'https://openaccess-api.clevelandart.org/api/artworks/?' + new URLSearchParams({
          department: 'Chinese Art', type: 'Painting', has_image: '1', cc0: '1',
          ...(query ? { q: query } : {}), limit: String(page), skip: String(skip),
        });
        const d = await getJson(u);
        if (!d.data?.length) return;
        for (const a of d.data) {
          // Prefer `print` (~3400px JPEG). `full` is a 28MB TIFF we do not want,
          // `web` (~1100px) is below the training bucket.
          const img = a.images?.print || a.images?.web;
          if (!img?.url) continue;
          yield {
            source: 'cleveland', id: a.accession_number || String(a.id),
            seriesKey: accStem(a.accession_number),
            title: a.title, artist: (a.creators || []).map((c) => c.description).join('; '),
            date: a.creation_date, culture: [].concat(a.culture || []).join('; '),
            medium: a.technique, type: a.type,
            rights: a.share_license_status, pageUrl: a.url, imageUrl: img.url,
            width: parseInt(img.width, 10) || 0, height: parseInt(img.height, 10) || 0,
            inscriptions: (a.inscriptions || []).map((i) => i.inscription).join(' | ').slice(0, 500),
            description: (a.description || '').slice(0, 800),
          };
        }
        await sleep(250);
      }
    },
  },

  // The Met: search returns bare IDs, so every record costs a second request.
  // Individual IDs 404 sometimes; skip them rather than aborting the run.
  met: {
    defaultQuery: 'ink on paper',
    async *records({ query, limit }) {
      const u = 'https://collectionapi.metmuseum.org/public/collection/v1/search?' + new URLSearchParams({
        q: query, hasImages: 'true', medium: 'Paintings', departmentId: '6',
      });
      const ids = (await getJson(u)).objectIDs || [];
      let seen = 0;
      for (const oid of ids) {
        if (seen >= limit * 4) return;   // generous headroom for the PD/culture filters
        seen++;
        let o;
        try { o = await getJson(`https://collectionapi.metmuseum.org/public/collection/v1/objects/${oid}`); }
        catch { await sleep(120); continue; }
        await sleep(120);
        if (!o.isPublicDomain || !o.primaryImage) continue;
        yield {
          source: 'met', id: String(o.objectID),
          seriesKey: accStem(o.accessionNumber),
          title: o.title, artist: o.artistDisplayName, date: o.objectDate,
          culture: [o.culture, o.country, o.dynasty, o.period].filter(Boolean).join('; '),
          medium: o.medium, type: o.classification,
          rights: o.isPublicDomain ? 'Public Domain (CC0)' : o.rightsAndReproduction,
          pageUrl: o.objectURL, imageUrl: o.primaryImage,
          width: 0, height: 0,   // Met does not publish dimensions in the API
          inscriptions: '', description: (o.creditLine || '').slice(0, 300),
        };
      }
    },
  },

  // The Met, offline-first: filter the published dump locally, then spend one
  // object call per KEEPER to resolve its image URL. Same museum as `met`, two
  // orders of magnitude fewer requests, and no 403.
  'met-csv': {
    defaultQuery: '',
    async *records({ limit }) {
      const csvPath = flag('--csv');
      if (!csvPath) throw new Error('met-csv needs --csv path/to/MetObjects.csv (see --help)');
      const col = (r, k) => r[k] || '';
      for await (const r of streamCsv(csvPath)) {
        if (col(r, 'Is Public Domain') !== 'True') continue;
        const cult = `${col(r, 'Culture')} ${col(r, 'Country')}`;
        const med = col(r, 'Medium');
        const cls = `${col(r, 'Classification')} ${col(r, 'Object Name')}`;
        if (!/china/i.test(cult)) continue;
        if (!/painting/i.test(cls)) continue;
        // Gold- and alum-sized fan papers are not the white xuan ground we are
        // after; they read as metallic and would teach the model a gold field.
        if (/gold|alum/i.test(med)) continue;
        // Titles are "中文|English" — keep both, the Chinese half is real signal.
        const title = col(r, 'Title');
        yield {
          source: 'met', id: col(r, 'Object ID'),
          seriesKey: accStem(col(r, 'Accession Number')),
          title, artist: col(r, 'Artist Display Name'), date: col(r, 'Object Date'),
          culture: cult.trim(), medium: med, type: col(r, 'Classification'),
          rights: 'Public Domain (CC0)',
          pageUrl: `https://www.metmuseum.org/art/collection/search/${col(r, 'Object ID')}`,
          imageUrl: null,          // resolved lazily below, only for keepers
          resolveImage: true,
          width: 0, height: 0, inscriptions: '', description: col(r, 'Credit Line').slice(0, 300),
        };
      }
    },
  },

  // Art Institute: Elasticsearch-flavoured POST, IIIF image server.
  aic: {
    defaultQuery: 'ink',
    async *records({ query, limit }) {
      const body = {
        q: query,
        query: { bool: { must: [
          { term: { is_public_domain: true } },
          { match: { classification_title: 'painting' } },
          ...(culture ? [{ match: { place_of_origin: culture } }] : []),
        ] } },
        fields: 'id,title,artist_display,date_display,medium_display,place_of_origin,image_id,classification_title',
        limit: Math.min(100, limit * 2),
      };
      const r = await fetch('https://api.artic.edu/api/v1/artworks/search', {
        method: 'POST', headers: { ...UA, 'Content-Type': 'application/json' },
        body: JSON.stringify(body), signal: AbortSignal.timeout(60000),
      });
      const d = await r.json();
      for (const a of d.data || []) {
        if (!a.image_id) continue;
        yield {
          source: 'aic', id: String(a.id),
          title: a.title, artist: a.artist_display, date: a.date_display,
          culture: a.place_of_origin, medium: a.medium_display, type: a.classification_title,
          rights: 'Public Domain (CC0)',
          pageUrl: `https://www.artic.edu/artworks/${a.id}`,
          // IIIF: ask for 3000px on the long edge; the server downsizes if smaller.
          imageUrl: `https://www.artic.edu/iiif/2/${a.image_id}/full/3000,/0/default.jpg`,
          width: 3000, height: 0, inscriptions: '', description: '',
        };
      }
    },
  },

  // Smithsonian NMAA (Freer|Sackler) — one of the great Chinese painting
  // collections, fully open access. Free key: https://api.data.gov/signup/
  smithsonian: {
    defaultQuery: 'ink on paper',
    async *records({ query, limit }) {
      const key = envKey('SMITHSONIAN_API_KEY');
      const page = 100;
      for (let start = 0; start < 2000; start += page) {
        const u = 'https://api.si.edu/openaccess/api/v1.0/search?' + new URLSearchParams({
          q: `${query} AND unit_code:FSG AND online_media_type:"Images"`,
          rows: String(page), start: String(start), api_key: key,
        });
        const d = await getJson(u);
        const rows = d?.response?.rows || [];
        if (!rows.length) return;
        for (const a of rows) {
          const c = a.content || {};
          const nr = c.descriptiveNonRepeating || {};
          const media = nr.online_media?.media?.[0];
          if (!media?.resources && !media?.content) continue;
          const big = (media.resources || []).find((r) => /screen|hi|large/i.test(r.label || ''));
          const free = c.indexedStructured?.usage_flag || [];
          if (!free.some((f) => /CC0/i.test(f))) continue;
          yield {
            source: 'smithsonian', id: a.id,
            title: a.title,
            artist: (c.freetext?.name || []).map((n) => n.content).join('; '),
            date: (c.freetext?.date || []).map((n) => n.content).join('; '),
            culture: (c.indexedStructured?.place || []).join('; '),
            medium: (c.freetext?.physicalDescription || []).map((n) => n.content).join('; '),
            type: (c.indexedStructured?.object_type || []).join('; '),
            rights: 'CC0', pageUrl: nr.record_link,
            imageUrl: big?.url || media.content,
            width: 0, height: 0, inscriptions: '', description: '',
          };
        }
        await sleep(300);
      }
    },
  },
};

const adapter = SOURCES[source];
if (!adapter) { console.error(`unknown --source '${source}' (known: ${Object.keys(SOURCES).join(', ')})`); process.exit(2); }
const query = flag('--query', adapter.defaultQuery);

// A record with no clear open licence never gets downloaded, whatever the source says.
const isOpen = (r) => /CC0|public domain|no copyright/i.test(r.rights || '');

console.error(`fetch-artwork: ${source} · query "${query}"${culture ? ` · culture~"${culture}"` : ''} · limit ${limit} · min-width ${minWidth}`);

let kept = 0;
const skipped = { rights: 0, small: 0, culture: 0, medium: 0, aspect: 0, series: 0, artist: 0, existing: 0, failed: 0 };
const scrolls = [];   // recorded, not discarded — these are the tiling backlog
const seriesCount = new Map();
const artistCount = new Map();

// The single selection gate. --explain and the real run MUST share it, or the
// dry run shows records the real run would have thrown away — which is worse
// than no dry run at all.
function reject(r) {
  if (!isOpen(r)) return 'rights';
  if (culture && !new RegExp(culture, 'i').test(`${r.culture} ${r.title}`)) return 'culture';
  if (medium && !new RegExp(medium, 'i').test(`${r.medium} ${r.type}`)) return 'medium';
  if ((seriesCount.get(seriesOf(r)) || 0) >= maxPerSeries) return 'series';
  // Anonymous works share the empty artist key; never cap them as one hand.
  const artist = artistOf(r);
  if (artist && (artistCount.get(artist) || 0) >= maxPerArtist) return 'artist';
  if (r.width && r.height) {
    const aspect = Math.max(r.width / r.height, r.height / r.width);
    if (aspect > maxAspect) return 'aspect';
  }
  if (r.width && r.width < minWidth) return 'small';
  return null;
}

if (explain) {
  const sample = [];
  for await (const r of adapter.records({ query, limit })) {
    const why = reject(r);
    if (why) { skipped[why]++; continue; }
    // Count as if kept, so the caps behave exactly as they would in a real run.
    seriesCount.set(seriesOf(r), (seriesCount.get(seriesOf(r)) || 0) + 1);
    const a = artistOf(r); if (a) artistCount.set(a, (artistCount.get(a) || 0) + 1);
    if (sample.length < 10) sample.push(r);
    if (++kept >= limit) break;
  }
  console.log(JSON.stringify({ tool: 'fetch-artwork', source, query, culture, medium,
    maxPerSeries, maxPerArtist, maxAspect, minWidth, limit, out,
    wouldDownload: kept, skipped, spent: 'nothing', sample }, null, 2));
  process.exit(0);
}

mkdirSync(out, { recursive: true });

for await (const r of adapter.records({ query, limit })) {
  if (kept >= limit) break;
  const why = reject(r);
  if (why) {
    skipped[why]++;
    if (why === 'aspect') scrolls.push({ id: r.id, title: r.title, imageUrl: r.imageUrl });
    continue;
  }
  const s = seriesOf(r);
  const artist = artistOf(r);

  // Sources that publish no image URL (met-csv) pay one object call HERE, after
  // every cheap filter has already had its say. Resolving before the caps would
  // spend a request on records we were always going to drop.
  if (r.resolveImage && !r.imageUrl) {
    try {
      const o = await getJson(`https://collectionapi.metmuseum.org/public/collection/v1/objects/${r.id}`);
      r.imageUrl = o.primaryImage || '';
      r.inscriptions = (o.dimensions || '').slice(0, 200);
    } catch { skipped.failed++; await sleep(400); continue; }
    await sleep(400);
    if (!r.imageUrl) { skipped.failed++; continue; }
  }

  const stem = `${r.source}-${String(r.id).replace(/[^\w.-]+/g, '_')}`;
  const ext = (extname(new URL(r.imageUrl).pathname) || '.jpg').split('?')[0] || '.jpg';
  const imgPath = join(out, stem + ext);
  const metaPath = join(out, stem + '.json');
  if (existsSync(imgPath)) { skipped.existing++; kept++; continue; }

  try {
    const res = await fetch(r.imageUrl, { headers: UA, signal: AbortSignal.timeout(120000) });
    if (!res.ok) throw new Error(`image ${res.status}`);
    const buf = Buffer.from(await res.arrayBuffer());
    if (buf.length < 20000) throw new Error(`suspiciously small (${buf.length}B)`);
    // Re-apply the shape checks against the file itself. The Met publishes no
    // dimensions, so this is the only place a 12:1 handscroll gets caught.
    const dim = imageSize(buf);
    if (dim.width && dim.height) {
      const aspect = Math.max(dim.width / dim.height, dim.height / dim.width);
      if (aspect > maxAspect) {
        skipped.aspect++;
        scrolls.push({ id: r.id, title: r.title, aspect: +aspect.toFixed(1), imageUrl: r.imageUrl });
        await sleep(200);
        continue;
      }
      if (dim.width < minWidth) { skipped.small++; await sleep(200); continue; }
      r.width = dim.width; r.height = dim.height;
    }
    writeFileSync(imgPath, buf);
    writeFileSync(metaPath, JSON.stringify({ ...r, series: s, bytes: buf.length, file: imgPath,
      fetchedBy: 'media-tools/fetch-artwork' }, null, 2));
    kept++;
    seriesCount.set(s, (seriesCount.get(s) || 0) + 1);
    if (artist) artistCount.set(artist, (artistCount.get(artist) || 0) + 1);
    process.stderr.write(`\r  ${kept}/${limit}  ${r.title.slice(0, 50).padEnd(50)}`);
  } catch (e) {
    skipped.failed++;
    console.error(`\n  skip ${stem}: ${e.message}`);
  }
  await sleep(200);
}

process.stderr.write('\n');
// Scrolls are deferred work, not rejects. Write the list so tiling has a worklist.
if (scrolls.length) {
  writeFileSync(join(out, `_scrolls-${source}.json`), JSON.stringify(scrolls, null, 2));
  console.error(`  ${scrolls.length} scrolls set aside (aspect > ${maxAspect}) → ${join(out, `_scrolls-${source}.json`)}`);
}
console.log(JSON.stringify({ tool: 'fetch-artwork', source, query, culture, medium, maxAspect,
  out, downloaded: kept, skipped, scrollsDeferred: scrolls.length }, null, 2));
