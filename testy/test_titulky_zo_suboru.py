#!/usr/bin/env python3
"""TEST TITULKOV ZO SÚBORU seo-titulky-en.json (Zadanie 61) — bez prehliadača a bez živého webu.

Nič nemení — repozitár ani web. Pracuje v dočasnom priečinku.

  A) Jednotkový test compute_titles() na malom vymyslenom strome (EN):
     - dobrý záznam → titulok presne zo súboru, priečinok nie je v _titleNoSport/_titleNameOnly;
     - zlé name_en (liga sa premenovala) → starý vypočítaný titulok + VAROVANIE s id;
     - dva záznamy s rovnakým titulkom → oba starý titulok + VAROVANIE;
     - titulok zo súboru = vypočítaný titulok inej stránky / titulok domova → starý + VAROVANIE;
     - titulok dlhší ako TITLE_MAX alebo prázdny → starý + VAROVANIE;
     - neexistujúci priečinok → ignoruje sa;
     - titulok zo súboru = skrátený titulok inej stránky (bez športu) → titulok zo súboru sa
       odmietne, skrátený ostáva (žiadne dva rovnaké titulky na webe).
  B) load_title_file(): chýbajúci / prázdny {} / pokazený súbor → {} a 1 riadok upozornenia;
     SK build súbor vôbec nečíta.
  C) Build nanečisto (generator.py v dočasnom priečinku, dáta z data.json repozitára, inak
     data-full.json zo sportlinky.sk):
     - EN s upraveným súborom (1 zlé name_en, 2 rovnaké titulky) → build prejde, tie 3 stránky
       majú starý titulok, VAROVANIA sú vo výpise, ostatné majú titulok zo súboru;
     - EN bez súboru → build prejde, výstup = výstup s prázdnym {} súborom;
     - SK so súborom = SK bez súboru (bajt po bajte, okrem nič) — slovenský web sa nemení.
  Keď súbor seo-titulky-en.json v repozitári nie je, časť C so skutočným súborom sa preskočí.

Spustenie:  python testy/test_titulky_zo_suboru.py
"""
import contextlib
import filecmp
import html
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request

KOREN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUBOR = "seo-titulky-en.json"
SK_MASTER = "https://sportlinky.sk/"
CHYBY = []


def over(podmienka, text):
    print(("  ✅ " if podmienka else "  ❌ ") + text, flush=True)
    if not podmienka:
        CHYBY.append(text)


def nacitaj_generator(lang):
    """Načíta generator.py z repozitára ako modul (LANG sa číta z premennej pri načítaní)."""
    stary = os.environ.get("SITE_LANG")
    os.environ["SITE_LANG"] = lang
    try:
        spec = importlib.util.spec_from_file_location(f"generator_{lang}", os.path.join(KOREN, "generator.py"))
        g = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(g)
    finally:
        if stary is None:
            os.environ.pop("SITE_LANG", None)
        else:
            os.environ["SITE_LANG"] = stary
    return g


