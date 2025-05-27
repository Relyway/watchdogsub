import re, requests
from bs4 import BeautifulSoup

URL_PAGE = "https://megogo.net/ru/view/subscriptions"

def fetch_megogo() -> list[dict]:
    try:
        soup = BeautifulSoup(requests.get(URL, timeout=10).text, "html.parser")
        txt = soup.get_text(" ", strip=True)
        m = re.search(r"(\d+)\s*₽/мес", txt)
        price = int(m.group(1)) if m else 399
    except Exception as e:
        print("[tariff] megogo:", e)
        price = 399

    return [{"name": "Megogo Light", "price": price, "period": "monthly", "url": URL_PAGE}]
