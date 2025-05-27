import re, requests, bs4

URL_PAGE = "https://more.tv/tariff"

def fetch_moretv() -> list[dict]:
    try:
        text = bs4.BeautifulSoup(requests.get(URL, timeout=10).text, "html.parser").get_text(" ", strip=True)
        price = int(re.search(r"(\d+)\s*₽", text).group(1))
    except Exception as e:
        print("[tariff] more.tv:", e)
        price = 399                 # безопасная заглушка

    return [{"name": "more.tv подписка", "price": price, "period": "monthly", "url": URL_PAGE}]
