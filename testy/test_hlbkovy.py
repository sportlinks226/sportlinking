#!/usr/bin/env python3
"""
HĹBKOVÝ TEST ŽIVÉHO WEBU — raz denne (sportlinky.sk aj sportlinking.com — ten istý súbor).

Spúšťa ho .github/workflows/test-hlbkovy.yml každé ráno (05:30 UTC, po nočných
buildoch) alebo ručne. Na rozdiel od testu po nasadení (testy/test_webu.py, skúša
pár stránok v prehliadači) prejde CELÝ web: všetky adresy zo sitemap.xml, ich
titulky, canonical a hreflang, páry SK ↔ EN, robots.txt, verziu dát, presmerovania,
ikonky a vlajky — a porovná adresy, titulky a obsah stránok (karty v poradí), ktoré
vyrába appka (index.html), s tými od generátora (generator.py). Nič nemení — web ani súbory v repozitári.

Jazyk webu sa nezisťuje z textov, ale zo štruktúry (<html lang>, hreflang),
takže ten istý súbor funguje na SK aj EN webe (Zadanie 24, body 20 a 15).

Výsledok (rovnako ako test_webu.py):
  ✅ OK         — kontrola prešla
  ⚠️ varovanie  — niečo nie je ideálne, ale web funguje (test ostane zelený)
  ❌ chyba      — web nefunguje, ako má (test skončí červeným krížikom)
Každá kontrola sa pri neúspechu skúsi ešte raz (pri sťahovaní stránok sa
opakuje len každá neúspešná adresa).

KONTROLY
  a) sitemap.xml: platné XML, bez duplicít, všetky <loc> patria na --url, VŠETKY
     adresy vrátia HTTP 200 (8 naraz, neúspešná adresa ešte raz) — inak ❌.
  b) Každá stránka zo sitemapy (statické HTML): <title>, canonical = adresa zo
     sitemapy, hreflang sk/en/x-default (vlastný jazyk = canonical, druhý jazyk
     na druhom webe, x-default = en). Páry SK ↔ EN: adresa druhého jazyka vráti
     200 a jej hreflang ukazuje späť (pri odhade nad 10 min len vzorka 200) — ❌.
  c) robots.txt: HTTP 200, odkaz na sitemap.xml, neblokuje celý web — ❌.
  d) Verzia dát: SK web — data-full.json na webe = data.json v repozitári (main)
     → inak ❌; EN web — data.json na webe = data-full.json na SK webe → inak ⚠️
     (EN web môže ešte čakať na svoj build).
  e) Presmerovania http → https a www → bez www (aj hlbšia adresa) — ❌;
     keď www v DNS neexistuje, len ⚠️.
  f) Ikonky /ikony/<host>.png pre 200 náhodných webov z data.json — chýbajúce
     len ⚠️ (časť webov ikonku nemá); vlajky: 30 náhodných z /vlajky/ → 200, inak ❌.
  g) Zrkadlové funkcie appka ↔ generátor (bod 15): appka v prehliadači vypočíta
     adresu a titulok VŠETKÝCH priečinkov (svojimi vlastnými funkciami urlForId
     a updateHead — slugify, nodeSlugBase, _slugFix, _titleNoSport, liveTitle);
     porovnanie so sitemap.xml a <title> statických stránok — rozdiel = ❌.
     Stránky, ktoré generátor zámerne vynecháva (prázdne priečinky, enOnly /
     en:false, Aktuálne bez položiek), sa nehlásia — len ich počet.
  h) Obsah stránok appka ↔ statika (previerka 3, bod 41): pre VŠETKY stránky priečinkov
     zoznam a PORADIE kariet — appka (tileKids: priečinky, potom linky — tak ich kreslí
     renderLevel) proti kartám statickej stránky. Statické karty nemajú id, párujú sa
     podľa poradia: karta priečinka = adresa jeho stránky, karta linky = adresa linky
     (safeUrl / safe_url). Porovnáva sa ZOZNAM v poradí (nie množina), takže duplicitné
     linky v jednom priečinku nič nepokazia. Pri kartách priečinkov sa porovnáva aj text
     počtov „X sekcií · Y liniek“ (bod 27 previerky 3: folderCountText ↔ folder_count_text).
     Stránky sa znova nesťahujú (berú sa z kontroly a). Pri odhade nad 10 min len náhodná vzorka 200 stránok. Rozdiel = ❌;
     výnimka: stránka Aktuálne (Live This Week) — statické HTML je z nočného buildu,
     appka počíta s dnešným dátumom (položka mohla medzitým začať/skončiť) → len ⚠️.
     Zámerné rozdiely sa nehlásia, lebo ich robia obe strany rovnako: enOnly / en:false
     (skryté v danom jazyku), prázdne priečinky (bez karty aj bez stránky), Aktuálne bez
     položiek (stránka nie je). Domov sa neporovnáva (dlaždice, lišta Aktuálne s „+N ›",
     bannery) — ten kontroluje test_webu.py.
  i) Mobilné zariadenia — Android + iPhone (Zadanie 48a, 82 % návštev je z mobilu). Strážia
     opravy zo Zadania 47b. Prehliadače: Chromium s mobilným UA = Android, WebKit (jadro Safari)
     = iPhone; všetko is_mobile + has_touch, správne DPR. Zariadenia (každé je samostatný riadok
     a pri ❌ sa skúsi ešte raz samo):
       A Android 360×800 (DPR 3) · B Android s veľkým písmom 130 % (stránka „vidí“ 277×615, DPR 3,9
       — ako nový Chrome) · C Android na šírku 800×360 · D iPhone SE 375×667 (DPR 2) · E iPhone 15
       393×852 (DPR 3) · E′ iPhone 15 na šírku 852×393 · F pomalý Android (A + procesor 4× +
       „Slow 4G“ — len meranie výkonu).
     Stránky: domov, šport, krajina (Slovensko), liga s dlhými názvami (MOL liga ženy), Bangladéš,
     Správy & Médiá, Aktuálne, Tipovanie (len SK), vyhľadávanie („slovan“, „brondby“, nič sa
     nenašlo) — adresy vypočíta appka (urlForId), takže na EN webe vyjde /football/ atď.; navyše
     denne iná náhodná vzorka 12 hlbokých stránok zo sitemap.xml na A aj na E (len pretečenie a
     konzola — za pár týždňov sa prejde celý web). Na C a E′ (na šírku) len domov, liga, Bangladéš,
     hľadanie, hlavička, admin (C aj panel obľúbených).
     ❌: vodorovné pretečenie (stránka sa hýbe do strany); chyby v konzole a porušenia CSP; appka
     neprevezme stránku; Späť (A, E): domov → šport → krajina → liga, na lige Späť pri otvorenom
     paneli obľúbených len zavrie panel, potom 3× Späť krok po kroku s obnoveným posunom; písmo
     v hľadaní < 16 px (iPhone by priblížil) aj na šírku; hlavička sa po posune nezbalí (aj na
     šírku), lupa v zbalenej hlavičke nie je celá na obrazovke, na B „☆ N“ nie je vedľa loga;
     okno s heslom (/#admin, BEZ prihlásenia) sa nezmestí / nejde zavrieť / na šírku nie je hore;
     panel obľúbených (2× ★ len v prehliadači testu) sa nezmestí / nejde zavrieť krížikom.
     ⚠️: dotykové plochy pod mierou zo 47b (★ 44×36, FB/IG 36×36 kde to výška karty dovolí,
     drobčeky výška 32, „+N ›“ 44×32, krížiky 44×44 — zoznam s rozmermi v Summary); písmo < 12 px
     (štítok LIGA/LEAGUE smie byť menší); kontrast počítadla a „LINKY“ v logu < 4,5 : 1; štítok
     LIGA prekrýva názov (B); plná hlavička > 30 % výšky; Safari (WebKit) stiahne index.html viac
     ako raz; výkon na F (domov a krajina „z Googlu“) horší ako prahy MOBIL_PRAH_* (z merania 47a
     s rezervou). Reklama Tipsport a GoatCounter BLOKOVANÉ (BLOKOVANE) — žiadne falošné zobrazenia
     ani návštevy; na Tipovaní sa kontroluje len pretečenie (prázdny/zbalený slot nič nerozbije).
     Snímky (zmenšené, CSS pixely): z každého zariadenia domov, liga, hľadanie (aj keď je všetko
     OK) + miesto chyby → príloha „test-hlbkovy“. V Summary tabuľka zariadenie × stránka.

  j) Web ako aplikácia (Zadanie 50, PWA): ak je manifest.webmanifest na webe, VŠETKY stránky zo
     sitemapy (stiahnuté v a) majú <link rel="manifest"> a theme-color, /sw.js vráti 200 ako
     JavaScript a ikonky z manifestu 200 — inak ❌. Bez PWA (starý web) aj vypnuté PWA (PWA = False:
     samozničujúci sw.js, stránky bez manifestu) = ✅ s poznámkou. Všetky prehliadačové kontroly
     (g, h, i) bežia BEZ service workera (SW_VYP_SKRIPT) — merajú prvú návštevu ako doteraz.

Spustenie (lokálne):  python testy/test_hlbkovy.py --url https://sportlinky.sk/
Voliteľne:  --vystup test-hlbkovy-vystup   (priečinok na zoznam chýb)
            --len-mobil                    (len kontrola i) — rýchlo po zmene webu; aj LEN_MOBIL=áno)
            --zariadenia A,E,F             (i) len vybrané zariadenia)
Lokálne skúšanie: CHROMIUM_PATH = vlastný Chromium; MOBIL_SK_ZDROJ = adresa kópie SK webu, odkiaľ
si EN web berie Aktuálne (inak https://sportlinky.sk/).
Premenná REPO_DATA_JSON = cesta k data.json z repozitára (kontrola d na SK webe,
predvolene data.json v aktuálnom priečinku). Zhrnutie sa zapíše aj do súboru
z premennej GITHUB_STEP_SUMMARY (stránka behu v Actions).
"""

import argparse
import collections
import html
import json
import os
import random
import re
import socket
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

# ---------------------------------------------------------------- nastavenia
# UA_PC, X_TEST, BLOKOVANE (štatistiky a reklamy sa v teste BLOKUJÚ — žiadne falošné
# návštevy ani zobrazenia reklám), Zlyhanie, titulok_z_html, meta_z_html: testy/_spolocne.py
from _spolocne import BLOKOVANE, SW_VYP_SKRIPT, UA_PC, X_TEST, Zlyhanie, meta_z_html, titulok_z_html   # spoločné (Zadanie 36)

NARAZ = 8                   # toľko stránok sa sťahuje naraz (slušne, nie záťažový test)
TIMEOUT_S = 30              # max. čas na jednu adresu
MAX_VYPIS = 30              # v zhrnutí sa vypíše najviac toľko chýb jednej kontroly
PARY_MAX_S = 600            # páry SK ↔ EN: ak by trvali dlhšie (odhad), len vzorka …
PARY_VZORKA = 200           # … s toľkými stránkami
OBSAH_MAX_S = 600           # h) obsah appka ↔ statika: ak by trval dlhšie (odhad), len vzorka …
OBSAH_VZORKA = 200          # … s toľkými stránkami
OBSAH_DAVKA = 100           # h) toľko stránok naraz vypočíta appka v prehliadači
IKONY_VZORKA = 200          # náhodných webov (hostov) pre kontrolu ikoniek
VLAJKY_VZORKA = 30          # náhodných vlajok
SK_MASTER = "https://sportlinky.sk/"    # hlavná kópia dát (EN web si berie data-full.json odtiaľto)
SM_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
# rovnaké pravidlá ako ikony.py / favHtml() v index.html — týmto webom sa ikonka nesťahuje
SOCIAL_FAV = re.compile(r'(^|\.)(facebook\.com|fb\.com|instagram\.com|x\.com|twitter\.com|youtube\.com|youtu\.be|tiktok\.com|wikipedia\.org)$')
NO_FAVICON_HOSTS = re.compile(r'(^|\.)(vereine\.oefb\.at|vereine\.fussballoesterreich\.at)$')
SAFE_HOST = re.compile(r'^[a-z0-9](?:[a-z0-9-]{0,62})(?:\.[a-z0-9-]{1,63})*$')
VLAJKA_RE = re.compile(r'[^"\s,]*/vlajky/\d+x\d+/[a-z0-9_-]+\.png')

# ---------------------------------------------------------------- i) mobil (Zadanie 48a)
UA_ANDROID = ("Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36")
UA_IPHONE = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
             "(KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1")
# pevné stránky: kľúč → (id priečinka v data.json, názov stĺpca). Adresu vypočíta appka
# (urlForId), takže na EN webe vyjde /football/, /live-this-week/ … (LIVE = stránka Aktuálne).
MOBIL_STRANKY = {
    "sport": ("f_fut", "Šport"), "krajina": ("f_fut_klu_eu_svk", "Krajina"),
    "liga": ("f_had_cze_l3", "Liga (MOL ženy)"), "bangl": ("f_bgd_l1", "Bangladéš"),
    "spravy": ("f_med", "Správy & Médiá"), "aktualne": ("LIVE", "Aktuálne"),
    "tipovanie": ("f_tip", "Tipovanie"), "spat_liga": ("f_svk_l1", "liga pre Späť"),
}
# stĺpce tabuľky v Summary (v tomto poradí)
MOBIL_STLPCE = {"domov": "Domov", **{k: v for k, (_, v) in MOBIL_STRANKY.items() if k != "spat_liga"},
                "hladanie": "Hľadanie", "hlavicka": "Hlavička", "spat": "Späť", "admin": "Admin",
                "oblubene": "Obľúbené", "plochy": "Dotyk ⚠️", "vzorka": "Vzorka"}
