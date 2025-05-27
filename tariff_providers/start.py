import re, requests
from bs4 import BeautifulSoup

URL_PAGE = "https://start.ru/about/subscription"

def fetch_start() -> list[dict]:
    try:
        html = requests.get(URL, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)
        # ищем «599 ₽» или «599₽»
        m = re.search(r"(\d[\d\s]*)\s*₽", text)
        price = int(m.group(1).replace(" ", "")) if m else 599
    except Exception as e:
        print("[tariff] start:", e)
        price = 599

    return [{"name": "START", "price": price, "period": "monthly", "url": URL_PAGE}]
