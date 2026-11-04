#!/usr/bin/env python3
"""
AUTOMATICKÝ TEST ŽIVÉHO WEBU (sportlinky.sk aj sportlinking.com — ten istý súbor).

Spúšťa ho .github/workflows/test-webu.yml po každom nasadení webu (aj po nočnom
builde) alebo ručne. Otvorí ŽIVÝ web v prehliadači Chromium (Playwright) a overí,
že funguje. Nič nemení — web ani súbory v repozitári.

Jazyk webu sa nezisťuje z textov, ale zo štruktúry (<html lang>, og:site_name,
sitemap.xml, data.json), takže ten istý test funguje na SK aj EN webe.

Výsledok:
  ✅ OK         — kontrola prešla
  ⚠️ varovanie  — niečo nie je ideálne, ale web funguje (test ostane zelený)
  ❌ chyba      — web nefunguje, ako má (test skončí červeným krížikom)
Každá kontrola sa pri neúspechu skúsi ešte raz — chyba je až keď zlyhá aj druhý pokus.

Bod 16 (3.11.2026): každá stránka otvorená v prehliadači sa kontroluje aj na porušenia
Content-Security-Policy (zoznam povolených domén) — porušenie = ❌. Kontrola j) overí,
že reklama partnera (banner v slote 1, promo blok v Tipovaní) beží v uzavretom okienku
(<iframe sandbox>). Reklamy sa ani tu NEnačítavajú — overuje sa len kód okienka.

Kontrola k) (3.11.2026, Zadanie 16a): lišta Aktuálne na domove zodpovedá súboru aktualne.json
(EN web ho berie zo SK webu) — vidno len viditeľné položky v ručnom poradí, popis je bublina
(title) na karte. Navyše sa appke podstrčí VYMYSLENÝ aktualne.json (len v prehliadači testu,
web sa nemení) s naplánovanou, skončenou a vypnutou položkou — tie sa nesmú zobraziť.

Kontrola l) (3.11.2026, Zadanie 17): domov má presne toľko dlaždíc (a ikoniek v hlavičke),
koľko koreňových priečinkov bez noTileSk; stránka Aktuálne (SK /aktualne/, EN /live-this-week/)
má H1, jeden zoznam položiek v ručnom poradí z aktualne.json (Zadanie 27: bez skupín podľa
športu — rovnaké poradie v appke aj v statickej stránke), úvodný text POD zoznamom, popisy pod
názvom, skrytú lištu, titulok so športom;
vyhľadávanie nájde položku Aktuálnych; odkaz v pätičke vedie na stránku. Kým priečinok f_ltw
na SK webe nie je (enOnly:true v dátach), časť o stránke sa na SK webe preskočí.

Bod 19 (4.11.2026, Zadanie 24): keď sa ani po 10 minútach čakania neobjaví na webe nová
verzia (Last-Modified index.html starší než štart buildu), je to ❌ — nasadenie sa nepodarilo
a test by inak skúšal starý web. Všetky adresy, ktoré test prečíta z webu (sitemap.xml,
odkazy v stránkach), sa prepíšu na zadanú --url (schéma + doména), takže skúška na inej
adrese (napr. http://localhost:8000/) testuje tú adresu, nie ostrý web.

Spustenie (lokálne):  python testy/test_webu.py --url https://sportlinky.sk/
Voliteľne:  --od 2026-11-02T02:30:00Z  (počkaj, kým živý web nemá novšiu verziu)
            --vystup test-vystup        (priečinok na snímky a zoznam chýb)
Zhrnutie sa zapíše aj do súboru z premennej GITHUB_STEP_SUMMARY (stránka behu v Actions).
"""

import argparse
import email.utils
import html
import json
import os
import random
import re
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright

# ---------------------------------------------------------------- nastavenia
UA_PC = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
         "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
UA_MOBIL = ("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36")
X_TEST = {"X-Test": "sportlinky-test"}   # podľa tejto hlavičky sa dá test odlíšiť od návštevníkov

# Štatistiky a reklamy sa v teste BLOKUJÚ — test nesmie robiť falošné návštevy
# ani falošné zobrazenia reklám.
BLOKOVANE = ("goatcounter.com", "zgo.at", "googletagmanager.com",
             "google-analytics.com", "ban.tipsport.sk")

# bod 16: uzavreté okienko pre reklamu — tieto práva NESMIE mať (videl by stránku /
# presmeroval hlavné okno); a tieto MUSÍ mať (skript beží, klik otvorí novú kartu)
SANDBOX_ZAKAZANE = ("allow-same-origin", "allow-top-navigation")
SANDBOX_POTREBNE = ("allow-scripts", "allow-popups", "allow-popups-to-escape-sandbox")
CSP_META_RE = re.compile(r'<meta\s+http-equiv="Content-Security-Policy"\s+content="([^"]+)"', re.I)
# zachytí porušenie CSP v každom okne aj okienku (prehliadač ho inak len zapíše do konzoly)
CSP_SKRIPT = ("document.addEventListener('securitypolicyviolation', function(e){"
              "console.error('CSP-PORUSENIE: Content Security Policy ' + e.violatedDirective + ' ' + e.blockedURI);});")

NAVIGACIA_MS = 30_000       # max. čas na otvorenie stránky
CAKANIE_MS = 20_000         # max. čas na zobrazenie prvku (dlaždice, výsledky…)
POMALA_S = 15               # stránka pomalšia ako toto = ⚠️ varovanie
MIN_LINIEK = 10_000         # data.json musí mať aspoň toľko liniek
AKT_MASTER = "https://sportlinky.sk/aktualne.json"   # hlavná kópia Aktuálnych (EN web ju číta zo SK webu)
# kód športu → (SK, EN) — len na kontrolu titulku stránky Aktuálne; ROVNAKO ako AKT_SPORTS
# v index.html a generator.py
SPORT_NAZVY = {
    "tenis": ("tenis", "tennis"), "badminton": ("badminton", "badminton"), "squash": ("squash", "squash"),
    "stolny-tenis": ("stolný tenis", "table tennis"), "padel": ("padel", "padel"), "sipky": ("šípky", "darts"),
    "snooker": ("snooker", "snooker"), "atletika": ("atletika", "athletics"), "cyklistika": ("cyklistika", "cycling"),
    "plavanie": ("plávanie", "swimming"), "motosport": ("motošport", "motorsport"), "futbal": ("futbal", "football"),
    "hokej": ("hokej", "ice hockey"), "basketbal": ("basketbal", "basketball"), "hadzana": ("hádzaná", "handball"),
    "volejbal": ("volejbal", "volleyball"), "zimne": ("zimné športy", "winter sports"),
    "bojove": ("bojové športy", "combat sports"), "golf": ("golf", "golf"), "sach": ("šach", "chess"),
    "multisport": ("multišportové podujatie", "multi-sport event"),
}
DEPLOY_MAX_S = 600          # čakanie na obnovenie GitHub Pages (max. 10 min, potom ❌)
DEPLOY_KROK_S = 20          # … skúšať každých 20 s


class Zlyhanie(Exception):
    """Kontrola neprešla (text = vysvetlenie pre zhrnutie)."""


