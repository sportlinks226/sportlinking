#!/usr/bin/env python3
"""
TEST ESCAPOVANIA (XSS) GENERÁTORA — bez prehliadača, bez zmeny repozitára.
(sportlinky.sk aj sportlinking.com — ten istý súbor; previerka 3, bod 41)

Čo robí:
  1. Skopíruje generator.py, index.html, sitemap-lastmod.json a dáta (data.json,
     aktualne.json) do DOČASNÉHO priečinka. Originály v repozitári sa nemenia
     (generátor spustený v repozitári by prepísal sitemap-lastmod.json).
  2. Do kópie dát vloží ŠKODLIVÉ hodnoty (vzor: navrhy/previerka-3/skripty/F-01-xss-data.py):
     názvy a popisy so <script>, </script>, <img onerror>, <svg onload>, " onmouseover=,
     lomené úvodzovky, adresy javascript:, data:, //cudzi-web, slug s ../, id s ' a ",
     titulok webu s </title><script>, banner, promo blok a položku Aktuálnych.
  3. Vygeneruje web pre SK aj EN (python generator.py --out …) a v KAŽDOM vyrobenom
     .html súbore overí:
       a) žiadny <script> navyše — text zo zlých dát nikde neukončil značku <script>
          (skript s kódom „window.__XSS…" = únik), JSON bloky (pageBoot, ld+json)
          sa dajú prečítať;
       b) žiadny HTML atribút on…= (onerror, onload, onmouseover, onclick…) nevznikol
          zo zlých dát a žiadna značka <img>/<svg>/<b> zo zlých dát;
       c) žiadny odkaz/obrázok/okienko s adresou javascript:, data:, vbscript:
          alebo //cudzi-web — zlé adresy sú nahradené „#" (safe_url);
       d) škodlivé texty sú na stránke ako TEXT (escapované, nie zmazané) — H1,
          <title>, karty liniek, Aktuálne, promo blok;
       e) priečinok so slugom „../.." nevytvoril súbor mimo výstupného priečinka.

Dáta: data.json a aktualne.json z koreňa repozitára; keď tam nie sú (EN repozitár ich
necommituje), stiahnu sa zo SK webu (data-full.json, aktualne.json). Voliteľne
--data / --aktualne (cesta k súboru).

Výsledok: ✅ OK / ❌ chyba (beh skončí kódom 1). Zhrnutie sa zapíše aj do súboru
z premennej GITHUB_STEP_SUMMARY. Trvá asi pol minúty (2 buildy celého webu).

Spustenie (z koreňa repozitára):  python testy/test_escapovanie.py
Spúšťa ho .github/workflows/test-rychle.yml (pri PR / pushi, ktorý mení generator.py,
index.html alebo testy, a ručne).
"""

import argparse
import copy
import html
import html.parser
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

KOREN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SK_MASTER = "https://sportlinky.sk/"          # hlavná kópia dát (EN repozitár dáta nemá)
UA = "sportlinky-test-escapovania"
MAX_VYPIS = 20

# Značka v škodlivých textoch — podľa nej sa na stránke hľadá, či text ostal ako TEXT.
ZN = "XSSPOKUS"
EV = f'<img src=x onerror=window.__XSS=1>{ZN}'          # obrázok s onerror
SC = f'</script><script>window.__XSS2=1</script>{ZN}'  # ukončenie <script> + nový skript
NEBEZPECNE_ADRESY = re.compile(r"^\s*(javascript|data|vbscript)\s*:|^\s*//|^\s*\\\\", re.I)
URL_ATRIBUTY = ("href", "src", "action", "formaction", "poster", "background", "xlink:href")