_VSETKY = ["domov", "sport", "krajina", "liga", "bangl", "spravy", "aktualne", "tipovanie", "hladanie"]
_NA_SIRKU = ["domov", "liga", "bangl", "hladanie"]
# B = Android s veľkým systémovým písmom 130 %: nový Chrome ho prenáša do priblíženia
# stránky — stránka „vidí“ displej 360 / 1,3 = 277 px (výška 800 / 1,3 = 615), DPR 3 × 1,3
# (rovnaká simulácia ako v Zadaní 47a/47b).
MOBIL_ZARIADENIA = [
    {"kod": "A", "nazov": "Android malý 360×800", "prehliadac": "chromium", "okno": (360, 800), "dpr": 3,
     "ua": UA_ANDROID, "stranky": _VSETKY, "pismo": True, "kontrast": True, "admin": True, "spat": True, "oblubene": True},
    {"kod": "B", "nazov": "Android veľké písmo 130 % (277×615)", "prehliadac": "chromium", "okno": (277, 615), "dpr": 3.9,
     "ua": UA_ANDROID, "stranky": _VSETKY, "pismo": True, "kontrast": False, "admin": True, "spat": False, "oblubene": True},
    {"kod": "C", "nazov": "Android na šírku 800×360", "prehliadac": "chromium", "okno": (800, 360), "dpr": 3,
     "ua": UA_ANDROID, "stranky": _NA_SIRKU, "pismo": False, "kontrast": False, "admin": True, "spat": False, "oblubene": True},
    {"kod": "D", "nazov": "iPhone SE 375×667 (WebKit)", "prehliadac": "webkit", "okno": (375, 667), "dpr": 2,
     "ua": UA_IPHONE, "stranky": _VSETKY, "pismo": False, "kontrast": False, "admin": True, "spat": False, "oblubene": False},
    {"kod": "E", "nazov": "iPhone 15 393×852 (WebKit)", "prehliadac": "webkit", "okno": (393, 852), "dpr": 3,
     "ua": UA_IPHONE, "stranky": _VSETKY, "pismo": True, "kontrast": False, "admin": True, "spat": True, "oblubene": True},
    {"kod": "E′", "nazov": "iPhone 15 na šírku 852×393 (WebKit)", "prehliadac": "webkit", "okno": (852, 393), "dpr": 3,
     "ua": UA_IPHONE, "stranky": _NA_SIRKU, "pismo": False, "kontrast": False, "admin": True, "spat": False, "oblubene": False},
]
for _z in MOBIL_ZARIADENIA:   # názov súboru snímky bez znaku ′ (E′ → E2)
    _z["subor"] = _z["kod"].replace("′", "2")
MOBIL_POMALY = {"kod": "F", "nazov": "Android pomalý (A + procesor 4× + Slow 4G)", "okno": (360, 800), "dpr": 3, "ua": UA_ANDROID}
MOBIL_VZORKA = 12           # náhodných hlbokých stránok denne na A aj na E (iné na každom)
# „Slow 4G“ presne ako v DevTools (Chrome): 1,6 Mb/s dole, 750 kb/s hore, odozva 562,5 ms
SLOW_4G = {"offline": False, "latency": 562.5, "downloadThroughput": 180_000, "uploadThroughput": 84_375,
           "connectionType": "cellular4g"}
# prahy výkonu na F (⚠️, nie ❌) — Zadanie 47a namerala FCP 0,7–0,9 s, prevzatie domov
# 0,7–1,0 s / hlboká 2,3–2,9 s, celé dáta 9,4–13,8 s, stiahnuté 1,27–1,35 MB; prahy majú
# rezervu, lebo živý web kolíše
MOBIL_PRAH_FCP = 2.5
MOBIL_PRAH_APP_DOMOV = 3.0
MOBIL_PRAH_APP_HLBOKA = 6.0
MOBIL_PRAH_DATA = 20.0
MOBIL_PRAH_MB = 1.7

# appka prevzala stránku (statická stránka appku nemá)
MOBIL_APPKA = "() => typeof urlForId === 'function' && !!document.getElementById('srch') && !!document.getElementById('main')"
MOBIL_CELE_DATA = "() => typeof DB !== 'undefined' && !!DB && !!DB.nodes && DB.nodes.length > 100 && !DB._partial"
# ❌ 1) vodorovné pretečenie: šírka obsahu > obrazovka, alebo viditeľný prvok presahuje
# okraj obrazovky a nič ho neoreže (vodorovne posuvný pás Aktuálne ho oreže — to je OK)
MOBIL_PRETECENIE_JS = """(vw) => {
  const de = document.documentElement, b = document.body, out = [], hlasene = [];
  const popis = el => el.tagName.toLowerCase() + (el.id ? '#' + el.id : '')
    + (typeof el.className === 'string' && el.className.trim() ? '.' + el.className.trim().split(/\\s+/).slice(0, 2).join('.') : '');
  for (const el of b.querySelectorAll('*')) {
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) continue;
    if (!(r.right > vw + 1 && r.left < vw) && !(r.left < -1 && r.right > 0)) continue;
    if (hlasene.some(h => h.contains(el))) continue;
    if (getComputedStyle(el).visibility === 'hidden') continue;
    let p = el.parentElement, orez = false;
    while (p && p !== b) {
      const ps = getComputedStyle(p);
      if (ps.overflowX !== 'visible' || ps.clipPath !== 'none') {
        const pr = p.getBoundingClientRect();
        if (pr.right <= vw + 1 && pr.left >= -1) { orez = true; break; }
      }
      p = p.parentElement;
    }
    if (orez) continue;
    hlasene.push(el);
    out.push(popis(el) + ' (' + Math.round(r.left) + '–' + Math.round(r.right) + ' px)');
    if (out.length >= 4) break;
  }
  return {sw: Math.max(de.scrollWidth, b.scrollWidth), iw: innerWidth, prvky: out};
}"""
# ⚠️ 10) viditeľný text menší ako 12 px (štítok LIGA/SCORES/LEAGUE smie byť menší)
MOBIL_PISMO_JS = """() => {
  const out = new Set(), w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = w.nextNode())) {
    const t = n.nodeValue.trim();
    const el = n.parentElement;
    if (!t || !el || el.closest('.liga-tag, script, style, noscript, .sr-only, [hidden]')) continue;
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) continue;
    const s = getComputedStyle(el);
    if (s.visibility === 'hidden' || parseFloat(s.opacity) === 0) continue;
    const px = parseFloat(s.fontSize);
    if (px < 11.95) {
      const k = (typeof el.className === 'string' && el.className.trim() ? '.' + el.className.trim().split(/\\s+/)[0] : el.tagName.toLowerCase());
      out.add(k + ' „' + t.slice(0, 24) + '“ ' + px.toFixed(1) + ' px');
    }
  }
  return [...out];
}"""
# ⚠️ 10) kontrast čísla počítadla a „LINKY“ v logu proti pozadiu hlavičky (aj najsvetlejšej
# farbe jej prechodu)
MOBIL_KONTRAST_JS = """() => {
  const rgb = s => (s.match(/rgba?\\([^)]+\\)/g) || []).map(c => c.match(/[\\d.]+/g).map(Number)).filter(c => c.length < 4 || c[3] > 0);
  const lum = c => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
  const kontrast = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const out = [];
  for (const sel of ['#linkCount b', '.h-wordmark .wm-r']) {
    const el = document.querySelector(sel);
    if (!el || !el.getBoundingClientRect().width) continue;
    const fg = rgb(getComputedStyle(el).color)[0];
    let p = el, poz = [];
    while (p && !poz.length) { const s = getComputedStyle(p); poz = rgb(s.backgroundImage).concat(rgb(s.backgroundColor)); p = p.parentElement; }
    if (!fg || !poz.length) continue;
    out.push({text: el.textContent.trim().slice(0, 20), k: Math.min(...poz.map(c => kontrast(fg, c)))});
  }
  return out;
}"""
# ⚠️ 9) dotyková plocha = kam až ťuk naozaj trafí prvok (elementFromPoint od stredu na
# všetky 4 strany) — započíta aj neviditeľné zväčšenie (::before) a „mŕtvy“ pás nad ★
MOBIL_PLOCHY_JS = """() => {
  const out = [];
  const vid = el => el && el.getBoundingClientRect().width > 0 && getComputedStyle(el).visibility !== 'hidden';
  const plocha = el => {
    el.scrollIntoView({block: 'center'});
    const r = el.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    const ok = (x, y) => { const e = document.elementFromPoint(x, y); return !!e && (e === el || el.contains(e)); };
    if (!ok(cx, cy)) return null;
    let l = 0, p = 0, h = 0, d = 0;
    while (l < 80 && ok(cx - l - 1, cy)) l++;
    while (p < 80 && ok(cx + p + 1, cy)) p++;
    while (h < 80 && ok(cx, cy - h - 1)) h++;
    while (d < 80 && ok(cx, cy + d + 1)) d++;
    return [l + p + 1, h + d + 1];
  };
  const pridaj = (co, el, mw, mh) => { const s = plocha(el); if (s) out.push({co, w: s[0], h: s[1], mw, mh}); };
  [...document.querySelectorAll('#main .card-link > .star')].filter(vid).slice(0, 3).forEach(e => pridaj('★ na karte', e, 44, 36));
  [...document.querySelectorAll('#main .card-link .socs a.si')].filter(vid).slice(0, 4).forEach(e => {
    const k = e.closest('.card-link').getBoundingClientRect().height;   // FB hore + IG dole v jednej karte
    pridaj(/instagram/.test(e.href) ? 'IG na karte' : 'FB na karte', e, 36, Math.min(36, Math.floor(k / 2) - 1));
  });
  [...document.querySelectorAll('#breadcrumb a.bc-item')].filter(vid).slice(0, 2).forEach(e => pridaj('drobček', e, 0, 32));
  const plus = document.getElementById('aktMoreBadge');
  if (vid(plus) && getComputedStyle(plus).display !== 'none') pridaj('„+N ›“ pri Aktuálnych', plus, 44, 32);
  scrollTo(0, 0);
  return out;
}"""
# ⚠️ 11) štítok LIGA/LEAGUE prekrýva text názvu linky
MOBIL_STITOK_JS = """() => {
  const out = [];
  for (const c of document.querySelectorAll('#main .card-link')) {
    const t = c.querySelector(':scope > .liga-tag'), n = c.querySelector('.cl-name');
    if (!t || !n) continue;
    const tr = t.getBoundingClientRect(), rg = document.createRange();
    rg.selectNodeContents(n);
    for (const r of rg.getClientRects()) {
      if (r.width && r.right > tr.left + 0.5 && r.left < tr.right - 0.5 && r.bottom > tr.top + 0.5 && r.top < tr.bottom - 0.5) {
        out.push(n.textContent.trim().slice(0, 40)); break; }
    }
  }
  return out;
}"""
MOBIL_HLAVICKA_JS = """() => {
  const h = document.querySelector('header'), l = document.getElementById('hLupa').getBoundingClientRect(),
        f = document.getElementById('hFav').getBoundingClientRect(), g = document.querySelector('header .h-wordmark').getBoundingClientRect();
  return {min: document.body.classList.contains('hdr-min'), h: h.offsetHeight, vh: innerHeight,
          lupa: [Math.round(l.left), Math.round(l.right), Math.round(l.top), Math.round(l.bottom)].join('/') + ' px',
          lupaCela: l.width > 0 && l.left >= -0.5 && l.right <= innerWidth + 0.5 && l.top >= -0.5,
          favPriLogu: f.width > 0 && f.top < g.bottom && f.bottom > g.top};
}"""
# ⚠️ 13) meranie na F: čas od začiatku načítania (performance.now)
MOBIL_VYKON_JS = """() => { const p = performance.getEntriesByName('first-contentful-paint')[0];
  return {t: performance.now(), fcp: p ? p.startTime : null,
          app: typeof urlForId === 'function' && !!document.getElementById('srch'),
          full: typeof DB !== 'undefined' && !!DB && !!DB.nodes && DB.nodes.length > 100 && !DB._partial}; }"""


# ---------------------------------------------------------------- pomocníci
def uri(url):
    """Adresu s diakritikou (napr. /jemenská-liga/) zakóduje tak, ako to robí prehliadač
    (/jemensk%C3%A1-liga/) — urllib by ju inak vôbec neposlal."""
    c = urllib.parse.urlsplit(url)
    bezpecne = "/%:@!$&'()*+,;=-._~"
    return urllib.parse.urlunsplit((c.scheme, c.netloc.encode("idna").decode("ascii") if any(ord(x) > 127 for x in c.netloc) else c.netloc,
                                    urllib.parse.quote(c.path, safe=bezpecne),
                                    urllib.parse.quote(c.query, safe=bezpecne + "?"), c.fragment))


