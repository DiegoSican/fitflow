from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.database import Base, check_database_connection, engine
from app.routes import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)

    yield


app = FastAPI(
    title="FitFlow Users Service",
    description="Microservicio encargado de la gestión y autenticación de usuarios",
    version="0.1.0",
    lifespan=lifespan,
)


app.include_router(users_router)


@app.get("/")
def root():
    return {
        "service": "users-svc",
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