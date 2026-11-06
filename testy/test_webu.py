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

Kontroly n) – p) (5.11.2026, Zadanie 34 — previerka 3, body 6, 28, 30): n) odkaz „Preskočiť na
obsah“ je prvý prvok a prvý Tab (→ #main), drobčeky sú <nav>, lišta Aktuálne <section>, reklamné
okienka Tab preskočí, odkazy v banneroch majú čitateľný názov; o) ikonky FB/IG na karte klubu
majú klikaciu plochu aspoň 24×24 px na počítači aj mobile a názov klubu ostáva hlavnou linkou;
p) na mobile sa hlavička po posune nadol zbalí (lupa ≥ 44×44 px, obsah neposkočí) a hore rozbalí.

Zadanie 35 (5.11.2026, previerka 3, bod 41): f) Banner overí aj obsah slotov — reklama partnera
(okienko s kódom ban.tipsport.sk) sa len označí (v teste blokovaná, žiadne falošné zobrazenie),
VLASTNÝ banner musí mať odkaz (nie „#") a obrázok (načítaný) alebo text. k) čaká na stiahnutie
aktualne.json až 15 s; appka, ktorá kód pre aktualne.json má, ale súbor nestiahne = ❌ (lišta
Aktuálne by chýbala); stará appka bez aktualne.json = ✅ s poznámkou (nie je to chyba webu).

Kontrola q) (6.11.2026, Zadanie 38a): stĺpcové zobrazenie (okná 1366×768 a 1280×720, domov a
jedna hlboká stránka, plná lišta Aktuálne = 20 podstrčených položiek len v prehliadači testu) —
po kliku na „▥ Stĺpce“, pri príchode so zapamätanými stĺpcami aj po Späť/Vpred začína pás
tesne pod hlavičkou a prvý stĺpec (hlavné sekcie) nemá vlastnú posuvnú lištu; návrat do dlaždíc.

Kontrola r) (6.11.2026, Zadanie 39): obľúbené ★ — v čistom prehliadači testu (localStorage,
web sa nemení; GoatCounter a reklamy blokované): hviezdička len pri linkách (nie pri priečinkoch
ani v lište Aktuálne), zóna počítač ≥ 40×20 / mobil ≥ 44×28 px pod ikonkou a mimo textu, klik na ňu
neotvorí web; pridať/odobrať, počet „★ N“ v hlavičke, uloženie po F5, neexistujúca linka sa pri
celých dátach vyradí, zmena v inej karte sa prejaví, panel (10 riadkov + „Zobraziť všetky (N) ›“,
Escape, klik mimo), /?oblubene (noindex, odobratie, Späť/Vpred), admin bez hviezdičiek, na mobile
★ v zbalenej hlavičke pred lupou. Appka bez obľúbených (starý web) = ✅ s poznámkou.
Zadanie 39a3: tlačidlo „☆ 0“ vidno aj pri 0, panel pri 0 s vetou (aj po odobratí poslednej pri
otvorenom paneli), „✕ Zavrieť obľúbené“ vráti na stránku, odkiaľ sa prišlo (priamy príchod → domov),
pri ~50 obľúbených je riadok s hľadaním a Zavrieť prilepený pod hlavičkou aj na konci zoznamu.
Zadanie 39a4: „🗑 Vymazať všetky“ dole pod zoznamom — otázka (Nie / Escape nič nezmení), Áno → 0
a „☆ 0“, stránka skočí hore, lišta „Vrátiť späť“ obnoví presne pôvodný zoznam (ID, poradie, časy), po F5 stav sedí.

