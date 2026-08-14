// media-tools — find-page-image: a web page → the images in it, ranked. One job.
//
// It DOWNLOADS NOTHING. It reads the HTML, works out which images are actual
// artworks rather than logos and spacers, pulls whatever caption the page hangs
// on them, and prints candidates as JSON. fetch-image does the downloading.
//
// Why this exists (2026-08-13): the Stream Deck GRAB key was pressed while
// standing on a gallery page, and fetch-image dutifully tried to download the
// PAGE as an image. Standing on a page and wanting the picture in it is the
// normal case, not the edge case — the front browser tab is a page almost every
// time.
//
// THE FRAGMENT IS THE STRONGEST SIGNAL and it is free. A URL ending
// `#liu-haisu_clouds-in-the-yellow-mountains` is the page telling you which of
// its forty images you are looking at, because that slug is also the image's
// own filename stem. When a fragment matches, there is nothing to choose.
//
// Full-size over thumbnail, always. WordPress galleries serve
// `name-300x580.jpg` in the <img> and link `name.jpg` from the wrapping <a>.
// Taking the <img> src gets you a 300px thumbnail of a painting; taking the
// anchor gets you the scan. Anything matching -WxH before the extension is
// treated as a derivative of its unsuffixed original.

const HELP = `find-page-image — a web page → the images in it, ranked. Downloads nothing.

usage: node find-page-image.mjs --url PAGE_URL [flags]

  --url URL        the page. A #fragment is used as a strong hint.
  --fragment S     override the fragment hint
  --limit N        most candidates to return (default 40)
  --min-px N       drop images whose DECLARED width or height is under this
                   (default 200; images with no declared size are kept)
  --all            do not drop anything; return every image found

Output on stdout:
  { page, pageTitle, fragment, count, candidates: [
      { url, thumb, alt, caption, width, height, score, why } ] }

Ranked best-first. A fragment match scores far above everything else; after
that it is og:image, then anchor-linked full sizes, then plain <img>.

example:
  node ~/projects/media-tools/tools/find-page-image.mjs \\
    --url 'https://www.comuseum.com/painting/landscape-painting/#liu-haisu_clouds-in-the-yellow-mountains'`;

const args = process.argv.slice(2);
if (args.includes('--help') || args.length === 0) { console.log(HELP); process.exit(0); }
const flag = (n, d) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : d; };

const pageUrl = flag('--url');
if (!pageUrl) { console.error(HELP); process.exit(2); }
const limit = parseInt(flag('--limit', '40'), 10);
const minPx = args.includes('--all') ? 0 : parseInt(flag('--min-px', '200'), 10);

// Sites block unknown agents outright — comuseum.com returns 403 to a custom UA
// and 200 to a browser one, for the identical URL. Measured 2026-08-13. This is
// bot-blocking, not a licence check, and reading a public page in a browser is
// what a person does anyway.
const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36';

