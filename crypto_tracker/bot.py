import asyncio
import logging
import math
import os

import aiohttp
from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("crypto-bot")

BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_API_SECRET = os.getenv("BOT_API_SECRET")
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000/api").rstrip("/")

if not BOT_TOKEN:
    raise ValueError("ОШИБКА: BOT_TOKEN не найден в переменных окружения!")
if not BOT_API_SECRET:
    raise ValueError("ОШИБКА: BOT_API_SECRET не найден в переменных окружения!")

# Единый parse_mode для всех сообщений — HTML
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
http = None  # общая aiohttp-сессия, создаётся в main()

SERVER_DOWN = ("⚠ Не удалось связаться с сервером сайта. Возможно, он «просыпается» — "
               "попробуйте ещё раз через минуту.")


class BackendUnavailable(Exception):
    pass


async def api(method, path, **kwargs):
    """Запрос к Django API. Возвращает (status, dict)."""
    try:
        async with http.request(method, f"{BACKEND_URL}{path}", **kwargs) as resp:
            try:
                data = await resp.json(content_type=None)
            except ValueError:
                data = {}
            if not isinstance(data, dict):
                data = {}
            return resp.status, data
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        logger.error("Backend request failed: %s %s: %r", method, path, exc)
        raise BackendUnavailable from exc


# ---------- форматирование ----------
def money(value):
    value = float(value)
    a = abs(value)
    digits = 2 if (a == 0 or a >= 1) else min(8, max(2, 2 - math.floor(math.log10(a))))
    text = f"{a:,.{digits}f}"
    sign = "-" if value < 0 and text.strip("0.,") else ""
    return f"{sign}${text}"


def signed_money(value):
    text = money(value)
    return text if text.startswith("-") else "+" + text


def signed_percent(value):
    value = round(float(value), 2) or 0.0   # убираем «-0.00»
    return f"{value:+.2f}%"


def amount_text(value):
    return f"{float(value):.8f}".rstrip("0").rstrip(".") or "0"


def split_message(lines, limit=3500):
    """Лимит Telegram — 4096 символов; режем по строкам."""
    chunks, current = [], ""
    for line in lines:
        if current and len(current) + len(line) + 1 > limit:
            chunks.append(current)
            current = ""
        current += line + "\n"
    if current:
        chunks.append(current)
    return chunks


# ---------- команды ----------
HELP_TEXT = (
    "Команды:\n"
    "/link <code>КЛЮЧ</code> — привязать аккаунт сайта\n"
    "/portfolio — баланс и PnL портфеля\n"
    "/unlink — отвязать аккаунт\n"
    "/help — эта справка\n\n"
    "Ключ находится на странице «Портфель» сайта."
)


@dp.message(Command("start"))
async def cmd_start(message: Message):
    name = html.quote(message.from_user.full_name)
    await message.answer(
        f"Привет, {html.bold(name)}! 👋\n\n"
        "Я твой личный помощник по криптопортфелю.\n"
        "Чтобы связать меня с аккаунтом на сайте, введи:\n"
        "<code>/link ВАШ_СЕКРЕТНЫЙ_КЛЮЧ</code>\n\n"
        "Секретный ключ показан на странице «Портфель» сайта.\n"
        "Список команд: /help"
    )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(HELP_TEXT)


@dp.message(Command("link"))
async def cmd_link(message: Message, command: CommandObject):
    secret_key = (command.args or "").strip()
    if not secret_key:
        await message.answer("⚠ Укажите секретный ключ. Пример: <code>/link 12345678-abcd-...</code>")
        return

    try:
        status, data = await api("POST", "/link-bot/", json={
            "secret_key": secret_key,
            "telegram_id": str(message.from_user.id),
        })
    except BackendUnavailable:
        await message.answer(SERVER_DOWN)
        return

    # Убираем сообщение с ключом из чата (в личных чатах бот может удалять входящие)
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    if status == 200:
        username = html.quote(str(data.get("username", "")))
        await message.answer(
            f"🎉 Успешно! Аккаунт {html.bold(username)} привязан.\n"
            "Теперь доступна команда /portfolio.\n"
            "Ключ на сайте обновлён, старый больше не действует."
        )
    elif status == 403:
        logger.error("Backend rejected BOT_API_SECRET: %s", data)
        await message.answer("⚠ Бот не настроен для работы с сайтом (проверьте BOT_API_SECRET).")
    else:
        error = html.quote(str(data.get("error", "Не удалось привязать аккаунт.")))
        await message.answer(f"❌ {error}")


