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

Spustenie (lokálne):  python testy/test_hlbkovy.py --url https://sportlinky.sk/
Voliteľne:  --vystup test-hlbkovy-vystup   (priečinok na zoznam chýb)
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
from _spolocne import BLOKOVANE, UA_PC, X_TEST, Zlyhanie, meta_z_html, titulok_z_html   # spoločné (Zadanie 36)

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
                "vlajky": set(VLAJKA_RE.findall(text)), "karty": karty_stranky(text, url)}

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
        self.kontrola("a) sitemap.xml a všetky jej adresy (HTTP 200)", self.sitemap)
        self.kontrola("b) Titulok, canonical, hreflang, páry SK ↔ EN", self.hlavicky)
        self.kontrola("c) robots.txt", self.robots)
        self.kontrola("d) Verzia data.json", self.verzia)
        self.kontrola("e) Presmerovania http→https, www→bez www", self.presmerovania)
        self.kontrola("f) Ikonky /ikony/ a vlajky /vlajky/", self.ikony_vlajky)
        self.kontrola("g) Appka ↔ generátor: adresy a titulky všetkých stránok", self.zrkadlo)
        self.kontrola("h) Obsah stránok appka ↔ statika: zoznam, poradie a počty kariet", self.obsah)

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
    a = ap.parse_args()
    if not a.url:
        sys.exit("Chýba adresa webu (--url alebo WEB_URL).")
    t = Test(a.url, a.vystup)
    t0 = time.time()
    try:
        t.spusti()
    except Exception as e:   # neočakávaná chyba samotného testu = tiež ❌, ale so zhrnutím
        t.vysledky.append(("fail", "Beh testu", f"{type(e).__name__}: {e}"))
        t.log.append(traceback.format_exc())
    sys.exit(1 if t.zhrnutie(time.time() - t0) else 0)


if __name__ == "__main__":
    main()
