from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.models import Satsangi, SatsangiCreate
from app import store

app = FastAPI(title="JKP Registration POC")


@app.post("/api/satsangis", response_model=Satsangi)
async def create_satsangi(data: SatsangiCreate) -> Satsangi:
    return store.create_satsangi(data)


@app.get("/api/satsangis", response_model=list[Satsangi])
async def list_satsangis(q: str = "") -> list[Satsangi]:
    if q:
        return store.search_satsangis(q)
    return store.get_all_satsangis()
