from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text

from db import get_db, init_db
from models import House

app = FastAPI()


@app.on_event("startup")
async def on_startup():
    await init_db()


@app.get("/houses")
async def get_houses(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(House))
    return result.scalars().all()


@app.get("/whoami")
async def whoami(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT current_user"))
    return {"user": result.scalar_one()}
