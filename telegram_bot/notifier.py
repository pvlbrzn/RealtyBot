import tempfile
import os
from uuid import uuid4
import openpyxl
from sqlalchemy.future import select
from models import House
from db import get_db
from aiogram import Bot
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# CHAT_ID может быть строкой, разделённой запятыми — сделаем список
ADMIN_CHAT_IDS = os.getenv("CHAT_ID", "").split(",")


async def notify_new_house(house_data):
    text = (
        f"🏠 <b>Новый дом обнаружен</b>\n\n"
        f"<b>Адрес:</b> {house_data.position}\n"
        f"<b>Состояние:</b> {house_data.state_type}\n"
        f"<b>Дата осмотра:</b> {house_data.inspection_date or '—'}\n"
        f"<b>Ссылка:</b> {house_data.link}"
    )
    for chat_id in ADMIN_CHAT_IDS:
        await bot.send_message(chat_id.strip(), text, parse_mode="HTML")


async def export_to_excel():
    async for db in get_db():
        result = await db.execute(select(House))
        houses = result.scalars().all()

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["ID", "Адрес", "Состояние", "Дата состояния", "Дата осмотра", "Ссылка", "Широта", "Долгота"])

        for house in houses:
            ws.append([
                house.id,
                house.position,
                house.state_type,
                house.state_date,
                house.inspection_date,
                house.link,
                house.latitude,
                house.longitude,
            ])

        # Используем временную папку, безопасно на всех ОС
        temp_dir = tempfile.gettempdir()
        file_name = os.path.join(temp_dir, f"houses_{uuid4().hex}.xlsx")
        wb.save(file_name)
        return file_name
