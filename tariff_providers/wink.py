import re, requests
from bs4 import BeautifulSoup

URL_PAGE = "https://wink.rt.ru/tariffs"

def fetch_wink() -> list[dict]:
    try:
        soup = BeautifulSoup(requests.get(URL, timeout=10).text, "html.parser")
        block = soup.find(string=re.compile("Подписка Wink"))
        text  = block.parent.get_text(" ", strip=True) if block else soup.get_text(" ", strip=True)
        m = re.search(r"(\d+)\s*₽", text)
        price = int(m.group(1)) if m else 249
    except Exception as e:
        print("[tariff] wink:", e)
        price = 249

    return [{"name": "Wink", "price": price, "period": "monthly", "url": URL_PAGE}]
