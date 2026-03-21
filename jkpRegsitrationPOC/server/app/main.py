import contextlib
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.models import Devotee, DevoteeCreate, Visit, VisitCreate
from app.db import init_db
from app import store

logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("REST server ready (PostgreSQL: jkp_reg_poc_rest)")
    yield


app = FastAPI(title="JKP Registration POC", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Devotees ───

@app.post("/api/devotees", response_model=Devotee)
async def create_devotee(data: DevoteeCreate) -> Devotee:
    return store.create_devotee(data)


@app.get("/api/devotees/{satsangi_id}", response_model=Devotee)
async def get_devotee(satsangi_id: str) -> Devotee:
    result = store.get_devotee_by_satsangi_id(satsangi_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Devotee not found")
    return result


@app.get("/api/devotees", response_model=list[Devotee])
async def list_devotees(q: str = "") -> list[Devotee]:
    if q:
        return store.search_devotees(q)
    return store.get_all_devotees()


# ─── Visits ───

@app.post("/api/visits", response_model=Visit)
async def create_visit(data: VisitCreate) -> Visit:
    return store.create_visit(data)


@app.get("/api/devotees/{satsangi_id}/visits", response_model=list[Visit])
async def get_devotee_visits(satsangi_id: str) -> list[Visit]:
    devotee = store.get_devotee_by_satsangi_id(satsangi_id)
    if devotee is None:
        raise HTTPException(status_code=404, detail="Devotee not found")
    return store.get_visits_for_devotee(devotee.id)
