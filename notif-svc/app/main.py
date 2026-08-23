import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.database import Base, check_database_connection, engine
from app.routes import router


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)

    yield


app = FastAPI(
    title="FitFlow Notification Service",
    description="Microservicio encargado de la gestión de notificaciones de FitFlow.",
    version="0.1.0",
    lifespan=lifespan,
)


app.include_router(router)


@app.get("/")
def root():
    return {
        "service": "notif-svc",
        "status": "running",
    }


@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
    }


@app.get("/readyz")
def readyz():
    if not check_database_connection():
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "database": "unavailable",
            },
        )

    return {
        "status": "ok",
    }