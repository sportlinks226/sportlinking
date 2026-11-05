#!/usr/bin/env python3
"""IKONKY WEBOV Z VLASTNÉHO WEBU (bod 15 previerky, 2.11.2026).

Ikonky (favicony) webov sa sťahujú LEN tu — pri builde na GitHube (server),
nie v prehliadači návštevníka. Návštevník tak neposiela Googlu ani Yandexu
svoju IP a to, aké weby si prezerá. Web ich servíruje sám zo /ikony/.

Postup pre jeden web (host) = rovnaká logika, akú dovtedy robil prehliadač:
  1. Google s2 (sz=64). Ak je obrázok širší ako 17 px → hotovo („ok", google).
  2. Inak (16 px = pravá malá ikona ALEBO Googlova „zemeguľa") sa spýtame
     Yandexu: 1×1 px → web ikonku NEMÁ („none"); väčší obrázok → „ok", yandex.
  3. Chyba / timeout / 429 = NIE JE výsledok — nič sa nezapíše, skúsi sa to
     v ďalšom builde. Výnimka: ak Yandex zlyhá pri tom istom webe 3 builde po
     sebe, uloží sa Googlov obrázok (tak to robil aj prehliadač, keď Yandex
     nebol dostupný).

Ukladanie (priečinok ikony/):
  ikony/<host>.png  — ikonka; pri „none" maličký priehľadný obrázok 1×1 px
                      (appka ho spozná a ukáže ikonu športu). Súbor pre „none"
                      existuje zámerne: chýbajúci súbor by GitHub Pages nahradil
                      celou stránkou 404.html (~150 KB) — zbytočná záťaž.
  ikony/stav.json   — pre každý host: dátum stiahnutia, výsledok, zdroj;
                      pri chybách počet pokusov; pri webe, ktorý z dát zmizol,
                      dátum „nevideny_od" (kedy ho v dátach prvýkrát nebolo).
                      Navyše kľúč "obnova" = denné počítadlo obnovy:
                      {"den": "2026-11-05", "obnovene": 123} (deň podľa Europe/Bratislava).

Pri každom builde:
  - dotiahne weby, ktoré ešte výsledok nemajú (nové weby, chyby z minula),
  - obnoví LEN ikonky, ktoré majú v stav.json dátum starší ako 30 dní (najstaršie
    prvé, najviac --obnov = 300 ZA DEŇ podľa času v Bratislave — počíta sa
    v stav.json (kľúč "obnova"), súčet za všetky buildy v ten deň; bod 9 previerky 2,
    bod 21a previerky 3). Prvé stiahnutie nových webov limit NEMÁ.
    Keď sa obnovená ikonka nezmenila, súbor .png sa neprepisuje,
  - keď sa v build nič nestiahlo ani nezmenilo, stav.json sa neprepíše (žiadny commit),
  - web, ktorý chýba v dátach 30+ dní, zmaže (súbor aj záznam). Poistka: ak sa
    dáta nepodarilo načítať alebo je webov podozrivo málo (< 80 % počtu
    v stav.json), NEMAŽE NIČ a len vypíše upozornenie.
  - časový limit (predvolene 12 min) — čo nestihne, dotiahne ďalší build.
  - s --git priebežne (každé ~3 min) commitne a pushne, čo už stiahol, aby
    zrušený build (concurrency cancel-in-progress) prácu nestratil.

Skript NIKDY nekončí chybou (exit 0), aby build kvôli ikonkám nespadol.
Iba štandardný Python 3 (bez ďalších knižníc).

Použitie:
  python ikony.py                  # bežný beh (ako na GitHube, bez commitov)
  python ikony.py --git            # na GitHube: priebežné commity a push
  python ikony.py --vzorka 200 --dir _vzorka --vystup vzorka.json
                                   # skúška na vzorke (nič nemaže, necommituje)
"""
import argparse
import datetime as dt
import json
import os
import random
import re
import struct
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from concurrent.futures import ThreadPoolExecutor, FIRST_COMPLETED, wait