# ---------------------------------------------------------------- pomocníci
def stiahni(url, cache_bust=True, timeout=30):
    """Stiahne adresu bez prehliadača. Vráti (HTTP kód, hlavičky, text)."""
    if cache_bust:
        url += ("&" if "?" in url else "?") + "t=" + str(int(time.time() * 1000))
    req = urllib.request.Request(url, headers={"User-Agent": UA_PC, **X_TEST,
                                               "Cache-Control": "no-cache"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.headers, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read().decode("utf-8", "replace")


def titulok_z_html(text):
    m = re.search(r"<title[^>]*>(.*?)</title>", text, re.S | re.I)
    return html.unescape(m.group(1)).strip() if m else ""


def meta_z_html(text, prop):
    m = re.search(r'<meta[^>]+property="%s"[^>]+content="([^"]*)"' % re.escape(prop), text)
    return html.unescape(m.group(1)).strip() if m else ""


class Test:
    def __init__(self, base, vystup):
        self.base = base if base.endswith("/") else base + "/"
        self.host = urllib.parse.urlsplit(self.base).netloc
        self.schema = urllib.parse.urlsplit(self.base).scheme
        self.vystup = vystup
        os.makedirs(vystup, exist_ok=True)
        self.vysledky = []      # (stav, názov, detail)  stav: ok / warn / fail
        self.info = []          # doplňujúce riadky do zhrnutia
        self.log = []           # podrobný zoznam chýb (chyby.txt)
        self.data = None        # data.json zo živého webu
        self.lang = "sk"
        self.nazov_webu = ""
        self.ligy = []          # adresy z kontroly c) (pre mobil)
        self.adresy = []        # všetky adresy zo sitemap.xml (náhrada pre kontrolu i)
        self.snimky = 0

    def na_url(self, u):
        """Bod 19: absolútnu adresu prečítanú z webu (sitemap.xml, odkaz v stránke)
        prepíše na schému a doménu zo zadanej --url — skúška na inej adrese tak
        testuje tú adresu, nie ostrý web. Relatívne adresy ostávajú bez zmeny."""
        c = urllib.parse.urlsplit((u or "").strip())
        if c.scheme in ("http", "https") and c.netloc:
            return urllib.parse.urlunsplit((self.schema, self.host, c.path, c.query, c.fragment))
        return u

    # ------------------------------------------------ prehliadač
    def smerovanie(self, route):
        """Blokuje štatistiky a reklamy; vlastnej doméne pridá hlavičku X-Test."""
        req = route.request
        host = urllib.parse.urlsplit(req.url).netloc
        if any(host == b or host.endswith("." + b) for b in BLOKOVANE):
            return route.abort()
        if host == self.host:
            return route.continue_(headers={**req.headers, "x-test": X_TEST["X-Test"]})
        return route.continue_()

    def kontext(self, mobil=False):
        if mobil:
            ctx = self.browser.new_context(viewport={"width": 390, "height": 844},
                                           device_scale_factor=2, is_mobile=True,
                                           has_touch=True, user_agent=UA_MOBIL)
        else:
            ctx = self.browser.new_context(viewport={"width": 1366, "height": 900},
                                           user_agent=UA_PC)
        ctx.set_default_navigation_timeout(NAVIGACIA_MS)
        ctx.set_default_timeout(CAKANIE_MS)
        ctx.route("**/*", self.smerovanie)
        ctx.add_init_script(CSP_SKRIPT)
        return ctx

    def stranka(self, ctx, povolene_404=()):
        """Nová karta, ktorá si zbiera chyby JavaScriptu a chybné vlastné súbory."""
        page = ctx.new_page()
        page.chyby_js = []
        page.chyby_suborov = []
        page.chyby_csp = []     # bod 16: porušenia Content-Security-Policy (aj z okienok)

        def on_console(m):
            t = m.text
            if "Content Security Policy" in t and t not in page.chyby_csp:
                page.chyby_csp.append(t)

        def on_resp(r):
            u = urllib.parse.urlsplit(r.url)
            # aktualne.json môže v prechodnom období chýbať (appka vtedy berie data.json)
            if u.path.endswith("/aktualne.json") and r.status == 404:
                return
            if u.netloc == self.host and r.status >= 400 and u.path not in povolene_404:
                page.chyby_suborov.append(f"{r.status} {u.path}")

        def on_fail(rq):
            u = urllib.parse.urlsplit(rq.url)
            if u.netloc == self.host and "ERR_ABORTED" not in (rq.failure or ""):
                page.chyby_suborov.append(f"nenačítané ({rq.failure}) {u.path}")

        page.on("pageerror", lambda e: page.chyby_js.append(str(e)))
        page.on("console", on_console)
        page.on("response", on_resp)
        page.on("requestfailed", on_fail)
        return page

    def snimka(self, page, meno):
        try:
            page.screenshot(path=os.path.join(self.vystup, meno + ".png"), full_page=False)
            self.snimky += 1
        except Exception as e:  # snímka je len pomôcka, test kvôli nej nespadne
            self.log.append(f"snímka {meno} sa nepodarila: {e}")

    @staticmethod
    def over_chyby(page, kde):
        problemy = []
        if page.chyby_js:
            problemy.append("chyby JavaScriptu: " + " | ".join(page.chyby_js[:5]))
        if page.chyby_suborov:
            problemy.append("chybné súbory webu: " + ", ".join(sorted(set(page.chyby_suborov))[:10]))
        if page.chyby_csp:
            problemy.append("porušenia Content-Security-Policy (niečo bolo zablokované): "
                            + " | ".join(c[:200] for c in page.chyby_csp[:5]))
        if problemy:
            raise Zlyhanie(f"{kde} — " + "; ".join(problemy))

    def pocet_odkazov(self, page):
        return page.locator("#main a[href]:visible").count()

    def cakaj_na_appku(self, page):
        """Appka je načítaná, keď je tu vyhľadávacie pole a v #main viditeľné odkazy."""
        page.wait_for_selector("#srch", state="attached")
        page.wait_for_selector("#main a[href]", state="visible")

    # ------------------------------------------------ spúšťanie kontrol
    def kontrola(self, nazov, fn, pri_chybe="fail"):
        """Spustí kontrolu, pri neúspechu ešte raz. pri_chybe = fail (❌) alebo warn (⚠️)."""
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

    # ------------------------------------------------ 0) čakanie na nasadenie
    def cakaj_na_nasadenie(self, od):
        """Živý web má novú verziu, keď je Last-Modified index.html novší ako štart buildu."""
        if not od:
            self.vysledky.append(("ok", "Nová verzia na webe",
                                  "ručné spustenie — bez čakania na nasadenie"))
            return
        start = datetime.fromisoformat(od.replace("Z", "+00:00"))
        koniec = time.time() + DEPLOY_MAX_S
        posledny = "?"
        while True:
            try:
                kod, hlav, _ = stiahni(self.base + "index.html")
                lm = hlav.get("Last-Modified") if hlav else None
                if not lm:
                    self.vysledky.append(("warn", "Nová verzia na webe",
                                          "web neposiela hlavičku Last-Modified — nedá sa overiť, test pokračuje"))
                    return
                posledny = lm
                if email.utils.parsedate_to_datetime(lm) >= start:
                    self.vysledky.append(("ok", "Nová verzia na webe",
                                          f"index.html zmenený {lm} (build začal {od})"))
                    return
            except Exception as e:
                posledny = f"chyba: {e}"
            if time.time() >= koniec:
                # bod 19: nasadenie sa neprejavilo — ❌ (test ďalej beží, ale skúša STARÝ web)
                self.vysledky.append(("fail", "Nová verzia na webe",
                                      f"ani po {DEPLOY_MAX_S // 60} min nie je na webe novšia verzia "
                                      f"(Last-Modified: {posledny}, build začal {od}) — nasadenie sa "
                                      "neprejavilo; ďalšie kontroly skúšajú STARÚ verziu webu"))
                self.log.append(f"[fail] Nová verzia na webe: Last-Modified {posledny}, build začal {od}")
                return
            print(f"čakám na novú verziu webu (Last-Modified: {posledny})…", flush=True)
            time.sleep(DEPLOY_KROK_S)

    # ------------------------------------------------ a) domov
    def domov(self, pokus):
        kod, _, text = stiahni(self.base)
        if kod != 200:
            raise Zlyhanie(f"domovská stránka vrátila HTTP {kod}")
        m = re.search(r'<html[^>]*\slang="([a-z]+)', text)
        self.lang = m.group(1) if m else "sk"
        self.nazov_webu = meta_z_html(text, "og:site_name")
        titulok = titulok_z_html(text)
        if not titulok:
            raise Zlyhanie("domovská stránka nemá titulok")
        if not self.nazov_webu or self.nazov_webu not in titulok:
            raise Zlyhanie(f"titulok „{titulok}“ neobsahuje názov webu „{self.nazov_webu}“")
        # dlaždice sekcií v surovom HTML (pre roboty): odkazy na koreňové sekcie /futbal/…
        main = re.search(r'<main id="main">(.*?)</main>', text, re.S)
        root_path = urllib.parse.urlsplit(self.base).path
        sekcie = set(re.findall(r'<a[^>]+href="(%s[a-z0-9-]+/)"' % re.escape(root_path),
                                main.group(1) if main else ""))
        if len(sekcie) < 3:
            raise Zlyhanie(f"v surovom HTML domova je len {len(sekcie)} dlaždíc sekcií (čakám aspoň 3)")
        if not CSP_META_RE.search(text):
            raise Zlyhanie("domovská stránka nemá Content-Security-Policy (bod 16)")

        ctx = self.kontext()
        try:
            page = self.stranka(ctx)
            t0 = time.time()
            page.goto(self.base, wait_until="load")
            self.cakaj_na_appku(page)
            trvanie = time.time() - t0
            pocet = self.pocet_odkazov(page)
            if pocet < 3:
                raise Zlyhanie(f"po načítaní appky je na domove len {pocet} dlaždíc")
            page.wait_for_timeout(2000)   # nech sa stihnú prejaviť oneskorené chyby
            self.snimka(page, "1-domov-pc")
            self.over_chyby(page, "domov")
        finally:
            ctx.close()
        detail = (f"titulok „{titulok}“, {len(sekcie)} sekcií v HTML, "
                  f"{pocet} dlaždíc po načítaní, jazyk {self.lang}, {trvanie:.1f} s")
        if trvanie > POMALA_S:
            return "warn", "pomalé načítanie — " + detail
        return "ok", detail

    # ------------------------------------------------ b) data.json
    def data_json(self, pokus):
        kod, _, text = stiahni(self.base + "data.json")
        if kod != 200:
            raise Zlyhanie(f"data.json vrátil HTTP {kod}")
        try:
            data = json.loads(text)
        except ValueError as e:
            raise Zlyhanie(f"data.json nie je platný JSON ({e})")
        verzia = data.get("version")
        if not isinstance(verzia, int) or verzia <= 0:
            raise Zlyhanie(f"data.json nemá platnú verziu ({verzia!r})")
        uzly = data.get("nodes") or []
        linky = sum(1 for n in uzly if n.get("type") == "link")
        if linky <= MIN_LINIEK:
            raise Zlyhanie(f"data.json má len {linky} liniek (čakám viac ako {MIN_LINIEK})")
        self.data = data
        pekne = f"{linky:,}".replace(",", " ")
        self.info.append(f"**data.json:** verzia **{verzia}**, liniek **{pekne}**")
        return "ok", f"verzia {verzia}, {linky} liniek, {len(text) / 1e6:.1f} MB"

    # ------------------------------------------------ c) ligy „z Googlu"
    def vyber_stranky(self):
        kod, _, text = stiahni(self.base + "sitemap.xml")
        if kod != 200:
            raise Zlyhanie(f"sitemap.xml vrátil HTTP {kod}")
        # bod 19: adresy zo sitemapy na zadanú --url (inak by sa testoval ostrý web)
        adresy = [self.na_url(html.unescape(u.strip())) for u in re.findall(r"<loc>([^<]+)</loc>", text)]
        self.adresy = adresy
        root_path = urllib.parse.urlsplit(self.base).path

        def hlbka(u):
            p = urllib.parse.urlsplit(u).path[len(root_path):].strip("/")
            return len(p.split("/")) if p else 0

        hlboke = [u for u in adresy if hlbka(u) >= 3]
        if len(hlboke) < 2:
            raise Zlyhanie(f"sitemap.xml má len {len(hlboke)} hlbších stránok")
        vyber = random.sample(hlboke, 2)
        # pevná stránka: hokejové kluby — cesta zo slugov v data.json (f_hok / f_hok_klu)
        pevna = None
        if self.data:
            uzly = {n["id"]: n for n in self.data.get("nodes", [])}
            kl = "slug_en" if self.lang == "en" else "slug"
            try:
                cesta = f"{uzly['f_hok'].get(kl) or uzly['f_hok']['slug']}/" \
                        f"{uzly['f_hok_klu'].get(kl) or uzly['f_hok_klu']['slug']}/"
                pevna = next((u for u in adresy if urllib.parse.urlsplit(u).path == root_path + cesta), None)
            except KeyError:
                pevna = None
        if not pevna:
            self.vysledky.append(("warn", "Pevná stránka (hokejové kluby)",
                                  "nenašla sa v sitemap.xml — namiesto nej náhodná stránka 2. úrovne"))
            pevna = random.choice([u for u in adresy if hlbka(u) == 2])
        return vyber + [pevna]

    def liga(self, url):
        def fn(pokus):
            kod, _, text = stiahni(url)
            if kod != 200:
                raise Zlyhanie(f"statická stránka vrátila HTTP {kod}")
            stat_titulok = titulok_z_html(text)
            if not stat_titulok:
                raise Zlyhanie("statická stránka nemá titulok")
            if not re.search(r'<a class="card"', text) and 'id="pageBoot"' not in text:
                raise Zlyhanie("statická stránka nemá obsah (karty ani balík stránky)")
            if not CSP_META_RE.search(text):
                raise Zlyhanie("statická stránka nemá Content-Security-Policy (bod 16)")
            cesta = urllib.parse.urlsplit(url).path
            ctx = self.kontext()
            try:
                page = self.stranka(ctx)
                t0 = time.time()
                page.goto(url, wait_until="load")
                self.cakaj_na_appku(page)          # appka stránku prevzala
                trvanie = time.time() - t0
                page.wait_for_timeout(1500)
                self.snimka(page, "3-liga-" + cesta.strip("/").replace("/", "_")[:70])
                akt_cesta = page.evaluate("location.pathname")
                if akt_cesta != cesta:
                    raise Zlyhanie(f"po prevzatí appkou sa adresa zmenila: {cesta} → {akt_cesta}")
                akt_titulok = page.title()
                if akt_titulok != stat_titulok:
                    raise Zlyhanie(f"titulok po prevzatí „{akt_titulok}“ ≠ statický „{stat_titulok}“")
                pocet = self.pocet_odkazov(page)
                if pocet < 1:
                    raise Zlyhanie("po prevzatí appkou nie sú na stránke žiadne linky")
                self.over_chyby(page, cesta)
            finally:
                ctx.close()
            detail = f"„{stat_titulok}“, odkazov: {pocet}, {trvanie:.1f} s"
            if trvanie > POMALA_S:
                return "warn", "pomalá stránka — " + detail
            return "ok", detail
        return fn

    # ------------------------------------------------ d) vyhľadávanie
    def vyber_hladany(self):
        uzly = self.data.get("nodes", [])
        podla_id = {n["id"]: n for n in uzly}
        deti = {}
        for n in uzly:
            deti.setdefault(n.get("parentId"), []).append(n)

        def meno(n):
            return (n.get("name_en") or n.get("name") or "") if self.lang == "en" else (n.get("name") or "")

        def hlbka(n):
            h = 0
            while n and n.get("parentId"):
                n = podla_id.get(n["parentId"])
                h += 1
            return h

        pocet_mien = {}
        for n in uzly:
            pocet_mien[meno(n)] = pocet_mien.get(meno(n), 0) + 1
        # priečinok s jedinečným názvom (aspoň 2 položky vnútri), nie úplne hore v strome
        kandidati = [n for n in uzly if n.get("type") == "folder" and len(deti.get(n["id"], [])) >= 2
                     and 6 <= len(meno(n)) <= 40 and hlbka(n) >= 2 and pocet_mien[meno(n)] == 1]
        n = random.choice(kandidati)
        return meno(n)

    def hladanie(self, pokus):
        if not self.data:
            raise Zlyhanie("bez data.json sa nedá vybrať hľadaný názov")
        hladany = self.vyber_hladany()
        ctx = self.kontext()
        try:
            page = self.stranka(ctx)
            page.goto(self.base, wait_until="load")
            self.cakaj_na_appku(page)
            page.fill("#srch", hladany)
            vysledok = page.locator("#main a.card-folder", has_text=hladany).first
            try:
                vysledok.wait_for(state="visible")
            except Exception:
                self.snimka(page, "4-hladanie-chyba")
                raise Zlyhanie(f"hľadanie „{hladany}“ neukázalo výsledok s týmto názvom")
            self.snimka(page, "4-hladanie-vysledky")
            ciel = urllib.parse.urlsplit(vysledok.get_attribute("href") or "").path
            vysledok.click()
            page.wait_for_function("p => location.pathname === p", arg=ciel)
            page.wait_for_selector("#main a[href]", state="visible")
            page.wait_for_timeout(1000)
            self.snimka(page, "4-hladanie-otvorene")
            self.over_chyby(page, "vyhľadávanie")
        finally:
            ctx.close()
        return "ok", f"„{hladany}“ → klik otvoril {ciel}"

    # ------------------------------------------------ e) mobil
    def mobil(self, pokus):
        adresy = [("domov", self.base)]
        if self.ligy:
            adresy.append(("liga", self.ligy[0]))
        popis = []
        ctx = self.kontext(mobil=True)
        try:
            for meno, url in adresy:
                page = self.stranka(ctx)
                page.goto(url, wait_until="load")
                self.cakaj_na_appku(page)
                page.wait_for_timeout(1500)
                self.snimka(page, f"5-mobil-{meno}")
                sirka = page.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
                if sirka[0] > sirka[1]:
                    raise Zlyhanie(f"mobil ({meno}): stránka sa posúva do strany — "
                                   f"šírka obsahu {sirka[0]} px > okno {sirka[1]} px")
                if not page.locator("header").first.is_visible():
                    raise Zlyhanie(f"mobil ({meno}): hlavička nie je viditeľná")
                if not page.locator("#srch").is_visible():
                    raise Zlyhanie(f"mobil ({meno}): vyhľadávanie nie je viditeľné")
                self.over_chyby(page, f"mobil ({meno})")
                popis.append(f"{meno} {urllib.parse.urlsplit(url).path} OK (šírka {sirka[0]} px)")
                page.close()
        finally:
            ctx.close()
        return "ok", "390×844: " + ", ".join(popis)

    # ------------------------------------------------ f) banner
    def banner(self, pokus):
        ctx = self.kontext()
        try:
            page = self.stranka(ctx)
            page.goto(self.base, wait_until="load")
            self.cakaj_na_appku(page)
            if page.locator("#bannerSlot").count() == 0:
                raise Zlyhanie("na domove chýba kontajner pre banner (#bannerSlot)")
        finally:
            ctx.close()
        return "ok", "kontajner pre banner je na stránke (reklamy v teste blokované)"

    # ------------------------------------------------ g) admin
    def admin(self, pokus):
        ctx = self.kontext()
        try:
            page = self.stranka(ctx)
            page.goto(self.base + "#admin", wait_until="load")
            try:
                page.wait_for_selector("#pwScreen.open #pwIn", state="visible")
            except Exception:
                self.snimka(page, "6-admin-chyba")
                raise Zlyhanie("/#admin neotvoril prihlasovacie okno")
            self.snimka(page, "6-admin")
            self.over_chyby(page, "admin")
        finally:
            ctx.close()
        return "ok", "/#admin otvorí prihlasovacie okno (heslo sa nezadáva)"

    # ------------------------------------------------ i) vlajky z vlastného webu
    # priečinok s vlajkou v statickom HTML (karta priečinka: href="slug/", v názve <img> vlajky)
    VLAJKA_PRIECINKA_RE = re.compile(r'<a class="card" href="[^"]+/"><div class="nm"><img src="[^"]*(/vlajky/|flagcdn\.com/)')

    def stranka_s_vlajkami(self):
        """Stránka so zoznamom krajín (priečinky s vlajkami): stránky z kontroly c)
        a ich nadradené stránky (napr. liga → krajina → kontinent), inak náhodné
        stránky zo sitemap.xml. Vráti (adresa, statické HTML) alebo (None, None)."""
        root_path = urllib.parse.urlsplit(self.base).path
        kandidati = []
        for u in reversed(self.ligy):
            casti = urllib.parse.urlsplit(u).path[len(root_path):].strip("/").split("/")
            for n in range(len(casti), 0, -1):
                a = urllib.parse.urljoin(self.base, root_path + "/".join(casti[:n]) + "/")
                if a not in kandidati:
                    kandidati.append(a)
        kandidati += random.sample(self.adresy, min(10, len(self.adresy)))
        for url in kandidati[:25]:
            kod, _, text = stiahni(url)
            if kod == 200 and self.VLAJKA_PRIECINKA_RE.search(text):
                return url, text
        return None, None

    VLAJKY_JS = """() => [...document.querySelectorAll('img[src*="/vlajky/"]')].map(i => ({
        src: i.getAttribute('src'), cur: i.currentSrc, w: +i.getAttribute('width'),
        ok: i.complete, nw: i.naturalWidth}))"""

    def vlajky(self, pokus):
        url, text = self.stranka_s_vlajkami()
        if not url:
            return "warn", "nenašla sa stránka s vlajkami (kontrola sa preskočila)"
        cesta = urllib.parse.urlsplit(url).path
        if "/vlajky/" not in text:
            # web je ešte po starom (napr. sportlinking pred prevzatím zmeny) — nie je to chyba webu
            return "warn", (f"{cesta}: web ešte načítava vlajky z flagcdn.com "
                            "(vlajky z vlastného webu /vlajky/ ešte nie sú nasadené)")
        cudzie = []    # požiadavky na flagcdn.com — nesmú byť žiadne
        vysledok = {}
        for mobil in (False, True):
            ctx = self.kontext(mobil=mobil)
            try:
                page = self.stranka(ctx)
                page.on("request", lambda rq: cudzie.append(rq.url) if "flagcdn.com" in rq.url else None)
                page.goto(url, wait_until="load")
                self.cakaj_na_appku(page)
                try:   # počkaj, kým sa načíta aspoň jedna skutočná vlajka (nie náhradník 1×1)
                    page.wait_for_function("""() => [...document.querySelectorAll('img[src*="/vlajky/"]')]
                        .some(i => i.complete && i.naturalWidth > 1)""", timeout=10_000)
                except Exception:
                    pass
                page.wait_for_timeout(1000)
                vlajky = page.evaluate(self.VLAJKY_JS)
                self.snimka(page, "8-vlajky-" + ("mobil" if mobil else "pc"))
                self.over_chyby(page, cesta + (" (mobil)" if mobil else ""))
            finally:
                ctx.close()
            vysledok[mobil] = vlajky
        if cudzie:
            raise Zlyhanie(f"{cesta}: prehliadač sťahuje vlajky z flagcdn.com ({len(cudzie)}×, napr. {cudzie[0]})")
        pc = vysledok[False]
        nacitane = [v for v in pc if v["ok"]]
        skutocne = [v for v in nacitane if v["nw"] > 1]
        if not pc:
            raise Zlyhanie(f"{cesta}: v statickom HTML sú vlajky, ale po prevzatí appkou na stránke nie sú")
        if not skutocne:
            raise Zlyhanie(f"{cesta}: žiadna vlajka sa nenačítala ako obrázok — všetkých {len(nacitane)} "
                           f"načítaných je priehľadný náhradník 1×1 (vlajky sa pri builde nestiahli?)")
        detail = (f"{cesta}: vlajok {len(pc)}, načítaných {len(nacitane)}, skutočných {len(skutocne)}"
                  + (f", náhradníkov {len(nacitane) - len(skutocne)}" if len(nacitane) > len(skutocne) else "")
                  + ", flagcdn.com 0×")
        # mobil (2× displej): má sa načítať dvojnásobná vlajka zo srcset
        mob = [v for v in vysledok[True] if v["ok"] and v["nw"] > 1]
        # pozor: naturalWidth pri 2× obrázku zo srcset prehliadač hlási už vydelený dvomi,
        # preto sa 2× verzia spozná podľa adresy, ktorú naozaj načítal (currentSrc)
        dvojite = [v for v in mob if f"/vlajky/{2 * v['w']}x" in v["cur"]]
        if mob and not dvojite:
            return "warn", detail + f"; mobil 2×: načítala sa len obyčajná vlajka (napr. {mob[0]['cur']})"
        return "ok", detail + (f"; mobil 2×: {len(dvojite)} ostrých vlajok" if mob else "")

    # ------------------------------------------------ h) 404
    def chyba_404(self, pokus):
        cesta = urllib.parse.urlsplit(self.base).path + f"neexistuje-test-{random.randint(1000, 9999)}/"
        url = urllib.parse.urljoin(self.base, cesta)
        kod, _, text = stiahni(url)
        if kod != 404:
            raise Zlyhanie(f"neexistujúca adresa vrátila HTTP {kod} (čakám 404)")
        if len(text) < 1000 or not titulok_z_html(text):
            raise Zlyhanie(f"stránka 404 je prázdna ({len(text)} znakov)")
        ctx = self.kontext()
        try:
            page = self.stranka(ctx, povolene_404=(cesta,))
            page.goto(url, wait_until="load")
            page.wait_for_timeout(3000)
            self.snimka(page, "7-stranka-404")
            dlzka = page.evaluate("document.body ? document.body.innerText.trim().length : 0")
            if dlzka < 50:
                raise Zlyhanie(f"stránka 404 sa v prehliadači zobrazí prázdna ({dlzka} znakov)")
            self.over_chyby(page, "stránka 404")
        finally:
            ctx.close()
        return "ok", f"{cesta} → HTTP 404, stránka webu sa zobrazí"

    # ------------------------------------------------ j) reklama v uzavretom okienku (bod 16)
    @staticmethod
    def over_okienko(page, sel, kde):
        """V prvku sel nesmie byť cudzí <script> priamo v stránke; ak je tam okienko,
        musí mať správny sandbox a v srcdoc skript z ban.tipsport.sk.
        Vráti True = okienko je, False = v prvku nie je kód partnera."""
        o = page.evaluate("""sel => {
            const el = document.querySelector(sel); if(!el) return null;
            const f = el.querySelector('iframe');
            return { priame: el.querySelectorAll('script').length,
                     sandbox: f ? f.getAttribute('sandbox') : null,
                     srcdoc: f ? (f.getAttribute('srcdoc') || '') : null };
        }""", sel)
        if o is None:
            raise Zlyhanie(f"{kde}: prvok {sel} na stránke nie je")
        if o["priame"]:
            raise Zlyhanie(f"{kde}: cudzí <script> beží PRIAMO v stránke (nie v uzavretom okienku)")
        if o["srcdoc"] is None:
            return False
        if o["sandbox"] is None:
            raise Zlyhanie(f"{kde}: okienko reklamy nemá sandbox")
        prava = o["sandbox"].split()
        zle = [x for x in SANDBOX_ZAKAZANE if x in prava]
        if zle:
            raise Zlyhanie(f"{kde}: okienko reklamy má zakázané právo {', '.join(zle)}")
        chyba = [x for x in SANDBOX_POTREBNE if x not in prava]
        if chyba:
            raise Zlyhanie(f"{kde}: okienku reklamy chýba právo {', '.join(chyba)} (klik by neotvoril novú kartu)")
        if not re.search(r"<script[^>]+src=['\"]https://ban\.tipsport\.sk/", o["srcdoc"], re.I):
            raise Zlyhanie(f"{kde}: v okienku chýba skript z ban.tipsport.sk")
        return True

    def reklama_okienko(self, pokus):
        lang = self.lang
        dnes = datetime.now().strftime("%Y-%m-%d")
        # bannery partnera pre slot 1 na domove podľa data.json (rovnaké pravidlá ako appka)
        bannery = [b for b in (self.data or {}).get("banners", [])
                   if (b.get("lang") or "sk") == lang and b.get("active") is not False
                   and str(b.get("slot") or 1) != "2" and not b.get("sectionId")
                   and not (b.get("startsAt") and dnes < b["startsAt"])
                   and not (b.get("endsAt") and dnes > b["endsAt"])]
        partner = [b for b in bannery if re.search(r"<(script|iframe)\b", b.get("html") or "", re.I)]
        len_partner = bool(bannery) and len(partner) == len(bannery)
        popis = []
        ctx = self.kontext()
        try:
            page = self.stranka(ctx)
            page.goto(self.base, wait_until="load")
            self.cakaj_na_appku(page)
            page.wait_for_timeout(1500)
            ok = self.over_okienko(page, "#bannerSlot", "slot 1")
            if len_partner and not ok:
                raise Zlyhanie("slot 1: banner partnera nie je v uzavretom okienku (iframe sandbox)")
            popis.append("slot 1: " + ("okienko so sandboxom, skript ban.tipsport.sk" if ok else "bez kódu partnera"))
            self.over_chyby(page, "domov (reklama)")
            page.close()

            pb = (self.data or {}).get("promoBanner") or {}
            if lang == "sk" and pb.get("active") is not False and re.search(r"<script\b", pb.get("html") or "", re.I):
                uzly = {n["id"]: n for n in (self.data or {}).get("nodes", [])}
                n, cesta = uzly.get(pb.get("sectionId") or "f_tip"), []
                while n:
                    cesta.insert(0, n.get("slug") or "")
                    n = uzly.get(n.get("parentId"))
                url = self.base + "/".join(cesta) + "/"
                kod, _, text = stiahni(url)
                if kod != 200:
                    raise Zlyhanie(f"Tipovanie {url} vrátilo HTTP {kod}")
                if not CSP_META_RE.search(text):
                    raise Zlyhanie("statická stránka Tipovania nemá Content-Security-Policy")
                m = re.search(r'<div class="promo-ban">(.*?)</div>', text, re.S)
                if m and re.search(r"<script\b", m.group(1), re.I):
                    raise Zlyhanie("statická stránka Tipovania má skript partnera PRIAMO v stránke")
                page = self.stranka(ctx)
                page.goto(url, wait_until="load")
                self.cakaj_na_appku(page)          # prevzatie appkou
                page.wait_for_selector(".promo-ban", state="attached")
                page.wait_for_timeout(1500)
                self.snimka(page, "8-tipovanie-promo")
                if not self.over_okienko(page, ".promo-ban", "promo blok"):
                    raise Zlyhanie("promo blok: rotátor partnera nie je v uzavretom okienku")
                if not page.locator(".promo-txt").count():
                    self.log.append("promo blok: bez reklamného textu (žiadny aktívny text)")
                self.over_chyby(page, "Tipovanie (promo blok)")
                popis.append("promo blok: okienko so sandboxom, skript ban.tipsport.sk")
            else:
                popis.append("promo blok: na tomto webe nie je")
        finally:
            ctx.close()
        return "ok", "; ".join(popis) + "; 0 porušení CSP (reklamy v teste blokované)"

    # ------------------------------------------------ k) Aktuálne (aktualne.json)
    @staticmethod
    def akt_viditelne(items, dnes):
        """ROVNAKÉ pravidlá ako appka (aktVisible) a generator.py (akt_visible)."""
        def poradie(x):
            try:
                return float(x[1].get("order"))
            except (TypeError, ValueError):
                return float(x[0])
        zorad = [a for _, a in sorted(enumerate(i for i in items if isinstance(i, dict)),
                                      key=lambda x: (poradie(x), x[0]))]
        return [a for a in zorad if a.get("url") and a.get("disabled") is not True
                and not (a.get("startsAt") and dnes < a["startsAt"])
                and not (a.get("endsAt") and dnes > a["endsAt"])]

    def akt_zdroj(self):
        """Odkiaľ appka berie Aktuálne: (položky, popis zdroja)."""
        adresy = ([AKT_MASTER] if self.lang == "en" else []) + [self.base + "aktualne.json"]
        chyba = []
        for u in adresy:
            try:
                kod, _, text = stiahni(u)
            except Exception as e:      # sieť — appka v takom prípade skúsi ďalšiu adresu, test tiež
                self.log.append(f"k) {u}: {e}")
                chyba.append(str(e)[:60])
                continue
            if kod == 200:
                try:
                    d = json.loads(text)
                except ValueError as e:
                    raise Zlyhanie(f"{u} nie je platný JSON ({e})")
                if not isinstance(d, dict) or not isinstance(d.get("items"), list):
                    raise Zlyhanie(f"{u} nemá pole \"items\"")
                return d["items"], f"{u} (verzia {d.get('version')})"
            chyba.append(kod)
        if chyba and all(k == 404 for k in chyba):
            return (self.data or {}).get("aktualne") or [], "data.json (aktualne.json zatiaľ nie je — prechodné obdobie)"
        raise Zlyhanie(f"aktualne.json sa nepodarilo stiahnuť (HTTP {chyba})")

    @staticmethod
    def akt_karty(page):
        return page.eval_on_selector_all("#aktualneScroll .akt-card", """els => els.map(e => ({
            href: e.getAttribute('href') || '', title: e.getAttribute('title') || '',
            new: !!e.querySelector('.akt-new'), text: e.innerText.replace(/\\s+/g, ' ').trim()}))""")

    def aktualne(self, pokus):
        dnes = datetime.now().strftime("%Y-%m-%d")
        items, zdroj = self.akt_zdroj()
        vid = self.akt_viditelne(items, dnes)
        en = self.lang == "en"
        popis = lambda a: ((a.get("desc_en") if en and a.get("desc_en") else a.get("desc")) or "").strip()
        cakane = [a["url"].strip() for a in vid]
        skryte = {(a.get("url") or "").strip() for a in items if isinstance(a, dict)} - set(cakane)
        popis_info = []
        # surové HTML (to, čo vidí Google) — po polnoci / pred nočným buildom môže byť o deň staršie
        kod, _, text = stiahni(self.base)
        m = re.search(r'<div id="aktualneScroll"[^>]*>(.*?)</div>', text, re.S)
        v_html = [html.unescape(h) for h in re.findall(r'<a class="akt-card[^"]*" href="([^"]*)"', m.group(1) if m else "")]
        stav = "ok"
        if v_html != cakane:
            stav = "warn"
            popis_info.append(f"⚠️ surové HTML má {len(v_html)} kariet, súbor dnes {len(cakane)} (HTML sa obnoví nočným buildom)")
        ctx = self.kontext()
        try:
            page = self.stranka(ctx)
            page.goto(self.base, wait_until="load")
            self.cakaj_na_appku(page)
            page.wait_for_timeout(3000)          # aktualne.json sa sťahuje zvlášť od data.json
            karty = self.akt_karty(page)
            hrefy = [k["href"] for k in karty]
            if hrefy != cakane:
                raise Zlyhanie(f"lišta v appke {hrefy[:6]} ≠ viditeľné položky zo zdroja {cakane[:6]}")
            zle = [h for h in hrefy if h in skryte]
            if zle:
                raise Zlyhanie(f"na lište je skrytá položka (vypnutá/naplánovaná/skončená): {zle}")
            for a, k in zip(vid, karty):
                if popis(a) and k["title"] != popis(a):
                    raise Zlyhanie(f"karta {k['text']}: bublina „{k['title']}“ ≠ popis „{popis(a)}“")
            if any(re.search(r"\bLIVE\b", k["text"]) for k in karty):
                raise Zlyhanie("na karte Aktuálnych je štítok LIVE")
            self.over_chyby(page, "domov (Aktuálne)")
            page.close()

            # VYMYSLENÝ aktualne.json (len v tomto prehliadači): naplánovaná, skončená a vypnutá sa nesmú ukázať
            from datetime import timedelta
            d = lambda n: (datetime.now() + timedelta(days=n)).strftime("%Y-%m-%d")
            teraz = int(time.time() * 1000)
            test_items = [
                {"id": "t1", "order": 1, "icon": "🏸", "name": "TEST viditeľná", "name_en": "TEST visible",
                 "url": "https://test.invalid/vidno", "desc": "TEST popis", "desc_en": "TEST tip",
                 "addedAt": teraz - 3600_000},
                {"id": "t2", "order": 0, "icon": "🎯", "name": "TEST stará", "url": "https://test.invalid/stara",
                 "addedAt": teraz - 5 * 86400_000, "endsAt": d(2)},
                {"id": "t3", "order": 2, "icon": "🎱", "name": "TEST naplánovaná", "url": "https://test.invalid/zajtra",
                 "startsAt": d(1), "addedAt": teraz},
                {"id": "t4", "order": 3, "icon": "🏓", "name": "TEST skončená", "url": "https://test.invalid/vcera",
                 "endsAt": d(-1), "addedAt": teraz},
                {"id": "t5", "order": 4, "icon": "⛳", "name": "TEST vypnutá", "url": "https://test.invalid/vypnuta",
                 "disabled": True, "addedAt": teraz},
            ]
            telo = json.dumps({"version": 1, "items": test_items}, ensure_ascii=False)
            page = self.stranka(ctx)
            ziadosti = []
            def podstrc(r):
                ziadosti.append(r.request.url)
                r.fulfill(status=200, content_type="application/json", body=telo,
                          headers={"Access-Control-Allow-Origin": "*"})
            page.route("**/aktualne.json*", podstrc)
            page.goto(self.base, wait_until="load")
            self.cakaj_na_appku(page)
            page.wait_for_timeout(3000)
            if not ziadosti:
                # stará appka (pred Zadaním 16a) aktualne.json ešte nesťahuje — napr. test
                # pull requestu proti živému webu pred zlúčením
                popis_info.insert(0, f"zdroj {zdroj}: {len(items)} položiek, viditeľných {len(cakane)}, na lište {len(cakane)}")
                popis_info.append("⚠️ appka na webe ešte nesťahuje aktualne.json (stará verzia) — test s podstrčeným súborom preskočený")
                return "warn", "; ".join(popis_info)
            page.wait_for_function("() => [...document.querySelectorAll('#aktualneScroll .akt-card')]"
                                   ".some(e => (e.getAttribute('href')||'').indexOf('test.invalid') >= 0)")
            page.wait_for_timeout(500)
            karty = self.akt_karty(page)
            self.snimka(page, "9-aktualne-test")
            hrefy = [k["href"] for k in karty]
            if hrefy != ["https://test.invalid/stara", "https://test.invalid/vidno"]:
                raise Zlyhanie(f"podstrčený aktualne.json: na lište je {hrefy} (čakám len 2 viditeľné v poradí podľa order)")
            k = {x["href"]: x for x in karty}
            if k["https://test.invalid/vidno"]["title"] != ("TEST tip" if en else "TEST popis"):
                raise Zlyhanie("podstrčený aktualne.json: na karte chýba bublina (title) s popisom")
            if not k["https://test.invalid/vidno"]["new"] or k["https://test.invalid/stara"]["new"]:
                raise Zlyhanie("podstrčený aktualne.json: štítok NEW má byť len pri položke pridanej pred < 24 h")
            if en and "TEST visible" not in k["https://test.invalid/vidno"]["text"]:
                raise Zlyhanie("podstrčený aktualne.json: EN web neukazuje name_en")
            self.over_chyby(page, "domov (podstrčený aktualne.json)")
        finally:
            ctx.close()
        popis_info.insert(0, f"zdroj {zdroj}: {len(items)} položiek, viditeľných {len(cakane)}, na lište {len(cakane)}")
        popis_info.append("podstrčený súbor: naplánovaná, skončená a vypnutá položka skryté, bublina a NEW OK")
        return stav, "; ".join(popis_info)

    # ------------------------------------------------ l) stránka Aktuálne (Zadanie 17)
    def stranka_aktualne(self, pokus):
        """Domov má toľko dlaždíc, koľko koreňových priečinkov bez noTileSk (SK); stránka
        Aktuálne (SK /aktualne/, EN /live-this-week/): H1, položky v ručnom poradí
        (appka = statická stránka = aktualne.json, bez nadpisov so športom), úvodný
        text pod zoznamom, popis pod názvom, skrytá lišta, titulok so športom,
        vyhľadávanie, odkaz v pätičke. Kým priečinok f_ltw na SK webe nie je (enOnly:true), časť
        o stránke sa na SK webe PRESKOČÍ (kontrola dlaždíc a pätičky ostáva)."""
        if not self.data:
            raise Zlyhanie("data.json sa nepodarilo načítať (kontrola b)")
        en = self.lang == "en"
        uzly = self.data.get("nodes") or []
        vid = (lambda n: n.get("en") is not False) if en else (lambda n: n.get("enOnly") is not True)
        koren = [n for n in uzly if n.get("parentId") is None and n.get("type") == "folder" and vid(n)]
        dlazdice = [n for n in koren if en or n.get("noTileSk") is not True]
        live = next((n for n in koren if n.get("id") == "f_ltw"), None)
        nazov = lambda n: ((n.get("name_en") if en and n.get("name_en") else n.get("name")) or "").strip()
        popis_uzla = lambda n: ((n.get("desc_en") if en and n.get("desc_en") else n.get("desc")) or "").strip()
        kod, _, domov = stiahni(self.base)
        m = re.search(r'<a class="f-live" id="fLive"([^>]*)>', domov)
        odkaz = re.search(r'href="([^"]+)"', m.group(1)).group(1) if (m and "href=" in m.group(1)) else ""
        odkaz = self.na_url(html.unescape(odkaz)) if odkaz else ""   # bod 19
        stav, info = "ok", []
        items, zdroj = self.akt_zdroj()
        # ikonka webu novej položky Aktuálnych sa stiahne až pri ďalšom builde (ikony.py) —
        # dovtedy appka ukáže emoji; chýbajúca ikonka položky Aktuálnych preto nie je chyba
        koren_cesta = urllib.parse.urlsplit(self.base).path
        bez_ikonky = {f"{koren_cesta}ikony/{urllib.parse.urlsplit((a.get('url') or '').strip()).hostname or ''}.png"
                      for a in items if isinstance(a, dict)}
        ctx = self.kontext()
        try:
            page = self.stranka(ctx, bez_ikonky)
            page.goto(self.base, wait_until="load")
            self.cakaj_na_appku(page)
            page.wait_for_timeout(1500)
            n_dl = page.locator("#main .card-root, #main .card-folder").count()
            n_ik = page.locator("#hSports a").count()
            if n_dl != len(dlazdice) or n_ik != len(dlazdice):
                raise Zlyhanie(f"domov má {n_dl} dlaždíc a {n_ik} ikoniek v hlavičke, čakám {len(dlazdice)} "
                               f"(koreňové priečinky bez noTileSk)")
            info.append(f"domov {n_dl} dlaždíc = priečinky bez noTileSk")
            if not live:
                if odkaz or page.locator("#fLive:visible").count():
                    raise Zlyhanie("priečinok Aktuálne na tomto webe nie je, ale pätička naň odkazuje")
                info.append("stránka Aktuálne na tomto webe zatiaľ nie je (f_ltw má enOnly:true) — kontrola stránky preskočená")
                return "ok", "; ".join(info)
            if not odkaz:
                raise Zlyhanie("v surovom HTML domova chýba odkaz v pätičke na stránku Aktuálne (#fLive)")
            hlav = page.eval_on_selector("#aktHead", "e => e.getAttribute('href') || ''")
            hlav = self.na_url(hlav) if hlav else ""
            if hlav != odkaz:
                raise Zlyhanie(f"nápis lišty Aktuálne nie je odkaz na stránku ({hlav!r} ≠ {odkaz!r})")
            page.click("#fLive")
            page.wait_for_selector("#main .live-intro, #main .live-none, #main .card-link", state="attached")
            if not page.url.endswith(odkaz):
                raise Zlyhanie(f"klik na odkaz v pätičke viedol na {page.url}, čakám {odkaz}")
            self.over_chyby(page, "domov (pätička → Aktuálne)")
            page.close()

            url = urllib.parse.urljoin(self.base, odkaz)
            kod, _, raw = stiahni(url)
            if kod != 200:
                raise Zlyhanie(f"stránka Aktuálne {odkaz} vrátila HTTP {kod}")
            vidno = self.akt_viditelne(items, datetime.now().strftime("%Y-%m-%d"))
            meno = lambda a: ((a.get("name_en") if en and a.get("name_en") else a.get("name")) or "").strip()
            popis = lambda a: ((a.get("desc_en") if en and a.get("desc_en") else a.get("desc")) or "").strip()
            # surové HTML (to, čo vidí Google)
            h1 = re.search(r"<h1>(.*?)</h1>", raw, re.S)
            if not h1 or nazov(live) not in html.unescape(re.sub(r"<[^>]+>", "", h1.group(1))):
                raise Zlyhanie(f"statická stránka nemá nadpis H1 „{nazov(live)}“")
            uvod = popis_uzla(live)
            poradie = [meno(a) for a in vidno]       # ručné poradie z aktualne.json ("order")
            telo = raw[raw.find("</h1>"):]
            telo = telo[:telo.find('<a class="appbtn"')] if '<a class="appbtn"' in telo else telo
            if re.search(r"<h2[ >]", telo):
                raise Zlyhanie("statická stránka má nadpisy H2 (skupiny podľa športu majú byť zrušené — Zadanie 27)")
            if uvod:
                u_esc = html.escape(uvod, quote=False)
                if f'<p class="live-intro">{u_esc}</p>' not in telo:
                    raise Zlyhanie("v surovom HTML chýba úvodný text (popis priečinka) v <p class=\"live-intro\">")
                if telo.count(u_esc) != 1:
                    raise Zlyhanie(f"v surovom HTML je úvodný text {telo.count(u_esc)}× (má byť len raz, pod zoznamom)")
                u_pos = telo.find('<p class="live-intro">')
                if re.search(r'<div class="nm">', telo[u_pos:]) or ("nie je nič aktívne" in telo[u_pos:] or "Nothing is live" in telo[u_pos:]):
                    raise Zlyhanie("v surovom HTML nie je úvodný text pod zoznamom položiek")
            nm_raw = [html.unescape(x) for x in re.findall(r'<div class="nm">([^<]*)</div>', telo)]
            if nm_raw != poradie:
                stav = "warn"
                info.append(f"⚠️ surové HTML má položky {nm_raw[:6]}, súbor dnes v poradí {poradie[:6]} (obnoví nočný build)")
            for a in vidno:
                if popis(a) and meno(a) in nm_raw and html.escape(popis(a), quote=False) not in raw:
                    raise Zlyhanie(f"v surovom HTML chýba popis pod názvom „{meno(a)}“")
            titulok = titulok_z_html(raw)
            # prvý šport v ručnom poradí (bez „iné“/prázdneho) musí byť v titulku
            prvy_kod = next((a.get("sport") for a in vidno if a.get("sport") and a.get("sport") != "ine"), "")
            prvy = SPORT_NAZVY.get(prvy_kod, ("", ""))[1 if en else 0]
            if prvy and prvy not in titulok.lower():
                raise Zlyhanie(f"titulok „{titulok}“ neobsahuje prvý aktívny šport „{prvy}“")
            if not vidno and ("nie je nič aktívne" not in raw and "Nothing is live" not in raw):
                raise Zlyhanie("bez aktívnych položiek chýba veta „Práve teraz nie je nič aktívne…“")
            # appka (po prevzatí)
            page = self.stranka(ctx, bez_ikonky)
            page.goto(url, wait_until="load")
            page.wait_for_selector("#main .live-intro, #main .live-none, #main .card-link", state="attached")
            page.wait_for_timeout(2500)          # aktualne.json sa sťahuje zvlášť
            app = page.evaluate("""() => ({
                h1: (document.querySelector('#breadcrumb h1') || {}).textContent || '',
                intro: (document.querySelector('#main .live-intro') || {}).textContent || '',
                h2: document.querySelectorAll('#main h2').length,
                gridy: document.querySelectorAll('#main .grid-deep').length,
                // úvodný text je za zoznamom: za ním už nie je žiadna karta ani veta „nič aktívne“
                pod: (() => { const i = document.querySelector('#main .live-intro'); if(!i) return null;
                  const z = document.querySelector('#main .grid-deep, #main .live-none');
                  return !!z && !!(z.compareDocumentPosition(i) & Node.DOCUMENT_POSITION_FOLLOWING); })(),
                names: [...document.querySelectorAll('#main .cl-name')].map(e => e.textContent.trim()),
                descs: [...document.querySelectorAll('#main .cl-desc')].map(e => e.textContent.trim()),
                lista: getComputedStyle(document.getElementById('aktualneWrap')).display,
                title: document.title})""")
            self.snimka(page, "10-stranka-aktualne")
            if nazov(live) not in app["h1"]:
                raise Zlyhanie(f"appka: nadpis H1 „{app['h1']}“ neobsahuje „{nazov(live)}“")
            if uvod and app["intro"].strip() != uvod:
                raise Zlyhanie("appka: úvodný text sa líši od popisu priečinka")
            if uvod and app["pod"] is not True:
                raise Zlyhanie("appka: úvodný text nie je pod zoznamom položiek")
            if app["h2"]:
                raise Zlyhanie(f"appka: na stránke Aktuálne je {app['h2']} nadpisov H2 (skupiny podľa športu majú byť zrušené)")
            if vidno and app["gridy"] != 1:
                raise Zlyhanie(f"appka: položky majú byť v jednej mriežke, je ich {app['gridy']}")
            if app["names"] != poradie:
                raise Zlyhanie(f"appka: položky {app['names'][:6]} ≠ ručné poradie z aktualne.json {poradie[:6]}")
            for a in vidno:
                if popis(a) and popis(a) not in app["descs"]:
                    raise Zlyhanie(f"appka: pod názvom „{meno(a)}“ chýba popis")
            if app["lista"] != "none":
                raise Zlyhanie("appka: na stránke Aktuálne je viditeľná lišta Aktuálne")
            if app["names"] != nm_raw:
                stav = "warn"
                info.append(f"⚠️ poradie v appke {app['names'][:6]} ≠ statická {nm_raw[:6]} (obnoví nočný build)")
            if app["title"] != titulok:
                stav = "warn"
                info.append(f"⚠️ titulok v appke „{app['title']}“ ≠ statická „{titulok}“")
            self.over_chyby(page, "stránka Aktuálne")
            # vyhľadávanie nájde položku Aktuálnych
            if vidno:
                hladaj = meno(vidno[0])
                page.fill("#srch", hladaj)
                page.wait_for_timeout(800)
                vysl = page.eval_on_selector_all("#main .card-link", """els => els.map(e => (e.querySelector('.cl-name')||{}).textContent + ' | ' + ((e.querySelector('.sr-path')||{}).textContent||''))""")
                if not any(v.startswith(hladaj) and nazov(live) in v for v in vysl):
                    raise Zlyhanie(f"vyhľadanie „{hladaj}“ nenašlo položku Aktuálnych ({vysl[:4]})")
                info.append(f"hľadanie „{hladaj}“ OK")
        finally:
            ctx.close()
        info.insert(1, f"{odkaz}: H1, poradie {poradie[:6]}, úvod pod zoznamom, {len(vidno)} položiek (zdroj {zdroj}), lišta skrytá, titulok „{titulok}“")
        return stav, "; ".join(info)

    # ------------------------------------------------ m) stĺpce (Zadanie 26b)
    def stlpce(self, pokus):
        """Stĺpcové zobrazenie (počítač s myšou): priečinok sa otvorí len po skutočnom
        pohybe myši, ktorý sa zastavil nad položkou. Posun obsahu pod NEHYBNOU myšou
        (koliesko v stĺpci, posun stránky) nesmie nič otvoriť a zrolovaný stĺpec nesmie
        skočiť na začiatok — chyby z analýzy stĺpcov (navrhy/stlpce-analyza-2026-11-04.md)."""
        ctx = self.kontext()
        try:
            page = self.stranka(ctx)
            page.goto(self.base, wait_until="load")
            self.cakaj_na_appku(page)
            # celé dáta v appke — bez wait_for_function so stringom (to potrebuje eval, ktorý
            # CSP webu zakazuje — 'unsafe-eval' nie je povolený); page.evaluate eval nepotrebuje
            koniec = time.time() + CAKANIE_MS / 1000
            while not page.evaluate("typeof DB !== 'undefined' && !!DB.nodes && DB.nodes.length > 100 && !DB._partial"):
                if time.time() > koniec:
                    raise Zlyhanie("appka nenačítala celé dáta (data.json) do limitu")
                page.wait_for_timeout(250)
            page.click("#vSwitch button[data-mode=cols]")
            page.wait_for_selector("#colsWrap .col[data-lv='0'] .cit[data-t='f']", state="visible")

            def cesta():
                # názvy v jazyku webu (nName) — porovnávajú sa s textom položiek na obrazovke (EN web: name_en)
                return page.evaluate("colPath.map(id => { const n = DB.nodes.find(x => x.id === id); return n ? nName(n) : null; })")

            def stred(loc):
                b = loc.bounding_box()
                if not b:
                    raise Zlyhanie("položka stĺpca nemá rozmery (nie je vidno)")
                return b["x"] + b["width"] / 2, b["y"] + b["height"] / 2

            # hlavná sekcia s najviac podpriečinkami — aby bol stĺpec 1 dlhý (rolovateľný)
            koren_id = page.evaluate(
                "tileKids(null).filter(n => n.type === 'folder')"
                ".sort((a, b) => tileKids(b.id).length - tileKids(a.id).length)[0].id")
            koren = page.locator(f"#colsWrap .col[data-lv='0'] .cit[data-id='{koren_id}']")
            meno_koren = koren.locator(".nm").inner_text().strip()
            x, y = stred(koren)
            page.mouse.move(x - 60, y, steps=5)
            page.mouse.move(x, y, steps=6)        # skutočný pohyb, zastaví sa na položke
            page.wait_for_timeout(700)
            if cesta() != [meno_koren]:
                raise Zlyhanie(f"po zastavení myši na „{meno_koren}“ je otvorené {cesta()}")
            # 2. položka stĺpca 1 — otvorí sa (správne), myš na nej ostane stáť
            druha = page.locator("#colsWrap .col[data-lv='1'] .cit[data-t='f']").nth(1)
            meno_druha = druha.locator(".nm").inner_text().strip()
            x, y = stred(druha)
            page.mouse.move(x, y, steps=6)
            page.wait_for_timeout(700)
            otvorene = cesta()
            if otvorene != [meno_koren, meno_druha]:
                raise Zlyhanie(f"po zastavení myši na „{meno_druha}“ je otvorené {otvorene}")
            # koliesko nad stĺpcom 1 (najprv posúva stránku, po prilepení pásu roluje stĺpec):
            # položky sa posúvajú pod nehybnou myšou — nič sa nesmie otvoriť
            stlpec = page.locator("#colsWrap .col[data-lv='1']")
            roluje = page.evaluate("c => c.scrollHeight > c.clientHeight + 1", stlpec.element_handle())
            posun = 0
            for _ in range(14):
                page.mouse.wheel(0, 150)
                page.wait_for_timeout(120)
                posun = page.evaluate("c => c.scrollTop", stlpec.element_handle())
                if posun > 100:
                    break
            page.wait_for_timeout(700)
            if cesta() != otvorene:
                raise Zlyhanie(f"koliesko nad stĺpcom otvorilo iný priečinok: {cesta()} (bolo {otvorene})")
            if roluje and posun <= 0:
                raise Zlyhanie("koliesko nad dlhým stĺpcom ho nezrolovalo (ani stránku po prilepení)")
            # malý pohyb myši (2 px) nad položkou, ktorá sa pod ňu dostala posunom → stále nič
            page.mouse.move(x + 2, y + 1, steps=2)
            page.wait_for_timeout(600)
            po = page.evaluate("c => c.scrollTop", stlpec.element_handle())
            if cesta() != otvorene:
                raise Zlyhanie(f"po 2 px pohybe nad posunutým obsahom sa otvorilo {cesta()} (bolo {otvorene})")
            if po != posun:
                raise Zlyhanie(f"zrolovaný stĺpec skočil: posun {posun} → {po}")
            # skutočný pohyb (10 px) po položke, ktorá je pod kurzorom → tá sa má otvoriť (nie „zaseknuté“)
            pod = page.evaluate("([x, y]) => { const e = document.elementFromPoint(x, y); const a = e && e.closest('.cit[data-t=\"f\"]');"
                                " return a ? a.querySelector('.nm').textContent.trim() : null; }", [x + 2, y + 1])
            if pod:
                page.mouse.move(x + 12, y + 1, steps=4)
                page.wait_for_timeout(600)
                if cesta() != [meno_koren, pod]:
                    raise Zlyhanie(f"po 10 px pohybe po položke „{pod}“ sa neotvorila: {cesta()}")
                otvorene = cesta()
                x += 12
            # posun stránky pod nehybnou myšou → nič
            page.evaluate("window.scrollBy(0, -120)")
            page.wait_for_timeout(700)
            if cesta() != otvorene:
                raise Zlyhanie(f"po posune stránky pod myšou sa otvorilo {cesta()} (bolo {otvorene})")
            # poradie ako v dlaždiciach (Zadanie 26b2): v každom stĺpci priečinky pred linkami
            zle = page.evaluate(
                "[...document.querySelectorAll('#colsWrap .col')].map(c => {"
                "  const t = [...c.querySelectorAll('.cit')].map(a => a.dataset.t);"
                "  const prvaLinka = t.indexOf('l'); const poslednyPriecinok = t.lastIndexOf('f');"
                "  return prvaLinka >= 0 && poslednyPriecinok > prvaLinka ? c.querySelector('.col-title').textContent : null;"
                "}).filter(Boolean)")
            if zle:
                raise Zlyhanie(f"v stĺpci je linka pred priečinkom: {zle}")
            self.snimka(page, "13-stlpce")
            self.over_chyby(page, "stĺpce")
        finally:
            ctx.close()
        return "ok", (f"„{meno_koren} › {meno_druha}“ otvorené myšou; koliesko (posun stĺpca {posun} px"
                      f"{'' if roluje else ', stĺpec krátky'}), 2 px pohyb ani posun stránky nič neotvorili"
                      f"{', 10 px pohyb otvoril „' + pod + '“' if pod else ''}")

    # ------------------------------------------------ hlavný beh
    def spusti(self, od):
        self.cakaj_na_nasadenie(od)
        with sync_playwright() as p:
            spustit = {}
            if os.environ.get("CHROMIUM_PATH"):   # len pre lokálne skúšanie
                spustit["executable_path"] = os.environ["CHROMIUM_PATH"]
            self.browser = p.chromium.launch(**spustit)
            try:
                self.kontrola("a) Domovská stránka", self.domov)
                self.kontrola("b) data.json", self.data_json)
                self.ligy = []
                for pokus in (1, 2):
                    try:
                        self.ligy = self.vyber_stranky()
                        break
                    except Exception as e:
                        self.log.append(f"[pokus {pokus}] c) Výber stránok zo sitemap.xml: {e}")
                        if pokus == 1:
                            time.sleep(5)
                        else:
                            self.vysledky.append(("fail", "c) Výber stránok zo sitemap.xml", str(e)))
                for url in self.ligy:
                    self.kontrola("c) Stránka z Googlu: " + urllib.parse.urlsplit(url).path, self.liga(url))
                if self.ligy:
                    self.info.append("**Testované adresy:** " + ", ".join(
                        f"[{urllib.parse.urlsplit(u).path}]({u})" for u in self.ligy))
                self.kontrola("d) Vyhľadávanie", self.hladanie)
                self.kontrola("e) Mobil 390×844", self.mobil)
                self.kontrola("f) Banner", self.banner, pri_chybe="warn")
                self.kontrola("g) Admin (/#admin)", self.admin)
                self.kontrola("h) Stránka 404", self.chyba_404)
                self.kontrola("i) Vlajky z vlastného webu", self.vlajky)
                self.kontrola("j) Reklama v uzavretom okienku + CSP", self.reklama_okienko)
                self.kontrola("k) Aktuálne (aktualne.json)", self.aktualne)
                self.kontrola("l) Stránka Aktuálne (dlaždice, poradie, pätička)", self.stranka_aktualne)
                self.kontrola("m) Stĺpce (počítač, myš)", self.stlpce)
            finally:
                self.browser.close()

    def zhrnutie(self):
        ikona = {"ok": "✅", "warn": "⚠️", "fail": "❌"}
        chyby = sum(1 for s, *_ in self.vysledky if s == "fail")
        varov = sum(1 for s, *_ in self.vysledky if s == "warn")
        if chyby:
            celkovo = f"❌ **Web má problém** — chýb: {chyby}, varovaní: {varov}"
        elif varov:
            celkovo = f"✅ **Web funguje** (varovaní: {varov} — pozri ⚠️ nižšie)"
        else:
            celkovo = "✅ **Web funguje** — všetky kontroly prešli"
        r = [f"## Test webu {self.nazov_webu or ''} — {self.base}", "", celkovo, "",
             "| | Kontrola | Výsledok |", "|---|---|---|"]
        for stav, nazov, detail in self.vysledky:
            r.append(f"| {ikona[stav]} | {nazov} | {detail.replace('|', '/')} |")
        r.append("")
        r += [f"- {i}" for i in self.info]
        r.append(f"- **Snímky obrazovky:** {self.snimky} (príloha *test-webu* nižšie na tejto stránke, sekcia Artifacts)")
        r.append(f"- Čas testu: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC")
        text = "\n".join(r) + "\n"
        print("\n" + text)
        with open(os.path.join(self.vystup, "chyby.txt"), "w", encoding="utf-8") as f:
            f.write(text + "\n\nPODROBNOSTI:\n" + ("\n".join(self.log) or "(bez chýb)") + "\n")
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
                f.write(text)
        return chyby


def main():
    ap = argparse.ArgumentParser(description="Automatický test živého webu.")
    ap.add_argument("--url", default=os.environ.get("WEB_URL", ""), help="adresa webu, napr. https://sportlinky.sk/")
    ap.add_argument("--od", default="", help="čas štartu buildu (ISO) — čakaj, kým web nemá novšiu verziu")
    ap.add_argument("--vystup", default="test-vystup", help="priečinok na snímky a chyby.txt")
    a = ap.parse_args()
    if not a.url:
        sys.exit("Chýba adresa webu (--url alebo WEB_URL).")
    t = Test(a.url, a.vystup)
    try:
        t.spusti(a.od)
    except Exception as e:   # neočakávaná chyba samotného testu = tiež ❌, ale so zhrnutím
        t.vysledky.append(("fail", "Beh testu", f"{type(e).__name__}: {e}"))
        t.log.append(traceback.format_exc())
    sys.exit(1 if t.zhrnutie() else 0)


if __name__ == "__main__":
    main()
