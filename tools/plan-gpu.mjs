#!/usr/bin/env node
// media-tools — plan-gpu: a workload → which card to rent. One job.
//
// gpu-box RENTS. This tool only RECOMMENDS, and it rents nothing — so it is safe
// to run any time and costs nothing.
//
// Why it exists: gpu-box searches ONE gpu type and sorts by $/hour. That is the
// wrong metric. A card at 2x the price that renders 5x faster is 2.5x cheaper
// PER CLIP and finishes in a fifth of the wall-clock. It also had no notion of
// how much VRAM the job needs, so it happily rented a card that spends the whole
// render offloading (measured: hunyuan 720p at 43.3/49GB on a 6000 Ada,
// 135 s/step).
//
// Estimates come from tools/benchmarks.json, which prefers MEASURED numbers and
// falls back to a relative-throughput prior. Measure and record; never guess
// into that file.

import { readFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { join } from 'node:path';
import { envKey, repoRoot } from './_env.mjs';

const HELP = `plan-gpu — pick the right card for a workload, ranked by cost PER JOB

usage: node plan-gpu.mjs --workload KEY --count N [flags]

flags:
  --workload KEY   a key from tools/benchmarks.json workloads, e.g.
                   hunyuan-1.5-i2v-720p-fp16 | uso-inkwash-still
  --count N        how many clips/stills you intend to render (default 1)
  --list           list known workloads and measurements, then exit
  --max-price F    ignore offers above this $/hr (default 6.00)
  --min-reliability F  default 0.98
  --disk N         GB of disk required (default 120)
  --region R       US | EU | any  (default any — speed matters more than latency
                   for batch rendering)
  --headroom F     VRAM safety multiplier (default 1.15) — a card that only just
                   fits will offload and crawl
  --top N          how many candidates to print (default 10)

Prints a table sorted by ESTIMATED TOTAL COST for the whole job, with wall-clock
beside it so you can pay a little more to finish sooner if you want to.

example:
  node ~/projects/media-tools/tools/plan-gpu.mjs --workload hunyuan-1.5-i2v-720p-fp16 --count 9`;

const args = process.argv.slice(2);
if (args.includes('--help')) { console.log(HELP); process.exit(0); }
const flag = (n, d) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : d; };

const BENCH = JSON.parse(readFileSync(join(repoRoot(), 'tools', 'benchmarks.json'), 'utf8'));

if (args.includes('--list') || args.length === 0) {
  console.log('known workloads:\n');
  for (const [k, w] of Object.entries(BENCH.workloads)) {
    console.log(`  ${k}`);
    console.log(`    needs ~${w.vramGB}GB VRAM`);
    for (const m of w.measured || []) {
      console.log(`    MEASURED ${m.gpu}: ${m.secondsPerClip}s per unit (${m.date})`);
    }
  }
  console.log('\nrun with --workload KEY --count N to plan.');
  process.exit(0);
}

const key = flag('--workload');
const workload = BENCH.workloads[key];
if (!workload) { console.error(`unknown --workload '${key}'. Run --list.`); process.exit(2); }
const count = parseInt(flag('--count', '1'), 10);
const maxPrice = parseFloat(flag('--max-price', '6.00'));
const minRel = parseFloat(flag('--min-reliability', '0.98'));
const disk = parseInt(flag('--disk', '120'), 10);
const region = flag('--region', 'any');
const headroom = parseFloat(flag('--headroom', '1.15'));
const top = parseInt(flag('--top', '10'), 10);

const needVram = workload.vramGB * headroom;

// The measured baseline: whichever card we have a real number for.
const base = (workload.measured || [])[0];
if (!base) { console.error(`no measurement for '${key}' — render one unit and record it before planning.`); process.exit(2); }
const basePerf = BENCH.gpuPerf[base.gpu] || 1;

function secondsFor(gpuName) {
  const measured = (workload.measured || []).find((m) => m.gpu === gpuName);
  if (measured) return { seconds: measured.secondsPerClip, source: 'measured' };
  const perf = BENCH.gpuPerf[gpuName];
  if (!perf) return null;
  return { seconds: base.secondsPerClip * (basePerf / perf), source: 'estimated' };
}

const VAST_API_KEY = envKey('VAST_API_KEY');
function vast(a) {
  const out = execFileSync('vastai', [...a, '--api-key', VAST_API_KEY], { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });
  return JSON.parse(out);
}