# ---------------------------------------------------------------- škodlivé dáta
def otrav(d, a):
    """Do KÓPIE dát (d = data.json, a = aktualne.json) vloží škodlivé hodnoty.
    Vráti popis vložených uzlov (na kontrolu d)."""
    nodes = d.get("nodes") or []
    # koreňový priečinok viditeľný v OBOCH jazykoch (bez enOnly / en:false)
    root = next(n for n in nodes if n.get("parentId") is None and n.get("type") == "folder"
                and not n.get("enOnly") and n.get("en") is not False and not n.get("noTileSk"))
    fx = {"id": "xss'f\"<>", "parentId": root["id"], "type": "folder", "order": -100,
          "name": EV + " Pokus", "name_en": EV + " Test",
          "desc": "popis " + SC, "desc_en": "d " + SC,
          "icon": '"onmouseover="alert(1)', "slug": "../..?a=1&b=<x>", "slug_en": "../?q"}
    linky = [
        {"id": "xssl1", "parentId": fx["id"], "type": "link", "order": 0,
         "name": EV + " javascript", "desc": 'x" onmouseover="window.__XSS3=1',
         "url": "javascript:window.__XSS4=1", "icon": "🔗",
         "fb": "javascript:window.__XSS5=1", "ig": "data:text/html,<script>window.__XSS6=1</script>"},
        {"id": "xss'l2", "parentId": fx["id"], "type": "link", "order": 1,
         "name": "data linka " + SC, "desc": "</script><img src=x onerror=window.__XSS7=1>",
         "url": "data:text/html,<script>parent.__XSS8=1</script>",
         "icon": "<svg onload=window.__XSS9=1>", "tag": "<b onclick=window.__XSS19=1>"},
        {"id": "xssl3", "parentId": fx["id"], "type": "link", "order": 2,
         "name": f"lomené \\\" úvodzovky \\' {ZN}", "desc": "\\\"><img src=x onerror=window.__XSS20=1>",
         "url": " JaVaScRiPt:window.__XSS21=1", "icon": "⚽"},
        {"id": "xssl4", "parentId": fx["id"], "type": "link", "order": 3,
         "name": f"cudzí web {ZN}", "url": "//zly-web.invalid/x", "icon": "⚽"},
        {"id": "xssl5", "parentId": fx["id"], "type": "link", "order": 4,
         "name": f"dobrá adresa so znakmi {ZN}", "url": "https://example.com/?a=1&b=<x>\"'", "icon": "⚽"},
        # škodlivá linka priamo v koreňovom priečinku (je v balíku BOOT na každej stránke)
        {"id": "xssl6", "parentId": root["id"], "type": "link", "order": -100,
         "name": EV + " v koreni", "name_en": EV + " in root", "desc": SC,
         "url": "https://example.com/?a=1&b=<x>\"'"},
    ]
    d["nodes"] = [fx] + linky + nodes
    d["title"] = f"Športové Linky</title><script>window.__XSS10=1</script>{ZN}"
    d["title_en"] = f"Sportlinking</title><script>window.__XSS10=1</script>{ZN}"
    d["subtitle"] = f"<img src=x onerror=window.__XSS11=1>{ZN}"
    d["subtitle_en"] = d["subtitle"]
    bannery = [b for b in (d.get("banners") or []) if isinstance(b, dict)]
    for jaz in ("sk", "en"):
        for slot in (1, 2):
            bannery.insert(0, {"id": f"bxss'{jaz}{slot}", "name": "xss", "lang": jaz, "slot": slot,
                               "imageUrl": "javascript:alert(1)", "linkUrl": "javascript:window.__XSS12=1",
                               "alt": f"\"><img src=x onerror=window.__XSS13=1>{ZN}", "active": True,
                               "weight": 10})
    d["banners"] = bannery
    d["bannerSettings"] = {"rotate": False, "interval": 30, "activeId": "bxss'sk1"}
    d["promos"] = [{"id": "pxss", "title": EV, "text": SC, "btnText": f"<b>x</b>{ZN}",
                    "btnUrl": "javascript:window.__XSS15=1", "active": True, "weight": 10,
                    "sectionId": fx["id"]}] + [p for p in (d.get("promos") or []) if isinstance(p, dict)]
    a.setdefault("items", [])
    a["items"].insert(0, {"id": "axss'", "order": -1, "sport": "tenis",
                          "icon": "<svg onload=window.__XSS16=1>", "name": EV + " Aktuálne",
                          "name_en": EV + " Live", "url": "javascript:window.__XSS17=1",
                          "desc": f"\"><img src=x onerror=window.__XSS18=1>{ZN}",
                          "desc_en": f"\"><img src=x onerror=window.__XSS18=1>{ZN}",
                          "startsAt": "", "endsAt": "", "disabled": False,
                          "addedAt": int(time.time() * 1000)})
    return fx, linky


