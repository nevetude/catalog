"""Catalog application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import STATIC, VERSION
from app.db import init_db
from app.routers import auth, catalog, library


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Catalog", version=VERSION, lifespan=lifespan)
app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(library.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


def _page(name: str) -> FileResponse:
    return FileResponse(STATIC / "pages" / name)


@app.get("/", include_in_schema=False)
def index_page():
    return _page("index.html")


@app.get("/movie/{movie_id}", include_in_schema=False)
def movie_page(movie_id: int):
    return _page("movie.html")


@app.get("/show/{show_id}", include_in_schema=False)
def show_page(show_id: int):
    return _page("show.html")


@app.get("/library", include_in_schema=False)
@app.get("/library/{folder_slug}", include_in_schema=False)
def library_page(folder_slug: str | None = None):
    return _page("library.html")


@app.get("/company/{company_id}", include_in_schema=False)
def company_page(company_id: int):
    return _page("company.html")


@app.get("/collection/{collection_id}", include_in_schema=False)
def collection_page(collection_id: int):
    return _page("collection.html")


@app.get("/login", include_in_schema=False)
def login_page():
    return _page("login.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
