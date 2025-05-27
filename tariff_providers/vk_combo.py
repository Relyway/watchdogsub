import re, requests
from bs4 import BeautifulSoup

URL_PAGE = "https://combo.vk.com"

def fetch_vk_combo() -> list[dict]:
    try:
        html = requests.get(URL, timeout=10).text
        text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
        m = re.search(r"(\d+)\s*₽/мес", text)
        price = int(m.group(1)) if m else 299
    except Exception as e:
        print("[tariff] vk_combo:", e)
        price = 299

    return [{"name": "VK Combo", "price": price, "period": "monthly", "url": URL_PAGE}]
