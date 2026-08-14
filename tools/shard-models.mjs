#!/usr/bin/env node
// media-tools — shard-models: one source image, N renderers, N boxes, in parallel.
//
// The bake-off tool. Every model gets the SAME image, the SAME swatch, the SAME
// seed and the SAME prompt, each on its own box, so the ONLY variable is the
// model and Ryan's eyes decide.
//
// WHY PARALLEL: GPU-hours price linearly, so five boxes for a fifth of the time
// costs what one box for the whole time costs — wall-clock divides by the box
// count at the same total spend. Proven by shard-stills.mjs, which is how
// keyframes-v10 got rendered. shard-stills shards ONE model across N boxes by
// shot; this shards N MODELS across N boxes on the same shot. Same fleet, same
// tunnels, same resume rule, different partition.
//
// WHY IT DOES NOT RENT BY DEFAULT: renting is gpu-box's job and the tool
// contract says a tool never invokes another tool. `--plan` prints the exact
// gpu-box commands; `--rent` is an explicit opt-in that runs them for you.
//
// CARD SELECTION is delegated, not reimplemented. Each model's catalog entry
// names its card and its measured VRAM; gpu-box's own search already filters
// for the things that bite — reliability >= 0.99, US region, and
// `inet_down >= 500` Mbps, because a slow host turns a 17GB model pull into
// thirty minutes. Do not re-solve that here.
//
// RESUME-SAFE: a model whose output already exists is skipped unless --force.
// So an evicted or Ctrl-C'd run is re-runnable and only redoes what is missing.

import { readFileSync, writeFileSync, mkdirSync, existsSync, readdirSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, join, basename, resolve, isAbsolute } from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { repoRoot } from './_env.mjs';
import { discoverRunning, withTunnels } from './_fleet.mjs';
import { uploadInput, runWorkflow, fetchOutput, setInput, findNode } from './_comfy.mjs';
import { buildUsoGraph } from './_uso.mjs';

const TOOLS = dirname(fileURLToPath(import.meta.url));
const GPU_BOX = join(TOOLS, 'gpu-box.mjs');
const ROOT = repoRoot();

const HELP = `shard-models — one source image through N renderers on N boxes, in parallel

usage: node shard-models.mjs --image src.png --models a,b,c --out DIR [flags]

flags:
  --image PATH     (required) the source image every model receives
  --models LIST    (required) comma-separated keys from models/<key>.json,
                   or 'all' for every catalogued model
  --out DIR        (required) writes <key>.png + <key>.png.json per model
  --style KEY      style whose swatch rides the style channel (default: inkwash)
  --prompt TEXT    content-only scene text. The medium comes from the swatch —
                   do NOT describe the look here.
  --seed N         one seed for every model, so the comparison is fair
                   (default: random, then reused across all models)
  --boxes IDS      comma-separated Vast instance ids (default: all running)
  --base-port N    local tunnel ports = N, N+1, … (default 8211)
  --plan           print the model→card→box assignment plus the gpu-box
                   commands for anything missing, then exit. Spends NOTHING.
  --rent           rent the missing boxes first (opt-in; shells out to gpu-box)
  --force          re-render even when the output already exists
  --catalog DIR    model catalog (default: <repo>/models)

Card selection comes from each model's catalog entry (gpu + measured vramGB).
gpu-box's search does the rest: cheapest first, reliability >=0.99, US, and
inet_down >=500Mbps so a slow host doesn't turn the weight pull into 30 minutes.

example:
  node ~/projects/media-tools/tools/shard-models.mjs \\
    --image jobs/ryan-portrait/source.png --models all \\
    --prompt "a man in round glasses talks to camera" \\
    --out jobs/ryan-portrait/bakeoff --plan`;

const args = process.argv.slice(2);
if (args.includes('--help') || args.length === 0) { console.log(HELP); process.exit(0); }
const flag = (n, d) => { const i = args.indexOf(`--${n}`); return i >= 0 ? args[i + 1] : d; };
const has = (n) => args.includes(`--${n}`);

