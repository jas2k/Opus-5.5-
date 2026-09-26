// Проверка читаемости QR на кадрах: BarcodeDetector в Chrome (на macOS — Apple Vision).
//   node qrcheck.mjs frame1.png frame2.jpg ...
import http from 'node:http';
import fs from 'node:fs';
import puppeteer from 'puppeteer-core';

const files = process.argv.slice(2);
const server = http.createServer((req, res) => { res.writeHead(200, { 'Content-Type': 'text/html' }); res.end('<body></body>'); });
await new Promise(r => server.listen(0, '127.0.0.1', r));
const b = await puppeteer.launch({ executablePath: process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true,
  args: ['--enable-experimental-web-platform-features'] });
const p = await b.newPage();
await p.goto(`http://127.0.0.1:${server.address().port}/`);
for (const f of files) {
  const data = `data:image/${f.endsWith('.png') ? 'png' : 'jpeg'};base64,` + fs.readFileSync(f).toString('base64');
  const r = await p.evaluate(async (src) => {
    if (!('BarcodeDetector' in window)) return 'no BarcodeDetector';
    const img = new Image(); img.src = src; await img.decode();
    const out = {};
    for (const scale of [1, .5, .3]) {
      const c = document.createElement('canvas'); c.width = img.width * scale; c.height = img.height * scale;
      c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
      out[scale] = (await new BarcodeDetector({ formats: ['qr_code'] }).detect(c)).map(x => x.rawValue);
    }
    return out;
  }, data);
  console.log(f.split('/').slice(-2).join('/'), JSON.stringify(r));
}
await b.close(); server.close();
