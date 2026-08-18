// The bake-off, side by side. One source, one swatch, six models.
// usage: node board.mjs && open board.html
import { readdirSync, existsSync, readFileSync, writeFileSync } from 'node:fs';

const FIRST = ['source.png'];
const BASELINE = { file: 'baseline-text-only.png', note: 'flux-2-dev, style as TEXT only — the first attempt, no swatch' };

const pngs = readdirSync('.').filter(f => f.endsWith('.png') && !FIRST.includes(f) && f !== BASELINE.file).sort();
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

const card = (f, note) => {
  const m = existsSync(`${f}.json`) ? JSON.parse(readFileSync(`${f}.json`, 'utf8')) : null;
  const mb = existsSync(f) ? (readFileSync(f).length / 1e6).toFixed(1) : '?';
  return `<figure>
    <a href="${esc(f)}" target="_blank"><img loading="lazy" src="${esc(f)}"></a>
    <figcaption>
      <b>${esc(m?.model || f.replace(/\.png$/, ''))}</b>
      ${note ? `<span class="note">${esc(note)}</span>` : ''}
      <span class="meta">style channel: <i class="${m?.styleChannel === 'image' ? 'img' : 'txt'}">${esc(m?.styleChannel || '—')}</i> · ${mb} MB</span>
    </figcaption>
  </figure>`;
};

writeFileSync('board.html', `<!doctype html><meta charset="utf-8">
<title>ryan portrait — model bake-off</title>
<style>
 :root{color-scheme:dark}
 body{background:#131313;color:#e9e5dd;font:14px/1.5 -apple-system,system-ui,sans-serif;margin:0;padding:26px 30px 120px}
 h1{font-size:22px;margin:0 0 6px}
 .lede{color:#9b958b;max-width:76ch;margin:0 0 26px}
 h2{font-size:13px;font-weight:600;color:#c9b98a;border-bottom:1px solid #2b2b2b;padding-bottom:6px;margin:36px 0 16px}
 .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(400px,1fr));gap:20px}
 figure{margin:0;background:#1b1b1b;border:1px solid #2b2b2b;border-radius:5px;overflow:hidden}
 img{width:100%;display:block;background:#0c0c0c}
 figcaption{padding:9px 11px 11px}
 figcaption b{color:#e6dcbc;font-size:12.5px}
 .note{display:block;color:#9b958b;font-size:11px;margin-top:2px}
 .meta{display:block;color:#7d776f;font-size:11px;margin-top:4px}
 i{font-style:normal}.img{color:#7fae8a}.txt{color:#c98a8a}
</style>
<h1>ryan portrait — one photo, six models, the same LOCKED swatch</h1>
<p class="lede">Every render below got the identical instruction and the identical style reference image.
The only variable is the model. <i class="img">image</i> = the medium arrived as a picture (the USO mechanism);
<i class="txt">text</i> = it arrived as adjectives. Click any frame for full resolution.</p>

<h2>inputs</h2><div class="grid">
${card('source.png', 'the photograph — frame 1s of IMG_0310.MOV')}
${card('../../styles/inkwash/reference/LOCKED-inkwash-texture-1.png', 'the LOCKED swatch — style channel, locked 2026-06-09')}
${existsSync(BASELINE.file) ? card(BASELINE.file, BASELINE.note) : ''}
</div>

<h2>candidates</h2><div class="grid">
${pngs.map(f => card(f)).join('\n')}
</div>`);

console.log(`${pngs.length} candidates → board.html`);
