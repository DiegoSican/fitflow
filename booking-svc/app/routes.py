from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import get_current_user_id
from app.database import get_db
from app.models import Booking, FitnessClass
from app.schemas import (
    BookingCreate,
    BookingResponse,
    ClassResponse,
)


router = APIRouter()


# =========================================================
# Listar clases disponibles
# =========================================================

@router.get(
    "/classes",
    response_model=list[ClassResponse],
    tags=["classes"],
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


# =========================================================
# Crear reserva
# =========================================================

@router.post(
    "/bookings",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["bookings"],
)
def create_booking(
    booking_data: BookingCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    fitness_class = db.get(
        FitnessClass,
        booking_data.class_id,
    )

    if not fitness_class:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class not found.",
        )

    existing_booking = db.scalar(
        select(Booking).where(
            Booking.user_id == user_id,
            Booking.class_id == booking_data.class_id,
            Booking.status == "active",
        )
    )

    if existing_booking:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already has an active booking for this class.",
        )

    active_bookings = db.scalar(
        select(func.count())
        .select_from(Booking)
        .where(
            Booking.class_id == booking_data.class_id,
            Booking.status == "active",
        )
    )

    if active_bookings >= fitness_class.capacity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Class is full.",
        )

    booking = Booking(
        user_id=user_id,
        class_id=booking_data.class_id,
        status="active",
    )

    db.add(booking)
    db.commit()
    db.refresh(booking)

    return booking

# =========================================================
# Consultar reserva por ID
# =========================================================

@router.get(
    "/bookings/{booking_id}",
    response_model=BookingResponse,
    tags=["bookings"],
)
def get_booking(
    booking_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    booking = db.get(
        Booking,
        booking_id,
    )

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found.",
        )

    if booking.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this booking.",
        )

    return booking

# =========================================================
# Cancelar reserva
# =========================================================

@router.delete(
    "/bookings/{booking_id}",
    response_model=BookingResponse,
    tags=["bookings"],
)
def cancel_booking(
    booking_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    booking = db.get(
        Booking,
        booking_id,
    )

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found.",
        )

    if booking.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to cancel this booking.",
        )

    if booking.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Booking is already cancelled.",
        )

    booking.status = "cancelled"

    db.commit()
    db.refresh(booking)

    return booking

