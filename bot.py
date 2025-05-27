import telebot
import json
import os
import io

import re
from html import escape

from datetime import datetime
from dateutil.relativedelta import relativedelta
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import timedelta
from firebase_init import init_firebase
db = init_firebase()                  # db теперь — это firebase_admin.db

from service_aliases import canon 
         # вместо старой функции
from tariff_providers import (
    fetch_yandex_plus, fetch_vk_combo,
    fetch_okko, fetch_ivi, fetch_megogo,
    fetch_start, fetch_wink, fetch_moretv,
    fetch_premier, fetch_kinopoisk,       
)

BAD = re.compile(r'[.#$/\[\]]')          # запрещённые символы

MONTHS_RU = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
}


def safe_key(name: str) -> str:
    """safe_key('more.tv') → 'more_tv'  (Firebase-совместимый ключ)"""
    key = BAD.sub('_', name.lower())
    key = re.sub(r'__+', '_', key).strip('_')   # двойные «__» и крайние «_»
    return key or "unnamed"                     # пустой → 'unnamed'





TOKEN = os.environ["TOKEN"]
bot = telebot.TeleBot(TOKEN)




# FIREBASE ветка, в которой будем хранить
FIREBASE_ROOT = db.reference("/subscriptions")
TARIFF_REF = db.reference("/tariffs")
user_states = {}  # хранит, кто сейчас вводит подписку


def escape_markdown_v2(text):
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    for ch in escape_chars:
        text = text.replace(ch, f"\\{ch}")
    return text



def load_subscriptions() -> dict:
    data = FIREBASE_ROOT.get()
    return data or {}

def save_subscriptions(data: dict) -> None:
    FIREBASE_ROOT.set(data)





def update_tariff_db() -> None:
   
    tariffs_raw = {
        "Yandex Plus": fetch_yandex_plus(),
        "VK Combo":    fetch_vk_combo(),
        "Okko":        fetch_okko(),
        "Ivi":         fetch_ivi(),
        "Megogo":      fetch_megogo(),
        "START":       fetch_start(),
        "Wink":        fetch_wink(),
        "more.tv":     fetch_moretv(),
        "Premier":     fetch_premier(),
        "Kinopoisk":   fetch_kinopoisk(),

    }


    tariffs = {
        safe_key(name): offers               
        for name, offers in tariffs_raw.items()
        if offers                         
    }

    # ---------- запись в Firebase ----------
    TARIFF_REF.set(tariffs)
    print("🆙 Tariffs refreshed:", list(tariffs.keys()))




# ===== Команды =====

def auto_update_subscriptions(subs):
    today = datetime.today()
    updated = False

    for sub in subs:
        try:
            pay_date = datetime.strptime(sub["next_payment"], "%d.%m.%Y")
            while pay_date < today:
                period = sub.get("period", "monthly")
                if period == "monthly":
                    pay_date += relativedelta(months=1)
                elif period == "yearly":
                    pay_date += relativedelta(years=1)
                else:
                    break
                updated = True
            sub["next_payment"] = pay_date.strftime("%d.%m.%Y")
            # Добавляем запись в историю
            if "history" not in sub:
                sub["history"] = []

            sub["history"].append({
                "date": pay_date.strftime("%d.%m.%Y"),
                "price": sub.get("price", 0)
            })

        except:
            continue

    return updated






















@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "👋 Привет! Я твой бот-помошник (WatchDogSub) для управления подписками на стриминговые сервисы. Напиши /menu если готов начать.")