// Only ask about cards we can reason about AND that hold the job in VRAM.
const candidates = Object.keys(BENCH.gpuPerf)
  .filter((g) => g !== '_note')
  .filter((g) => (BENCH.gpuVram[g] || 0) >= needVram);

if (!candidates.length) {
  console.error(`no known card has ${needVram.toFixed(0)}GB VRAM. Lower --headroom or split the workload.`);
  process.exit(1);
}

console.error(`plan-gpu: ${key} x${count} · needs ≥${needVram.toFixed(0)}GB VRAM · baseline ${base.gpu} @ ${base.secondsPerClip}s/unit (measured ${base.date})`);
console.error(`querying ${candidates.length} card types on Vast…\n`);

const rows = [];
for (const gpu of candidates) {
  let offers = [];
  try {
    offers = vast(['search', 'offers',
      `gpu_name=${gpu} num_gpus=1 verified=true rentable=true disk_space>=${disk} dph_total<=${maxPrice} reliability>=${minRel}`,
      '-o', 'dph_total', '--raw']);
  } catch { continue; }
  if (!Array.isArray(offers) || !offers.length) continue;
  // The card table is a PRIOR, the offer is the truth: A100 ships in 40GB and
  // 80GB, H100 in 80 and 94. Filtering on the table alone recommended a 40GB
  // A100 for a 53GB job (caught 2026-08-12, before it cost anything).
  let pool = offers.filter((o) => (o.gpu_ram || 0) / 1024 >= needVram);
  if (!pool.length) continue;
  if (region.toLowerCase() !== 'any') {
    const inRegion = pool.filter((o) => String(o.geolocation || '').toUpperCase().includes(region.toUpperCase()));
    if (inRegion.length) pool = inRegion;
  }
  const o = pool[0];
  const est = secondsFor(gpu);
  if (!est) continue;
  const hours = (est.seconds * count) / 3600;
  rows.push({
    gpu, id: o.id, dph: o.dph_total, vram: Math.round((o.gpu_ram || 0) / 1024),
    geo: o.geolocation || '', rel: o.reliability2 ?? o.reliability ?? 0,
    secondsEach: est.seconds, source: est.source,
    hours, total: hours * o.dph_total,
  });
}

if (!rows.length) { console.error('no offers matched on any candidate card. Raise --max-price or lower --min-reliability.'); process.exit(1); }
rows.sort((a, b) => a.total - b.total);

const fmt = (n, w) => String(n).padStart(w);
console.log(`${'GPU'.padEnd(14)} ${'$/hr'.padStart(7)} ${'VRAM'.padStart(5)} ${'s/unit'.padStart(7)} ${'wall'.padStart(8)} ${'TOTAL'.padStart(8)}  src        offer`);
console.log('-'.repeat(92));
for (const r of rows.slice(0, top)) {
  const wall = r.hours >= 1 ? `${r.hours.toFixed(1)}h` : `${Math.round(r.hours * 60)}m`;
  console.log(`${r.gpu.padEnd(14)} ${fmt('$' + r.dph.toFixed(3), 7)} ${fmt(r.vram + 'G', 5)} ${fmt(Math.round(r.secondsEach), 7)} ${fmt(wall, 8)} ${fmt('$' + r.total.toFixed(2), 8)}  ${r.source.padEnd(9)}  ${r.id} ${r.geo}`);
}
const best = rows[0], fastest = [...rows].sort((a, b) => a.hours - b.hours)[0];
console.log(`\ncheapest for the job: ${best.gpu} — $${best.total.toFixed(2)} over ${best.hours < 1 ? Math.round(best.hours * 60) + 'm' : best.hours.toFixed(1) + 'h'}`);
if (fastest.gpu !== best.gpu) {
  console.log(`fastest:              ${fastest.gpu} — $${fastest.total.toFixed(2)} over ${fastest.hours < 1 ? Math.round(fastest.hours * 60) + 'm' : fastest.hours.toFixed(1) + 'h'}`);
}
console.log(`\nrent it:  node ${join(repoRoot(), 'tools/gpu-box.mjs')} up --gpu ${best.gpu} --max-price ${(best.dph * 1.15).toFixed(2)} --rent`);
console.log('(estimates marked "estimated" are scaled from the measured baseline — record a real timing on any new card.)');
