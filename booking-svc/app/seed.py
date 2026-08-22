from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.database import SessionLocal
from app.models import FitnessClass


def seed_classes() -> None:
    db = SessionLocal()

    try:
        existing_class = db.scalar(
            select(FitnessClass).limit(1)
        )

        if existing_class:
            return

        now = datetime.now(timezone.utc)

        classes = [
            FitnessClass(
                name="Yoga",
                instructor="Ana López",
                capacity=20,
                scheduled_at=now + timedelta(days=1, hours=2),
            ),
            FitnessClass(
                name="Spinning",
                instructor="Carlos Méndez",
                capacity=15,
                scheduled_at=now + timedelta(days=1, hours=5),
            ),
            FitnessClass(
                name="CrossFit",
                instructor="Laura García",
                capacity=12,
                scheduled_at=now + timedelta(days=2, hours=3),
            ),
            FitnessClass(
                name="Pilates",
                instructor="María Rodríguez",
                capacity=18,
                scheduled_at=now + timedelta(days=3, hours=1),
            ),
        ]

        db.add_all(classes)
        db.commit()

    finally:
        db.close()