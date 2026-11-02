// SKÚŠKA bod 15: porovná DNEŠNÉ správanie prehliadača (favHtml/favLoad/favError
// z index.html pred zmenou: Google s2 → pri ≤17 px Yandex) s výsledkom ikony.py.
// Použitie: node porovnaj.js vzorka.json porovnanie.json
const fs = require('fs');
const { chromium } = require('playwright-core');
const [, , vstup, vystup] = process.argv;
const skript = JSON.parse(fs.readFileSync(vstup, 'utf8')).hosty;
const hosty = Object.keys(skript);
const page_html = `<!doctype html><meta charset="utf-8"><body><script>
function favLoad(img){
  const st = img.dataset.st || 'g';
  if(st === 'g' && img.naturalWidth <= 17){ img.dataset.st = 'y'; img.src = 'https://favicon.yandex.net/favicon/' + img.dataset.host; return; }
  if(st === 'y' && img.naturalWidth <= 1){ done(img, 'none'); return; }
  done(img, 'ok');
}
function favError(img){
  if(img.dataset.st === 'y'){ img.dataset.st = 'done'; img.src = 'https://www.google.com/s2/favicons?domain=' + img.dataset.host + '&sz=64'; return; }
  done(img, 'error');
}
window.R = {};
function done(img, v){
  const src = img.currentSrc || img.src;
  R[img.dataset.host] = {vysledok: v, zdroj: src.includes('yandex') ? 'yandex' : 'google', sirka: img.naturalWidth};
}
</script>` + hosty.map(h => `<img src="https://www.google.com/s2/favicons?domain=${h}&sz=64" data-host="${h}" onload="favLoad(this)" onerror="favError(this)">`).join('');
(async () => {
  const b = await chromium.launch({ channel: 'chrome' });
  const p = await b.newPage();
  await p.setContent(page_html);
  const t0 = Date.now();
  while (Date.now() - t0 < 90000) {
    const n = await p.evaluate(() => Object.keys(R).length);
    if (n >= hosty.length) break;
    await p.waitForTimeout(1000);
  }
  const R = await p.evaluate(() => R);
  await b.close();
  const out = { zhoda: 0, rozdiel: [], skript_chyba: [], prehliadac_nedobehol: [] };
  for (const h of hosty) {
    const s = skript[h], q = R[h];
    if (!q) { out.prehliadac_nedobehol.push(h); continue; }
    if (s.chyba) { out.skript_chyba.push({ host: h, skript: s, prehliadac: q }); continue; }
    const rovnako = s.vysledok === q.vysledok && (s.vysledok === 'none' || (s.zdroj === q.zdroj && s.sirka === q.sirka));
    if (rovnako) out.zhoda++; else out.rozdiel.push({ host: h, skript: s, prehliadac: q });
  }
  out.spolu = hosty.length;
  out.prehliadac_suhrn = Object.values(R).reduce((a, q) => (a[q.vysledok + '/' + q.zdroj] = (a[q.vysledok + '/' + q.zdroj] || 0) + 1, a), {});
  fs.writeFileSync(vystup, JSON.stringify(out, null, 1));
  console.log(`POROVNANIE: spolu ${out.spolu}, zhoda ${out.zhoda}, rozdiel ${out.rozdiel.length}, ` +
              `chyba skriptu ${out.skript_chyba.length}, prehliadač nedobehol ${out.prehliadac_nedobehol.length}`);
  console.log('prehliadač:', JSON.stringify(out.prehliadac_suhrn));
  for (const r of out.rozdiel.concat(out.skript_chyba)) console.log('  ', JSON.stringify(r));
})().catch(e => { console.error(e); process.exit(1); });
