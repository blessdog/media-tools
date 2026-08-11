// media-tools — transcribe: audio/video file → diarized transcript.json. One job.
//
// Salvaged from cutwork/tools/transcribe-local.mjs 2026-08-11. POSTs the file
// BYTES straight to Deepgram, so the audio is never published to a public URL.
// DEEPGRAM ALWAYS — never Whisper, never ElevenLabs (locked decision).
//
// Nothing calls this implicitly. A tool that needs a transcript takes
// --transcript PATH; this is the only thing that makes one.

import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';
import { envKey } from './_env.mjs';

const DEEPGRAM_LISTEN_URL = 'https://api.deepgram.com/v1/listen';
const DEEPGRAM_MODEL = 'nova-3';
const DEEPGRAM_UTT_SPLIT = 1.2;

const HELP = `transcribe — audio/video file to a diarized, word-level transcript.json

usage: node transcribe.mjs <media-file> --out transcript.json

flags:
  <media-file>   (required, positional) mp3/wav/m4a/mp4 — bytes are POSTed directly
  --out PATH     (required) output transcript.json

output shape:
  { words: [{word,start,end,confidence,speaker}], utterances: [{start,end,text,speaker,confidence}] }

example:
  node ~/projects/media-tools/tools/transcribe.mjs interview.mp3 --out transcript.json`;

const args = process.argv.slice(2);
if (args.includes('--help') || args.length === 0) { console.log(HELP); process.exit(0); }
const flag = (n) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : undefined; };
const audioPath = args.find((a) => !a.startsWith('--') && args[args.indexOf(a) - 1] !== '--out');
const outPath = flag('--out');
if (!audioPath || !outPath) { console.error(HELP); process.exit(2); }

const dgUrl = DEEPGRAM_LISTEN_URL
  + `?model=${DEEPGRAM_MODEL}`
  + '&smart_format=true&punctuate=true&diarize=true&utterances=true'
  + `&utt_split=${DEEPGRAM_UTT_SPLIT}`;

const audio = readFileSync(audioPath);
console.error(`transcribe: ${audioPath} (${(audio.length / 1e6).toFixed(1)}MB) via Deepgram ${DEEPGRAM_MODEL}…`);
const t0 = Date.now();
const res = await fetch(dgUrl, {
  method: 'POST',
  headers: { Authorization: `Token ${envKey('DEEPGRAM_API_KEY')}`, 'Content-Type': 'audio/mpeg' },
  body: audio,
});
if (!res.ok) { console.error(`deepgram ${res.status}: ${(await res.text()).slice(0, 300)}`); process.exit(1); }
const data = await res.json();

const words = data?.results?.channels?.[0]?.alternatives?.[0]?.words ?? [];
const utterances = (data?.results?.utterances ?? []).map((u) => ({
  start: u.start, end: u.end, text: u.transcript, speaker: u.speaker ?? 0, confidence: u.confidence,
}));

mkdirSync(dirname(outPath), { recursive: true });
writeFileSync(outPath, JSON.stringify({ words, utterances }, null, 2));
console.error(`✓ ${((Date.now() - t0) / 1000).toFixed(1)}s`);
console.log(JSON.stringify({
  out: outPath,
  words: words.length,
  utterances: utterances.length,
  speakers: new Set(utterances.map((u) => u.speaker)).size,
  duration: Number((utterances.at(-1)?.end ?? 0).toFixed(1)),
}));