const image = flag('image');
const outDir = flag('out');
const modelsArg = flag('models');
if (!image || !outDir || !modelsArg) { console.error(HELP); process.exit(2); }
if (!existsSync(image)) { console.error(`--image not found: ${image}`); process.exit(2); }

const styleKey = flag('style', 'inkwash');
const scenePrompt = flag('prompt', '');
const basePort = parseInt(flag('base-port', '8211'), 10);
const force = has('force');
const planOnly = has('plan');
const doRent = has('rent');
const catalogDir = flag('catalog', join(ROOT, 'models'));
const seed = parseInt(flag('seed', String(Math.floor(Math.random() * 1e6))), 10);
const onlyBoxes = flag('boxes') ? String(flag('boxes')).split(',').map((s) => s.trim()) : null;

const sha = (p) => createHash('sha256').update(readFileSync(p)).digest('hex').slice(0, 16);
const abs = (p) => (isAbsolute(p) ? p : resolve(process.cwd(), p));

// ─── catalog ────────────────────────────────────────────────────────────────
function loadCatalog() {
  if (!existsSync(catalogDir)) { console.error(`no model catalog at ${catalogDir}`); process.exit(2); }
  const out = new Map();
  for (const f of readdirSync(catalogDir).filter((f) => f.endsWith('.json'))) {
    const m = JSON.parse(readFileSync(join(catalogDir, f), 'utf8'));
    out.set(m.id || basename(f, '.json'), m);
  }
  return out;
}
const catalog = loadCatalog();
const wanted = modelsArg === 'all' ? [...catalog.keys()] : modelsArg.split(',').map((s) => s.trim());
const unknown = wanted.filter((k) => !catalog.has(k));
if (unknown.length) {
  console.error(`unknown model(s): ${unknown.join(', ')}\n  known: ${[...catalog.keys()].join(', ')}`);
  process.exit(2);
}

// ─── style ──────────────────────────────────────────────────────────────────
const stylePath = join(ROOT, 'styles', styleKey, 'style.json');
if (!existsSync(stylePath)) { console.error(`unknown --style '${styleKey}' (no ${stylePath})`); process.exit(2); }
const style = JSON.parse(readFileSync(stylePath, 'utf8'));
const swatch = join(ROOT, 'styles', styleKey, style.styleSwatch || '');
if (!existsSync(swatch)) { console.error(`style '${styleKey}' has no usable styleSwatch (${swatch})`); process.exit(2); }

// ─── resume: skip what already exists ───────────────────────────────────────
mkdirSync(outDir, { recursive: true });
const todo = wanted.filter((k) => {
  const done = existsSync(join(outDir, `${k}.png`));
  if (done && !force) console.error(`skip ${k} — already in ${outDir} (use --force to redo)`);
  return force || !done;
});
if (!todo.length) { console.error('nothing to do — every model already rendered.'); console.log(JSON.stringify({ rendered: [], skipped: wanted })); process.exit(0); }

// ─── assignment: match each model to a box that can actually hold it ────────
// A box with less VRAM than the model needs will "work" and be silently 3-5x
// slower via offload — the failure mode that wastes money without erroring.
const HEADROOM = 1.15;
const boxVram = (i) => Math.round((i.gpu_totalram || i.gpu_ram || 0) / 1024);

// Models that share a BASE share a box: the base is 12-33GB, a LoRA is 0.2-0.5GB,
// so krea2-darkbrush and krea2-linen-scroll on separate boxes means renting two
// cards and downloading the same 17.4GB twice. One box renders them in sequence,
// swapping only the LoRA. Krea's whole appeal is many LoRAs on one base, so this
// case will keep recurring.
const baseKey = (m) => {
  const w = (m.weights || []).filter((x) => x.dest !== 'loras').map((x) => x.url).sort();
  return w.length ? w.join('|') : `solo:${m.id}`;   // no manifest → never group
};
const groupNeed = (g) => Math.max(...g.map((x) => (x.model.vramGB || 0) * HEADROOM));