# --- rovnaké pravidlá ako v index.html (SOCIAL_FAV, NO_FAVICON_HOSTS) --------
# Pri týchto doménach appka ikonku webu nesťahuje (ukáže ikonu športu / vlajku).
SOCIAL_FAV = re.compile(r'(^|\.)(facebook\.com|fb\.com|instagram\.com|x\.com|twitter\.com|youtube\.com|youtu\.be|tiktok\.com|wikipedia\.org)$')
NO_FAVICON_HOSTS = re.compile(r'(^|\.)(vereine\.oefb\.at|vereine\.fussballoesterreich\.at)$')
# ikonky sietí pre socHtml() (polia fb/ig na dlaždici)
EXTRA_HOSTS = ("facebook.com", "instagram.com")
# Pozn.: položky Aktuálnych (aktualne.json) appka od Zadania 17 kreslí na stránke
# Aktuálne a vo vyhľadávaní s ikonkou webu → ich hosty sa pridávajú tiež
# (hosty_z_aktualnych), aj keď v data.json nie sú.

GOOGLE = "https://www.google.com/s2/favicons?domain={host}&sz=64"
YANDEX = "https://favicon.yandex.net/favicon/{host}"
UA = "Mozilla/5.0 (compatible; sportlinky-ikony/1.0; +https://www.sportlinky.sk/)"

SAFE_HOST = re.compile(r'^[a-z0-9](?:[a-z0-9-]{0,62})(?:\.[a-z0-9-]{1,63})*$')
MAX_BYTES = 512 * 1024
YANDEX_MAX_CHYB = 3      # po toľkých buildoch s nedostupným Yandexom → Googlov obrázok
ZMAZAT_PO_DNOCH = 30
OBNOV_PO_DNOCH = 30      # ikonka staršia ako toľko dní sa stiahne znova (bod 9)
POISTKA_PODIEL = 0.80


# SPOLOČNÉ S vlajky.py (Zadanie 36, bod 44): log(), png_1x1_priehladny() a git_uloz()
# sú v oboch skriptoch takmer rovnaké (git_uloz sa líši len textami v logu).
# Zámerne NIE sú v spoločnom module: skúšobné workflowy (ikony-vzorka.yml,
# vlajky-skuska.yml) sa spúšťajú len pri zmene „svojho“ skriptu. Opravu urob v OBOCH.
def log(*a):
    print(*a, flush=True)


# --- host = presne to, čo v appke vráti new URL(n.url).hostname ----------------
def host_z_url(url):
    """Malé písmená, IDN v punycode (xn--…), bez portu. '' ak sa nedá."""
    try:
        h = urllib.parse.urlsplit((url or "").strip()).hostname or ""
    except ValueError:
        return ""
    h = h.strip().lower()
    if not h:
        return ""
    if any(ord(c) > 127 for c in h):
        try:
            h = ".".join(
                (p.encode("idna").decode("ascii") if any(ord(c) > 127 for c in p) else p)
                for p in h.split("."))
        except UnicodeError:
            return ""
    return h


def hosty_z_aktualnych(cesta="aktualne.json"):
    """Hosty položiek Aktuálnych (aj vypnutých/naplánovaných — ikonka bude pripravená).
    Súbor chýba alebo je pokazený → prázdna množina (nič sa nestane)."""
    hosty = set()
    try:
        with open(cesta, encoding="utf-8") as f:
            d = json.load(f)
        for a in (d.get("items") or []) if isinstance(d, dict) else []:
            h = host_z_url(a.get("url")) if isinstance(a, dict) else ""
            if h and not SOCIAL_FAV.search(h) and not NO_FAVICON_HOSTS.search(h) \
                    and SAFE_HOST.match(h) and len(h) <= 253:
                hosty.add(h)
    except (OSError, ValueError, AttributeError):
        pass
    return hosty


def hosty_z_dat(data):
    hosty = set()
    for n in data.get("nodes") or []:
        if n.get("type") != "link":
            continue
        h = host_z_url(n.get("url"))
        if not h or SOCIAL_FAV.search(h) or NO_FAVICON_HOSTS.search(h):
            continue
        if SAFE_HOST.match(h) and len(h) <= 253:
            hosty.add(h)
    hosty.update(EXTRA_HOSTS)
    return hosty