const IMG_RE = /\.(png|jpe?g|webp|gif|avif|tiff?)(\?[^"'\s]*)?$/i;
// Logos, icons, avatars, tracking pixels, spacers, sprites — never the artwork.
const JUNK_RE = /(logo|icon|favicon|sprite|avatar|spacer|placeholder|pixel|button|badge|banner|thumb(nail)?s?\/|\/emoji\/|1x1|blank)/i;
// WordPress and friends: name-300x580.jpg is a derivative of name.jpg.
const SIZE_SUFFIX = /-(\d{2,5})x(\d{2,5})(?=\.[a-z]{3,4}(\?|$))/i;

let page;
try { page = new URL(pageUrl); } catch { console.error(`not a URL: ${pageUrl}`); process.exit(2); }
const fragment = (flag('--fragment') ?? decodeURIComponent(page.hash.replace(/^#/, ''))).trim();

const res = await fetch(page.href, {
  headers: { 'User-Agent': UA, Accept: 'text/html,application/xhtml+xml' },
  redirect: 'follow', signal: AbortSignal.timeout(30000),
});
if (!res.ok) { console.error(`HTTP ${res.status} ${res.statusText}`); process.exit(1); }
const ct = (res.headers.get('content-type') || '').toLowerCase();
if (!ct.includes('html')) { console.error(`not an HTML page (Content-Type: ${ct || 'none'})`); process.exit(1); }
const html = await res.text();

const abs = (u) => { try { return new URL(u, res.url).href; } catch { return null; } };
const unsuffixed = (u) => u.replace(SIZE_SUFFIX, '');
const decode = (s) => String(s || '')
  .replace(/&#(\d+);/g, (_, d) => String.fromCharCode(+d))
  .replace(/&(amp|lt|gt|quot|#39|apos|nbsp);/g, (_, e) =>
    ({ amp: '&', lt: '<', gt: '>', quot: '"', '#39': "'", apos: "'", nbsp: ' ' }[e]))
  .replace(/\s+/g, ' ').trim();

const pageTitle = decode((html.match(/<title[^>]*>([\s\S]*?)<\/title>/i) || [])[1] || '');

// url -> candidate. Keyed on the FULL-SIZE url so a thumbnail and the original
// it derives from collapse into one entry rather than competing.
const found = new Map();
const add = (url, patch) => {
  if (!url) return;
  const key = unsuffixed(url);
  const prev = found.get(key) || { url: key, thumb: null, alt: '', caption: '', width: 0, height: 0, score: 0, why: [] };
  found.set(key, {
    ...prev, ...Object.fromEntries(Object.entries(patch).filter(([, v]) => v !== null && v !== '' && v !== 0)),
    why: [...new Set([...prev.why, ...(patch.why || [])])],
    score: Math.max(prev.score, patch.score || 0),
  });
};

// 1. og:image / twitter:image — the page's own nomination for what it is about.
for (const m of html.matchAll(/<meta[^>]+(?:property|name)=["'](?:og:image(?::secure_url)?|twitter:image)["'][^>]*>/gi)) {
  const c = (m[0].match(/content=["']([^"']+)["']/i) || [])[1];
  const u = abs(c);
  if (u && IMG_RE.test(u)) add(u, { score: 60, why: ['og:image'] });
}

// 2. Anchors that point straight at an image file. In a gallery this is the
//    full-size scan and the <img> inside it is the thumbnail — so parse the
//    whole <a>…</a> together and keep both, with the anchor as the real url.
for (const m of html.matchAll(/<a\b[^>]*href=["']([^"']+)["'][^>]*>([\s\S]{0,1200}?)<\/a>/gi)) {
  const href = abs(m[1]);
  if (!href || !IMG_RE.test(href)) continue;
  const inner = m[2];
  const img = inner.match(/<img\b[^>]*>/i);
  const attr = (tag, name) => (tag.match(new RegExp(`${name}=["']([^"']*)["']`, 'i')) || [])[1] || '';
  add(href, {
    score: 40,
    why: ['linked full size'],
    thumb: img ? abs(attr(img[0], 'src')) : null,
    alt: img ? decode(attr(img[0], 'alt')) : '',
    width: img ? parseInt(attr(img[0], 'width'), 10) || 0 : 0,
    height: img ? parseInt(attr(img[0], 'height'), 10) || 0 : 0,
  });
}

// 3. Every remaining <img>. Lazy-loaded galleries hide the real src in
//    data-src / data-lazy-src, so a plain src read finds a placeholder.
for (const m of html.matchAll(/<img\b[^>]*>/gi)) {
  const tag = m[0];
  const attr = (name) => (tag.match(new RegExp(`${name}=["']([^"']*)["']`, 'i')) || [])[1] || '';
  const src = attr('data-src') || attr('data-lazy-src') || attr('data-original') || attr('src');
  const u = abs(src);
  if (!u || !IMG_RE.test(u)) continue;
  add(u, {
    score: 20, why: ['<img>'],
    alt: decode(attr('alt')),
    width: parseInt(attr('width'), 10) || 0,
    height: parseInt(attr('height'), 10) || 0,
  });
}

// 4. Captions. Themify/WordPress hang the work's name in a sibling div rather
//    than in alt, and it is often the only place the artist appears.
for (const m of html.matchAll(/class=["'][^"']*image-caption[^"']*["'][^>]*>([\s\S]{0,300}?)<\/div>/gi)) {
  const text = decode(m[1].replace(/<[^>]+>/g, ' '));
  if (!text) continue;
  // Attach to the nearest preceding candidate in document order.
  const at = m.index;
  let best = null, bestAt = -1;
  for (const c of found.values()) {
    const i = Math.max(html.lastIndexOf(c.url, at), html.lastIndexOf(unsuffixed(c.url), at));
    if (i > bestAt && i < at && at - i < 2000) { bestAt = i; best = c; }
  }
  if (best) best.caption = text;
}

let candidates = [...found.values()].filter((c) => !JUNK_RE.test(c.url));
if (minPx) candidates = candidates.filter((c) => !(c.width && c.height) || (c.width >= minPx || c.height >= minPx));

// The fragment hint, applied last so it outranks every structural signal.
if (fragment) {
  const norm = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, '');
  const f = norm(fragment);
  for (const c of candidates) {
    const stem = norm(decodeURIComponent(c.url.split('/').pop().replace(/\.[a-z]{3,4}(\?.*)?$/i, '')));
    if (!f || !stem) continue;
    if (stem === f) { c.score += 1000; c.why.push('fragment exact'); }
    else if (stem.includes(f) || f.includes(stem)) { c.score += 500; c.why.push('fragment match'); }
  }
}

// Declared pixels break ties: a bigger picture on the same page is the subject,
// the smaller ones are related links down the sidebar.
for (const c of candidates) c.score += Math.min(15, Math.round(Math.max(c.width, c.height) / 100));

candidates.sort((a, b) => b.score - a.score);
candidates = candidates.slice(0, limit).map((c) => ({ ...c, why: c.why.join(' + ') }));

console.log(JSON.stringify({
  page: res.url, pageTitle, fragment: fragment || null,
  count: candidates.length, candidates,
}, null, 2));
