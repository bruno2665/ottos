# ottos

Liest die Aktionen von [ottos.ch](https://www.ottos.ch) direkt aus dem HTML-Code aus, ohne KI. Die Preise werden also exakt übernommen und nicht abgeschrieben.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Verwendung

```bash
# Getränke (Standard), alle Artikel mit Rabatt, sortiert nach Rabatt
python ottos_aktionen.py

# Nur Getränke mit mindestens 30 % Rabatt, ohne Alkohol, zusätzlich als CSV
python ottos_aktionen.py --min-rabatt 30 --ohne-alkohol --csv getraenke.csv

# Andere Kategorie, z. B. alle Supermarkt-Aktionen
python ottos_aktionen.py --url https://www.ottos.ch/de/aktionen/supermarkt/c/sale_m_10000
```

| Option | Bedeutung |
|---|---|
| `--url` | Kategorie-URL von ottos.ch (Standard: Getränke) |
| `--min-rabatt N` | nur Artikel mit mindestens N % Rabatt (`0` = alle, auch ohne Rabatt) |
| `--ohne-alkohol` | Bier, Wein, Spirituosen anhand des Namens ausfiltern |
| `--csv DATEI` | Ergebnis als CSV speichern (Trennzeichen `;`, öffnet direkt in Excel) |
| `--pause S` | Sekunden zwischen Seitenabrufen (Standard 2, damit ottos.ch nicht blockiert) |
| `--debug` | HTML jeder Seite als `debug_seite_N.html` speichern |

## So funktioniert es

1. Lädt die Kategorieseite und blättert mit `?currentPage=` durch alle Seiten, bis keine neuen Artikel mehr kommen oder die von ottos.ch genannte Gesamtzahl erreicht ist.
2. Sucht alle Produktlinks (Pfad mit `/p/<Nummer>`) und nimmt jeweils die zugehörige Produktkachel.
3. Liest aus dem Kacheltext: Preis (erster CHF-Betrag), Vergleichspreis («statt» oder «Konkurrenzpreis») und Rabatt (`-NN%`). Fehlt der Rabatt, wird er aus den beiden Preisen berechnet.

Die Auswertung orientiert sich am Text und nicht an bestimmten CSS-Klassen, damit sie auch kleinere Änderungen am Seitenlayout übersteht. Wenn ottos.ch die Seite stark umbaut oder die Produkte nur noch per JavaScript nachlädt, findet das Skript nichts mehr. Dann `--debug` verwenden und die gespeicherten HTML-Dateien ansehen.

## Tests

```bash
python -m pytest tests
```
