from fastapi import FastAPI


app = FastAPI(
    title="FitFlow Users Service",
    description="Microservicio encargado de la gestión y autenticación de usuarios",
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