function assign(instances) {
  const groups = new Map();
  for (const key of todo) {
    const m = catalog.get(key);
    const k = baseKey(m);
    if (!groups.has(k)) groups.set(k, []);
    groups.get(k).push({ key, model: m });
  }

  const free = [...instances];
  const placed = [], unplaced = [];
  // Biggest requirement first. Placing smallest-first lets a 20GB group take the
  // only 96GB card and strand the 69GB group that had nowhere else to go.
  for (const g of [...groups.values()].sort((a, b) => groupNeed(b) - groupNeed(a))) {
    const need = groupNeed(g);
    free.sort((a, b) => boxVram(a) - boxVram(b));   // then smallest sufficient
    const idx = free.findIndex((i) => boxVram(i) >= need);
    if (idx === -1) {
      unplaced.push({ keys: g.map((x) => x.key), need: Math.ceil(need), gpu: g[0].model.gpu });
      continue;
    }
    placed.push({ inst: free.splice(idx, 1)[0], models: g, need: Math.ceil(need) });
  }
  return { placed, unplaced, idle: free };
}

let instances;
try { instances = discoverRunning(onlyBoxes); }
catch (e) { console.error(`fleet discovery failed: ${e.message}`); process.exit(2); }

let { placed, unplaced, idle } = assign(instances);

// ─── plan ───────────────────────────────────────────────────────────────────
function printPlan() {
  const boxesNeeded = placed.length + unplaced.length;
  console.error(`\nmodels: ${todo.length} to render · ${boxesNeeded} box(es) needed · ${instances.length} running · seed ${seed}\n`);
  console.error(`${'MODEL'.padEnd(22)} ${'VRAM'.padStart(5)} ${'CARD'.padEnd(14)} BOX`);
  for (const p of placed) {
    for (const [n, m] of p.models.entries()) {
      const shared = p.models.length > 1 ? (n === 0 ? '┌' : (n === p.models.length - 1 ? '└' : '│')) : ' ';
      console.error(`${shared} ${m.key.padEnd(20)} ${String(m.model.vramGB || '?').padStart(4)}G ${(p.inst.gpu_name || '?').slice(0, 14).padEnd(14)} ${p.inst.id} (${boxVram(p.inst)}G)`);
    }
  }
  for (const u of unplaced) {
    for (const [n, k] of u.keys.entries()) {
      const shared = u.keys.length > 1 ? (n === 0 ? '┌' : (n === u.keys.length - 1 ? '└' : '│')) : ' ';
      console.error(`${shared} ${k.padEnd(20)} ${String(u.need).padStart(4)}G ${(u.gpu || '?').padEnd(14)} — NO BOX`);
    }
  }
  const shares = placed.filter((p) => p.models.length > 1);
  if (shares.length) {
    console.error(`\n${shares.length} box(es) shared by same-base models — ${shares.reduce((s, p) => s + p.models.length - 1, 0)} rental(s) and duplicate download(s) avoided.`);
  }
  if (idle.length) console.error(`\n${idle.length} idle box(es): ${idle.map((i) => i.id).join(', ')} — burning money for nothing.`);
  if (unplaced.length) {
    console.error(`\nrent the missing ${unplaced.length} box(es):`);
    for (const u of unplaced) {
      console.error(`  node ${GPU_BOX} up --gpu ${u.gpu || 'RTX_5090'} --count 1 --rent   # ${u.keys.join(' + ')}`);
    }
    console.error(`\n(gpu-box picks cheapest-first with reliability >=0.99, US, inet_down >=500Mbps.)`);
  }
}

if (planOnly) {
  printPlan();
  console.log(JSON.stringify({
    seed, style: styleKey, swatch,
    assigned: placed.map((p) => ({ instance: p.inst.id, gpu: p.inst.gpu_name, vramGB: boxVram(p.inst), models: p.models.map((m) => m.key) })),
    unplaced, idle: idle.map((i) => i.id), boxesNeeded: placed.length + unplaced.length, spent: 'nothing',
  }, null, 2));
  process.exit(0);
}

