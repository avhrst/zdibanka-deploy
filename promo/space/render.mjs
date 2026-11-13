// Renders space.html frame by frame through the Chrome DevTools protocol and pipes JPEG frames into ffmpeg.
// usage: node render.mjs out.mp4 [firstFrame lastFrame]   |   node render.mjs --stills dir 30,120,...
import { spawn } from 'node:child_process';
import { mkdtempSync, writeFileSync, mkdirSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';

const args = process.argv.slice(2), PORT = 9377;
const page = 'file://' + path.resolve('space.html');
const chrome = spawn('chromium', ['--headless=new', '--disable-gpu', '--hide-scrollbars', '--window-size=1920,1080', '--allow-file-access-from-files',
  `--remote-debugging-port=${PORT}`, `--user-data-dir=${mkdtempSync(path.join(tmpdir(), 'trailer-'))}`, page], { stdio: 'ignore' });
let ws, id = 0; const pending = new Map();
const send = (method, params = {}) => new Promise((res, rej) => { const i = ++id; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params })); });
const evalJs = async (expression) => { const r = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true }); if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails)); return r.result.value; };
try {
  let target;
  for (let k = 0; k < 100 && !target; k++) { await new Promise(r => setTimeout(r, 200)); try { target = (await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json()).find(t => t.type === 'page' && t.url.startsWith('file:')); } catch {} }
  if (!target) throw new Error('chromium did not start');
  ws = new WebSocket(target.webSocketDebuggerUrl);
  ws.onmessage = e => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.rej(new Error(m.error.message)) : p.res(m.result); } };
  await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; });
  for (let k = 0; k < 100; k++) { if (await evalJs('typeof window.ready !== "undefined"')) break; await new Promise(r => setTimeout(r, 200)); }
  console.log('fonts:', await evalJs('window.ready'));
  const total = await evalJs('window.totalFrames');
  const frame = async i => Buffer.from((await evalJs(`renderFrame(${i})`)).split(',')[1], 'base64');
  if (args[0] === '--stills') {
    const want = new Set(args[2].split(',').map(Number)); mkdirSync(args[1], { recursive: true });
    const last = Math.max(...want);
    for (let i = 0; i <= last && i < total; i++) { const buf = await frame(i); if (want.has(i)) writeFileSync(path.join(args[1], `f${String(i).padStart(4, '0')}.jpg`), buf); }
    console.log('stills done');
  } else {
    const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', '30', '-c:v', 'mjpeg', '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '19', '-pix_fmt', 'yuv420p', '-r', '30', args[0]], { stdio: ['pipe', 'inherit', 'inherit'] });
    const t0 = Date.now();
    for (let i = 0; i < total; i++) { const buf = await frame(i); if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r)); if (i % 300 === 0) console.log(`frame ${i}/${total} ${((Date.now() - t0) / 1000).toFixed(0)}s`); }
    ff.stdin.end(); await new Promise(r => ff.on('close', r)); console.log('video done', total, 'frames');
  }
} finally { try { ws && ws.close(); } catch {} chrome.kill(); }
