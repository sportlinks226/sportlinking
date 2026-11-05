#!/usr/bin/env python3
"""VLAJKY KRAJÍN Z VLASTNÉHO WEBU (3.11.2026).

Vlajky sa sťahujú z flagcdn.com LEN tu — pri builde na GitHube (server), nie
v prehliadači návštevníka. Web ich potom servíruje sám zo /vlajky/
(podobne ako ikonky webov — ikony.py, /ikony/).

Čo skript robí:
  1. Z data.json zistí všetky kódy vlajok — ikona, ktorá vyzerá ako kód krajiny
     (rovnaké pravidlo ako renderIcon v index.html a FLAG_RE v generator.py):
     „sk", „jp", „gb-eng", „gb-sct"… data.json iba ČÍTA.
  2. Z index.html (renderIcon(…,'24x18')) a generator.py (icon_html(…,"40x30"))
     zistí veľkosti, ktoré web používa, a pridá k nim 2× veľkosti pre ostré
     displeje (iPhone, retina): 24x18 → 48x36 atď.
  3. Stiahne LEN CHÝBAJÚCE súbory do vlajky/<veľkosť>/<kód>.png (vlajky sa
     nemenia → po prvom builde sa už nesťahuje nič, len pri novej krajine).
  4. S --git ich commitne „[skip ci]" a pushne do main (ako ikony.py).

Ak sa vlajka nestiahne, nič sa nedeje: generator.py na jej miesto na webe dá
priehľadný obrázok 1×1 px (žiadny rozbitý obrázok) a ďalší build to skúsi znova.

Skript NIKDY nekončí chybou (exit 0), aby build kvôli vlajkám nespadol.
Iba štandardný Python 3 (bez ďalších knižníc). generator.py z neho preberá
funkcie kody_vlajok(), velkosti() a PNG_NAHRADNIK.

Použitie:
  python vlajky.py                       # stiahne chýbajúce do vlajky/
  python vlajky.py --git                 # na GitHube: + commit a push
  python vlajky.py --dir _skuska --vystup vlajky-skuska.json
                                         # skúška do dočasného priečinka (PR)
"""
import argparse
import concurrent.futures
import json
import os
import re
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zlib

ZDROJ = "https://flagcdn.com/{velkost}/{kod}.png"
PRIECINOK = "vlajky"
# Kód krajiny — ROVNAKÉ pravidlo ako renderIcon v index.html a FLAG_RE v generator.py.
FLAG_RE = re.compile(r"^[a-z]{2}(-[a-z]{2,4})?$")
# Keby sa veľkosti v kóde nenašli (zmena zápisu), použijú sa tieto (stav k 3.11.2026).
ZAKLADNE_VELKOSTI = ("16x12", "20x15", "24x18", "40x30")
PREDVOLENA_VELKOST = "24x18"   # renderIcon/icon_html bez zadanej veľkosti
UA = "Mozilla/5.0 (compatible; sportlinky-build/1.0; +https://sportlinky.sk/)"
TIMEOUT_S = 20
VLAKNA = 8


# SPOLOČNÉ S ikony.py (Zadanie 36, bod 44): log(), png_1x1_priehladny() a git_uloz()
# sú v oboch skriptoch takmer rovnaké (git_uloz sa líši len textami v logu).
# Zámerne NIE sú v spoločnom module: skúšobné workflowy (ikony-vzorka.yml,
# vlajky-skuska.yml) sa spúšťajú len pri zmene „svojho“ skriptu. Opravu urob v OBOCH.
def log(*a):
    print(*a, flush=True)


def png_1x1_priehladny():
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00\x00")) + chunk(b"IEND", b""))


# Náhradník za vlajku, ktorá sa nestiahla (generator.py ho dá na web namiesto nej).
PNG_NAHRADNIK = png_1x1_priehladny()


