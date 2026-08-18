// Backfill sidecars for the nine frames rendered 2026-08-11 20:47-20:50, BEFORE
// generate-image learned to write them. Values are transcribed from that run's
// stdout JSON — seeds are exact; the rest are the settings that run used
// (style.json defaults at the time: lora 1.35, guidance 3.5, 20 steps).
// Marked reconstructed:true so nobody mistakes these for machine-written truth.
import { writeFileSync, existsSync, readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';

const SEEDS = { '00': 516905, '01': 117662, '02': 13302, '03': 646239, '04': 660730,
  '05': 7834, '06': 957447, '07': 862453, '08': 54934 };
const SWATCH = '/Users/SSDrive/projects/media-tools/styles/inkwash/reference/LOCKED-inkwash-texture-1.png';
const sha = (p) => createHash('sha256').update(readFileSync(p)).digest('hex').slice(0, 16);
const STYLE_PREFIX = JSON.parse(readFileSync('/Users/SSDrive/projects/media-tools/styles/inkwash/style.json', 'utf8')).prompt;

for (const [n, seed] of Object.entries(SEEDS)) {
  const png = `renders/shot-${n}.png`;
  if (!existsSync(png)) { console.error(`missing ${png}`); continue; }
  const scene = execFileSync('./dephoto.sh', [`regen/shot-${n}.txt`], { encoding: 'utf8' }).trim();
  writeFileSync(`${png}.json`, JSON.stringify({
    reconstructed: true,
    reconstructedNote: 'Written after the fact from the run stdout. Seed is exact; settings are that run\'s style.json defaults. Not machine-recorded.',
    tool: 'generate-image', provider: 'comfy', renderer: 'uso-inkwash', style: 'inkwash',
    model: { checkpoint: 'flux1-dev-fp8.safetensors', lora: 'uso-flux1-dit-lora-v1.safetensors',
      loraStrength: 1.35, modelPatch: 'uso-flux1-projector-v1.safetensors',
      clipVision: 'sigclip_vision_patch14_384.safetensors' },
    sampler: { seed, steps: 20, guidance: 3.5, cfg: 1.0, sampler: 'euler', scheduler: 'simple', denoise: 1.0 },
    frame: { width: 1152, height: 640 },
    channels: {
      style: { file: SWATCH, sha256: sha(SWATCH) },
      identity: null,
      scene: { text: `${STYLE_PREFIX} ${scene}`, stylePrefix: STYLE_PREFIX, yourPrompt: scene },
    },
    source: { describedFrom: 'source.mp4', shotScript: `regen/shot-${n}.txt`, filteredBy: 'dephoto.sh' },
    out: png,
  }, null, 2));
  console.log(`wrote ${png}.json  seed ${seed}`);
}
