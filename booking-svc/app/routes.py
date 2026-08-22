from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import FitnessClass
from app.schemas import ClassResponse


router = APIRouter(
    tags=["classes"],
)


@router.get(
    "/classes",
    response_model=list[ClassResponse],
)
def get_available_classes(
    db: Session = Depends(get_db),
):
    classes = db.scalars(
        select(FitnessClass).order_by(
            FitnessClass.scheduled_at
        )
    ).all()

    return classes