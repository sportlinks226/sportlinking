#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEO generátor pre Športové Linky (sport-strom).

Číta data.json a vygeneruje:
  - statickú HTML stránku pre každý priečinok (napr. hokej/sutaze/index.html)
  - sitemap.xml a robots.txt
  - skopíruje index.html (aplikáciu) do výstupného priečinka
  - zapíše data.json (odľahčený pre návštevníkov, "_lite") a data-full.json
    (celé dáta pre admina) — viď lite_data()

Použitie:
  python generator.py                 # výstup do _site/
  python generator.py --out _site

BASE_URL (absolútna adresa webu pre sitemap/canonical) sa berie z premennej
prostredia BASE_URL — v GitHub Actions ju dodá configure-pages automaticky.

ANGLIČTINA (sportlinking.com):
  - jazyk sa prepína premennou prostredia SITE_LANG ("sk" | "en"), default "sk"
  - EN používa polia name_en/desc_en/slug_en s fallbackom na SK
  - uzly s "en": false sa na EN webe nezobrazia (aj s celým podstromom)
  - EN má modrý akcent (#4287e8), vlastný GoatCounter (GOAT_CODE) a bannery
    filtrované podľa poľa lang (bez lang = SK banner)
  - krajiny vnútri kontinentov sa v EN radia podľa anglickej abecedy

DYNAMICKÉ ČASTI (banner + Aktuálne) — každá vygenerovaná stránka obsahuje
malý skript, ktorý ich načíta z data.json pri otvorení stránky. Denná
aktualizácia Aktuálnych a bannerov teda NEVYŽADUJE prebudovanie webu.
Logika zrkadlí sport-strom.html vrátane cielenia bannerov na sekcie,
kampaní od–do a váh rotácie.

SEO (od 2.10.2026):
  - sitemap <lastmod> = dátum SKUTOČNEJ zmeny stránky. Pre každú stránku sa
    spočíta odtlačok obsahu (page_fingerprint) a porovná so stavovým súborom
    sitemap-lastmod.json v koreni repozitára; zmenený odtlačok → dnešný dátum,
    inak ostáva starý. Súbor po builde commitne GitHub Action (build.yml).
    Predtým mali všetky stránky lastmod = deň buildu a denný cron ich tak
    každé ráno hlásil Googlu ako zmenené — signál, ktorému Google neverí.
  - Aktuálne sa vkladajú do index.html už pri builde (inject_aktualne), aby
    ich Google videl v surovom HTML; appka ich po štarte prekreslí na to isté.
"""

import hashlib
import json
import os
import re
import time
import shutil
import sys
import unicodedata
from datetime import date, timedelta
from html import escape
from urllib.parse import unquote, urlsplit

# ------------------------------------------------------------
# KONFIGURÁCIA
# ------------------------------------------------------------
LANG = os.environ.get("SITE_LANG", "sk")   # "sk" alebo "en"
OUT_PREFIX = os.environ.get("OUT_PREFIX", "")
BASE_URL = os.environ.get("BASE_URL", "").rstrip("/")

# hreflang: adresa webu v DRUHOM jazyku (SK build ukazuje na EN web a naopak).
# Vlastnú adresu dodá BASE_URL (configure-pages); druhá je natvrdo tu,
# s možnosťou prepísania premennou prostredia ALT_BASE_URL.
ALT_LANG = "en" if LANG == "sk" else "sk"
_ALT_DEFAULTS = {"sk": "https://sportlinky.sk", "en": "https://sportlinking.com"}
ALT_BASE_URL = os.environ.get("ALT_BASE_URL", _ALT_DEFAULTS[ALT_LANG]).rstrip("/")

# Absolútna cesta ku koreňu webu (podľa nej appka vyrába pekné adresy).
# Slovenský web beží na https://sportlinky.sk a anglický na
# https://sportlinking.com (oba BEZ www, overené 22.10.2026), oba v koreni "/".
# Kód však funguje aj pre web v podpriečinku (napr. github.io/nazov-repa/,
# koreň "/nazov-repa/"), preto sa koreň berie z BASE_URL, ktorú dodá GitHub Actions.
_base_path = urlsplit(BASE_URL).path.strip("/") if BASE_URL else ""
_root_parts = [p for p in (_base_path, OUT_PREFIX.strip("/")) if p]
SITE_ABS_ROOT = "/" + ("/".join(_root_parts) + "/" if _root_parts else "")

UI = {
    "sk": {
        "home": "Domov",
        "folders": "Kategórie",
        "links": "Linky",
        "open_app": "Otvoriť v interaktívnej aplikácii",
        "meta_folder": "{name} — športové linky: {nfold} podkategórií, {nlink} liniek.",
        "footer": "Prehľadný rozcestník športových webov. Databáza liniek je chránená právom na ochranu databáz (smernica 96/9/ES); jej kopírovanie alebo systematické vyťažovanie bez súhlasu prevádzkovateľa je zakázané.",
        "aktualne": "Aktuálne",
    },
    "en": {
        "home": "Home",
        "folders": "Categories",
        "links": "Links",
        "open_app": "Open in the interactive app",
        "meta_folder": "{name} — sports links: {nfold} subcategories, {nlink} links.",
        "footer": "A clear directory of sports websites. The link database is protected by database rights (Directive 96/9/EC); copying or systematic extraction without the operator's consent is prohibited.",
        "aktualne": "Live this week",
    },
}
T = UI[LANG]

# akcentová farba: SK červená, EN modrá
ACCENT = "#e84242" if LANG == "sk" else "#4287e8"
ACCENT_HOVER = "#c73535" if LANG == "sk" else "#2f6bc4"
# kontrast podľa WCAG (bod 17 previerky): svetlejší akcent pre malý farebný
# text na tmavom pozadí a tmavší akcent pre pozadie pod bielym textom
ACCENT_TEXT = "#ef5a5a" if LANG == "sk" else "#5b9bf0"
ACCENT_STRONG = "#d63333" if LANG == "sk" else "#2a6fd6"

# priečinky, ktorých deti (krajiny) sa v EN verzii radia podľa anglickej abecedy
CONTINENTS = {"Európa", "Ázia", "Afrika", "Južná Amerika", "Severná Amerika",
              "Severná a Stredná Amerika", "Oceánia", "Ázia & Oceánia"}

# VÝNIMKY z abecedného radenia v EN — priečinky, ktoré sa síce volajú ako kontinent,
# ale ich obsah NIE SÚ krajiny (napr. Súťaže › Európa: poradie = úroveň súťaže).
# MUSÍ zostať zhodné s NO_EN_ALPHA v sport-strom.html.
NO_EN_ALPHA = {"f_bas_sut_eu", "f_bas_sut_oc", "f_bas_sut_na", "f_bas_sut_ja", "f_bas_sut_af", "f_bas_sut_az"}

# "Live This Week" — priečinok, ktorý existuje LEN na anglickom webe (enOnly:true)
# a nemá vlastné linky: napĺňa sa naživo z poľa "aktualne" (tie isté linky, aké
# sú v lište na domovskej stránke). Skončené udalosti sa pri builde vynechajú.
# MUSÍ zostať zhodné s LIVE_ID v sport-strom.html.
LIVE_ID = "f_ltw"

# og:locale (bod 23 previerky) — jazyk webu pre Facebook a pod.
OG_LOCALE = "en_US" if LANG == "en" else "sk_SK"

# GoatCounter kód (oddelené štatistiky pre SK a EN web)
GOAT = os.environ.get("GOAT_CODE", "sportlinky" if LANG == "sk" else "sportlinking")

# ------------------------------------------------------------
# POMOCNÉ FUNKCIE
# ------------------------------------------------------------

def slugify(name: str) -> str:
    """Musí sa správať ROVNAKO ako slugify() v sport-strom.html (hash routing)."""
    s = unicodedata.normalize("NFD", name or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def node_desc(node: dict) -> str:
    """Popis v aktuálnom jazyku s fallbackom na slovenčinu."""
    if LANG != "sk":
        v = (node.get("desc_" + LANG) or "").strip()
        if v:
            return v
    return (node.get("desc") or "").strip()


def node_name(node: dict, lang: str = None) -> str:
    """Názov v danom jazyku (default = jazyk buildu) s fallbackom na slovenčinu."""
    lang = lang or LANG
    if lang != "sk":
        v = (node.get("name_" + lang) or "").strip()
        if v:
            return v
    return (node.get("name") or "").strip()


def visible(node: dict, lang: str = None) -> bool:
    """en:false skryje uzol (aj s podstromom) na anglickom webe.
    enOnly:true je opak — uzol sa ukáže LEN na anglickom webe."""
    lang = lang or LANG
    if lang == "sk":
        return node.get("enOnly") is not True
    return node.get("en") is not False


def live_week_links(aktualne: list) -> list:
    """Z poľa "aktualne" vyrobí linky pre priečinok Live This Week.
    Sú to bežné uzly typu link, len nie sú uložené v data.json — vznikajú
    pri každom builde nanovo, takže sekcia je vždy taká čerstvá ako lišta."""
    today = date.today().isoformat()
    out = []
    for i, a in enumerate(aktualne):
        if a.get("endsAt") and today > a["endsAt"]:
            continue          # skončená udalosť sa na stránku nedostane
        out.append({
            "id": "akt_%d" % i,
            "type": "link",
            "parentId": LIVE_ID,
            "name": a.get("name", ""),
            "name_en": a.get("name_en") or a.get("name", ""),
            "url": a.get("url", ""),
            "icon": a.get("icon", "") or "",
            "order": i,
        })
    return out


def load_data(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------------------
# STROM
# ------------------------------------------------------------

def build_tree(nodes: list, lang: str = None):
    """Vráti (children, by_id): mapy pre rýchlu navigáciu stromom."""
    lang = lang or LANG
    children: dict = {}
    by_id = {}
    for n in nodes:
        by_id[n["id"]] = n
        if not visible(n, lang):
            continue          # en:false — uzol aj celý podstrom mimo EN webu
        children.setdefault(n.get("parentId"), []).append(n)
    for pid, lst in children.items():
        # order_en — voliteľné pole: na EN webe má prednosť pred order
        if lang == "en":
            lst.sort(key=lambda x: x.get("order_en", x.get("order", 0)))
        else:
            lst.sort(key=lambda x: x.get("order", 0))
        # EN: krajiny vnútri kontinentov podľa anglickej abecedy
        parent = by_id.get(pid)
        if (lang == "en" and parent is not None and pid not in NO_EN_ALPHA
                and parent.get("name") in CONTINENTS):
            lst.sort(key=lambda x: node_name(x, lang).lower())
    return children, by_id


def folder_paths(children: dict, lang: str = None):
    """Priradí každému priečinku URL cestu (zoznam slugov). Rieši duplicitné slugy.

    Prednosť má TRVALÝ slug uložený v dátach (pole "slug" — priraďuje ho
    aplikácia pri vytvorení priečinka / migrácii ensureSlugs). Fallback na
    slugify(názov) je len pre dáta, ktoré migráciou ešte neprešli.
    Algoritmus (poradie podľa order + dedupe) je IDENTICKÝ s ensureSlugs()
    v sport-strom.html — obe strany musia vyrobiť rovnaké adresy.
    """
    lang = lang or LANG
    paths = {}  # folder id -> [slug, slug, ...]

    def walk(parent_id, prefix):
        used = set()
        for n in children.get(parent_id, []):
            if n.get("type") != "folder":
                continue
            slug = slug_base(n, lang)
            base, i = slug, 2
            while slug in used:          # súrodenci s rovnakým slugom
                slug = f"{base}-{i}"
                i += 1
            used.add(slug)
            p = prefix + [slug]
            paths[n["id"]] = p
            walk(n["id"], p)

    walk(None, [])
    return paths


def slug_base(n: dict, lang: str = None) -> str:
    """Slug priečinka PRED riešením duplicít medzi súrodencami.
    ROVNAKÉ ako nodeSlugBase() v index.html."""
    lang = lang or LANG
    if lang == "en":
        return (n.get("slug_en")
                or slugify(node_name(n, lang))
                or "cat-" + slugify(n["id"]))
    return (n.get("slug")
            or slugify(n.get("name", ""))
            or "kat-" + slugify(n["id"]))


# SLUGY SÚRODENCOV S ROVNAKÝM NÁZVOM (bod 21 previerky, 2.11.2026): folder_paths()
# dá druhému „-2", tretiemu „-3"… Appka (nodeSlug v index.html) dostane tie isté
# výsledné slugy ako mapu id -> slug (len priečinky, ktorých slug sa líši od
# slug_base) — kľúč "_slugFix" v odľahčenom data.json, v BOOT a v mini-balíku.
# Appka tak nemusí opakovať poradie súrodencov (EN abeceda kontinentov sa v appke
# a generátore radí trochu inak) a adresy sú zaručene zhodné. Do data-full.json
# sa NEPÍŠE. Vypĺňa main().
SLUG_FIX = {}


def gen_meta(ids) -> dict:
    """Kľúče _titleNoSport a _slugFix obmedzené na dané id-čka (BOOT, mini-balík).
    ids=None = všetko (odľahčený data.json)."""
    if ids is None:
        return {"_titleNoSport": sorted(TITLE_NOSPORT), "_slugFix": dict(sorted(SLUG_FIX.items()))}
    ids = set(ids)
    return {"_titleNoSport": sorted(i for i in TITLE_NOSPORT if i in ids),
            "_slugFix": {k: v for k, v in sorted(SLUG_FIX.items()) if k in ids}}


def build_boot(data: dict, children: dict) -> dict:
    """ŠTARTOVACÍ BALÍK pre appku (od 2.10.2026, rýchlosť domovskej stránky).

    Appka (index.html) má riadok `let BOOT = null;` — main() doň vloží tento
    malý výrez dát (~28 kB), z ktorého sa domovská stránka a hlavné sekcie
    vykreslia OKAMŽITE, ešte pred stiahnutím celého data.json (~5,5 MB):
      - priečinky 1. a 2. úrovne (bez popisov) s predpočítanými počtami
        _cnt (liniek v podstrome) a _sub (podpriečinkov) — presne to, čo appka
        píše na karty, takže po príchode celých dát čísla nepreskočia;
      - Aktuálne, bannery, promá, názov webu;
      - _totalLinks = počet VŠETKÝCH liniek v dátach (appka počíta rovnako,
        bez ohľadu na jazyk).
    Strom `children` je už filtrovaný podľa jazyka (visible), rovnako ako
    getChildren() v appke."""
    link_count = {}

    def cnt(fid):
        c = 0
        for k in children.get(fid, []):
            c += 1 if k.get("type") == "link" else cnt(k["id"])
        link_count[fid] = c
        return c

    for top in children.get(None, []):
        if top.get("type") == "folder":
            cnt(top["id"])

    keep = ("id", "parentId", "type", "name", "name_en", "slug", "slug_en",
            "icon", "order", "order_en", "en", "enOnly")
    nodes = []

    def take(n, depth):
        if n.get("type") != "folder":
            return
        m = {k: n[k] for k in keep if k in n}
        m["_cnt"] = link_count.get(n["id"], 0)
        m["_sub"] = sum(1 for k in children.get(n["id"], []) if k.get("type") == "folder")
        nodes.append(m)
        if depth < 2:
            for k in children.get(n["id"], []):
                take(k, depth + 1)

    for top in children.get(None, []):
        take(top, 1)

    boot = {"version": data.get("version"), "nodes": nodes,
            "_totalLinks": sum(1 for n in data.get("nodes", []) if n.get("type") == "link")}
    for k in ("title", "subtitle", "title_en", "subtitle_en", "aktualne",
              "banners", "bannerSettings", "promos", "promoBanner"):
        if k in data:
            boot[k] = data[k]
    if LANG != "en":
        # SK appka anglické polia nepoužíva (bod 3 previerky)
        boot = strip_en(boot)
    boot.update(gen_meta(n["id"] for n in nodes))   # bod 21 + 23 (viď SLUG_FIX, TITLE_NOSPORT)
    return boot


def link_counts(children: dict) -> dict:
    """Počet liniek v podstrome každého priečinka (ako _cnt v build_boot)."""
    out = {}

    def cnt(fid):
        c = 0
        for k in children.get(fid, []):
            c += 1 if k.get("type") == "link" else cnt(k["id"])
        out[fid] = c
        return c

    for top in children.get(None, []):
        if top.get("type") == "folder":
            cnt(top["id"])
    return out


def _lite_node(n: dict) -> dict:
    """Uzol presne tak, ako ho má návštevník v data.json (viď lite_data)."""
    if LANG == "en":
        return {k: v for k, v in n.items() if not (k == "desc" and n.get("desc_en"))}
    return {k: v for k, v in n.items() if k not in EN_NODE_KEYS}


BOOT_KEEP = ("id", "parentId", "type", "name", "name_en", "slug", "slug_en",
             "icon", "order", "order_en", "en", "enOnly")


def build_page_boot(node, children, by_id, boot_ids, lcnt) -> str:
    """MINI-BALÍK PODSTRÁNKY (od 2.11.2026, bod 2 previerky).

    DOPLNOK k balíku BOOT z index.html (ten má priečinky 1. a 2. úrovne,
    Aktuálne, bannery, promá) — appka si ich po prevzatí spojí a podstránku
    vykreslí hneď, bez čakania na celý data.json:
      - reťazec predkov od koreňa po túto stránku (cesta z adresy sa rozlúšti celá),
      - táto stránka celá (aj s popisom — appka ho dáva do meta popisu),
      - VŠETKY jej deti: priečinky s _cnt/_sub, linky so všetkými poľami
        z data.json (po príchode celých dát sa nič nezmení ani nepreblikne).
    "full" = priečinky, ktorých deti sú v balíku kompletné (appka ich kreslí
    hneď, inde ukáže „Načítavam…“). Výsledok je JSON so znakmi < > & zakódovanými
    ako \\u003c \\u003e \\u0026 — bezpečný vnútri <script> (bod 14)."""
    def folder(n, full_node=False):
        m = _lite_node(n) if full_node else {k: n[k] for k in BOOT_KEEP if k in n}
        if LANG != "en":
            m = {k: v for k, v in m.items() if k not in EN_NODE_KEYS}
        m["_cnt"] = lcnt.get(n["id"], 0)
        m["_sub"] = sum(1 for k in children.get(n["id"], []) if k.get("type") == "folder")
        return m

    nodes = []
    chain = []
    a = node
    while a is not None:
        chain.append(a)
        a = by_id.get(a.get("parentId"))
    for anc in reversed(chain):
        if anc is node:
            nodes.append(folder(anc, True))      # vždy (popis), prepíše uzol z BOOT
        elif anc["id"] not in boot_ids:
            nodes.append(folder(anc))
    if node["id"] != LIVE_ID:   # Live This Week: linky si appka skladá z Aktuálnych
        for k in children.get(node["id"], []):
            if k["id"] in boot_ids:
                continue
            nodes.append(folder(k) if k.get("type") == "folder" else _lite_node(k))
    pb = {"version": DATA_VER, "nodes": nodes, "full": [node["id"]]}
    pb.update(gen_meta(n["id"] for n in nodes))     # bod 21 + 23 (viď SLUG_FIX, TITLE_NOSPORT)
    return (json.dumps(pb, ensure_ascii=False, separators=(",", ":"))
            .replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026"))


# ------------------------------------------------------------
# ODĽAHČENÉ DÁTA PRE NÁVŠTEVNÍKOV (od 26.10.2026, bod 3 a 13 previerky)
# ------------------------------------------------------------
# VEĽKOSŤ DÁT (zmerané 2.11.2026, verzia dát z repozitára): data.json v repozitári
# ~9,6 MB (s odsadením); na webe data-full.json ~8,0 MB (zbalený ~1,7 MB),
# odľahčený data.json SK ~5,5 MB / EN ~5,8 MB (zbalený ~1,2 MB); BOOT ~28 kB.
# Na web idú dva súbory:
#   data-full.json — celé dáta bez zmeny obsahu (len bez medzier). Sťahuje ho
#                    LEN admin po prihlásení, aby 🚀 Publikovať vyrobilo úplný
#                    data.json s poliami oboch jazykov.
#   data.json      — odľahčená kópia pre návštevníkov daného jazyka s príznakom
#                    "_lite": true (appka ju nedovolí publikovať ani uložiť).
# Uzly ani ich počet sa NEMENIA — počty liniek musia sedieť s BOOT a titulkom.
# Originál data.json v repozitári ostáva bez zmeny.
EN_NODE_KEYS = ("name_en", "desc_en", "slug_en", "order_en")
EN_ROOT_KEYS = ("title_en", "subtitle_en")


def strip_en(data: dict) -> dict:
    """Kópia dát bez anglických polí (pre SK web). Originál nemení."""
    d = {k: v for k, v in data.items() if k not in EN_ROOT_KEYS}
    d["nodes"] = [{k: v for k, v in n.items() if k not in EN_NODE_KEYS}
                  for n in data.get("nodes", [])]
    for key in ("aktualne", "banners", "promos"):
        if isinstance(data.get(key), list):
            d[key] = [({k: v for k, v in a.items() if k != "name_en"}
                       if isinstance(a, dict) else a) for a in data[key]]
    return d


def lite_data(data: dict) -> dict:
    """Odľahčená kópia data.json pre návštevníkov webu v jazyku LANG.

    Vždy bez passwordHash/password (pwKdf ostáva — overuje sa ním heslo).
    SK: bez *_en polí. EN: bez slovenského desc tam, kde je vyplnený desc_en
    (appka v EN berie nDesc = desc_en, inak desc). slug ostáva aj v EN
    (pracuje s ním ensureSlugs v appke)."""
    if LANG == "en":
        d = dict(data)
        d["nodes"] = [({k: v for k, v in n.items() if k != "desc"}
                       if n.get("desc_en") else n) for n in data.get("nodes", [])]
    else:
        d = strip_en(data)
    for k in ("passwordHash", "password"):
        d.pop(k, None)
    d["_lite"] = True
    # bod 21 + 23: výsledné slugy duplicít a priečinky s titulkom bez športu —
    # appka si ich pri načítaní odloží bokom a z dát ich zmaže (do dát admina
    # sa nikdy nedostanú; data-full.json ich nemá)
    d.update(gen_meta(None))
    return d


def write_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))


# ------------------------------------------------------------
# SITEMAP lastmod PODĽA SKUTOČNEJ ZMENY (od 2.10.2026)
# ------------------------------------------------------------
# Stavový súbor v koreni repozitára: { "hokej/kluby/usa/nhl/": {"h": odtlačok,
# "d": "2026-10-02"}, ... }. Kľúč = cesta stránky ("/" = domov). Zapisuje ho
# save_lastmod() po každom builde; na GitHube ho commitne Action (build.yml,
# krok „Ulož dátumy zmien pre sitemap"). Lokálny build bez gitu ho len prepíše.
LASTMOD_FILE = "sitemap-lastmod.json"


def _fp(rows) -> str:
    return hashlib.sha1(json.dumps(rows, ensure_ascii=False, separators=(",", ":"))
                        .encode("utf-8")).hexdigest()[:16]


def _row(n: dict) -> list:
    """To, čo sa z uzla na stránke (statickej aj v appke) naozaj ukáže — v jazyku buildu."""
    return [n.get("type") or "", node_name(n), node_desc(n), n.get("icon") or "",
            n.get("url") or "", n.get("fb") or "", n.get("ig") or ""]


def page_fingerprint(node: dict, children: dict) -> str:
    """Odtlačok stránky priečinka: vlastný názov/popis/ikona + PRIAME deti v poradí
    zobrazenia. Zmena hlbšie (vnútri podpriečinka) patrí stránke toho podpriečinka,
    takže nová linka v NHL zmení len /hokej/kluby/usa/nhl/, nie celú cestu nad ňou."""
    rows = [_row(node)] + [_row(k) for k in children.get(node["id"], [])]
    return _fp(rows)


def home_fingerprint(data: dict, children: dict) -> str:
    """Domov: názov webu, hlavné sekcie a NESKONČENÉ Aktuálne (tie sa menia najčastejšie)."""
    today = date.today().isoformat()
    akt = [[a.get("name") or "", a.get("name_en") or "", a.get("url") or "", a.get("icon") or ""]
           for a in (data.get("aktualne") or []) if not (a.get("endsAt") and today > a["endsAt"])]
    title = [data.get("title") or "", data.get("subtitle") or "",
             data.get("title_en") or "", data.get("subtitle_en") or ""]
    rows = [title] + [_row(k) for k in children.get(None, [])] + akt
    return _fp(rows)


def load_lastmod() -> dict:
    try:
        with open(LASTMOD_FILE, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def lastmod_for(state: dict, new_state: dict, key: str, fp: str, today: str) -> str:
    """Rovnaký odtlačok ako minule → starý dátum; inak (zmena alebo nová stránka) dnešok."""
    old = state.get(key)
    d = old["d"] if (old and old.get("h") == fp and old.get("d")) else today
    new_state[key] = {"h": fp, "d": d}
    return d


def save_lastmod(new_state: dict) -> None:
    """Jeden záznam na riadok (prehľadný git diff), zotriedené podľa cesty."""
    lines = ",\n".join(
        f'  {json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False, separators=(",", ":"))}'
        for k, v in sorted(new_state.items()))
    with open(LASTMOD_FILE, "w", encoding="utf-8") as f:
        f.write("{\n" + lines + "\n}\n")


# ------------------------------------------------------------
# AKTUÁLNE PRIAMO V HTML (od 2.10.2026)
# ------------------------------------------------------------
def akt_static_html(aktualne: list):
    """Vráti (text počítadla, HTML kariet) PRESNE v značkovaní renderAktualne()
    v index.html (verejný režim: skončené vynechané, NEW do 24 h od pridania).
    Appka po štarte pás prekreslí na to isté — DOM je zhodný, nič neblikne."""
    today = date.today().isoformat()
    now_ms = int(time.time() * 1000)
    items = [a for a in aktualne if not (a.get("endsAt") and today > a["endsAt"])]
    if not items:
        txt = "No current events" if LANG == "en" else "Žiadne aktuálne udalosti"
        return "", f'<span style="font-size:0.78rem;color:var(--muted);padding:6px 0">{txt}</span>'
    parts = []
    for a in items:
        try:   # bod 21 previerky: zlá hodnota addedAt (text, prázdne) nesmie zhodiť build
            added = int(a.get("addedAt") or 0)
        except (TypeError, ValueError):
            added = 0
        is_new = bool(added) and (now_ms - added) < 86400000
        name = (a.get("name_en") if (LANG == "en" and a.get("name_en")) else a.get("name")) or ""
        parts.append(
            '\n    <a class="akt-card" href="' + escape(a.get("url") or "", quote=True)
            + '" target="_blank" rel="noopener">'
            + '\n      ' + ('<span class="akt-new">NEW</span>' if is_new else '')
            + '\n      <span class="akt-icon" aria-hidden="true">' + escape(a.get("icon") or "📌") + '</span>'
            + '\n      <span>' + escape(name) + '</span>'
            + '\n    </a>')
    return f"({len(items)})", "".join(parts)


def inject_aktualne(html: str, aktualne: list) -> str:
    """Do prázdneho #aktualneScroll (a #aktualneCount) v index.html vloží karty
    Aktuálnych. Google číta surový HTML a JavaScript spúšťa neskoro alebo vôbec —
    dovtedy pás vkladala až appka, takže ho Google nevidel. Denný cron rebuild
    zabezpečí, že skončené udalosti z HTML vypadnú."""
    m = re.search(r'(<div id="aktualneScroll"[^>]*>)\s*</div>', html)
    c = re.search(r'(<span id="aktualneCount"[^>]*>)</span>', html)
    if not m or not c:
        print("UPOZORNENIE: v index.html nie je prázdny #aktualneScroll / #aktualneCount — "
              "Aktuálne ostanú len cez JavaScript (Google ich neuvidí).")
        return html
    count_txt, cards = akt_static_html(aktualne)
    # #aktualneCount je v HTML PRED #aktualneScroll — najprv zadný úsek, aby pozície sedeli
    html = html[:m.start()] + m.group(1) + cards + "\n  </div>" + html[m.end():]
    html = html[:c.start()] + c.group(1) + count_txt + "</span>" + html[c.end():]
    return html


# ------------------------------------------------------------
# DLAŽDICE DOMOVA A IKONKY ŠPORTOV PRIAMO V HTML (od 2.11.2026, bod 6 previerky)
# ------------------------------------------------------------
_SKL_EN = {"sekcia": "section", "sekcie": "sections", "sekcií": "sections",
           "linka": "link", "linky": "links", "liniek": "links"}


def skl(n: int, jedna: str, dvestyri: str, vela: str) -> str:
    """Skloňovanie — ROVNAKÉ ako skl() v index.html (EN: section/sections, link/links)."""
    if LANG == "en":
        return _SKL_EN.get(jedna, jedna) if n == 1 else _SKL_EN.get(vela, vela)
    return jedna if n == 1 else (dvestyri if 2 <= n <= 4 else vela)


def home_static_html(children: dict, paths: dict):
    """Vráti (HTML do #main, HTML do #hSports) PRESNE v značkovaní renderLevel()
    (domov, bežný režim — vrátane skrytej admin lišty, aby bol obsah zhodný
    s appkou) a renderSportsNav() (bez triedy "on"). Počty _cnt/_sub sa rátajú
    ako v build_boot(), zo stromu children už filtrovaného podľa jazyka.
    Appka pri prvom vykreslení obsah porovná a ak je zhodný, neprepíše ho."""
    def cnt(fid):
        return sum(1 if k.get("type") == "link" else cnt(k["id"])
                   for k in children.get(fid, []))

    def href(fid):
        return escape(SITE_ABS_ROOT + "/".join(paths.get(fid, [])) + "/", quote=True)

    top = children.get(None, [])
    folders = [n for n in top if n.get("type") == "folder"]
    has_links = any(n.get("type") == "link" for n in top)
    main = ""
    if folders:
        if has_links:
            main += '<div class="section-label">' + ("Categories" if LANG == "en" else "Kategórie") + "</div>"
        big = len(folders) <= 10
        main += '<div class="grid-root anim">' if big else '<div class="grid-deep anim">'
        for n in folders:
            i = n["id"]
            total = cnt(i)
            sub = sum(1 for k in children.get(i, []) if k.get("type") == "folder")
            sek = f"{sub} {skl(sub, 'sekcia', 'sekcie', 'sekcií')}"
            lin = f"{total} {skl(total, 'linka', 'linky', 'liniek')}"
            c = f"{sek} · {lin}" if (sub > 0 and total > 0) else (sek if sub > 0 else lin)
            name = escape(node_name(n), quote=True)
            if big:
                main += f"""
          <a class="card-root" href="{href(i)}" onclick="return navClick(event,'{i}')">
            <div class="card-admin-bar">
              <button class="ibtn" title="Hore" onclick="event.stopPropagation();event.preventDefault();moveNode('{i}',-1)">▲</button>
              <button class="ibtn" title="Dole" onclick="event.stopPropagation();event.preventDefault();moveNode('{i}',1)">▼</button>
              <button class="ibtn" title="Upraviť" onclick="event.stopPropagation();event.preventDefault();openEdit('{i}')">✏️</button>
              <button class="ibtn d" title="Zmazať" onclick="event.stopPropagation();event.preventDefault();delNode('{i}')">🗑</button>
            </div>
            <div class="c-icon">{icon_html(n.get("icon", ""), "40x30")}</div>
            <div class="c-name">{name}</div>
            <div class="c-count">{c}</div>
            <div class="c-arrow">→</div>
          </a>"""
            else:
                main += f"""
          <a class="card-folder" href="{href(i)}" onclick="return navClick(event,'{i}')">
            <div class="card-admin-bar">
              <button class="ibtn" onclick="event.stopPropagation();event.preventDefault();moveNode('{i}',-1)">▲</button>
              <button class="ibtn" onclick="event.stopPropagation();event.preventDefault();moveNode('{i}',1)">▼</button>
              <button class="ibtn" onclick="event.stopPropagation();event.preventDefault();openEdit('{i}')">✏️</button>
              <button class="ibtn d" onclick="event.stopPropagation();event.preventDefault();delNode('{i}')">🗑</button>
            </div>
            <div class="cf-icon">{icon_html(n.get("icon", ""), "24x18")}</div>
            <div class="cf-info">
              <div class="cf-name">{name}</div>
              <div class="cf-count">{c}</div>
            </div>
            <div class="cf-arrow">›</div>
          </a>"""
        main += "</div>"
    nav = "".join(
        f'<a href="{href(n["id"])}" onclick="return navClick(event,\'{n["id"]}\')" class="" '
        f'aria-label="{escape(node_name(n), quote=True)}">{icon_html(n.get("icon", ""), "24x18")}'
        f'<span>{escape(node_name(n), quote=True)}</span></a>'
        for n in folders)
    return main, nav


def inject_home(html: str, children: dict, paths: dict) -> str:
    """Do prázdneho #main vloží dlaždice hlavných sekcií a do prázdneho #hSports
    ikonky športov. Dovtedy ich kreslil len JavaScript, takže roboti bez neho
    nevideli na domove žiadny odkaz dovnútra webu. Rovnako ako inject_aktualne()."""
    m = re.search(r'<main id="main"></main>', html)
    v = re.search(r'(<nav class="h-sports" id="hSports"[^>]*>)</nav>', html)
    if not m or not v:
        print("UPOZORNENIE: v index.html nie je prázdny #main / #hSports — "
              "dlaždice domova ostanú len cez JavaScript (roboti ich neuvidia).")
        return html
    main, nav = home_static_html(children, paths)
    # #hSports je v HTML PRED #main — najprv zadný úsek, aby pozície sedeli
    html = html[:m.start()] + '<main id="main">' + main + "</main>" + html[m.end():]
    html = html[:v.start()] + v.group(1) + nav + "</nav>" + html[v.end():]
    return html


def compute_has_link(children: dict) -> dict:
    """Pre každý priečinok zistí, či má v podstrome aspoň 1 linku.
    Priečinky bez liniek nedostanú statickú stránku („tenký obsah")."""
    has_link = {}

    def check(fid):
        kids = children.get(fid, [])
        result = any(k.get("type") == "link" for k in kids)
        for k in kids:
            if k.get("type") == "folder":
                result = check(k["id"]) or result
        has_link[fid] = result
        return result

    for top in children.get(None, []):
        if top.get("type") == "folder":
            check(top["id"])
    return has_link


# ------------------------------------------------------------
# HTML ŠABLÓNA
# ------------------------------------------------------------
CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0f1923;color:#e8edf2;font-family:'Segoe UI',Arial,sans-serif;line-height:1.5}
a{color:#e8edf2;text-decoration:none}
.wrap{max-width:900px;margin:0 auto;padding:20px 16px 60px}
.crumbs{font-size:.9rem;color:#8fa3b3;margin-bottom:18px}
.crumbs a{color:#8fa3b3}
.crumbs a:hover{color:#e84242}
h1{font-size:1.6rem;margin-bottom:6px}
h1 .ic{margin-right:8px}
.desc{color:#8fa3b3;margin-bottom:22px}
.promo{display:flex;gap:22px;align-items:flex-start;background:#182430;border:1px solid #2a3642;border-radius:12px;padding:20px;margin-bottom:22px}
.promo-ban{flex-shrink:0;width:300px;min-height:250px;display:flex;flex-direction:column;align-items:center}
.promo-ban img{max-width:100%;display:block}
.promo-txt{flex:1;min-width:0}
.promo-tag{font-size:.65rem;letter-spacing:1px;color:#8fa3b3;margin-bottom:8px}
.promo-txt h3{margin:0 0 10px;font-size:1.25rem;line-height:1.25;color:#fff}
.promo-txt p{margin:0 0 10px;font-size:.9rem;line-height:1.55}
.promo-btn{display:inline-block;background:__ACCENT_STRONG__;color:#fff!important;font-weight:700;font-size:.9rem;padding:10px 18px;border-radius:8px;margin-top:6px;text-decoration:none}
.promo-warn{font-size:.7rem;color:#8fa3b3;border-top:1px solid #2a3642;padding-top:10px;margin-top:22px}
@media(max-width:560px){.promo{flex-direction:column;padding:14px;gap:12px}.promo-ban{align-self:center;width:100%;max-width:300px}}
h2{font-size:1.05rem;color:__ACCENT_TEXT__;margin:26px 0 10px;text-transform:uppercase;letter-spacing:.05em}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:10px}
.card{display:block;background:#182635;border:1px solid #24364a;border-radius:10px;padding:12px 14px;transition:.15s}
@media(hover:hover){.card:hover{border-color:#e84242;transform:translateY(-1px)}}
.card .nm{font-weight:600}
.card .ds{font-size:.85rem;color:#8fa3b3;margin-top:3px}
.card .ur{font-size:.78rem;color:#8396a8;margin-top:3px;word-break:break-all}
.appbtn{display:inline-block;background:__ACCENT_STRONG__;color:#fff;border-radius:8px;padding:10px 18px;font-weight:600;margin-top:30px}
.appbtn:hover{background:#c73535}
.brow{display:flex;gap:10px;flex-wrap:wrap;margin:0 0 16px}
.bslot{width:468px;max-width:100%;height:60px;border-radius:8px;overflow:hidden}
.bslot a{display:block;width:100%;height:100%}
.bslot img{width:100%;height:100%;object-fit:cover;display:block}
@media(max-width:560px){#bslot2{display:none!important}.bslot{aspect-ratio:468/60;height:auto}.bslot img{object-fit:contain}}
.adframe{display:block;border:0;width:100%;overflow:hidden;background:transparent;color-scheme:dark}
.adframe-slot{height:100%}
.adframe-auto{height:250px}
.akt{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 20px;align-items:center}
.akt .lbl{color:__ACCENT_TEXT__;font-weight:600;font-size:.78rem;text-transform:uppercase;letter-spacing:.05em}
.akt a{background:#182635;border:1px solid #24364a;border-radius:20px;padding:6px 12px;font-size:.85rem}
.akt a:hover{border-color:#e84242}
.secnav{margin-top:34px;padding-top:18px;border-top:1px solid #24364a;display:flex;flex-wrap:wrap;gap:6px 16px;font-size:.85rem}
.secnav a{color:#8fa3b3}
.secnav a:hover{color:#e84242}
footer{display:block;margin-top:14px;color:#8396a8;font-size:.78rem}
"""
CSS = CSS.replace("#e84242", ACCENT).replace("#c73535", ACCENT_HOVER)
# nové odtiene sú v CSS ako značky, aby ich náhrada #e84242 vyššie nepokazila
CSS = CSS.replace("__ACCENT_TEXT__", ACCENT_TEXT).replace("__ACCENT_STRONG__", ACCENT_STRONG)

FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E"
           "%3Crect width='64' height='64' rx='12' fill='%230f1923'/%3E"
           "%3Crect y='54' width='64' height='10' fill='%23e84242'/%3E"
           "%3Ctext x='32' y='42' font-family='Arial,sans-serif' font-size='32' font-weight='800'"
           " font-style='italic' text-anchor='middle' fill='%23ffffff'%3ES"
           "%3Ctspan fill='%23e84242'%3EL%3C/tspan%3E%3C/text%3E%3C/svg%3E")
FAVICON = FAVICON.replace("%23e84242", "%23" + ACCENT[1:])
# Favicon ako SÚBORY (bod 7 previerky): Google vo výsledkoch hľadania neukáže
# favicon vložený ako data:. Pri builde sa zapíše favicon.svg (čisté SVG
# z FAVICON vyššie, už vo farbe jazyka) a skopírujú sa favicon.ico
# a apple-touch-icon.png. Cesty sú od koreňa webu, aby fungovali na každej
# podstránke aj v 404.html.
FAVICON_SVG = unquote(FAVICON[len("data:image/svg+xml,"):])
FAVICON_LINKS = (f'<link rel="icon" href="{SITE_ABS_ROOT}favicon.ico" sizes="48x48">\n'
                 f'<link rel="icon" href="{SITE_ABS_ROOT}favicon.svg" type="image/svg+xml">\n'
                 f'<link rel="apple-touch-icon" href="{SITE_ABS_ROOT}apple-touch-icon.png">')

# BOD 16 (3.11.2026): ZOZNAM POVOLENÝCH DOMÉN (Content-Security-Policy) — rovnaký
# ako <meta http-equiv="Content-Security-Policy"> v index.html (main() to pri builde
# kontroluje, build pri rozdiele spadne). Vysvetlenie jednotlivých častí je v index.html.
CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline' https://ban.tipsport.sk https://gc.zgo.at; "
       "connect-src 'self' https://ban.tipsport.sk https://sportlinky.goatcounter.com https://sportlinking.goatcounter.com; "
       "img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; font-src 'self' data:; "
       "frame-src 'self' https://ban.tipsport.sk; object-src 'none'; base-uri 'self'; form-action 'self'")
CSP_META = f'<meta http-equiv="Content-Security-Policy" content="{CSP}"/>'

# BOD 16: CUDZÍ REKLAMNÝ KÓD V UZAVRETOM OKIENKU — rovnako ako adFrame() v index.html
# (obsah okienka musí byť ZHODNÝ; meň oba naraz). HTML s <script>/<iframe> (kód
# partnera) sa vloží do <iframe sandbox> cez srcdoc: bez allow-same-origin a bez
# allow-top-navigation skript nevidí stránku, cookies ani nepresmeruje hlavné okno.
AD_SANDBOX = "allow-scripts allow-popups allow-popups-to-escape-sandbox"
AD_NEEDS_FRAME_RE = re.compile(r"<(script|iframe)\b", re.I)


def ad_frame_doc(h: str, auto: bool) -> str:
    """Obsah okienka (srcdoc) — znak po znaku ako v adFrame() v index.html."""
    css = ('<style>:root{color-scheme:dark}html,body{margin:0;padding:0;border:0;overflow:hidden;background:transparent}'
           + ('' if auto else 'html,body{height:100%}')
           + 'body{color:#e8eaf0;font:14px/1.4 "Segoe UI",Arial,sans-serif;text-align:center}'
           + 'a{color:inherit;text-decoration:none}img{max-width:100%;height:auto;display:block;margin:0 auto;border:0}</style>')
    vyska = ('<script>(function(){var p=0;function s(){var h=Math.ceil(document.body.getBoundingClientRect().height);'
             'if(h&&h!==p){p=h;parent.postMessage({sportlinkyAdH:h},"*")}}'
             'if(window.ResizeObserver)new ResizeObserver(s).observe(document.body);addEventListener("load",s);setTimeout(s,0);setTimeout(s,2000)})()</script>'
             if auto else '')
    return ('<!DOCTYPE html><html><head><meta charset="utf-8"><base target="_blank">' + css
            + '</head><body>' + h + vyska + '</body></html>')


def ad_frame(h: str, auto: bool) -> str:
    """<iframe sandbox srcdoc=…> pre kód partnera; ostatné HTML vráti bez zmeny."""
    if not AD_NEEDS_FRAME_RE.search(h or ""):
        return h
    return (f'<iframe class="adframe adframe-{"auto" if auto else "slot"}" sandbox="{AD_SANDBOX}" '
            f'srcdoc="{escape(ad_frame_doc(h, auto), quote=True)}" title="Reklama" scrolling="no"></iframe>')


PAGE = """<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<!--CSP-->
<title>{title}</title>
<meta name="description" content="{meta_desc}">
{favicons}
{canonical}
{og_tags}
{jsonld}
<style>{css}</style>
</head>
<body>
<div class="wrap">
<nav class="crumbs">{crumbs}</nav>
<div class="brow"><div id="bslot" class="bslot" hidden></div><div id="bslot2" class="bslot" hidden></div></div>
<div id="akt" class="akt" hidden></div>
<h1><span class="ic">{icon}</span>{name}</h1>
{desc_html}
{promo_html}
{folders_html}
{links_html}
{promo_warn}
<a class="appbtn" id="appbtn" style="display:none" href="{app_href}">{open_app} →</a>
<noscript><style>#appbtn{{display:inline-block!important}}</style></noscript>
{secnav}
<footer>{site_title} — {footer}</footer>
</div>
{page_boot}{dyn_js}
{takeover}
</body>
</html>
"""
PAGE = PAGE.replace("<!--CSP-->", CSP_META, 1)
# začiatok a koniec okienka slotu + sandbox pre __dyn (JS pole; "</" → "<\\/", aby
# text nezavrel <script>)
_af = ad_frame_doc("\x00", False).split("\x00")
ADFRAME_JS = json.dumps([_af[0], _af[1], AD_SANDBOX]).replace("</", "<\\/")

# Dynamický JS: banner + Aktuálne z data.json.
# __ANC__ = id priečinkov od koreňa po túto stránku (cielenie bannerov),
# __ROOT__ = relatívna cesta ku koreňu webu, __AKT_LABEL__ = nadpis pásu.
# POZOR: spúšťa sa LEN ako záloha, ak sa nepodarí prevziať appku (viď TAKEOVER).
# Pri úspešnom prevzatí si bannery aj Aktuálne vykreslí appka sama.
DYN_JS = """<script>
// bod 16: výška okienka s reklamou (promo blok) — len od nášho okienka, len rozumné číslo
window.addEventListener("message",function(e){
  var d=e.data;if(!d||typeof d!=="object"||typeof d.sportlinkyAdH!=="number")return;
  var h=d.sportlinkyAdH;if(!isFinite(h)||h<10||h>1000)return;
  var fs=document.querySelectorAll("iframe.adframe-auto");
  for(var i=0;i<fs.length;i++){if(fs[i].contentWindow===e.source){fs[i].style.height=Math.round(h)+"px";return}}
});
function __dyn(){
  // bod 16: kód partnera (<script>/<iframe>) v banneri → uzavreté okienko (ako adFrame v index.html)
  var AF=__ADFRAME__;
  var ANC=__ANC__;
  // bod 14: text z dát → HTML entity; adresa len http(s) alebo relatívna od koreňa
  // webu („/obrazok.png", nie „//cudzi-web"), inak "#" — ROVNAKO ako safeUrl v index.html
  function esc(s){return String(s||"").replace(/&/g,"&amp;").replace(/"/g,"&quot;").replace(/</g,"&lt;").replace(/>/g,"&gt;")}
  function safeUrl(u){var s=String(u||"").trim();return /^(https?:\\/\\/|\\/(?!\\/))/i.test(s)?s:"#"}
  fetch("__DATAURL__").then(function(r){return r.json()}).then(function(d){
    // bod 19: MIESTNY dátum (slovenský čas), nie UTC — po polnoci by banner
    // s kampaňou do včera svietil ešte 1–2 hodiny (toISOString je v UTC)
    var _d=new Date(),today=_d.getFullYear()+"-"+("0"+(_d.getMonth()+1)).slice(-2)+"-"+("0"+_d.getDate()).slice(-2);
    var bs=(d.banners||[]).filter(function(b){
      if((b.lang||"sk")!=="__LANG__")return false;
      if(b.active===false)return false;
      if(b.startsAt&&today<b.startsAt)return false;
      if(b.endsAt&&today>b.endsAt)return false;
      if(b.sectionId&&ANC.indexOf(b.sectionId)<0)return false;
      return true;
    });
    var st=d.bannerSettings||{};
    function pickBanner(arr){
      if(!arr.length)return null;
      if(st.rotate&&arr.length>1){
        var pool=[];
        arr.forEach(function(x){var w=Math.max(1,Math.min(10,parseInt(x.weight)||1));for(var i=0;i<w;i++)pool.push(x)});
        return pool[Math.floor(Math.random()*pool.length)];
      }
      return arr.filter(function(x){return x.id===st.activeId})[0]||arr[0];
    }
    function showSlot(elId,slotNum){
      var b=pickBanner(bs.filter(function(x){return (x.slot===2||x.slot==="2"?2:1)===slotNum}));
      if(!b)return;
      var el=document.getElementById(elId);
      el.hidden=false;
      el.innerHTML=!b.html?'<a href="'+esc(safeUrl(b.linkUrl))+'" target="_blank" rel="noopener sponsored"><img src="'+esc(safeUrl(b.imageUrl))+'" alt="'+esc(b.alt||"Reklama")+'"></a>'
        :/<(script|iframe)\\b/i.test(b.html)?'<iframe class="adframe adframe-slot" sandbox="'+AF[2]+'" srcdoc="'+esc(AF[0]+b.html+AF[1])+'" title="Reklama" scrolling="no"></iframe>'
        :b.html;
    }
    showSlot("bslot",1);
    showSlot("bslot2",2);
    var ak=ANC.indexOf("f_ltw")>=0?[]:(d.aktualne||[]).filter(function(a){return !(a.endsAt&&today>a.endsAt)});
    if(ak.length){
      var el2=document.getElementById("akt");
      el2.hidden=false;
      el2.innerHTML='<span class="lbl">__AKT_LABEL__</span>'+ak.map(function(a){
        return '<a href="'+esc(safeUrl(a.url))+'" target="_blank" rel="noopener">'+(a.icon?esc(a.icon)+" ":"")+esc(("__LANG__"==="en"&&a.name_en)?a.name_en:a.name)+'</a>';
      }).join("");
    }
  }).catch(function(e){});
}
</script>

<!-- PREVZATIE APPKOU: statická stránka (ktorú vidí Google) sa hneď po načítaní
     nahradí plnou interaktívnou aplikáciou. Adresa v prehliadači sa NEMENÍ,
     návštevník z Googlu tak skončí rovno v appke bez jediného kliknutia.
     Ak sa to z akéhokoľvek dôvodu nepodarí, ukáže sa pôvodné tlačidlo
     a dokreslia sa bannery + Aktuálne tak ako predtým. -->"""

# __ROOT__ = relatívna cesta ku koreňu, odkiaľ sa stiahne appka.
# Koreň webu už má appka zapísaný v sebe (dopĺňa ho main() pri kopírovaní),
# takže tu ju stačí prevziať tak, ako je.
# Verzia publikovaných dát — dopĺňa ju main() z data.json. Používa sa na
# adresu "data.json?v=138", vďaka ktorej sa smie súbor cachovať.
DATA_VER = ""

# PREVZATIE BEZ ČAKANIA NA DÁTA (od 2.11.2026, bod 2 previerky): appka sa preberá
# hneď, ako je stiahnutý index.html (po prvej stránke je v pamäti prehliadača).
# data.json (~1,2 MB zbalený) si appka stiahne až PO prevzatí, na pozadí. Podstránku
# vykreslí z mini-balíka #pageBoot (viď build_page_boot) — má v ňom celú cestu
# z adresy aj deti tejto stránky, takže adresu nikdy neprepíše vyššie (to bol
# pôvodný dôvod čakania na dáta: Google hlásil „Stránka s presmerovaním").
# Balík a pozícia posunu sa odovzdajú prevzatému dokumentu VLOŽENÍM <script> do
# HTML pred document.write — globálne premenné okna document.open() vo všetkých
# prehliadačoch spoľahlivo neprežijú (staršie Safari/Firefox vyrábali nové okno).
TAKEOVER = """<script>
(function(){
  // Vyhladavacie roboty (Googlebot, Bingbot, nastroj kontroly adresy v Search
  // Console...) stranku appkou NEPREBERAME: indexuju staticku stranku, ktora ma
  // unikatny titulok, popis, drobcekovu navigaciu a zoznam podpriecinkov bez
  // ramu appky (hlavicka, pocitadlo, Live This Week). Po prevzati bol pri tenkych
  // priecinkoch obsah z 95 % rovnaky a Google ich oznacoval za duplicity
  // (Search Console 22.9.2026, 33 stranok). Obsah je ten isty, nejde o cloaking.
  if(/Googlebot|Google-InspectionTool|bingbot|Applebot|DuckDuckBot|YandexBot|Baiduspider|Slurp|SeznamBot|PetalBot|Bytespider|facebookexternalhit|Twitterbot|LinkedInBot/i.test(navigator.userAgent)) return;
  var btn=document.getElementById("appbtn"), done=false;
  // Prevzatie appkou prepise CELY dokument obsahom domovskeho index.html —
  // aj jeho hlavicku. updateHead() opravi <title>, popis aj canonical, ale
  // hreflang uz nie, takze na podstranke zostali hreflang odkazy DOMOVSKEJ
  // stranky ("anglicka verzia tejto stranky je domovska stranka"). To si
  // odporuje s canonical a Google preto stranky oznacoval za duplicity
  // (Search Console 19.9.2026, 30 stranok; overenie opravy titulkov zlyhalo).
  // Riesenie: hreflang zo statickej stranky — generator ich pocita spravne —
  // sa prenesu do prevzateho dokumentu a domovske sa zahodia. Ak staticka
  // stranka hreflang nema (404.html, stranka bez naprotivku v druhom jazyku),
  // nevlozi sa ziadny: neparovy hreflang je horsi nez ziadny.
  function prenesHreflang(h){
    try{
      var moje = "", ls = document.querySelectorAll('link[rel="alternate"][hreflang]');
      for(var i=0;i<ls.length;i++){
        moje += '<link rel="alternate" hreflang="' + ls[i].getAttribute("hreflang")
              + '" href="' + ls[i].getAttribute("href") + '">';
      }
      h = h.replace(/<link[^>]*hreflang=[^>]*>\\s*/gi, "");
      if(moje) h = h.replace(/<head([^>]*)>/i, "<head$1>" + moje);
    }catch(e){}
    return h;
  }
  function fallback(){
    if(done) return;
    if(btn) btn.style.display="inline-block";
    try{ __dyn(); }catch(e){}
    var s=document.createElement("script");
    s.async=true; s.src="https://gc.zgo.at/count.js";
    s.setAttribute("data-goatcounter","https://__GOAT__.goatcounter.com/count");
    document.body.appendChild(s);
  }
  // mini-balik stranky (JSON v <script type="application/json" id="pageBoot">)
  // a poziciu posunu si treba vziat PRED document.open(), ktory dokument vymaze
  function balik(){
    try{
      var el = document.getElementById("pageBoot");
      if(!el) return "";
      var t = el.textContent || "";
      JSON.parse(t); // poskodeny balik radsej vynechat — appka si pocka na data
      // generator uz znaky < > & zakodoval; poistka, aby text nikdy nezavrel <script>
      t = t.replace(/</g,"\\\\u003c").replace(/>/g,"\\\\u003e").replace(/&/g,"\\\\u0026");
      return "<script>window.__PAGE_BOOT=" + t + ";window.__PAGE_SCROLL="
           + (Math.round(window.scrollY||window.pageYOffset||0)) + ";<\\/script>";
    }catch(e){ return ""; }
  }
  try{
    fetch("__ROOT__index.html").then(function(r){
      if(!r.ok) throw new Error("app");
      return r.text();
    }).then(function(h){
      if(h.indexOf("let SITE_ROOT =")<0) throw new Error("marker");
      done=true;
      // POZOR na poradie: document.open() VYMAZE cely dokument, preto sa hreflang
      // aj balik zo statickej stranky musia precitat PRED nim (chyba z 20.9.2026 —
      // po prevzati nezostal ziadny hreflang).
      var nh = prenesHreflang(h), pb = balik();
      if(pb) nh = nh.replace(/<head([^>]*)>/i, function(m){ return m + pb; });
      document.open(); document.write(nh); document.close();
    }).catch(fallback);
  }catch(e){ fallback(); }
})();
</script>"""


PROMO_WARN = ("Hazardné hry predstavujú riziko vysokých finančných strát. Nadmerné hranie hazardných hier "
              "predstavuje riziko vzniku závislosti. Hráčom môže byť len osoba staršia ako 18 rokov.")
PROMOS = []          # DB.promos — doplní main() z data.json
PROMO_BANNER = {}    # DB.promoBanner


def _promo_ok(p: dict, anc_ids: list) -> bool:
    """Rovnaké pravidlá ako v appke: aktívny, v dátumovom okne, cielený na sekciu v ceste."""
    if p.get("active") is False:
        return False
    today = date.today().isoformat()
    if p.get("startsAt") and today < p["startsAt"]:
        return False
    if p.get("endsAt") and today > p["endsAt"]:
        return False
    return (not p.get("sectionId")) or p["sectionId"] in anc_ids


def promo_block(anc_ids: list):
    """Statický promo blok (banner/rotátor + reklamný text) pre SK stránky sekcie Tipovanie.
    Text sa vyberie deterministicky (prvý aktívny s najvyššou váhou) — pri prevzatí appkou
    sa aj tak vykreslí náhodný výber. Vracia (html, varovanie)."""
    if LANG != "sk":
        return "", ""
    pb = PROMO_BANNER or {}
    ban_on = pb.get("active") is not False and (pb.get("html") or "").strip() and _promo_ok(pb, anc_ids)
    texts = [p for p in PROMOS if (p.get("lang") or "sk") == "sk" and _promo_ok(p, anc_ids)]
    if not ban_on and not texts:
        return "", ""
    out = ['<div class="promo">']
    if ban_on:
        out.append(f'<div class="promo-ban">{ad_frame(pb["html"], True)}</div>')   # bod 16: okienko
    if texts:
        p = max(texts, key=lambda x: int(x.get("weight") or 1))
        paras = "".join(f"<p>{escape(t.strip())}</p>" for t in str(p.get("text") or "").split("\n") if t.strip())
        out.append(f'<div class="promo-txt"><div class="promo-tag">{escape(pb.get("label") or "REKLAMA")}</div>'
                   f'<h3>{escape(p.get("title") or "")}</h3>{paras}')
        if p.get("btnUrl"):
            out.append(f'<a class="promo-btn" href="{escape(p["btnUrl"], quote=True)}" target="_blank" '
                       f'rel="noopener sponsored">{escape(p.get("btnText") or "Viac")} ›</a>')
        out.append("</div>")
    out.append("</div>")
    return "".join(out), f'<div class="promo-warn">{PROMO_WARN}</div>'


# Kód krajiny (rovnaké pravidlo ako renderIcon v index.html): „jp", „gb-eng".
FLAG_RE = re.compile(r"^[a-z]{2}(-[a-z]{2,4})?$")


def icon_html(icon: str, size: str = "24x18") -> str:
    """Ikona ako HTML: kód krajiny → obrázok vlajky z vlastného webu /vlajky/
    (sťahuje vlajky.py pri builde; srcset 2× pre ostré displeje — ako v appke),
    emoji → escapovaný text, prázdna → "". Výsledok sa už NEescapuje znova.
    (Dedenie vlajky od rodiča ako nodeIcon v appke sa tu zámerne nerobí.)"""
    icon = (icon or "").strip()
    if not icon:
        return ""
    if FLAG_RE.match(icon):
        w, h = size.split("x")
        s2 = f"{int(w) * 2}x{int(h) * 2}"
        v = SITE_ABS_ROOT + "vlajky/"
        return (f'<img src="{v}{size}/{icon}.png" srcset="{v}{s2}/{icon}.png 2x" width="{w}" height="{h}" '
                f'alt="" loading="lazy" style="border-radius:2px;vertical-align:middle">')
    # bod 25: emoji je len ozdoba — čítačka ho nečíta (rovnako renderIcon v index.html)
    return f'<span aria-hidden="true">{escape(icon)}</span>'


def kopiruj_vlajky(data, out: str) -> None:
    """Skopíruje vlajky/ do <out>/vlajky/ a chýbajúce nahradí priehľadným 1×1 px.
    Kódy a veľkosti berie z vlajky.py (rovnaké, aké sťahuje). Build nikdy nezastaví."""
    try:
        sys.dont_write_bytecode = True   # bez priečinka __pycache__ v repozitári
        import vlajky as vl
        kody, velkosti = vl.kody_vlajok(data), vl.velkosti()
    except Exception as e:
        print(f"UPOZORNENIE: vlajky.py sa nepodarilo použiť ({e}) — vlajky sa len skopírujú.")
        kody, velkosti = [], []
    skopirovane, nahradnikov, chyba = 0, 0, []
    if os.path.isdir("vlajky"):
        for vel in sorted(os.listdir("vlajky")):
            if not os.path.isdir(os.path.join("vlajky", vel)):
                continue
            os.makedirs(os.path.join(out, "vlajky", vel), exist_ok=True)
            for fname in os.listdir(os.path.join("vlajky", vel)):
                if fname.endswith(".png"):
                    shutil.copy(os.path.join("vlajky", vel, fname), os.path.join(out, "vlajky", vel, fname))
                    skopirovane += 1
    for vel in velkosti:
        for kod in kody:
            ciel = os.path.join(out, "vlajky", vel, kod + ".png")
            if not os.path.exists(ciel):
                os.makedirs(os.path.dirname(ciel), exist_ok=True)
                with open(ciel, "wb") as f:
                    f.write(vl.PNG_NAHRADNIK)
                nahradnikov += 1
                chyba.append(f"{vel}/{kod}")
    print(f"Vlajky: {skopirovane} súborov -> {out}/vlajky/"
          + (f", NÁHRADNÍK (priehľadný) za {nahradnikov} chýbajúcich: {', '.join(chyba[:15])}"
             + (" …" if len(chyba) > 15 else "") if nahradnikov else ""))


def count_links(children: dict, paths: dict) -> int:
    """Počet liniek, ktoré sa na webe naozaj zobrazujú: viditeľné v jazyku
    buildu (children už obsahuje len visible()) a uložené v priečinkoch, ktoré
    dostali stránku. Umelé linky Live This Week (z lišty Aktuálne) sa nerátajú."""
    return sum(1 for fid in paths if fid != LIVE_ID
               for k in children.get(fid, []) if k.get("type") == "link")


def links_label(n: int) -> str:
    """Počet zaokrúhlený NADOL na tisíce: SK „14 000+“, EN „14,000+“.
    Pod 1000 presné číslo bez „+“."""
    if n < 1000:
        return str(n)
    s = f"{n // 1000 * 1000:,}"
    return (s if LANG == "en" else s.replace(",", " ")) + "+"


def home_title(n: int) -> str:
    """Titulok domovskej stránky (index.html aj 404.html) s počtom webov."""
    if LANG == "en":
        return f"Sportlinking — {links_label(n)} club, league and news websites"
    return f"Športové Linky — {links_label(n)} webov klubov, líg a správ"


# ------------------------------------------------------------
# TITULKY STRÁNOK (bod 23 previerky, 2.11.2026)
# ------------------------------------------------------------
# Titulok má tvar „{názov} — {rodič} · {šport} — {web}". Google vo výsledkoch
# ukáže zhruba 60–65 znakov, dlhšie titulky odreže. Ak je titulok dlhší ako
# TITLE_MAX znakov, vynechá sa z kontextu ŠPORT („{názov} — {rodič} — {web}"),
# ale IBA vtedy, keď je takto skrátený titulok na celom webe JEDINEČNÝ (inak by
# Google stránky bral ako duplicity — kvôli tomu sa šport do titulku pridával).
# Zoznam priečinkov so skráteným titulkom (TITLE_NOSPORT) dostane aj appka —
# kľúč "_titleNoSport" v odľahčenom data.json, v BOOT a v mini-balíku stránky —
# aby titulok po prevzatí appkou bol presne taký istý ako na statickej stránke.
# Do data-full.json (dáta admina) sa NEPÍŠE.
TITLE_MAX = 65
TITLES = {}             # id priečinka -> titulok (bez HTML escapovania)
TITLE_NOSPORT = set()   # id priečinkov, ktorým sa šport z titulku vynechal


def live_title(name: str, site_title: str) -> str:
    """Titulok Live This Week s rozsahom aktuálneho týždňa (pondelok–nedeľa).
    Vďaka dennému cron rebuildu je dátum vždy čerstvý — vo výsledkoch Googlu to
    signalizuje živú stránku. Mení sa LEN <title>, názov priečinka ostáva."""
    _mon = date.today() - timedelta(days=date.today().weekday())
    _sun = _mon + timedelta(days=6)
    _m = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
    if _mon.month == _sun.month:
        _rng = f"{_mon.day}–{_sun.day} {_m[_sun.month-1]}"
    else:
        _rng = f"{_mon.day} {_m[_mon.month-1]} – {_sun.day} {_m[_sun.month-1]}"
    return f"{name} ({_rng}) — {site_title}"


def compute_titles(folder_ids, by_id, site_title: str, home: str):
    """Vypočíta titulky všetkých priečinkov (folder_ids = všetky priečinky, na
    ktoré sa dá v appke prekliknúť, aj tie bez statickej stránky) a rozhodne,
    ktorým sa vynechá šport. Vracia (titulky, množina id bez športu).

    Skrátený titulok sa použije, len ak sa na webe nevyskytuje nikde inde —
    ani medzi plnými titulkami iných stránok, ani medzi inými skrátenými,
    ani ako titulok domova. Kontroluje sa opakovane, kým sa nič nemení
    (stránka, ktorej sa skrátenie zamietne, má zase plný titulok)."""
    full, short = {}, {}
    for fid in folder_ids:
        n = by_id[fid]
        chain = []
        a = n
        while a is not None:
            chain.append(a)
            a = by_id.get(a.get("parentId"))
        name = node_name(n)
        if fid == LIVE_ID:
            full[fid] = live_title(name, site_title)
            continue
        ctx = []
        if len(chain) >= 2:
            ctx.append(node_name(chain[1]))          # rodič
        if len(chain) >= 3:
            ctx.append(node_name(chain[-1]))         # šport (koreň)
        full[fid] = (f"{name} — {' · '.join(ctx)} — {site_title}" if ctx
                     else f"{name} — {site_title}")
        if len(chain) >= 3 and len(full[fid]) > TITLE_MAX:
            short[fid] = f"{name} — {ctx[0]} — {site_title}"
    nosport = set(short)
    while True:
        cnt = {}
        for fid in folder_ids:
            t = short[fid] if fid in nosport else full[fid]
            cnt[t] = cnt.get(t, 0) + 1
        cnt[home] = cnt.get(home, 0) + 1
        bad = {fid for fid in nosport if cnt[short[fid]] > 1}
        if not bad:
            break
        nosport -= bad
    titles = {fid: (short[fid] if fid in nosport else full[fid]) for fid in folder_ids}
    return titles, nosport


def render_page(node, path, children, by_id, paths, site_title, alt_url=None, page_boot=""):
    depth = len(path)
    root = "../" * depth
    name = escape(node_name(node))
    icon = icon_html(node.get("icon", ""), "24x18")
    if icon:
        icon += " "   # medzera, aby názov nebol nalepený na ikonu („jpJaponsko")
    desc = escape(node_desc(node))

    # breadcrumbs
    crumbs = [f'<a href="{root}">{T["home"]}</a>']
    acc = node
    chain = []
    while acc is not None:
        chain.append(acc)
        acc = by_id.get(acc.get("parentId"))
    for i, anc in enumerate(reversed(chain)):
        if anc["id"] == node["id"]:
            crumbs.append(name)
        else:
            up = "../" * (depth - i - 1)
            crumbs.append(f'<a href="{up}">{escape(node_name(anc))}</a>')
    crumbs_html = " › ".join(crumbs)

    kids = children.get(node["id"], [])
    # karty priečinkov len pre tie, ktoré majú vlastnú stránku (nie prázdne)
    folders = [k for k in kids if k.get("type") == "folder" and k["id"] in paths]
    links = [k for k in kids if k.get("type") == "link"]

    fold_cards = ""
    if folders:
        cards = []
        for f in folders:
            slug = paths[f["id"]][-1]
            d = escape(node_desc(f))
            fic = icon_html(f.get("icon", ""), "20x15")
            ds = f'<div class="ds">{d}</div>' if d else ""
            cards.append(
                f'<a class="card" href="{slug}/">'
                f'<div class="nm">{fic + " " if fic else ""}{escape(node_name(f))}</div>{ds}</a>'
            )
        fold_cards = f'<h2>{T["folders"]}</h2><div class="grid">' + "".join(cards) + "</div>"

    link_cards = ""
    if links:
        cards = []
        for l in links:
            d = escape(node_desc(l))
            lic = icon_html(l.get("icon", ""), "20x15")
            ds = f'<div class="ds">{d}</div>' if d else ""
            url = escape(l.get("url", ""), quote=True)
            host = re.sub(r"^https?://(www\.)?", "", l.get("url", "")).split("/")[0]
            cards.append(
                f'<a class="card" href="{url}" target="_blank" rel="noopener">'
                f'<div class="nm">{lic + " " if lic else ""}{escape(node_name(l))}</div>{ds}'
                f'<div class="ur">{escape(host)}</div></a>'
            )
        link_cards = f'<h2>{T["links"]}</h2><div class="grid">' + "".join(cards) + "</div>"

    # meta popis z NEescapovaného textu (escapuje sa až pri vložení do šablóny,
    # inak by apostrofy skončili dvojito escapované, napr. Europe&amp;#x27;s)
    meta = node_desc(node) or T["meta_folder"].format(
        name=node_name(node), nfold=len(folders), nlink=len(links))
    url_path = "/".join(path) + "/"
    canonical = f'<link rel="canonical" href="{BASE_URL}/{url_path}">' if BASE_URL else ""

    # hreflang: párové prepojenie SK ↔ EN verzie tej istej stránky.
    # x-default = EN (priorita anglického trhu). Ak stránka na druhom webe
    # neexistuje (alt_url je None), hreflang sa nevypíše — nepárový je zbytočný.
    if BASE_URL and alt_url:
        self_url = f"{BASE_URL}/{url_path}"
        sk_url = self_url if LANG == "sk" else alt_url
        en_url = alt_url if LANG == "sk" else self_url
        canonical += (
            f'\n<link rel="alternate" hreflang="sk" href="{sk_url}">'
            f'\n<link rel="alternate" hreflang="en" href="{en_url}">'
            f'\n<link rel="alternate" hreflang="x-default" href="{en_url}">')

    # <title> s kontextom: „Europe — Competitions · Football — Sportlinking".
    # Bez kontextu mali napr. futbalová a hokejová „Europe" rovnaký titulok
    # a Google ich bral ako duplicity (Search Console 29.8.2026).
    # Titulok (aj skrátený bez športu a Live This Week s dátumom) vyrába
    # compute_titles() — viď TITLES / TITLE_NOSPORT.
    page_title = escape(TITLES[node["id"]])
    og = [f'<meta property="og:title" content="{page_title}">',
          f'<meta property="og:description" content="{escape(meta, quote=True)}">',
          '<meta property="og:type" content="website">',
          f'<meta property="og:site_name" content="{escape(site_title)}">',     # bod 23
          f'<meta property="og:locale" content="{OG_LOCALE}">']
    if BASE_URL:
        og.append(f'<meta property="og:url" content="{BASE_URL}/{url_path}">')
        og.append(f'<meta property="og:image" content="{BASE_URL}/og-image.png">')
    og_tags = "\n".join(og)

    # SEO PÄTIČKA: na každej stránke skutočné odkazy na všetky hlavné sekcie.
    # Bočné prelinkovanie — každá hlboká stránka odkazuje na 10 hlavných sekcií,
    # takže žiadna sekcia nie je pre Google „ďaleko" a každá dostane stovky
    # interných odkazov. Prázdne sekcie (bez stránky) sa vynechajú automaticky.
    sec_links = [f'<a href="{root}">{T["home"]}</a>']
    for t in children.get(None, []):
        if t.get("type") == "folder" and t["id"] in paths:
            sec_links.append(
                f'<a href="{root}{paths[t["id"]][0]}/">{escape(node_name(t))}</a>')
    secnav = ('<nav class="secnav">' + "".join(sec_links) + "</nav>") if len(sec_links) > 1 else ""

    # ŠTRUKTÚROVANÉ DÁTA (BreadcrumbList): strojovo čitateľná drobčeková cesta
    # „Domov › Futbal › Kluby" — Google podľa nej chápe hierarchiu a vo
    # výsledkoch vie zobraziť peknú cestu namiesto holej adresy.
    jsonld = ""
    if BASE_URL:
        items = [{"@type": "ListItem", "position": 1,
                  "name": T["home"], "item": f"{BASE_URL}/"}]
        pos = 2
        for anc in reversed(chain):
            if anc["id"] == node["id"]:
                items.append({"@type": "ListItem", "position": pos,
                              "name": node_name(node)})
            elif anc["id"] in paths:
                items.append({"@type": "ListItem", "position": pos,
                              "name": node_name(anc),
                              "item": f'{BASE_URL}/{"/".join(paths[anc["id"]])}/'})
            else:
                continue
            pos += 1
        jsonld = ('<script type="application/ld+json">'
                  + json.dumps({"@context": "https://schema.org",
                                "@type": "BreadcrumbList",
                                "itemListElement": items}, ensure_ascii=False)
                     .replace("</", "<\\/")   # bod 21: názov s „</script>" nesmie ukončiť značku
                  + "</script>")

    # dynamický JS: banner + Aktuálne z data.json (ANC = id-čka od koreňa po túto stránku)
    anc_ids = [n["id"] for n in reversed(chain)]
    promo_html, promo_warn = promo_block(anc_ids)
    data_url = f"{root}data.json" + (f"?v={DATA_VER}" if DATA_VER else "")

    dyn_js = (DYN_JS
              .replace("__ADFRAME__", ADFRAME_JS)
              .replace("__ANC__", json.dumps(anc_ids))
              .replace("__DATAURL__", data_url)
              .replace("__ROOT__", root)
              .replace("__LANG__", LANG)
              .replace("__AKT_LABEL__", escape(T["aktualne"])))

    takeover = (TAKEOVER
                .replace("__DATAURL__", data_url)
                .replace("__ROOT__", root)
                .replace("__GOAT__", GOAT))

    body = fold_cards + link_cards + icon
    return PAGE.format(
        lang=LANG,
        title=page_title,
        meta_desc=escape(meta, quote=True),
        favicons=FAVICON_LINKS,
        canonical=canonical,
        og_tags=og_tags,
        jsonld=jsonld,
        css=CSS,
        crumbs=crumbs_html,
        icon=icon,
        name=name,
        desc_html=f'<p class="desc">{desc}</p>' if desc else "",
        promo_html=promo_html,
        promo_warn=promo_warn,
        folders_html=fold_cards,
        links_html=link_cards,
        app_href=f'{root}#/{"/".join(path)}',
        open_app=T["open_app"],
        secnav=secnav,
        footer=T["footer"],
        site_title=escape(site_title),
        dyn_js=dyn_js,
        takeover=takeover,
        page_boot=(f'<script type="application/json" id="pageBoot">{page_boot}</script>\n'
                   if page_boot else ""),
    )


# ------------------------------------------------------------
# HLAVNÝ BEH
# ------------------------------------------------------------

def main():
    out = "_site"
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]
    if OUT_PREFIX:
        out = os.path.join(out, OUT_PREFIX)

    data = load_data("data.json")
    global PROMOS, PROMO_BANNER
    PROMOS = data.get("promos") or []
    PROMO_BANNER = data.get("promoBanner") or {}
    global DATA_VER
    DATA_VER = str(data.get("version", "") or "")
    if LANG == "en":
        site_title = data.get("title_en") or data.get("title", "Sportlinking")
    else:
        site_title = data.get("title", "Športové Linky")
    nodes = data.get("nodes", [])
    children, by_id = build_tree(nodes)

    # Live This Week (len EN): priečinok je v dátach prázdny, obsah mu dodá
    # pole "aktualne". Musí sa to stať TU — pred kontrolou prázdnych priečinkov
    # aj pred sitemapou, aby stránka vôbec vznikla.
    if LANG == "en" and LIVE_ID in by_id:
        children[LIVE_ID] = live_week_links(data.get("aktualne", []))

    paths = folder_paths(children)

    # POISTKA: stránku dostanú len priečinky s aspoň 1 linkou v podstrome.
    # Prázdne sekcie (rozostavané) tak nemajú verejnú SEO stránku — neodradia
    # návštevníkov ani Google („tenký obsah"). Po doplnení liniek sa stránka
    # vyrobí automaticky pri najbližšom builde.
    has_link = compute_has_link(children)
    skipped = [fid for fid in paths if not has_link.get(fid)]
    all_paths = paths   # aj priečinky bez liniek — appka na ne tiež odkazuje (dlaždice domova)
    paths = {fid: p for fid, p in paths.items() if has_link.get(fid)}

    # bod 21: výsledné slugy, ktoré sa líšia od základného (duplicity súrodencov)
    SLUG_FIX.clear()
    SLUG_FIX.update({fid: p[-1] for fid, p in all_paths.items() if p[-1] != slug_base(by_id[fid])})

    # bod 23: titulky všetkých priečinkov (aj bez statickej stránky — appka ich
    # tiež ukazuje) a zoznam tých, ktorým sa vynechá šport
    n_links = count_links(children, paths)
    titles, nosport = compute_titles(list(all_paths), by_id, site_title, home_title(n_links))
    TITLES.clear(); TITLES.update(titles)
    TITLE_NOSPORT.clear(); TITLE_NOSPORT.update(nosport)
    n_long = sum(1 for fid in paths if len(titles[fid]) > TITLE_MAX)
    print(f"titulky: {len(nosport)} priečinkov bez športu v titulku "
          f"(statických stránok s titulkom nad {TITLE_MAX} znakov ostáva: {n_long})")

    # hreflang: strom a cesty DRUHÉHO jazyka — aby sme vedeli, či tá istá
    # stránka existuje aj na druhom webe a na akej adrese. Live This Week sa
    # do alt stromu nedopĺňa (nemá slovenský náprotivok, hreflang nedostane).
    children_alt, _ = build_tree(nodes, ALT_LANG)
    has_link_alt = compute_has_link(children_alt)
    paths_alt = {fid: p for fid, p in folder_paths(children_alt, ALT_LANG).items()
                 if has_link_alt.get(fid)}

    os.makedirs(out, exist_ok=True)

    # mini-balíky podstránok (bod 2) — doplnok k BOOT, viď build_page_boot()
    boot_ids = {n["id"] for n in build_boot(data, children)["nodes"]}
    lcnt = link_counts(children)

    # stránky priečinkov
    count = 0
    for fid, path in paths.items():
        d = os.path.join(out, *path)
        os.makedirs(d, exist_ok=True)
        alt_url = (f'{ALT_BASE_URL}/{"/".join(paths_alt[fid])}/'
                   if fid in paths_alt else None)
        html = render_page(by_id[fid], path, children, by_id, paths, site_title, alt_url,
                           build_page_boot(by_id[fid], children, by_id, boot_ids, lcnt))
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(html)
        count += 1

    # sitemap.xml (len v hlavnej jazykovej vetve)
    if not OUT_PREFIX:
        today = date.today().isoformat()
        # lastmod podľa skutočnej zmeny (viď page_fingerprint / LASTMOD_FILE)
        lm_state, lm_new = load_lastmod(), {}
        # štvorice (vlastná adresa, adresa v druhom jazyku alebo None, kľúč, odtlačok)
        entries = [(f"{BASE_URL}/", f"{ALT_BASE_URL}/", "/", home_fingerprint(data, children))]
        for fid, p in sorted(paths.items(), key=lambda kv: kv[1]):
            loc = f'{BASE_URL}/{"/".join(p)}/'
            alt = (f'{ALT_BASE_URL}/{"/".join(paths_alt[fid])}/'
                   if fid in paths_alt else None)
            entries.append((loc, alt, "/".join(p) + "/", page_fingerprint(by_id[fid], children)))
        sm = ['<?xml version="1.0" encoding="UTF-8"?>',
              '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
              '        xmlns:xhtml="http://www.w3.org/1999/xhtml">']
        for loc, alt, lm_key, lm_fp in entries:
            row = f"  <url><loc>{escape(loc)}</loc>"
            # hreflang alternates aj v sitemape (rovnaké pravidlá ako v HTML)
            if BASE_URL and alt:
                sk_u = loc if LANG == "sk" else alt
                en_u = alt if LANG == "sk" else loc
                row += (f'<xhtml:link rel="alternate" hreflang="sk" href="{escape(sk_u)}"/>'
                        f'<xhtml:link rel="alternate" hreflang="en" href="{escape(en_u)}"/>'
                        f'<xhtml:link rel="alternate" hreflang="x-default" href="{escape(en_u)}"/>')
            row += f"<lastmod>{lastmod_for(lm_state, lm_new, lm_key, lm_fp, today)}</lastmod></url>"
            sm.append(row)
        sm.append("</urlset>")
        with open(os.path.join(out, "sitemap.xml"), "w", encoding="utf-8") as f:
            f.write("\n".join(sm))
        save_lastmod(lm_new)
        zmenene = sum(1 for k, v in lm_new.items() if v["d"] == today and (lm_state.get(k) or {}).get("d") != today)
        print(f"sitemap: {len(lm_new)} adries, dnes zmenených/nových {zmenene} -> {LASTMOD_FILE}")

        with open(os.path.join(out, "robots.txt"), "w", encoding="utf-8") as f:
            # bod 23: dátové súbory appky nie sú stránky — roboti appku nepreberajú
            # (TAKEOVER), statickým stránkam stačí HTML; domov sa vykreslí z BOOT
            f.write(f"User-agent: *\nAllow: /\nDisallow: /data.json\nDisallow: /data-full.json\n"
                    f"Sitemap: {BASE_URL}/sitemap.xml\n")

        # version.txt — pár bajtov s číslom verzie dát. Appka si ho pýta bez
        # cache pri každom otvorení. Keď má návštevník v pamäti prehliadača
        # starý index.html (a v ňom staré DATA_VER), takto sa aj tak dozvie,
        # že web má novšie dáta, a stiahne si ich. Bez tohto by videl staré
        # linky, kým sa mu cache sama neprečistí.
        with open(os.path.join(out, "version.txt"), "w", encoding="utf-8") as f:
            f.write(DATA_VER + "\n")

        # skopíruj aplikáciu a dáta; do index.html doplň og:url a og:image
        # (marker <!--OG_DYNAMIC--> — absolútna adresa je známa až pri builde)
        if os.path.exists("index.html"):
            with open("index.html", encoding="utf-8") as f:
                html = f.read()
            if LANG == "en":
                # EN build: prepni jazyk aplikácie, texty, farby a analytiku
                for a, b in (
                    ('const SITE_LANG = "sk";', 'const SITE_LANG = "en";'),
                    ('<html lang="sk">', '<html lang="en">'),
                    ('<title>Športové Linky</title>', '<title>Sportlinking</title>'),
                    ('content="Všetky športové weby sveta na jednom mieste — prehľadný rozcestník overených liniek pre každý šport a krajinu."',
                     'content="All the world\'s sports websites in one place — a clear directory of verified links for every sport and country."'),
                    ('<meta property="og:title" content="Športové Linky"/>',
                     '<meta property="og:title" content="Sportlinking"/>'),
                    ('<meta property="og:site_name" content="Športové Linky"/>',
                     '<meta property="og:site_name" content="Sportlinking"/>'),
                    ('<meta property="og:locale" content="sk_SK"/>',
                     '<meta property="og:locale" content="en_US"/>'),
                    ('content="Všetky športové weby sveta na jednom mieste — prehľadný rozcestník overených liniek."',
                     'content="All the world\'s sports websites in one place — a clear directory of verified links."'),
                    ('<span class="wm-w">ŠPORTOVÉ</span><span class="wm-r">LINKY</span>',
                     '<span class="wm-w">SPORT</span><span class="wm-r">LINKING</span>'),
                    ('Naviguj sa cez kategórie', 'Navigate through the categories'),
                    ('🔍  Hľadaj kdekoľvek v strome...', '🔍  Search anywhere in the tree...'),
                    ('aria-label="Hľadaj v strome"', 'aria-label="Search the tree"'),
                    ('aria-label="Heslo"', 'aria-label="Password"'),
                    ('aria-label="Zobraziť ďalšie linky"', 'aria-label="Show more links"'),
                    ('animation:pulse 1.5s infinite"></span>\n      Aktuálne',
                     'animation:pulse 1.5s infinite"></span>\n      Live this week'),
                    ('© 2026 · Všetky športové weby sveta na jednom mieste<br>\n  Databáza liniek je chránená právom na ochranu databáz (smernica 96/9/ES). Jej kopírovanie alebo systematické vyťažovanie bez súhlasu prevádzkovateľa je zakázané.',
                     '© 2026 · All the world\'s sports websites in one place<br>\n  The link database is protected by database rights (Directive 96/9/EC). Copying or systematic extraction without the operator\'s consent is prohibited.'),
                    ('https://sportlinky.goatcounter.com/count',
                     f'https://{GOAT}.goatcounter.com/count'),
                    ('e84242', ACCENT[1:]),       # akcent
                    ('ef5a5a', ACCENT_TEXT[1:]),  # akcent pre text (kontrast)
                    ('d63333', ACCENT_STRONG[1:]),  # silný akcent pod bielym textom
                    ('#c03030', ACCENT_HOVER),    # tmavší odtieň akcentu
                    ('232,66,66', '66,135,232'),  # rgba() odtiene akcentu
                ):
                    html = html.replace(a, b)
            # Titulok domova s počtom webov (bod 5 previerky). Až PO EN náhradách,
            # aby prepísal akýkoľvek pôvodný titulok; og:title ostáva krátky.
            html, n_t = re.subn(r"<title>[^<]*</title>",
                                lambda m: f"<title>{escape(home_title(n_links))}</title>", html, count=1)
            if not n_t:
                raise SystemExit("CHYBA: v index.html chýba <title>...</title>.")
            print(f"titulok domova: {home_title(n_links)} (liniek: {n_links})")
            if BASE_URL and "<!--OG_DYNAMIC-->" in html:
                og_dyn = (f'<meta property="og:url" content="{BASE_URL}/"/>\n'
                          f'<meta property="og:image" content="{BASE_URL}/og-image.png"/>')
                html = html.replace("<!--OG_DYNAMIC-->", og_dyn, 1)
            # Appke povedz, kde je koreň webu — podľa neho vyrába pekné adresy.
            # Oba weby (sportlinky.sk, sportlinking.com) dnes bežia v koreni "/",
            # ale keby web bežal v podpriečinku (napr. github.io/nazov-repa/),
            # bez tohto by appka vyrábala adresy od koreňa domény a odkazy by
            # nikam neviedli.
            marker = 'let SITE_ROOT = "";'
            if marker not in html:
                raise SystemExit(
                    "CHYBA: v index.html chýba riadok 'let SITE_ROOT = \"\";' — "
                    "appka nevie, kde je koreň webu. Skontroluj index.html.")
            html = html.replace(marker, f'let SITE_ROOT = "{SITE_ABS_ROOT}";')

            # bod 16: index.html musí mať TÚ ISTÚ CSP ako statické stránky (CSP vyššie)
            if CSP_META not in html:
                raise SystemExit(
                    "CHYBA: index.html nemá rovnakú Content-Security-Policy ako generator.py "
                    "(CSP). Oprav riadok <meta http-equiv=\"Content-Security-Policy\"> tak, "
                    "aby boli zhodné.")

            # Favicon ako súbory s cestou od koreňa webu (bod 7 previerky).
            fav_marker = "<!--FAVICONS-->"
            if fav_marker not in html:
                raise SystemExit(
                    "CHYBA: v index.html chýba značka <!--FAVICONS--> — "
                    "favicon by sa nezobrazil. Skontroluj index.html.")
            html = html.replace(fav_marker, FAVICON_LINKS, 1)

            # Appke povedz verziu dát — sťahuje si data.json?v=NNN, takže si ho
            # prehliadač smie odložiť do pamäte a pri novej verzii si stiahne
            # čerstvý. Bez toho by sa data.json ťahal pri každom otvorení stránky.
            ver_marker = 'let DATA_VER = "";'
            if ver_marker not in html:
                raise SystemExit(
                    "CHYBA: v index.html chýba riadok 'let DATA_VER = \"\";' — "
                    "appka by data.json sťahovala stále odznova. Skontroluj index.html.")
            html = html.replace(ver_marker, f'let DATA_VER = "{DATA_VER}";')

            # ŠTARTOVACÍ BALÍK (od 2.10.2026) — viď build_boot(). Starší index.html
            # bez markera sa správa ako doteraz (čaká na celé dáta).
            boot_marker = 'let BOOT = null;'
            if boot_marker in html:
                boot_js = json.dumps(build_boot(data, children), ensure_ascii=False,
                                     separators=(",", ":")).replace("</", "<\\/")
                html = html.replace(boot_marker, "let BOOT = " + boot_js + ";", 1)
            # AKTUÁLNE PRIAMO V HTML (od 2.10.2026) — viď inject_aktualne().
            html = inject_aktualne(html, data.get("aktualne") or [])
            # DLAŽDICE DOMOVA + IKONKY ŠPORTOV PRIAMO V HTML (od 2.11.2026) — viď inject_home().
            html = inject_home(html, children, all_paths)
            # (preload data.json ZRUŠENÝ 2.10.2026 večer: na pomalej sieti súperil
            # o pásmo s bannerom, ktorý je na mobile najväčším prvkom — LCP 9,4 s.
            # Appka si dáta sťahuje až po udalosti load, s nízkou prioritou.)

            # 404.html NAJPRV a BEZ hreflangu — poistka pre adresy bez vlastnej
            # statickej stránky (rozostavané sekcie, preklepy). GitHub Pages ju
            # vráti pre ĽUBOVOĽNÚ neznámu adresu, takže hreflang ukazujúci na
            # domov by tam bol zavádzajúci.
            with open(os.path.join(out, "404.html"), "w", encoding="utf-8") as f:
                f.write(html)

            # domovská stránka: canonical + hreflang trio SK ↔ EN (x-default = EN,
            # priorita anglického trhu). 404.html je už zapísaný — canonical nemá.
            if BASE_URL:
                sk_home = f"{BASE_URL}/" if LANG == "sk" else f"{ALT_BASE_URL}/"
                en_home = f"{ALT_BASE_URL}/" if LANG == "sk" else f"{BASE_URL}/"
                # bod 23: štruktúrované dáta WebSite (názov webu pre Google), bez SearchAction
                website_ld = json.dumps({"@context": "https://schema.org", "@type": "WebSite",
                                         "name": site_title, "url": f"{BASE_URL}/",
                                         "inLanguage": LANG}, ensure_ascii=False).replace("</", "<\\/")
                html = html.replace("</title>", (
                    "</title>\n"
                    f'<link rel="canonical" href="{BASE_URL}/"/>\n'
                    f'<link rel="alternate" hreflang="sk" href="{sk_home}"/>\n'
                    f'<link rel="alternate" hreflang="en" href="{en_home}"/>\n'
                    f'<link rel="alternate" hreflang="x-default" href="{en_home}"/>\n'
                    f'<script type="application/ld+json">{website_ld}</script>'), 1)

            with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as f:
                f.write(html)
        with open(os.path.join(out, "favicon.svg"), "w", encoding="utf-8") as f:
            f.write(FAVICON_SVG)
        # dáta: data-full.json (celé, len pre admina) + data.json (odľahčený
        # pre návštevníkov) — viď lite_data(). data.json sa už nekopíruje.
        write_json(os.path.join(out, "data-full.json"), data)
        write_json(os.path.join(out, "data.json"), lite_data(data))
        for fname in ("og-image.png",
                      "banner-sportlinking-1.png", "banner-sportlinking-2.png",
                      "favicon.ico", "apple-touch-icon.png"):
            if os.path.exists(fname):
                shutil.copy(fname, os.path.join(out, fname))
            elif fname in ("favicon.ico", "apple-touch-icon.png"):
                print(f"UPOZORNENIE: chýba súbor {fname} — na webe nebude (build pokračuje).")
        # IKONKY WEBOV (bod 15, 2.11.2026): ikony/*.png (sťahuje ikony.py pri
        # builde) → _site/ikony/. Appka ich načíta od koreňa webu (/ikony/<host>.png).
        # stav.json sa na web nekopíruje (je len pre ikony.py).
        if os.path.isdir("ikony"):
            os.makedirs(os.path.join(out, "ikony"), exist_ok=True)
            n_ikon = 0
            for fname in os.listdir("ikony"):
                if fname.endswith(".png"):
                    shutil.copy(os.path.join("ikony", fname), os.path.join(out, "ikony", fname))
                    n_ikon += 1
            print(f"Ikonky webov: {n_ikon} súborov -> {out}/ikony/")
        else:
            print("UPOZORNENIE: priečinok ikony/ chýba — ikonky webov na webe nebudú (build pokračuje).")
        # VLAJKY KRAJÍN (3.11.2026): vlajky/<veľkosť>/<kód>.png (sťahuje vlajky.py
        # pri builde) → _site/vlajky/. Vlajku, ktorá chýba (nestiahla sa), nahradí
        # priehľadný obrázok 1×1 px — návštevník neuvidí rozbitý obrázok ani 404,
        # len prázdne miesto. Ďalší build ju skúsi stiahnuť znova.
        kopiruj_vlajky(data, out)

    print(f"Hotovo: {count} stránok priečinkov -> {out}/ (preskočených prázdnych: {len(skipped)})")
    if not BASE_URL:
        print("UPOZORNENIE: BASE_URL nie je nastavená — sitemap/canonical budú relatívne (na GitHube sa doplní automaticky).")


if __name__ == "__main__":
    main()
