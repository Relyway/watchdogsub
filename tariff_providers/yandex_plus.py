import re, requests
from bs4 import BeautifulSoup

URL_PAGE = "https://yandex.ru/support/plus/types.html"

def fetch_yandex_plus() -> list[dict]:
    """
    Скачиваем страницу справки Плюса и вытаскиваем цену «399».
    Возвращаем список [{name, price, period}] – формат общий для бота.
    """
    try:
        html = requests.get(URL, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")
        # Берём первый ценник вида «399 ₽»
        match = re.search(r"(\d[\d\s]*)\s*₽", soup.get_text(" ", strip=True))
        price = int(match.group(1).replace(" ", "")) if match else 399
    except Exception as e:
        print("[tariff] yandex_plus:", e)
        price = 399

    return [{"name": "Yandex Plus", "price": price, "period": "monthly", "url": URL_PAGE}]
