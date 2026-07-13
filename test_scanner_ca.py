"""Unit tests for the Canadian-broker additions to scanner.py.

These test the pure-Python logic (location parsing + site/route selection)
without spinning up a browser. Run:  python test_scanner_ca.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import scanner


def test_parse_location():
    cases = [
        # input,                expected (city, province, country)
        ("Toronto, ON",         ("Toronto", "ON", "CA")),
        ("Toronto, Ontario",    ("Toronto", "ON", "CA")),
        ("Toronto, Canada",     ("Toronto", "",   "CA")),
        ("Vancouver, BC",       ("Vancouver", "BC", "CA")),
        ("Quebec, QC",          ("Quebec", "QC", "CA")),
        ("Springfield, IL",     ("Springfield", "IL", "US")),
        ("Springfield",         ("Springfield", "",  "")),
        ("Montreal, Quebec",    ("Montreal", "QC", "CA")),
        ("Halifax, NS",         ("Halifax", "NS", "CA")),
    ]
    for raw, (ec, ep, ecy) in cases:
        got = scanner.parse_location(raw)
        assert got["city"] == ec, f"city mismatch for {raw!r}: {got}"
        assert got["province"] == ep, f"province mismatch for {raw!r}: {got}"
        assert got["country"] == ecy, f"country mismatch for {raw!r}: {got}"
    print("[ok] parse_location:", len(cases), "cases")


def test_routing():
    ca = scanner.parse_location("Toronto, ON")
    assert ca["country"] == "CA"
    assert scanner.CA_PHASE_1_SITES is not scanner.PHASE_1_SITES  # distinct lists

    us = scanner.parse_location("Springfield, IL")
    assert us["country"] == "US"

    # CA list has the two CA brokers; US list has all 19 US brokers.
    ca_names = {s["name"] for s in scanner.CA_PHASE_1_SITES}
    assert "Canada411" in ca_names and "WhitepagesCA" in ca_names
    assert len(scanner.PHASE_1_SITES) >= 19
    print("[ok] routing: CA list =", sorted(ca_names), "| US list size =", len(scanner.PHASE_1_SITES))


def test_ca_url_builders():
    loc = scanner.parse_location("Toronto, ON")
    c411 = [s for s in scanner.CA_PHASE_1_SITES if s["name"] == "Canada411"][0]
    url = c411["url"]("John Smith", loc)
    assert "what=John+Smith" in url, url
    assert "Toronto" in url and "ON" in url, url

    wp = [s for s in scanner.CA_PHASE_1_SITES if s["name"] == "WhitepagesCA"][0]
    url2 = wp["url"]("John Smith", loc)
    assert "name=John+Smith" in url2 and "Toronto" in url2 and "ON" in url2, url2
    print("[ok] CA url builders include city + province:", url[:80], "... |", url2[:80], "...")


def test_discovery_domains_include_ca():
    assert "canada411" in scanner.DISCOVERY_DOMAINS
    assert "whitepages.ca" in scanner.DISCOVERY_DOMAINS
    print("[ok] discovery domains include CA brokers")


if __name__ == "__main__":
    test_parse_location()
    test_routing()
    test_ca_url_builders()
    test_discovery_domains_include_ca()
    print("\nALL PASS")