Kontrola s) (7.11.2026, Zadanie 41): admin na LOKÁLNEJ KÓPII webu (generator.py z repozitára, SK aj EN,
testovacie heslo len v kópii dát; dáta z data.json repozitára, inak data-full.json z testovaného webu;
repozitár ani web sa nemenia, Tipsport a GoatCounter blokované): okno linky (poradie polí, zbalené „Viac“,
doplnenie https:// a odstránenie utm, návrh názvu z adresy, povinný Popis (EN), otázka pri slovenskom
názve, duplicita s cestou, linka ligy −1 navrch aj cez „Uložiť a pridať ďalšiu“, zaradenie abecedne aj
s CH, IG adresa v poli Facebook, http:// ostáva), ⤒/⤓ na SK (order) aj EN (order_en), na EN webe nová
linka dostane SK order aj order_en, 1366×768 bez prekrytia názvu, mobil 5 polí + tlačidlá bez „Viac“,
sprievodca po 🚀 Publikovať (3 kroky, odkaz na nahrávanie do sport-linky aj z EN webu) a značka
„⚠️ vN ešte nie je na webe“, ktorá zmizne po novej verzii webu (podstrčený version.txt).

Spustenie (lokálne):  python testy/test_webu.py --url https://sportlinky.sk/
Voliteľne:  --od 2026-11-02T02:30:00Z  (počkaj, kým živý web nemá novšiu verziu)
            --vystup test-vystup        (priečinok na snímky a zoznam chýb)
Zhrnutie sa zapíše aj do súboru z premennej GITHUB_STEP_SUMMARY (stránka behu v Actions).
"""

import argparse
import email.utils
import functools
import hashlib
import html
import http.server
import json
import os
import shutil
import subprocess
import tempfile
import threading
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
# UA_PC, X_TEST, BLOKOVANE (štatistiky a reklamy sa v teste BLOKUJÚ — žiadne falošné
# návštevy ani zobrazenia reklám), Zlyhanie, titulok_z_html, meta_z_html: testy/_spolocne.py
from _spolocne import BLOKOVANE, UA_PC, X_TEST, Zlyhanie, meta_z_html, titulok_z_html   # spoločné (Zadanie 36)
UA_MOBIL = ("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36")

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
AKT_CAKANIE_S = 15          # k) max. čakanie, kým appka stiahne (podstrčený) aktualne.json


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

    def kontext(self, mobil=False, okno=None):
        if mobil:
            ctx = self.browser.new_context(viewport={"width": 390, "height": 844},
                                           device_scale_factor=2, is_mobile=True,
                                           has_touch=True, user_agent=UA_MOBIL)
        else:
            w, h = okno or (1366, 900)
            ctx = self.browser.new_context(viewport={"width": w, "height": h},
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
        main = re.search(r'<main id="main"[^>]*>(.*?)</main>', text, re.S)
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
            raise Zlyhanie(f"data.json nie je platný JSON ({e})") from e
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
                raise Zlyhanie(f"hľadanie „{hladany}“ neukázalo výsledok s týmto názvom") from None
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
    # Zadanie 35 (previerka 3, bod 41): okrem kontajnera aj obsah slotov. Reklama partnera
    # (okienko <iframe> s kódom ban.tipsport.sk) sa NEnačíta — doména je blokovaná, takže
    # žiadne falošné zobrazenie; len sa označí. VLASTNÝ banner (obrázok alebo HTML bez
    # skriptu, napr. EN „Live This Week") musí mať odkaz (nie „#") a obrázok alebo text.
    BANNER_JS = """() => [1, 2].map(n => {
      const el = document.getElementById(n === 1 ? 'bannerSlot' : 'bannerSlot2');
      if(!el) return {n: n, chyba: true};
      const a = el.querySelector('a[href]'), img = el.querySelector('img');
      return {n: n, bid: el.dataset.bid || '', partner: !!el.querySelector('iframe'),
              prazdny: !!el.querySelector('.banner-placeholder'), skryty: getComputedStyle(el).display === 'none',
              href: a ? a.getAttribute('href') : null,
              img: img ? {src: img.getAttribute('src') || '', ok: img.complete && img.naturalWidth > 0} : null,
              svg: !!el.querySelector('svg'), text: (el.innerText || '').trim().slice(0, 60)};
    })"""

    def banner(self, pokus):
        ctx = self.kontext()
        try:
            page = self.stranka(ctx)
            page.goto(self.base, wait_until="load")
            self.cakaj_na_appku(page)
            if page.locator("#bannerSlot").count() == 0:
                raise Zlyhanie("na domove chýba kontajner pre banner (#bannerSlot)")
            try:   # obrázok vlastného bannera sa môže ešte sťahovať
                page.wait_for_function("() => [...document.querySelectorAll('#bannerSlot img, #bannerSlot2 img')]"
                                       ".every(i => i.complete)", timeout=10_000)
            except Exception:
                pass
            sloty = page.evaluate(self.BANNER_JS)
        finally:
            ctx.close()
        popis, zle = [], []
        for s in sloty:
            meno = f"slot {s['n']}"
            if s.get("chyba"):
                popis.append(f"{meno}: kontajner chýba")
            elif s["partner"]:
                popis.append(f"{meno}: reklama partnera v okienku (v teste blokovaná)")
            elif s["prazdny"] or not s["bid"]:
                popis.append(f"{meno}: bez bannera")
            else:
                ch = []
                if not s["href"] or s["href"].strip() == "#":
                    ch.append(f"odkaz {s['href']!r}")
                if s["img"] is not None and not s["img"]["ok"]:
                    ch.append(f"obrázok {s['img']['src']!r} sa nenačítal")
                if s["img"] is None and not s["svg"] and not s["text"]:
                    ch.append("nemá obrázok ani text")
                if ch:
                    zle.append(f"{meno} (vlastný banner {s['bid']}): " + ", ".join(ch))
                else:
                    popis.append(f"{meno}: vlastný banner {s['bid']} — odkaz {s['href']}, "
                                 + ("obrázok OK" if s["img"] else "obsah OK"))
        if zle:
            raise Zlyhanie("; ".join(zle))
        return "ok", "; ".join(popis) + " (reklamy partnera v teste blokované)"

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
                raise Zlyhanie("/#admin neotvoril prihlasovacie okno") from None
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
                    raise Zlyhanie(f"{u} nie je platný JSON ({e})") from e
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
            for a, k in zip(vid, karty, strict=True):   # dĺžky sedia (hrefy == cakane vyššie)
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
            # Zadanie 35 (previerka 3, bod 41): namiesto pevných 3 s čaká na stiahnutie
            # aktualne.json až AKT_CAKANIE_S (pomalý web / sieť nesmie dať falošný výsledok)
            koniec = time.time() + AKT_CAKANIE_S
            while not ziadosti and time.time() < koniec:
                page.wait_for_timeout(250)
            if not ziadosti:
                if "aktualne.json" in text:
                    # appka kód pre aktualne.json MÁ, ale súbor nestiahla → lišta Aktuálne
                    # by na webe chýbala (skutočná chyba; kontrola sa ešte raz zopakuje)
                    raise Zlyhanie(f"appka do {AKT_CAKANIE_S} s nestiahla aktualne.json (podstrčený súbor) — "
                                   "lišta Aktuálne by na webe chýbala")
                # stará appka (pred Zadaním 16a) aktualne.json ešte nesťahuje — napr. test
                # pull requestu proti staršiemu živému webu. Nie je to chyba webu → bez ⚠️.
                popis_info.insert(0, f"zdroj {zdroj}: {len(items)} položiek, viditeľných {len(cakane)}, na lište {len(cakane)}")
                popis_info.append("appka na webe je staršia verzia bez aktualne.json — test s podstrčeným súborom "
                                  "preskočený (nie je to chyba)")
                return stav, "; ".join(popis_info)
            page.wait_for_timeout(500)
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
            # Zadanie 38a: po prepnutí sa stránka plynulo posunie (pás pod hlavičku) — počkaj, kým
            # sa posun zastaví (počas posunu sa pohyb myši nad posúvaným obsahom zámerne ignoruje)
            y0, koniec = -1, time.time() + 5
            while time.time() < koniec:
                page.wait_for_timeout(200)
                y = page.evaluate("window.scrollY")
                if y == y0:
                    break
                y0 = y

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

    # ------------------------------------------------ q) stĺpce: pás pod hlavičkou (Zadanie 38a)
    def stlpce_posun(self, pokus):
        """Po kliknutí na „▥ Stĺpce“ aj pri príchode so zapamätanými stĺpcami sa stránka
        (raz) posunie tak, že pás stĺpcov začína tesne pod hlavičkou (colsStickTop ± 2 px);
        prvý stĺpec (hlavné sekcie) nemá vlastnú posuvnú lištu; návrat do dlaždíc funguje;
        Späť/Vpred nechá pás pod hlavičkou. Lišta Aktuálne je plná (20 podstrčených
        položiek LEN v prehliadači testu — web ani aktualne.json sa nemenia). Reklamy sú
        blokované (žiadne falošné zobrazenia)."""
        polozky = [{"id": f"q{i}", "order": i, "icon": "⚽", "name": f"TEST Aktuálne položka {i + 1}",
                    "name_en": f"TEST live item {i + 1}", "url": f"https://test.invalid/q{i}",
                    "addedAt": int(time.time() * 1000) - 5 * 86400_000} for i in range(20)]
        telo = json.dumps({"version": 1, "items": polozky}, ensure_ascii=False)
        stranky = [self.base] + self.ligy[:1]
        info = []

        def stav(page):
            return page.evaluate("""() => { const w = document.getElementById('colsWrap'); if(!w) return null;
                const c = w.querySelector('.col[data-lv="0"]'); const k = [...document.querySelectorAll('#aktualneScroll .akt-card')];
                return {top: Math.round(w.getBoundingClientRect().top), stick: colsStickTop(),
                        ch: c ? c.clientHeight : 0, sh: c ? c.scrollHeight : 0, sy: Math.round(scrollY),
                        riadky: new Set(k.map(e => e.offsetTop)).size}; }""")

        def over(page, kde):
            # plynulý posun / dočítaná lišta Aktuálne — počkaj, kým sa pás ustáli pod hlavičkou
            koniec = time.time() + 6
            s, pred = stav(page), None
            while s and (abs(s["top"] - s["stick"]) > 2 or s != pred) and time.time() < koniec:
                page.wait_for_timeout(250)
                s, pred = stav(page), s
            if not s:
                raise Zlyhanie(f"{kde}: pás stĺpcov (#colsWrap) chýba")
            if abs(s["top"] - s["stick"]) > 2:
                raise Zlyhanie(f"{kde}: pás začína na {s['top']} px, má byť pod hlavičkou na {s['stick']} px")
            if s["sh"] > s["ch"] + 1:
                raise Zlyhanie(f"{kde}: prvý stĺpec (hlavné sekcie) má vlastnú posuvnú lištu ({s['ch']}/{s['sh']} px)")
            return s

        def otvor(ctx, url):
            page = self.stranka(ctx)
            page.route("**/aktualne.json*", lambda r: r.fulfill(status=200, content_type="application/json", body=telo,
                                                                headers={"Access-Control-Allow-Origin": "*"}))
            page.goto(url, wait_until="load")
            self.cakaj_na_appku(page)
            koniec = time.time() + CAKANIE_MS / 1000
            while not page.evaluate("typeof DB !== 'undefined' && !!DB.nodes && DB.nodes.length > 100 && !DB._partial"):
                if time.time() > koniec:
                    raise Zlyhanie("appka nenačítala celé dáta (data.json) do limitu")
                page.wait_for_timeout(250)
            page.wait_for_timeout(800)
            return page

        for okno in ((1366, 768), (1280, 720)):
            ctx = self.kontext(okno=okno)
            try:
                for url in stranky:
                    kde = f"{okno[0]}×{okno[1]} {urllib.parse.urlsplit(url).path}"
                    page = otvor(ctx, url)
                    if not page.evaluate("typeof colsStick === 'function'"):
                        page.close()
                        return "ok", "appka na webe je staršia verzia bez posunu stĺpcov (Zadanie 38a) — preskočené"
                    page.click("#vSwitch button[data-mode=cols]")
                    s = over(page, kde + " po kliku na Stĺpce")
                    page.click("#vSwitch button[data-mode=tiles]")
                    page.wait_for_timeout(500)
                    if page.locator("#colsWrap").count() or not page.locator("#main a[href]:visible").count():
                        raise Zlyhanie(f"{kde}: po návrate do dlaždíc ostal pás stĺpcov alebo nie sú dlaždice")
                    self.over_chyby(page, kde)
                    # dlaždice sa zapamätali — pre príchod nižšie znova zapamätaj stĺpce
                    page.evaluate("localStorage.setItem('sportStromView', 'cols')")
                    page.close()
                    # príchod so zapamätaným režimom stĺpcov (localStorage z kliku vyššie)
                    page = otvor(ctx, url)
                    s2 = over(page, kde + " pri príchode so zapamätanými stĺpcami")
                    # Späť/Vpred: preklik do priečinka v 2. stĺpci (ak je), posun hore, Späť → pás opäť pod hlavičkou
                    pol = page.locator("#colsWrap .col[data-lv='1'] .cit[data-t='f']")
                    if pol.count():
                        adresa = page.evaluate("location.pathname")
                        pol.first.click()
                        page.wait_for_timeout(600)
                        page.evaluate("window.scrollTo(0, 0)")
                        page.wait_for_timeout(400)
                        page.go_back()
                        page.wait_for_timeout(600)
                        if page.evaluate("location.pathname") != adresa:
                            raise Zlyhanie(f"{kde}: Späť neviedlo na {adresa}")
                        over(page, kde + " po Späť")
                        page.go_forward()
                        page.wait_for_timeout(600)
                        over(page, kde + " po Vpred")
                    if okno == (1366, 768):
                        self.snimka(page, "14-stlpce-pod-hlavickou" + ("" if url == self.base else "-hlbka"))
                    self.over_chyby(page, kde + " (príchod)")
                    page.close()
                    info.append(f"{kde}: pás {s['top']}/{s2['top']} px (hlavička {s['stick']}), 1. stĺpec {s2['ch']}/{s2['sh']}, Aktuálne {s2['riadky']} riadky")
            finally:
                ctx.close()
        return "ok", "; ".join(info)

    # ------------------------------------------------ n) – p) Zadanie 34 (previerka 3, body 6, 28, 30)
    def pristupnost(self, pokus):
        """Odkaz „Preskočiť na obsah“ je prvý prvok a prvý Tab; vedie na #main (tabindex -1);
        drobčeky sú <nav aria-label>, lišta Aktuálne <section aria-label>; reklamné okienka
        Tab preskočí; každý odkaz v banneri má čitateľný názov (text, alt alebo aria-label)."""
        ctx = self.kontext()
        try:
            page = self.stranka(ctx)
            page.goto(self.base, wait_until="load")
            self.cakaj_na_appku(page)
            page.wait_for_timeout(1500)
            prvy = page.evaluate("""() => { const a = document.body.firstElementChild;
                return a ? [a.tagName, a.className, a.getAttribute('href'), a.textContent.trim()] : null; }""")
            if not prvy or prvy[1] != "skip-link" or prvy[2] != "#main" or not prvy[3]:
                raise Zlyhanie(f"prvý prvok v <body> nie je odkaz „Preskočiť na obsah“ (#main): {prvy}")
            page.keyboard.press("Tab")
            fokus = page.evaluate("""() => { const a = document.activeElement, r = a.getBoundingClientRect();
                return [a.className, Math.round(r.top), Math.round(r.height)]; }""")
            if fokus[0] != "skip-link" or fokus[1] < 0 or fokus[2] < 10:
                raise Zlyhanie(f"prvý Tab nie je na viditeľnom odkaze „Preskočiť na obsah“: {fokus}")
            page.keyboard.press("Enter")
            page.wait_for_timeout(300)
            if page.evaluate("document.activeElement.id") != "main":
                raise Zlyhanie("Enter na „Preskočiť na obsah“ nepresunul kurzor na #main")
            stav = page.evaluate("""() => {
                const m = document.getElementById('main'), b = document.getElementById('breadcrumb'),
                      w = document.getElementById('aktualneWrap');
                const bez = [...document.querySelectorAll('.banner-slot a[href]')].filter(a =>
                    !(a.getAttribute('aria-label') || '').trim() && !a.textContent.trim()
                    && ![...a.querySelectorAll('img[alt]')].some(i => i.alt.trim()));
                return {mainTab: m && m.getAttribute('tabindex'),
                        bc: b && b.tagName, bcLabel: b && b.getAttribute('aria-label'),
                        akt: w && w.tagName, aktLabel: w && w.getAttribute('aria-label'),
                        iframy: document.querySelectorAll('iframe.adframe').length,
                        iframyTab: [...document.querySelectorAll('iframe.adframe')].filter(f => f.getAttribute('tabindex') !== '-1').length,
                        bannerBezNazvu: bez.length}; }""")
            chyby = []
            if stav["mainTab"] != "-1":
                chyby.append("#main nemá tabindex=-1")
            if stav["bc"] != "NAV" or not stav["bcLabel"]:
                chyby.append(f"#breadcrumb nie je <nav aria-label> ({stav['bc']})")
            if stav["akt"] != "SECTION" or not stav["aktLabel"]:
                chyby.append(f"#aktualneWrap nie je <section aria-label> ({stav['akt']})")
            if stav["iframyTab"]:
                chyby.append(f"{stav['iframyTab']} reklamných okienok nemá tabindex=-1")
            if stav["bannerBezNazvu"]:
                chyby.append(f"{stav['bannerBezNazvu']} odkazov v banneri bez čitateľného názvu")
            if chyby:
                raise Zlyhanie("; ".join(chyby))
            self.over_chyby(page, "prístupnosť")
        finally:
            ctx.close()
        return "ok", (f"skip-link „{prvy[3]}“ = prvý Tab → #main; drobčeky <nav „{stav['bcLabel']}“>, "
                      f"Aktuálne <section „{stav['aktLabel']}“>; okienok bez Tabu: {stav['iframy']}")

    def vyber_klub_so_socs(self):
        """Názvy liniek (klubov), ktoré majú aj Facebook, aj Instagram (polia fb, ig) a jedinečný
        názov — v appke ich nájde hľadanie a karta výsledku má ikonky FB/IG."""
        uzly = self.data.get("nodes", [])
        def meno(n):
            return (n.get("name_en") or n.get("name") or "") if self.lang == "en" else (n.get("name") or "")
        pocet = {}
        for n in uzly:
            pocet[meno(n)] = pocet.get(meno(n), 0) + 1
        nevid = "enOnly" if self.lang == "sk" else None
        kand = [meno(n) for n in uzly if n.get("type") == "link" and n.get("fb") and n.get("ig")
                and 6 <= len(meno(n)) <= 30 and pocet[meno(n)] == 1 and re.fullmatch(r"[\w .'-]+", meno(n))
                and not (nevid and n.get(nevid)) and not (self.lang == "en" and n.get("en") is False)]
        random.shuffle(kand)
        return kand[:3]

    # JavaScript: klikacia plocha ikoniek (elementFromPoint po 1 px okolo ikonky) a kontrola,
    # že každý viditeľný bod názvu klubu otvorí hlavnú linku (nie FB/IG)
    SOCS_JS = """() => {
        const out = [];
        for (const card of [...document.querySelectorAll('#main .card-link.has-soc')].slice(0, 4)) {
            card.scrollIntoView({block: 'center'});
            const main = card.querySelector(':scope > a');
            for (const a of card.querySelectorAll('.socs a.si')) {
                const r = a.getBoundingClientRect();
                let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
                for (let y = Math.floor(r.top - 20); y <= r.bottom + 20; y++)
                    for (let x = Math.floor(r.left - 20); x <= r.right + 20; x++) {
                        const e = document.elementFromPoint(x + 0.5, y + 0.5);
                        if (e && e.closest('a.si') === a) { x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); }
                    }
                out.push([x1 - x0 + 1, y1 - y0 + 1]);
            }
            let textOk = true;
            const n = main && main.querySelector('.cl-name');
            if (n) { const b = n.getBoundingClientRect();
                for (let y = b.top + 2; y < b.bottom - 2; y += 3) for (let x = b.left + 2; x < b.right - 2; x += 3) {
                    const e = document.elementFromPoint(x, y); if (!e || e.closest('.card-link > a') !== main) textOk = false; } }
            if (!textOk) out.push('text');
        }
        return out; }"""

    def socs_plocha(self, pokus):
        if not self.data:
            raise Zlyhanie("bez data.json sa nedá vybrať klub s ikonkami FB/IG")
        mena = self.vyber_klub_so_socs()
        if not mena:
            return "warn", "v dátach nie je klub s Facebookom aj Instagramom — kontrola preskočená"
        popis = []
        for mobil in (False, True):
            ctx = self.kontext(mobil=mobil)
            try:
                page = self.stranka(ctx)
                page.goto(self.base, wait_until="load")
                self.cakaj_na_appku(page)
                plochy = None
                for meno in mena:
                    page.fill("#srch", meno)
                    try:
                        page.wait_for_selector("#main .card-link.has-soc .socs a.si", state="visible", timeout=8000)
                    except Exception:
                        continue
                    page.wait_for_timeout(500)
                    plochy = page.evaluate(self.SOCS_JS)
                    break
                kde = "mobil 390 px" if mobil else "počítač 1366 px"
                if not plochy:
                    self.snimka(page, "o-socs-chyba")
                    raise Zlyhanie(f"{kde}: hľadanie {mena} neukázalo kartu s ikonkami FB/IG")
                if "text" in plochy:
                    raise Zlyhanie(f"{kde}: ťuknutie na názov klubu by trafilo ikonku FB/IG, nie web klubu")
                male = [p for p in plochy if p[0] < 24 or p[1] < 24]
                if male:
                    raise Zlyhanie(f"{kde}: klikacia plocha ikonky FB/IG pod 24×24 px: {male}")
                self.over_chyby(page, f"FB/IG ({kde})")
                popis.append(f"{kde}: najmenšia {min(p[0] for p in plochy)}×{min(p[1] for p in plochy)} px "
                             f"({len(plochy)} ikoniek, „{meno}“)")
            finally:
                ctx.close()
        return "ok", "; ".join(popis)

    def hlavicka_mobil(self, pokus):
        """Mobil (390 px): po posune nadol o viac než 150 px sa hlavička zbalí na jeden riadok
        (logo + lupa ≥ 44×44), obsah pod ňou sa nepohne; pri návrate hore (< 60 px) sa rozbalí."""
        adresy = [self.base] + list(self.ligy)
        ctx = self.kontext(mobil=True)
        try:
            page = self.stranka(ctx)
            for url in adresy:
                page.goto(url, wait_until="load")
                self.cakaj_na_appku(page)
                page.wait_for_timeout(1200)
                if page.evaluate("document.documentElement.scrollHeight - innerHeight") > 450:
                    break
            else:
                return "warn", "žiadna z testovaných stránok nie je na mobile dosť dlhá — kontrola preskočená"
            STAV = """() => { const h = document.querySelector('header'), b = document.getElementById('breadcrumb'),
                l = document.getElementById('hLupa').getBoundingClientRect();
                return {min: document.body.classList.contains('hdr-min'), h: h.offsetHeight,
                        bc: Math.round(b.getBoundingClientRect().top + scrollY), lupa: [Math.round(l.width), Math.round(l.height)]}; }"""
            s0 = page.evaluate(STAV)
            if s0["min"]:
                raise Zlyhanie("hlavička je zbalená už na vrchu stránky")
            for y in range(0, 401, 50):          # posun nadol po krokoch ako prstom
                page.evaluate("y => scrollTo(0, y)", y)
                page.wait_for_timeout(60)
            s1 = page.evaluate(STAV)
            self.snimka(page, "p-mobil-hlavicka-zbalena")
            if not s1["min"] or s1["h"] >= s0["h"]:
                raise Zlyhanie(f"po posune o 400 px sa hlavička nezbalila (výška {s0['h']} → {s1['h']} px)")
            if s1["lupa"][0] < 44 or s1["lupa"][1] < 44:
                raise Zlyhanie(f"tlačidlo lupy je menšie než 44×44 px: {s1['lupa']}")
            if abs(s1["bc"] - s0["bc"]) > 1:
                raise Zlyhanie(f"obsah pod hlavičkou poskočil pri zbalení ({s0['bc']} → {s1['bc']} px)")
            page.evaluate("scrollTo(0, 100)")    # medzi 60 a 150 px sa stav nemení
            page.wait_for_timeout(150)
            if not page.evaluate(STAV)["min"]:
                raise Zlyhanie("hlavička sa rozbalila už na 100 px (má až pod 60 px)")
            page.evaluate("scrollTo(0, 0)")
            page.wait_for_timeout(150)
            s2 = page.evaluate(STAV)
            if s2["min"] or s2["h"] != s0["h"]:
                raise Zlyhanie(f"pri návrate hore sa hlavička nerozbalila (výška {s2['h']} px)")
            self.over_chyby(page, "hlavička na mobile")
            cesta = urllib.parse.urlsplit(page.url).path
        finally:
            ctx.close()
        return "ok", f"{cesta}: plná {s0['h']} px → zbalená {s1['h']} px (lupa {s1['lupa'][0]}×{s1['lupa'][1]}) → hore {s2['h']} px, obsah bez skoku"

    # ------------------------------------------------ r) obľúbené ★ (Zadanie 39)
    # Obľúbené sú LEN v prehliadači (localStorage) — test si ich robí vo vlastnom, čistom
    # prehliadači; web ani dáta nemení. GoatCounter (počítanie pridania „obl/+<id>“)
    # a reklamy sú v teste blokované (BLOKOVANE) — žiadne falošné počty ani zobrazenia.
    OBL_KLUC = "sportLinkyObl"
    OBL_CELE_DATA = "() => typeof DB !== 'undefined' && DB.nodes && DB.nodes.length > 0 && !DB._partial"

    def vyber_priecinok_obl(self):
        """Priečinok s 12–60 linkami (nie Aktuálne, nie skrytý v tomto jazyku) — na ňom sa
        pridáva hviezdičkou. Viac ako 10 liniek treba na „Zobraziť všetky (N) ›“."""
        uzly = self.data.get("nodes", [])
        podla_id = {n["id"]: n for n in uzly}
        def skryty(n):
            while n:
                if (self.lang == "sk" and n.get("enOnly")) or (self.lang == "en" and n.get("en") is False):
                    return True
                n = podla_id.get(n.get("parentId"))
            return False
        linky = {}
        for n in uzly:
            if n.get("type") == "link" and not skryty(n):
                linky[n.get("parentId")] = linky.get(n.get("parentId"), 0) + 1
        kand = [pid for pid, k in linky.items() if 12 <= k <= 60 and pid in podla_id
                and podla_id[pid].get("parentId") and pid != "f_ltw" and not skryty(podla_id[pid])]
        random.shuffle(kand)
        return kand[:3]

    # zóna hviezdičky na karte: veľkosť, neprekrýva ikonku webu ani text, klik do jej stredu trafí hviezdičku
    OBL_ZONA_JS = """() => {
        const out = [];
        for (const c of [...document.querySelectorAll('#main .card-link.has-star')].slice(0, 6)) {
            const s = c.querySelector(':scope > .star'), a = c.querySelector(':scope > a');
            if (!s || !a) { out.push({chyba: 'karta bez hviezdičky alebo odkazu'}); continue; }
            c.scrollIntoView({block: 'center'});
            const z = s.getBoundingClientRect(), ic = a.firstElementChild.getBoundingClientRect();
            const t = a.querySelector('.cl-name').getBoundingClientRect();
            const e = document.elementFromPoint(z.left + z.width / 2, z.top + z.height / 2);
            out.push({w: Math.round(z.width), h: Math.round(z.height), podIkonkou: z.top >= ic.bottom - 0.5,
                      mimoTextu: z.right <= t.left + 0.5, trafi: !!(e && e.closest('.star') === s),
                      vOdkaze: !!s.closest('a')});
        }
        return out; }"""

    def obl_zoznam(self, page):
        return page.evaluate(f"() => {{ try {{ return JSON.parse(localStorage.getItem('{self.OBL_KLUC}') || '[]').map(x => x.id); }} catch (e) {{ return null; }} }}")

    def obl_pocet_hlavicka(self, page):
        """Počet v tlačidle „★ N“ v hlavičke; None = tlačidlo nie je vidno."""
        if not page.locator("#hFav").is_visible():
            return None
        return int(page.locator("#hFavN").inner_text().strip() or "0")

    def obl_vyber_ids(self, k):
        """k náhodných ID liniek, ktoré návštevník tohto webu vidí (nie skryté v jazyku, nie Aktuálne)."""
        uzly = self.data.get("nodes", [])
        podla_id = {n["id"]: n for n in uzly}
        def skryty(n):
            while n:
                if (self.lang == "sk" and n.get("enOnly")) or (self.lang == "en" and n.get("en") is False) or n.get("id") == "f_ltw":
                    return True
                n = podla_id.get(n.get("parentId"))
            return False
        ids = [n["id"] for n in uzly if n.get("type") == "link" and n.get("parentId") and not skryty(n)]
        return random.sample(ids, min(k, len(ids)))

    def obl_dlhy(self, page, kde):
        """Zadanie 39a3: ~50 obľúbených (len v prehliadači testu), priamy príchod na /?oblubene:
        po posune na koniec zoznamu je riadok s „Hľadaj v obľúbených“ a „Zavrieť“ prilepený pod
        hlavičkou a vidno ho; priamy príchod → „Zavrieť“ vedie na domov."""
        ids = self.obl_vyber_ids(50)
        page.evaluate("([k, a]) => localStorage.setItem(k, JSON.stringify(a.map((id, i) => ({id, t: Date.now() - i * 1000}))))",
                      [self.OBL_KLUC, ids])
        o = urllib.parse.urlsplit(self.base)
        page.goto(f"{o.scheme}://{o.netloc}{o.path}?" + ("favorites" if self.lang == "en" else "oblubene"), wait_until="load")
        page.wait_for_function(self.OBL_CELE_DATA, timeout=30_000)
        page.wait_for_selector("#fvBar #fvClose", state="visible")
        page.wait_for_selector("#main .card-link > .star.on", state="visible")
        if not page.locator("#fvSrch").is_visible():
            raise Zlyhanie(f"{kde}: pri {len(ids)} obľúbených chýba políčko „Hľadaj v obľúbených“")
        for y in range(0, 100001, 600):            # posun po krokoch až na koniec (hlavička sa na mobile zbalí)
            page.evaluate("y => scrollTo(0, y)", y)
            page.wait_for_timeout(40)
            if page.evaluate("innerHeight + scrollY >= document.documentElement.scrollHeight - 2"):
                break
        page.wait_for_timeout(300)
        st = page.evaluate("""() => { const b = document.getElementById('fvClose').getBoundingClientRect(),
            s = document.getElementById('fvSrch').getBoundingClientRect(), h = document.querySelector('header').getBoundingClientRect();
            const e = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
            return {y: Math.round(scrollY), hore: Math.round(b.top), hlav: Math.round(h.bottom), trafi: !!(e && e.closest('#fvClose')),
                    srch: s.top >= h.bottom - 1 && s.bottom <= innerHeight}; }""")
        self.snimka(page, "r-obl-dlhy-" + ("mobil" if kde == "mobil" else "pc"))
        if st["y"] < 300 or not st["trafi"] or not st["srch"] or st["hore"] < st["hlav"] - 1:
            raise Zlyhanie(f"{kde}: pri posune na koniec {len(ids)} obľúbených nie je „Zavrieť“/hľadanie vidno pod hlavičkou: {st}")
        vym = self.obl_vymazat(page, kde, len(ids))
        page.click("#fvClose")
        page.wait_for_timeout(500)
        if urllib.parse.urlsplit(page.url).path != o.path or urllib.parse.urlsplit(page.url).query:
            raise Zlyhanie(f"{kde}: „Zavrieť“ pri priamom príchode nevedie na domov (adresa {page.url})")
        return f"{kde}: {len(ids)} obľúbených, na konci (posun {st['y']} px) „Zavrieť“ pod hlavičkou, {vym}, priamy príchod → domov"

    def obl_vymazat(self, page, kde, n):
        """Zadanie 39a4: „🗑 Vymazať všetky“ dole pod zoznamom — poistka 1 (otázka; Nie / Escape nič
        nezmení), Áno → 0 a „☆ 0“, poistka 2 (lišta „Vrátiť späť“) obnoví PRESNE pôvodný zoznam
        (ID, poradie, časy); po F5 stav sedí. Všetko len v prehliadači testu, GoatCounter blokovaný."""
        surovy = lambda: page.evaluate(f"() => localStorage.getItem('{self.OBL_KLUC}')")
        povodny = surovy()
        btn = page.locator("#fvClear #fvClearBtn")
        btn.scroll_into_view_if_needed()
        if not btn.is_visible():
            raise Zlyhanie(f"{kde}: pod zoznamom obľúbených chýba tlačidlo „Vymazať všetky“")
        if page.locator("#fvBar #fvClearBtn, #favPanel #fvClearBtn").count():
            raise Zlyhanie(f"{kde}: „Vymazať všetky“ je v prilepenom riadku alebo v paneli (má byť len dole)")
        btn.click()
        page.wait_for_selector("#fvAsk", state="visible")
        if f"{n}" not in page.locator("#fvAsk").inner_text() or surovy() != povodny:
            raise Zlyhanie(f"{kde}: po kliku na „Vymazať všetky“ chýba otázka s počtom {n} alebo sa už niečo vymazalo")
        self.snimka(page, f"r-obl-vymazat-otazka-{kde}")
        page.click("#fvNo")
        page.wait_for_selector("#fvClearBtn", state="visible")
        if surovy() != povodny or page.locator("#main .card-link").count() != n:
            raise Zlyhanie(f"{kde}: „Nie“ zmenilo obľúbené")
        page.click("#fvClearBtn")
        page.wait_for_selector("#fvAsk", state="visible")
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
        if (not page.locator("#fvClearBtn").is_visible() or surovy() != povodny
                or urllib.parse.urlsplit(page.url).query not in ("oblubene", "favorites")):
            raise Zlyhanie(f"{kde}: Escape pri otázke nemá byť nič iné než „Nie“ (stránka obľúbených ostáva)")
        page.click("#fvClearBtn")
        if page.evaluate("scrollY") < 50:
            raise Zlyhanie(f"{kde}: pred „Áno“ nie je stránka posunutá nadol — skok hore sa nedá overiť")
        page.click("#fvYes")
        page.wait_for_selector("#favUndo #favUndoBtn", state="visible")
        try:   # po vymazaní skok hore — prázdny stav aj „Zavrieť“ hneď vidno
            page.wait_for_function("() => scrollY === 0", timeout=3000)
        except Exception:
            raise Zlyhanie(f"{kde}: po „Áno, vymazať“ stránka neskočila hore (posun {page.evaluate('scrollY')} px)") from None
        if not page.locator("#fvClose").is_visible() or not page.locator("#main .empty").is_visible():
            raise Zlyhanie(f"{kde}: po vymazaní nie je hore vidno prázdny stav a „Zavrieť“")
        zoz = self.obl_zoznam(page)
        if zoz != [] or page.locator("#hFav").inner_text().split() != ["☆", "0"] or page.locator("#main .card-link").count():
            raise Zlyhanie(f"{kde}: po „Áno“ nie je 0 obľúbených a „☆ 0“ (úložisko {zoz}, hlavička {page.locator('#hFav').inner_text()})")
        if f"({n})" not in page.locator("#favUndo").inner_text():
            raise Zlyhanie(f"{kde}: lišta „Vrátiť späť“ neukazuje počet {n}")
        self.snimka(page, f"r-obl-vymazat-lista-{kde}")
        page.click("#favUndoBtn")
        page.wait_for_selector("#main .card-link > .star.on", state="visible")
        if surovy() != povodny:
            raise Zlyhanie(f"{kde}: „Vrátiť späť“ neobnovilo PRESNE pôvodný zoznam (ID, poradie, časy)")
        if page.locator("#favUndo").count() or self.obl_pocet_hlavicka(page) != n or page.locator("#main .card-link").count() != n:
            raise Zlyhanie(f"{kde}: po „Vrátiť späť“ nesedí lišta, hlavička ({self.obl_pocet_hlavicka(page)}) alebo počet kariet")
        page.reload(wait_until="load")
        page.wait_for_function(self.OBL_CELE_DATA, timeout=30_000)
        page.wait_for_selector("#main .card-link > .star.on", state="visible")
        page.wait_for_timeout(300)
        if surovy() != povodny or self.obl_pocet_hlavicka(page) != n:
            raise Zlyhanie(f"{kde}: po F5 nesedí obnovený zoznam obľúbených")
        return "vymazať: otázka/Nie/Escape/Áno → skok hore, ☆ 0 → Vrátiť späť = rovnaký zoznam aj po F5"

    def oblubene(self, pokus):
        if not self.data:
            raise Zlyhanie("bez data.json sa nedá vybrať priečinok s linkami")
        kand = self.vyber_priecinok_obl()
        if not kand:
            return "warn", "v dátach nie je priečinok s 12–60 linkami — kontrola preskočená"
        popis = []
        ctx = self.kontext()
        try:
            page = self.stranka(ctx)
            page.goto(self.base, wait_until="load")
            self.cakaj_na_appku(page)
            if page.evaluate("typeof favToggle") != "function":
                return "ok", "appka na webe ešte nemá obľúbené (Zadanie 39) — kontrola preskočená"
            page.wait_for_function(self.OBL_CELE_DATA, timeout=30_000)
            # Zadanie 39a3: tlačidlo je vidno aj pri 0 — sivé „☆ 0“, panel s vetou o hviezdičke
            if not page.locator("#hFav").is_visible() or page.locator("#hFav").inner_text().split() != ["☆", "0"]:
                raise Zlyhanie(f"pri 0 obľúbených nie je v hlavičke tlačidlo „☆ 0“ "
                               f"({page.locator('#hFav').inner_text() if page.locator('#hFav').is_visible() else 'nevidno'})")
            if "(0)" not in (page.get_attribute("#hFav", "aria-label") or ""):
                raise Zlyhanie(f"aria-label tlačidla pri 0: „{page.get_attribute('#hFav', 'aria-label')}“ (má byť „… (0)“)")
            page.click("#hFav")
            page.wait_for_selector("#favPanel .fp-empty", state="visible")
            if "(0)" not in page.locator("#fpTitle").inner_text() or "☆" not in page.locator("#favPanel .fp-empty").inner_text():
                raise Zlyhanie("panel pri 0 nemá nadpis „☆ … (0)“ a vetu o hviezdičke ☆")
            page.keyboard.press("Escape")
            # adresu priečinka vypočíta appka (urlForId) — rovnaká ako statická stránka
            o = urllib.parse.urlsplit(self.base)
            fid = kand[0]
            url = f"{o.scheme}://{o.netloc}" + page.evaluate("id => urlForId(id)", fid)
            page.goto(url, wait_until="load")
            self.cakaj_na_appku(page)
            page.wait_for_selector("#main .card-link .star", state="visible")
            page.wait_for_function(self.OBL_CELE_DATA, timeout=30_000)
            page.wait_for_timeout(600)
            cesta = urllib.parse.urlsplit(page.url).path

            # 1) hviezdička len pri linkách: priečinky ani lišta Aktuálne ju nemajú
            if page.locator("#main .card-folder .star, #main .card-root .star, #aktualneWrap .star").count():
                raise Zlyhanie(f"{cesta}: hviezdička pri priečinku alebo v lište Aktuálne")
            # 2) zóna: počítač ≥ 40×20 px, pod ikonkou, mimo textu, mimo odkazu <a>
            zony = page.evaluate(self.OBL_ZONA_JS)
            zle = [z for z in zony if z.get("chyba") or z["w"] < 40 or z["h"] < 20 or not z["podIkonkou"]
                   or not z["mimoTextu"] or not z["trafi"] or z["vOdkaze"]]
            if not zony or zle:
                self.snimka(page, "r-obl-zona-chyba")
                raise Zlyhanie(f"{cesta}: zóna hviezdičky (počítač) nesedí: {zle or 'žiadna karta s ★'}")
            popis.append(f"zóna počítač {min(z['w'] for z in zony)}×{min(z['h'] for z in zony)} px")

            # 3) pridať / odobrať hviezdičkou; klik NEotvorí web (žiadna nová karta, adresa ostáva)
            hv = page.locator("#main .card-link > .star")
            prva = hv.nth(0)
            prva.click()
            page.wait_for_timeout(300)
            if prva.get_attribute("aria-pressed") != "true" or prva.inner_text().strip() != "★":
                raise Zlyhanie(f"{cesta}: po kliku na ☆ sa linka neoznačila (aria-pressed/★)")
            if len(ctx.pages) != 1 or urllib.parse.urlsplit(page.url).path != cesta:
                raise Zlyhanie(f"{cesta}: klik na hviezdičku otvoril web alebo zmenil adresu")
            if self.obl_pocet_hlavicka(page) != 1:
                raise Zlyhanie(f"{cesta}: po pridaní 1 linky ukazuje hlavička {self.obl_pocet_hlavicka(page)}")
            prva.click()
            page.wait_for_timeout(300)
            if prva.get_attribute("aria-pressed") != "false" or self.obl_pocet_hlavicka(page) != 0:
                raise Zlyhanie(f"{cesta}: odobratie hviezdičkou nefunguje (hlavička {self.obl_pocet_hlavicka(page)}, má byť 0)")
            n = min(12, hv.count())
            if n < 11:
                raise Zlyhanie(f"{cesta}: len {n} kariet s hviezdičkou (treba aspoň 11)")
            for i in range(n):
                hv.nth(i).click()
            page.wait_for_timeout(300)
            if self.obl_pocet_hlavicka(page) != n or len(self.obl_zoznam(page) or []) != n:
                raise Zlyhanie(f"{cesta}: po pridaní {n} liniek hlavička {self.obl_pocet_hlavicka(page)}, "
                               f"úložisko {self.obl_zoznam(page)}")
            if len(ctx.pages) != 1:
                raise Zlyhanie(f"{cesta}: klik na hviezdičku otvoril novú kartu")

            # 4) uloženie po F5 (+ linka, ktorá v dátach nie je, sa pri celých dátach ticho vyradí)
            page.evaluate(f"() => {{ const a = JSON.parse(localStorage.getItem('{self.OBL_KLUC}'));"
                          f" a.push({{id: 'test_neexistuje', t: 1}}); localStorage.setItem('{self.OBL_KLUC}', JSON.stringify(a)); }}")
            page.reload(wait_until="load")
            self.cakaj_na_appku(page)
            page.wait_for_selector("#main .card-link .star.on", state="visible")
            page.wait_for_function(self.OBL_CELE_DATA, timeout=30_000)
            page.wait_for_timeout(600)
            on = page.locator("#main .card-link > .star.on").count()
            zoz = self.obl_zoznam(page) or []
            if on != n or self.obl_pocet_hlavicka(page) != n:
                raise Zlyhanie(f"{cesta}: po F5 je označených {on} kariet, hlavička {self.obl_pocet_hlavicka(page)} (čakal som {n})")
            if "test_neexistuje" in zoz or len(zoz) != n:
                raise Zlyhanie(f"neexistujúca linka sa po načítaní celých dát z obľúbených nevyradila: {zoz}")

            # 5) zmena v inej karte (udalosť storage) sa prejaví
            p2 = self.stranka(ctx)
            p2.goto(url, wait_until="load")
            p2.wait_for_selector("#main .card-link > .star.on", state="visible")
            p2.locator("#main .card-link > .star.on").first.click()
            page.wait_for_timeout(800)
            if self.obl_pocet_hlavicka(page) != n - 1:
                raise Zlyhanie(f"odobratie v inej karte sa neprejavilo (hlavička {self.obl_pocet_hlavicka(page)}, čakal som {n - 1})")
            p2.locator("#main .card-link > .star:not(.on)").first.click()
            page.wait_for_timeout(800)
            self.over_chyby(p2, "obľúbené (druhá karta)")
            p2.close()
            if self.obl_pocet_hlavicka(page) != n:
                raise Zlyhanie("pridanie v inej karte sa neprejavilo")

            # 6) panel v hlavičke: najviac 10 riadkov + „Zobraziť všetky (N) ›“; Escape a klik mimo zatvoria
            page.click("#hFav")
            page.wait_for_selector("#favPanel .fp-row", state="visible")
            riadky = page.locator("#favPanel .fp-row").count()
            nadpis = page.locator("#fpTitle").inner_text()
            vsetky = page.locator("#favPanel .fp-all")
            if riadky != 10 or f"({n})" not in nadpis or vsetky.count() != 1 or f"({n})" not in vsetky.inner_text():
                raise Zlyhanie(f"panel: {riadky} riadkov (má byť 10), nadpis „{nadpis}“, "
                               f"odkaz „Zobraziť všetky“ {'chýba' if not vsetky.count() else vsetky.inner_text()}")
            if page.locator("#favPanel .fp-row a[target=_blank][rel~=noopener]").count() != 10:
                raise Zlyhanie("riadky panela neotvárajú web v novej karte (target/rel ako karta)")
            self.snimka(page, "r-obl-panel")
            # Zadanie 39a2: klik na hviezdičku karty pri otvorenom paneli panel NEZATVORÍ —
            # odobratie aj pridanie ho hneď prekreslí, pridaná linka je v ňom na prvom mieste
            idx = page.evaluate("""() => { const p = document.getElementById('favPanel').getBoundingClientRect();
                const h = document.querySelector('header').getBoundingClientRect().bottom;
                const v = [...document.querySelectorAll('#main .card-link > .star.on')];
                return v.findIndex(s => { const r = s.getBoundingClientRect();
                    return r.top > h && r.bottom < innerHeight && (r.right < p.left || r.left > p.right || r.top > p.bottom); }); }""")
            if idx < 0:
                raise Zlyhanie("panel: nenašla sa karta s ★ mimo panela (na skúšku kliku pri otvorenom paneli)")
            hv_k = page.locator("#main .card-link > .star.on").nth(idx)
            fid = hv_k.get_attribute("data-fid")
            hv_k.click()
            page.wait_for_timeout(300)
            if not page.locator("#favPanel").is_visible() or f"({n - 1})" not in page.locator("#fpTitle").inner_text():
                raise Zlyhanie("panel: odobratie hviezdičkou na karte panel zatvorilo alebo neprekreslilo")
            page.locator(f'#main .card-link > .star[data-fid="{fid}"]').click()
            page.wait_for_timeout(300)
            prvy = page.locator("#favPanel .fp-row .star").first.get_attribute("data-fid") if page.locator("#favPanel").is_visible() else None
            if prvy != fid or f"({n})" not in page.locator("#fpTitle").inner_text():
                raise Zlyhanie(f"panel: po pridaní hviezdičkou na karte sa panel zatvoril alebo nová linka nie je prvá (prvý riadok {prvy}, čakal som {fid})")
            page.keyboard.press("Escape")
            page.wait_for_timeout(200)
            if page.locator("#favPanel").is_visible():
                raise Zlyhanie("panel sa nezatvoril klávesom Escape")
            page.click("#hFav")
            page.wait_for_selector("#favPanel .fp-row", state="visible")
            page.mouse.click(5, page.viewport_size["height"] - 5)
            page.wait_for_timeout(200)
            if page.locator("#favPanel").is_visible():
                raise Zlyhanie("panel sa nezatvoril klikom mimo")
            page.click("#hFav")
            page.wait_for_selector("#favPanel .fp-all", state="visible")
            page.click("#favPanel .fp-all")

            # 7) zobrazenie všetkých: ?oblubene / ?favorites, noindex, odobratie, Späť
            page.wait_for_selector("#main .card-link > .star.on", state="visible")
            q = urllib.parse.urlsplit(page.url).query
            if q not in ("oblubene", "favorites"):
                raise Zlyhanie(f"„Zobraziť všetky“ neotvorilo /?oblubene (adresa {page.url})")
            karty = page.locator("#main .card-link").count()
            if karty != n or page.locator("#main .card-link > .star.on").count() != n:
                raise Zlyhanie(f"zobrazenie všetkých: {karty} kariet (čakal som {n})")
            if page.evaluate("(document.querySelector('meta[name=robots]') || {}).content") != "noindex":
                raise Zlyhanie("zobrazenie všetkých nemá meta robots noindex")
            if not page.locator("#breadcrumb h1").is_visible():
                raise Zlyhanie("zobrazenie všetkých nemá nadpis H1 v drobčekoch")
            self.snimka(page, "r-obl-vsetky")
            page.locator("#main .card-link > .star.on").first.click()
            page.wait_for_timeout(300)
            if page.locator("#main .card-link").count() != n - 1 or self.obl_pocet_hlavicka(page) != n - 1:
                raise Zlyhanie("odobratie v zobrazení všetkých neubralo kartu ani počet v hlavičke")
            # Zadanie 39a3: „✕ Zavrieť obľúbené“ vráti na stránku, z ktorej sa obľúbené otvorili
            if not page.locator("#fvBar #fvClose").is_visible():
                raise Zlyhanie("zobrazenie všetkých nemá tlačidlo „Zavrieť obľúbené“")
            page.click("#fvClose")
            page.wait_for_selector("#main .card-link > .star", state="visible")
            page.wait_for_timeout(400)
            if urllib.parse.urlsplit(page.url).path != cesta or page.evaluate("!!document.querySelector('meta[name=robots]#favRobots')"):
                raise Zlyhanie(f"„Zavrieť obľúbené“ nevrátilo stránku {cesta} (adresa {page.url})")
            page.go_forward()
            page.wait_for_selector("#main .card-link > .star.on", state="visible")
            if urllib.parse.urlsplit(page.url).query not in ("oblubene", "favorites"):
                raise Zlyhanie("Vpred nevrátil zobrazenie všetkých obľúbených")
            page.go_back()
            page.wait_for_selector("#main .card-link > .star", state="visible")

            # 7b) Zadanie 39a3: odobratie POSLEDNEJ linky pri otvorenom paneli — panel ostane s vetou
            idx = page.evaluate("""() => { const h = document.querySelector('header').getBoundingClientRect().bottom;
                return [...document.querySelectorAll('#main .card-link > .star')].findIndex(s => {
                    const r = s.getBoundingClientRect(); return r.top > h && r.bottom < innerHeight && r.right < innerWidth - 340; }); }  // vľavo od panela""")
            if idx < 0:
                page.evaluate("scrollTo(0, 0)")
                idx = 0
            posl = page.locator("#main .card-link > .star").nth(idx)
            page.evaluate(f"() => localStorage.setItem('{self.OBL_KLUC}', JSON.stringify([{{id: '{posl.get_attribute('data-fid')}', t: Date.now()}}]))")
            page.evaluate("() => { FAV = favRead(); favRefresh(); }")   # rovnako ako po zmene v inej karte
            page.click("#hFav")
            page.wait_for_selector("#favPanel .fp-row", state="visible")
            posl.click()
            page.wait_for_timeout(300)
            if not page.locator("#favPanel .fp-empty").is_visible() or "(0)" not in page.locator("#fpTitle").inner_text():
                self.snimka(page, "r-obl-panel-0-chyba")
                raise Zlyhanie("odobratie poslednej linky pri otvorenom paneli panel zatvorilo alebo neukázalo vetu")
            page.keyboard.press("Escape")

            # 8) admin režim: žiadne hviezdičky, lišta kariet admina ostáva, tlačidlo ★ skryté
            # (vstup bez hesla len v pamäti prehliadača testu — nič sa neukladá ani neodosiela)
            page.evaluate("() => enterAdmin()")
            page.wait_for_timeout(500)
            hv_admin = page.locator("#main .star:visible").count()
            bary = page.locator("#main .card-link .card-admin-bar").count()
            hfav_admin = page.locator("#hFav").is_visible()
            page.evaluate("() => logoutAdmin()")
            if hv_admin or hfav_admin or not bary:
                raise Zlyhanie(f"admin: viditeľných hviezdičiek {hv_admin}, tlačidlo ★ v hlavičke "
                               f"{'vidno' if hfav_admin else 'skryté'}, lišty kariet admina {bary}")
            popis.append(self.obl_dlhy(page, "počítač"))
            self.over_chyby(page, "obľúbené (počítač)")
            popis.append(f"{cesta}: ±★, {n} uložené po F5, panel 10 + „Zobraziť všetky ({n})“, "
                         "/?oblubene + Zavrieť/Späť/Vpred, ☆ 0 a panel pri 0, iná karta, admin bez ★")
        finally:
            ctx.close()

        # 9) mobil: zóna ≥ 44×28 px, ★ v zbalenej hlavičke vedľa lupy
        ctx = self.kontext(mobil=True)
        try:
            page = self.stranka(ctx)
            page.goto(url, wait_until="load")
            self.cakaj_na_appku(page)
            page.wait_for_selector("#main .card-link .star", state="visible")
            page.wait_for_function(self.OBL_CELE_DATA, timeout=30_000)
            page.wait_for_timeout(600)
            zony = page.evaluate(self.OBL_ZONA_JS)
            zle = [z for z in zony if z.get("chyba") or z["w"] < 44 or z["h"] < 28 or not z["podIkonkou"]
                   or not z["mimoTextu"] or not z["trafi"] or z["vOdkaze"]]
            if not zony or zle:
                self.snimka(page, "r-obl-zona-mobil-chyba")
                raise Zlyhanie(f"zóna hviezdičky (mobil) nesedí: {zle or 'žiadna karta s ★'}")
            if not page.locator("#hFav").is_visible() or page.locator("#hFavN").inner_text().strip() != "0":
                raise Zlyhanie("mobil: pri 0 obľúbených nie je v hlavičke tlačidlo „☆ 0“")
            page.locator("#main .card-link > .star").first.tap()
            page.wait_for_timeout(300)
            if len(ctx.pages) != 1 or self.obl_pocet_hlavicka(page) != 1:
                raise Zlyhanie("mobil: ťuknutie na hviezdičku nepridalo linku alebo otvorilo web")
            for y in range(0, 401, 50):
                page.evaluate("y => scrollTo(0, y)", y)
                page.wait_for_timeout(60)
            if page.evaluate("document.body.classList.contains('hdr-min')"):
                b = page.locator("#hFav").bounding_box()
                lupa = page.locator("#hLupa").bounding_box()
                if not page.locator("#hFav").is_visible() or not b or not lupa or b["x"] + b["width"] > lupa["x"] + 1:
                    self.snimka(page, "r-obl-mobil-hlavicka-chyba")
                    raise Zlyhanie("mobil: v zbalenej hlavičke chýba ★ pred lupou")
                self.snimka(page, "r-obl-mobil-hlavicka")
            popis.append(self.obl_dlhy(page, "mobil"))
            self.over_chyby(page, "obľúbené (mobil)")
            popis.append(f"mobil: zóna {min(z['w'] for z in zony)}×{min(z['h'] for z in zony)} px, ★ v zbalenej hlavičke")
        finally:
            ctx.close()
        return "ok", "; ".join(popis)

    # ------------------------------------------------ s) admin v lokálnej kópii (Zadanie 41)
    # Admin sa skúša na LOKÁLNEJ KÓPII webu: generator.py z repozitára vyrobí SK aj EN web
    # do dočasného priečinka, do kópie dát sa vloží testovacie heslo (skutočné heslo test
    # nepozná a nepotrebuje), kópiu obslúži malý server na 127.0.0.1. Dáta: data.json z
    # repozitára (sport-linky); kde v repozitári nie je (sportlinking), stiahnu sa úplné dáta
    # data-full.json z testovaného webu. Repozitár ani web sa nemenia. Tipsport aj GoatCounter
    # ostávajú blokované (BLOKOVANE). Skúšobný priečinok „Zadanie 41 test“ s linkami vzniká
    # LEN v pamäti prehliadača testu.
    ADMIN_HESLO = "test"
    T41 = "t41"              # id skúšobného priečinka
    GITHUB_UPLOAD = "https://github.com/sportlinks226/sport-linky/upload/main"

    class _TichyServer(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a, **k):   # bez výpisov do konzoly
            pass

    def lokalna_kopia(self):
        """Vráti {'sk': url, 'en': url} lokálnych kópií (vyrobí ich pri prvom volaní)."""
        if getattr(self, "_kopia", None):
            return self._kopia
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if not os.path.exists(os.path.join(repo, "generator.py")):
            raise Zlyhanie("v repozitári nie je generator.py — lokálna kópia sa nedá vyrobiť")
        tmp = tempfile.mkdtemp(prefix="sportlinky-admin-")
        self._kopia_dir = tmp
        self._servery = []
        src = os.path.join(tmp, "src")
        os.makedirs(src)
        for f in ("generator.py", "index.html", "aktualne.json", "favicon.ico", "apple-touch-icon.png", "og-image.png"):
            if os.path.exists(os.path.join(repo, f)):
                shutil.copy(os.path.join(repo, f), src)
        dj = os.path.join(repo, "data.json")
        if os.path.exists(dj):
            with open(dj, encoding="utf-8") as f:
                d = json.load(f)
            zdroj = "data.json z repozitára"
        else:
            kod, _, text = stiahni(self.base + "data-full.json", timeout=180)
            if kod != 200:
                raise Zlyhanie(f"úplné dáta data-full.json z webu sa nepodarilo stiahnuť (HTTP {kod})")
            d = json.loads(text)
            zdroj = "data-full.json z testovaného webu"
        if not isinstance(d, dict) or not isinstance(d.get("nodes"), list) or d.get("_lite"):
            raise Zlyhanie(f"dáta ({zdroj}) nie sú úplné (chýbajú nodes alebo sú odľahčené)")
        salt = "0123456789abcdef0123456789abcdef"
        d["pwKdf"] = {"salt": salt, "iter": 600_000,
                      "hash": hashlib.pbkdf2_hmac("sha256", self.ADMIN_HESLO.encode(), bytes.fromhex(salt), 600_000).hex()}
        with open(os.path.join(src, "data.json"), "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        self._kopia_verzia = int(d.get("version") or 0)
        urls = {}
        for lang in ("sk", "en"):
            out = os.path.join(tmp, lang)
            r = subprocess.run([sys.executable, "generator.py", "--out", out], cwd=src,
                               env={**os.environ, "SITE_LANG": lang, "BASE_URL": "", "OUT_PREFIX": ""},
                               capture_output=True, text=True, timeout=600)
            if r.returncode != 0 or not os.path.exists(os.path.join(out, "index.html")):
                raise Zlyhanie(f"generator.py ({lang}) zlyhal: {(r.stderr or r.stdout)[-400:]}")
            srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(self._TichyServer, directory=out))
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            self._servery.append(srv)
            urls[lang] = f"http://127.0.0.1:{srv.server_address[1]}/"
        self.info.append(f"**Lokálna kópia pre admin (s):** {zdroj}, v{self._kopia_verzia}, SK aj EN z generator.py")
        self._kopia = urls
        return urls

    def uprac_kopiu(self):
        for srv in getattr(self, "_servery", []) or []:
            try:
                srv.shutdown()
            except Exception:
                pass
        if getattr(self, "_kopia_dir", None):
            shutil.rmtree(self._kopia_dir, ignore_errors=True)

    def admin_prihlas(self, ctx, base, cesta=""):
        """Otvorí lokálnu kópiu s #admin, prihlási sa testovacím heslom. Stránka si zbiera
        otázky okna (confirm/alert) do page.dialogy; page.odpovede = pripravené odpovede
        (True = OK, False = Zrušiť) na nasledujúce otázky, inak OK."""
        page = self.stranka(ctx)
        page.dialogy = []
        page.odpovede = []
        host = urllib.parse.urlsplit(base).netloc

        def na_dialog(d):
            page.dialogy.append(d.message)
            odp = page.odpovede.pop(0) if page.odpovede else True
            (d.accept if odp else d.dismiss)()

        def na_odpoved(r):
            u = urllib.parse.urlsplit(r.url)
            # ikonky webov (/ikony/) v lokálnej kópii nie sú — sťahuje ich až build na GitHube
            if u.netloc == host and r.status >= 400 and not u.path.startswith("/ikony/"):
                page.chyby_suborov.append(f"{r.status} {u.path}")

        page.on("dialog", na_dialog)
        page.on("response", na_odpoved)
        page.goto(base + cesta + "#admin", wait_until="load")
        page.wait_for_selector("#pwScreen.open #pwIn", state="visible")
        page.fill("#pwIn", self.ADMIN_HESLO)
        page.press("#pwIn", "Enter")
        page.wait_for_function("() => (document.body.classList.contains('admin-mode'))", timeout=CAKANIE_MS)
        page.wait_for_timeout(400)
        return page

    # Skúšobný priečinok LEN v prehliadači: v prvej koreňovej sekcii, linky Hodonín › Chomutov ›
    # Ilava = presná slovenská abeceda (CH za H), ale NIE podľa kľúča bez diakritiky.
    # order_en: True = priečinok používa order_en (SK web), False = nepoužíva (EN web).
    T41_JS = """([id, sOrderEn]) => {
      DB.nodes = DB.nodes.filter(n => n.id !== id && n.parentId !== id);
      const sekcia = DB.nodes.find(n => n.parentId === null && n.type === 'folder' && n.id !== LIVE_ID);
      DB.nodes.push({id, parentId: sekcia.id, type:'folder', name:'Zadanie 41 test', name_en:'Task 41 test',
                     slug:'zadanie-41-test', slug_en:'task-41-test', icon:'', desc:'', order: 9999});
      ['Hodonín', 'Chomutov', 'Ilava'].forEach((m, i) => {
        const n = {id: id + '_' + i, parentId: id, type:'link', icon:'', name: m, name_en: m, desc:'popis', desc_en:'desc',
                   url: 'https://t41-' + i + '.example/', order: i};
        if(sOrderEn) n.order_en = i;
        DB.nodes.push(n);
      });
      save(); navigate(id); return sekcia.name;
    }"""
    T41_STAV = """id => getChildren(id).map(n => [n.name, n.order, (n.order_en === undefined ? null : n.order_en)])"""
    PREKRYTIE_JS = """() => { const zle = [];
      document.querySelectorAll('#main .card-link, #main .card-folder, #main .card-root').forEach(c => {
        const nm = c.querySelector('.cl-name, .cf-name, .c-name'); if(!nm) return;
        const n = nm.getBoundingClientRect(); if(!n.width) return;
        c.querySelectorAll('.ibtn').forEach(b => { const x = b.getBoundingClientRect();
          if(x.left < n.right && x.right > n.left && x.top < n.bottom && x.bottom > n.top) zle.push(nm.textContent.trim()); });
      });
      return {karty: document.querySelectorAll('#main .ibtn').length / 6, zle}; }"""

    def t41_pripravit(self, page, s_order_en):
        return page.evaluate(self.T41_JS, [self.T41, s_order_en])

    def t41_stav(self, page):
        return page.evaluate(self.T41_STAV, self.T41)

    def okno_otvor(self, page):
        page.click("#adminBar >> text=Pridať sem")
        page.wait_for_selector("#nodeMo.open", state="visible")
        page.wait_for_timeout(250)

    def okno_otvorene(self, page):
        return page.evaluate("() => (document.getElementById('nodeMo').classList.contains('open'))")

    def okno_vyplnit(self, page, url, nazov, desc_en="desc", nazov_en="", viac=None):
        page.fill("#nUrl", url)
        page.press("#nUrl", "Tab")       # onchange: úprava adresy + návrh názvu
        page.wait_for_timeout(100)
        if nazov is not None:
            page.fill("#nName", nazov)
        page.fill("#nNameEn", nazov_en)
        page.fill("#nDescEn", desc_en)
        if viac:
            if not page.evaluate("() => (document.getElementById('nViac').open)"):
                page.click("#nViac summary")
            for k, v in viac.items():
                if k in ("nTyp", "nZarad"):
                    page.select_option("#" + k, v)
                else:
                    page.fill("#" + k, v)

    def uloz(self, page, odpovede=(), dalsia=False):
        page.dialogy.clear()
        page.odpovede[:] = list(odpovede)
        page.click("#nSaveNext" if dalsia else "#nSave")
        page.wait_for_timeout(350)
        return list(page.dialogy)

    def admin_okno(self, pokus):
        kopia = self.lokalna_kopia()
        popis = []
        # ---------------- SK, počítač 1366×768
        ctx = self.kontext(okno=(1366, 768))
        try:
            page = self.admin_prihlas(ctx, kopia["sk"])
            sekcia = self.t41_pripravit(page, True)
            page.wait_for_timeout(300)
            # 3) prekrytie: lišta ⤒▲▼⤓✏️🗑 (6 tlačidiel) nesmie ležať na názve — v priečinku aj na domove
            pr = page.evaluate(self.PREKRYTIE_JS)
            if pr["karty"] < 3 or pr["zle"]:
                self.snimka(page, "s-prekrytie-chyba")
                raise Zlyhanie(f"1366×768: tlačidlá prekrývajú názov ({pr['zle'] or 'karty bez 6 tlačidiel'})")
            self.snimka(page, "s-karty-pc")
            page.evaluate("() => (navigate(null))")
            page.wait_for_timeout(300)
            pr2 = page.evaluate(self.PREKRYTIE_JS)
            if pr2["zle"]:
                raise Zlyhanie(f"1366×768 domov: tlačidlá prekrývajú názov ({pr2['zle']})")
            page.evaluate("id => navigate(id)", self.T41)
            page.wait_for_timeout(300)
            # okno: poradie polí, zbalené Viac, kurzor v URL, predvoľba abecedne
            self.okno_otvor(page)
            st = page.evaluate("""() => ({
              poradie: [...document.querySelectorAll('#nodeMo input[type=text], #nodeMo input[type=url]')].filter(i => i.offsetParent).map(i => i.id),
              viac: document.getElementById('nViac').open, fokus: document.activeElement.id,
              zarad: document.getElementById('nZarad').value, typ: document.getElementById('nTyp').value,
              ikona: document.getElementById('nIcon').placeholder, next: !!document.getElementById('nSaveNext').offsetParent})""")
            if st["poradie"][:5] != ["nUrl", "nName", "nDesc", "nNameEn", "nDescEn"] or st["viac"] or st["fokus"] != "nUrl":
                raise Zlyhanie(f"okno linky: poradie polí / Viac / kurzor nesedí: {st}")
            if st["zarad"] != "abc":
                raise Zlyhanie(f"abecedný priečinok (aj s CH) nemá predvoľbu Zaradiť = abecedne, má „{st['zarad']}“")
            if st["ikona"] or not st["next"]:
                raise Zlyhanie("pole ikonky má ukážku ⚽ alebo chýba „Uložiť a pridať ďalšiu“")
            self.snimka(page, "s-okno-zbalene-pc")
            # b) https:// + sledovacie prívesky + c) návrh názvu z adresy
            page.fill("#nUrl", "sportnet.sme.sk/?utm_source=t&utm_medium=x&z=1")
            page.press("#nUrl", "Tab")
            page.wait_for_timeout(150)
            url, nazov, pozn = page.input_value("#nUrl"), page.input_value("#nName"), page.text_content("#nUrlNote")
            if url != "https://sportnet.sme.sk/?z=1" or nazov != "Sportnet" or "https://" not in pozn or "utm_source" not in pozn:
                raise Zlyhanie(f"úprava adresy / návrh názvu nesedí: {url!r}, {nazov!r}, {pozn!r}")
            # e) bez EN popisu sa linka neuloží — červený text, kurzor v poli, žiadna otázka
            page.fill("#nDescEn", "")
            d = self.uloz(page)
            chyba = page.evaluate("""() => ({txt: document.getElementById('nDescEnErr').textContent,
              vidno: !!document.getElementById('nDescEnErr').offsetParent, fokus: document.activeElement.id})""")
            if d or not chyba["vidno"] or "anglický popis" not in chyba["txt"] or chyba["fokus"] != "nDescEn" or not self.okno_otvorene(page):
                raise Zlyhanie(f"chýbajúci Popis (EN) nezastavil uloženie: {d}, {chyba}")
            self.snimka(page, "s-okno-chyba-en-popis-pc")
            # f) slovenský názov bez EN názvu — otázka; Zrušiť = kurzor do Názov (EN)
            page.fill("#nName", "Šport správy test")
            page.fill("#nDescEn", "desc")
            d = self.uloz(page, odpovede=[False])
            if len(d) != 1 or "po slovensky" not in d[0] or page.evaluate("() => (document.activeElement.id)") != "nNameEn" or not self.okno_otvorene(page):
                raise Zlyhanie(f"otázka pri slovenskom názve nesedí: {d}")
            # bez slovenského slova (klub) sa nepýta; h) abecedne aj s CH: Humenné medzi Hodonín a Chomutov,
            # SK order aj order_en (priečinok ho používa — EN podľa anglického kľúča)
            page.fill("#nName", "Humenné")
            d = self.uloz(page)
            if d or self.okno_otvorene(page):
                raise Zlyhanie(f"uloženie bežnej linky: nečakaná otázka {d} / okno ostalo otvorené")
            stav = self.t41_stav(page)
            ocak = [["Hodonín", 0, 0], ["Humenné", 1, 2], ["Chomutov", 2, 1], ["Ilava", 3, 3]]
            if stav != ocak:
                raise Zlyhanie(f"abecedné zaradenie (CH za H) nesedí: {stav} ≠ {ocak}")
            popis.append("abecedne s CH (order aj order_en)")
            # d) duplicita s cestou: adresa linky z iného priečinka — Zrušiť nepridá, OK pridá
            dup = page.evaluate("""id => { const n = DB.nodes.find(x => x.type === 'link' && x.order >= 0 && x.parentId !== id && x.url);
              return {url: n.url, cesta: getPath(n.parentId).map(x => x.name).join(' › ')}; }""", self.T41)
            self.okno_otvor(page)
            self.okno_vyplnit(page, dup["url"], "Duplicita test", viac={"nZarad": "koniec"})
            d = self.uloz(page, odpovede=[False])
            if len(d) != 1 or "Táto adresa už je v:" not in d[0] or dup["cesta"] not in d[0] or not self.okno_otvorene(page):
                raise Zlyhanie(f"upozornenie na duplicitu nesedí: {d} (čakaná cesta {dup['cesta']})")
            self.snimka(page, "s-okno-duplicita-pc")
            d = self.uloz(page, odpovede=[True])
            stav = self.t41_stav(page)
            if self.okno_otvorene(page) or stav[-1][:2] != ["Duplicita test", 4]:
                raise Zlyhanie(f"„Pridať aj tak“ nepridalo linku na koniec: {stav}")
            popis.append("duplicita s cestou")
            # g) linka ligy cez „Uložiť a pridať ďalšiu“: order −1 (aj order_en), navrch, okno ostáva,
            # Typ späť na Bežná, Zaradiť sa pamätá
            self.okno_otvor(page)
            self.okno_vyplnit(page, "https://liga.example/tabulka", "Liga test", viac={"nTyp": "-1", "nZarad": "zaciatok"})
            d = self.uloz(page, dalsia=True)
            po = page.evaluate("""() => ({open: document.getElementById('nodeMo').classList.contains('open'),
              url: document.getElementById('nUrl').value, typ: document.getElementById('nTyp').value,
              zarad: document.getElementById('nZarad').value, pozn: document.getElementById('nUrlNote').textContent})""")
            stav = self.t41_stav(page)
            if d or stav[0] != ["Liga test", -1, -1] or not po["open"] or po["url"] or po["typ"] != "0" or po["zarad"] != "zaciatok" or "Uložené" not in po["pozn"]:
                raise Zlyhanie(f"linka ligy / Uložiť a pridať ďalšiu nesedí: {d}, {stav[:2]}, {po}")
            # druhá linka ligy → upozornenie; Zrušiť = neuloží
            self.okno_vyplnit(page, "https://liga2.example/", "Liga test 2", viac={"nTyp": "-1"})
            d = self.uloz(page, odpovede=[False])
            if len(d) != 1 or "už má linku ligy" not in d[0] or "Liga test" not in d[0] or len(self.t41_stav(page)) != 6:
                raise Zlyhanie(f"upozornenie na druhú linku ligy nesedí: {d}")
            page.odpovede[:] = [True]
            page.click("#nodeMo >> text=Zrušiť")   # rozpísané zmeny → otázka → OK
            page.wait_for_timeout(300)
            popis.append("linka ligy −1 navrch")
            # 2) skoky ⤒/⤓ na SK: mení order (0, 1, 2…), −1 ostáva navrchu, order_en sa nemení
            posledna = page.evaluate("id => { const c = getChildren(id).filter(n => n.order >= 0); return c[c.length - 1].id; }", self.T41)
            page.click(f"#main .card-link:has(button[onclick*=\"'{posledna}'\"]) .ibtn.kraj >> nth=0")
            page.wait_for_timeout(300)
            stav = self.t41_stav(page)
            if stav[0][1] != -1 or stav[1][:2] != ["Duplicita test", 0] or [x[1] for x in stav[1:]] != [0, 1, 2, 3, 4] or stav[2][2] != 0:   # order_en sa na SK nemení
                raise Zlyhanie(f"⤒ na SK nesedí: {stav}")
            page.click(f"#main .card-link:has(button[onclick*=\"'{posledna}'\"]) .ibtn.kraj >> nth=1")
            page.wait_for_timeout(300)
            stav = self.t41_stav(page)
            if stav[-1][:2] != ["Duplicita test", 4] or [x[1] for x in stav[1:]] != [0, 1, 2, 3, 4]:
                raise Zlyhanie(f"⤓ na SK nesedí: {stav}")
            page.odpovede[:] = [True]
            page.click("#main .card-link:nth-child(1) .ibtn.kraj >> nth=1")   # linka ligy sa nehýbe — hláška
            page.wait_for_timeout(200)
            if not page.dialogy or "navrchu" not in page.dialogy[-1] or self.t41_stav(page)[0][1] != -1:
                raise Zlyhanie("⤓ pri linke ligy nezastavil s hláškou")
            popis.append("⤒/⤓ SK (order)")
            # Facebook ↔ Instagram: IG adresa v poli Facebook → ponuka presunúť
            self.okno_otvor(page)
            self.okno_vyplnit(page, "https://klub.example/", "Klub FC", viac={"nFb": "https://www.instagram.com/klubfc/", "nZarad": "koniec"})
            d = self.uloz(page, odpovede=[True])
            n = page.evaluate("id => { const c = getChildren(id); const n = c[c.length - 1]; return {fb: n.fb || '', ig: n.ig || '', name: n.name}; }", self.T41)
            if len(d) != 1 or "Instagramu" not in d[0] or n != {"fb": "", "ig": "https://www.instagram.com/klubfc/", "name": "Klub FC"}:
                raise Zlyhanie(f"IG adresa v poli Facebook: {d}, {n}")
            # http:// ostáva, len upozornenie; úprava linky: Viac rozbalené (má IG)
            page.click(f"#main .card-link:has(button[onclick*=\"openEdit\"]) >> nth=-1 >> .ibtn:has-text('✏️')")
            page.wait_for_selector("#nodeMo.open", state="visible")
            page.wait_for_timeout(200)
            if not page.evaluate("() => (document.getElementById('nViac').open)") or page.evaluate("() => (!!document.getElementById('nSaveNext').offsetParent)"):
                raise Zlyhanie("úprava linky s IG: „Viac“ nie je rozbalené alebo je vidno „Uložiť a pridať ďalšiu“")
            self.snimka(page, "s-okno-uprava-viac-pc")
            page.fill("#nUrl", "http://stary.example/x")
            page.press("#nUrl", "Tab")
            page.wait_for_timeout(150)
            if page.input_value("#nUrl") != "http://stary.example/x" or "http://" not in page.text_content("#nUrlNote"):
                raise Zlyhanie("http:// sa mal nechať s upozornením")
            d = self.uloz(page)   # adresa sa zmenila, nie je duplicitná → bez otázky
            if d or self.okno_otvorene(page):
                raise Zlyhanie(f"úprava linky s http:// sa neuložila: {d}")
            # 4) sprievodca po Publikovať + značka verzie
            with page.expect_download() as dl:
                page.click("#adminBar >> text=Publikovať")
            if dl.value.suggested_filename != "data.json":
                raise Zlyhanie(f"Publikovať nestiahol data.json ({dl.value.suggested_filename})")
            page.wait_for_selector("#pubMo.open", state="visible")
            v = self._kopia_verzia
            sp = page.evaluate("""() => ({ver: document.getElementById('pubVer').textContent,
              href: document.getElementById('pubGh').getAttribute('href'), target: document.getElementById('pubGh').getAttribute('target'),
              kroky: document.querySelectorAll('#pubMo .pub-kroky li').length,
              badge: document.getElementById('webVerBadge').textContent, vidno: !document.getElementById('webVerBadge').hidden})""")
            if sp["ver"] != f"v{v + 1}" or sp["href"] != self.GITHUB_UPLOAD or sp["target"] != "_blank" or sp["kroky"] != 3:
                raise Zlyhanie(f"sprievodca po Publikovať nesedí: {sp}")
            if not sp["vidno"] or sp["badge"] != f"⚠️ v{v + 1} ešte nie je na webe (web má v{v})":
                raise Zlyhanie(f"značka verzie v admin lište nesedí: {sp}")
            self.snimka(page, "s-sprievodca-publikovat-pc")
            page.route("**/version.txt*", lambda r: r.fulfill(status=200, content_type="text/plain", body=str(v + 1)))
            page.evaluate("() => (sledujWebVer())")
            page.wait_for_function("() => (document.getElementById('webVerBadge').hidden)", timeout=CAKANIE_MS)
            page.click("#pubMo >> text=Zavrieť")
            popis.append("sprievodca + značka verzie")
            self.over_chyby(page, "admin SK (lokálna kópia)")
        finally:
            ctx.close()
        # ---------------- SK, mobil: 5 polí + tlačidlá bez „Viac“, ⤒⤓ v jednom riadku
        ctx = self.kontext(mobil=True)
        try:
            page = self.admin_prihlas(ctx, kopia["sk"])
            self.t41_pripravit(page, True)
            page.wait_for_timeout(300)
            m = page.evaluate("""() => { const c = document.querySelector('#main .card-link'); const b = c.querySelector('.card-admin-bar');
              const r = b.getBoundingClientRect(); const t = [...b.querySelectorAll('.ibtn')].map(x => x.getBoundingClientRect());
              return {n: t.length, vyska: r.height, riadky: new Set(t.map(x => Math.round(x.top))).size, min: Math.min(...t.map(x => Math.min(x.width, x.height)))}; }""")
            if m["n"] != 6 or m["riadky"] != 1 or m["min"] < 38:
                raise Zlyhanie(f"mobil: lišta karty nemá 6 tlačidiel v jednom riadku ≥ 38 px: {m}")
            self.snimka(page, "s-karty-mobil")
            self.okno_otvor(page)
            ok = page.evaluate("""() => { const v = id => { const r = document.getElementById(id).getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight; };
              return {polia: ['nUrl','nName','nDesc','nNameEn','nDescEn'].every(v), save: v('nSave'), next: v('nSaveNext'), viac: document.getElementById('nViac').open}; }""")
            if not ok["polia"] or not ok["save"] or not ok["next"] or ok["viac"]:
                self.snimka(page, "s-okno-mobil-chyba")
                raise Zlyhanie(f"mobil: bez otvorenia „Viac“ nevidno 5 polí + tlačidlá: {ok}")
            self.snimka(page, "s-okno-zbalene-mobil")
            page.click("#nViac summary")
            page.wait_for_timeout(200)
            self.snimka(page, "s-okno-viac-mobil")
            page.click("#nodeMo >> text=Zrušiť")
            self.over_chyby(page, "admin SK mobil (lokálna kópia)")
            popis.append("mobil: 5 polí + ⤒⤓ v riadku")
        finally:
            ctx.close()
        # ---------------- EN: ⤒⤓ menia order_en (order nie), nová linka dostane SK order aj order_en
        ctx = self.kontext(okno=(1366, 768))
        try:
            page = self.admin_prihlas(ctx, kopia["en"])
            self.t41_pripravit(page, False)
            page.wait_for_timeout(300)
            posledna = page.evaluate("id => { const c = getChildren(id); return c[c.length - 1].id; }", self.T41)
            page.click(f"#main .card-link:has(button[onclick*=\"'{posledna}'\"]) .ibtn.kraj >> nth=0")
            page.wait_for_timeout(300)
            stav = self.t41_stav(page)
            if stav != [["Ilava", 2, 0], ["Hodonín", 0, 1], ["Chomutov", 1, 2]]:
                raise Zlyhanie(f"⤒ na EN nesedí (má meniť len order_en): {stav}")
            page.click(f"#main .card-link:has(button[onclick*=\"'{posledna}'\"]) .ibtn.kraj >> nth=1")
            page.wait_for_timeout(300)
            stav = self.t41_stav(page)
            if stav != [["Hodonín", 0, 0], ["Chomutov", 1, 1], ["Ilava", 2, 2]]:
                raise Zlyhanie(f"⤓ na EN nesedí: {stav}")
            popis.append("⤒/⤓ EN (order_en)")
            # nová linka na EN webe, abecedne: SK order podľa slovenskej abecedy (Hodonín › Hrabušice › Chomutov › Ilava),
            # order_en podľa anglického kľúča v EN poradí (Hodonín › Chomutov › Hrabušice › Ilava)
            self.okno_otvor(page)
            if page.evaluate("() => (document.getElementById('nZarad').value)") != "abc":
                raise Zlyhanie("EN: abecedný priečinok nemá predvoľbu abecedne")
            self.okno_vyplnit(page, "https://hrabusice.example/", "Hrabušice", nazov_en="Hrabusice")
            d = self.uloz(page)
            stav = self.t41_stav(page)
            ocak = [["Hodonín", 0, 0], ["Chomutov", 2, 1], ["Hrabušice", 1, 2], ["Ilava", 3, 3]]
            if d or stav != ocak:
                raise Zlyhanie(f"EN: nová linka nedostala SK order aj order_en podľa voľby: {stav} ≠ {ocak} ({d})")
            # linka ligy na EN: order −1 aj order_en −1
            self.okno_otvor(page)
            self.okno_vyplnit(page, "https://liga-en.example/", "League test", viac={"nTyp": "-1"})
            d = self.uloz(page)
            stav = self.t41_stav(page)
            if d or stav[0] != ["League test", -1, -1]:
                raise Zlyhanie(f"EN: linka ligy nemá order aj order_en −1: {stav[:2]}")
            # sprievodca aj na EN webe vedie do sport-linky
            with page.expect_download() as dl:
                page.click("#adminBar >> text=Publikovať")
            page.wait_for_selector("#pubMo.open", state="visible")
            if page.evaluate("() => (document.getElementById('pubGh').getAttribute('href'))") != self.GITHUB_UPLOAD:
                raise Zlyhanie("EN: sprievodca nevedie na nahrávanie do sport-linky")
            page.click("#pubMo >> text=Zavrieť")
            self.over_chyby(page, "admin EN (lokálna kópia)")
            popis.append("EN: SK order + order_en, sprievodca → sport-linky")
        finally:
            ctx.close()
        return "ok", "; ".join(popis)

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
                self.kontrola("n) Prístupnosť: klávesnica a oblasti stránky", self.pristupnost)
                self.kontrola("o) Ikonky FB/IG: klikacia plocha ≥ 24×24 px", self.socs_plocha)
                self.kontrola("p) Mobil: hlavička sa pri posune zbalí a hore rozbalí", self.hlavicka_mobil)
                self.kontrola("q) Stĺpce: pás pod hlavičkou (prepnutie, príchod, Späť/Vpred)", self.stlpce_posun)
                self.kontrola("r) Obľúbené ★ (hviezdička, hlavička, panel, ?oblubene, admin)", self.oblubene)
                self.kontrola("s) Admin v lokálnej kópii: okno linky, ⤒⤓, prekrytie na PC, sprievodca", self.admin_okno)
            finally:
                self.browser.close()
                self.uprac_kopiu()

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
