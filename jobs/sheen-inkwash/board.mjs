// renders/*.png + their sidecars → one HTML page showing INPUTS beside OUTPUTS.
// A picture on its own is not reviewable: you cannot tell whether a frame is
// wrong because of the prompt, the seed, or the settings. This puts every input
// that produced each frame next to the frame.
//
// usage: node board.mjs > board.html
import { readdirSync, readFileSync, existsSync } from 'node:fs';

const esc = (s) => String(s).replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
const pngs = readdirSync('renders').filter((f) => /^shot-\d+\.png$/.test(f)).sort();

const rows = pngs.map((f) => {
  const mPath = `renders/${f}.json`;
  if (!existsSync(mPath)) return `<section><h2>${f}</h2><img src="renders/${f}"><p class="warn">NO MANIFEST — inputs unknown</p></section>`;
  const m = JSON.parse(readFileSync(mPath, 'utf8'));
  const s = m.sampler || {}, mo = m.model || {}, fr = m.frame || {}, ch = m.channels || {};
  return `<section>
  <h2>${f} ${m.reconstructed ? '<span class="warn">reconstructed manifest</span>' : ''}</h2>
  <div class="pair">
    <img src="renders/${f}">
    <div class="inputs">
      <table>
        <tr><th>renderer</th><td>${esc(m.renderer)} via ${esc(m.provider)}</td></tr>
        <tr><th>checkpoint</th><td>${esc(mo.checkpoint)}</td></tr>
        <tr><th>style lora</th><td>${esc(mo.lora)} @ <b>${esc(mo.loraStrength)}</b></td></tr>
        <tr><th>model patch</th><td>${esc(mo.modelPatch)}</td></tr>
        <tr><th>clip vision</th><td>${esc(mo.clipVision)}</td></tr>
        <tr><th>seed</th><td><b>${esc(s.seed)}</b></td></tr>
        <tr><th>steps / guidance</th><td>${esc(s.steps)} / ${esc(s.guidance)}</td></tr>
        <tr><th>sampler</th><td>${esc(s.sampler)} · ${esc(s.scheduler)} · cfg ${esc(s.cfg)} · denoise ${esc(s.denoise)}</td></tr>
        <tr><th>frame</th><td>${esc(fr.width)}x${esc(fr.height)}</td></tr>
        <tr><th>STYLE channel</th><td>${esc((ch.style?.file || '').split('/').pop())}<br><code>sha ${esc(ch.style?.sha256)}</code></td></tr>
        <tr><th>IDENTITY channel</th><td>${ch.identity ? esc(ch.identity.file) : '<span class="warn">none — generic face</span>'}</td></tr>
        <tr><th>from</th><td>${esc(m.source?.shotScript || '—')} → ${esc(m.source?.filteredBy || '—')}</td></tr>
      </table>
      <h3>SCENE channel — the text actually sent</h3>
      <p class="prompt"><span class="pre">${esc(ch.scene?.stylePrefix || '')}</span> ${esc(ch.scene?.yourPrompt || ch.scene?.text || '')}</p>
    </div>
  </div>
</section>`;
}).join('\n');

console.log(`<!doctype html><meta charset="utf-8"><title>sheen-inkwash — inputs &amp; outputs</title>
<style>
 body{background:#141414;color:#ddd;font:14px/1.5 -apple-system,sans-serif;margin:0;padding:24px}
 h1{font-size:20px;margin:0 0 4px} .sub{color:#888;margin:0 0 24px}
 section{border-top:1px solid #333;padding:20px 0}
 h2{font-size:15px;margin:0 0 12px;color:#fff}
 .pair{display:flex;gap:20px;align-items:flex-start;flex-wrap:wrap}
 img{width:min(560px,48vw);border:1px solid #333}
 .inputs{flex:1;min-width:340px}
 table{border-collapse:collapse;width:100%} th,td{text-align:left;padding:3px 8px;vertical-align:top;border-bottom:1px solid #262626}
 th{color:#888;font-weight:400;white-space:nowrap;width:130px}
 h3{font-size:12px;color:#888;margin:14px 0 4px;font-weight:400;text-transform:uppercase;letter-spacing:.05em}
 .prompt{background:#1c1c1c;padding:10px;border-left:2px solid #444;margin:0}
 .pre{color:#7aa}
 code{color:#888;font-size:11px}
 .warn{color:#e08}
</style>
<h1>sheen-inkwash — every input beside its output</h1>
<p class="sub">Generated from renders/*.png.json. Nothing here is retyped by hand except where marked reconstructed.</p>
${rows}`);