# --- obrázky ---------------------------------------------------------------------
def rozmer_obrazka(b):
    """(šírka, výška) alebo None, ak dáta nie sú obrázok (PNG/GIF/ICO/JPEG/WEBP/BMP)."""
    try:
        if b[:8] == b"\x89PNG\r\n\x1a\n" and b[12:16] == b"IHDR":
            return struct.unpack(">II", b[16:24])
        if b[:6] in (b"GIF87a", b"GIF89a"):
            return struct.unpack("<HH", b[6:10])
        if b[:4] == b"\x00\x00\x01\x00" and len(b) >= 22:   # ICO: najväčší obrázok
            pocet = struct.unpack("<H", b[4:6])[0]
            best = 0
            for i in range(min(pocet, 64)):
                w = b[6 + 16 * i] or 256
                best = max(best, w)
            return (best, best) if best else None
        if b[:2] == b"BM":
            w, h = struct.unpack("<ii", b[18:26])
            return (abs(w), abs(h))
        if b[:4] == b"RIFF" and b[8:12] == b"WEBP":
            kind = b[12:16]
            if kind == b"VP8 ":
                w, h = struct.unpack("<HH", b[26:30]); return (w & 0x3fff, h & 0x3fff)
            if kind == b"VP8L":
                v = struct.unpack("<I", b[21:25])[0]; return ((v & 0x3fff) + 1, ((v >> 14) & 0x3fff) + 1)
            if kind == b"VP8X":
                return (int.from_bytes(b[24:27], "little") + 1, int.from_bytes(b[27:30], "little") + 1)
        if b[:3] == b"\xff\xd8\xff":
            i = 2
            while i + 9 < len(b):
                if b[i] != 0xFF:
                    i += 1; continue
                m = b[i + 1]
                if m in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    h, w = struct.unpack(">HH", b[i + 5:i + 9]); return (w, h)
                i += 2 + struct.unpack(">H", b[i + 2:i + 4])[0]
    except (struct.error, IndexError):
        return None
    return None


def png_1x1_priehladny():
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00\x00")) + chunk(b"IEND", b""))


PNG_NONE = png_1x1_priehladny()


# --- slušné sťahovanie: obmedzenie súbežnosti + spomalenie pri 429 ---------------
class Brzda:
    """Spoločná brzda pre všetky vlákna. Pri 429 zníži počet súbežných
    požiadaviek na polovicu a všetci chvíľu počkajú; po sérii úspechov
    pomaly zrýchli späť."""

    def __init__(self, max_naraz):
        self.max = max_naraz
        self.limit = max_naraz
        self.bezi = 0
        self.pauza_do = 0.0
        self.cakanie = 15.0
        self.uspechy = 0
        self.c = threading.Condition()

    def vstup(self):
        with self.c:
            while True:
                teraz = time.monotonic()
                if teraz < self.pauza_do:
                    self.c.wait(self.pauza_do - teraz); continue
                if self.bezi >= self.limit:
                    self.c.wait(1.0); continue
                self.bezi += 1
                return

    def odchod(self, bolo_429=False):
        with self.c:
            self.bezi -= 1
            if bolo_429:
                self.limit = max(2, self.limit // 2)
                self.pauza_do = max(self.pauza_do, time.monotonic() + self.cakanie)
                log(f"  429 (príliš veľa požiadaviek) → pauza {self.cakanie:.0f} s, súbežne {self.limit}")
                self.cakanie = min(self.cakanie * 2, 120.0)
                self.uspechy = 0
            else:
                self.uspechy += 1
                if self.uspechy >= 100 and self.limit < self.max:
                    self.limit += 1; self.uspechy = 0
                    self.cakanie = max(15.0, self.cakanie / 2)
            self.c.notify_all()


class Chyba(Exception):
    """Dočasná chyba (timeout, 5xx, 429, nie-obrázok) — výsledok sa nezapíše."""


def stiahni(url, brzda, timeout, koniec):
    """Vráti (bajty, (šírka, výška)). Google pri neznámom webe vráti 404 SO
    zemeguľou — prehliadač ju zobrazil (onload), preto aj tu platí obrázok
    v tele odpovede bez ohľadu na HTTP status (okrem 429 a 5xx)."""
    posledna = None
    for pokus in range(4):
        if time.monotonic() > koniec + 60:
            raise Chyba("čas vypršal")
        brzda.vstup()
        bolo_429 = False
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "image/*,*/*;q=0.5"})
            try:
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    status, body = r.status, r.read(MAX_BYTES + 1)
            except urllib.error.HTTPError as e:
                status = e.code
                try:
                    body = e.read(MAX_BYTES + 1)
                except Exception:
                    body = b""
            if status == 429:
                bolo_429 = True
                posledna = "HTTP 429"
            elif status >= 500:
                posledna = f"HTTP {status}"
            elif len(body) > MAX_BYTES:
                raise Chyba("príliš veľký súbor")
            else:
                rozmer = rozmer_obrazka(body)
                if rozmer:
                    return body, rozmer
                raise Chyba(f"HTTP {status}, nie je obrázok")
        except Chyba:
            raise
        except Exception as e:   # timeout, spojenie, DNS…
            posledna = type(e).__name__
        finally:
            brzda.odchod(bolo_429)
        if pokus < 3:
            time.sleep((1, 3, 6)[pokus] + random.random())
    raise Chyba(posledna or "neznáma chyba")