# ---------------------------------------------------------------- A) compute_titles
def test_compute_titles():
    print("A) compute_titles() s titulkami zo súboru (vymyslený strom, EN)")
    g = nacitaj_generator("en")
    nodes = [
        {"id": "s", "type": "folder", "name": "Futbal", "name_en": "Football"},
        {"id": "c", "type": "folder", "name": "Kluby", "name_en": "Clubs", "parentId": "s"},
        {"id": "l1", "type": "folder", "name": "Liga A", "name_en": "League A", "parentId": "c"},
        {"id": "l2", "type": "folder", "name": "Liga B", "name_en": "League B", "parentId": "c"},
        {"id": "l3", "type": "folder", "name": "Liga C", "name_en": "League C", "parentId": "c"},
        {"id": "l4", "type": "folder", "name": "Liga D", "name_en": "League D", "parentId": "c"},
        {"id": "l5", "type": "folder", "name": "Liga E", "name_en": "League E", "parentId": "c"},
        {"id": "l6", "type": "folder", "name": "Liga F", "name_en": "League F", "parentId": "c"},
        {"id": "l7", "type": "folder", "name": "Liga G", "name_en": "League G", "parentId": "c"},
        {"id": "l8", "type": "folder", "name": "Liga H", "name_en": "League H", "parentId": "c"},
        # dlhý názov → skrátený titulok bez športu „{názov} — Clubs — Sportlinking"
        {"id": "dl", "type": "folder", "name": "X", "name_en": "Abcdefghij Long League Name Testing",
         "parentId": "c"},
    ]
    by_id = {n["id"]: n for n in nodes}
    ids = [n["id"] for n in nodes]
    site, home = "Sportlinking", "Sportlinking — home"
    zaklad, ns0, no0 = g.compute_titles(ids, by_id, site, home)
    skrateny_dl = zaklad["dl"]
    over(skrateny_dl == "Abcdefghij Long League Name Testing — Clubs — Sportlinking" and "dl" in ns0,
         f"bez súboru: dlhý priečinok má skrátený titulok „{skrateny_dl}“")
    subor = {
        "l1": {"title": "League A – Country Football Clubs & Standings", "name_en": "League A"},   # dobrý
        "l2": {"title": "League B – premenovaná", "name_en": "League B OLD"},                      # b) iný názov
        "l3": {"title": "Rovnaký titulok", "name_en": "League C"},                                   # d) duplicita
        "l4": {"title": "Rovnaký titulok", "name_en": "League D"},                                   # d) duplicita
        "l5": {"title": zaklad["l6"], "name_en": "League E"},                                        # d) = iná stránka
        "l6": {"title": "x" * (g.TITLE_MAX + 1), "name_en": "League F"},                             # c) dlhý
        "l7": {"title": home, "name_en": "League G"},                                                # d) = domov
        "l8": {"title": "", "name_en": "League H"},                                                  # c) prázdny
        "nie": {"title": "Neexistuje", "name_en": "Nope"},                                           # a) nie je
        "c": {"title": skrateny_dl, "name_en": "Clubs"},   # d) = skrátený titulok inej stránky
    }
    stats = {}
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        titles, ns, no = g.compute_titles(ids, by_id, site, home, from_file=subor, file_stats=stats)
    vypis = out.getvalue()
    over(titles["l1"] == subor["l1"]["title"], "dobrý záznam → titulok presne zo súboru")
    over(titles["l2"] == zaklad["l2"] and "l2" in vypis and "VAROVANIE" in vypis,
         "zlé name_en → starý titulok + VAROVANIE s id")
    over(titles["l3"] == zaklad["l3"] and titles["l4"] == zaklad["l4"],
         "dva rovnaké titulky v súbore → oba starý titulok")
    over(titles["l5"] == zaklad["l5"], "titulok zo súboru = titulok inej stránky → starý titulok")
    over(titles["l6"] == zaklad["l6"], f"titulok dlhší ako {g.TITLE_MAX} znakov → starý titulok")
    over(titles["l7"] == zaklad["l7"], "titulok zo súboru = titulok domova → starý titulok")
    over(titles["l8"] == zaklad["l8"], "prázdny titulok → starý titulok")
    over("nie" not in titles, "neexistujúci priečinok sa ignoruje")
    over(titles["c"] == zaklad["c"] and titles["dl"] == skrateny_dl and "dl" in ns,
         "titulok zo súboru = skrátený titulok inej stránky → titulok zo súboru odmietnutý, skrátený ostáva")
    over(stats.get("used") == {"l1": subor["l1"]["title"]}, f"použité: {sorted(stats.get('used', {}))}")
    over((stats["a_chyba"], stats["b_name_en"], stats["c_dlzka"], stats["d_duplicita"]) == (1, 1, 2, 5),
         f"počty odmietnutých a/b/c/d = {stats['a_chyba']}/{stats['b_name_en']}/{stats['c_dlzka']}/{stats['d_duplicita']}")
    for fid in ("l3", "l4", "l5", "l7", "c"):
        over(f"VAROVANIE titulky zo súboru: {fid}" in vypis, f"VAROVANIE pri duplicite má id {fid}")
    over("l1" not in (ns | no), "priečinky s titulkom zo súboru nie sú v TITLE_NOSPORT ani TITLE_NAMEONLY")
    over(len(set(titles.values())) == len(titles) and home not in titles.values(), "všetky titulky jedinečné")
    # bez súboru (None aj {}) = presne ako doteraz
    t2 = g.compute_titles(ids, by_id, site, home, from_file={})
    over(t2 == (zaklad, ns0, no0), "prázdny súbor {} → titulky ako bez súboru")


