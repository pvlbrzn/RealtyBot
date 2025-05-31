import asyncio
from telegram_bot.notifier import notify_new_house


class DummyHouse:
    position = "г. Тестоград, ул. Примерная, д. 1"
    state_type = "Хорошее"
    inspection_date = "2025-05-28"
    link = "https://example.com/house/1"


async def main():
    await notify_new_house(DummyHouse())

asyncio.run(main())