def spracuj_host(host, predosly, brzda, timeout, koniec):
    """Vráti dict: {'vysledok': 'ok'|'none', 'zdroj':…, 'data': bytes}
    alebo {'chyba': text, 'yandex_chyba': bool}."""
    try:
        g, (gw, _) = stiahni(GOOGLE.format(host=host), brzda, timeout, koniec)
    except Chyba as e:
        return {"chyba": f"google: {e}"}
    if gw > 17:
        return {"vysledok": "ok", "zdroj": "google", "data": g, "sirka": gw}
    try:
        y, (yw, _) = stiahni(YANDEX.format(host=urllib.parse.quote(host)), brzda, timeout, koniec)
    except Chyba as e:
        # Yandex nedostupný: pri opakovanom zlyhaní (3 buildy) ulož Googlov obrázok
        if (predosly or {}).get("yandex_chyby", 0) + 1 >= YANDEX_MAX_CHYB:
            return {"vysledok": "ok", "zdroj": "google", "data": g, "sirka": gw}
        return {"chyba": f"yandex: {e}", "yandex_chyba": True}
    if yw <= 1:
        return {"vysledok": "none", "zdroj": "yandex", "data": PNG_NONE, "sirka": yw}
    return {"vysledok": "ok", "zdroj": "yandex", "data": y, "sirka": yw}


# --- denné počítadlo obnovy (kľúč "obnova" v stav.json) ----------------------------
# --obnov je limit NA DEŇ (predtým na build — pri ~10 buildoch denne až 3 000 obnov).
# Deň sa ráta podľa Bratislavy, aby sa počítadlo nulovalo o našej polnoci.
def den_bratislava(teraz=None):
    """Dátum (YYYY-MM-DD) v Europe/Bratislava pre čas `teraz` (predvolene teraz);
    keby v systéme chýbali časové pásma, použije sa UTC."""
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("Europe/Bratislava")
    except Exception:
        tz = dt.timezone.utc
    teraz = teraz or dt.datetime.now(dt.timezone.utc)
    return teraz.astimezone(tz).date().isoformat()


def nacitaj_obnovu(cesta, den):
    """Koľko ikoniek sa už v deň `den` obnovilo (kľúč "obnova" v stav.json).
    Iný deň, chýbajúci kľúč alebo pokazený súbor = 0."""
    try:
        with open(cesta, encoding="utf-8") as f:
            d = json.load(f).get("obnova")
        if isinstance(d, dict) and d.get("den") == den:
            return max(0, int(d.get("obnovene", 0)))
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return 0


# --- stav.json -------------------------------------------------------------------
def nacitaj_stav(cesta):
    try:
        with open(cesta, encoding="utf-8") as f:
            s = json.load(f)
        if isinstance(s, dict) and isinstance(s.get("hosty"), dict):
            return s["hosty"]
    except FileNotFoundError:
        pass
    except Exception as e:
        log(f"UPOZORNENIE: stav.json sa nedá prečítať ({e}) — začínam nanovo")
    return {}


def uloz_stav(cesta, hosty, obnova=None):
    """Jeden host = jeden riadok, zoradené → malé rozdiely v gite.
    obnova = {"den", "obnovene"} — denné počítadlo obnovy (bod 21a), None = bez neho."""
    riadky = [f"  {json.dumps(h, ensure_ascii=True)}: {json.dumps(hosty[h], ensure_ascii=False, sort_keys=True)}"
              for h in sorted(hosty)]
    obn = f' "obnova": {json.dumps(obnova, sort_keys=True)},\n' if obnova else ""
    obsah = ('{\n "info": "Stav ikoniek webov (ikony.py). Generuje GitHub Actions — ručne nemeniť.",\n'
             + obn + ' "hosty": {\n' + ",\n".join(riadky) + "\n }\n}\n")
    zapis_atomicky(cesta, obsah.encode("utf-8"))