# ---------------------------------------------------------------- B) load_title_file
def test_load():
    print("B) load_title_file(): chýbajúci / prázdny / pokazený súbor")
    g = nacitaj_generator("en")
    tmp = tempfile.mkdtemp(prefix="test-titulky-")
    try:
        pripady = {"chýbajúci": None, "prázdny {}": "{}", "pokazený JSON": "{nie je json", "zoznam": "[1, 2]"}
        for nazov, obsah in pripady.items():
            p = os.path.join(tmp, nazov.replace(" ", "_") + ".json")
            if obsah is not None:
                with open(p, "w", encoding="utf-8") as f:
                    f.write(obsah)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                d = g.load_title_file(p)
            riadky = [r for r in out.getvalue().splitlines() if r.strip()]
            over(d == {} and len(riadky) == 1 and "UPOZORNENIE" in riadky[0],
                 f"{nazov} → {{}} a 1 riadok upozornenia")
        sk = nacitaj_generator("sk")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            d = sk.load_title_file(os.path.join(KOREN, SUBOR))
        over(d == {} and not out.getvalue(), "SK build súbor nečíta (bez výpisu)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------- C) build nanečisto
def nacitaj_data():
    dj = os.path.join(KOREN, "data.json")
    if os.path.exists(dj):
        with open(dj, encoding="utf-8") as f:
            return f.read(), "data.json z repozitára"
    req = urllib.request.Request(SK_MASTER + "data-full.json", headers={"User-Agent": "sportlinky-test-titulkov"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode("utf-8"), "data-full.json zo sportlinky.sk"


def build(tmp, meno, lang, data_txt, subor_obsah):
    """subor_obsah: None = súbor nie je, inak text súboru seo-titulky-en.json."""
    prac = os.path.join(tmp, meno)
    os.makedirs(prac)
    for f in ("generator.py", "index.html", "sitemap-lastmod.json", "aktualne.json"):
        if os.path.exists(os.path.join(KOREN, f)):
            shutil.copy(os.path.join(KOREN, f), prac)
    with open(os.path.join(prac, "data.json"), "w", encoding="utf-8") as f:
        f.write(data_txt)
    if subor_obsah is not None:
        with open(os.path.join(prac, SUBOR), "w", encoding="utf-8") as f:
            f.write(subor_obsah)
    env = {k: v for k, v in os.environ.items()
           if k not in ("OUT_PREFIX", "AKTUALNE_FILE", "GOAT_CODE", "ALT_BASE_URL")}
    env.update(SITE_LANG=lang, BASE_URL="https://titulky-test.invalid", PYTHONDONTWRITEBYTECODE="1")
    p = subprocess.run([sys.executable, "generator.py", "--out", "site"], cwd=prac, env=env,
                       capture_output=True, text=True, timeout=600)
    return p.returncode, p.stdout + p.stderr, os.path.join(prac, "site")


def titulky_stranok(site):
    """{id priečinka: (<title>, og:title)} zo statických stránok (id z mini-balíka, pole full)."""
    out = {}
    for koren, _, subory in os.walk(site):
        if "index.html" not in subory:
            continue
        t = open(os.path.join(koren, "index.html"), encoding="utf-8").read()
        m = re.search(r'"full":\["([^"]+)"\]', t)
        if not m:
            continue
        ti = re.search(r"<title>([^<]*)</title>", t)
        og = re.search(r'<meta property="og:title" content="([^"]*)"', t)
        out[m.group(1)] = (html.unescape(ti.group(1)) if ti else "", html.unescape(og.group(1)) if og else "")
    return out


def rovnake_priecinky(a, b):
    """Zoznam súborov, ktoré sa v dvoch výstupoch líšia (alebo chýbajú)."""
    rozdiel = []
    for koren, _, subory in os.walk(a):
        for f in subory:
            pa = os.path.join(koren, f)
            pb = os.path.join(b, os.path.relpath(pa, a))
            if not os.path.exists(pb) or not filecmp.cmp(pa, pb, shallow=False):
                rozdiel.append(os.path.relpath(pa, a))
    for koren, _, subory in os.walk(b):
        for f in subory:
            if not os.path.exists(os.path.join(a, os.path.relpath(os.path.join(koren, f), b))):
                rozdiel.append(os.path.relpath(os.path.join(koren, f), b))
    return rozdiel


def test_build():
    print("C) build nanečisto (dočasný priečinok)")
    cesta = os.path.join(KOREN, SUBOR)
    data_txt, zdroj = nacitaj_data()
    print(f"  dáta: {zdroj}")
    tmp = tempfile.mkdtemp(prefix="test-titulky-build-")
    try:
        # EN bez súboru a s prázdnym {} — build prejde, výstup rovnaký
        kod0, vyp0, site0 = build(tmp, "en-bez", "en", data_txt, None)
        over(kod0 == 0, "EN build BEZ súboru prešiel")
        over("UPOZORNENIE" in vyp0 and SUBOR in vyp0, "EN bez súboru: vypísané upozornenie")
        kod1, _, site1 = build(tmp, "en-prazdny", "en", data_txt, "{}")
        over(kod1 == 0, "EN build s prázdnym {} prešiel")
        if kod0 == 0 and kod1 == 0:
            r = rovnake_priecinky(site0, site1)
            over(not r, "EN bez súboru = EN s prázdnym {} (výstup rovnaký)" + (f" — rozdiel: {r[:3]}" if r else ""))
        if not os.path.exists(cesta):
            print(f"  (súbor {SUBOR} v repozitári nie je — zvyšok časti C sa preskočil)")
            return
        with open(cesta, encoding="utf-8") as f:
            povodny = json.load(f)
        ids = sorted(povodny)
        if len(ids) < 4:
            print(f"  (v {SUBOR} je menej ako 4 záznamy — zvyšok časti C sa preskočil)")
            return
        upraveny = json.loads(json.dumps(povodny))
        zle, dup_a, dup_b = ids[0], ids[1], ids[2]
        upraveny[zle]["name_en"] = upraveny[zle]["name_en"] + " (starý názov)"
        upraveny[dup_b]["title"] = upraveny[dup_a]["title"]
        kod2, vyp2, site2 = build(tmp, "en-upraveny", "en", data_txt, json.dumps(upraveny, ensure_ascii=False))
        over(kod2 == 0, "EN build s upraveným súborom (zlé name_en + duplicita) prešiel")
        if kod2 != 0:
            print(vyp2[-1500:])
            return
        bez = titulky_stranok(site0)
        s_upr = titulky_stranok(site2)
        for fid, pr in ((zle, "zlé name_en"), (dup_a, "duplicita"), (dup_b, "duplicita")):
            if fid not in s_upr:
                print(f"  (priečinok {fid} nemá statickú stránku — preskočené)")
                continue
            over(s_upr[fid] == bez[fid], f"{pr}: {fid} má starý titulok „{s_upr[fid][0]}“")
            over(f"VAROVANIE titulky zo súboru: {fid}" in vyp2, f"{pr}: VAROVANIE s id {fid} vo výpise")
        ostatne = [fid for fid in ids[3:] if fid in s_upr]
        zle_ost = [fid for fid in ostatne if s_upr[fid] != (upraveny[fid]["title"],) * 2]
        over(not zle_ost, f"ostatné stránky zo súboru ({len(ostatne)}) majú <title> aj og:title zo súboru"
             + (f" — iné: {zle_ost[:5]}" if zle_ost else ""))
        # skutočný súbor: koľko titulkov sa použilo
        kod3, vyp3, site3 = build(tmp, "en-subor", "en", data_txt, open(cesta, encoding="utf-8").read())
        over(kod3 == 0, "EN build so skutočným súborom prešiel")
        riadok = next((r for r in vyp3.splitlines() if r.startswith("titulky zo súboru")), "")
        print("  " + riadok)
        s3 = titulky_stranok(site3)
        pouzite = [fid for fid in ids if s3.get(fid) == (povodny[fid]["title"],) * 2]
        print(f"  stránok s titulkom zo súboru: {len(pouzite)} z {len(ids)}"
              + (f"; bez: {[f for f in ids if f not in pouzite][:20]}" if len(pouzite) < len(ids) else ""))
        dj = json.load(open(os.path.join(site3, "data.json"), encoding="utf-8"))
        over(dj.get("_titles", {}) and all(dj["_titles"].get(f) == povodny[f]["title"] for f in pouzite),
             f"odľahčený data.json má mapu _titles ({len(dj.get('_titles', {}))} titulkov)")
        dfull = json.load(open(os.path.join(site3, "data-full.json"), encoding="utf-8"))
        over("_titles" not in dfull, "data-full.json mapu _titles nemá")
        # SK: so súborom aj bez neho úplne rovnaký výstup, bez _titles
        kod4, _, sk1 = build(tmp, "sk-subor", "sk", data_txt, open(cesta, encoding="utf-8").read())
        kod5, _, sk0 = build(tmp, "sk-bez", "sk", data_txt, None)
        over(kod4 == 0 and kod5 == 0, "SK buildy prešli")
        if kod4 == 0 and kod5 == 0:
            r = rovnake_priecinky(sk0, sk1)
            over(not r, "SK web so súborom = SK web bez súboru (všetky titulky ako predtým)"
                 + (f" — rozdiel: {r[:3]}" if r else ""))
            dsk = json.load(open(os.path.join(sk1, "data.json"), encoding="utf-8"))
            over("_titles" not in dsk, "SK data.json nemá kľúč _titles")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    for fn in (test_compute_titles, test_load, test_build):
        try:
            fn()
        except Exception as e:
            over(False, f"{fn.__name__}: {type(e).__name__}: {e}")
    print()
    if CHYBY:
        print(f"❌ Test titulkov zo súboru: chýb {len(CHYBY)}")
        for c in CHYBY:
            print("   - " + c)
    else:
        print("✅ Test titulkov zo súboru: všetko v poriadku")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write("## Test titulkov zo súboru (Zadanie 61)\n\n"
                    + ("❌ chyby:\n" + "\n".join(f"- {c}" for c in CHYBY) if CHYBY else "✅ všetko v poriadku")
                    + "\n")
    sys.exit(1 if CHYBY else 0)


if __name__ == "__main__":
    main()
