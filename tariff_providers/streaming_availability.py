# tariff_providers/streaming_availability.py
def fetch_service_tariffs(service: str, country: str = "ru") -> list[dict]:
    """
    Возвращаем цену из своего словаря, без запроса к RapidAPI.
    Этого достаточно, чтобы демонстрировать сравнение тарифов.
    """
    manual_prices = {
        "netflix": 599,
        "disney": 449,
        "prime":   399
    }
    price = manual_prices.get(service.lower())
    if price is None:
        return []                     # сервиса нет в таблице

    return [{
        "name": f"{service.capitalize()} стандарт",
        "price": price,
        "period": "monthly"
    }]