def kody_vlajok(data):
    """Všetky kódy vlajok z dát (každé pole „icon" kdekoľvek v data.json)."""
    kody = set()

    def prejdi(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "icon" and isinstance(v, str) and FLAG_RE.match(v.strip()):
                    kody.add(v.strip())
                else:
                    prejdi(v)
        elif isinstance(o, list):
            for x in o:
                prejdi(x)
    prejdi(data)
    return sorted(kody)


def dvojnasobna(velkost):
    w, h = velkost.split("x")
    return f"{int(w) * 2}x{int(h) * 2}"


def zakladne_velkosti(koren="."):
    """Veľkosti z volaní renderIcon(…,'WxH') v index.html a icon_html(…,"WxH") v generator.py."""
    najdene = {PREDVOLENA_VELKOST}
    for subor, funkcia in (("index.html", "renderIcon("), ("generator.py", "icon_html(")):
        try:
            with open(os.path.join(koren, subor), encoding="utf-8") as f:
                for riadok in f:
                    if funkcia in riadok:
                        najdene.update(re.findall(r"""['"](\d{1,3}x\d{1,3})['"]""", riadok))
        except OSError:
            pass
    if len(najdene) <= 1:
        najdene.update(ZAKLADNE_VELKOSTI)
    return sorted(najdene, key=lambda s: int(s.split("x")[0]))


def velkosti(koren="."):
    """Základné veľkosti + ich 2× verzie (bez duplicít), zoradené podľa šírky."""
    zakl = zakladne_velkosti(koren)
    return sorted(set(zakl) | {dvojnasobna(v) for v in zakl}, key=lambda s: int(s.split("x")[0]))


def je_png(b):
    return len(b) > 24 and b[:8] == b"\x89PNG\r\n\x1a\n" and b[12:16] == b"IHDR"


def stiahni(kod, velkost):
    """Vráti (bajty PNG, None) alebo (None, popis chyby). 2 pokusy."""
    url = ZDROJ.format(velkost=velkost, kod=kod)
    chyba = "?"
    for pokus in (1, 2):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
                b = r.read()
            if je_png(b):
                return b, None
            chyba = "odpoveď nie je PNG"
        except urllib.error.HTTPError as e:
            chyba = f"HTTP {e.code}"
            if e.code == 404:
                break        # flagcdn takú vlajku nemá — opakovať nemá zmysel
        except Exception as e:
            chyba = f"{type(e).__name__}: {e}"
        if pokus == 1:
            time.sleep(2)
    return None, chyba


def git_uloz(priecinok, sprava):
    def g(*a):
        return subprocess.run(["git", *a], capture_output=True, text=True, timeout=120)
    try:
        g("add", "-A", "--", priecinok)
        if g("diff", "--cached", "--quiet", "--", priecinok).returncode == 0:
            log("git: vo vlajky/ nie je nič nové")
            return
        r = g("commit", "-m", sprava + " [skip ci]", "--", priecinok)
        if r.returncode != 0:
            log("git commit zlyhal:", r.stderr.strip()[:300]); return
        # --autostash: iné neuložené zmeny (napr. ikony/) sa odložia a vrátia, NEcommitujú sa
        r = g("pull", "--rebase", "--autostash", "origin", "main")
        if r.returncode != 0:
            # bod 8: nepokračovať v polorozbitom stave — rebase zrušiť a NEpushovať
            g("rebase", "--abort")
            log("UPOZORNENIE: git pull --rebase zlyhal — rebase zrušený, NEpushujem "
                f"(vlajky sa dorovnajú pri ďalšom builde): {(r.stderr or r.stdout).strip()[:300]}")
            return
        r = g("push", "origin", "HEAD:main")
        log("git: vlajky uložené do repozitára" if r.returncode == 0
            else f"git push zlyhal (dorovná sa pri ďalšom builde): {r.stderr.strip()[:300]}")
    except Exception as e:
        log("git chyba (nevadí, dorovná sa pri ďalšom builde):", e)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default="data.json", help="súbor s dátami (len čítanie)")
    ap.add_argument("--dir", default=PRIECINOK, help="kam ukladať vlajky (predvolene vlajky/)")
    ap.add_argument("--git", action="store_true", help="commitnúť a pushnúť vlajky/")
    ap.add_argument("--limit-s", type=int, default=480, help="časový limit sťahovania v sekundách")
    ap.add_argument("--vystup", default="", help="JSON so súhrnom (pre skúšku)")
    a = ap.parse_args()

    t0 = time.time()
    with open(a.data, encoding="utf-8") as f:
        kody = kody_vlajok(json.load(f))
    vel = velkosti()
    log(f"Vlajky: {len(kody)} kódov × {len(vel)} veľkostí ({', '.join(vel)}) = {len(kody) * len(vel)} súborov")

    chyba_zoznam = [(k, v) for v in vel for k in kody
                    if not os.path.isfile(os.path.join(a.dir, v, k + ".png"))]
    log(f"Už stiahnuté: {len(kody) * len(vel) - len(chyba_zoznam)}, chýba: {len(chyba_zoznam)}")

    ok, zlyhalo, nestihnute = [], {}, []
    if chyba_zoznam:
        with concurrent.futures.ThreadPoolExecutor(VLAKNA) as ex:
            buduce = {}
            for kod, v in chyba_zoznam:
                buduce[ex.submit(lambda k=kod, s=v: (None, "časový limit") if time.time() - t0 > a.limit_s
                                 else stiahni(k, s))] = (kod, v)
            for fut in concurrent.futures.as_completed(buduce):
                kod, v = buduce[fut]
                b, chyba = fut.result()
                if b is None:
                    (nestihnute.append(f"{v}/{kod}") if chyba == "časový limit"
                     else zlyhalo.__setitem__(f"{v}/{kod}", chyba))
                    continue
                cesta = os.path.join(a.dir, v, kod + ".png")
                os.makedirs(os.path.dirname(cesta), exist_ok=True)
                with open(cesta + ".tmp", "wb") as f:
                    f.write(b)
                os.replace(cesta + ".tmp", cesta)
                ok.append(f"{v}/{kod}")

    velkost_kb = sum(os.path.getsize(os.path.join(r, s)) for r, _, ss in os.walk(a.dir) for s in ss) / 1024 \
        if os.path.isdir(a.dir) else 0
    log(f"Stiahnuté teraz: {len(ok)}, nepodarilo sa: {len(zlyhalo)}, nestihnuté (limit): {len(nestihnute)}")
    log(f"Priečinok {a.dir}/: {velkost_kb:.0f} KB, trvanie {time.time() - t0:.1f} s")
    for k, c in sorted(zlyhalo.items()):
        log(f"  CHÝBA {k}: {c}")
    if a.vystup:
        with open(a.vystup, "w", encoding="utf-8") as f:
            json.dump({"kody": len(kody), "velkosti": vel, "spolu": len(kody) * len(vel),
                       "stiahnute": len(ok), "zlyhalo": zlyhalo, "nestihnute": nestihnute,
                       "kb": round(velkost_kb), "trvanie_s": round(time.time() - t0, 1)},
                      f, ensure_ascii=False, indent=1)
    if a.git and ok:
        git_uloz(a.dir, f"vlajky: {len(ok)} nových")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:   # build kvôli vlajkám NIKDY nespadne
        log("vlajky.py: neočakávaná chyba (build pokračuje):", type(e).__name__, e)
    sys.exit(0)
