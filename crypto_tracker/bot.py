import logging
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, html
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# ТОКЕН И URL БЭКЕНДА (Замените на свои данные)
BOT_TOKEN = "8709754600:AAHpLvgF7RqCk7GCHyFCVCifpPpw307REjw"
BACKEND_URL = "https://crypto-tracker-rbig.onrender.com/api"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Приветствие при старте."""
    await message.answer(
        f"Привет, {html.bold(message.from_user.full_name)}! 👋\n\n"
        f"Я твой личный помощник по криптопортфелю.\n"
        f"Чтобы связать меня с твоим аккаунтом на сайте, введи команду:\n"
        f"<code>/link ВАШ_СЕКРЕТНЫЙ_КЛЮЧ</code>\n\n"
        f"Секретный ключ можно найти на главной странице сайта в личном кабинете.",
        parse_mode="HTML"
    )


@dp.message(Command("link"))
async def cmd_link(message: Message, command: CommandObject):
    """Привязка аккаунта через секретный ключ."""
    secret_key = command.args

    if not secret_key:
        await message.answer("⚠ Пожалуйста, укажите секретный ключ. Пример: `/link 12345-abcde...`",
                             parse_mode="Markdown")
        return

    telegram_id = message.from_user.id
    payload = {
        "secret_key": secret_key,
        "telegram_id": str(telegram_id)
    }

    # Отправляем POST запрос к нашему Django API на Render
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f"{BACKEND_URL}/link-bot/", json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    await message.answer(
                        f"🎉 Успешно! Аккаунт {html.bold(data['username'])} привязан.\n"
                        f"Теперь вы можете проверить баланс с помощью команды /portfolio",
                        parse_mode="HTML"
                    )
                else:
                    data = await response.json()
                    error_msg = data.get("error", "Произошла ошибка при привязке.")
                    await message.answer(f"❌ Ошибка: {error_msg}")
        except Exception as e:
            await message.answer("⚠ Не удалось связаться с сервером сайта. Проверьте, работает ли он.")


@dp.message(Command("portfolio"))
async def cmd_portfolio(message: Message):
    """Запрос баланса и аналитики портфеля."""
    telegram_id = message.from_user.id

    # Отправляем GET запрос к нашему Django API на Render
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{BACKEND_URL}/portfolio/", params={"telegram_id": telegram_id}) as response:
                if response.status == 200:
                    data = await response.json()

                    # Формируем красивый отчет
                    text = f"📊 {html.bold('Портфель пользователя:')} {data['username']}\n"
                    text += "─" * 20 + "\n"
                    text += f"💵 Инвестировано: {html.bold(f'${data['total_invested']}')}\n"
                    text += f"💰 Текущая оценка: {html.bold(f'${data['total_current_value']}')}\n"

                    pnl = data['total_pnl_usd']
                    pnl_sign = "+" if pnl >= 0 else ""
                    pnl_emoji = "🟢" if pnl >= 0 else "🔴"
                    text += f"{pnl_emoji} Общий PnL: {html.bold(f'{pnl_sign}${pnl}')}\n"
                    text += "─" * 20 + "\n\n"

                    # Выводим монеты списком
                    if data['assets']:
                        text += f"{html.bold('Активы в портфеле:')}\n"
                        for asset in data['assets']:
                            asset_pnl_sign = "+" if asset['pnl_usd'] >= 0 else ""
                            text += (
                                f"▪ {html.bold(asset['symbol'])} ({asset['name']}): {asset['amount']} шт.\n"
                                f"  Цена покупки: ${asset['buy_price']} | Сейчас: ${asset['current_price']}\n"
                                f"  Текущая стоимость: ${asset['current_value']}\n"
                                f"  PnL: {asset_pnl_sign}${asset['pnl_usd']}\n\n"
                            )
                    else:
                        text += "У вас пока нет купленных монет."

                    await message.answer(text, parse_mode="HTML")
                elif response.status == 404:
                    await message.answer(
                        "❌ Ваш Telegram ID не привязан к аккаунту на сайте. Сначала введите команду `/link СЕКРЕТНЫЙ_КЛЮЧ`",
                        parse_mode="Markdown")
                else:
                    await message.answer("⚠ Не удалось получить данные портфеля.")
        except Exception as e:
            await message.answer("⚠ Ошибка подключения к серверу сайта.")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())