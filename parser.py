import asyncio
from datetime import datetime
from sqlalchemy import select, delete
from models import House
from db import get_db
from telegram_bot.notifier import notify_new_house
from playwright.async_api import async_playwright
import aiohttp
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("parser.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

API_URL = "https://eri2.nca.by/api/guest/abandonedObject/search"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}


# --------------------------- Playwright Geo Extraction ---------------------------

async def extract_latlon(house_id: int) -> tuple[float, float] | None:
    try:
        url = f"https://eri2.nca.by/guest/abandonedObject/{house_id}#address"
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url)
            await page.wait_for_selector(".leaflet-marker-icon", timeout=15000)

            result = await page.evaluate("""() => {
                try {
                    const marker = document.querySelector(".leaflet-marker-icon");
                    const mapEl = document.querySelector(".vue2leaflet-map");
                    const markerRect = marker.getBoundingClientRect();
                    const mapRect = mapEl.getBoundingClientRect();
                    const centerX = markerRect.left + markerRect.width / 2 - mapRect.left;
                    const centerY = markerRect.top + markerRect.height / 2 - mapRect.top;
                    const leafletMap = mapEl.__vue__?.mapObject;
                    if (!leafletMap) return null;
                    const latlng = leafletMap.containerPointToLatLng([centerX, centerY]);
                    return { lat: latlng.lat, lon: latlng.lng };
                } catch (e) {
                    return null;
                }
            }""")

            await browser.close()

            if result:
                return result["lat"], result["lon"]
            return None
    except Exception as e:
        logger.error(f"[!] Ошибка получения координат: {e}")
        return None


# --------------------------- House Parser ---------------------------

def is_target_region(house, region: str) -> bool:
    return region in house.get("position", "")


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
                logger.warning(f"[{page_number}] HTTP Error: {response.status}")
                return []
            data = await response.json()
            return data.get("data", {}).get("content", [])
    except Exception as e:
        logger.error(f"[{page_number}] Error: {e}")
        return []


async def fetch_all(region="Минская обл."):
    async with aiohttp.ClientSession() as session:
        all_houses = []
        page_number = 0

        while True:
            logger.info(f"\n📄 Страница {page_number}")
            houses = await fetch_page(session, page_number)
            if not houses:
                break

            region_houses = [h for h in houses if is_target_region(h, region)]
            for h in region_houses:
                h["link"] = build_link(h["id"])
                h["inspectionDateStr"] = timestamp_to_str(h.get("inspectionDate"))
                h["abandonedObjectStateDateStr"] = timestamp_to_str(h.get("abandonedObjectStateDate"))

                coords = await extract_latlon(h["id"])
                if coords:
                    h["latitude"], h["longitude"] = coords
                    logger.info(f"[✓] Координаты для ID {h['id']}: {coords}")
                else:
                    logger.warning(f"[✗] Не удалось получить координаты для ID {h['id']}")

            logger.info(f"{region}: {len(region_houses)} найдено объектов")
            all_houses.extend(region_houses)

            page_number += 1
            await asyncio.sleep(2)

        return all_houses


async def save_new_houses(houses, region):
    if not houses:
        logger.warning("❗ Нет данных для сохранения. Отмена операций с БД.")
        return 0, 0, 0

    added = updated = deleted = 0

    async for session in get_db():
        incoming_ids = {house["id"] for house in houses}
        result = await session.execute(
            select(House.id).where(House.position.ilike(f"%{region}%"))
        )
        db_ids = set(result.scalars().all())

        ids_to_delete = db_ids - incoming_ids
        if ids_to_delete:
            await session.execute(delete(House).where(House.id.in_(ids_to_delete)))
            deleted = len(ids_to_delete)

        for house in houses:
            existing = await session.get(House, house["id"])
            if existing:
                existing.position = house.get("position")
                existing.state_type = house.get("abandonedObjectStateType")
                existing.state_date = house.get("abandonedObjectStateDateStr")
                existing.inspection_date = house.get("inspectionDateStr")
                existing.link = house.get("link")
                existing.latitude = house.get("latitude")
                existing.longitude = house.get("longitude")
                existing.actual = house.get("actual", True)
                updated += 1
            else:
                db_obj = House(
                    id=house["id"],
                    position=house.get("position"),
                    state_type=house.get("abandonedObjectStateType"),
                    state_date=house.get("abandonedObjectStateDateStr"),
                    inspection_date=house.get("inspectionDateStr"),
                    link=house.get("link"),
                    latitude=house.get("latitude"),
                    longitude=house.get("longitude"),
                    actual=house.get("actual", True)
                )
                session.add(db_obj)
                await session.flush()
                added += 1
                await notify_new_house(db_obj)

        await session.commit()

    return added, updated, deleted


async def main(region="Минская обл."):
    logger.info(f"🚀 Запуск парсера для региона: {region}")
    houses = await fetch_all(region)

    if not houses:
        logger.warning("❌ Парсер не нашёл ни одной записи. Обновление БД прервано для безопасности.")
        return

    logger.info(f"\n🔎 Всего получено объектов: {len(houses)}")
    added, updated, deleted = await save_new_houses(houses, region)

    logger.info(f"\n✅ Обновление завершено:")
    logger.info(f"➕ Добавлено: {added}")
    logger.info(f"🔁 Обновлено: {updated}")
    logger.info(f"🗑 Удалено: {deleted}")


if __name__ == "__main__":
    import sys

    region = sys.argv[1] if len(sys.argv) > 1 else "Минская обл."
    asyncio.run(main(region))


async def run_parser(region: str = "Минская обл."):
    await main(region)