@dp.message(Command("unlink"))
async def cmd_unlink(message: Message):
    try:
        status, data = await api("POST", "/unlink-bot/", json={"telegram_id": str(message.from_user.id)})
    except BackendUnavailable:
        await message.answer(SERVER_DOWN)
        return
    if status == 200:
        await message.answer("✅ Аккаунт отвязан. Чтобы привязать снова, используйте /link.")
    elif status == 404:
        await message.answer("ℹ Этот Telegram и так не привязан ни к одному аккаунту.")
    else:
        logger.error("Unlink failed: %s %s", status, data)
        await message.answer("⚠ Не удалось отвязать аккаунт. Попробуйте позже.")


@dp.message(Command("portfolio"))
async def cmd_portfolio(message: Message):
    await bot.send_chat_action(message.chat.id, "typing")
    try:
        status, data = await api("GET", "/portfolio/", params={"telegram_id": str(message.from_user.id)})
    except BackendUnavailable:
        await message.answer(SERVER_DOWN)
        return

    if status == 404:
        await message.answer("❌ Ваш Telegram не привязан к аккаунту. "
                             "Введите <code>/link СЕКРЕТНЫЙ_КЛЮЧ</code>.")
        return
    if status != 200:
        logger.error("Unexpected portfolio response: %s %s", status, data)
        await message.answer("⚠ Не удалось получить данные портфеля (ошибка на стороне сайта).")
        return

    pnl = data["total_pnl_usd"]
    emoji = "🟢" if pnl >= 0 else "🔴"
    username = html.quote(str(data["username"]))
    invested = money(data["total_invested"])
    current = money(data["total_current_value"])
    pnl_line = f"{signed_money(pnl)} ({signed_percent(data['total_pnl_percent'])})"

    lines = [
        f"📊 {html.bold('Портфель:')} {username}",
        "─" * 20,
        f"💵 Инвестировано: {html.bold(invested)}",
        f"💰 Текущая оценка: {html.bold(current)}",
        f"{emoji} Общий PnL: {html.bold(pnl_line)}",
        "─" * 20,
        "",
    ]

    if not data["assets"]:
        lines.append("У вас пока нет купленных монет.")
    else:
        lines.append(html.bold("Активы в портфеле:"))
        for a in data["assets"]:
            symbol = html.quote(a["symbol"])
            name = html.quote(a["name"])
            note = "" if a.get("price_known", True) else " ⚠ цена недоступна"
            lines.append(
                f"▪ {html.bold(symbol)} ({name}): {amount_text(a['amount'])} шт.\n"
                f"  Покупка: {money(a['buy_price'])} | Сейчас: {money(a['current_price'])}{note}\n"
                f"  Стоимость: {money(a['current_value'])}\n"
                f"  PnL: {signed_money(a['pnl_usd'])} ({signed_percent(a['pnl_percent'])})\n"
            )

    if not data.get("prices_ok", True):
        missing = html.quote(", ".join(data.get("missing_symbols", [])))
        lines.append(f"⚠ Не удалось получить цены для: {missing}. Для них показана цена покупки.")

    for chunk in split_message(lines):
        await message.answer(chunk)


async def main():
    global http
    http = aiohttp.ClientSession(
        headers={"X-Bot-Secret": BOT_API_SECRET},
        timeout=aiohttp.ClientTimeout(total=45),  # запас на «просыпание» Render
    )
    try:
        await dp.start_polling(bot)
    finally:
        await http.close()


if __name__ == "__main__":
    asyncio.run(main())