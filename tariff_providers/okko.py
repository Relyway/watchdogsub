import re, requests
from bs4 import BeautifulSoup

URL_PAGE = "https://okko.tv/tariffs"

def fetch_okko() -> list[dict]:
    try:
        text = BeautifulSoup(requests.get(URL, timeout=10).text, "html.parser").get_text(" ", strip=True)
        m = re.search(r"(\d+)\s*₽/мес", text)
        price = int(m.group(1)) if m else 549
    except Exception as e:
        print("[tariff] okko:", e)
        price = 549

    return [{"name": "Okko подписка", "price": price, "period": "monthly", "url": URL_PAGE}]
