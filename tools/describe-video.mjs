// media-tools — describe-video: a video → a shot-by-shot written script. One job.
//
// The counterpart to transcribe. transcribe turns AUDIO into words; this turns
// PICTURES into words. Needed because plenty of footage has no dialogue at all
// (music videos, b-roll, silent archive) — proven 2026-08-11 on a 43s clip whose
// audio ran at -9dB but returned zero words from Deepgram: loud, but no speech.
//
// ffmpeg detects shot cuts, one representative frame is pulled per shot, and a
// vision model describes each. Output is shots.json — an editable script. Nothing
// downstream runs automatically: hand shots.json to restyle-video/generate-image
// per shot when YOU decide to, exactly like --transcript.

import { readFileSync, writeFileSync, mkdirSync, rmSync, readdirSync } from 'node:fs';
import { execFileSync, spawnSync } from 'node:child_process';
import { dirname, join } from 'node:path';
import { tmpdir } from 'node:os';
import { envKey } from './_env.mjs';

const OPENROUTER_CHAT_URL = 'https://openrouter.ai/api/v1/chat/completions';
const DEFAULT_MODEL = 'anthropic/claude-sonnet-4-6';

const HELP = `describe-video — shot-detect a video and describe each shot in words

usage: node describe-video.mjs --video in.mp4 --out shots.json [flags]

flags:
  --video PATH     (required) source video
  --out PATH       (required) output shots.json
  --threshold N    scene-cut sensitivity 0-1, lower = more cuts (default 0.3)
  --every N        ALSO sample a frame every N seconds (default 0 = off).
                   Use on footage with no hard cuts, e.g. one long handheld take.
  --model M        vision model via OpenRouter (default ${DEFAULT_MODEL})
  --style-notes T  extra direction for the descriptions
                   (e.g. "note lighting and camera distance")

output shape:
  { video, shots: [{ index, start, frame, description }] }

example:
  node ~/projects/media-tools/tools/describe-video.mjs --video clip.mp4 --out shots.json`;

const args = process.argv.slice(2);
if (args.includes('--help') || args.length === 0) { console.log(HELP); process.exit(0); }
const flag = (n, d) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : d; };
const video = flag('--video');
const out = flag('--out');
if (!video || !out) { console.error(HELP); process.exit(2); }
const threshold = parseFloat(flag('--threshold', '0.3'));
const every = parseFloat(flag('--every', '0'));
const model = flag('--model', DEFAULT_MODEL);
const styleNotes = flag('--style-notes', '');

const work = join(tmpdir(), `describe-${process.pid}`);
rmSync(work, { recursive: true, force: true });
mkdirSync(work, { recursive: true });

// ffmpeg's showinfo prints pts_time for every frame the scene filter passes.
console.error(`describe-video: detecting shots (threshold ${threshold})…`);
let times = [];
try {
  const log = execFileSync('ffmpeg', ['-hide_banner', '-i', video,
    '-filter:v', `select='gt(scene,${threshold})',showinfo`, '-vsync', '0', '-f', 'null', '-'],
    { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
  times = [...log.matchAll(/pts_time:([0-9.]+)/g)].map((m) => parseFloat(m[1]));
} catch (e) {
  times = [...(e.stderr || '').matchAll(/pts_time:([0-9.]+)/g)].map((m) => parseFloat(m[1]));
}
times.unshift(0); // the opening shot is never a "cut"

if (every > 0) {
  const dur = parseFloat(execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration',
    '-of', 'default=nw=1:nk=1', video], { encoding: 'utf8' }).trim());
  for (let t = every; t < dur; t += every) times.push(t);
}
times = [...new Set(times.map((t) => Number(t.toFixed(2))))].sort((a, b) => a - b);
// Drop cuts closer than 0.5s — flashes and whip-pans, not shots.
times = times.filter((t, i) => i === 0 || t - times[i - 1] >= 0.5);
console.error(`  ${times.length} shots`);

// Fades and cuts-to-black land on frames with nothing in them. Describing those
// burns a vision call to be told "the frame is black" — measured on the first
// real run, 2 of 11 shots. Measure mean luma and drop them.
// signalstats writes to STDERR, not stdout — execFileSync's return value is
// stdout only, so reading it always came back empty and nothing was ever
// dropped. spawnSync gives both streams.
function meanLuma(path) {
  const r = spawnSync('ffmpeg', ['-hide_banner', '-i', path, '-vf', 'signalstats,metadata=print',
    '-f', 'null', '-'], { encoding: 'utf8' });
  const m = `${r.stderr || ''}${r.stdout || ''}`.match(/YAVG=([0-9.]+)/);
  return m ? parseFloat(m[1]) : 255;
}

const frames = [];
let dropped = 0;
times.forEach((t, i) => {
  const f = join(work, `${String(i).padStart(3, '0')}.jpg`);
  execFileSync('ffmpeg', ['-y', '-hide_banner', '-loglevel', 'error', '-ss', String(t),
    '-i', video, '-frames:v', '1', '-vf', 'scale=768:-1', '-q:v', '3', f]);
  if (meanLuma(f) < 16) { dropped++; return; }
  frames.push({ index: frames.length, start: t, frame: f });
});
if (dropped) console.error(`  dropped ${dropped} black frame(s)`);

const key = envKey('OPENROUTER_API_KEY');
const SYSTEM = `You describe single frames from a video so a director can rebuild the shot from words alone.
For each frame give ONE dense paragraph covering, in this order: shot size (extreme close-up/close-up/medium/wide), subject and what they are doing, wardrobe, setting, lighting (direction, colour, hardness), and camera angle.
Write plain declarative description. No interpretation, no mood adjectives, no "this image shows".${styleNotes ? `\nAlso: ${styleNotes}` : ''}`;

console.error(`describing ${frames.length} shots via ${model}…`);
const shots = [];
for (const f of frames) {
  const b64 = readFileSync(f.frame).toString('base64');
  const r = await fetch(OPENROUTER_CHAT_URL, {
    method: 'POST',
    headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model,
      messages: [
        { role: 'system', content: SYSTEM },
        { role: 'user', content: [
          { type: 'text', text: `Shot ${f.index} at ${f.start}s. Describe it.` },
          { type: 'image_url', image_url: { url: `data:image/jpeg;base64,${b64}` } },
        ] },
      ],
    }),
  });
  const j = await r.json();
  if (!r.ok) { console.error(`openrouter ${r.status}: ${JSON.stringify(j).slice(0, 300)}`); process.exit(1); }
  const description = j?.choices?.[0]?.message?.content?.trim() || '';
  shots.push({ index: f.index, start: f.start, description });
  console.error(`  [${f.index + 1}/${frames.length}] ${f.start}s — ${description.slice(0, 70)}…`);
}

mkdirSync(dirname(out), { recursive: true });
writeFileSync(out, JSON.stringify({ video, model, shots }, null, 2));
rmSync(work, { recursive: true, force: true });
console.log(JSON.stringify({ out, shots: shots.length, model }));
