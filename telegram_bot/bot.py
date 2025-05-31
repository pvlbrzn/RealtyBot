import os
import asyncio
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types, Router
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, ReplyKeyboardMarkup, KeyboardButton
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart

from telegram_bot.notifier import export_to_excel

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
SITE_URL = "http://localhost:53947"


bot = Bot(
    token=TELEGRAM_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()
router = Router()
dp.include_router(router)


@router.message(CommandStart())
async def start(message: types.Message):
    welcome_text = (
        "👋 Привет! Я <b>RealtyBot</b>.\n\n"
        "Я могу:\n"
        "• 🔔 Присылать уведомления о новых домах\n"
        "• 📊 Генерировать Excel-отчёт\n"
        "• 🗺 Показать карту домов в выбранной области\n\n"
        "Выбери действие ниже:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Получить отчёт", callback_data="get_excel")],
        [InlineKeyboardButton(text="🗺 Показать карту", callback_data="show_map")]
    ])

    await message.answer(welcome_text, reply_markup=keyboard)


@router.callback_query(lambda c: c.data == "get_excel")
async def send_excel(callback: types.CallbackQuery):
    file_path = await export_to_excel()
    await callback.message.answer_document(FSInputFile(file_path))
    os.remove(file_path)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
