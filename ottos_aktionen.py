#!/usr/bin/env python3
"""Liest Aktionsartikel einer Kategorie von ottos.ch und gibt sie als Tabelle oder CSV aus.

Beispiele:
    python ottos_aktionen.py                       # Getränke, alle Artikel mit Rabatt
    python ottos_aktionen.py --min-rabatt 30       # nur Rabatt >= 30 %
    python ottos_aktionen.py --csv getraenke.csv   # zusätzlich als CSV speichern
    python ottos_aktionen.py --url https://www.ottos.ch/de/aktionen/supermarkt/c/sale_m_10000

Das Skript liest den HTML-Code direkt (keine KI). Es sucht alle Produktlinks
(Pfad enthält "/p/") und wertet den Text der jeweiligen Produktkachel aus:
erster CHF-Betrag = Preis, "statt"/"Konkurrenzpreis" = Vergleichspreis, "-NN%" = Rabatt.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import time
from dataclasses import dataclass, asdict
from urllib.parse import urljoin, urlparse, urlencode, parse_qsl, urlunparse

import requests
from bs4 import BeautifulSoup, Tag

DEFAULT_URL = "https://www.ottos.ch/de/supermarkt-weine/getraenke/c/m_10300"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept-Language": "de-CH,de;q=0.9",
}

PRODUCT_PATH = re.compile(r"/p/\d+")
AMOUNT = r"(\d{1,3}(?:['’]\d{3})*(?:[.,]\d{2}|\.–|\.-)?)"
CHF = re.compile(r"CHF\s*" + AMOUNT)
COMPARE = re.compile(r"(statt|Konkurrenzpreis)\s*:?\s*(?:CHF\s*)?" + AMOUNT, re.I)
DISCOUNT = re.compile(r"-\s?(\d{1,2})\s?%")
ALKOHOL = re.compile(r"\b(bier|birra|wein|vino|prosecco|champagner|spirituose|whisk(e)?y|gin|vodka|rum|lager)\b", re.I)


@dataclass
class Artikel:
    name: str
    preis: float | None
    vergleich: float | None
    vergleich_art: str
    rabatt: int | None
    url: str


def to_float(s: str | None) -> float | None:
    if not s:
        return None
    s = s.replace("'", "").replace("’", "").replace(",", ".").replace(".–", "").replace(".-", "")
    try:
        return float(s)
    except ValueError:
        return None


def page_url(base: str, page: int) -> str:
    """Seite 1 = ohne Parameter, Seite n = ?currentPage=n-1 (so paginiert ottos.ch)."""
    parts = urlparse(base)
    q = [(k, v) for k, v in parse_qsl(parts.query) if k != "currentPage"]
    if page > 1:
        q.append(("currentPage", str(page - 1)))
    return urlunparse(parts._replace(query=urlencode(q)))


def tile_for(link: Tag) -> Tag:
    """Steigt vom Produktlink nach oben, bis die Kachel einen Preis enthält,
    aber noch keinen zweiten, anderen Produktlink."""
    own = urlparse(link["href"]).path
    node = link
    best = link
    while node.parent is not None and node.parent.name not in ("body", "html"):
        parent = node.parent
        others = {
            urlparse(a["href"]).path
            for a in parent.find_all("a", href=PRODUCT_PATH)
        } - {own}
        if others:
            break
        node = parent
        if CHF.search(node.get_text(" ", strip=True)):
            best = node
    return best


def parse(html: str, base: str) -> list[Artikel]:
    soup = BeautifulSoup(html, "html.parser")
    seen: dict[str, Artikel] = {}
    for a in soup.find_all("a", href=PRODUCT_PATH):
        url = urljoin(base, a["href"]).split("?")[0]
        if url in seen:
            continue
        tile = tile_for(a)
        text = " ".join(tile.get_text(" ", strip=True).split())
        prices = CHF.findall(text)
        if not prices:
            continue
        cmp_m = COMPARE.search(text)
        vergleich = to_float(cmp_m.group(2)) if cmp_m else None
        preis = next((to_float(p) for p in prices if to_float(p) != vergleich), to_float(prices[0]))
        rab_m = DISCOUNT.search(text)
        rabatt = int(rab_m.group(1)) if rab_m else None
        if rabatt is None and preis and vergleich and vergleich > preis:
            rabatt = round((1 - preis / vergleich) * 100)
        name = (a.get("title") or a.get_text(" ", strip=True) or "").strip()
        if not name or CHF.search(name):
            img = tile.find("img", alt=True)
            name = img["alt"].strip() if img else url.rsplit("/", 3)[-3]
        seen[url] = Artikel(
            name=name,
            preis=preis,
            vergleich=vergleich,
            vergleich_art=(cmp_m.group(1).capitalize() if cmp_m else ""),
            rabatt=rabatt,
            url=url,
        )
    return list(seen.values())


def total_count(html: str) -> int | None:
    m = re.search(r"(\d[\d'’]*)\s+Produkte", BeautifulSoup(html, "html.parser").get_text(" "))
    return int(re.sub(r"\D", "", m.group(1))) if m else None


def scrape(base: str, max_pages: int, pause: float, debug: bool) -> list[Artikel]:
    session = requests.Session()
    session.headers.update(HEADERS)
    alle: dict[str, Artikel] = {}
    total = None
    for page in range(1, max_pages + 1):
        url = page_url(base, page)
        r = session.get(url, timeout=30)
        r.raise_for_status()
        if debug:
            with open(f"debug_seite_{page}.html", "w", encoding="utf-8") as f:
                f.write(r.text)
        if total is None:
            total = total_count(r.text)
        neu = [a for a in parse(r.text, url) if a.url not in alle]
        print(f"Seite {page}: {len(neu)} neue Artikel", file=sys.stderr)
        if not neu:
            break
        for a in neu:
            alle[a.url] = a
        if total and len(alle) >= total:
            break
        time.sleep(pause)
    if total and len(alle) != total:
        print(f"Hinweis: {len(alle)} Artikel gelesen, ottos.ch nennt {total}.", file=sys.stderr)
    return list(alle.values())


def fmt(x: float | None) -> str:
    return f"{x:.2f}" if x is not None else ""


def main() -> None:
    p = argparse.ArgumentParser(description="Aktionen von ottos.ch auslesen")
    p.add_argument("--url", default=DEFAULT_URL, help="Kategorie-URL (Standard: Getränke)")
    p.add_argument("--min-rabatt", type=int, default=1, help="Mindestrabatt in %% (0 = auch ohne Rabatt)")
    p.add_argument("--ohne-alkohol", action="store_true", help="Bier, Wein, Spirituosen ausfiltern (nach Name)")
    p.add_argument("--csv", help="Ergebnis zusätzlich als CSV speichern")
    p.add_argument("--max-seiten", type=int, default=50)
    p.add_argument("--pause", type=float, default=2.0, help="Sekunden zwischen Seitenabrufen")
    p.add_argument("--debug", action="store_true", help="HTML jeder Seite als debug_seite_N.html speichern")
    args = p.parse_args()

    artikel = scrape(args.url, args.max_seiten, args.pause, args.debug)
    if args.min_rabatt > 0:
        artikel = [a for a in artikel if (a.rabatt or 0) >= args.min_rabatt]
    if args.ohne_alkohol:
        artikel = [a for a in artikel if not ALKOHOL.search(a.name)]
    artikel.sort(key=lambda a: (-(a.rabatt or 0), a.name))

    print(f"{'Rabatt':>6}  {'Preis':>8}  {'Vergleich':>9}  Produkt")
    for a in artikel:
        rab = f"-{a.rabatt}%" if a.rabatt else ""
        print(f"{rab:>6}  {fmt(a.preis):>8}  {fmt(a.vergleich):>9}  {a.name}")
    print(f"\n{len(artikel)} Artikel", file=sys.stderr)

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(asdict(artikel[0]).keys()) if artikel else ["name"], delimiter=";")
            w.writeheader()
            for a in artikel:
                w.writerow(asdict(a))
        print(f"CSV gespeichert: {args.csv}", file=sys.stderr)


if __name__ == "__main__":
    main()
