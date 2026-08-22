from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.database import Base, check_database_connection, engine
from app.routes import router
from app.seed import seed_classes


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)

    seed_classes()

    yield


app = FastAPI(
    title="FitFlow Booking Service",
    description="Microservicio encargado de la gestión de clases y reservas",
    version="0.1.0",
    lifespan=lifespan,
)


app.include_router(router)


@app.get("/")
def root():
    return {
        "service": "booking-svc",
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