#!/usr/bin/env python3
"""TEST DENNÉHO LIMITU OBNOVY IKONIEK (ikony.py, Zadanie 36 — bod 21a previerky 3).

Beží BEZ SIETE: sťahovanie (spracuj_host) sa nahradí falošným, ktoré hneď vráti
malý obrázok. Všetko sa deje v dočasnom priečinku — repozitár (ikony/, data.json)
sa nemení.

Overí:
  a) prvý build v deň X obnoví najviac --obnov starých ikoniek a zapíše počítadlo
     do stav.json (kľúč "obnova" = {"den": X, "obnovene": N}),
  b) ďalší build v ten istý deň už NEOBNOVÍ nič (limit je na deň, nie na build),
  c) nové weby (bez výsledku v stav.json) sa stiahnu VŽDY, aj keď je denný limit vyčerpaný,
  d) v nový deň (iný "den" v počítadle) sa počíta znova od nuly,
  e) pokazené počítadlo (nie slovník) = počíta sa od nuly (build nespadne),
  f) den_bratislava(): 23:30 UTC v zime je už ďalší deň v Bratislave.

Spustenie:  python testy/test_ikony.py     (výsledok: ✅ / ❌, exit 0 / 1)
"""
import datetime as dt
import json
import os
import sys
import tempfile

KOREN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOREN)
import ikony  # noqa: E402

chyby = []


def over(podmienka, text):
    print(("✅ " if podmienka else "❌ ") + text)
    if not podmienka:
        chyby.append(text)


def falosne_stiahnutie(host, predosly, brzda, timeout, koniec):
    return {"vysledok": "ok", "zdroj": "test", "data": ikony.png_1x1_priehladny()}


def spusti(priecinok, obnov):
    """Jeden „build": ikony.py v priečinku `priecinok`, vráti zoznam stiahnutých hostov."""
    stiahnute = []

    def sledovane(host, *a):
        stiahnute.append(host)
        return falosne_stiahnutie(host, *a)

    povodne = ikony.spracuj_host, sys.argv, os.getcwd()
    ikony.spracuj_host = sledovane
    sys.argv = ["ikony.py", "--data", "data.json", "--dir", "ikony", "--obnov", str(obnov), "--naraz", "2"]
    try:
        os.chdir(priecinok)
        ikony.main()
    finally:
        ikony.spracuj_host, sys.argv = povodne[0], povodne[1]
        os.chdir(povodne[2])
    return stiahnute


def main():
    with tempfile.TemporaryDirectory() as tmp:
        # facebook.com a instagram.com pridáva ikony.py vždy (EXTRA_HOSTS) — aj tie sú „staré"
        stare = [f"stary{i}.sk" for i in range(10)] + list(ikony.EXTRA_HOSTS)
        data = {"nodes": [{"id": f"n{i}", "type": "link", "url": f"https://{h}/"}
                          for i, h in enumerate(stare)]}
        with open(os.path.join(tmp, "data.json"), "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.makedirs(os.path.join(tmp, "ikony"))
        davno = (dt.date.today() - dt.timedelta(days=60)).isoformat()
        stav = {h: {"datum": davno, "vysledok": "ok", "zdroj": "google"} for h in stare}
        cesta_stavu = os.path.join(tmp, "ikony", "stav.json")
        ikony.uloz_stav(cesta_stavu, stav)
        dnes = ikony.den_bratislava()

        def pocitadlo():
            with open(cesta_stavu, encoding="utf-8") as f:
                return json.load(f).get("obnova")

        def nastav_pocitadlo(hodnota):
            with open(cesta_stavu, encoding="utf-8") as f:
                d = json.load(f)
            d["obnova"] = hodnota
            with open(cesta_stavu, "w", encoding="utf-8") as f:
                json.dump(d, f)

        # a) prvý build: obnoví 3 z 10 starých
        s1 = spusti(tmp, 3)
        over(len(s1) == 3, f"a) prvý build obnovil 3 ikonky (obnovil {len(s1)})")
        o = pocitadlo()
        over(o == {"den": dnes, "obnovene": 3}, f"a) stav.json → obnova = {{den: {dnes}, obnovene: 3}} (je {o})")
        with open(cesta_stavu, encoding="utf-8") as f:
            hosty = json.load(f).get("hosty", {})
        over(len(hosty) == len(stare), f"a) zoznam webov v stav.json ostal celý ({len(hosty)})")

        # b) druhý build v ten istý deň: nič
        s2 = spusti(tmp, 3)
        over(len(s2) == 0, f"b) druhý build v ten istý deň neobnovil nič (obnovil {len(s2)})")

        # c) nový web sa stiahne aj pri vyčerpanom limite
        data["nodes"].append({"id": "nový", "type": "link", "url": "https://novy-web.sk/"})
        with open(os.path.join(tmp, "data.json"), "w", encoding="utf-8") as f:
            json.dump(data, f)
        s3 = spusti(tmp, 3)
        over(s3 == ["novy-web.sk"], f"c) nový web sa stiahol aj pri vyčerpanom limite ({s3})")
        o = pocitadlo()
        over(o.get("obnovene") == 3, f"c) nový web sa do denného limitu nerátal (obnovene = {o.get('obnovene')})")

        # d) nový deň: počíta sa od nuly
        nastav_pocitadlo({"den": "2000-01-01", "obnovene": 300})
        s4 = spusti(tmp, 3)
        over(len(s4) == 3, f"d) v nový deň sa znova obnovili 3 ikonky (obnovil {len(s4)})")

        # e) pokazené počítadlo
        nastav_pocitadlo("toto nie je slovník")
        s5 = spusti(tmp, 2)
        over(len(s5) == 2, f"e) pokazené počítadlo → počíta sa od nuly (obnovil {len(s5)})")

    # f) deň podľa Bratislavy
    utc = dt.datetime(2026, 1, 10, 23, 30, tzinfo=dt.timezone.utc)
    over(ikony.den_bratislava(utc) == "2026-01-11", "f) 10. 1. 23:30 UTC = 11. 1. v Bratislave")
    leto = dt.datetime(2026, 7, 10, 21, 30, tzinfo=dt.timezone.utc)
    over(ikony.den_bratislava(leto) == "2026-07-10", "f) 10. 7. 21:30 UTC = ešte 10. 7. v Bratislave (23:30)")

    print()
    if chyby:
        print(f"❌ TEST IKONIEK ZLYHAL ({len(chyby)} chýb)")
        return 1
    print("✅ Test denného limitu obnovy ikoniek prešiel")
    return 0


if __name__ == "__main__":
    sys.exit(main())
