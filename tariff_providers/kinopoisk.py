# tariff_providers/kinopoisk.py
import re, requests
from bs4 import BeautifulSoup

URL_PAGE = "https://www.kinopoisk.ru/special/kinopoisk_hd/"         # официальный лендинг HD-подписки

def fetch_kinopoisk() -> list[dict]:
    """Возвращает [{name, price, period}] для Кинопоиска HD."""
    try:
        html  = requests.get(URL, timeout=10).text
        text  = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
        # ищем «299 ₽» / «299₽» / «299руб»
        m = re.search(r"(\d[\d\s]*)\s*₽", text)
        price = int(m.group(1).replace(" ", "")) if m else 299
    except Exception as e:
        print("[tariff] kinopoisk:", e)
        price = 299            # ← ненулевая заглушка


    return [{"name": "Кинопоиск HD", "price": price, "period": "monthly", "url": URL_PAGE}]
