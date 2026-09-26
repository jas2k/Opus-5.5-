// Превью: thumb.html (16:9 + 9:16) и thumb-yt.html (16:9 для ролика «Opus 5.5 делает видео») → PNG + JPG.
//   node thumb.mjs [папка] [фильтр по имени]
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import puppeteer from 'puppeteer-core';

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.resolve(process.argv[2] || ROOT);
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.ttf': 'font/ttf', '.png': 'image/png', '.json': 'application/json' };
const server = http.createServer((req, res) => {
  const p = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));
  if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': MIME[path.extname(p)] || 'application/octet-stream' });
  fs.createReadStream(p).pipe(res);
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const browser = await puppeteer.launch({ executablePath: process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true,
  args: ['--hide-scrollbars', '--force-color-profile=srgb', '--font-render-hinting=none'] });
const JOBS = [
  ['thumb.html?v=h', 1920, 1080, 'Превью — YouTube 16x9 1920x1080'],
  ['thumb.html?v=v', 1080, 1920, 'Превью — вертикальное 1080x1920'],
  ['thumb-yt.html', 1920, 1080, 'Превью — Opus 5.5 делает видео 1920x1080'],
].filter(j => !process.argv[3] || j[3].includes(process.argv[3]));
for (const [url, w, h, name] of JOBS) {
  const page = await browser.newPage();
  await page.setViewport({ width: w, height: h, deviceScaleFactor: 1 });
  await page.goto(`http://127.0.0.1:${server.address().port}/${url}`, { waitUntil: 'load' });
  await page.evaluate(async () => { await Promise.all([...document.fonts].map(f => f.load())); await window.READY; });
  await page.screenshot({ path: path.join(OUT, name + '.png'), type: 'png' });
  await page.screenshot({ path: path.join(OUT, name + '.jpg'), type: 'jpeg', quality: 93 });
  // габариты ключевых блоков — чтобы ловить вылезание за края
  console.log(name, JSON.stringify(await page.evaluate(() => ['.hdr', '.t3d', '.cmp', '.pill', '.hero', '.phone', '.card16', '.duck'].flatMap(s =>
    [...document.querySelectorAll(s)].map(e => { const r = e.getBoundingClientRect(); return [s, Math.round(r.left), Math.round(r.top), Math.round(r.right), Math.round(r.bottom)]; })))));
}
await browser.close(); server.close();
