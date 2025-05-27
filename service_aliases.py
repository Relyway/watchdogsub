# service_aliases.py
"""Словарь синонимов + функция canon(). Используется bot.py и парсерами."""

ALIASES = {
    # Yandex Plus
    "яндекс плюс": "Yandex Plus",
    "yandex плюс": "Yandex Plus",
    "yandex plus": "Yandex Plus",
    "yandex+": "Yandex Plus",
    "plus": "Yandex Plus",
    "плюс": "Yandex Plus",
    "яндекс": "Yandex Plus",
    "Yandex": "Yandex Plus",
    "яндкс": "Yandex Plus",

    # VK Combo / Музыка
    "vk combo": "VK Combo",
    "вк комбо": "VK Combo",
    "вк музыка": "VK Combo",
    "combo": "VK Combo",
    "vk music": "VK Combo",
    "вк": "VK Combo",
    "VK": "VK Combo",
    "vk": "VK Combo",
    "вК": "VK Combo",
    "Вконтакте": "VK Combo",
    "ВКонтакте": "VK Combo",

    # Okko
    "окко": "Okko",
    "око": "Okko",
    "Око": "Okko",
    "Окко": "Okko",

    # Ivi
    "ivi.ru": "Ivi",
    "ivi": "Ivi",
    "иви": "Ivi",
    "Ивви": "Ivi",

    # Megogo
    "мегого": "Megogo",
    "megogo": "Megogo",
    "Мегого": "Megogo",

    # Netflix (пускай останется)
    "нетфликс": "Netflix",
    "netflix": "Netflix",


    # --- START ---
    "старт":    "START",
    "start":    "START",

    # --- Wink ---
    "wink":         "Wink",
    "винг":         "Wink",
    "винк":         "Wink",
    "ростелеком":   "Wink",

    # --- more.tv ---
    "more.tv":  "more_tv",
    "moretv":   "more_tv",
    "море тв":  "more_tv",
    "море":     "more_tv",

    # --- Premier ---
    "premier":      "Premier",
    "премьер":      "Premier",
    "premier one":  "Premier",

    # --- Kinopoisk HD ---
    "кинопоиск": "Kinopoisk",
    "kino": "Kinopoisk",
    "kinopoisk": "Kinopoisk",
    "кино": "Kinopoisk",
    "kp": "Kinopoisk",
    "kinopoisk hd": "Kinopoisk",
    "кинопоиск hd": "Kinopoisk",


    # (оставляем старые алиасы неизменными …)
}
# внизу файла — нормализация, чтобы ключи точно lower
ALIASES = {k.lower(): v for k, v in ALIASES.items()}
def canon(name: str) -> str:
    return ALIASES.get(name.lower(), name.strip())
