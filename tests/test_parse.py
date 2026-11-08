import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from ottos_aktionen import parse, page_url, total_count

HTML = """
<html><body><div class="grid">
 <span>201 Produkte</span>
 <div class="tile"><a href="/de/x/coca-cola-24x33/p/113851" title="Coca-Cola Original Taste 24 x 33 cl"><img alt="Coca-Cola"></a>
   <div><span>-50%</span><span>CHF 12.95</span><span>statt CHF 26.00</span></div></div>
 <div class="tile"><a href="/de/x/lipton/p/200001">Lipton Ice Tea Peach 24 x 33 cl</a>
   <div><span>CHF 13.95</span><span>Konkurrenzpreis CHF 23.85</span></div></div>
 <div class="tile"><a href="/de/x/valser/p/300001"><img alt="Valser Prickelnd 6 x 1.5 l"></a>
   <div><span>CHF 6.95</span></div></div>
 <div class="tile"><a href="/de/x/sauna/p/400001" title="Infrarotsauna OHIO">x</a>
   <div>CHF 2'999.00 Konkurrenzpreis CHF 5'999.00 -50%</div></div>
</div></body></html>
"""

def test_parse():
    a = {x.name: x for x in parse(HTML, "https://www.ottos.ch/de/c/m_10300")}
    assert len(a) == 4
    c = a["Coca-Cola Original Taste 24 x 33 cl"]
    assert (c.preis, c.vergleich, c.rabatt, c.vergleich_art) == (12.95, 26.0, 50, "Statt")
    l = a["Lipton Ice Tea Peach 24 x 33 cl"]
    assert (l.preis, l.vergleich, l.rabatt) == (13.95, 23.85, 42)
    v = a["Valser Prickelnd 6 x 1.5 l"]
    assert (v.preis, v.vergleich, v.rabatt) == (6.95, None, None)
    s = a["Infrarotsauna OHIO"]
    assert (s.preis, s.vergleich, s.rabatt) == (2999.0, 5999.0, 50)
    assert c.url == "https://www.ottos.ch/de/x/coca-cola-24x33/p/113851"

def test_page_url():
    b = "https://www.ottos.ch/de/c/m_10300"
    assert page_url(b, 1) == b
    assert page_url(b, 3) == b + "?currentPage=2"

def test_total():
    assert total_count(HTML) == 201