def zapis_atomicky(cesta, bajty):
    # dočasný súbor MIMO priečinka ikony/, aby ho priebežný „git add ikony" nezachytil
    tmp_dir = os.path.join(os.path.dirname(os.path.abspath(cesta)), os.pardir)
    fd, tmp = tempfile.mkstemp(prefix=".ikony-tmp-", dir=tmp_dir)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(bajty)
        os.chmod(tmp, 0o644)
        os.replace(tmp, cesta)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# --- git (priebežné ukladanie na GitHube) -----------------------------------------
def git_uloz(priecinok, sprava):
    def g(*a):
        return subprocess.run(["git", *a], capture_output=True, text=True, timeout=120)
    try:
        g("add", "-A", "--", priecinok)
        if g("diff", "--cached", "--quiet", "--", priecinok).returncode == 0:
            return
        r = g("commit", "-m", sprava + " [skip ci]", "--", priecinok)
        if r.returncode != 0:
            log("  git commit zlyhal:", r.stderr.strip()[:300]); return
        # --autostash: neuložené zmeny v pracovnom priečinku (napr. sitemap-lastmod.json) sa odložia a vrátia, NEcommitujú sa
        r = g("pull", "--rebase", "--autostash", "origin", "main")
        if r.returncode != 0:
            # bod 8: nepokračovať v polorozbitom stave — rebase zrušiť a NEpushovať;
            # commit ostane len lokálne, ikonky sa dorovnajú pri ďalšom builde
            g("rebase", "--abort")
            log("  UPOZORNENIE: git pull --rebase zlyhal — rebase zrušený, NEpushujem "
                f"(dorovná sa pri ďalšom builde): {(r.stderr or r.stdout).strip()[:300]}")
            return
        r = g("push", "origin", "HEAD:main")
        log("  git: uložené do repozitára" if r.returncode == 0
            else f"  git push zlyhal (dorovná sa neskôr): {r.stderr.strip()[:300]}")
    except Exception as e:
        log("  git chyba (nevadí, dorovná sa neskôr):", e)