@bot.message_handler(commands=['menu'])
def show_menu(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📋 Подписки", "🔔 Уведомления")
    markup.row("📊 Аналитика", "⚙️ Служебное")
    markup.row("📑 Тарифы сервисов")


    bot.send_message(message.chat.id, "📌 Главное меню. Выберите раздел:", reply_markup=markup)



@bot.message_handler(func=lambda msg: msg.text == "📋 Подписки")
def show_subscriptions_menu(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📋 Мои подписки")
    markup.row("➕ Добавить", "📦 Выбрать из списка")
    markup.row("🗑 Удалить", "⏸ Приостановить", "▶️ Возобновить")


    markup.row("🔙 Назад")
    bot.send_message(message.chat.id, "📋 Меню подписок:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text == "🔔 Уведомления")
def show_notify_menu(message):
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        telebot.types.InlineKeyboardButton("📅 Ближайшие оплаты", callback_data="notify_upcoming"),
        telebot.types.InlineKeyboardButton("⏳ Настроить срок", callback_data="change_notify_days"),
        telebot.types.InlineKeyboardButton("❌ Отключить", callback_data="notify_disable"),
        telebot.types.InlineKeyboardButton("✅ Включить", callback_data="notify_enable"),
        telebot.types.InlineKeyboardButton("↩ Назад", callback_data="notify_back")
    )
    bot.send_message(message.chat.id, "🔔 Меню уведомлений. Что настроить?", reply_markup=markup)


@bot.message_handler(func=lambda msg: msg.text == "📊 Аналитика")
def show_analytics_menu(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📊 Анализ", "💡 Рекомендации")
    markup.row("📤 Экспорт подписок", "📁 Импорт подписок")
    markup.row("🧾 История")
    markup.row("🔙 Назад")
    bot.send_message(message.chat.id, "📊 Меню аналитики:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text == "⚙️ Служебное")
def show_service_menu(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("ℹ️ Помощь", "🔍 Проверить напоминания")
    markup.row("🔙 Назад")
    bot.send_message(message.chat.id, "⚙️ Служебное меню:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text == "🔙 Назад")
def handle_back(message):
    show_menu(message)











# ===== Обработка сообщений =====

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = str(message.from_user.id)
    menu_commands = ["📋 Мои подписки", "📊 Анализ", "🔔 Уведомления", "➕ Добавить", "▶️ Возобновить", "⏸ Приостановить", "🗑 Удалить", "💡 Рекомендации", "📤 Экспорт подписок", "🧾 История", "ℹ️ Помощь", "🔍 Проверить напоминания", "📑 Тарифы сервисов", "📁 Импорт подписок"   ]

        # -------- блок редактирования --------
    state = user_states.get(user_id)
    if state and state.startswith("editing_"):
        idx = int(state.split("_")[1])

        parts = message.text.split(',')
        if len(parts) != 2:
            bot.send_message(message.chat.id,
                            "❌ Нужно 2 элемента: Цена, Дата (ДД.ММ.ГГГГ).")
            return

        price_str, date_str = map(str.strip, parts)

        try:
            price = int(price_str)
            if price <= 0:
                raise ValueError
        except ValueError:
            bot.send_message(message.chat.id, "❌ Цена должна быть положительным числом.")
            return

        try:
            pay_date = datetime.strptime(date_str, "%d.%m.%Y")
            if pay_date < datetime.today():
                bot.send_message(message.chat.id, "❌ Дата уже прошла. Укажите будущую.")
                return
        except ValueError:
            bot.send_message(message.chat.id, "❌ Формат даты: 01.05.2025")
            return

        # ---- сохраняем ----
        data = load_subscriptions()
        subs = data.get(user_id, [])
        if 0 <= idx < len(subs):
            subs[idx]["price"]        = price
            subs[idx]["next_payment"] = pay_date.strftime("%d.%m.%Y")
            save_subscriptions(data)
            bot.send_message(message.chat.id, "✅ Подписка обновлена!")
        else:
            bot.send_message(message.chat.id, "⚠️ Подписка не найдена.")

        user_states[user_id] = None
        return


    print("[DEBUG] message.text:", message.text)

    if message.text in menu_commands:
        user_states[user_id] = None  # сбрасываем любое предыдущее состояние

    if user_states.get(user_id) == "waiting_for_subscription":
        if message.text == "↩️ Отменить ввод":
            user_states[user_id] = None
            show_subscriptions_menu(message)
            bot.send_message(message.chat.id, "❎ Ввод отменён. Возвращаюсь в главное меню.")
            return
        else:
            handle_subscription_input(message)
            return

    if message.text == "➕ Добавить":
        user_states[user_id] = "waiting_for_subscription"
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("↩️ Отменить ввод")
        bot.send_message(
            message.chat.id,
            "✍️ Введите подписку в формате:\n"
            "`Название, Цена, Дата оплаты (ДД.ММ.ГГГГ)`\n\n"
            "📌 Пример:\n"
            "```text\nVK Combo, 200, 25.12.2025\n```",
            parse_mode="Markdown",
            reply_markup=markup
        )
        return













    elif message.text == "📋 Мои подписки":
        data = load_subscriptions()
        subs = data.get(user_id, [])

        if auto_update_subscriptions(subs):
            save_subscriptions(data)

        if not subs:
            bot.send_message(message.chat.id, "🔍 У тебя пока нет подписок.")
            return

        lines = []
        for s in subs:
            canon_id = canon(s["service"])
            key      = safe_key(canon_id)
            offers   = (TARIFF_REF.get(key) or [])
            url      = offers[0].get("url") if offers else None

            status   = "🟢" if s.get("active", True) else "🔴"
            title    = escape(s["display"])
            if url:
                safe_url = (
                    url.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .strip()
                )
                service = f'<a href="{safe_url}">{title}</a>'
            else:
                service = title
            price    = s.get("price", "—")
            from urllib.parse import quote


            

            # обработка даты
            raw_date = s.get("next_payment")
            if raw_date:
                try:
                    date_obj = datetime.strptime(raw_date, "%d.%m.%Y")
                    date_str = date_obj.strftime("%d.%m.%Y")
                except:
                    date_str = raw_date
            else:
                date_str = "—"

            lines.append(
                f"{status} {service}\n"
                f"💰 Стоимость: <b>{price}₽</b>\n"
                f"📅 Оплата до: <b>{date_str}</b>\n"
                "──────────────"
            )

        text = "\n".join(lines)
        bot.send_message(
            message.chat.id,
            f"📋 <b>Твои подписки:</b>\n\n{text}",
            parse_mode="HTML"
        )
        return


        



    elif message.text == "📊 Анализ":

        user_id = str(message.from_user.id)
        data = load_subscriptions()
        subs = data.get(user_id, [])

        if not subs:
            bot.send_message(message.chat.id, "📊 У тебя пока нет подписок.")
            return

        total = sum(sub["price"] for sub in subs)
        active_subs = [s for s in subs if s.get("active", True)]
        inactive_subs = [s for s in subs if not s.get("active", True)]
        notify_on = sum(1 for s in subs if s.get("notify", False))
        average = round(total / len(subs), 2) if subs else 0

        notify_days_values = [s.get("notify_days", 0) for s in subs if s.get("notify", False)]
        avg_notify_days = round(sum(notify_days_values) / len(notify_days_values), 1) if notify_days_values else 0

        no_notify = [s for s in subs if not s.get("notify", False)]

        # Ближайшие 3 платежа
        upcoming_list = sorted(
            [s for s in active_subs if s.get("next_payment")],
            key=lambda s: datetime.strptime(s["next_payment"], "%d.%m.%Y")
        )[:3]

        upcoming_text = ""
        for s in upcoming_list:
            try:
                pd = datetime.strptime(s["next_payment"], "%d.%m.%Y")
                pretty_date = f"{pd.day} {MONTHS_RU[pd.month]} {pd.year}"

                upcoming_text += f"• 🔹 {s['service']} — {pretty_date} ({s['price']}₽)\n"
            except:
                continue

        most_expensive = max(subs, key=lambda s: s["price"])

        text = (
            "📊 *Анализ подписок*\n\n"
            "*Общая статистика:*\n"
            f"• 📦 Всего подписок: **{len(subs)}**\n"
            f"• ✅ Активные: **{len(active_subs)}**\n"
            f"• ❌ Приостановленные: **{len(inactive_subs)}**\n"
            f"• 🔔 С уведомлениями: **{notify_on}**\n\n"
            "*Финансовая сводка:*\n"
            f"• 💸 Сумма в месяц: **{total}₽**\n"
            f"• 📈 Средняя стоимость: **{average}₽**\n"
            f"• 👑 Самая дорогая: **{most_expensive['service']}** — **{most_expensive['price']}₽**\n\n"
            "*Ближайшие оплаты:*\n"
            f"{upcoming_text}\n"
            "*Сроки оповещений:*\n"
            f"• 🔔 Средний срок уведомлений: **{avg_notify_days} дня**\n"
            f"• 🔕 Без уведомлений: **{len(no_notify)}** подписки(ок)\n\n"
            "*Рекомендации:*\n"
            "• 🔍 Проверь архив — возможно, есть забытые подписки\n"
            "• 💡 Включи уведомления там, где они отключены\n"
        )

        bot.send_message(message.chat.id, text, parse_mode="Markdown")





    elif message.text == "🔔 Уведомления":
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            telebot.types.InlineKeyboardButton("📅 Ближайшие оплаты", callback_data="notify_upcoming"),
            telebot.types.InlineKeyboardButton("⏳ Настроить срок", callback_data="change_notify_days"),
            telebot.types.InlineKeyboardButton("❌ Отключить", callback_data="notify_disable"),
            telebot.types.InlineKeyboardButton("✅ Включить", callback_data="notify_enable")
        )
        bot.send_message(
            message.chat.id,
            "🔔 Меню уведомлений. Что ты хочешь настроить?",
            reply_markup=markup
    )


    elif message.text == "🗑 Удалить":
        data = load_subscriptions()
        subs = data.get(user_id, [])
        if not subs:
            bot.send_message(message.chat.id, "У тебя нет подписок для удаления.")
            return

        markup = telebot.types.InlineKeyboardMarkup()
        for i, s in enumerate(subs):
            btn_text = f"{s['service']} ({s['next_payment']})"
            markup.add(telebot.types.InlineKeyboardButton(
                text=btn_text,
                callback_data=f"del_{i}"
            ))

        bot.send_message(message.chat.id, "Выбери подписку для удаления:", reply_markup=markup)

    elif message.text == "⏸ Приостановить":
        data = load_subscriptions()
        subs = data.get(user_id, [])
        active_subs = [s for s in subs if s.get("active", True)]
        if not active_subs:
            bot.send_message(message.chat.id, "Нет активных подписок для остановки.")
            return

        markup = telebot.types.InlineKeyboardMarkup()
        for i, s in enumerate(active_subs):
            btn_text = f"{s['service']} ({s['next_payment']})"
            markup.add(telebot.types.InlineKeyboardButton(
                text=btn_text,
                callback_data=f"pause_{i}"
            ))

        bot.send_message(message.chat.id, "Выбери подписку для остановки:", reply_markup=markup)

    elif message.text == "▶️ Возобновить":
        data = load_subscriptions()
        subs = data.get(user_id, [])
        inactive_subs = [s for s in subs if not s.get("active", True)]

        if not inactive_subs:
            bot.send_message(message.chat.id, "У тебя нет остановленных подписок.")
            return

        markup = telebot.types.InlineKeyboardMarkup()
        for i, s in enumerate(inactive_subs):
            btn_text = f"{s['service']} ({s['next_payment']})"
            markup.add(telebot.types.InlineKeyboardButton(
                text=btn_text,
                callback_data=f"resume_{i}"
            ))

        bot.send_message(message.chat.id, "Выбери подписку для возобновления:", reply_markup=markup)


    elif message.text == "💡 Рекомендации":
        user_id = str(message.from_user.id)
        data = load_subscriptions()
        subs = data.get(user_id, [])

        if not subs:
            bot.send_message(message.chat.id, "У тебя пока нет подписок.")
            return

        text = "💡 *Рекомендации по отключению подписок:*\n\n"
        has_recommendations = False

        for s in subs:
            if not s.get("active", True):
                continue

            next_payment = s.get("next_payment")
            if not next_payment:
                continue

            try:
                pay_date = datetime.strptime(next_payment, "%d.%m.%Y")
                days_remaining = (pay_date - datetime.today()).days
                if days_remaining > 60:
                    text += f"🔸 {s['service']} — следующая оплата через {days_remaining} дней. Возможно, стоит отключить.\n"
                    has_recommendations = True
            except:
                continue

        if not has_recommendations:
            text = "✅ Все подписки активны и находятся в пределах 60 дней оплаты."

        bot.send_message(message.chat.id, text, parse_mode="Markdown")


    elif message.text == "ℹ️ Помощь":

        help_text = (
        "🆘 <b>Помощь по боту WatchDogSub</b>\n\n"

        "<b>📋 Управление подписками:</b>\n"
        "•  Добавить подписку вручную (в формате: Название, Цена, Дата)\n"
        "•  Посмотреть список всех подписок\n"
        "• Удалить, Приостановить, Возобновить любую подписку\n"
        "• Все подписки автоматически обновляются по периоду\n\n"

        "<b>🔔 Уведомления:</b>\n"
        "• Включить / отключить напоминания по подпискам\n"
        "• Настроить срок напоминания: за 1, 3, 5 или 7 дней до оплаты\n"
        "• Просмотреть  ближайшие платежи с указанием даты и суммы\n"

        "<b>📊 Аналитика и рекомендации:</b>\n"
        "• Подробная статистика: количество подписок, активных/неактивных, средняя цена\n"
        "• Определение самой дорогой подписки\n"
        "•  Советы по отключению малоиспользуемых или отложенных подписок\n"

        "<b>📄 Экспорт и история:</b>\n"
        "•  Экспорт списка подписок в текстовый файл\n"
        "•  Просмотр истории цен по каждой подписке\n"

        "<b>📑 Сравнение с реальными тарифами:</b>\n"
        "• Сравнение стоимости твоих подписок с актуальными тарифами из открытых источников\n"
        "• Рекомендации, если найдены более дешёвые предложения\n"
        "• Возможность перейти на сайт сервиса через ссылку\n"

        "<b>⚙️ Дополнительно:</b>\n"
        "• Умная автопроверка уведомлений каждый день\n"
        "• Быстрый доступ к основным функциям через кнопки меню\n\n"

        "🔹 <b>Полезные команды:</b>\n"
        "• /start — запустить бота\n"
        "• /menu — открыть главное меню\n"

        "ℹ️ Все действия можно выполнять через кнопки. Просто открой меню и выбери нужный пункт!"
    )
        bot.send_message(message.chat.id, help_text, parse_mode="HTML")


    elif message.text == "🔍 Проверить напоминания":


        data = load_subscriptions()
        today = datetime.today()
        notify_delta = timedelta(days=1)
        user_id = str(message.from_user.id)
        subs = data.get(user_id, [])

        if not subs:
            bot.send_message(message.chat.id, "У тебя пока нет активных подписок.")
            return

        notified = False
        for sub in subs:
            if not sub.get("active", True) or not sub.get("notify", True):
                continue

            try:
                pay_date = datetime.strptime(sub["next_payment"], "%d.%m.%Y")
                if 0 <= (pay_date - today).days <= notify_delta.days:
                    bot.send_message(
                        message.chat.id,
                        f"🔔 Напоминание: завтра оплата за {sub['service']} — {pay_date.strftime('%d.%m.%Y')} на сумму {sub['price']}₽"
                    )
                    notified = True
            except:
                continue

        if not notified:
            bot.send_message(message.chat.id, "✅ Пока нет подписок, требующих уведомлений на завтра.")


    elif message.text == "📄 Экспорт":

        user_id = str(message.from_user.id)
        data = load_subscriptions()
        subs = data.get(user_id, [])

        if not subs:
            bot.send_message(message.chat.id, "❌ У тебя пока нет подписок.")
            return

        filename = f"subscriptions_{user_id}.txt"
        lines = []

        for s in subs:
            status = "Активна" if s.get("active", True) else "Остановлена"
            service = s.get("service", "Без названия")
            price = s.get("price", 0)
            date = s.get("next_payment", "Не указано")
            lines.append(f"{service} — {price}₽, дата: {date}, статус: {status}")

        with open(filename, "w", encoding="utf-8") as f:
            f.write("📄 Список подписок:\n\n")
            f.write("\n".join(lines))

        with open(filename, "rb") as f:
            bot.send_document(message.chat.id, f, caption="📄 Вот ваш список подписок")



    elif message.text ==  "🧾 История":

        user_id = str(message.from_user.id)
        data = load_subscriptions()
        subs = data.get(user_id, [])

        if not subs:
            bot.send_message(message.chat.id, "❌ У тебя пока нет подписок.")
            return

        text = "🧾 *История оплат по подпискам:*\n\n"
        has_history = False

        for s in subs:
            history = s.get("history", [])
            if not history:
                continue

            text += f"🔹 {s['service']}:\n"
            for h in history:
                text += f"• {h['date']} — {h['price']}₽\n"
            text += "\n"
            has_history = True

        if not has_history:
            text = "ℹ️ История пока отсутствует для всех подписок."

        bot.send_message(message.chat.id, text, parse_mode="Markdown")






    # ─── выводим рекомендации ──────────────────────────────────────────
    elif message.text == "📑 Тарифы сервисов":

        tariffs  = TARIFF_REF.get() or {}
        uid      = str(message.from_user.id)
        subs     = load_subscriptions().get(uid, [])

        any_cheaper = False           # flag: найдены ли варианты

        for idx, sub in enumerate(subs):
            if not sub.get("active", True):
                continue

            canon_id = canon(sub["service"])
            offers = tariffs.get(safe_key(canon_id))
            if not offers:
                continue

            cheapest   = min(offers, key=lambda o: o["price"])
            diff       = sub["price"] - cheapest["price"]
            if diff <= 0:
                continue             # дорого не нашлось

            any_cheaper = True
            user_title  = sub.get("display", sub["service"])
            text_line   = (
                f"🔻 {user_title} → тариф «{cheapest['name']}» "
                f"дешевле на {diff} ₽"
            )

            # ── СБОРКА клавиатуры ──────────────────────────────────────
            kb = telebot.types.InlineKeyboardMarkup(row_width=4)

            # ① старые кнопки управления
            kb.add(
                telebot.types.InlineKeyboardButton("✏️", callback_data=f"edit_{idx}"),
                telebot.types.InlineKeyboardButton("🔔", callback_data=f"rem7_{idx}"),
                telebot.types.InlineKeyboardButton("🚫", callback_data=f"cancel_{idx}"),
            )

            # ② ссылка, если есть
            if cheapest.get("url"):
                kb.add(
                    telebot.types.InlineKeyboardButton("🌐 Перейти", url=cheapest["url"])
                )

            # ── вывод сообщения с клавиатурой ─────────────────────────
            bot.send_message(message.chat.id, text_line, reply_markup=kb)

        # если ничего не нашли – пишем прежнее сообщение
        if not any_cheaper:
            bot.send_message(message.chat.id, "✅ У тебя уже самые выгодные тарифы.")


    elif message.text == "📦 Выбрать из списка":
        user_states[user_id] = "selecting_tariff"
        tariffs = TARIFF_REF.get() or {}

        markup = telebot.types.InlineKeyboardMarkup()
        for key, offers in tariffs.items():
            name = offers[0]["name"]
            markup.add(telebot.types.InlineKeyboardButton(name, callback_data=f"choose_tariff_{key}"))

        markup.add(telebot.types.InlineKeyboardButton("↩️ Отменить", callback_data="cancel_tariff_add"))
        bot.send_message(message.chat.id, "📦 Выбери сервис из списка:", reply_markup=markup)
        return

    elif (user_states.get(user_id) or "").startswith("tariff_date_"):

        key = user_states[user_id].split("_", 2)[2]
        offers = TARIFF_REF.get() or {}
        if key not in offers:
            bot.send_message(message.chat.id, "❌ Сервис не найден.")
            user_states[user_id] = None
            return

        try:
            pay_date = datetime.strptime(message.text.strip(), "%d.%m.%Y")
            if pay_date < datetime.today():
                bot.send_message(message.chat.id, "❌ Дата уже прошла.")
                return
        except:
            bot.send_message(message.chat.id, "❌ Формат даты: 01.06.2025")
            return

        offer = offers[key][0]
        subs = load_subscriptions()
        subs.setdefault(user_id, []).append({
            "service": canon(offer["name"]),
            "display": offer["name"],
            "price": offer["price"],
            "next_payment": pay_date.strftime("%d.%m.%Y"),
            "active": True,
            "notify": True,
            "notify_days": 3,
            "period": offer.get("period", "monthly")
        })
        save_subscriptions(subs)
        user_states[user_id] = None
        bot.send_message(message.chat.id, f"✅ Подписка на {offer['name']} добавлена!")
        show_subscriptions_menu(message)
        return


    elif message.text == "📁 Импорт подписок":
        user_states[user_id] = "awaiting_import"
        bot.send_message(message.chat.id, "📎 Пришли файл .json с экспортом подписок. Я добавлю их к текущим.")

    elif message.text == "📤 Экспорт подписок":
        subs = load_subscriptions().get(user_id, [])
        if not subs:
            bot.send_message(message.chat.id, "📂 У тебя нет подписок для экспорта.")
            return

        json_data = json.dumps(subs, indent=2, ensure_ascii=False)
        file = io.BytesIO()
        file.write(json_data.encode("utf-8"))
        file.seek(0)
        bot.send_document(message.chat.id, file, visible_file_name="subscriptions.json")









    else:
            bot.send_message(message.chat.id, "❓ Не понял. Напиши /menu")
    return



























def handle_subscription_input(message):
    user_id = str(message.from_user.id)
    parts = message.text.split(',')
    if len(parts) != 3:
        bot.send_message(message.chat.id, "❌ Неверное количество элементов. Нужно 3: Название, Цена, Дата.\nПример: VK Combo, 200, 25.12.2025")
        return

    service, price_str, date_str = map(str.strip, parts)
        # сохраняем оригинал и канон
    service_input = service              # то, как ввёл пользователь
    canon_name    = canon(service)       # нормализованное имя


    try:
        price = int(price_str)
        if price <= 0:
            raise ValueError
    except ValueError:
        bot.send_message(message.chat.id, "❌ Цена должна быть положительным числом. Пример: 599")
        return

    try:
        pay_date = datetime.strptime(date_str, "%d.%m.%Y")
        if pay_date < datetime.today():
            bot.send_message(message.chat.id, "❌ Дата уже прошла. Укажи дату в будущем.")
            return
    except ValueError:
        bot.send_message(message.chat.id, "❌  Неверный формат даты. Используй `ДД.ММ.ГГГГ`, например: `01.05.2025`", parse_mode="Markdown")
        return

    data = load_subscriptions()
    if user_id not in data:
        data[user_id] = []

    data[user_id].append({
        "service": canon_name,         # каноническое для поиска тарифов
        "display": service_input,      # оригинал для вывода
        "price": price,
        "next_payment": pay_date.strftime("%d.%m.%Y"),
        "active": True,
        "notify": True,
        "notify_days": 1,
        "period": "monthly"
    })

    save_subscriptions(data)
    user_states[user_id] = None

    bot.send_message(message.chat.id, f"✅ Подписка на {service} сохранена!")
    show_menu(message)








@bot.callback_query_handler(func=lambda call: call.data.startswith("del_"))
def callback_delete_subscription(call):
    user_id = str(call.from_user.id)
    index = int(call.data.split("_")[1])

    data = load_subscriptions()
    subs = data.get(user_id, [])

    if index >= len(subs):
        bot.answer_callback_query(call.id, "Ошибка: подписка не найдена.")
        return

    deleted = subs.pop(index)
    save_subscriptions(data)

    bot.edit_message_text(
        f"🗑 Подписка на {deleted['service']} удалена.",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )
@bot.callback_query_handler(func=lambda call: call.data.startswith("pause_"))
def callback_pause_subscription(call):
    user_id = str(call.from_user.id)
    index = int(call.data.split("_")[1])

    data = load_subscriptions()
    active_subs = [s for s in data.get(user_id, []) if s.get("active", True) and s.get("notify", True)]

    if index >= len(active_subs):
        bot.answer_callback_query(call.id, "Ошибка: подписка не найдена.")
        return

    paused = active_subs[index]
    paused["active"] = False
    save_subscriptions(data)

    bot.edit_message_text(
        f"⏸ Подписка на {paused['service']} остановлена.",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("resume_"))
def callback_resume_subscription(call):
    user_id = str(call.from_user.id)
    index = int(call.data.split("_")[1])

    data = load_subscriptions()
    all_subs = data.get(user_id, [])
    inactive_subs = [s for s in all_subs if not s.get("active", True) and s.get("notify", True)]

    if index >= len(inactive_subs):
        bot.answer_callback_query(call.id, "Ошибка: подписка не найдена.")
        return

    resumed = inactive_subs[index]
    resumed["active"] = True
    save_subscriptions(data)

    bot.edit_message_text(
        f"▶️ Подписка на {resumed['service']} возобновлена.",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )





















# === УВЕДОМЛЕНИЯ ===




@bot.callback_query_handler(func=lambda call: call.data == "change_notify_days")
def notify_days_select_subscription(call):
    bot.answer_callback_query(call.id)
    user_id = str(call.from_user.id)
    data = load_subscriptions()
    full_subs = data.get(user_id, [])

    # ⏳ фильтруем только активные подписки с включёнными уведомлениями
    active_notified = [
        (i, s) for i, s in enumerate(full_subs)
        if s.get("active", True) and s.get("notify", True)
    ]

    if not active_notified:
        bot.send_message(call.message.chat.id, "❌ Все уведомления отключены или подписки приостановлены.")
        return

    markup = telebot.types.InlineKeyboardMarkup()
    for real_index, s in active_notified:
        btn_text = f"{s['service']} ({s['next_payment']})"
        callback = f"notifydays_select_{real_index}"
        markup.add(telebot.types.InlineKeyboardButton(btn_text, callback_data=callback))

    markup.add(telebot.types.InlineKeyboardButton("↩ Назад", callback_data="notify_back"))

    bot.edit_message_text(
        "⏳ Выбери подписку для изменения срока уведомлений:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )



@bot.callback_query_handler(func=lambda call: call.data.startswith("notifydays_select_"))
def choose_days(call):
    bot.answer_callback_query(call.id)
    user_id = str(call.from_user.id)
    index = int(call.data.split("_")[-1])

    data = load_subscriptions()
    subs = data.get(user_id, [])
    if index >= len(subs):
        bot.answer_callback_query(call.id, "Ошибка: подписка не найдена.")
        return

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("↩ Назад", callback_data="notify_back"))

    for d in [1, 3, 5, 7]:
        markup.add(telebot.types.InlineKeyboardButton(
            f"🔔 За {d} дн.", callback_data=f"set_notifydays_{index}_{d}"
        ))

    bot.edit_message_text(
        "⏱ На сколько дней до оплаты напоминать?",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("set_notifydays_"))
def save_notify_days(call):
    bot.answer_callback_query(call.id)
    user_id = str(call.from_user.id)
    parts = call.data.split("_")
    index = int(parts[2])
    days = int(parts[3])

    data = load_subscriptions()
    subs = data.get(user_id, [])
    if 0 <= index < len(subs):
        subs[index].setdefault("notify", True)
        subs[index]["notify_days"] = days
        save_subscriptions(data)
        bot.edit_message_text(
            f"✅ Напоминание за {days} дней до оплаты включено для {subs[index]['service']}.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
    else:
        bot.answer_callback_query(call.id, "Ошибка: подписка не найдена.")


@bot.callback_query_handler(func=lambda call: call.data == "notify_disable")
def disable_notifications(call):
    bot.answer_callback_query(call.id)
    print("[DEBUG] notify_disable clicked")
    user_id = str(call.from_user.id)
    data = load_subscriptions()
    subs = data.get(user_id, [])

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("↩ Назад", callback_data="notify_back"))
    for i, s in enumerate(subs):
        if s.get("active", True) and s.get("notify", True):
            markup.add(telebot.types.InlineKeyboardButton(
                f"{s['service']} ({s['next_payment']})",
                callback_data=f"notify_disable_{i}"
            ))

    if not markup.keyboard:
        bot.answer_callback_query(call.id, "Все уведомления уже отключены.")
        return

    bot.edit_message_text(
        "🔕 Выбери подписку для отключения уведомлений:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("notify_disable_"))
def disable_notify_subscription(call):
    bot.answer_callback_query(call.id)
    user_id = str(call.from_user.id)
    index = int(call.data.split("_")[-1])
    data = load_subscriptions()
    subs = data.get(user_id, [])

    if index >= len(subs):
        bot.answer_callback_query(call.id, "Ошибка: подписка не найдена.")
        return

    subs[index].setdefault("notify", True)
    subs[index]["notify"] = False
    save_subscriptions(data)

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("↩ Назад", callback_data="notify_back"))

    bot.edit_message_text(
        f"🔕 Уведомления отключены для подписки {subs[index]['service']}.",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )

@bot.callback_query_handler(func=lambda call: call.data == "notify_enable")
def show_notify_enable_menu(call):
    bot.answer_callback_query(call.id)
    user_id = str(call.from_user.id)
    data = load_subscriptions()
    subs = data.get(user_id, [])

    markup = telebot.types.InlineKeyboardMarkup()
    for i, s in enumerate(subs):
        if s.get("active", True) and not s.get("notify", True):
            markup.add(telebot.types.InlineKeyboardButton(
                f"{s['service']} ({s['next_payment']})",
                callback_data=f"notify_enable_{i}"
            ))

    if not markup.to_dict().get("inline_keyboard"):
        bot.send_message(call.message.chat.id, "Все уведомления уже включены.")
        return

    # Добавляем кнопку Назад
    markup.add(telebot.types.InlineKeyboardButton("↩ Назад", callback_data="notify_back"))

    bot.edit_message_text(
        "✅ Выбери подписку, для которой включить уведомления:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("notify_enable_"))
def enable_notify_subscription(call):
    bot.answer_callback_query(call.id)
    user_id = str(call.from_user.id)
    index = int(call.data.split("_")[-1])
    data = load_subscriptions()
    subs = data.get(user_id, [])

    if index >= len(subs):
        bot.send_message(call.message.chat.id, "⚠️ Подписка не найдена.")
        return

    subs[index]["notify"] = True
    save_subscriptions(data)

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("↩ Назад", callback_data="notify_back"))

    bot.edit_message_text(
        f"✅ Уведомления включены для подписки {subs[index]['service']}.",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )

def send_notify_menu(chat_id, message_id=None):
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        telebot.types.InlineKeyboardButton("📅 Ближайшие оплаты", callback_data="notify_upcoming"),
        telebot.types.InlineKeyboardButton("⏳ Настроить срок", callback_data="change_notify_days"),
        telebot.types.InlineKeyboardButton("❌ Отключить", callback_data="notify_disable"),
        telebot.types.InlineKeyboardButton("✅ Включить", callback_data="notify_enable")
    )
    if message_id:
        bot.edit_message_text(
            "🔔 Меню уведомлений. Что ты хочешь настроить?",
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=markup
        )
    else:
        bot.send_message(
            chat_id,
            "🔔 Меню уведомлений. Что ты хочешь настроить?",
            reply_markup=markup
        )


def check_for_upcoming_payments():
    data = load_subscriptions()
    today = datetime.today()
    notify_delta = timedelta(days=1)

    for user_id, subs in data.items():
        for sub in subs:
            if not sub.get("active", True):
                continue

            try:
                pay_date = datetime.strptime(sub["next_payment"], "%d.%m.%Y")
                if 0 <= (pay_date - today).days <= notify_delta.days:
                    bot.send_message(
                        user_id,
                        f"🔔 Напоминание: завтра оплата за {sub['service']} — {pay_date.strftime('%d.%m.%Y')} на сумму {sub['price']}₽"
                    )
            except:
                continue


@bot.callback_query_handler(func=lambda call: call.data == "notify_upcoming")
def show_upcoming_payments(call):
    user_id = str(call.from_user.id)
    data = load_subscriptions()
    subs = data.get(user_id, [])

    if not subs:
        bot.answer_callback_query(call.id, "Нет подписок для отображения.")
        return

    subs = [s for s in subs if s.get("active", True)]

    if not subs:
        bot.answer_callback_query(call.id, "Нет активных подписок.")
        return

    # Отсортировать по дате
    try:
        subs.sort(key=lambda s: datetime.strptime(s["next_payment"], "%d.%m.%Y"))
    except:
        pass

    text = "📅 *Ближайшие подписки:*\n\n"
    for s in subs:
        try:
            pay_date = datetime.strptime(s["next_payment"], "%d.%m.%Y")
            date_str = f"{pay_date.day} {MONTHS_RU[pay_date.month]} {pay_date.year}"

        except:
            date_str = s["next_payment"]

        notify = s.get("notify", True)
        notify_days = s.get("notify_days", 1)

        if notify:
            notify_info = f"🔔 Уведомление за {notify_days} дн."
        else:
            notify_info = "🔕 Уведомление выключено"

        text += f"🔹 {s['service']} — {date_str} ({s['price']}₽)\n{notify_info}\n\n"

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("↩ Назад", callback_data="notify_back"))

    bot.edit_message_text(
        text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        parse_mode="Markdown",
        reply_markup=markup
    )



@bot.callback_query_handler(func=lambda c: c.data.startswith("cancel_") and not c.data.startswith("edit_cancel") and c.data != "cancel_tariff_add")
def cb_cancel(call):
    idx = int(call.data.split("_")[1])
    uid = str(call.from_user.id)
    data = load_subscriptions()
    subs = data.get(uid, [])

    if 0 <= idx < len(subs):
        subs[idx]["active"] = False
        save_subscriptions(data)
        bot.answer_callback_query(call.id, "⏸ Подписка остановлена")
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    else:
        bot.answer_callback_query(call.id, "Ошибка: подписка не найдена")

@bot.callback_query_handler(
    func=lambda c: c.data.startswith("edit_") and c.data != "edit_cancel")
def cb_edit(call):
    parts = call.data.split("_")
    if len(parts) != 2 or not parts[1].isdigit():          # защита
        return                                             # чужой callback — игнор
    idx = int(parts[1])
    uid = str(call.from_user.id)
    user_states[uid] = f"editing_{idx}"
    bot.answer_callback_query(call.id)
    cancel_kb = telebot.types.InlineKeyboardMarkup()
    cancel_kb.add(
        telebot.types.InlineKeyboardButton("↩ Отменить", callback_data="edit_cancel")
    )

    bot.send_message(
        call.message.chat.id,
        "🖉 Введите новую строку: `Цена,  Дата (ДД.ММ.ГГГГ)`",
        parse_mode="Markdown",
        reply_markup=cancel_kb
    )





@bot.callback_query_handler(func=lambda c: c.data.startswith("rem7_"))
def cb_remind(call):
    idx = int(call.data.split("_")[1])
    uid = str(call.from_user.id)
    data = load_subscriptions()
    subs = data.get(uid, [])

    if not (0 <= idx < len(subs)):
        bot.answer_callback_query(call.id, "Ошибка")
        return

    sub = subs[idx]
    try:
        pay_date = datetime.strptime(sub["next_payment"], "%d.%m.%Y")
        remind_date = pay_date - timedelta(days=7)
        scheduler.add_job(
            bot.send_message,
            'date',
            run_date=remind_date,
            args=[uid, f"🔔 Напоминание: через неделю оплата за {sub['display']}"]
        )
        bot.answer_callback_query(call.id, "⏰ Напоминание поставлено")
    except Exception as e:
        bot.answer_callback_query(call.id, "Не удалось поставить напоминание")
        print("rem7 error", e)





@bot.callback_query_handler(func=lambda c: c.data == "edit_cancel")
def cb_edit_cancel(call):
    uid = str(call.from_user.id)
    user_states[uid] = None
    bot.answer_callback_query(call.id, "✖️ Редактирование отменено")

    # вернуть меню тарифов — просто пересоздадим сообщение без кнопок
    bot.edit_message_reply_markup(call.message.chat.id,
                                  call.message.message_id,
                                  reply_markup=None)




@bot.callback_query_handler(func=lambda c: c.data.startswith("choose_tariff_"))
def cb_choose_tariff(call):
    key = call.data.split("_", 2)[2]
    uid = str(call.from_user.id)
    offers = TARIFF_REF.get() or {}

    if key not in offers:
        bot.answer_callback_query(call.id, "❌ Сервис не найден.")
        return

    user_states[uid] = f"tariff_date_{key}"
    name = offers[key][0]["name"]
    price = offers[key][0]["price"]

    bot.send_message(call.message.chat.id,
        f"📺 <b>{name}</b>\n"
        f"💰 Стоимость по тарифу: <b>{price}₽</b>\n\n"
        f"📅 Введите дату следующей оплаты в формате ДД.ММ.ГГГГ:",
        parse_mode="HTML"
    )



@bot.callback_query_handler(func=lambda c: c.data == "cancel_tariff_add")
def cb_cancel_tariff_add(call):
    user_states[str(call.from_user.id)] = None
    bot.answer_callback_query(call.id, "❎ Отменено")
    bot.edit_message_text("❎ Добавление отменено.", call.message.chat.id, call.message.message_id)







@bot.message_handler(content_types=["document"])
def handle_file_upload(message):
    uid = str(message.from_user.id)
    if user_states.get(uid) != "awaiting_import":
        return

    file_info = bot.get_file(message.document.file_id)
    downloaded = bot.download_file(file_info.file_path)

    try:
        new_subs = json.loads(downloaded.decode("utf-8"))
        if not isinstance(new_subs, list):
            raise Exception("Файл должен содержать список подписок.")

        subs = load_subscriptions()
        current = subs.get(uid, [])

        # фильтрация: чтобы не было дубликатов
        def unique_key(s): return f"{s.get('service')}::{s.get('next_payment')}"
        existing_keys = {unique_key(s) for s in current}

        added = [s for s in new_subs if unique_key(s) not in existing_keys]
        current.extend(added)
        subs[uid] = current
        save_subscriptions(subs)

        bot.send_message(message.chat.id, f"✅ Импортировано {len(added)} новых подписок.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка при импорте: {e}")
    finally:
        user_states[uid] = None





@bot.callback_query_handler(func=lambda c: c.data == "cancel_tariff_add")
def cb_cancel_tariff_add(call):
    user_id = str(call.from_user.id)
    user_states[user_id] = None
    bot.answer_callback_query(call.id, "❎ Добавление отменено.")
    bot.edit_message_text("❎ Добавление подписки отменено.", call.message.chat.id, call.message.message_id)





































@bot.callback_query_handler(func=lambda call: call.data == "notify_back")
def notify_back_menu(call):
    send_notify_menu(call.message.chat.id, call.message.message_id)



scheduler = BackgroundScheduler()
scheduler.start()
scheduler.add_job(check_for_upcoming_payments, 'interval', hours=24)









update_tariff_db()      
scheduler.add_job(update_tariff_db, 'interval', hours=24)








# ===== Запуск =====
bot.polling(none_stop=True)
