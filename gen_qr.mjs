// QR-матрица для финальной сцены → assets/qr.js (уровень H — центр можно закрыть логотипом)
import fs from 'node:fs';
import QRCode from 'qrcode';
const URL = process.argv[2] || 'https://t.me/StriverDev';
const q = QRCode.create(URL, { errorCorrectionLevel: 'H' });
const n = q.modules.size, m = [];
for (let y = 0; y < n; y++) m.push([...Array(n)].map((_, x) => q.modules.get(y, x) ? 1 : 0));
fs.writeFileSync(new URL_('./assets/qr.js', import.meta.url), `window.QR_URL=${JSON.stringify(URL)};\nwindow.QR=${JSON.stringify(m)};\n`);
console.log(URL, `${n}x${n}`);
function URL_(p, b) { return new globalThis.URL(p, b); }
