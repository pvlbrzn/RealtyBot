import sys
import asyncio

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, Depends, APIRouter, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text

from db import get_db, init_db
from models import House
from parser import run_parser

from pydantic import BaseModel

app = FastAPI(debug=False)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
router = APIRouter()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class RegionRequest(BaseModel):
    region: str


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/run-tasks")
async def run_tasks(payload: RegionRequest):
    if not payload.region:
        raise HTTPException(status_code=400, detail="Region is required")
    await run_parser(payload.region)
    return {"status": "ok"}


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


@router.get("/api/houses")
async def get_api_houses(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(House).where(House.latitude != None, House.longitude != None))
    houses = result.scalars().all()
    return [
        {
            "id": house.id,
            "address": house.position,
            "lat": house.latitude,
            "lon": house.longitude
        }
        for house in houses
    ]


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    return HTMLResponse(content=f"{exc.detail}", status_code=exc.status_code)


app.include_router(router)
