import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models, seed  # noqa: F401 - models must be imported before create_all
from .config import settings
from .db import Base, engine
from .errors import register_handlers
from .routers import admin, auth, catalog, evaluation

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    seed.run()
    yield


app = FastAPI(title="InkGrade AI API", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
register_handlers(app)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"], expose_headers=["Content-Disposition"])


@app.get("/actuator/health")
def health():
    return {"status": "UP"}


for r in (auth.router, admin.router, catalog.router, evaluation.router):
    app.include_router(r, prefix="/api")