def stiahni(url, cache_bust=False, timeout=TIMEOUT_S, binarne=False):
    """Stiahne adresu bez prehliadača. Vráti (HTTP kód, hlavičky, text alebo bajty)."""
    if cache_bust:
        url += ("&" if "?" in url else "?") + "t=" + str(int(time.time() * 1000))
    req = urllib.request.Request(uri(url), headers={"User-Agent": UA_PC, **X_TEST})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            b = r.read()
            return r.status, r.headers, (b if binarne else b.decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        b = e.read()
        return e.code, e.headers, (b if binarne else b.decode("utf-8", "replace"))


class BezPresmerovania(urllib.request.HTTPRedirectHandler):
    """Presmerovanie sa NEnasleduje — test chce vidieť kód 301/308 a cieľ."""
    def redirect_request(self, *a, **k):
        return None


def presmerovanie(url):
    """Vráti (HTTP kód, cieľ z hlavičky Location) bez nasledovania presmerovania."""
    op = urllib.request.build_opener(BezPresmerovania)
    req = urllib.request.Request(uri(url), headers={"User-Agent": UA_PC, **X_TEST})
    try:
        with op.open(req, timeout=TIMEOUT_S) as r:
            return r.status, r.headers.get("Location", "")
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Location", "")


def host_z_url(url):
    """ROVNAKO ako host_z_url() v ikony.py: malé písmená, IDN v punycode, bez portu."""
    try:
        h = urllib.parse.urlsplit((url or "").strip()).hostname or ""
    except ValueError:
        return ""
    h = h.strip().lower()
    if not h:
        return ""
    if any(ord(c) > 127 for c in h):
        try:
            h = ".".join((p.encode("idna").decode("ascii") if any(ord(c) > 127 for c in p) else p)
                         for p in h.split("."))
        except UnicodeError:
            return ""
    return h


def atributy(tag):
    return {k.lower(): html.unescape(v) for k, v in re.findall(r'([a-zA-Z-]+)="([^"]*)"', tag)}


def hlavicka_stranky(text):
    """Z <head> statickej stránky (bez skriptov — v nich sú len texty kódu) vytiahne
    canonical a hreflang {jazyk: adresa}."""
    m = re.search(r"<head[^>]*>(.*?)</head>", text, re.S | re.I)
    head = re.sub(r"<script\b.*?</script>", "", m.group(1) if m else "", flags=re.S | re.I)
    canonical, hreflang = None, {}
    for tag in re.findall(r"<link\b[^>]*>", head, re.I):
        a = atributy(tag)
        rel = a.get("rel", "").lower()
        if rel == "canonical":
            canonical = a.get("href", "")
        elif rel == "alternate" and a.get("hreflang"):
            hreflang[a["hreflang"].lower()] = a.get("href", "")
    return canonical, hreflang


def id_stranky(text):
    """Id priečinka, z ktorého generátor stránku vyrobil (mini-balík pageBoot, pole full)."""
    m = re.search(r'<script[^>]*id="pageBoot"[^>]*>(.*?)</script>', text, re.S)
    if not m:
        return None
    try:
        full = json.loads(m.group(1)).get("full") or []
        return full[0] if full else None
    except (ValueError, AttributeError):
        return None


def karty_stranky(text, url):
    """h) Karty statickej stránky v poradí: ("f", cesta stránky priečinka, text počtov)
    alebo ("l", adresa linky, ""). Text počtov = <div class="ct"> na karte priečinka
    („3 sekcie · 120 liniek“, bod 27 previerky 3). Bez obsahu <script> (tam sú len texty kódu)."""
    bez = re.sub(r"<script\b.*?</script>", "", text, flags=re.S | re.I)
    karty = []
    for tag, vnutro in re.findall(r'(<a class="card"[^>]*>)(.*?)</a>', bez, flags=re.S):
        a = atributy(tag)
        href = a.get("href", "")
        if a.get("target") == "_blank":
            karty.append(("l", href, ""))
        else:
            m = re.search(r'<div class="ct">(.*?)</div>', vnutro, flags=re.S)
            karty.append(("f", urllib.parse.unquote(urllib.parse.urlsplit(
                urllib.parse.urljoin(url, href)).path), html.unescape(m.group(1)) if m else ""))
    return karty


def pekne(n):
    return f"{n:,}".replace(",", " ")


class Test:
    def __init__(self, base, vystup):
        self.base = base if base.endswith("/") else base + "/"
        c = urllib.parse.urlsplit(self.base)
        self.host, self.schema, self.koren = c.netloc, c.scheme, c.path
        self.vystup = vystup
        os.makedirs(vystup, exist_ok=True)
        self.vysledky = []      # (stav, názov, detail)  stav: ok / warn / fail
        self.info = []          # doplňujúce riadky do zhrnutia
        self.zoznamy = []       # (nadpis, [riadky]) — podrobné zoznamy chýb pod tabuľkou
        self.log = []           # podrobný zoznam chýb (chyby.txt — všetky, nie len 30)
        self.lang = "sk"
        self.nazov_webu = ""
        self.adresy = []        # <loc> zo sitemap.xml (v poradí)
        self.stranky = {}       # adresa → {kod, title, canonical, hreflang, id, vlajky}
        self.cas_stranky = 0.0  # priemerný čas na stránku (odhad trvania párov)
        self.len_mobil = False  # --len-mobil: len kontrola i)
        self.mobil_vyber = None  # --zariadenia A,E: len vybrané zariadenia (lokálne skúšanie)
        self.mobil_matica = {}   # i) zariadenie → {stránka: (stav, poznámka)}

    # ------------------------------------------------ spúšťanie kontrol
    def kontrola(self, nazov, fn, pri_chybe="fail"):
        """Spustí kontrolu, pri neúspechu (výnimke) ešte raz. pri_chybe = fail (❌) / warn (⚠️).
        Kontrola, ktorá si opakuje adresy sama, vráti („fail", text) — tá sa už neopakuje."""
        for pokus in (1, 2):
            zaciatok = time.time()
            try:
                stav, detail = fn(pokus)
                self.vysledky.append((stav, nazov, detail))
                print(f"[{stav}] {nazov}: {detail} ({time.time() - zaciatok:.1f} s)", flush=True)
                if stav != "ok":
                    self.log.append(f"[{stav}] {nazov}: {detail}")
                return
            except Exception as e:
                text = str(e) if isinstance(e, Zlyhanie) else f"{type(e).__name__}: {e}"
                text = text.strip().splitlines()[0][:400] if text.strip() else type(e).__name__
                self.log.append(f"[pokus {pokus}] {nazov}: {text}")
                if not isinstance(e, Zlyhanie):
                    self.log.append(traceback.format_exc())
                print(f"[pokus {pokus} zlyhal] {nazov}: {text}", flush=True)
                if pokus == 1:
                    time.sleep(5)
                    continue
                self.vysledky.append((pri_chybe, nazov, text))

    def zoznam(self, nadpis, riadky):
        """Zoznam chýb: do zhrnutia max. MAX_VYPIS, do chyby.txt všetky."""
        if not riadky:
            return
        self.log.append(f"--- {nadpis} ({len(riadky)}) ---")
        self.log.extend(riadky)
        ukaz = riadky[:MAX_VYPIS]
        if len(riadky) > MAX_VYPIS:
            ukaz = ukaz + [f"… a ďalších {len(riadky) - MAX_VYPIS} (všetky v prílohe chyby.txt)"]
        self.zoznamy.append((f"{nadpis} ({len(riadky)})", ukaz))

    def paralelne(self, fn, polozky):
        with ThreadPoolExecutor(max_workers=NARAZ) as ex:
            return list(ex.map(fn, polozky))

    def cesta(self, u):
        return urllib.parse.urlsplit(u).path

    # ------------------------------------------------ domov (jazyk webu)
    def zisti_jazyk(self):
        kod, _, text = stiahni(self.base, cache_bust=True)
        if kod != 200:
            raise Zlyhanie(f"domovská stránka vrátila HTTP {kod}")
        m = re.search(r'<html[^>]*\slang="([a-z]+)', text)
        self.lang = m.group(1) if m else "sk"
        self.nazov_webu = meta_z_html(text, "og:site_name")
        _, hl = hlavicka_stranky(text)
        self.domov_hreflang = hl

    # ------------------------------------------------ a) sitemap.xml + všetky adresy
    def nacitaj_stranku(self, url):
        """Stiahne stránku a vytiahne z nej všetko potrebné (celé HTML sa neodkladá)."""
        try:
            kod, _, text = stiahni(url)
        except Exception as e:
            return {"kod": 0, "chyba": f"{type(e).__name__}: {e}"[:150]}
        if kod != 200:
            return {"kod": kod}
        canonical, hreflang = hlavicka_stranky(text)
        return {"kod": 200, "title": titulok_z_html(text), "canonical": canonical,
                "hreflang": hreflang, "id": id_stranky(text),
                "vlajky": set(VLAJKA_RE.findall(text)), "karty": karty_stranky(text, url),
                "manifest": 'rel="manifest"' in text and 'name="theme-color"' in text}   # j) Zadanie 50

    def sitemap(self, pokus):
        kod, _, text = stiahni(self.base + "sitemap.xml", cache_bust=True)
        if kod != 200:
            raise Zlyhanie(f"sitemap.xml vrátil HTTP {kod}")
        try:
            koren = ET.fromstring(text.encode("utf-8"))
        except ET.ParseError as e:
            raise Zlyhanie(f"sitemap.xml nie je platné XML ({e})") from e
        if koren.tag != SM_NS + "urlset":
            raise Zlyhanie(f"sitemap.xml nemá koreň <urlset> ({koren.tag})")
        adresy = [(e.text or "").strip() for e in koren.iter(SM_NS + "loc")]
        if len(adresy) < 10:
            raise Zlyhanie(f"sitemap.xml má len {len(adresy)} adries")
        problemy = []
        dup = sorted({u for u in adresy if adresy.count(u) > 1}) if len(set(adresy)) != len(adresy) else []
        if dup:
            self.zoznam("a) Duplicitné adresy v sitemap.xml", dup)
            problemy.append(f"{len(dup)} duplicitných adries")
        cudzie = [u for u in adresy if not u.startswith(self.base)]
        if cudzie:
            self.zoznam(f"a) Adresy v sitemap.xml mimo {self.base}", cudzie)
            problemy.append(f"{len(cudzie)} adries nepatrí na {self.base}")
        adresy = list(dict.fromkeys(u for u in adresy if u.startswith(self.base)))
        self.adresy = adresy
        # adresy so znakmi mimo ASCII (diakritika v slugu z data.json) — fungujú, ale Google
        # ich ukazuje zakódované (%C3%A1…) a sitemap by ich mala mať zakódované → len ⚠️
        diakritika = [self.cesta(u) for u in adresy if any(ord(c) > 127 for c in u)]
        if diakritika:
            self.zoznam("a) Adresy s diakritikou v sitemap.xml (slug v data.json — len upozornenie)", diakritika)
        # všetky adresy — 8 naraz; neúspešná ešte raz (po krátkej pauze)
        t0 = time.time()
        vysl = dict(zip(adresy, self.paralelne(self.nacitaj_stranku, adresy), strict=True))
        trvanie = time.time() - t0
        self.cas_stranky = trvanie / max(1, len(adresy))
        zle = [u for u, v in vysl.items() if v["kod"] != 200]
        if zle:
            time.sleep(10)
            vysl.update(zip(zle, self.paralelne(self.nacitaj_stranku, zle), strict=True))
        self.stranky = {u: v for u, v in vysl.items() if v["kod"] == 200}
        chybaju = [f"{self.cesta(u)} → " + (f"HTTP {v['kod']}" if v["kod"] else v.get("chyba", "chyba"))
                   for u, v in vysl.items() if v["kod"] != 200]
        if chybaju:
            self.zoznam("a) Stránky zo sitemap.xml, ktoré nevrátili HTTP 200", chybaju)
            problemy.append(f"{len(chybaju)} stránok nevrátilo 200 ani na druhý pokus")
        self.info.append(f"**sitemap.xml:** {pekne(len(adresy))} adries, stiahnuté za {trvanie:.0f} s "
                         f"({NARAZ} naraz)")
        detail = f"{len(adresy)} adries, platné XML, HTTP 200: {len(self.stranky)}"
        if problemy:
            return "fail", detail + " — " + "; ".join(problemy)
        detail += ", bez duplicít, všetky na " + self.base
        if diakritika:
            return "warn", detail + (f"; ⚠️ {len(diakritika)} adries s diakritikou v slugu "
                                     f"(napr. {diakritika[0]}) — oprava slugu v data.json")
        return "ok", detail

    # ------------------------------------------------ b) title, canonical, hreflang, páry
    def druhy_web(self):
        """Adresa druhého webu (SK ↔ EN) z hreflang domova."""
        druhy = "en" if self.lang == "sk" else "sk"
        u = (self.domov_hreflang or {}).get(druhy) or ""
        c = urllib.parse.urlsplit(u)
        return druhy, (c.netloc if c.scheme in ("http", "https") else "")

    # ------------------------------------------------ j) web ako aplikácia (Zadanie 50)
    def pwa(self, pokus):
        """Ak web má PWA (manifest.webmanifest 200): VŠETKY stránky zo sitemapy (stiahnuté
        v kontrole a) majú <link rel="manifest"> a theme-color, sw.js vráti 200 ako JavaScript
        a manifest odkazuje na ikonky, ktoré vrátia 200. Bez PWA / PWA vypnuté = ✅ s poznámkou."""
        kod_sw, hl_sw, sw = stiahni(self.base + "sw.js")
        kod_m, _, man = stiahni(self.base + "manifest.webmanifest")
        if kod_m == 404:
            if kod_sw == 200 and "PWA je VYPNUTÉ" in sw:
                zle = [self.cesta(u) for u, v in self.stranky.items() if v.get("kod") == 200 and v.get("manifest")]
                if zle:
                    self.zoznam("j) Stránky s manifestom, hoci je PWA vypnuté", zle)
                    raise Zlyhanie(f"PWA je vypnuté, ale {len(zle)} stránok má ešte <link rel=\"manifest\">")
                return "ok", "PWA je VYPNUTÉ (samozničujúci sw.js, stránky bez manifestu)"
            if kod_sw == 200:   # bežný sw.js beží, ale manifest chýba = pokazené nasadenie
                raise Zlyhanie("/sw.js je na webe (PWA zapnuté), ale manifest.webmanifest vrátil HTTP 404")
            return "ok", "web ešte nemá PWA (sw.js ani manifest nie sú) — nič sa neskúša"
        if kod_m != 200:
            raise Zlyhanie(f"manifest.webmanifest vrátil HTTP {kod_m}")
        try:
            m = json.loads(man)
        except ValueError as e:
            raise Zlyhanie(f"manifest.webmanifest nie je platný JSON ({e})") from e
        if kod_sw != 200 or "javascript" not in (hl_sw.get("Content-Type") or "").lower():
            raise Zlyhanie(f"/sw.js: HTTP {kod_sw}, typ {hl_sw.get('Content-Type') if hl_sw else '?'}")
        zle_ik = [i.get("src") for i in m.get("icons", []) if stiahni(urllib.parse.urljoin(self.base, i.get("src", "")), binarne=True)[0] != 200]
        if not m.get("icons") or zle_ik:
            raise Zlyhanie(f"ikonky aplikácie v manifeste chýbajú alebo nevrátia 200: {zle_ik}")
        ok = [u for u, v in self.stranky.items() if v.get("kod") == 200]
        zle = [self.cesta(u) for u in ok if not self.stranky[u].get("manifest")]
        if zle:
            self.zoznam("j) Stránky bez <link rel=\"manifest\"> / theme-color", zle)
            raise Zlyhanie(f"{len(zle)} z {len(ok)} stránok nemá <link rel=\"manifest\"> alebo theme-color")
        return "ok", (f"manifest „{m.get('short_name')}“ ({len(m['icons'])} ikonky 200), sw.js JavaScript; "
                      f"<link rel=\"manifest\"> + theme-color na všetkých {len(ok)} stránkach")

    def hlavicky(self, pokus):
        if not self.stranky:
            raise Zlyhanie("bez stránok zo sitemap.xml (kontrola a) sa nedá kontrolovať")
        vlastny = self.lang
        druhy, druhy_host = self.druhy_web()
        if not druhy_host:
            raise Zlyhanie(f"domovská stránka nemá hreflang „{druhy}“ — nevie sa, kde je druhý web")
        if druhy_host == self.host:
            raise Zlyhanie(f"hreflang „{druhy}“ domova ukazuje na ten istý web ({druhy_host})")
        chyby, bez_paru, pary = [], 0, []
        for u in self.adresy:
            s = self.stranky.get(u)
            if not s:
                continue
            p = self.cesta(u)
            if not s["title"]:
                chyby.append(f"{p}: chýba <title>")
            if s["canonical"] != u:
                chyby.append(f"{p}: canonical {s['canonical']!r} ≠ adresa zo sitemapy")
            h = s["hreflang"]
            if not h:
                bez_paru += 1         # stránka bez náprotivku v druhom jazyku — hreflang zámerne nie je
                continue
            chyba = [k for k in ("sk", "en", "x-default") if not h.get(k)]
            if chyba:
                chyby.append(f"{p}: hreflang bez {', '.join(chyba)}")
                continue
            if h[vlastny] != u:
                chyby.append(f"{p}: hreflang „{vlastny}“ {h[vlastny]} ≠ canonical")
            if urllib.parse.urlsplit(h[druhy]).netloc != druhy_host:
                chyby.append(f"{p}: hreflang „{druhy}“ {h[druhy]} nie je na druhom webe ({druhy_host})")
                continue
            if h["x-default"] != h["en"]:
                chyby.append(f"{p}: hreflang x-default {h['x-default']} ≠ en {h['en']}")
            pary.append((u, h[druhy]))
        # páry SK ↔ EN na druhom webe — celé, alebo vzorka, keby to trvalo príliš dlho
        odhad = len(pary) * self.cas_stranky
        vzorka = len(pary) > PARY_VZORKA and odhad > PARY_MAX_S
        overit = random.sample(pary, PARY_VZORKA) if vzorka else pary

        def over_par(par):
            u, alt = par
            v = self.nacitaj_stranku(alt)
            if v["kod"] != 200:
                time.sleep(3)
                v = self.nacitaj_stranku(alt)
            if v["kod"] != 200:
                return f"{self.cesta(u)}: náprotivok {alt} → " + (
                    f"HTTP {v['kod']}" if v["kod"] else v.get("chyba", "chyba"))
            spat = (v.get("hreflang") or {}).get(vlastny)
            if spat != u:
                return f"{self.cesta(u)}: náprotivok {alt} má hreflang „{vlastny}“ {spat!r} (čakám späť túto stránku)"
            return None

        t0 = time.time()
        chyby_pary = [x for x in self.paralelne(over_par, overit) if x]
        trvanie = time.time() - t0
        self.zoznam("b) Titulok / canonical / hreflang", chyby)
        self.zoznam("b) Páry SK ↔ EN", chyby_pary)
        rozsah = (f"náhodná vzorka {len(overit)} z {len(pary)} párov (všetky by trvali ~{odhad / 60:.0f} min)"
                  if vzorka else f"všetkých {len(pary)} párov")
        self.info.append(f"**Páry SK ↔ EN:** overených {rozsah} na {druhy_host}, {trvanie:.0f} s; "
                         f"stránok bez náprotivku (bez hreflang): {bez_paru}")
        detail = (f"{len(self.stranky)} stránok: titulok, canonical, hreflang; páry {druhy_host}: "
                  f"{len(overit) - len(chyby_pary)}/{len(overit)} OK" + (" (vzorka)" if vzorka else ""))
        if chyby or chyby_pary:
            return "fail", detail + f" — chýb: hlavička {len(chyby)}, páry {len(chyby_pary)}"
        return "ok", detail

    # ------------------------------------------------ c) robots.txt
    def robots(self, pokus):
        kod, _, text = stiahni(self.base + "robots.txt", cache_bust=True)
        if kod != 200:
            raise Zlyhanie(f"robots.txt vrátil HTTP {kod}")
        if not re.search(r"(?im)^\s*sitemap:\s*\S*sitemap\.xml\s*$", text):
            raise Zlyhanie("robots.txt neobsahuje riadok „Sitemap: …/sitemap.xml“")
        # celý web zablokovaný = „Disallow: /“ (bez ďalšej cesty) v skupine pre všetkých robotov
        agenti, pravidla, blok = [], False, False
        for r in text.splitlines():
            r = r.split("#", 1)[0].strip()
            k, _, v = r.partition(":")
            k, v = k.strip().lower(), v.strip()
            if k == "user-agent":
                if pravidla:              # nová skupina robotov
                    agenti, pravidla = [], False
                agenti.append(v)
            elif k in ("disallow", "allow"):
                pravidla = True
                if k == "disallow" and v == "/" and "*" in agenti:
                    blok = True
        if blok:
            raise Zlyhanie("robots.txt blokuje celý web (User-agent: * / Disallow: /)")
        return "ok", "HTTP 200, odkaz na sitemap.xml, celý web povolený"

    # ------------------------------------------------ d) verzia data.json
    def verzia(self, pokus):
        def ver_z_webu(url):
            kod, _, text = stiahni(url, cache_bust=True, timeout=60)
            if kod != 200:
                raise Zlyhanie(f"{url} vrátil HTTP {kod}")
            try:
                return json.loads(text).get("version")
            except ValueError as e:
                raise Zlyhanie(f"{url} nie je platný JSON ({e})") from e
        if self.lang == "sk":
            cesta = os.environ.get("REPO_DATA_JSON") or "data.json"
            try:
                with open(cesta, encoding="utf-8") as f:
                    v_repo = json.load(f).get("version")
            except (OSError, ValueError) as e:
                raise Zlyhanie(f"data.json z repozitára ({cesta}) sa nedá prečítať: {e}") from e
            v_web = ver_z_webu(self.base + "data-full.json")
            if v_web != v_repo:
                return "fail", (f"data-full.json na webe má verziu {v_web}, data.json v repozitári (main) "
                                f"{v_repo} — web nemá najnovšie dáta (build/nasadenie zlyhalo?)")
            return "ok", f"verzia {v_web} na webe = verzia v repozitári (main)"
        # EN web: dáta sú zo SK webu (data-full.json); EN sa obnoví až svojím buildom
        sk = (self.domov_hreflang or {}).get("sk") or SK_MASTER
        sk = sk if sk.endswith("/") else sk + "/"
        v_web = ver_z_webu(self.base + "data.json")
        v_sk = ver_z_webu(urllib.parse.urljoin(sk, "/data-full.json"))
        if v_web != v_sk:
            return "warn", (f"data.json na webe má verziu {v_web}, SK web ({sk}data-full.json) {v_sk} — "
                            "EN web ešte čaká na svoj build")
        return "ok", f"verzia {v_web} = verzia na SK webe ({sk})"

    # ------------------------------------------------ e) presmerovania
    def presmerovania(self, pokus):
        domena = urllib.parse.urlsplit(self.base).hostname or ""
        if domena in ("localhost",) or re.fullmatch(r"[\d.]+|\[?[0-9a-f:]+\]?", domena):
            return "warn", f"{domena}: lokálna adresa — presmerovania sa nedajú overiť (preskočené)"
        hlbsia = next((self.cesta(u) for u in self.adresy if self.cesta(u).count("/") >= 4),
                      self.koren)
        chyby, ok, varovania = [], [], []

        def over(z, cakam, popis):
            kod, kam = presmerovanie(z)
            if kod not in (301, 308):
                chyby.append(f"{popis}: {z} → HTTP {kod} (čakám 301/308 na {cakam})")
            elif urllib.parse.urljoin(z, kam) != cakam:
                chyby.append(f"{popis}: {z} → {kam} (čakám {cakam})")
            else:
                ok.append(f"{popis} {kod}")

        for cesta in (self.koren, hlbsia):
            over(f"http://{domena}{cesta}", f"https://{domena}{cesta}", "http→https" + (" (hlbšia)" if cesta != self.koren else ""))
        www = "www." + domena
        try:
            socket.getaddrinfo(www, 443)
            mam_www = True
        except socket.gaierror:
            mam_www = False
        if not mam_www:
            varovania.append(f"{www} nemá záznam v DNS — kto napíše adresu s www, web nenájde "
                             "(stačí pridať u registrátora CNAME www → GitHub Pages, ak to chceš)")
        else:
            for cesta in (self.koren, hlbsia):
                popis = "www→bez www" + (" (hlbšia)" if cesta != self.koren else "")
                try:
                    over(f"https://{www}{cesta}", f"https://{domena}{cesta}", popis)
                except (urllib.error.URLError, OSError) as e:
                    chyby.append(f"{popis}: https://{www}{cesta} neodpovedá ({e})")
        if chyby:
            self.zoznam("e) Presmerovania", chyby)
            return "fail", "; ".join(chyby[:3])
        detail = ", ".join(ok) + f" (hlbšia adresa {hlbsia})"
        if varovania:
            return "warn", detail + "; ⚠️ " + "; ".join(varovania)
        return "ok", detail

    # ------------------------------------------------ f) ikonky a vlajky
    def ikony_vlajky(self, pokus):
        kod, _, text = stiahni(self.base + "data.json", cache_bust=True, timeout=60)
        if kod != 200:
            raise Zlyhanie(f"data.json vrátil HTTP {kod}")
        uzly = json.loads(text).get("nodes") or []
        hosty = set()
        for n in uzly:
            if n.get("type") != "link":
                continue
            h = host_z_url(n.get("url"))
            if h and not SOCIAL_FAV.search(h) and not NO_FAVICON_HOSTS.search(h) \
                    and SAFE_HOST.match(h) and len(h) <= 253:
                hosty.add(h)
        vyber = random.sample(sorted(hosty), min(IKONY_VZORKA, len(hosty)))

        def skus(u):
            for p in (1, 2):
                try:
                    k, _, b = stiahni(u, binarne=True)
                except Exception:
                    k, b = 0, b""
                if k == 200 or k == 404 or p == 2:
                    return k, len(b)
                time.sleep(2)
            return 0, 0

        ik = dict(zip(vyber, self.paralelne(lambda h: skus(f"{self.base}ikony/{h}.png"), vyber), strict=True))
        chybaju = sorted(h for h, (k, _) in ik.items() if k != 200)
        # vlajky: tie, na ktoré odkazujú statické stránky (src aj srcset)
        vsetky = sorted({v for s in self.stranky.values() for v in s.get("vlajky", ())})
        vl_vyber = random.sample(vsetky, min(VLAJKY_VZORKA, len(vsetky)))
        vl = dict(zip(vl_vyber, self.paralelne(lambda p: skus(urllib.parse.urljoin(self.base, p)), vl_vyber), strict=True))
        vl_zle = sorted(f"{p} → HTTP {k}" for p, (k, _) in vl.items() if k != 200)
        vl_nahr = sorted(p for p, (k, d) in vl.items() if k == 200 and d < 100)   # priehľadný 1×1
        pct = 100 * len(chybaju) / max(1, len(ik))
        self.zoznam("f) Weby bez ikonky /ikony/ (len upozornenie)", [f"{h}.png" for h in chybaju])
        self.zoznam("f) Vlajky, ktoré nevrátili HTTP 200", vl_zle)
        self.zoznam("f) Vlajky — priehľadný náhradník 1×1 (vlajka sa pri builde nestiahla)", vl_nahr)
        detail = (f"ikonky: {len(ik) - len(chybaju)}/{len(ik)} náhodných webov má /ikony/<host>.png "
                  f"(chýba {pct:.1f} %); vlajky: {len(vl) - len(vl_zle)}/{len(vl)} náhodných z {len(vsetky)} OK")
        if vl_zle:
            return "fail", detail
        if not vsetky:
            return "warn", detail + " — na stránkach sa nenašla žiadna vlajka z /vlajky/"
        if chybaju or vl_nahr:
            return "warn", detail + (f", náhradníkov 1×1: {len(vl_nahr)}" if vl_nahr else "")
        return "ok", detail

    # ------------------------------------------------ g) appka ↔ generátor (bod 15)
    def smerovanie(self, route):
        host = urllib.parse.urlsplit(route.request.url).netloc
        if any(host == b or host.endswith("." + b) for b in BLOKOVANE):
            return route.abort()
        return route.continue_()

    # Beží V PREHLIADAČI: pre všetky priečinky zo stiahnutého data.json vypočíta adresu
    # (urlForId → nodeSlug → _slugFix / nodeSlugBase / slugify) a titulok tak, ako ho appka
    # naozaj nastaví (updateHead: kontext, _titleNoSport, Aktuálne cez liveTitle).
    # Navyše adresu aj BEZ mapy _slugFix (vlastné riešenie rovnakých slugov v appke).
    APP_JS = """() => {
      const vidno = new Set(), zas = [null];
      while(zas.length){ const p = zas.pop();
        for(const k of getChildren(p)){ if(k.type==='folder' && !vidno.has(k.id)){ vidno.add(k.id); zas.push(k.id); } } }
      const povodny = curId, out = [];
      for(const n of DB.nodes){
        if(n.type !== 'folder') continue;
        const r = {id: n.id, name: nName(n), vid: vidno.has(n.id), live: n.id === LIVE_ID};
        if(r.vid){
          r.empty = emptyFolder(n);
          r.url = urlForId(n.id);
          curId = n.id; updateHead(); r.title = document.title;
        }
        out.push(r);
      }
      curId = povodny; updateHead();
      const fix = SLUG_FIX; SLUG_FIX = null; _slugMemo = null;
      try { out.forEach(r => { if(r.vid) r.urlBezFix = urlForId(r.id); }); }
      finally { SLUG_FIX = fix; _slugMemo = null; }
      let akt = 0; try { akt = liveWeekLinks().length; } catch(e) {}
      return {nodes: out, mamFix: !!fix, akt: akt, base: BASE_PATH};
    }"""

    def v_appke(self, fn):
        """Otvorí domov v prehliadači, počká na CELÉ dáta a aktualne.json a zavolá fn(page).
        Štatistiky a reklamy sú blokované (BLOKOVANE). Vráti výsledok fn."""
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            spustit = {}
            if os.environ.get("CHROMIUM_PATH"):   # len pre lokálne skúšanie
                spustit["executable_path"] = os.environ["CHROMIUM_PATH"]
            browser = p.chromium.launch(**spustit)
            try:
                ctx = browser.new_context(viewport={"width": 1366, "height": 900}, user_agent=UA_PC,
                                          extra_http_headers=X_TEST)
                ctx.route("**/*", self.smerovanie)
                ctx.add_init_script(SW_VYP_SKRIPT)   # Zadanie 50: bez service workera (ako pred PWA)
                page = ctx.new_page()
                chyby_js = []
                page.on("pageerror", lambda e: chyby_js.append(str(e)))
                page.goto(self.base, wait_until="load", timeout=60_000)
                try:   # celé dáta (nie len štartovací balík BOOT)
                    page.wait_for_function("() => typeof DB !== 'undefined' && DB && DB.nodes"
                                           " && DB.nodes.length > 100 && !DB._partial", timeout=90_000)
                except Exception:
                    raise Zlyhanie("appka do 90 s nestiahla celý data.json" +
                                   (f" (chyby JS: {' | '.join(chyby_js[:3])})" if chyby_js else "")) from None
                try:   # aktualne.json (titulok a obsah stránky Aktuálne) sa sťahuje zvlášť
                    page.wait_for_load_state("networkidle", timeout=20_000)
                except Exception:
                    pass
                page.wait_for_timeout(1500)
                return fn(page)
            finally:
                browser.close()

    def zrkadlo(self, pokus):
        if not self.stranky:
            raise Zlyhanie("bez stránok zo sitemap.xml (kontrola a) sa nedá porovnať")
        app = self.v_appke(lambda page: page.evaluate(self.APP_JS))
        # generátor: stránky zo sitemapy — id priečinka (pageBoot), adresa, statický titulok
        domov = self.base
        gen = {}            # id → (cesta, titulok)
        bez_id = []
        for u in self.adresy:
            s = self.stranky.get(u)
            if not s or u == domov:
                continue
            if s.get("id"):
                gen[s["id"]] = (self.cesta(u), s["title"])
            else:
                bez_id.append(u)
        gen_cesty = {self.cesta(u) for u in self.adresy if u != domov}
        rozdiely, bezfix, zhoda = [], [], 0
        vynech = {"skryté (enOnly / en:false)": 0, "prázdne priečinky": 0, "Aktuálne bez položiek": 0}
        app_cesty = set()
        for r in app["nodes"]:
            if not r["vid"]:
                vynech["skryté (enOnly / en:false)"] += 1
                continue
            g = gen.get(r["id"])
            if r["empty"] and not g:
                vynech["prázdne priečinky"] += 1
                continue
            if r["live"] and not app["akt"] and not g and r["url"] not in gen_cesty:
                vynech["Aktuálne bez položiek"] += 1
                continue
            app_cesty.add(r["url"])
            if r.get("urlBezFix") and r["urlBezFix"] != r["url"]:
                bezfix.append(f"{r['id']} „{r['name']}“: bez _slugFix {r['urlBezFix']} ≠ {r['url']}")
            if not g:
                if r["url"] in gen_cesty:   # stránka bez pageBoot — aspoň adresa sedí
                    zhoda += 1
                    continue
                rozdiely.append(f"{r['id']} „{r['name']}“: appka {r['url']} — v sitemap.xml nie je"
                                + (" (appka ho má za prázdny)" if r["empty"] else ""))
                continue
            chyba = []
            if r["url"] != g[0]:
                chyba.append(f"adresa appky {r['url']} ≠ sitemap {g[0]}")
            if r["title"] != g[1]:
                chyba.append(f"titulok appky „{r['title']}“ ≠ statický „{g[1]}“")
            if r["empty"]:
                chyba.append("appka ho má za prázdny (dlaždicu neukáže), generátor stránku vyrobil")
            if chyba:
                rozdiely.append(f"{r['id']} „{r['name']}“: " + "; ".join(chyba))
            else:
                zhoda += 1
        navyse = sorted(gen_cesty - app_cesty)   # stránky generátora, ktoré appka nevyrába
        rozdiely += [f"sitemap.xml má {c}, appka takú stránku nevyrába" for c in navyse]
        self.zoznam("g) Rozdiely appka ↔ generátor (adresa / titulok)", rozdiely)
        self.zoznam("g) Adresy appky bez mapy _slugFix (vlastné riešenie rovnakých slugov) — len upozornenie", bezfix)
        vyn = ", ".join(f"{k} {v}" for k, v in vynech.items() if v) or "žiadne"
        self.info.append(f"**Appka ↔ generátor:** zhodných stránok {pekne(zhoda)} (adresa aj titulok); "
                         f"zámerne vynechané generátorom (nehlásia sa): {vyn}"
                         + (f"; stránok bez pageBoot (porovnaná len adresa): {len(bez_id)}" if bez_id else ""))
        detail = (f"zhoda {zhoda} stránok, rozdielov {len(rozdiely)}; vynechané: {vyn}"
                  + ("" if app["mamFix"] else "; appka nedostala mapu _slugFix"))
        if rozdiely:
            return "fail", detail
        if bezfix:
            return "warn", detail + f"; ⚠️ bez mapy _slugFix by appka mala inú adresu pri {len(bezfix)} priečinkoch"
        return "ok", detail

    # ------------------------------------------------ h) obsah stránok appka ↔ statika
    # Beží V PREHLIADAČI pre dávku id priečinkov: karty tak, ako ich appka ukáže návštevníkovi
    # (tileKids → renderLevel: najprv priečinky, potom linky; Aktuálne = liveWeekLinks).
    # Kľúč karty: priečinok = urlForId (adresa jeho stránky), linka = safeUrl(url).
    OBSAH_JS = """(ids) => {
      const out = {};
      for(const id of ids){
        const n = nodeById(id);
        if(!n){ out[id] = null; continue; }
        const kids = tileKids(id);
        const k = kids.filter(x => x.type === 'folder').concat(kids.filter(x => x.type === 'link'));
        out[id] = {name: nName(n), live: id === LIVE_ID,
                   karty: k.map(x => [x.type === 'folder' ? 'f' : 'l', x.id, nName(x),
                                      x.type === 'folder' ? urlForId(x.id) : safeUrl(x.url),
                                      x.type === 'folder' ? folderCountText(x) : ''])};
      }
      return out;
    }"""

    def obsah(self, pokus):
        if not self.stranky:
            raise Zlyhanie("bez stránok zo sitemap.xml (kontrola a) sa nedá porovnať")
        # statika: stránky so známym id priečinka (pageBoot) — adresa, karty
        stat = {}
        for u in self.adresy:
            s = self.stranky.get(u)
            if s and u != self.base and s.get("id") and s.get("karty") is not None:
                stat.setdefault(s["id"], (self.cesta(u), s["karty"]))
        ids = list(stat)
        info = {}

        def porovnaj(page):
            t0 = time.time()
            prva = page.evaluate(self.OBSAH_JS, ids[:OBSAH_DAVKA])
            trv = time.time() - t0
            odhad = trv * len(ids) / max(1, min(len(ids), OBSAH_DAVKA))
            vzorka = len(ids) > OBSAH_VZORKA and odhad > OBSAH_MAX_S
            zvysok = ids[OBSAH_DAVKA:]
            if vzorka:
                zvysok = random.sample(zvysok, max(0, OBSAH_VZORKA - len(prva)))
            app = dict(prva)
            for i in range(0, len(zvysok), OBSAH_DAVKA):
                app.update(page.evaluate(self.OBSAH_JS, zvysok[i:i + OBSAH_DAVKA]))
            info.update(odhad=odhad, vzorka=vzorka, cas=time.time() - t0)
            return app

        app = self.v_appke(porovnaj)
        rozdiely, live_rozdiely, zhoda, kariet = [], [], 0, 0
        for fid, a in app.items():
            cesta, karty_s = stat[fid]
            if a is None:
                rozdiely.append(f"{fid} {cesta}: statická stránka je, appka taký priečinok nepozná")
                continue
            # adresy v appke aj statike porovnávať v rovnakom tvare (diakritika, %C3%A1…)
            karty_a = [(t, urllib.parse.unquote(k) if t == "f" else k, c) for t, _, _, k, c in a["karty"]]
            kariet += len(karty_a)
            if karty_a == karty_s:
                zhoda += 1
                continue
            ciel = live_rozdiely if a["live"] else rozdiely
            ciel.append(f"{fid} „{a['name']}“ {cesta}: " + self.rozdiel_kariet(a["karty"], karty_a, karty_s))
        self.zoznam("h) Obsah stránok: karty appky ≠ karty statickej stránky", rozdiely)
        self.zoznam("h) Stránka Aktuálne: karty appky ≠ statika (statika je z nočného buildu) — len upozornenie",
                    live_rozdiely)
        rozsah = (f"náhodná vzorka {len(app)} z {len(ids)} stránok (všetky by trvali ~{info['odhad'] / 60:.0f} min)"
                  if info["vzorka"] else f"všetkých {len(app)} stránok")
        self.info.append(f"**Obsah appka ↔ statika:** {rozsah}, {pekne(kariet)} kariet, "
                         f"porovnanie v prehliadači {info['cas']:.0f} s; zhodných stránok {pekne(zhoda)}")
        detail = (f"{rozsah}: zhoda {zhoda}, rozdielov {len(rozdiely) + len(live_rozdiely)}"
                  + (" (vzorka)" if info["vzorka"] else ""))
        if rozdiely:
            return "fail", detail
        if live_rozdiely:
            return "warn", detail + " — len stránka Aktuálne (statika z nočného buildu, appka podľa dnešného dátumu)"
        return "ok", detail

    @staticmethod
    def rozdiel_kariet(karty_app, a, s):
        """Čitateľný popis prvého rozdielu dvoch zoznamov kariet (v poradí)."""
        def popis(i, zoznam):
            if i >= len(zoznam):
                return "(nič)"
            t, k, c = zoznam[i]
            return ("priečinok " if t == "f" else "linka ") + k + (f" [{c}]" if c else "")
        if len(a) != len(s) or sorted(a) != sorted(s):
            # rozdiel s počtom výskytov (duplicitná linka v priečinku sa ráta 2×)
            chyba_a = list((collections.Counter(a) - collections.Counter(s)).elements())[:3]
            chyba_s = list((collections.Counter(s) - collections.Counter(a)).elements())[:3]
            text = (f"kariet appka {len(a)} ≠ statika {len(s)}" if len(a) != len(s)
                    else "iná adresa alebo iný počet „X sekcií · Y liniek“ na karte")
            if chyba_a:
                text += "; len v appke: " + ", ".join(f"{k} [{c}]" if c else k for _, k, c in chyba_a)
            if chyba_s:
                text += "; len v statike: " + ", ".join(f"{k} [{c}]" if c else k for _, k, c in chyba_s)
            return text
        i = next(i for i, (x, y) in enumerate(zip(a, s, strict=True)) if x != y)
        meno = f"{karty_app[i][1]} „{karty_app[i][2]}“"
        return (f"iné PORADIE od karty č. {i + 1}: appka {meno} = {popis(i, a)}, statika {popis(i, s)} "
                f"(appka [{', '.join(x[2] for x in karty_app[i:i + 4])}…])")

    # ------------------------------------------------ i) mobilné zariadenia (Zadanie 48a)
    # Celá kontrola beží v čistých prehliadačoch testu: Chromium (Android) a WebKit (jadro
    # Safari = iPhone). Štatistiky a reklamy sú blokované (BLOKOVANE) — žiadne falošné
    # návštevy ani zobrazenia reklamy. Obľúbené (★) sa pridávajú LEN v prehliadači testu,
    # do admina sa test NEPRIHLASUJE (len otvorí a zavrie okno s heslom).
    def mobil_priprav(self):
        """Adresy pevných stránok (vypočíta ich appka sama — urlForId, takže SK aj EN)
        a náhodná vzorka hlbokých stránok zo sitemap.xml (na každý deň iná)."""
        if not self.adresy:   # --len-mobil: kontrola a) nebežala — stačí zoznam adries
            kod, _, text = stiahni(self.base + "sitemap.xml", cache_bust=True)
            if kod != 200:
                raise Zlyhanie(f"sitemap.xml vrátil HTTP {kod}")
            self.adresy = [(e.text or "").strip() for e in ET.fromstring(text.encode("utf-8")).iter(SM_NS + "loc")]
        cesty = {urllib.parse.unquote(self.cesta(u)) for u in self.adresy}
        with self.mobil_prehliadac("chromium") as browser:
            ctx = self.mobil_kontext(browser, MOBIL_ZARIADENIA[0])
            try:
                page = ctx.new_page()
                page.goto(self.base, wait_until="load", timeout=60_000)
                page.wait_for_function(MOBIL_CELE_DATA, timeout=90_000)
                ids = {k: v for k, (v, _) in MOBIL_STRANKY.items() if v}
                adr = page.evaluate("""(ids) => { const o = {};
                    for (const [k, v] of Object.entries(ids)) {
                      const id = v === 'LIVE' ? (typeof LIVE_ID !== 'undefined' ? LIVE_ID : null) : v;
                      o[k] = id && nodeById(id) ? urlForId(id) : null; }
                    return o; }""", ids)
            finally:
                ctx.close()
        self.mobil_adresy = {"domov": self.base}
        vynechane = []
        for k, cesta in adr.items():
            if cesta and urllib.parse.unquote(cesta) in cesty:
                self.mobil_adresy[k] = urllib.parse.urljoin(self.base, cesta)
            else:   # napr. Tipovanie na EN webe nie je, Aktuálne bez položiek nemá stránku
                vynechane.append(MOBIL_STRANKY[k][1])
        pevne = {urllib.parse.unquote(self.cesta(u)) for u in self.mobil_adresy.values()}
        hlboke = sorted(u for u in self.adresy if self.cesta(u).strip("/").count("/") >= 2
                        and urllib.parse.unquote(self.cesta(u)) not in pevne)
        rnd = random.Random(datetime.now(timezone.utc).strftime("%Y-%m-%d"))   # opakovaný pokus = tá istá vzorka
        vzorka = rnd.sample(hlboke, min(len(hlboke), 2 * MOBIL_VZORKA))
        self.mobil_vzorky = {"A": vzorka[:MOBIL_VZORKA], "E": vzorka[MOBIL_VZORKA:]}
        self.info.append(f"**Mobil i):** pevné stránky {len(self.mobil_adresy)}"
                         + (f" (na tomto webe nie sú: {', '.join(vynechane)})" if vynechane else "")
                         + f"; náhodná vzorka {len(vzorka)} z {len(hlboke)} hlbokých stránok"
                         + f" (za ~{len(hlboke) // max(1, len(vzorka)) + 1} dní sa prejde celý web)")

    class _Prehliadac:
        """with self.mobil_prehliadac('webkit') as browser: … (Playwright sa spustí a zavrie)."""
        def __init__(self, druh):
            self.druh = druh

        def __enter__(self):
            from playwright.sync_api import sync_playwright
            self.pw = sync_playwright().start()
            spustit = {}
            if self.druh == "chromium" and os.environ.get("CHROMIUM_PATH"):   # len pre lokálne skúšanie
                spustit["executable_path"] = os.environ["CHROMIUM_PATH"]
            try:
                self.browser = getattr(self.pw, self.druh).launch(**spustit)
            except Exception:
                self.pw.stop()
                raise
            return self.browser

        def __exit__(self, *a):
            try:
                self.browser.close()
            finally:
                self.pw.stop()

    def mobil_prehliadac(self, druh):
        return self._Prehliadac(druh)

    def mobil_smerovanie(self, route):
        """Blokuje štatistiky a reklamy; vlastnej doméne pridá hlavičku X-Test (len jej —
        cudzia hlavička pri požiadavke na druhý web by spustila kontrolu CORS)."""
        req = route.request
        host = urllib.parse.urlsplit(req.url).netloc
        if any(host == b or host.endswith("." + b) for b in BLOKOVANE):
            return route.abort()
        nahrada = os.environ.get("MOBIL_SK_ZDROJ")   # len pre lokálne skúšanie: SK web (Aktuálne pre EN) z kópie
        if nahrada and req.url.startswith(SK_MASTER):
            return route.fulfill(response=route.fetch(url=nahrada + req.url[len(SK_MASTER):]))
        if host == self.host:
            return route.continue_(headers={**req.headers, "x-test": X_TEST["X-Test"]})
        return route.continue_()

    def mobil_kontext(self, browser, z, cache=True):
        sirka, vyska = z["okno"]
        ctx = browser.new_context(viewport={"width": sirka, "height": vyska}, screen={"width": sirka, "height": vyska},
                                  device_scale_factor=z["dpr"], is_mobile=True, has_touch=True,
                                  user_agent=z["ua"], locale="sk-SK" if self.lang == "sk" else "en-US")
        ctx.set_default_timeout(20_000)
        ctx.set_default_navigation_timeout(45_000)
        if cache:
            ctx.route("**/*", self.mobil_smerovanie)
        ctx.add_init_script(SW_VYP_SKRIPT)   # Zadanie 50: bez service workera (ako pred PWA)
        return ctx

    def mobil_stranka(self, ctx):
        """Karta, ktorá si zbiera chyby JavaScriptu, chyby v konzole (aj porušenia CSP —
        prehliadač ich hlási ako chybu v konzole) a chybné súbory vlastného webu.
        page.mz_chyby sa pred každou stránkou vyprázdni (mobil_otvor)."""
        page = ctx.new_page()
        page.mz_chyby = []
        page.mz_index = 0          # koľkokrát sa stiahol index.html (appka) — bod 12

        def blokovane(t):
            return any(b in (t or "") for b in BLOKOVANE)

        def on_console(m):
            if m.type != "error":
                return
            miesto = (m.location or {}).get("url", "") if isinstance(m.location, dict) else ""
            if blokovane(m.text) or blokovane(miesto):
                return   # zablokovaná reklama/štatistika (zámer testu), nie chyba webu
            if "aktualne.json" in (m.text + miesto) and "404" in m.text:
                return   # aktualne.json môže v prechodnom období chýbať (appka berie zálohu)
            page.mz_chyby.append(("CSP: " if "Content Security Policy" in m.text or "Content-Security-Policy" in m.text
                                  else "konzola: ") + m.text[:200])

        def on_resp(r):
            u = urllib.parse.urlsplit(r.url)
            if u.netloc != self.host:
                return
            if u.path.endswith("/index.html"):
                page.mz_index += 1
            if r.status >= 400 and not (u.path.endswith("/aktualne.json") and r.status == 404):
                page.mz_chyby.append(f"súbor {r.status} {u.path}")

        def on_fail(rq):
            u = urllib.parse.urlsplit(rq.url)
            f = rq.failure or ""
            if u.netloc == self.host and "ABORT" not in f.upper() and "cancel" not in f.lower():
                page.mz_chyby.append(f"súbor nenačítaný ({f}) {u.path}")

        page.on("pageerror", lambda e: page.mz_chyby.append("JavaScript: " + str(e)[:200]))
        page.on("console", on_console)
        page.on("response", on_resp)
        page.on("requestfailed", on_fail)
        return page

    def mobil_otvor(self, page, url, cakaj_s=25):
        """Otvorí stránku a počká, kým ju prevezme appka. Vráti zoznam ❌ problémov."""
        page.mz_chyby = []
        page.mz_index = 0
        try:
            page.goto(url, wait_until="load")
        except Exception as e:
            # predošlá stránka mohla ešte dokončiť vlastný krok histórie (zavretie panela
            # obľúbených robí Späť) — ten otvorenie preruší (ERR_ABORTED); skúsi sa ešte raz
            if "ABORTED" not in str(e).upper():
                raise
            page.wait_for_timeout(1000)
            page.mz_chyby = []
            page.goto(url, wait_until="load")
        try:
            page.wait_for_function(MOBIL_APPKA, timeout=cakaj_s * 1000)
        except Exception:
            return ["appka stránku neprevzala (statická stránka ostala, alebo appka spadla)"]
        try:
            page.wait_for_selector("#main a[href], #main .empty", state="visible", timeout=15_000)
        except Exception:
            return ["po prevzatí appkou je stránka prázdna (#main bez obsahu)"]
        page.wait_for_timeout(700)
        return []

    def mobil_pretecenie(self, page, z):
        """❌ 1) Vodorovné pretečenie. Vráti text problému alebo ''."""
        r = page.evaluate(MOBIL_PRETECENIE_JS, z["okno"][0])
        if r["sw"] > r["iw"] + 1 or r["iw"] > z["okno"][0] + 1 or r["prvky"]:
            return (f"stránka sa hýbe do strany: šírka obsahu {r['sw']} px > obrazovka {min(r['iw'], z['okno'][0])} px"
                    + (f"; presahuje: {', '.join(r['prvky'])}" if r["prvky"] else ""))
        return ""

    @staticmethod
    def mobil_tukni(page, sel, popis):
        """Ťuk prstom na prvok; keď sa nedá (prekrytý, mimo obrazovky…), zrozumiteľná ❌."""
        try:
            page.locator(sel).first.tap(timeout=8_000)
        except Exception:
            raise Zlyhanie(f"na {popis} sa nedá ťuknúť (prvok je prekrytý, mimo obrazovky alebo chýba)") from None

    def mobil_snimka(self, page, meno):
        """Zmenšená snímka (CSS pixely, nie DPR 3) do prílohy test-hlbkovy."""
        try:
            page.screenshot(path=os.path.join(self.vystup, meno + ".png"), scale="css", full_page=False,
                            animations="disabled", timeout=15_000)
            self.mobil_snimky += 1
        except Exception as e:  # snímka je len pomôcka, test kvôli nej nespadne
            self.log.append(f"snímka {meno} sa nepodarila: {e}")

    def mobil_zariadenie(self, z):
        """Jedno zariadenie (A–E′): vráti fn(pokus) pre self.kontrola (pri ❌ sa zariadenie
        skúsi ešte raz celé; v tabuľke ostane výsledok posledného pokusu)."""
        def fn(pokus):
            bunky = {}                       # stránka → (stav, poznámka)
            chyby, varov, plochy = [], [], []
            self.mobil_matica[z["kod"]] = bunky
            self.mobil_plochy[z["kod"]] = plochy

            def zapis(k, stav, text=""):
                st, pozn = bunky.get(k, ("ok", ""))
                poradie = {"ok": 0, "warn": 1, "fail": 2}
                if poradie[stav] > poradie[st]:
                    st = stav
                if text:
                    pozn = (pozn + "; " if pozn else "") + text
                    (chyby if stav == "fail" else varov).append(f"{MOBIL_STLPCE.get(k, k)}: {text}")
                bunky[k] = (st, pozn)

            def chyba_snimka(page, k):
                self.mobil_snimka(page, f"i-{z['subor']}-chyba-{k}")

            def cast(k, page, fn, *a):
                """Jedna časť (hľadanie, hlavička, admin…): nečakaná chyba = ❌ len tejto časti."""
                try:
                    fn(*a)
                except Exception as e:
                    zapis(k, "fail", (str(e) if isinstance(e, Zlyhanie) else f"{type(e).__name__}: {e}").strip().splitlines()[0][:200])
                    chyba_snimka(page, k)

            with self.mobil_prehliadac(z["prehliadac"]) as browser:
                ctx = self.mobil_kontext(browser, z)
                try:
                    page = self.mobil_stranka(ctx)
                    # --- pevné stránky: prevzatie, pretečenie, konzola (+ písmo, plochy, štítok)
                    for k in z["stranky"]:
                        url = self.mobil_adresy.get(k)
                        if not url:
                            continue
                        problemy = self.mobil_otvor(page, url)
                        if not problemy:
                            p = self.mobil_pretecenie(page, z)
                            if p:
                                problemy.append(p)
                        problemy += page.mz_chyby[:5]
                        for p in problemy:
                            zapis(k, "fail", p)
                        if problemy:
                            chyba_snimka(page, k)
                            continue
                        zapis(k, "ok")
                        if k in ("domov", "liga"):
                            self.mobil_snimka(page, f"i-{z['subor']}-{k}")
                        if k in ("domov", "liga", "tipovanie") and z["pismo"]:
                            male = page.evaluate(MOBIL_PISMO_JS)
                            if male:
                                zapis(k, "warn", "písmo < 12 px: " + ", ".join(male[:6]))
                        if k == "domov" and z["kontrast"]:
                            for t in page.evaluate(MOBIL_KONTRAST_JS):
                                if t["k"] < 4.5:
                                    zapis(k, "warn", f"kontrast „{t['text']}“ {t['k']:.2f} : 1 (< 4,5)")
                        if k in ("liga", "bangl", "domov"):
                            plochy.extend(page.evaluate(MOBIL_PLOCHY_JS))
                        if k in ("bangl", "liga") and z["kod"] == "B":
                            prekryv = page.evaluate(MOBIL_STITOK_JS)
                            if prekryv:
                                zapis(k, "warn", "štítok LIGA prekrýva názov: " + ", ".join(prekryv[:3]))
                    # --- hľadanie (celé dáta): „slovan“, „brondby“, nezmysel
                    if "hladanie" in z["stranky"]:
                        cast("hladanie", page, self.mobil_hladanie, page, z, zapis, chyba_snimka)
                    # --- ❌ 6) hlavička sa po posune zbalí, lupa celá na obrazovke, (B) ☆ vedľa loga
                    cast("hlavicka", page, self.mobil_hlavicka, page, z, zapis, chyba_snimka)
                    # --- ❌ 5) písmo v hľadaní ≥ 16 px (iPhone by inak pri ťuknutí priblížil)
                    px = float(page.evaluate("parseFloat(getComputedStyle(document.getElementById('srch')).fontSize)"))
                    if px < 16:
                        zapis("hlavicka", "fail", f"písmo v hľadaní {px:g} px (treba ≥ 16 px — iPhone pri ťuknutí stránku priblíži)")
                    # --- ❌ 7) okno s heslom (admin) — NEPRIHLASUJE sa
                    if z["admin"]:
                        cast("admin", page, self.mobil_admin, page, z, zapis, chyba_snimka, plochy)
                    # --- ❌ 4) Späť krok po kroku + Späť pri paneli obľúbených
                    if z["spat"]:
                        self.mobil_spat(ctx, z, zapis)
                    # --- ❌ 8) panel obľúbených (2× ★ len v prehliadači testu)
                    if z["oblubene"]:
                        cast("oblubene", page, self.mobil_oblubene, page, z, zapis, chyba_snimka, plochy)
                    # --- ❌ vzorka hlbokých stránok: pretečenie a chyby v konzole
                    vz = self.mobil_vzorky.get(z["kod"]) or []
                    for url in vz:
                        problemy = self.mobil_otvor(page, url)
                        if not problemy:
                            p = self.mobil_pretecenie(page, z)
                            if p:
                                problemy.append(p)
                        problemy += page.mz_chyby[:3]
                        for p in problemy:
                            zapis("vzorka", "fail", f"{urllib.parse.unquote(self.cesta(url))}: {p}")
                        if problemy:
                            chyba_snimka(page, "vzorka")
                    if vz and "vzorka" not in bunky:
                        zapis("vzorka", "ok")
                        bunky["vzorka"] = ("ok", f"{len(vz)} stránok")
                finally:
                    ctx.close()
                # --- ⚠️ 12) WebKit: index.html (appka) sa pri príchode z Googlu stiahne len raz
                if z["prehliadac"] == "webkit" and self.mobil_adresy.get("krajina"):
                    ctx = self.mobil_kontext(browser, z)
                    try:
                        page = self.mobil_stranka(ctx)
                        self.mobil_otvor(page, self.mobil_adresy["krajina"])
                        page.wait_for_timeout(1500)
                        if page.mz_index > 1:
                            zapis("krajina", "warn", f"Safari stiahol appku index.html {page.mz_index}× (má raz — preload)")
                        self.mobil_index[z["kod"]] = page.mz_index
                    finally:
                        ctx.close()
            # ⚠️ 9) dotykové plochy pod dohodnutou mierou
            male = [p for p in plochy if p["w"] < p["mw"] or p["h"] < p["mh"]]
            for p in self.mobil_unik(male):
                zapis("plochy", "warn", f"{p['co']} {p['w']}×{p['h']} (má byť ≥ {p['mw']}×{p['mh']})")
            if "plochy" not in bunky and plochy:
                bunky["plochy"] = ("ok", "")
            if chyby:
                raise Zlyhanie(f"{z['nazov']}: " + " | ".join(chyby[:4]) + (f" … (spolu {len(chyby)})" if len(chyby) > 4 else ""))
            hotovo = f"{len([b for b in bunky if b not in ('plochy',)])} kontrol OK"
            if varov:
                return "warn", f"{hotovo}; ⚠️ " + " | ".join(varov[:4]) + (f" … (spolu {len(varov)})" if len(varov) > 4 else "")
            return "ok", hotovo
        return fn

    @staticmethod
    def mobil_unik(plochy):
        """Rovnaký prvok (napr. ★ na viacerých kartách) len raz — s najmenšími rozmermi."""
        out = {}
        for p in plochy:
            k = p["co"]
            if k not in out or p["w"] * p["h"] < out[k]["w"] * out[k]["h"]:
                out[k] = p
        return list(out.values())

    def mobil_hladanie(self, page, z, zapis, chyba_snimka):
        problemy = []
        page.mz_chyby = []
        page.goto(self.base, wait_until="load")
        try:
            page.wait_for_function(MOBIL_CELE_DATA, timeout=60_000)
        except Exception:
            zapis("hladanie", "fail", "appka do 60 s nestiahla celé dáta (hľadanie by ukazovalo len „Načítavam…“)")
            chyba_snimka(page, "hladanie")
            return
        vysl = []
        for q, cakam in (("slovan", True), ("brondby", True), ("qxzw9vbk", False)):
            page.fill("#srch", q)
            try:
                page.wait_for_function("""(c) => { const m = document.getElementById('main');
                    return c ? m.querySelectorAll('a[href]').length > 0 && !m.querySelector('.empty')
                             : !!m.querySelector('.empty'); }""", arg=cakam, timeout=10_000)
            except Exception:
                problemy.append(f"„{q}“: " + ("žiadny výsledok" if cakam else "chýba veta „nič sa nenašlo“"))
                continue
            page.wait_for_timeout(400)
            p = self.mobil_pretecenie(page, z)
            if p:
                problemy.append(f"„{q}“: {p}")
            if q == "slovan":
                self.mobil_snimka(page, f"i-{z['subor']}-hladanie")
            vysl.append(f"{q} {page.locator('#main a[href]').count()}" if cakam else "nič")
        problemy += page.mz_chyby[:3]
        page.fill("#srch", "")
        for p in problemy:
            zapis("hladanie", "fail", p)
        if problemy:
            chyba_snimka(page, "hladanie")
        else:
            zapis("hladanie", "ok")
            bunky_pozn = ", ".join(vysl)
            self.mobil_matica[z["kod"]]["hladanie"] = ("ok", bunky_pozn)

    def mobil_hlavicka(self, page, z, zapis, chyba_snimka):
        """❌ 6) Hlavička sa po posune zbalí (aj na šírku), lupa v zbalenej hlavičke je celá
        na obrazovke, na úzkom displeji (B) je „☆ N“ vedľa loga. ⚠️ hlavička > 30 % výšky."""
        for k in ("bangl", "liga", "krajina", "domov"):
            if not self.mobil_adresy.get(k):
                continue
            if self.mobil_otvor(page, self.mobil_adresy[k]):
                continue
            if page.evaluate("document.documentElement.scrollHeight - innerHeight") > 450:
                break
        else:
            zapis("hlavicka", "warn", "žiadna stránka nie je dosť dlhá na posun — zbalenie nekontrolované")
            return
        s0 = page.evaluate(MOBIL_HLAVICKA_JS)
        if s0["min"]:
            zapis("hlavicka", "fail", "hlavička je zbalená už na vrchu stránky")
        if z["kod"] == "B" and not s0["favPriLogu"]:
            zapis("hlavicka", "fail", "„☆ N“ nie je vedľa loga (spadlo do vlastného riadku)")
        if s0["h"] > 0.3 * s0["vh"]:
            zapis("hlavicka", "warn", f"plná hlavička zaberá {100 * s0['h'] / s0['vh']:.0f} % výšky ({s0['h']} px)")
        for y in range(0, 401, 50):          # posun nadol po krokoch ako prstom
            page.evaluate("y => scrollTo(0, y)", y)
            page.wait_for_timeout(60)
        page.wait_for_timeout(300)
        s1 = page.evaluate(MOBIL_HLAVICKA_JS)
        if not s1["min"]:
            zapis("hlavicka", "fail", f"po posune o 400 px sa hlavička nezbalila (výška {s0['h']} px)")
            chyba_snimka(page, "hlavicka")
        elif not s1["lupaCela"]:
            zapis("hlavicka", "fail", f"lupa v zbalenej hlavičke nie je celá na obrazovke ({s1['lupa']})")
            chyba_snimka(page, "hlavicka")
        else:
            zapis("hlavicka", "ok")
            st, pozn = self.mobil_matica[z["kod"]]["hlavicka"]
            self.mobil_matica[z["kod"]]["hlavicka"] = (st, pozn or f"{s0['h']} → {s1['h']} px")
        page.evaluate("scrollTo(0, 0)")
        page.wait_for_timeout(200)

    def mobil_admin(self, page, z, zapis, chyba_snimka, plochy):
        """❌ 7) /#admin: okno s heslom sa zmestí, na šírku je hore, krížik ho zavrie. Bez prihlásenia."""
        page.mz_chyby = []
        page.goto(self.base + "#admin", wait_until="load")
        try:
            page.wait_for_selector("#pwScreen", state="visible", timeout=15_000)
        except Exception:
            zapis("admin", "fail", "okno s heslom sa po /#admin neotvorilo")
            chyba_snimka(page, "admin")
            return
        page.wait_for_timeout(400)
        s = page.evaluate("""() => { const b = document.querySelector('#pwScreen .pw-box').getBoundingClientRect(),
            x = document.getElementById('pwClose').getBoundingClientRect(), i = document.getElementById('pwIn').getBoundingClientRect();
            return {l: b.left, r: b.right, t: b.top, b: b.bottom, vw: innerWidth, vh: innerHeight,
                    xw: Math.round(x.width), xh: Math.round(x.height), heslo: Math.round(i.bottom)}; }""")
        if s["l"] < -1 or s["r"] > s["vw"] + 1 or s["t"] < -1 or s["b"] > s["vh"] + 1:
            zapis("admin", "fail", f"okno s heslom sa nezmestí na obrazovku ({s['l']:.0f}–{s['r']:.0f} × {s['t']:.0f}–{s['b']:.0f} px)")
            chyba_snimka(page, "admin")
        if z["okno"][0] > z["okno"][1] and s["t"] > 0.25 * s["vh"]:
            zapis("admin", "fail", f"na šírku nie je okno s heslom hore (začína na {s['t']:.0f} px z {s['vh']} — klávesnica by prekryla heslo)")
            chyba_snimka(page, "admin")
        plochy.append({"co": "krížik okna s heslom", "w": s["xw"], "h": s["xh"], "mw": 44, "mh": 44})
        self.mobil_tukni(page, "#pwClose", "krížik okna s heslom")
        try:
            page.wait_for_selector("#pwScreen", state="hidden", timeout=5_000)
        except Exception:
            zapis("admin", "fail", "krížik okno s heslom nezavrel")
            chyba_snimka(page, "admin")
        for p in page.mz_chyby[:3]:
            zapis("admin", "fail", p)
        if "admin" not in self.mobil_matica[z["kod"]]:
            zapis("admin", "ok")

    def mobil_spat(self, ctx, z, zapis):
        """❌ 4) domov → šport → krajina → liga (s posunom); na lige Späť pri otvorenom paneli
        obľúbených len zavrie panel (Zadanie 47b); potom 3× Späť vráti krok po kroku aj posun (Zadanie 30)."""
        kroky = [k for k in ("sport", "krajina", "spat_liga") if self.mobil_adresy.get(k)]
        if len(kroky) < 3:
            zapis("spat", "warn", "chýba niektorá stránka cesty — Späť nekontrolované")
            return
        page = self.mobil_stranka(ctx)
        try:
            page.goto(self.base, wait_until="load")
            page.wait_for_function(MOBIL_CELE_DATA, timeout=60_000)
            page.wait_for_timeout(500)
            cesta = []

            def posun(karta=None):
                if karta is not None:   # dlaždica dole na obrazovke — ťuk potom stránkou nepohne
                    karta.evaluate("e => e.scrollIntoView({block: 'end'})")
                else:
                    ciel = page.evaluate("Math.max(0, Math.min(500, document.documentElement.scrollHeight - innerHeight - 10))")
                    page.evaluate("y => scrollTo(0, y)", ciel)
                page.wait_for_timeout(400)
                return page.evaluate("[location.pathname, Math.round(scrollY)]")

            for i, k in enumerate(kroky):
                ciel = urllib.parse.urlsplit(self.mobil_adresy[k]).path
                karta = page.locator(f'#main a[href="{ciel}"]') if i == 0 else None
                if karta is not None and karta.count():
                    cesta.append(posun(karta.first))
                    karta.first.tap()             # domov → šport ťuknutím na dlaždicu
                else:
                    cesta.append(posun())
                    page.evaluate("id => navigate(id)", MOBIL_STRANKY[k][0])   # ako ťuk na kartu hlbšie
                page.wait_for_function("p => decodeURI(location.pathname) === decodeURI(p)", arg=ciel, timeout=10_000)
                page.wait_for_timeout(600)
            # liga: panel obľúbených otvorený → Späť ho len zavrie, stránka ostane (Zadanie 47b)
            liga = page.evaluate("location.pathname")
            self.mobil_tukni(page, "#hFav", "„☆ N“ (obľúbené) v hlavičke")
            page.wait_for_selector("#favPanel", state="visible", timeout=5_000)
            page.wait_for_timeout(300)
            page.evaluate("history.back()")
            page.wait_for_timeout(1000)
            st = page.evaluate("[!document.getElementById('favPanel').hidden, location.pathname]")
            if st[0] or st[1] != liga:
                raise Zlyhanie(f"Späť pri otvorenom paneli obľúbených: panel {'ostal otvorený' if st[0] else 'sa zavrel'}, "
                               f"stránka {urllib.parse.unquote(st[1])} (čakám len zavretie panela na {urllib.parse.unquote(liga)})")
            # 3× Späť krok po kroku s obnoveným posunom (Zadanie 30)
            for p0, y0 in reversed(cesta):
                page.evaluate("history.back()")
                try:
                    page.wait_for_function("p => decodeURI(location.pathname) === decodeURI(p)", arg=p0, timeout=8_000)
                except Exception:
                    raise Zlyhanie(f"Späť nevrátil na {urllib.parse.unquote(p0)} (ostal na "
                                   f"{urllib.parse.unquote(page.evaluate('location.pathname'))})") from None
                page.wait_for_timeout(900)
                y = page.evaluate("Math.round(scrollY)")
                if abs(y - y0) > 40:
                    raise Zlyhanie(f"Späť na {urllib.parse.unquote(p0)} neobnovil posun ({y} px, bol {y0} px)")
            for p in page.mz_chyby[:3]:
                zapis("spat", "fail", p)
            if "spat" not in self.mobil_matica[z["kod"]]:
                zapis("spat", "ok")
                self.mobil_matica[z["kod"]]["spat"] = ("ok", "panel, potom 3× Späť s posunom")
        except Zlyhanie as e:
            zapis("spat", "fail", str(e))
            self.mobil_snimka(page, f"i-{z['subor']}-chyba-spat")
        except Exception as e:
            zapis("spat", "fail", f"{type(e).__name__}: {str(e).splitlines()[0][:200]}")
            self.mobil_snimka(page, f"i-{z['subor']}-chyba-spat")
        finally:
            page.close()

    def mobil_oblubene(self, page, z, zapis, chyba_snimka, plochy):
        """❌ 8) Na lige pridá ★ dvom linkám (len v prehliadači testu), otvorí panel — zmestí sa —
        a zavrie ho krížikom."""
        url = self.mobil_adresy.get("liga") or self.mobil_adresy.get("bangl")
        if not url:
            return
        if self.mobil_otvor(page, url):
            zapis("oblubene", "fail", "stránka ligy sa neotvorila")
            return
        try:
            page.wait_for_function(MOBIL_CELE_DATA, timeout=60_000)
            hviezdy = page.locator("#main .card-link > .star")
            if hviezdy.count() < 2:
                zapis("oblubene", "warn", "na stránke ligy nie sú 2 hviezdičky — panel nekontrolovaný")
                return
            for i in range(2):
                hviezdy.nth(i).scroll_into_view_if_needed()
                try:
                    hviezdy.nth(i).tap(timeout=8_000)
                except Exception:
                    raise Zlyhanie(f"na ★ na karte č. {i + 1} sa nedá ťuknúť (prekrytá alebo mimo obrazovky)") from None
                page.wait_for_timeout(300)
            n = page.locator("#hFavN").inner_text().strip()
            if n != "2":
                zapis("oblubene", "fail", f"po ťuknutí na 2× ★ ukazuje hlavička „{n}“ (čakám 2)")
            page.evaluate("scrollTo(0, 0)")
            page.wait_for_timeout(300)
            self.mobil_tukni(page, "#hFav", "„☆ N“ (obľúbené) v hlavičke")
            page.wait_for_selector("#favPanel", state="visible", timeout=5_000)
            page.wait_for_timeout(400)
            s = page.evaluate("""() => { const p = document.getElementById('favPanel').getBoundingClientRect(),
                x = document.querySelector('#favPanel .fp-x').getBoundingClientRect();
                return {l: p.left, r: p.right, t: p.top, vw: innerWidth, vh: innerHeight,
                        xl: x.left, xr: x.right, xt: x.top, xb: x.bottom, xw: Math.round(x.width), xh: Math.round(x.height),
                        riadky: document.querySelectorAll('#favPanel a[href]').length}; }""")
            if s["l"] < -1 or s["r"] > s["vw"] + 1 or s["xl"] < -1 or s["xr"] > s["vw"] + 1 or s["xt"] < -1 or s["xb"] > s["vh"] + 1:
                zapis("oblubene", "fail", f"panel obľúbených sa nezmestí (panel {s['l']:.0f}–{s['r']:.0f} px, krížik "
                                          f"{s['xl']:.0f}–{s['xr']:.0f} × {s['xt']:.0f}–{s['xb']:.0f} px, obrazovka {s['vw']}×{s['vh']})")
                chyba_snimka(page, "oblubene")
            plochy.append({"co": "krížik panela obľúbených", "w": s["xw"], "h": s["xh"], "mw": 44, "mh": 44})
            self.mobil_tukni(page, "#favPanel .fp-x", "krížik panela obľúbených")
            try:
                page.wait_for_selector("#favPanel", state="hidden", timeout=5_000)
            except Exception:
                zapis("oblubene", "fail", "krížik panel obľúbených nezavrel")
                chyba_snimka(page, "oblubene")
            page.wait_for_timeout(800)   # zavretie panela urobí krok Späť v histórii — nech dobehne
            for p in page.mz_chyby[:3]:
                zapis("oblubene", "fail", p)
            if "oblubene" not in self.mobil_matica[z["kod"]]:
                zapis("oblubene", "ok")
                self.mobil_matica[z["kod"]]["oblubene"] = ("ok", f"2× ★, panel {s['riadky']} riadkov, krížik")
        except Exception as e:
            zapis("oblubene", "fail", f"{type(e).__name__}: {str(e).splitlines()[0][:200]}")
            chyba_snimka(page, "oblubene")

    # ⚠️ 13) výkon na pomalom Androide — prvý obsah, prevzatie appkou, celé dáta, stiahnuté
    def mobil_vykon_meraj(self, browser, z, url):
        ctx = browser.new_context(viewport={"width": z["okno"][0], "height": z["okno"][1]},
                                  device_scale_factor=z["dpr"], is_mobile=True, has_touch=True, user_agent=z["ua"])
        ctx.add_init_script(SW_VYP_SKRIPT)   # Zadanie 50: meria sa prvá návšteva (bez service workera)
        try:
            page = ctx.new_page()
            cdp = ctx.new_cdp_session(page)
            cdp.send("Network.enable")
            cdp.send("Network.setCacheDisabled", {"cacheDisabled": True})
            # blokovanie cez CDP (nie route) — route by obchádzala spomalenie siete
            cdp.send("Network.setBlockedURLs", {"urls": [f"*{b}*" for b in BLOKOVANE]})
            cdp.send("Network.emulateNetworkConditions", SLOW_4G)
            cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
            bajty = [0]
            cdp.on("Network.loadingFinished", lambda e: bajty.__setitem__(0, bajty[0] + (e.get("encodedDataLength") or 0)))
            page.goto(url, wait_until="commit", timeout=60_000)
            vysl = {"fcp": None, "app": None, "data": None, "mb": None}
            koniec = time.time() + 60
            while time.time() < koniec:
                try:
                    s = page.evaluate(MOBIL_VYKON_JS)
                except Exception:
                    page.wait_for_timeout(100)
                    continue
                if vysl["fcp"] is None and s["fcp"]:
                    vysl["fcp"] = s["fcp"] / 1000
                if vysl["app"] is None and s["app"]:
                    vysl["app"] = s["t"] / 1000
                if s["full"]:
                    vysl["data"] = s["t"] / 1000
                    break
                page.wait_for_timeout(100)
            page.wait_for_timeout(500)
            vysl["mb"] = bajty[0] / 1e6
            return vysl
        finally:
            ctx.close()

    def mobil_vykon(self, pokus):
        z = MOBIL_POMALY
        bunky = {}
        self.mobil_matica["F"] = bunky
        ciele = [("domov", self.base, MOBIL_PRAH_APP_DOMOV)]
        if self.mobil_adresy.get("krajina"):
            ciele.append(("krajina", self.mobil_adresy["krajina"], MOBIL_PRAH_APP_HLBOKA))
        varov, texty, chyby = [], [], []
        with self.mobil_prehliadac("chromium") as browser:
            for k, url, prah_app in ciele:
                for _meranie in (1, 2):   # pri prekročení prahu ešte raz (živý web kolíše) — platí druhé meranie
                    v = self.mobil_vykon_meraj(browser, z, url)
                    zle = []
                    if v["app"] is None:
                        zle.append(("fail", "appka do 60 s stránku neprevzala"))
                    else:
                        if v["fcp"] is not None and v["fcp"] > MOBIL_PRAH_FCP:
                            zle.append(("warn", f"prvý obsah {v['fcp']:.1f} s (> {MOBIL_PRAH_FCP:g} s)"))
                        if v["app"] > prah_app:
                            zle.append(("warn", f"prevzatie appkou {v['app']:.1f} s (> {prah_app:g} s)"))
                        if v["data"] is None or v["data"] > MOBIL_PRAH_DATA:
                            zle.append(("warn", "celé dáta " + (f"{v['data']:.1f} s" if v["data"] else "nad 60 s")
                                        + f" (> {MOBIL_PRAH_DATA:g} s)"))
                        if v["mb"] > MOBIL_PRAH_MB:
                            zle.append(("warn", f"stiahnuté {v['mb']:.2f} MB (> {MOBIL_PRAH_MB:g} MB)"))
                    if not zle:
                        break
                cisla = (f"FCP {v['fcp']:.1f} s, appka {v['app']:.1f} s, " if v["fcp"] and v["app"] else "") \
                    + (f"dáta {v['data']:.1f} s, " if v["data"] else "") + f"{v['mb']:.2f} MB"
                texty.append(f"{MOBIL_STLPCE[k]}: {cisla}")
                stav = "fail" if any(s == "fail" for s, _ in zle) else ("warn" if zle else "ok")
                bunky[k] = (stav, cisla + ("; " + "; ".join(t for _, t in zle) if zle else ""))
                (chyby if stav == "fail" else varov).extend(f"{MOBIL_STLPCE[k]}: {t}" for _, t in zle)
        self.info.append("**Mobil F (pomalý Android: procesor 4×, Slow 4G):** " + " · ".join(texty)
                         + f" — prahy ⚠️: FCP {MOBIL_PRAH_FCP:g} s, appka {MOBIL_PRAH_APP_DOMOV:g}/{MOBIL_PRAH_APP_HLBOKA:g} s,"
                         f" dáta {MOBIL_PRAH_DATA:g} s, {MOBIL_PRAH_MB:g} MB (Zadanie 47a: 0,7–0,9 s, 0,7–2,9 s, 9,4–13,8 s, 1,3 MB)")
        if chyby:
            raise Zlyhanie("; ".join(chyby))
        if varov:
            return "warn", "; ".join(varov)
        return "ok", " · ".join(texty)

    def mobil(self):
        """i) Mobilné zariadenia — každé zariadenie je samostatný riadok (a pri ❌ sa skúsi
        ešte raz samo, nie celá mobilná časť)."""
        t0 = time.time()
        self.mobil_matica, self.mobil_plochy, self.mobil_index = {}, {}, {}
        self.mobil_snimky = 0
        self.mobil_adresy, self.mobil_vzorky = {}, {}
        vyber = set(self.mobil_vyber or [z["kod"] for z in MOBIL_ZARIADENIA] + ["F"])
        try:
            self.mobil_priprav()
        except Exception as e:
            self.vysledky.append(("fail", "i) Mobil — príprava (adresy stránok)", f"{type(e).__name__}: {e}"[:400]))
            self.log.append(traceback.format_exc())
            return
        for z in MOBIL_ZARIADENIA:
            if z["kod"] in vyber:
                self.kontrola(f"i) Mobil {z['kod']} — {z['nazov']}", self.mobil_zariadenie(z))
        if "F" in vyber:
            self.kontrola(f"i) Mobil F — {MOBIL_POMALY['nazov']} (len výkon)", self.mobil_vykon, pri_chybe="fail")
        self.mobil_cas = time.time() - t0
        self.info.append(f"**Mobil i):** trvanie {self.mobil_cas / 60:.1f} min, snímok {self.mobil_snimky} (príloha test-hlbkovy)")

    def mobil_tabulka(self):
        """Tabuľka zariadenie × stránka s ✅/⚠️/❌ (do Summary) + zoznam dotykových plôch."""
        if not getattr(self, "mobil_matica", None):
            return []
        ikona = {"ok": "✅", "warn": "⚠️", "fail": "❌"}
        stlpce = [k for k in MOBIL_STLPCE if any(k in b for b in self.mobil_matica.values())]
        r = ["", "### i) Mobilné zariadenia — zariadenie × stránka", "",
             "| Zariadenie | " + " | ".join(MOBIL_STLPCE[k] for k in stlpce) + " |",
             "|---|" + "---|" * len(stlpce)]
        nazvy = {z["kod"]: z["nazov"] for z in MOBIL_ZARIADENIA + [MOBIL_POMALY]}
        for kod, bunky in self.mobil_matica.items():
            r.append(f"| **{kod}** {nazvy.get(kod, '')} | " + " | ".join(
                (ikona[bunky[k][0]] + (" " + bunky[k][1].replace("|", "/")[:120] if bunky[k][0] != "ok" or kod == "F" else ""))
                if k in bunky else "·" for k in stlpce) + " |")
        r.append("")
        r.append("✅ OK · ⚠️ drobnosť (test ostane zelený) · ❌ rozbité · „·“ = na tomto zariadení sa nekontroluje")
        riadky = []
        for kod, pl in self.mobil_plochy.items():
            for p in sorted(self.mobil_unik(pl), key=lambda x: x["co"]):
                zle = p["w"] < p["mw"] or p["h"] < p["mh"]
                riadky.append(f"{'⚠️' if zle else '✅'} {kod}: {p['co']} {p['w']}×{p['h']} px (miera {p['mw']}×{p['mh']})")
        if riadky:
            self.zoznamy.append((f"i) Dotykové plochy — rozmery ({len(riadky)})", riadky))
        if self.mobil_index:
            self.info.append("**Mobil — Safari (WebKit) stiahol appku index.html:** "
                             + ", ".join(f"{k} {v}×" for k, v in self.mobil_index.items()))
        return r

    # ------------------------------------------------ hlavný beh
    def spusti(self):
        for pokus in (1, 2):
            try:
                self.zisti_jazyk()
                break
            except Exception as e:
                self.log.append(f"[pokus {pokus}] Domovská stránka: {e}")
                if pokus == 2:
                    self.vysledky.append(("fail", "Domovská stránka", str(e)[:400]))
                    return
                time.sleep(5)
        if self.len_mobil:   # ručné spustenie „len_mobil“: len kontrola i)
            self.mobil()
            return
        self.kontrola("a) sitemap.xml a všetky jej adresy (HTTP 200)", self.sitemap)
        self.kontrola("b) Titulok, canonical, hreflang, páry SK ↔ EN", self.hlavicky)
        self.kontrola("c) robots.txt", self.robots)
        self.kontrola("d) Verzia data.json", self.verzia)
        self.kontrola("e) Presmerovania http→https, www→bez www", self.presmerovania)
        self.kontrola("f) Ikonky /ikony/ a vlajky /vlajky/", self.ikony_vlajky)
        self.kontrola("g) Appka ↔ generátor: adresy a titulky všetkých stránok", self.zrkadlo)
        self.kontrola("h) Obsah stránok appka ↔ statika: zoznam, poradie a počty kariet", self.obsah)
        self.kontrola("j) Web ako aplikácia (PWA): manifest na všetkých stránkach, sw.js", self.pwa)
        self.mobil()

    def zhrnutie(self, trvanie):
        ikona = {"ok": "✅", "warn": "⚠️", "fail": "❌"}
        chyby = sum(1 for s, *_ in self.vysledky if s == "fail")
        varov = sum(1 for s, *_ in self.vysledky if s == "warn")
        if chyby:
            celkovo = f"❌ **Web má problém** — chýb: {chyby}, varovaní: {varov}"
        elif varov:
            celkovo = f"✅ **Web je v poriadku** (varovaní: {varov} — pozri ⚠️ nižšie)"
        else:
            celkovo = "✅ **Web je v poriadku** — všetky kontroly prešli"
        r = [f"## Hĺbkový test webu {self.nazov_webu or ''} — {self.base}", "", celkovo, "",
             "| | Kontrola | Výsledok |", "|---|---|---|"]
        for stav, nazov, detail in self.vysledky:
            r.append(f"| {ikona[stav]} | {nazov} | {detail.replace('|', '/')} |")
        r += self.mobil_tabulka()
        r.append("")
        r += [f"- {i}" for i in self.info]
        r.append(f"- Jazyk webu: **{self.lang}**, čas testu: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC, "
                 f"trvanie {trvanie / 60:.1f} min")
        for nadpis, riadky in self.zoznamy:
            r += ["", f"<details><summary>{html.escape(nadpis)}</summary>", ""]
            r += [f"- {html.escape(x, quote=False)}" for x in riadky]
            r += ["", "</details>"]
        text = "\n".join(r) + "\n"
        print("\n" + text)
        with open(os.path.join(self.vystup, "chyby.txt"), "w", encoding="utf-8") as f:
            f.write(text + "\n\nPODROBNOSTI:\n" + ("\n".join(self.log) or "(bez chýb)") + "\n")
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
                f.write(text)
        return chyby


def main():
    ap = argparse.ArgumentParser(description="Hĺbkový test živého webu (raz denne).")
    ap.add_argument("--url", default=os.environ.get("WEB_URL", ""), help="adresa webu, napr. https://sportlinky.sk/")
    ap.add_argument("--vystup", default="test-hlbkovy-vystup", help="priečinok na zoznam chýb (chyby.txt)")
    ap.add_argument("--len-mobil", action="store_true", help="len kontrola i) Mobilné zariadenia (rýchle overenie po zmene webu)")
    ap.add_argument("--zariadenia", default="", help="i) len tieto zariadenia, napr. A,E,F (predvolene všetky)")
    a = ap.parse_args()
    if not a.url:
        sys.exit("Chýba adresa webu (--url alebo WEB_URL).")
    t = Test(a.url, a.vystup)
    t.len_mobil = a.len_mobil or os.environ.get("LEN_MOBIL", "").lower() in ("1", "true", "áno", "ano", "yes")
    t.mobil_vyber = [x.strip() for x in a.zariadenia.split(",") if x.strip()] or None
    t0 = time.time()
    try:
        t.spusti()
    except Exception as e:   # neočakávaná chyba samotného testu = tiež ❌, ale so zhrnutím
        t.vysledky.append(("fail", "Beh testu", f"{type(e).__name__}: {e}"))
        t.log.append(traceback.format_exc())
    sys.exit(1 if t.zhrnutie(time.time() - t0) else 0)


if __name__ == "__main__":
    main()
