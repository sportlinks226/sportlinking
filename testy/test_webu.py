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

NAVIGACIA_MS = 30_000       # max. čas na otvorenie stránky
CAKANIE_MS = 20_000         # max. čas na zobrazenie prvku (dlaždice, výsledky…)
POMALA_S = 15               # stránka pomalšia ako toto = ⚠️ varovanie
MIN_LINIEK = 10_000         # data.json musí mať aspoň toľko liniek
DEPLOY_MAX_S = 300          # čakanie na obnovenie GitHub Pages (max. 5 min)
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
        self.vystup = vystup
        os.makedirs(vystup, exist_ok=True)
        self.vysledky = []      # (stav, názov, detail)  stav: ok / warn / fail
        self.info = []          # doplňujúce riadky do zhrnutia
        self.log = []           # podrobný zoznam chýb (chyby.txt)
        self.data = None        # data.json zo živého webu
        self.lang = "sk"
        self.nazov_webu = ""
        self.ligy = []          # adresy z kontroly c) (pre mobil)
        self.snimky = 0

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
        return ctx

    def stranka(self, ctx, povolene_404=()):
        """Nová karta, ktorá si zbiera chyby JavaScriptu a chybné vlastné súbory."""
        page = ctx.new_page()
        page.chyby_js = []
        page.chyby_suborov = []

        def on_resp(r):
            u = urllib.parse.urlsplit(r.url)
            if u.netloc == self.host and r.status >= 400 and u.path not in povolene_404:
                page.chyby_suborov.append(f"{r.status} {u.path}")

        def on_fail(rq):
            u = urllib.parse.urlsplit(rq.url)
            if u.netloc == self.host and "ERR_ABORTED" not in (rq.failure or ""):
                page.chyby_suborov.append(f"nenačítané ({rq.failure}) {u.path}")

        page.on("pageerror", lambda e: page.chyby_js.append(str(e)))
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
                self.vysledky.append(("warn", "Nová verzia na webe",
                                      f"ani po {DEPLOY_MAX_S // 60} min nie je na webe novšia verzia "
                                      f"(Last-Modified: {posledny}, build začal {od}) — GitHub Pages sa "
                                      "obnovuje pomaly, test pokračuje so starou verziou"))
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
        adresy = re.findall(r"<loc>([^<]+)</loc>", text)
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
