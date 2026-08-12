#!/usr/bin/env node
//
// media-tools — gpu-box: rent, provision, and destroy a Vast.ai GPU box. One job.
// Salvaged verbatim from cutwork/tools/vast.mjs 2026-08-11; only the env and
// state-dir lookups were repo-rooted and the usage strings renamed.
//
// Vast.ai instance control. Spin a GPU box up, run, tear it down — at a
// whim, from the CLI. Wraps the `vastai` CLI (https://docs.vast.ai/cli).
//
// COST-SAFE BY DESIGN:
//   • `up` is a DRY RUN by default — it searches + shows the pick and $/hr but
//     rents NOTHING until you add `--rent`.
//   • `--max-price` caps $/hr; offers above it are refused.
//   • `--min-reliability` (default 0.99) skips flaky marketplace hosts.
//   • `down` DESTROYS the instance → billing stops immediately. You pay only
//     while an instance EXISTS (rented), so destroy when done. `status` shows the
//     running clock + accrued cost so it can't silently burn.
//
// USAGE:
//   node gpu-box.mjs up   [--gpu RTX_5090] [--max-price 1.00] [--min-reliability 0.99] [--disk 100] [--retries 3] [--rent]
//                            [--count N] rent N boxes (a shard fleet)  [--clips-only] lean LTX-render manifest
//                            [--wan] Wan 2.2 + LongCat-Avatar probe stack (provision-wan.sh) instead of LTX
//        with --rent it AUTO-CYCLES hosts: rents → waits → on a dead host destroys
//        it, remembers the machine, rolls to the next. No babysitting a bad drive.
//   node gpu-box.mjs status            # honest state: READY / loading / ERROR + accrued cost
//   node gpu-box.mjs wait [--id <id>]  # block until READY, fast-fail on a dead host
//   node gpu-box.mjs down [--id <id>]  # destroy (stops billing); keeps learned bad-host list
//
// Needs VAST_API_KEY in .env (Vast → Keys page). SSH pubkey in .vast/ssh_key.pub
// is attached on rent (also add it to your Vast account SSH Keys page).

import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'node:fs';
import { execFileSync, spawn } from 'node:child_process';

// ─── env + state ──────────────────────────────────────────────────────────
// Repo-rooted, not cwd-rooted: this tool runs from any directory (foreign-cwd
// rule, CLAUDE.md §7).
const { envKey, repoRoot } = await import('./_env.mjs');
let VAST_API_KEY;
try { VAST_API_KEY = envKey('VAST_API_KEY'); }
catch { console.error('✗ VAST_API_KEY not in .env (get it from the Vast → Keys page)'); process.exit(1); }

const STATE_DIR = (await import('node:path')).join(repoRoot(), '.vast');
const STATE_FILE = `${STATE_DIR}/state.json`;
const SSH_PUBKEY = existsSync(`${STATE_DIR}/ssh_key.pub`) ? readFileSync(`${STATE_DIR}/ssh_key.pub`, 'utf8').trim() : null;
if (!existsSync(STATE_DIR)) mkdirSync(STATE_DIR, { recursive: true });
const loadState = () => { try { return JSON.parse(readFileSync(STATE_FILE, 'utf8')); } catch { return { instances: [] }; } };
const saveState = (s) => writeFileSync(STATE_FILE, JSON.stringify(s, null, 2));

