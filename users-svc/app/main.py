from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.database import check_database_connection


app = FastAPI(
    title="FitFlow Users Service",
    description="Microservicio encargado de la gestión y autenticación de usuarios de FitFlow.",
    version="0.1.0",
)


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