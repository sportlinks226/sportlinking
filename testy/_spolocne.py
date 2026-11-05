"""SPOLOČNÉ ČASTI testov test_webu.py a test_hlbkovy.py (Zadanie 36, bod 44 previerky 3).

Len to, čo je v oboch testoch NAOZAJ rovnaké. Funkcie s rovnakým menom, ktoré
robia niečo iné (stiahni, spusti, kontrola, zhrnutie…), ostávajú v testoch.
Testy sa spúšťajú ako `python testy/test_webu.py` — Python vtedy hľadá moduly
aj v priečinku testy/, takže `from _spolocne import …` funguje bez ďalších úprav
(lokálne aj vo workflowoch test-webu.yml a test-hlbkovy.yml, SK aj EN repozitár).
"""
import html
import re

UA_PC = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
         "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
X_TEST = {"X-Test": "sportlinky-test"}   # podľa tejto hlavičky sa dá test odlíšiť od návštevníkov

# Štatistiky a reklamy sa v teste BLOKUJÚ — test nesmie robiť falošné návštevy
# ani falošné zobrazenia reklám (ban.tipsport.sk = reklama partnera).
BLOKOVANE = ("goatcounter.com", "zgo.at", "googletagmanager.com",
             "google-analytics.com", "ban.tipsport.sk")


class Zlyhanie(Exception):
    """Kontrola neprešla (text = vysvetlenie pre zhrnutie)."""


def titulok_z_html(text):
    m = re.search(r"<title[^>]*>(.*?)</title>", text, re.S | re.I)
    return html.unescape(m.group(1)).strip() if m else ""


def meta_z_html(text, prop):
    m = re.search(r'<meta[^>]+property="%s"[^>]+content="([^"]*)"' % re.escape(prop), text)
    return html.unescape(m.group(1)).strip() if m else ""
