import asyncio
import aiohttp
from datetime import datetime
from sqlalchemy import select, delete
from models import House
from db import get_db

API_URL = "https://eri2.nca.by/api/guest/abandonedObject/search"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}


def is_minsk_region(house):
    return "Минская обл." in house.get("position", "")


def timestamp_to_str(ms):
    try:
        return datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d")
    except Exception:
        return None


def build_link(house_id):
    return f"https://eri2.nca.by/guest/abandonedObject/{house_id}"


async def fetch_page(session, page_number):
    payload = {
        "pageSize": 20,
        "pageNumber": page_number,
        "sortBy": 1,
        "sortDesc": True,
        "destroyed": False,
        "emergency": False,
        "oneBasePrice": True,
        "stateSearchCategoryId": 2
    }

    try:
        async with session.post(API_URL, json=payload, headers=HEADERS) as response:
            if response.status != 200:
                print(f"[{page_number}] HTTP Error: {response.status}")
                return []
            data = await response.json()
            return data.get("data", {}).get("content", [])
    except Exception as e:
        print(f"[{page_number}] Error: {e}")
        return []


async def fetch_all():
    async with aiohttp.ClientSession() as session:
        all_houses = []
        page_number = 0

        while True:
            print(f"\n📄 Страница {page_number}")
            houses = await fetch_page(session, page_number)
            if not houses:
                break

            minsk_houses = [h for h in houses if is_minsk_region(h)]
            for h in minsk_houses:
                h["link"] = build_link(h["id"])
                h["inspectionDateStr"] = timestamp_to_str(h.get("inspectionDate"))
                h["abandonedObjectStateDateStr"] = timestamp_to_str(h.get("abandonedObjectStateDate"))

            print(f"Минская область: {len(minsk_houses)} найдено объектов")
            all_houses.extend(minsk_houses)

            page_number += 1
            await asyncio.sleep(2)

        return all_houses


async def save_new_houses(houses):
    if not houses:
        print("❗ Нет данных для сохранения. Отмена операций с БД.")
        return 0, 0, 0

    added = updated = deleted = 0

    async for session in get_db():
        # 1. ID всех домов из API
        incoming_ids = {house["id"] for house in houses}

        # 2. Получаем ID всех домов из БД
        result = await session.execute(select(House.id))
        db_ids = set(result.scalars().all())

        # 3. Удаляем дома, которых больше нет
        ids_to_delete = db_ids - incoming_ids
        if ids_to_delete:
            await session.execute(delete(House).where(House.id.in_(ids_to_delete)))
            deleted = len(ids_to_delete)

        # 4. Добавляем новые / обновляем старые
        for house in houses:
            existing = await session.get(House, house["id"])
            if existing:
                # обновление
                existing.position = house.get("position")
                existing.state_type = house.get("abandonedObjectStateType")
                existing.state_date = house.get("abandonedObjectStateDateStr")
                existing.inspection_date = house.get("inspectionDateStr")
                existing.link = house.get("link")
                existing.actual = house.get("actual", True)
                updated += 1
            else:
                # добавление
                db_obj = House(
                    id=house["id"],
                    position=house.get("position"),
                    state_type=house.get("abandonedObjectStateType"),
                    state_date=house.get("abandonedObjectStateDateStr"),
                    inspection_date=house.get("inspectionDateStr"),
                    link=house.get("link"),
                    actual=house.get("actual", True)
                )
                session.add(db_obj)
                added += 1

        await session.commit()

    return added, updated, deleted


async def main():
    print("🚀 Запуск парсера...")
    houses = await fetch_all()

    if not houses:
        print("❌ Парсер не нашёл ни одной записи. Обновление БД прервано для безопасности.")
        return

    print(f"\n🔎 Всего получено объектов: {len(houses)}")

    added, updated, deleted = await save_new_houses(houses)

    print(f"\n✅ Обновление завершено:")
    print(f"➕ Добавлено: {added}")
    print(f"🔁 Обновлено: {updated}")
    print(f"🗑 Удалено: {deleted}")


if __name__ == "__main__":
    asyncio.run(main())


#TODO: Подключать бота
#TODO: EXCEL отчет с объекати в ТГ и на вью
#TODO: Запустить периодический парс и уведомления в бота