# --- hlavný beh --------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default="data.json")
    ap.add_argument("--dir", default="ikony")
    ap.add_argument("--limit", type=float, default=12 * 60, help="časový limit v sekundách (12 min)")
    ap.add_argument("--naraz", type=int, default=12, help="max. súbežných požiadaviek")
    ap.add_argument("--timeout", type=float, default=10.0)
    ap.add_argument("--obnov", type=int, default=300,
                    help=f"max. počet ikoniek starších ako {OBNOV_PO_DNOCH} dní, ktoré sa obnovia ZA DEŇ "
                         "(súčet všetkých buildov v ten deň, Europe/Bratislava; nové weby limit nemajú)")
    ap.add_argument("--git", action="store_true", help="priebežne commitovať a pushovať ikony/")
    ap.add_argument("--git-kazdych", type=float, default=180.0, help="sekúnd medzi priebežnými commitmi")
    ap.add_argument("--vzorka", type=int, default=0, help="skúška: len N náhodných hostov (nič nemaže)")
    ap.add_argument("--hosty", default="", help="skúška: hosty oddelené čiarkou (pridajú sa k vzorke)")
    ap.add_argument("--vystup", default="", help="skúška: JSON s výsledkom každého hosta")
    a = ap.parse_args()

    start = time.monotonic()
    koniec = start + a.limit
    dnes = dt.date.today().isoformat()
    os.makedirs(a.dir, exist_ok=True)
    stav_cesta = os.path.join(a.dir, "stav.json")
    stav = nacitaj_stav(stav_cesta)
    # bod 9: obsah stav.json pri poslednom uložení — zapisuje sa len pri skutočnej zmene
    ulozeny_stav = json.dumps(stav, sort_keys=True)
    # bod 21a: denné počítadlo obnovy (kľúč "obnova" v stav.json)
    den_obnovy = den_bratislava()
    obnovene_dnes = nacitaj_obnovu(stav_cesta, den_obnovy)
    ulozene_obnovene = obnovene_dnes

    try:
        with open(a.data, encoding="utf-8") as f:
            data = json.load(f)
        hosty = hosty_z_dat(data)
        if len(hosty) <= len(EXTRA_HOSTS):
            raise ValueError("v dátach nie sú žiadne linky")
        hosty |= hosty_z_aktualnych()   # Zadanie 17: ikonky aj pre položky Aktuálnych
    except Exception as e:
        log(f"UPOZORNENIE: dáta ({a.data}) sa nepodarilo načítať: {e} — ikonky sa nesťahujú, nič sa nemaže.")
        return

    skuska = bool(a.vzorka or a.hosty)
    if skuska:
        vyber = [h.strip().lower() for h in a.hosty.split(",") if h.strip()]
        zvysok = sorted(hosty - set(vyber))
        random.Random(15).shuffle(zvysok)
        vyber += zvysok[:max(0, a.vzorka - len(vyber))]
        na_rad = [(h, "vzorka") for h in vyber]
    else:
        # 1) mazanie webov, ktoré z dát zmizli (s poistkou)
        s_vysledkom = sum(1 for v in stav.values() if v.get("vysledok"))
        poistka = s_vysledkom and len(hosty) < POISTKA_PODIEL * s_vysledkom
        if poistka:
            log(f"UPOZORNENIE: v dátach je len {len(hosty)} webov, v stav.json {s_vysledkom} "
                f"(< {POISTKA_PODIEL:.0%}) — podozrivé, NEMAŽEM NIČ.")
        zmazane = 0
        for h in list(stav):
            v = stav[h]
            if h in hosty:
                v.pop("nevideny_od", None)
                continue
            if poistka:
                continue
            od = v.setdefault("nevideny_od", dnes)
            try:
                dni = (dt.date.fromisoformat(dnes) - dt.date.fromisoformat(od)).days
            except ValueError:
                v["nevideny_od"] = dnes; dni = 0
            if dni >= ZMAZAT_PO_DNOCH:
                try:
                    os.unlink(os.path.join(a.dir, h + ".png"))
                except OSError:
                    pass
                del stav[h]; zmazane += 1
        if zmazane:
            log(f"Zmazané ikonky webov, ktoré v dátach chýbajú {ZMAZAT_PO_DNOCH}+ dní: {zmazane}")

        # 2) poradie: najprv nové weby (bez výsledku), potom najstaršie na obnovu
        nove = sorted(h for h in hosty if not stav.get(h, {}).get("vysledok"))
        # chyby z minula až za úplne novými
        nove.sort(key=lambda h: stav.get(h, {}).get("chyby", 0))
        hotove = [h for h in hosty if stav.get(h, {}).get("vysledok")]
        # bod 9: obnova LEN ikoniek starších ako OBNOV_PO_DNOCH dní, najstaršie prvé;
        # bod 21a: najviac --obnov ZA DEŇ (mínus to, čo už dnes obnovili skoršie buildy)
        hranica = (dt.date.fromisoformat(dnes) - dt.timedelta(days=OBNOV_PO_DNOCH)).isoformat()
        hotove.sort(key=lambda h: (stav[h].get("datum", ""), h))
        zvysok_dnes = max(0, a.obnov - obnovene_dnes)
        stare = [h for h in hotove if stav[h].get("datum", "") < hranica][:zvysok_dnes]
        na_rad = [(h, "nový") for h in nove] + [(h, "obnova") for h in stare]
        log(f"Webov v dátach: {len(hosty)} | v stav.json s výsledkom: {len(hotove)} | "
            f"na stiahnutie nových: {len(nove)} | na obnovu: {len(stare)} "
            f"(dnes {den_obnovy} už obnovených {obnovene_dnes} z denného limitu {a.obnov})")

    brzda = Brzda(a.naraz)
    pocty = {"ok": 0, "none": 0, "chyba": 0}
    vysledky = {}
    posledny_git = time.monotonic()
    zmena_od_ulozenia = False

    def priebezne_uloz(final=False):
        nonlocal posledny_git, zmena_od_ulozenia, ulozeny_stav, ulozene_obnovene
        if skuska:
            return
        # bod 9: stav.json sa prepíše len pri skutočnej zmene (inak žiadny zbytočný commit)
        # bod 21a: aj zmena denného počítadla obnovy je dôvod na zápis
        teraz = json.dumps(stav, sort_keys=True)
        if teraz != ulozeny_stav or obnovene_dnes != ulozene_obnovene:
            uloz_stav(stav_cesta, stav, {"den": den_obnovy, "obnovene": obnovene_dnes})
            ulozeny_stav = teraz
            ulozene_obnovene = obnovene_dnes
        if a.git and (zmena_od_ulozenia or final):
            git_uloz(a.dir, f"ikony: {pocty['ok']} ok, {pocty['none']} bez ikonky"
                     + (" (priebežne)" if not final else ""))
        zmena_od_ulozenia = False
        posledny_git = time.monotonic()

    def zapis(host, dovod, r):
        nonlocal zmena_od_ulozenia, obnovene_dnes
        vysledky[host] = {k: v for k, v in r.items() if k != "data"}
        if dovod == "obnova" and not skuska:
            obnovene_dnes += 1        # bod 21a: ráta sa každý pokus (aj neúspešný = požiadavka)
        if "chyba" in r:
            pocty["chyba"] += 1
            if skuska:
                return
            v = stav.setdefault(host, {})
            if not v.get("vysledok"):     # pri obnove ostane starý výsledok aj súbor
                v["chyby"] = v.get("chyby", 0) + 1
                v["pokus"] = dnes
            if r.get("yandex_chyba"):
                v["yandex_chyby"] = v.get("yandex_chyby", 0) + 1
            zmena_od_ulozenia = True
            return
        pocty[r["vysledok"]] += 1
        subor = os.path.join(a.dir, host + ".png")
        try:
            with open(subor, "rb") as f:
                rovnaky = f.read() == r["data"]
        except OSError:
            rovnaky = False
        if not rovnaky:           # nezmenený obrázok sa neprepisuje
            zapis_atomicky(subor, r["data"])
        if not skuska:
            stav[host] = {"datum": dnes, "vysledok": r["vysledok"], "zdroj": r["zdroj"]}
            zmena_od_ulozenia = True

    if not na_rad:
        log("Nič na stiahnutie.")
    else:
        log(f"Sťahujem {len(na_rad)} webov (súbežne max. {a.naraz}, limit {a.limit/60:.0f} min)…")
    i = 0
    nestihnute = 0
    posledny_vypis = time.monotonic()
    with ThreadPoolExecutor(max_workers=a.naraz) as ex:
        bezi = {}
        try:
            while i < len(na_rad) or bezi:
                while i < len(na_rad) and len(bezi) < a.naraz * 2:
                    if time.monotonic() > koniec:
                        nestihnute = len(na_rad) - i
                        i = len(na_rad)
                        break
                    h, dovod = na_rad[i]; i += 1
                    f = ex.submit(spracuj_host, h, stav.get(h), brzda, a.timeout, koniec)
                    bezi[f] = (h, dovod)
                if not bezi:
                    break
                hotove_f, _ = wait(list(bezi), timeout=5, return_when=FIRST_COMPLETED)
                for f in hotove_f:
                    h, dovod = bezi.pop(f)
                    try:
                        r = f.result()
                    except Exception as e:
                        r = {"chyba": f"interná: {e}"}
                    try:
                        zapis(h, dovod, r)
                    except Exception as e:
                        log(f"  {h}: zápis zlyhal: {e}")
                if time.monotonic() - posledny_vypis > 60:
                    posledny_vypis = time.monotonic()
                    log(f"  … {sum(pocty.values())}/{len(na_rad)} ({posledny_vypis-start:.0f} s, "
                        f"ok {pocty['ok']}, bez ikonky {pocty['none']}, chyba {pocty['chyba']})")
                if time.monotonic() - posledny_git > a.git_kazdych:
                    priebezne_uloz()
        except KeyboardInterrupt:
            log("Prerušené — ukladám, čo je hotové.")
            for f in bezi:
                f.cancel()
    priebezne_uloz(final=True)

    trvanie = time.monotonic() - start
    log(f"Hotovo za {trvanie:.0f} s: ok {pocty['ok']}, bez ikonky {pocty['none']}, "
        f"chyba (skúsi sa znova) {pocty['chyba']}"
        + (f", nestihnuté (ďalší build) {nestihnute}" if nestihnute else ""))
    if a.vystup:
        with open(a.vystup, "w", encoding="utf-8") as f:
            json.dump({"trvanie_s": round(trvanie, 1), "pocty": pocty, "hosty": vysledky},
                      f, ensure_ascii=False, indent=1, sort_keys=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:   # build kvôli ikonkám NIKDY nesmie spadnúť
        print(f"UPOZORNENIE: ikony.py skončil chybou: {e!r} — build pokračuje.", flush=True)
    sys.exit(0)
