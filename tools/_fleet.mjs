// Bongpot — fleet plumbing shared by shard-clips.mjs / shard-stills.mjs.
//
// Discover running Vast boxes, open one SSH tunnel per box (via vast.mjs forward —
// the proven no-shell-footgun path), wait until each ComfyUI answers, hand the
// caller a per-box local port, and guarantee tunnel teardown.

import { readFileSync } from 'node:fs';
import { execFileSync, spawn } from 'node:child_process';

const env = (() => { try { return readFileSync('.env', 'utf8'); } catch { return ''; } })();
const VAST_API_KEY = (env.match(/^VAST_API_KEY=(.+)$/m) || [])[1]?.trim() || process.env.VAST_API_KEY;

// Running instances, optionally filtered to an id allow-list.
export function discoverRunning(onlyIds) {
  if (!VAST_API_KEY) throw new Error('VAST_API_KEY not in .env');
  const raw = JSON.parse(execFileSync('vastai', ['show', 'instances-v1', '--raw', '--api-key', VAST_API_KEY], { encoding: 'utf8' }));
  return (Array.isArray(raw) ? raw : raw.instances || [])
    .filter((i) => i.actual_status === 'running' && i.intended_status !== 'stopped')
    .filter((i) => !onlyIds || onlyIds.includes(String(i.id)));
}

async function waitComfy(port, instId, child, timeoutMs = 45000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (child.exitCode !== null) throw new Error(`tunnel to ${instId} exited (code ${child.exitCode})`);
    try {
      const r = await fetch(`http://127.0.0.1:${port}/system_stats`, { signal: AbortSignal.timeout(3000) });
      if (r.ok) return;
    } catch {}
    await new Promise((r) => setTimeout(r, 1500));
  }
  throw new Error(`ComfyUI on instance ${instId} (local :${port}) never answered — provisioning finished? (vast.mjs run --id ${instId} --cmd 'cat /var/log/prov.marker /var/log/models.marker')`);
}

// Open a tunnel per instance (local ports base, base+1, …), wait for every ComfyUI,
// run fn([{inst, port}, …]), and tear the tunnels down no matter how fn exits.
export async function withTunnels(instances, basePort, fn) {
  const tunnels = [];
  const kill = () => { for (const t of tunnels) try { t.kill(); } catch {} };
  process.on('SIGINT', () => { kill(); process.exit(130); });
  const boxes = instances.map((inst, i) => {
    const port = basePort + i;
    tunnels.push(spawn('node', ['tools/vast.mjs', 'forward', '--id', String(inst.id), '--port', String(port)], { stdio: 'ignore' }));
    return { inst, port };
  });
  try {
    await Promise.all(boxes.map((b, i) => waitComfy(b.port, b.inst.id, tunnels[i])));
    return await fn(boxes);
  } finally { kill(); }
}

// Spawn a child process per box with [instanceId]-prefixed line output; resolve all.
export function runShards(cmds) {
  return Promise.all(cmds.map(({ args, tag, env: extraEnv }) => new Promise((resolve) => {
    const c = spawn('node', args, { env: { ...process.env, ...extraEnv } });
    const pipe = (s) => s.on('data', (d) => process.stdout.write(String(d).split('\n').filter(Boolean).map((l) => `[${tag}] ${l}`).join('\n') + '\n'));
    pipe(c.stdout); pipe(c.stderr);
    c.on('exit', (code) => resolve({ tag, code }));
  })));
}
