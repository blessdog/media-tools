// media-tools — repo-rooted .env access. Tools run from ANY cwd (foreign-cwd
// rule, CLAUDE.md §7), so the .env lives next to this file's parent dir and is
// resolved via import.meta.url — never process.cwd().
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

export function repoRoot() {
  return dirname(dirname(fileURLToPath(import.meta.url)));
}

export function envKey(name) {
  if (process.env[name]) return process.env[name];
  let text = '';
  try { text = readFileSync(join(repoRoot(), '.env'), 'utf8'); } catch {}
  const m = text.match(new RegExp(`^\\s*${name}\\s*=\\s*(.+?)\\s*$`, 'm'));
  if (m) return m[1].replace(/^["']|["']$/g, '');
  throw new Error(`${name} not set (env or ${join(repoRoot(), '.env')})`);
}
