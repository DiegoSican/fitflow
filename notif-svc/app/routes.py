from fastapi import (
    APIRouter,
    Depends,
    Request,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Notification
from app.observability import json_log
from app.schemas import (
    NotificationCreate,
    NotificationResponse,
)


router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
)


# =========================================================
# Crear / enviar notificación
# =========================================================

@router.post(
    "",
    response_model=NotificationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_notification(
    notification_data: NotificationCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    correlation_id = request.state.correlation_id

    notification = Notification(
        user_id=notification_data.user_id,
        message=notification_data.message.strip(),
        status="sent",
    )

    db.add(notification)
    db.commit()
    db.refresh(notification)

    json_log(
        service="notif-svc",
        event="notification_sent",
        correlation_id=correlation_id,
        user_id=notification.user_id,
        notification_id=notification.id,
        message=notification.message,
    )

    return notification


# =========================================================
# Historial de notificaciones por usuario
# =========================================================

@router.get(
    "/user/{user_id}",
    response_model=list[NotificationResponse],
)
def get_user_notifications(
    user_id: int,
    db: Session = Depends(get_db),
):
    notifications = db.scalars(
        select(Notification)
        .where(
            Notification.user_id == user_id
        )
        .order_by(
            Notification.created_at.desc()
        )
    ).all()

    return notifications