// ─── vastai CLI shell (JSON via --raw) ──────────────────────────────────────
function vast(args, { json = false, input } = {}) {
  const full = [...args, '--api-key', VAST_API_KEY];
  const opts = { encoding: 'utf8' };
  if (input !== undefined) opts.input = input;   // feed confirmation prompts (destroy asks [y/N])
  let out;
  try { out = execFileSync('vastai', full, opts); }
  catch (e) { throw new Error(`vastai ${args[0]} ${args[1] || ''} failed: ${(e.stdout || '') + (e.stderr || e.message)}`.slice(0, 400)); }
  if (!json) return out;
  try { return JSON.parse(out); } catch { throw new Error(`vastai ${args.join(' ')} did not return JSON: ${out.slice(0, 200)}`); }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// instances-v1 is the non-deprecated query; normalize its shape (array OR {instances:[]}).
function listInstances() {
  const raw = vast(['show', 'instances-v1', '--raw'], { json: true });
  if (Array.isArray(raw)) return raw;
  if (raw && Array.isArray(raw.instances)) return raw.instances;
  return [];
}

// Honest state read — this is the bug we hit: a host that FAILS to pull/create the
// container sits at actual_status='loading' forever while Vast flips intended_status
// /next_state to 'stopped'. Reading only actual_status reports "loading" for a box
// that is actually DEAD. Discriminate on intent: if Vast no longer intends to run it,
// it's an error, not progress.
function classify(i) {
  const a = i.actual_status, intended = i.intended_status, next = i.next_state, cur = i.cur_state;
  if (a === 'running' && intended !== 'stopped') return { state: 'ready', msg: 'running — ComfyUI on :8188' };
  // Deliberately stopped/paused: it ACTUALLY exited (GPU billing off, storage-only). Must
  // check this BEFORE the error branch — a paused box also has intended_status='stopped',
  // so testing intent alone misreports a healthy paused box as a dead host.
  if (a === 'exited' || a === 'stopped') return { state: 'stopped', msg: 'paused — storage-only, GPU billing OFF' };
  // Host failed to EVER bring the container up (still loading/null while Vast gave up).
  if (intended === 'stopped' || next === 'stopped')
    return { state: 'error', msg: `host failed to bring the container up (actual=${a}, intended=${intended}). Container never created → destroy and retry a different host.` };
  if (a === 'loading' || cur === 'loading' || cur === 'created' || a == null)
    return { state: 'loading', msg: `${a || cur || 'provisioning'} — pulling image / starting` };
  return { state: 'unknown', msg: `actual=${a} cur=${cur} intended=${intended} next=${next}` };
}

// ─── arg parsing ────────────────────────────────────────────────────────────
const [cmd, ...rest] = process.argv.slice(2);
const flag = (name, def) => { const i = rest.indexOf(`--${name}`); return i >= 0 ? (rest[i + 1]?.startsWith('--') ? true : rest[i + 1]) : def; };
const has = (name) => rest.includes(`--${name}`);

// LTX-2.3 22B fp8 + Gemma text encoder need ~48GB VRAM — an Ada/Hopper/Blackwell
// card with native FP8. RTX 6000 Ada (48GB Ada) is the default: same class as the
// L40S but typically cheaper on Vast (~$0.90 vs ~$1.20/hr). A 32GB 5090 is too small
// for this model set (would OOM / offload heavily).
const GPU = flag('gpu', 'RTX_6000Ada');
const MAX_PRICE = parseFloat(flag('max-price', '1.20'));
const MIN_REL = parseFloat(flag('min-reliability', '0.99'));
const DISK = parseInt(flag('disk', '120'), 10);   // fp8 22B set (~45GB) + ComfyUI + headroom
// Geography + bandwidth matter as much as price: a far/slow host turns the model pull
// into 30+ min and makes port-forwarded viewing laggy. Default to US, fast downlink.
const REGION = flag('region', 'US');              // 'any' to disable the geo filter
const MIN_DOWN = parseInt(flag('min-down', '500'), 10); // min host downlink Mbps
// Official PyTorch base on CUDA 12.8 (the tier LTX-2.3 fp8 needs; ai-dock's 12.1.1 is
// too old). We provision it ourselves from tools/provision-ltx.sh (hosted as a gist,
// pulled by the onstart below): ComfyUI + ComfyUI-LTXVideo + kornia patch + the LTX-2.3
// LipDub model manifest, with supervisord keeping ComfyUI alive. Never a stranger's bundle.
const IMAGE = flag('image', 'pytorch/pytorch:2.11.0-cuda12.8-cudnn9-runtime');
// --wan: provision the Wan 2.2 + LongCat-Avatar stack (tools/provision-wan.sh,
// ~63GB — the call-2 probe rig) instead of the LTX stack. Each stack's script is
// hosted as a pinned gist (re-gist + update the URL if you edit the script).
const WAN = has('wan');
const PROVISION_URL = flag('provision-url', WAN
  ? 'https://gist.githubusercontent.com/blessdog/3b2ef4b87f66b88239858dac50b9ba9d/raw/fe379e5ced2f7d4697fede99bf34fd6433a4e920/provision-wan.sh'
  : 'https://gist.githubusercontent.com/blessdog/9785796184aab22543d0211b30b9f85d/raw/9f21030e0bf0df410bf41f6484bf52229e662471/provision-ltx.sh');
// --clips-only: provision a lean render SHARD (LTX fp8 set only, ~44GB instead of ~62GB)
// for fan-out clip rendering via tools/shard-clips.mjs. Skips Director/lipdub extras.
const CLIPS_ONLY = has('clips-only');
const optKey = (n) => { try { return envKey(n); } catch { return undefined; } };
const HF_TOKEN = optKey('HF_TOKEN');
// Civitai token (optional): unlocks the token-gated alt claymation LoRA on --wan boxes.
const CIVITAI_TOKEN = optKey('CIVITAI_TOKEN');

const fmt$ = (n) => `$${Number(n).toFixed(3)}`;

// ─── up ─────────────────────────────────────────────────────────────────────
async function up() {
  const query = `gpu_name=${GPU} num_gpus=1 verified=true rentable=true disk_space>=${DISK} dph_total<=${MAX_PRICE} reliability>=${MIN_REL} inet_down>=${MIN_DOWN}`;
  console.log(`searching: ${GPU}, ≤${fmt$(MAX_PRICE)}/hr, reliability ≥${MIN_REL}, disk ≥${DISK}GB, downlink ≥${MIN_DOWN}Mbps, region ${REGION}\n`);
  const offers = vast(['search', 'offers', query, '-o', 'dph_total', '--raw'], { json: true });
  if (!Array.isArray(offers) || !offers.length) {
    console.log('no offers match. loosen --max-price / --min-reliability / --gpu and retry.'); return;
  }
  const st0 = loadState();
  const bad = new Set((st0.badMachines || []).map(String));
  let pool = offers.filter((o) => !bad.has(String(o.machine_id)));
  if (REGION && REGION.toLowerCase() !== 'any') {
    const inRegion = pool.filter((o) => String(o.geolocation || '').toUpperCase().includes(REGION.toUpperCase()));
    if (inRegion.length) pool = inRegion;
    else console.log(`(no ${REGION} hosts matched — showing all regions; pass --region any to silence)`);
  }
  const top = pool.slice(0, 8);
  console.log('top candidates (cheapest first; bad hosts + region/bandwidth filtered):');
  for (const o of top) {
    console.log(`  id ${o.id}  machine ${o.machine_id}  ${o.gpu_name}  ${Math.round((o.gpu_ram || 0) / 1024)}GB  ${fmt$(o.dph_total)}/hr  rel ${(o.reliability2 ?? o.reliability ?? 0).toFixed(3)}  ↓${Math.round(o.inet_down || 0)}Mbps  ${o.geolocation || ''}`);
  }
  if (!top.length) { console.log('\nevery candidate is on a known-bad host. Widen --gpu/--max-price or clear .vast/state.json badMachines.'); return; }

  if (!has('rent')) {
    const pick = top[0];
    console.log(`\npick → id ${pick.id} (machine ${pick.machine_id}) @ ${fmt$(pick.dph_total)}/hr  (≈ ${fmt$(pick.dph_total)} /hr)`);
    console.log('\nDRY RUN — nothing rented. Re-run with --rent to actually create an instance.');
    return;
  }
  if (!HF_TOKEN) { console.error('✗ HF_TOKEN not in .env — the image needs it to pull LTX-2 + Gemma weights.'); process.exit(1); }

  // AUTO-CYCLE the bad-drive problem: marketplace hosts sometimes just fail to pull /
  // create the container (we hit machine 52162 — sat at actual_status='loading' while
  // Vast had already given up, intended_status='stopped'). So: rent a candidate, WAIT
  // for it to genuinely come up, and if it's a dead host destroy it and roll to the
  // NEXT distinct host — recording bad machines in state.json so we never re-pick them.
  // "You gotta get another one," automated. --retries N bounds how many hosts to try.
  // --count N rents a FLEET (N distinct hosts, e.g. render shards for shard-clips.mjs);
  // default 1 keeps the original single-box semantics.
  const want = Math.max(1, parseInt(flag('count', '1'), 10));
  const maxHosts = parseInt(flag('retries', '3'), 10) + want;
  const tried = new Set();
  const lives = [];

  for (const offer of top) {
    if (lives.length >= want || tried.size >= maxHosts) break;
    if (tried.has(String(offer.machine_id))) continue;
    tried.add(String(offer.machine_id));
    console.log(`\n→ attempt ${tried.size}/${maxHosts} (live ${lives.length}/${want}): offer ${offer.id} (machine ${offer.machine_id}) @ ${fmt$(offer.dph_total)}/hr — renting…`);
    let id;
    try { id = rentOffer(offer); }
    catch (e) { console.error(`  rent call failed: ${e.message}`); continue; }
    const s = loadState();
    s.instances = s.instances || [];
    s.instances.push({ id, dph: offer.dph_total, gpu: offer.gpu_name, machine: offer.machine_id, started: new Date().toISOString(), image: IMAGE });
    saveState(s);
    console.log(`  rented instance ${id} — waiting for it to actually come up (fast-fail on a bad host):`);
    const r = await waitReady(id, { timeoutMin: parseFloat(flag('timeout', '12')) });
    if (r === 'ready') { lives.push({ id, offer }); continue; }
    console.error(`  ✗ machine ${offer.machine_id}: ${r}. Destroying it and trying another host…`);
    try { vast(['destroy', 'instance', String(id)], { input: 'y\n' }); } catch (e) { console.error(`  destroy warn: ${e.message}`); }
    const s2 = loadState();
    s2.instances = (s2.instances || []).filter((x) => String(x.id) !== String(id));
    s2.badMachines = Array.from(new Set([...(s2.badMachines || []).map(String), String(offer.machine_id)]));
    saveState(s2);
  }

  if (!lives.length) { console.error(`\n✗ no host came up after ${tried.size} attempt(s). Re-run later, or widen --gpu / --max-price / --retries.`); process.exit(1); }
  if (lives.length < want) console.error(`\n⚠ only ${lives.length}/${want} boxes came up — shard across what's live or re-run \`up --rent --count ${want - lives.length}\` for the rest.`);

  for (const l of lives.slice(1))
    console.log(`✓ LIVE — instance ${l.id} (machine ${l.offer.machine_id}) @ ${fmt$(l.offer.dph_total)}/hr. BILLING IS RUNNING.`);
  const live = lives[0];
  console.log(`\n✓ LIVE — instance ${live.id} (machine ${live.offer.machine_id}) @ ${fmt$(live.offer.dph_total)}/hr. BILLING IS RUNNING.`);
  console.log(`  provisioning now: ComfyUI + LTX-2.3 pack + kornia patch, then ~45GB model pull (~15-25 min).`);
  console.log(`  readiness markers (on box):  /var/log/prov.marker (COMFY_UP)  ·  /var/log/models.marker (MODELS_DONE)`);
  console.log(`  watch state:    node gpu-box.mjs status`);
  console.log(`  KILL it:        node gpu-box.mjs down   ← the second you're done`);
  console.log(`  ssh + forward:  vastai ssh-url ${live.id}   then  ssh -L 8188:localhost:8188 -p <port> root@<host>`);
  console.log(`  tail boot log:  (on box)  tail -f /var/log/bongpot-start.log  +  tail -f /var/log/prov.log`);
}

// Create ONE instance from a search offer, with the onstart boot fix. Returns its id.
// (Single source for the launch incantation — up()'s auto-cycle calls this per host.)
function rentOffer(offer) {
  // Bare official base → we provision it ourselves. --onstart-cmd: persist HF_TOKEN to
  // /etc/environment (SSH shells + the script see it), then pull tools/provision-ltx.sh
  // from its gist and run it under nohup with a tailable log. The script installs
  // ComfyUI + the LTX node pack + kornia patch + the model manifest and brings ComfyUI
  // up under supervisord (so it stays alive). Re-runs idempotently on every box start.
  const dockerEnv = `-p 8188:8188`; // port only; token rides in onstart, not --env
  const onstart = [
    `printf 'HF_TOKEN=%s\\n' '${HF_TOKEN}' >> /etc/environment`,
    `export HF_TOKEN='${HF_TOKEN}'`,
    ...(CLIPS_ONLY ? [`echo 'CLIPS_ONLY=1' >> /etc/environment`, `export CLIPS_ONLY=1`] : []),
    ...(WAN && CIVITAI_TOKEN ? [`printf 'CIVITAI_TOKEN=%s\\n' '${CIVITAI_TOKEN}' >> /etc/environment`, `export CIVITAI_TOKEN='${CIVITAI_TOKEN}'`] : []),
    // python3 is guaranteed on the pytorch base; curl/wget may not be yet (apt runs
    // inside the script). Fetch the provisioning script with python, then run it.
    `python3 -c "import urllib.request; urllib.request.urlretrieve('${PROVISION_URL}','/provision.sh')"`,
    `nohup bash /provision.sh > /var/log/bongpot-start.log 2>&1 &`,
  ].join('; ');
  const res = vast(['create', 'instance', String(offer.id), '--image', IMAGE, '--env', dockerEnv, '--disk', String(DISK), '--ssh', '--direct', '--onstart-cmd', onstart, '--raw'], { json: true });
  const id = res.new_contract || res.instance_id || res.id;
  if (!id) throw new Error('create returned no instance id: ' + JSON.stringify(res).slice(0, 200));
  if (SSH_PUBKEY) { try { vast(['attach', 'ssh', String(id), SSH_PUBKEY]); } catch { /* non-fatal */ } }
  return id;
}

// Poll one instance until it's genuinely READY, or detect a dead host FAST and bail.
// The honest replacement for the bash poll loops that mistook a failed host for
// "still loading". Returns 'ready' | 'error' | 'timeout'.
async function waitReady(id, { timeoutMin = 12, every = 10000, errorPolls = 2 } = {}) {
  const deadline = Date.now() + timeoutMin * 60000;
  let last = '', errStreak = 0;
  while (Date.now() < deadline) {
    const inst = listInstances().find((i) => String(i.id) === String(id));
    if (!inst) { console.error(`    instance ${id} vanished`); return 'error'; }
    const c = classify(inst);
    const line = `${c.state}: ${c.msg}`;
    if (line !== last) { console.log(`    [${new Date().toLocaleTimeString()}] ${line}`); last = line; }
    if (c.state === 'ready') return 'ready';
    if (c.state === 'error') { if (++errStreak >= errorPolls) return 'error'; }
    else errStreak = 0;
    await sleep(every);
  }
  console.error(`    timed out after ${timeoutMin}min still not running — treating as a dead host`);
  return 'timeout';
}

// ─── status ───────────────────────────────────────────────────────────────
async function status() {
  const live = listInstances();
  if (!live.length) { console.log('no instances. ($0 burning.)'); return; }
  const tag = { ready: '✓ READY', loading: '… loading', stopped: '⏸ STOPPED (idle)', error: '✗ ERROR — dead host', unknown: '? unknown' };
  let total = 0;
  for (const i of live) {
    const c = classify(i);
    const startMs = i.start_date ? i.start_date * 1000 : Date.parse(i.started || 0);
    const hrs = startMs ? (Date.now() - startMs) / 3.6e6 : 0;
    const stopped = c.state === 'stopped';
    const rate = stopped ? (i.storage_total_cost || 0) : (i.dph_total || 0);
    if (!stopped) total += rate * hrs; // only RUNNING boxes accrue the GPU rate
    const cost = stopped ? `@ ${fmt$(rate)}/hr storage (GPU off)` : `@ ${fmt$(rate)}/hr  ≈ ${fmt$(rate * hrs)} so far`;
    console.log(`  instance ${i.id}  machine ${i.machine_id}  ${i.gpu_name || ''}  ${tag[c.state] || c.state}  up ${hrs.toFixed(2)}h  ${cost}`);
    if (c.state !== 'ready' && c.state !== 'stopped') console.log(`      → ${c.msg}`);
  }
  console.log(`\n  ⏱  GPU billing now ≈ ${fmt$(total)} (stopped boxes bill only tiny storage) — \`down\` to destroy.`);
}

// Wait on the current (or --id) instance until READY; fast-fail + exit non-zero on a dead host.
async function wait() {
  const id = flag('id') || listInstances()[0]?.id;
  if (!id) { console.log('no instance to wait on.'); return; }
  const r = await waitReady(id, { timeoutMin: parseFloat(flag('timeout', '12')) });
  if (r === 'ready') { console.log(`✓ instance ${id} READY — ComfyUI on :8188`); return; }
  console.error(`✗ instance ${id} ${r} — \`node gpu-box.mjs down\` to clear it, then \`up --rent\` to try another host.`);
  process.exit(2);
}

// ─── down ─────────────────────────────────────────────────────────────────
async function down() {
  const live = listInstances();
  const ids = has('id') ? [flag('id')] : live.map((i) => i.id);
  if (!ids.length) { console.log('nothing to destroy. ($0 burning.)'); return; }
  for (const id of ids) {
    console.log(`destroying instance ${id} …`);
    // `vastai destroy` prompts "Are you sure? [y/N]" and defaults to No when
    // non-interactive — feed it 'y' or it silently aborts (and keeps billing).
    try { vast(['destroy', 'instance', String(id)], { input: 'y\n' }); console.log(`  ✓ destroy sent for ${id}`); }
    catch (e) { console.error(`  ✗ ${id}: ${e.message}`); }
  }
  const prev = loadState();
  prev.instances = (prev.instances || []).filter((x) => !ids.some((id) => String(id) === String(x.id)));
  saveState(prev); // remove only the destroyed ids; keep other instances + learned bad hosts
  // verify the TARGETED instance(s) are gone — NOT that zero instances remain (other boxes
  // we want to keep would falsely trip a "still present" alarm).
  await sleep(6000);
  const left = listInstances();
  const stillThere = ids.filter((id) => left.some((i) => String(i.id) === String(id)));
  if (stillThere.length) console.error(`⚠ instance(s) ${stillThere.join(', ')} STILL present — re-run \`down --id <id>\` or check the dashboard.`);
  else console.log(`✓ confirmed destroyed: ${ids.join(', ')} gone ($0). ${left.length ? `(${left.length} other instance(s) still parked.)` : ''}`);
}

// ─── ssh helpers ────────────────────────────────────────────────────────────
// SSH/scp args are built as a LITERAL ARRAY and handed to spawn/execFileSync — no
// shell, so no word-splitting footgun (the recurring "zsh ate my -p flag" bug just
// can't happen here). Resolve host/port from `vastai ssh-url <id>`.
const SSH_KEY = `${process.env.HOME}/.ssh/id_ed25519`;
function sshTarget(id) {
  const url = String(vast(['ssh-url', String(id)])).trim();
  const m = url.match(/ssh:\/\/([^@]+)@([^:]+):(\d+)/);
  if (!m) throw new Error(`could not parse ssh-url (${url})`);
  return { user: m[1], host: m[2], port: m[3] };
}
function sshArgs(id, extra = []) {
  const t = sshTarget(id);
  return ['-i', SSH_KEY, '-p', t.port, '-o', 'StrictHostKeyChecking=accept-new', '-o', 'ConnectTimeout=15', '-o', 'BatchMode=yes', ...extra, `${t.user}@${t.host}`];
}
const pickId = () => flag('id') || listInstances()[0]?.id;

// run a remote command: node tools/gpu-box.mjs run --cmd 'du -sh /ComfyUI/models'
async function runCmd() {
  const id = pickId(); if (!id) { console.error('no instance'); process.exit(1); }
  const cmd = flag('cmd'); if (!cmd || cmd === true) { console.error('usage: run --cmd "<remote command>"'); process.exit(1); }
  // append the command as a SINGLE trailing arg (ssh runs it via the remote shell).
  // Do NOT let a non-zero remote exit (e.g. grep with no match) throw away the stdout
  // we actually wanted — capture and print it regardless.
  let out;
  try { out = execFileSync('ssh', [...sshArgs(id), cmd], { encoding: 'utf8' }); }
  catch (e) { out = (e.stdout || '') + (e.stderr || ''); }
  process.stdout.write(out);
}

// port-forward ComfyUI :8188 to localhost (foreground; Ctrl-C to stop)
async function forward() {
  const id = pickId(); if (!id) { console.error('no instance'); process.exit(1); }
  const local = flag('port', '8188');
  const args = sshArgs(id, ['-N', '-L', `${local}:localhost:8188`]);
  console.log(`forwarding localhost:${local} → instance ${id} :8188   (Ctrl-C to stop)`);
  const p = spawn('ssh', args, { stdio: 'inherit' });
  p.on('exit', (c) => process.exit(c || 0));
}

// ─── stop / start (scale compute to ~zero, keep the disk) ───────────────────
// STOP drops an idle box from the full GPU rate to STORAGE-ONLY (holds the
// downloaded weights, GPU billing stops). START resumes it (~1-2 min, no
// re-download). This is the cost model: pay GPU only while actually rendering.
// Caveat: a stopped marketplace box can be reclaimed by the host — not as firm as
// a persistent Volume (which survives destroy but is host-locality-bound).
async function stop() {
  const id = flag('id') || pickId(); if (!id) { console.log('no instance to stop.'); return; }
  vast(['stop', 'instance', String(id)]);
  // NEVER trust "sent" — this is a MONEY command. Poll the real state until billing
  // has actually dropped, or scream. A silent failure here = paying GPU rate for nothing.
  // ONLY actual_status proves billing stopped. intended_status='stopped' just means the
  // stop was REQUESTED — the box can still be running and billing at that point. Poll the
  // REAL state until it's genuinely exited/stopped (a stop can take ~30-90s), or scream.
  for (let i = 0; i < 18; i++) {
    await sleep(6000);
    const inst = listInstances().find((x) => String(x.id) === String(id));
    if (!inst) { console.log(`instance ${id} gone (destroyed?).`); return; }
    const st = inst.actual_status;
    if (st === 'exited' || st === 'stopped') {
      console.log(`✓ VERIFIED stopped (actual_status=${st}) — GPU billing stopped; storage-only ~${fmt$(inst.storage_total_cost || 0)}/hr, disk retained.`);
      console.log(`  resume: node tools/gpu-box.mjs start   (~1-2 min, no re-download)`);
      return;
    }
    console.log(`  …actual_status=${st}; STILL BILLING until it exits`);
  }
  console.error(`⚠ stop NOT confirmed after ~108s — you may STILL be billing the GPU. Re-run \`stop\` or check the dashboard NOW.`);
  process.exit(1);
}
async function start() {
  const id = flag('id') || pickId(); if (!id) { console.log('no instance id (pass --id).'); return; }
  vast(['start', 'instance', String(id)]);
  console.log(`✓ start sent for ${id} — resuming (GPU billing resumes). Waiting for READY:`);
  const r = await waitReady(id, { timeoutMin: 6 });
  console.log(r === 'ready' ? '✓ READY — ComfyUI on :8188 (forward it: node tools/gpu-box.mjs forward)' : `✗ ${r}`);
}

const run = { up, status, down, wait, run: runCmd, forward, stop, start }[cmd];
if (!run) { console.error('usage: node gpu-box.mjs <up|status|down|stop|start|wait|run|forward> [flags]  (see header)'); process.exit(1); }
run().catch((e) => { console.error('✗', e.message); process.exit(1); });
