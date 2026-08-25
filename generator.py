#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEO generátor pre Športové Linky (sport-strom).

Číta data.json a vygeneruje:
  - statickú HTML stránku pre každý priečinok (napr. hokej/sutaze/index.html)
  - sitemap.xml a robots.txt
  - skopíruje index.html (aplikáciu) a data.json do výstupného priečinka

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
"""

import json
import os
import re
import shutil
import sys
import unicodedata
from datetime import date
from html import escape
from urllib.parse import urlsplit

# ------------------------------------------------------------
# KONFIGURÁCIA
# ------------------------------------------------------------
LANG = os.environ.get("SITE_LANG", "sk")   # "sk" alebo "en"
OUT_PREFIX = os.environ.get("OUT_PREFIX", "")
BASE_URL = os.environ.get("BASE_URL", "").rstrip("/")

# Absolútna cesta ku koreňu webu (podľa nej appka vyrába pekné adresy).
# POZOR: web nemusí byť v koreni domény! Slovenský beží na www.sportlinky.sk
# (koreň "/"), anglický na sportlinks226.github.io/sportlinking/ (koreň
# "/sportlinking/"). Preto sa berie z BASE_URL, ktorú dodá GitHub Actions.
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


def node_name(node: dict) -> str:
    """Názov v aktuálnom jazyku s fallbackom na slovenčinu."""
    if LANG != "sk":
        v = (node.get("name_" + LANG) or "").strip()
        if v:
            return v
    return (node.get("name") or "").strip()


def visible(node: dict) -> bool:
    """en:false skryje uzol (aj s podstromom) na anglickom webe.
    enOnly:true je opak — uzol sa ukáže LEN na anglickom webe."""
    if LANG == "sk":
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

def build_tree(nodes: list):
    """Vráti (children, by_id): mapy pre rýchlu navigáciu stromom."""
    children: dict = {}
    by_id = {}
    for n in nodes:
        by_id[n["id"]] = n
        if not visible(n):
            continue          # en:false — uzol aj celý podstrom mimo EN webu
        children.setdefault(n.get("parentId"), []).append(n)
    for pid, lst in children.items():
        lst.sort(key=lambda x: x.get("order", 0))
        # EN: krajiny vnútri kontinentov podľa anglickej abecedy
        parent = by_id.get(pid)
        if (LANG == "en" and parent is not None and pid not in NO_EN_ALPHA
                and parent.get("name") in CONTINENTS):
            lst.sort(key=lambda x: node_name(x).lower())
    return children, by_id


def folder_paths(children: dict):
    """Priradí každému priečinku URL cestu (zoznam slugov). Rieši duplicitné slugy.

    Prednosť má TRVALÝ slug uložený v dátach (pole "slug" — priraďuje ho
    aplikácia pri vytvorení priečinka / migrácii ensureSlugs). Fallback na
    slugify(názov) je len pre dáta, ktoré migráciou ešte neprešli.
    Algoritmus (poradie podľa order + dedupe) je IDENTICKÝ s ensureSlugs()
    v sport-strom.html — obe strany musia vyrobiť rovnaké adresy.
    """
    paths = {}  # folder id -> [slug, slug, ...]

    def walk(parent_id, prefix):
        used = set()
        for n in children.get(parent_id, []):
            if n.get("type") != "folder":
                continue
            if LANG == "en":
                slug = (n.get("slug_en")
                        or slugify(node_name(n))
                        or "cat-" + slugify(n["id"]))
            else:
                slug = (n.get("slug")
                        or slugify(n.get("name", ""))
                        or "kat-" + slugify(n["id"]))
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
h2{font-size:1.05rem;color:#e84242;margin:26px 0 10px;text-transform:uppercase;letter-spacing:.05em}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:10px}
.card{display:block;background:#182635;border:1px solid #24364a;border-radius:10px;padding:12px 14px;transition:.15s}
.card:hover{border-color:#e84242;transform:translateY(-1px)}
.card .nm{font-weight:600}
.card .ds{font-size:.85rem;color:#8fa3b3;margin-top:3px}
.card .ur{font-size:.78rem;color:#5f7183;margin-top:3px;word-break:break-all}
.appbtn{display:inline-block;background:#e84242;color:#fff;border-radius:8px;padding:10px 18px;font-weight:600;margin-top:30px}
.appbtn:hover{background:#c73535}
.brow{display:flex;gap:10px;flex-wrap:wrap;margin:0 0 16px}
.bslot{width:468px;max-width:100%;height:60px;border-radius:8px;overflow:hidden}
.bslot a{display:block;width:100%;height:100%}
.bslot img{width:100%;height:100%;object-fit:cover;display:block}
@media(max-width:560px){#bslot2{display:none!important}}
.akt{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 20px;align-items:center}
.akt .lbl{color:#e84242;font-weight:600;font-size:.78rem;text-transform:uppercase;letter-spacing:.05em}
.akt a{background:#182635;border:1px solid #24364a;border-radius:20px;padding:6px 12px;font-size:.85rem}
.akt a:hover{border-color:#e84242}
"""
CSS = CSS.replace("#e84242", ACCENT).replace("#c73535", ACCENT_HOVER)

FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E"
           "%3Crect width='64' height='64' rx='12' fill='%230f1923'/%3E"
           "%3Crect y='54' width='64' height='10' fill='%23e84242'/%3E"
           "%3Ctext x='32' y='42' font-family='Arial,sans-serif' font-size='32' font-weight='800'"
           " font-style='italic' text-anchor='middle' fill='%23ffffff'%3ES"
           "%3Ctspan fill='%23e84242'%3EL%3C/tspan%3E%3C/text%3E%3C/svg%3E")
FAVICON = FAVICON.replace("%23e84242", "%23" + ACCENT[1:])

PAGE = """<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{meta_desc}">
<link rel="icon" href="{favicon}">
{canonical}
{og_tags}
<style>{css}</style>
</head>
<body>
<div class="wrap">
<nav class="crumbs">{crumbs}</nav>
<div class="brow"><div id="bslot" class="bslot" hidden></div><div id="bslot2" class="bslot" hidden></div></div>
<div id="akt" class="akt" hidden></div>
<h1><span class="ic">{icon}</span>{name}</h1>
{desc_html}
{folders_html}
{links_html}
<a class="appbtn" id="appbtn" style="display:none" href="{app_href}">{open_app} →</a>
<noscript><style>#appbtn{{display:inline-block!important}}</style></noscript>
<footer>{site_title} — {footer}</footer>
</div>
{dyn_js}
{takeover}
</body>
</html>
"""