// ─── rent what is missing (explicit opt-in) ─────────────────────────────────
// One rental per GROUP, not per model — that is the whole point of grouping.
if (unplaced.length && doRent) {
  for (const u of unplaced) {
    const gpu = u.gpu || 'RTX_5090';
    console.error(`renting ${gpu} for ${u.keys.join(' + ')} …`);
    try {
      execFileSync('node', [GPU_BOX, 'up', '--gpu', gpu, '--count', '1', '--rent'], { stdio: 'inherit' });
    } catch (e) { console.error(`  rent failed for ${u.keys.join(' + ')}: ${e.message}`); }
  }
  instances = discoverRunning(onlyBoxes);
  ({ placed, unplaced, idle } = assign(instances));
}

if (!placed.length) {
  console.error(`no box can hold any requested model.`);
  printPlan();
  process.exit(3);
}
if (unplaced.length) {
  const skipped = unplaced.flatMap((u) => u.keys);
  console.error(`⚠ ${skipped.length} model(s) have no box and will be SKIPPED: ${skipped.join(', ')}`);
  console.error(`  re-run with --rent, or rent them yourself and re-run (resume-safe).`);
}

printPlan();

// ─── prompt composition ─────────────────────────────────────────────────────
// Where the style lives decides what the text may say — the same three-channel
// rule as the USO graph.
//
//   LoRA models (Krea):  the style is IN THE WEIGHTS and is summoned by a
//     trigger phrase. Prepending style.json's ink-wash paragraph would fight
//     the LoRA with adjectives, which is exactly the failure this project spent
//     a day undoing. Content + trigger, nothing else.
//   Reference models (USO): the style arrives as the swatch image, and
//     style.json's prompt is a documented nudge, so it rides along.
function promptFor(model) {
  const parts = model.triggerPhrase
    ? [scenePrompt, model.triggerPhrase]
    : [style.prompt, scenePrompt];
  return parts.filter(Boolean).join(model.triggerPhrase ? ', ' : ' ');
}

// ─── build one graph for one model ──────────────────────────────────────────
function buildGraph(model, { swatchName, imageName }) {
  if (model.builder === 'uso') {
    const p = model.params || {};
    return buildUsoGraph({
      swatchImage: swatchName,
      plateImage: imageName,
      prompt: promptFor(model),
      seed,
      lora: p.lora ?? 1.35,
      guidance: p.guidance ?? 3.5,
      steps: p.steps ?? 20,
      width: p.width ?? 1152,
      height: p.height ?? 640,
      ckpt: model.checkpoint || 'flux1-dev-fp8.safetensors',
      // 512 welds the plate's FRAMING onto every render — three different shot
      // descriptions all collapsed to head-and-shoulders (style.json,
      // identityFindings2026_08_12). 288 keeps the likeness and lets the
      // composition survive, so it is the default here.
      plateSize: p.plateSize ?? 288,
      prefix: model.id,
    });
  }
  if (model.graph) {
    const gp = isAbsolute(model.graph) ? model.graph : join(ROOT, model.graph);
    if (!existsSync(gp)) throw new Error(`graph not found for ${model.id}: ${gp}`);
    const graph = JSON.parse(readFileSync(gp, 'utf8'));
    const inj = model.inputs || {};
    // Locate by class_type, not node id — a workflow re-export renumbers ids.
    const put = (spec, value) => {
      if (!spec || value === undefined) return;
      const node = spec.node || findNode(graph, spec.class);
      if (!node) throw new Error(`${model.id}: no node of class ${spec.class} in ${basename(gp)}`);
      setInput(graph, node, spec.field, value);
    };
    put(inj.image, imageName);
    put(inj.prompt, promptFor(model));
    put(inj.seed, seed);
    // A LoRA is a second style channel. Set the filename, and set the strength
    // on the SAME node — LoraLoader* carries both, so a separate mapping would
    // just be another thing to get out of sync.
    if (model.lora && inj.lora) {
      put(inj.lora, model.lora.file);
      const node = inj.lora.node || findNode(graph, inj.lora.class);
      if (node && graph[node]?.inputs && 'strength_model' in graph[node].inputs) {
        setInput(graph, node, 'strength_model', model.lora.strength ?? 1.0);
      }
    }
    return graph;
  }
  throw new Error(`${model.id}: catalog entry has neither 'builder' nor 'graph'`);
}

