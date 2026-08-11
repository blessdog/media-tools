// media-tools — stitch: an ordered clip list → one normalized video. One job.
//
// Salvaged core of clipsmith/tools/stitch.mjs (normalize → concat → music duck).
// Its hardcoded TIMELINE, title cards and per-act grades were lane content and
// stayed behind: this takes the order from a list file YOU write.
//
// No API, no keys. ffmpeg only.

import { readFileSync, writeFileSync, mkdirSync, existsSync, rmSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { join, resolve, dirname } from 'node:path';
import { tmpdir } from 'node:os';

const HELP = `stitch — concatenate clips into one video, normalized to a uniform format

usage: node stitch.mjs --list shots.txt --out final.mp4 [flags]

flags:
  --list PATH    (required) text file: one clip path per line, # comments ok.
                 Relative paths resolve against the LIST file's directory.
  --out PATH     (required) output video
  --music PATH   music bed, ducked to 0.18 under clip audio
  --width N      default 1920
  --height N     default 1080
  --fps N        default 30

Clips are letterboxed (never cropped) to the target frame, given silent audio if
they have none, then stream-copy concatenated — uniform codec/size/fps makes
that safe.

example:
  node ~/projects/media-tools/tools/stitch.mjs --list shots.txt --music bed.mp3 --out cut.mp4`;

const args = process.argv.slice(2);
if (args.includes('--help') || args.length === 0) { console.log(HELP); process.exit(0); }
const flag = (n, d) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : d; };
const listPath = flag('--list');
const outPath = flag('--out');
if (!listPath || !outPath) { console.error(HELP); process.exit(2); }
const music = flag('--music');
const W = parseInt(flag('--width', '1920'), 10);
const H = parseInt(flag('--height', '1080'), 10);
const FPS = parseInt(flag('--fps', '30'), 10);

const clips = readFileSync(listPath, 'utf8').split('\n')
  .map((l) => l.trim()).filter((l) => l && !l.startsWith('#'))
  .map((l) => resolve(dirname(resolve(listPath)), l));
if (!clips.length) { console.error(`no clips in ${listPath}`); process.exit(1); }
const missing = clips.filter((c) => !existsSync(c));
if (missing.length) { console.error(`missing clips:\n  ${missing.join('\n  ')}`); process.exit(1); }

const segDir = join(tmpdir(), `stitch-${process.pid}`);
rmSync(segDir, { recursive: true, force: true });
mkdirSync(segDir, { recursive: true });
const ff = (a) => execFileSync('ffmpeg', ['-y', '-hide_banner', '-loglevel', 'error', ...a]);

console.error(`stitch: ${clips.length} clips → ${W}x${H}@${FPS} → ${outPath}`);
clips.forEach((src, n) => {
  const seg = join(segDir, `${String(n).padStart(3, '0')}.mp4`);
  const vf = [
    `scale=${W}:${H}:force_original_aspect_ratio=decrease`,
    `pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2:black`,
    `fps=${FPS},setsar=1`,
  ].join(',');
  ff(['-i', src, '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo',
    '-map', '0:v:0', '-map', '1:a:0?', '-map', '0:a:0?',
    '-vf', vf, '-c:v', 'libx264', '-crf', '20', '-pix_fmt', 'yuv420p',
    '-c:a', 'aac', '-ar', '48000', '-ac', '2', '-shortest', seg]);
  console.error(`  ✓ ${n + 1}/${clips.length} ${src}`);
});

const listFile = join(segDir, 'concat.txt');
writeFileSync(listFile, clips.map((_, n) => `file '${join(segDir, `${String(n).padStart(3, '0')}.mp4`)}'`).join('\n'));
mkdirSync(dirname(resolve(outPath)), { recursive: true });

if (music && existsSync(music)) {
  const tmp = join(segDir, '_concat.mp4');
  ff(['-f', 'concat', '-safe', '0', '-i', listFile, '-c', 'copy', tmp]);
  ff(['-i', tmp, '-i', music,
    '-filter_complex', '[1:a]volume=0.18[m];[0:a][m]amix=inputs=2:duration=first:dropout_transition=2[a]',
    '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-shortest',
    '-movflags', '+faststart', outPath]);
} else {
  ff(['-f', 'concat', '-safe', '0', '-i', listFile, '-c', 'copy', '-movflags', '+faststart', outPath]);
}
rmSync(segDir, { recursive: true, force: true });

const dur = execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration',
  '-of', 'default=nw=1:nk=1', outPath], { encoding: 'utf8' }).trim();
console.log(JSON.stringify({ out: outPath, clips: clips.length, width: W, height: H, fps: FPS, duration: Number(Number(dur).toFixed(2)), music: music || null }));