# Dynamický JS: banner + Aktuálne z data.json.
# __ANC__ = id priečinkov od koreňa po túto stránku (cielenie bannerov),
# __ROOT__ = relatívna cesta ku koreňu webu, __AKT_LABEL__ = nadpis pásu.
# POZOR: spúšťa sa LEN ako záloha, ak sa nepodarí prevziať appku (viď TAKEOVER).
# Pri úspešnom prevzatí si bannery aj Aktuálne vykreslí appka sama.
DYN_JS = """<script>
function __dyn(){
  var ANC=__ANC__;
  fetch("__DATAURL__").then(function(r){return r.json()}).then(function(d){
    var today=new Date().toISOString().slice(0,10);
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
      el.innerHTML=b.html?b.html:'<a href="'+(b.linkUrl||"#")+'" target="_blank" rel="noopener sponsored"><img src="'+b.imageUrl+'" alt="'+(b.alt||"Reklama")+'"></a>';
      if(b.html){
        var scr=el.querySelectorAll("script");
        for(var i=0;i<scr.length;i++){
          var old=scr[i],s=document.createElement("script");
          for(var j=0;j<old.attributes.length;j++)s.setAttribute(old.attributes[j].name,old.attributes[j].value);
          s.text=old.text||"";
          old.parentNode.replaceChild(s,old);
        }
      }
    }
    showSlot("bslot",1);
    showSlot("bslot2",2);
    var ak=ANC.indexOf("f_ltw")>=0?[]:(d.aktualne||[]).filter(function(a){return !(a.endsAt&&today>a.endsAt)});
    if(ak.length){
      var el2=document.getElementById("akt");
      el2.hidden=false;
      el2.innerHTML='<span class="lbl">__AKT_LABEL__</span>'+ak.map(function(a){
        return '<a href="'+a.url+'" target="_blank" rel="noopener">'+(a.icon?a.icon+" ":"")+(("__LANG__"==="en"&&a.name_en)?a.name_en:a.name)+'</a>';
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

# POZOR: appka sa preberá AŽ KEĎ je isté, že sa dá stiahnuť aj data.json.
# Keby sa prevzala skôr a dáta by neprišli (Googlebot má na vykreslenie krátky
# limit), appka by bežala na starých zapečených dátach, nenašla by cestu z
# adresy a prepísala by ju vyššie — Google to hlásil ako „Stránka s
# presmerovaním" a stránku nezaindexoval. Keď sa dáta nestihnú, zostane
# zobrazená táto statická stránka: má správny obsah aj canonical.
TAKEOVER = """<script>
(function(){
  var btn=document.getElementById("appbtn"), done=false;
  function fallback(){
    if(done) return;
    if(btn) btn.style.display="inline-block";
    try{ __dyn(); }catch(e){}
    var s=document.createElement("script");
    s.async=true; s.src="//gc.zgo.at/count.js";
    s.setAttribute("data-goatcounter","https://__GOAT__.goatcounter.com/count");
    document.body.appendChild(s);
  }
  try{
    Promise.all([
      fetch("__ROOT__index.html").then(function(r){
        if(!r.ok) throw new Error("app");
        return r.text();
      }),
      // dáta sa musia dať stiahnuť, inak appku nepreberáme (viď komentár vyššie);
      // appka si ich potom vezme z pamäte prehliadača, nesťahuje ich druhýkrát
      fetch("__DATAURL__").then(function(r){
        if(!r.ok) throw new Error("data");
        return r.json();
      }).then(function(d){
        if(!d || !d.nodes) throw new Error("data");
      })
    ]).then(function(res){
      var h = res[0];
      if(h.indexOf("let SITE_ROOT =")<0) throw new Error("marker");
      done=true;
      document.open(); document.write(h); document.close();
    }).catch(fallback);
  }catch(e){ fallback(); }
})();
</script>"""


def render_page(node, path, children, by_id, paths, site_title):
    depth = len(path)
    root = "../" * depth
    name = escape(node_name(node))
    icon = escape(node.get("icon", "") or "")
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
            ds = f'<div class="ds">{d}</div>' if d else ""
            cards.append(
                f'<a class="card" href="{slug}/">'
                f'<div class="nm">{escape(f.get("icon","") or "")} {escape(node_name(f))}</div>{ds}</a>'
            )
        fold_cards = f'<h2>{T["folders"]}</h2><div class="grid">' + "".join(cards) + "</div>"

    link_cards = ""
    if links:
        cards = []
        for l in links:
            d = escape(node_desc(l))
            ds = f'<div class="ds">{d}</div>' if d else ""
            url = escape(l.get("url", ""), quote=True)
            host = re.sub(r"^https?://(www\.)?", "", l.get("url", "")).split("/")[0]
            cards.append(
                f'<a class="card" href="{url}" target="_blank" rel="noopener">'
                f'<div class="nm">{escape(l.get("icon","") or "")} {escape(node_name(l))}</div>{ds}'
                f'<div class="ur">{escape(host)}</div></a>'
            )
        link_cards = f'<h2>{T["links"]}</h2><div class="grid">' + "".join(cards) + "</div>"

    # meta popis z NEescapovaného textu (escapuje sa až pri vložení do šablóny,
    # inak by apostrofy skončili dvojito escapované, napr. Europe&amp;#x27;s)
    meta = node_desc(node) or T["meta_folder"].format(
        name=node_name(node), nfold=len(folders), nlink=len(links))
    url_path = "/".join(path) + "/"
    canonical = f'<link rel="canonical" href="{BASE_URL}/{url_path}">' if BASE_URL else ""

    # OG tagy — náhľad pri zdieľaní na sociálnych sieťach
    page_title = f"{name} — {escape(site_title)}"
    og = [f'<meta property="og:title" content="{page_title}">',
          f'<meta property="og:description" content="{escape(meta, quote=True)}">',
          '<meta property="og:type" content="website">']
    if BASE_URL:
        og.append(f'<meta property="og:url" content="{BASE_URL}/{url_path}">')
        og.append(f'<meta property="og:image" content="{BASE_URL}/og-image.png">')
    og_tags = "\n".join(og)

    # dynamický JS: banner + Aktuálne z data.json (ANC = id-čka od koreňa po túto stránku)
    anc_ids = [n["id"] for n in reversed(chain)]
    data_url = f"{root}data.json" + (f"?v={DATA_VER}" if DATA_VER else "")

    dyn_js = (DYN_JS
              .replace("__ANC__", json.dumps(anc_ids))
              .replace("__DATAURL__", data_url)
              .replace("__ROOT__", root)
              .replace("__LANG__", LANG)
              .replace("__AKT_LABEL__", escape(T["aktualne"])))

    takeover = (TAKEOVER
                .replace("__DATAURL__", data_url)
                .replace("__ROOT__", root)
                .replace("__GOAT__", GOAT))

    return PAGE.format(
        lang=LANG,
        title=page_title,
        meta_desc=escape(meta, quote=True),
        favicon=FAVICON,
        canonical=canonical,
        og_tags=og_tags,
        css=CSS,
        crumbs=crumbs_html,
        icon=icon,
        name=name,
        desc_html=f'<p class="desc">{desc}</p>' if desc else "",
        folders_html=fold_cards,
        links_html=link_cards,
        app_href=f'{root}#/{"/".join(path)}',
        open_app=T["open_app"],
        footer=T["footer"],
        site_title=escape(site_title),
        dyn_js=dyn_js,
        takeover=takeover,
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
    has_link = {}

    def check_links(fid):
        kids = children.get(fid, [])
        result = any(k.get("type") == "link" for k in kids)
        for k in kids:
            if k.get("type") == "folder":
                result = check_links(k["id"]) or result
        has_link[fid] = result
        return result

    for top in children.get(None, []):
        if top.get("type") == "folder":
            check_links(top["id"])
    skipped = [fid for fid in paths if not has_link.get(fid)]
    paths = {fid: p for fid, p in paths.items() if has_link.get(fid)}

    os.makedirs(out, exist_ok=True)

    # stránky priečinkov
    count = 0
    for fid, path in paths.items():
        d = os.path.join(out, *path)
        os.makedirs(d, exist_ok=True)
        html = render_page(by_id[fid], path, children, by_id, paths, site_title)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(html)
        count += 1

    # sitemap.xml (len v hlavnej jazykovej vetve)
    if not OUT_PREFIX:
        today = date.today().isoformat()
        urls = [f"{BASE_URL}/"] + [
            f'{BASE_URL}/{"/".join(p)}/' for p in sorted(paths.values())
        ]
        sm = ['<?xml version="1.0" encoding="UTF-8"?>',
              '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
        for u in urls:
            sm.append(f"  <url><loc>{escape(u)}</loc><lastmod>{today}</lastmod></url>")
        sm.append("</urlset>")
        with open(os.path.join(out, "sitemap.xml"), "w", encoding="utf-8") as f:
            f.write("\n".join(sm))

        with open(os.path.join(out, "robots.txt"), "w", encoding="utf-8") as f:
            f.write(f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}/sitemap.xml\n")

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
            html = open("index.html", encoding="utf-8").read()
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
                    ('content="Všetky športové weby sveta na jednom mieste — prehľadný rozcestník overených liniek."',
                     'content="All the world\'s sports websites in one place — a clear directory of verified links."'),
                    ('<span class="wm-w">ŠPORTOVÉ</span><span class="wm-r">LINKY</span>',
                     '<span class="wm-w">SPORT</span><span class="wm-r">LINKING</span>'),
                    ('Naviguj sa cez kategórie', 'Navigate through the categories'),
                    ('🔍  Hľadaj kdekoľvek v strome...', '🔍  Search anywhere in the tree...'),
                    ('animation:pulse 1.5s infinite"></span>\n      Aktuálne',
                     'animation:pulse 1.5s infinite"></span>\n      Live this week'),
                    ('© 2026 · Všetky športové weby sveta na jednom mieste<br>\n  Databáza liniek je chránená právom na ochranu databáz (smernica 96/9/ES). Jej kopírovanie alebo systematické vyťažovanie bez súhlasu prevádzkovateľa je zakázané.',
                     '© 2026 · All the world\'s sports websites in one place<br>\n  The link database is protected by database rights (Directive 96/9/EC). Copying or systematic extraction without the operator\'s consent is prohibited.'),
                    ('https://sportlinky.goatcounter.com/count',
                     f'https://{GOAT}.goatcounter.com/count'),
                    ('e84242', ACCENT[1:]),       # akcent (aj vo favicone %23...)
                    ('#c03030', ACCENT_HOVER),    # tmavší odtieň akcentu
                    ('232,66,66', '66,135,232'),  # rgba() odtiene akcentu
                ):
                    html = html.replace(a, b)
            if BASE_URL and "<!--OG_DYNAMIC-->" in html:
                og_dyn = (f'<meta property="og:url" content="{BASE_URL}/"/>\n'
                          f'<meta property="og:image" content="{BASE_URL}/og-image.png"/>')
                html = html.replace("<!--OG_DYNAMIC-->", og_dyn, 1)
            # Appke povedz, kde je koreň webu — podľa neho vyrába pekné adresy.
            # Bez toho by web v podpriečinku (anglická verzia na
            # sportlinks226.github.io/sportlinking/) vyrábal adresy od koreňa
            # domény a odkazy by nikam neviedli.
            marker = 'let SITE_ROOT = "";'
            if marker not in html:
                raise SystemExit(
                    "CHYBA: v index.html chýba riadok 'let SITE_ROOT = \"\";' — "
                    "appka nevie, kde je koreň webu. Skontroluj index.html.")
            html = html.replace(marker, f'let SITE_ROOT = "{SITE_ABS_ROOT}";')

            # Appke povedz verziu dát — sťahuje si data.json?v=NNN, takže si ho
            # prehliadač smie odložiť do pamäte a pri novej verzii si stiahne
            # čerstvý. Bez toho by sa 3,6 MB ťahalo pri každom otvorení stránky.
            ver_marker = 'let DATA_VER = "";'
            if ver_marker not in html:
                raise SystemExit(
                    "CHYBA: v index.html chýba riadok 'let DATA_VER = \"\";' — "
                    "appka by data.json sťahovala stále odznova. Skontroluj index.html.")
            html = html.replace(ver_marker, f'let DATA_VER = "{DATA_VER}";')

            with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as f:
                f.write(html)

            # 404.html — poistka pre adresy bez vlastnej statickej stránky
            # (napr. rozostavané prázdne sekcie alebo preklep v adrese).
            # GitHub Pages ju vráti namiesto chybovej hlášky; je to tá istá
            # appka, ktorá si zo skutočnej adresy zistí, ktorú sekciu otvoriť.
            with open(os.path.join(out, "404.html"), "w", encoding="utf-8") as f:
                f.write(html)
        for fname in ("data.json", "og-image.png",
                      "banner-sportlinking-1.png", "banner-sportlinking-2.png"):
            if os.path.exists(fname):
                shutil.copy(fname, os.path.join(out, fname))

    print(f"Hotovo: {count} stránok priečinkov -> {out}/ (preskočených prázdnych: {len(skipped)})")
    if not BASE_URL:
        print("UPOZORNENIE: BASE_URL nie je nastavená — sitemap/canonical budú relatívne (na GitHube sa doplní automaticky).")


if __name__ == "__main__":
    main()