// ─── render ─────────────────────────────────────────────────────────────────
// BOXES run in parallel. Models WITHIN a box run in sequence, because they share
// the same base weights and ComfyUI would otherwise evict and reload between
// them — the load is the expensive part, so serialising is faster than racing.
const t0 = Date.now();
const results = await withTunnels(placed.map((p) => p.inst), basePort, async (boxes) => {
  // withTunnels preserves order, so boxes[i] is the tunnel for placed[i].
  const perBox = await Promise.all(boxes.map(async ({ inst, port }, i) => {
    const host = `http://127.0.0.1:${port}`;
    const group = placed[i].models;
    const done = [];

    // Upload the inputs ONCE per box, not once per model.
    let swatchName, imageName;
    try {
      swatchName = await uploadInput(host, readFileSync(swatch), basename(swatch));
      imageName = await uploadInput(host, readFileSync(abs(image)), basename(image));
    } catch (e) {
      console.error(`[box ${inst.id}] ✗ upload failed: ${e.message}`);
      return group.map(({ key }) => ({ model: key, ok: false, error: `upload: ${e.message}`, box: inst.id }));
    }

    for (const { key, model } of group) {
      const out = join(outDir, `${key}.png`);
      const started = Date.now();
      try {
        const graph = buildGraph(model, { swatchName, imageName });
        console.error(`[${key}] → ${inst.gpu_name} ${inst.id} :${port}${group.length > 1 ? `  (${done.length + 1}/${group.length} on this box)` : ''}`);
        const { outputs, promptId } = await runWorkflow(host, graph, { clientId: `shard-models-${key}`, interval: 2500, maxPolls: 600 });
        const bytes = await fetchOutput(host, outputs[0]);
        writeFileSync(out, bytes);
        const secs = Math.round((Date.now() - started) / 1000);
        writeFileSync(`${out}.json`, JSON.stringify({
          tool: 'shard-models', model: key, engine: model.engine || 'comfy',
          renderer: model.builder || model.graph, style: styleKey, seed,
          params: model.params || null, prompt: promptFor(model),
          triggerPhrase: model.triggerPhrase || null,
          lora: model.lora || null,
          inputs: {
            source: { file: abs(image), sha256: sha(abs(image)) },
            swatch: { file: swatch, sha256: sha(swatch) },
          },
          box: { id: inst.id, gpu: inst.gpu_name, vramGB: boxVram(inst), dph: inst.dph_total ?? null },
          sharedBoxWith: group.filter((g) => g.key !== key).map((g) => g.key),
          promptId, secondsPerImage: secs, out, bytes: bytes.length,
        }, null, 2));
        console.error(`[${key}] ✓ ${out}  ${secs}s`);
        done.push({ model: key, out, ok: true, seconds: secs, box: inst.id, gpu: inst.gpu_name });
      } catch (e) {
        console.error(`[${key}] ✗ ${e.message}`);
        done.push({ model: key, ok: false, error: e.message, box: inst.id });
      }
    }
    return done;
  }));
  return perBox.flat();
});

const wall = Math.round((Date.now() - t0) / 1000);
const ok = results.filter((r) => r.ok);
const dph = placed.reduce((s, p) => s + (p.inst.dph_total || 0), 0);

console.error(`\n${ok.length}/${results.length} rendered in ${wall}s wall-clock across ${placed.length} box(es).`);
if (dph) console.error(`fleet burn: $${dph.toFixed(3)}/hr → this run cost ≈ $${((dph * wall) / 3600).toFixed(3)}.`);
console.error(`BOXES ARE STILL BILLING. Stop or destroy them:`);
console.error(`  node ${GPU_BOX} stop --id <id>    # storage-only, weights kept`);
console.error(`  node ${GPU_BOX} down --id <id>    # destroy`);

console.log(JSON.stringify({
  out: outDir, seed, style: styleKey, wallSeconds: wall,
  rendered: ok.map((r) => r.out),
  results, skipped: unplaced.flatMap((u) => u.keys), boxesUsed: placed.length,
  estimatedCost: dph ? +((dph * wall) / 3600).toFixed(4) : null,
}, null, 2));
process.exit(ok.length === results.length ? 0 : 1);
