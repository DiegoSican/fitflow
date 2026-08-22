import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import SQLAlchemyError


ROOT_DIR = Path(__file__).resolve().parents[2]

load_dotenv(ROOT_DIR / ".env")


DATABASE_URL = URL.create(
    drivername="postgresql+psycopg",
    username=os.getenv("USERS_DB_USER"),
    password=os.getenv("USERS_DB_PASSWORD"),
    host=os.getenv("USERS_DB_HOST"),
    port=int(os.getenv("USERS_DB_PORT", "5432")),
    database=os.getenv("USERS_DB_NAME"),
)


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={
        "connect_timeout": 2,
    },
)


def check_database_connection() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return True

    except SQLAlchemyError:
        return False