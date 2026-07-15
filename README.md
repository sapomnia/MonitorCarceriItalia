# Capienze e presenze nelle carceri italiane

Serie storica settimanale di **posti regolamentari**, **posti non disponibili**
e **detenuti presenti** nei 188 istituti penitenziari italiani, costruita a
partire dalle schede pubblicate dal Ministero della Giustizia su
[giustizia.it](https://www.giustizia.it).

## Come funziona

Ogni **lunedì alle 10:05** (ora italiana) un workflow di GitHub Actions
([`.github/workflows/scraper.yml`](.github/workflows/scraper.yml)) esegue
[`scraper_capienze.py`](scraper_capienze.py), che:

1. legge gli id delle schede da [`istituti.csv`](istituti.csv);
2. scarica da giustizia.it la sezione "Capienza e presenze" di ogni istituto;
3. accoda una riga per istituto a [`storico_capienze.csv`](storico_capienze.csv)
   e ne fa il commit nel repository.

Il workflow si può lanciare anche a mano dalla scheda **Actions → Scraping
settimanale capienze carceri → Run workflow**.

## Il dataset

`storico_capienze.csv`, formato lungo (una riga per istituto per rilevazione):

| Colonna | Contenuto |
|---|---|
| `data_rilevazione` | giorno dello scraping, `AAAA-MM-GG` |
| `data_aggiornamento_sito` | data "dati aggiornati al" dichiarata dal Ministero |
| `id_pagina` | id della scheda su giustizia.it |
| `istituto` | denominazione dell'istituto |
| `posti_regolamentari` | capienza regolamentare |
| `posti_non_disponibili` | posti temporaneamente non disponibili |
| `totale_detenuti` | detenuti presenti |

I valori mancanti sulla fonte restano celle vuote. La capienza effettiva si
ottiene come `posti_regolamentari - posti_non_disponibili`; il tasso di
affollamento come `totale_detenuti / capienza effettiva`.

## Esecuzione locale

```bash
pip install -r requirements.txt
python3 scraper_capienze.py
```

Lo script è idempotente: se il CSV contiene già la rilevazione di oggi, esce
senza scrivere.

## Note

- L'elenco degli istituti è fisso in `istituti.csv`: se il Ministero aggiunge
  una scheda, basta aggiungere il suo id in fondo al file.
- L'url di ogni scheda è `https://www.giustizia.it/giustizia/it/dettaglio_scheda.page?s=<id_pagina>`.
- Fonte dei dati: Ministero della Giustizia — Dipartimento dell'amministrazione
  penitenziaria. I dati sono riportati così come pubblicati.
