import asyncio
import httpx
from sqlalchemy import select
from db import AsyncSessionLocal
from models import House

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "RealtyBot-Geocoder"}


def generate_address_variants(raw_address: str) -> list[str]:
    parts = [p.strip() for p in raw_address.split(',') if p.strip()]
    variants = []

    # Полный адрес
    variants.append(f"{raw_address}, Беларусь")

    # Упрощённый — только населённый пункт
    simplified = []
    for part in parts:
        if any(x in part for x in ["д.", "аг.", "г.", "п.", "село"]):
            simplified.append(part)
    if simplified:
        variants.append(f"{', '.join(simplified)}, Минская область, Беларусь")
        variants.append(f"{simplified[-1]}, Минская область, Беларусь")

    return variants


async def try_geocode(session: httpx.AsyncClient, address: str):
    params = {
        "q": address,
        "format": "json",
        "limit": 1,
        "countrycodes": "by"
    }
    try:
        response = await session.get(NOMINATIM_URL, params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception as e:
        print(f"Ошибка геокодирования '{address}': {e}")
    return None


async def geocode_address_variants(raw_address: str, session: httpx.AsyncClient):
    for variant in generate_address_variants(raw_address):
        coords = await try_geocode(session, variant)
        if coords:
            print(f"[OK] {raw_address} → {coords} (вариант: '{variant}')")
            return coords
        else:
            print(f"[FAIL] {variant}")
        await asyncio.sleep(1)  # пауза между вариантами
    return None


async def main():
    async with AsyncSessionLocal() as db_session:
        result = await db_session.execute(select(House).where(House.latitude == None))
        houses = result.scalars().all()
        print(f"Найдено {len(houses)} адресов без координат.")

        async with httpx.AsyncClient() as http_session:
            for house in houses:
                coords = await geocode_address_variants(house.position, http_session)
                if coords:
                    house.latitude, house.longitude = coords
                    db_session.add(house)
                    await db_session.commit()
                await asyncio.sleep(1.2)  # пауза между домами


if __name__ == "__main__":
    asyncio.run(main())