# ---------------------------------------------------------------- čítanie HTML
class Rozbor(html.parser.HTMLParser):
    """Prejde HTML ako prehliadač (bez JavaScriptu): značky, atribúty, obsah <script>."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.znacky = []        # (značka, {atribúty})
        self.skripty = []       # (atribúty, text)
        self._skript = None
        self.texty = {}         # značka → text (title, h1)
        self._text_v = None

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        self.znacky.append((tag.lower(), a))
        if tag.lower() == "script":
            self._skript = (a, [])
        if tag.lower() in ("title", "h1"):
            self._text_v = tag.lower()
            self.texty.setdefault(self._text_v, "")

    def handle_endtag(self, tag):
        if tag.lower() == "script" and self._skript:
            self.skripty.append((self._skript[0], "".join(self._skript[1])))
            self._skript = None
        if tag.lower() == self._text_v:
            self._text_v = None

    def handle_data(self, data):
        if self._skript is not None:
            self._skript[1].append(data)
        elif self._text_v:
            self.texty[self._text_v] += data


def skontroluj_html(cesta, text):
    """Kontroly a)–c) pre jeden súbor. Vráti zoznam chýb."""
    chyby = []
    r = Rozbor()
    r.feed(text)
    r.close()
    for a, obsah in r.skripty:
        typ = a.get("type", "").lower()
        if re.match(r"\s*(window|parent)\.__XSS", obsah):
            chyby.append(f"{cesta}: a) únik zo <script> — vznikol skript zo zlých dát: {obsah[:80]!r}")
        elif "__XSS" in obsah or ZN in obsah:
            if typ in ("application/json", "application/ld+json"):
                try:
                    json.loads(obsah)
                except ValueError as e:
                    chyby.append(f"{cesta}: a) JSON v <script type={typ}> sa nedá prečítať ({e}) — "
                                 "text zo zlých dát ho pokazil")
                if re.search(r"</script", obsah, re.I):
                    chyby.append(f"{cesta}: a) v <script type={typ}> je surové </script")
            elif re.search(r"</script|<!--", obsah, re.I):
                # dáta v kóde (napr. balík BOOT) musia mať „</" zakódované ako „<\/"
                i = re.search(r"</script|<!--", obsah, re.I).start()
                chyby.append(f"{cesta}: a) v spustiteľnom <script> ({typ or 'JS'}) so zlými dátami "
                             f"je surové {obsah[i:i + 9]!r}: {obsah[max(i - 50, 0):i + 30]!r}")
    for tag, a in r.znacky:
        for k, v in a.items():
            if k.startswith("on") and ("XSS" in v or "alert(" in v):
                chyby.append(f"{cesta}: b) <{tag} {k}=…> zo zlých dát: {v[:80]!r}")
            if k.startswith("on") and tag in ("img", "svg", "b") and "XSS" in "".join(a.values()):
                chyby.append(f"{cesta}: b) <{tag}> s atribútom {k} zo zlých dát")
            if k in URL_ATRIBUTY and NEBEZPECNE_ADRESY.search(v):
                if not (tag == "img" and v.startswith("data:image/")):   # vložený obrázok je OK
                    chyby.append(f"{cesta}: c) <{tag} {k}=\"{v[:60]}\"> — nebezpečná adresa (čakám #)")
        if tag in ("img", "svg", "b") and any("XSS" in k for k in a):
            chyby.append(f"{cesta}: b) značka <{tag}> zo zlých dát")
    return chyby, r


def id_stranky(r):
    """Id priečinka, z ktorého generátor stránku vyrobil (mini-balík pageBoot, pole full)."""
    for a, obsah in r.skripty:
        if a.get("id") == "pageBoot":
            try:
                return (json.loads(obsah).get("full") or [None])[0]
            except (ValueError, AttributeError):
                return None
    return None


# ---------------------------------------------------------------- beh
def nacitaj_json(cesta, url):
    if cesta and os.path.exists(cesta):
        with open(cesta, encoding="utf-8") as f:
            return json.load(f), cesta
    req = urllib.request.Request(url + "?t=" + str(int(time.time())), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8")), url


def build(lang, data, akt, tmp):
    """Vygeneruje web z otrávených dát v dočasnom priečinku. Vráti cestu k webu."""
    pracovny = os.path.join(tmp, lang)
    os.makedirs(pracovny)
    for f in ("generator.py", "index.html", "sitemap-lastmod.json"):
        if os.path.exists(os.path.join(KOREN, f)):
            shutil.copy(os.path.join(KOREN, f), pracovny)
    with open(os.path.join(pracovny, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    with open(os.path.join(pracovny, "aktualne.json"), "w", encoding="utf-8") as f:
        json.dump(akt, f, ensure_ascii=False)
    site = os.path.join(pracovny, "site")
    env = {k: v for k, v in os.environ.items()
           if k not in ("OUT_PREFIX", "AKTUALNE_FILE", "GOAT_CODE", "ALT_BASE_URL")}
    env.update(SITE_LANG=lang, BASE_URL="https://xss-test.invalid", PYTHONDONTWRITEBYTECODE="1")
    t0 = time.time()
    p = subprocess.run([sys.executable, "generator.py", "--out", "site"], cwd=pracovny, env=env,
                       capture_output=True, text=True, timeout=600)
    if p.returncode != 0:
        raise RuntimeError(f"generátor ({lang}) skončil chybou {p.returncode}:\n"
                           + (p.stdout[-1500:] + p.stderr[-1500:]))
    return pracovny, site, time.time() - t0


def over_web(lang, pracovny, site, fx, linky):
    """Kontroly a)–e) pre jeden vygenerovaný web. Vráti (chyby, info)."""
    chyby, info = [], []
    # e) nič mimo výstupného priečinka (slug „../..")
    cakane = {"generator.py", "index.html", "sitemap-lastmod.json", "data.json", "aktualne.json",
              "site", "__pycache__"}
    navyse = sorted(set(os.listdir(pracovny)) - cakane)
    if navyse:
        chyby.append(f"e) generátor vytvoril mimo výstupného priečinka: {navyse}")
    if os.listdir(os.path.dirname(pracovny)) != [lang]:
        chyby.append(f"e) generátor zapisoval o úroveň vyššie: {os.listdir(os.path.dirname(pracovny))}")
    # a)–c) všetky .html
    suborov, pokus_strana, domov = 0, None, None
    for kor, _, subory in os.walk(site):
        for s in subory:
            if not s.endswith(".html"):
                continue
            cesta = os.path.join(kor, s)
            with open(cesta, encoding="utf-8") as f:
                text = f.read()
            suborov += 1
            rel = os.path.relpath(cesta, site)
            ch, r = skontroluj_html(rel, text)
            chyby += ch
            if id_stranky(r) == fx["id"]:
                pokus_strana = (rel, text, r)
            if rel == "index.html":
                domov = (text, r)
    info.append(f"{suborov} súborov .html")
    # d) škodlivé texty sú na stránke ako text
    if not domov:
        chyby.append("d) chýba domovská stránka index.html")
    if not pokus_strana:
        chyby.append("d) stránka škodlivého priečinka sa nevyrobila (alebo jej H1 nie je text so značkou)")
        return chyby, info
    rel, text, r = pokus_strana
    info.append(f"stránka škodlivého priečinka: /{os.path.dirname(rel)}/")
    if "<img src=x onerror=" not in r.texty.get("h1", ""):
        chyby.append(f"d) H1 nemá škodlivý názov ako text: {r.texty.get('h1')!r}")
    # názov webu z dát („…</title><script>…") je v titulku podstránky — ako text
    if "</title><script>" not in r.texty.get("title", "") or ZN not in r.texty.get("title", ""):
        chyby.append(f"d) <title> nemá názov webu zo zlých dát ako text: {r.texty.get('title')!r}")
    karty = [a for t, a in r.znacky if t == "a" and a.get("class") == "card" and a.get("target") == "_blank"]
    hrefy = [a.get("href") for a in karty]
    cakane_hrefy = ["#", "#", "#", "#", "https://example.com/?a=1&b=<x>\"'"]
    if hrefy != cakane_hrefy:
        chyby.append(f"c/d) karty liniek {hrefy} ≠ čakám {cakane_hrefy} (zlé adresy → #, dobrá ostane celá)")
    for ln in linky[:5]:
        meno = ln["name"]
        if html.escape(meno, quote=False) not in text and html.escape(meno) not in text:
            chyby.append(f"d) názov linky {ln['id']} nie je na stránke ako escapovaný text")
    promo = [a for t, a in r.znacky if t == "a" and "promo-btn" in a.get("class", "")]
    if promo:       # statický promo blok (SK) — tlačidlo s javascript: adresou → #
        if [a.get("href") for a in promo] != ["#"]:
            chyby.append(f"c) tlačidlo promo bloku {[a.get('href') for a in promo]} ≠ ['#']")
        info.append("promo blok: tlačidlo #")
    return chyby, info


def main():
    ap = argparse.ArgumentParser(description="Test escapovania (XSS) generátora.")
    ap.add_argument("--data", default=os.path.join(KOREN, "data.json"))
    ap.add_argument("--aktualne", default=os.path.join(KOREN, "aktualne.json"))
    ap.add_argument("--jazyky", default="sk,en")
    a = ap.parse_args()
    t0 = time.time()
    data0, zdroj_d = nacitaj_json(a.data, SK_MASTER + "data-full.json")
    akt0, zdroj_a = nacitaj_json(a.aktualne, SK_MASTER + "aktualne.json")
    if data0.get("_lite"):
        sys.exit("CHYBA: dáta sú odľahčené (_lite) — test potrebuje úplné dáta (data-full.json).")
    vysledky = []
    tmp = tempfile.mkdtemp(prefix="test-escapovanie-")
    try:
        for lang in a.jazyky.split(","):
            data, akt = copy.deepcopy(data0), copy.deepcopy(akt0)
            fx, linky = otrav(data, akt)
            jtmp = os.path.join(tmp, "beh-" + lang)
            os.makedirs(jtmp)
            try:
                pracovny, site, trv = build(lang, data, akt, jtmp)
                chyby, info = over_web(lang, pracovny, site, fx, linky)
                info.insert(0, f"build {trv:.1f} s")
            except Exception as e:
                chyby, info = [f"{type(e).__name__}: {e}"], []
            vysledky.append((lang, chyby, info))
            print(f"[{'fail' if chyby else 'ok'}] {lang.upper()}: " + "; ".join(info), flush=True)
            for c in chyby:
                print("   ❌ " + c, flush=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    zle = sum(1 for _, c, _ in vysledky if c)
    r = ["## Test escapovania (XSS) generátora", "",
         ("❌ **Generátor neescapuje zlé dáta správne**" if zle else
          "✅ **Výstup generátora je escapovaný** — zlé dáta nespustia kód a zlé adresy sú #"), "",
         f"Dáta: {zdroj_d}, {zdroj_a}; trvanie {time.time() - t0:.0f} s", "",
         "| | Web | Výsledok |", "|---|---|---|"]
    for lang, chyby, info in vysledky:
        r.append(f"| {'❌' if chyby else '✅'} | {lang.upper()} | {'; '.join(info).replace('|', '/')}"
                 + (f" — chýb: {len(chyby)}" if chyby else "") + " |")
    for lang, chyby, _ in vysledky:
        if chyby:
            r += ["", f"<details><summary>{lang.upper()}: chyby ({len(chyby)})</summary>", ""]
            r += [f"- {html.escape(c, quote=False)}" for c in chyby[:MAX_VYPIS]]
            r += ["", "</details>"]
    text = "\n".join(r) + "\n"
    print("\n" + text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(text)
    sys.exit(1 if zle else 0)


if __name__ == "__main__":
    main()
