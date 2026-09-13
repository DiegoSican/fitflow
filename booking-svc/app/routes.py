from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.observability import json_log

from app.auth import get_current_user_id
from app.database import get_db
from app.models import (
    Booking,
    FitnessClass,
    PendingNotification,
)
from app.notification_client import (
    get_circuit_breaker_state,
    send_notification,
)
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
    request: Request,
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
            detail=(
                "User already has an active booking "
                "for this class."
            ),
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

    # -----------------------------------------------------
    # IMPORTANTE:
    # Primero persistimos la reserva.
    # La notificación NO puede impedir la reserva.
    # -----------------------------------------------------

    booking = Booking(
        user_id=user_id,
        class_id=booking_data.class_id,
        status="active",
    )

    db.add(booking)
    db.commit()
    db.refresh(booking)

    correlation_id = request.state.correlation_id

    json_log(
        service="booking-svc",
        event="booking_created",
        correlation_id=correlation_id,
        user_id=user_id,
        booking_id=booking.id,
        class_id=booking.class_id,
    )

    # -----------------------------------------------------
    # Intentar notificación
    # -----------------------------------------------------

    message = (
        f"Booking {booking.id} confirmed for "
        f"{fitness_class.name}."
    )

    notification_sent = send_notification(
    user_id=user_id,
    message=message,
    correlation_id=correlation_id,
)

    # -----------------------------------------------------
    # Si notif-svc falla, guardar como pendiente.
    # La reserva YA está confirmada.
    # -----------------------------------------------------

    if not notification_sent:
        pending_notification = PendingNotification(
            user_id=user_id,
            booking_id=booking.id,
            message=message,
            status="pending",
        )

        db.add(pending_notification)
        db.commit()

        print(
            f"[OUTBOX] Notification for booking "
            f"{booking.id} stored as pending"
        )

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
            detail=(
                "You do not have permission "
                "to access this booking."
            ),
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
            detail=(
                "You do not have permission "
                "to cancel this booking."
            ),
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


# =========================================================
# Estado del Circuit Breaker
# =========================================================

@router.get(
    "/circuit-breaker",
    tags=["resilience"],
)
def circuit_breaker_status():
    return get_circuit_breaker_state()


# =========================================================
# Ver notificaciones pendientes
# =========================================================

@router.get(
    "/pending-notifications",
    tags=["resilience"],
)
def pending_notifications(
    db: Session = Depends(get_db),
):
    notifications = db.scalars(
        select(PendingNotification)
        .where(
            PendingNotification.status == "pending"
        )
        .order_by(PendingNotification.id)
    ).all()

    return [
        {
            "id": item.id,
            "user_id": item.user_id,
            "booking_id": item.booking_id,
            "message": item.message,
            "status": item.status,
            "created_at": item.created_at,
        }
        for item in notifications
    ]

# =========================================================
# Reprocesar notificaciones pendientes
# =========================================================

@router.post(
    "/pending-notifications/retry",
    tags=["resilience"],
)
def retry_pending_notifications(
    db: Session = Depends(get_db),
):
    notifications = db.scalars(
        select(PendingNotification)
        .where(
            PendingNotification.status == "pending"
        )
        .order_by(PendingNotification.id)
    ).all()

    processed = 0
    remaining = 0

    for item in notifications:
        sent = send_notification(
            user_id=item.user_id,
            message=item.message,
        )

        if sent:
            item.status = "sent"
            processed += 1
        else:
            remaining += 1

    db.commit()

    return {
        "processed": processed,
        "remaining": remaining,
    }