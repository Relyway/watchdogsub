import re, requests, bs4
URL_PAGE = "https://premier.one/tariff"

def fetch_premier() -> list[dict]:
    try:
        soup = bs4.BeautifulSoup(requests.get(URL, timeout=10).text, "html.parser")
        text = soup.get_text(" ", strip=True)
        m = re.search(r"Премиум[^₽]+(\d+)\s*₽", text)
        price = int(m.group(1)) if m else 299
    except Exception as e:
        print("[tariff] premier:", e)
        price = 299
    return [{"name": "Premier", "price": price, "period": "monthly", "url": URL_PAGE}]
