#!/usr/bin/env python3
"""
Monitoraggio settimanale di capienze e presenze negli istituti penitenziari.

Legge gli id delle schede da istituti.csv, scarica da giustizia.it i dati di
"Capienza e presenze" (posti regolamentari, posti non disponibili, totale
detenuti) e li accoda a storico_capienze.csv, un CSV in formato lungo che
cresce a ogni esecuzione e permette di ricostruire la serie storica.

Colonne del CSV:
    data_rilevazione        - giorno dello scraping (AAAA-MM-GG, ordinabile)
    data_aggiornamento_sito - data "dati aggiornati al" pubblicata sulla scheda
    id_pagina               - id della scheda su giustizia.it
    istituto                - denominazione dell'istituto
    posti_regolamentari
    posti_non_disponibili
    totale_detenuti

Lo script è idempotente: se per la data odierna esistono già righe nel CSV,
esce senza scrivere nulla (utile perché il workflow GitHub Actions gira due
volte il lunedì per coprire ora legale e ora solare).

Uso locale:
    pip install -r requirements.txt
    python3 scraper_capienze.py
"""

import concurrent.futures as cf
import csv
import datetime
import pathlib
import re
import sys
import time

import requests
from bs4 import BeautifulSoup

HERE = pathlib.Path(__file__).parent
BASE_URL = "https://www.giustizia.it/giustizia/it/dettaglio_scheda.page?s="
FILE_ISTITUTI = HERE / "istituti.csv"
FILE_STORICO = HERE / "storico_capienze.csv"
COLONNE = [
    "data_rilevazione",
    "data_aggiornamento_sito",
    "id_pagina",
    "istituto",
    "posti_regolamentari",
    "posti_non_disponibili",
    "totale_detenuti",
]
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
}


def clean(s):
    return re.sub(r"\s+", " ", s or "").strip()


def to_int(s):
    s = clean(s)
    return int(s) if re.fullmatch(r"\d+", s) else None


def carica_ids():
    with open(FILE_ISTITUTI, encoding="utf-8") as f:
        return [r["id_pagina"] for r in csv.DictReader(f) if r["id_pagina"].strip()]


def scarica(page_id):
    """Scarica una scheda con 4 tentativi. Ritorna (id, html oppure None)."""
    for tentativo in range(4):
        try:
            r = requests.get(BASE_URL + page_id, headers=HEADERS, timeout=60)
            if r.status_code == 200 and "titoloIstituto" in r.text:
                return page_id, r.text
        except requests.RequestException:
            pass
        time.sleep(2 * (tentativo + 1))
    return page_id, None


def estrai(pid, html, oggi):
    """Estrae la riga capienza/presenze da una scheda."""
    soup = BeautifulSoup(html, "html.parser")
    nome = clean(soup.find("h1", class_="titoloIstituto").get_text())

    aggiornamento = ""
    for h2 in soup.find_all("h2"):
        if "dati aggiornati al" in h2.get_text():
            span = h2.find_next("span")
            if span:
                aggiornamento = clean(span.get_text())
            break

    dati = {}
    for h2 in soup.find_all("h2"):
        if clean(h2.get_text()) == "Capienza e presenze":
            tab = h2.find_next("table")
            if tab and tab.find("thead"):
                head = [clean(th.get_text()) for th in tab.find("thead").find_all("th")]
                body = tab.find("tbody") or tab
                tr = body.find("tr")
                if tr:
                    celle = [clean(td.get_text(" ")) for td in tr.find_all("td")]
                    dati = dict(zip(head, celle))
            break

    return {
        "data_rilevazione": oggi,
        "data_aggiornamento_sito": aggiornamento,
        "id_pagina": pid,
        "istituto": nome,
        "posti_regolamentari": to_int(dati.get("posti regolamentari", "")),
        "posti_non_disponibili": to_int(dati.get("posti non disponibili", "")),
        "totale_detenuti": to_int(dati.get("totale detenuti", "")),
    }


def date_gia_presenti():
    if not FILE_STORICO.exists():
        return set()
    with open(FILE_STORICO, encoding="utf-8") as f:
        return {r["data_rilevazione"] for r in csv.DictReader(f)}


def main():
    oggi = datetime.date.today().isoformat()
    if oggi in date_gia_presenti():
        print(f"Rilevazione del {oggi} già presente in {FILE_STORICO.name}: esco.")
        return

    ids = carica_ids()
    print(f"{len(ids)} istituti da scaricare")

    righe, falliti = [], []
    with cf.ThreadPoolExecutor(max_workers=5) as ex:
        for i, (pid, html) in enumerate(ex.map(scarica, ids), 1):
            if html is None:
                falliti.append(pid)
            else:
                righe.append(estrai(pid, html, oggi))
            if i % 25 == 0:
                print(f"  {i}/{len(ids)}")

    if falliti:
        print(f"ATTENZIONE: {len(falliti)} schede non scaricate: {falliti}", file=sys.stderr)
    if not righe:
        print("Nessun dato estratto: non scrivo nulla.", file=sys.stderr)
        sys.exit(1)

    nuovo = not FILE_STORICO.exists()
    with open(FILE_STORICO, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLONNE)
        if nuovo:
            w.writeheader()
        for r in sorted(righe, key=lambda r: r["id_pagina"]):
            w.writerow({k: ("" if v is None else v) for k, v in r.items()})

    print(f"Aggiunte {len(righe)} righe a {FILE_STORICO.name} (data {oggi}).")


if __name__ == "__main__":
    main()
