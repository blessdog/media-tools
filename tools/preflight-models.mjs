// media-tools — preflight-models: can we actually DOWNLOAD what a box will need?
// One job. Rents nothing, downloads nothing, costs nothing.
//
// Why this exists, in one sentence: on 2026-08-12 I rented a $2.60/hr H100 to
// run LTX 2.5 and only THEN discovered the repo is gated — every file 403s
// until a human clicks "Agree" on the model page. $1.80 and forty minutes to
// learn something a free HEAD request would have said instantly.
//
// The rule: VERIFY YOU CAN OBTAIN THE INPUTS BEFORE YOU RENT THE COMPUTE.
//
// A HuggingFace repo can fail in ways that look identical from a distance:
//   gated: "auto"    — accept the terms once, instant, but ONLY the account
//                      owner can click it
//   gated: "manual"  — a human at the org has to approve; can take days
//   private / 404    — wrong path or no access at all
//   token missing    — reads fine in a browser, 401/403 from a script
// All of them mean the same thing operationally: do not rent yet.

import { readFileSync } from 'node:fs';
import { envKey } from './_env.mjs';

const HELP = `preflight-models — prove every model URL is fetchable BEFORE renting a box

usage: node preflight-models.mjs [--file PATH | --url URL ...] [--json]

  --url URL        check one or more literal URLs (repeatable)
  --repo R         a HuggingFace repo (repeatable). Alone, reports its gate
                   status; combined with --path, fetches from it.
  --path P         a file path inside the preceding --repo (repeatable)
  --file PATH      a provisioning script; literal huggingface.co/.../resolve/
                   URLs are extracted. URLs assembled from shell variables
                   CANNOT be extracted — pass those as --repo/--path instead.
  --json           machine-readable output

Exit 0 = everything is fetchable, safe to rent.
Exit 3 = something is gated/missing. The report names the exact page to click.

example:
  node ~/projects/media-tools/tools/preflight-models.mjs \\
    --file ~/projects/media-tools/tools/provision/pull-ltx25.sh`;

const args = process.argv.slice(2);
if (args.includes('--help') || args.length === 0) { console.log(HELP); process.exit(0); }
const many = (n) => args.reduce((a, v, i) => (v === n ? [...a, args[i + 1]] : a), []);
const asJson = args.includes('--json');

let token = null;
try { token = envKey('HF_TOKEN'); } catch { /* checked below, per-URL */ }
const hdr = token ? { Authorization: `Bearer ${token}` } : {};

const urls = [...many('--url')];
for (const f of many('--file')) {
  const text = readFileSync(f, 'utf8');
  for (const m of text.matchAll(/https:\/\/huggingface\.co\/[^\s"'`)]+?\/resolve\/[^\s"'`)]+/g)) {
    // A URL still holding ${VAR} was assembled at runtime and cannot be
    // resolved here. Blanking the variable produced a bogus URL that then
    // 404'd and reported a FALSE blocker — worse than reporting nothing.
    if (!m[0].includes('${')) urls.push(m[0]);
  }
}
const explicitRepos = many('--repo');
for (const p of many('--path')) {
  const repo = explicitRepos[explicitRepos.length - 1];
  if (repo) urls.push(`https://huggingface.co/${repo}/resolve/main/${p.replace(/^\//, '')}`);
}
const repos = [...explicitRepos,
  ...urls.map((u) => (u.match(/huggingface\.co\/([^/]+\/[^/]+)\/resolve/) || [])[1]).filter(Boolean)];

// Gate status is the DIAGNOSIS; the range request is the PROOF. Report both,
// because "gated: auto" plus a working fetch means the terms were already
// accepted and there is nothing to do.
async function repoInfo(repo) {
  try {
    const r = await fetch(`https://huggingface.co/api/models/${repo}`, { headers: hdr, signal: AbortSignal.timeout(30000) });
    if (!r.ok) return { repo, status: r.status, gated: null, error: `repo query ${r.status}` };
    const j = await r.json();
    return { repo, gated: j.gated ?? false, private: Boolean(j.private), downloads: j.downloads ?? null };
  } catch (e) { return { repo, error: e.message }; }
}

// One kilobyte, not one file. Enough to prove authorisation without traffic.
async function probe(url) {
  try {
    const r = await fetch(url, { headers: { ...hdr, Range: 'bytes=0-1023' }, redirect: 'follow', signal: AbortSignal.timeout(45000) });
    return { url, status: r.status, ok: r.status === 200 || r.status === 206 };
  } catch (e) { return { url, status: 0, ok: false, error: e.message }; }
}

const repoResults = await Promise.all([...new Set(repos)].map(repoInfo));
const urlResults = await Promise.all([...new Set(urls)].map(probe));
const blocked = urlResults.filter((r) => !r.ok);

if (asJson) {
  console.log(JSON.stringify({ tool: 'preflight-models', token: Boolean(token), repos: repoResults,
    urls: urlResults, blocked: blocked.length, safeToRent: blocked.length === 0 }, null, 2));
  process.exit(blocked.length ? 3 : 0);
}

console.log(`preflight: ${urlResults.length} files · ${repoResults.length} repos · HF_TOKEN ${token ? 'present' : 'MISSING'}\n`);
for (const r of repoResults) {
  const gate = r.error ? `ERROR ${r.error}` : `gated: ${r.gated}${r.private ? ' · PRIVATE' : ''}`;
  console.log(`  ${r.repo.padEnd(42)} ${gate}`);
}
console.log('');
for (const r of urlResults) {
  const name = r.url.split('/').pop().slice(0, 56);
  console.log(`  ${r.ok ? 'OK  ' : 'FAIL'} ${String(r.status).padStart(3)}  ${name}`);
}

if (!blocked.length) {
  console.log(`\n✓ every file is fetchable — safe to rent.`);
  process.exit(0);
}

console.log(`\n✗ ${blocked.length}/${urlResults.length} files are NOT fetchable. DO NOT RENT.`);
for (const r of repoResults.filter((x) => x.gated && x.gated !== false)) {
  const who = r.gated === 'auto'
    ? 'accept the terms once — instant, but only the account owner can click it'
    : 'a human at the org must approve this — can take days';
  console.log(`  https://huggingface.co/${r.repo}   (gated: ${r.gated} — ${who})`);
}
if (!token) console.log(`  HF_TOKEN is not set; a gated or private repo will 401 from a script even if it reads fine in a browser.`);
process.exit(3);
