import re, requests
from bs4 import BeautifulSoup

URL_PAGE = "https://www.ivi.ru/profile/subscriptions"

def fetch_ivi() -> list[dict]:
    try:
        txt = BeautifulSoup(requests.get(URL, timeout=10).text, "html.parser").get_text(" ", strip=True)
        m = re.search(r"(\d+)\s*₽/месяц", txt)
        price = int(m.group(1)) if m else 399
    except Exception as e:
        print("[tariff] ivi:", e)
        price = 399

    return [{"name": "Ivi подписка", "price": price, "period": "monthly", "url": URL_PAGE}]
