import contextlib
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.models import Satsangi, SatsangiCreate
from app.db import init_db
from app import store

logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("REST server ready (PostgreSQL: jkp_reg_poc_rest)")
    yield


app = FastAPI(title="JKP Registration POC (REST + PostgreSQL)", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/satsangis", response_model=Satsangi)
async def create_satsangi(data: SatsangiCreate) -> Satsangi:
    return store.create_satsangi(data)


@app.get("/api/satsangis", response_model=list[Satsangi])
async def list_satsangis(q: str = "") -> list[Satsangi]:
    if q:
        return store.search_satsangis(q)
    return store.get_all_satsangis()
