from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.notifications import NotificationJobChannel, NotificationJobStatus
from app.db.session import get_db
from app.models import (
    Notification,
    NotificationJob,
    NotificationPreference,
    User,
)
from app.schemas.notifications import (
    NotificationPreferencesResponse,
    NotificationPreferencesUpdate,
    NotificationResponse,
)
from app.services.notification_service import refresh_reminder_jobs_for_user

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _preferences_response(
    preference: NotificationPreference | None,
) -> NotificationPreferencesResponse:
    if preference is None:
        return NotificationPreferencesResponse(
            email_enabled=True,
            in_app_enabled=True,
            reminder_24h_enabled=True,
            reminder_1h_enabled=True,
        )
    return NotificationPreferencesResponse.model_validate(preference)


@router.get("", response_model=list[NotificationResponse])
def list_notifications(
    unread_only: bool = False,
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Notification]:
    statement = select(Notification).where(
        Notification.recipient_user_id == current_user.id
    )
    if unread_only:
        statement = statement.where(Notification.read_at.is_(None))
    return list(
        db.scalars(
            statement.order_by(
                Notification.created_at.desc(),
                Notification.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
    )


@router.get("/unread-count")
def unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, int]:
    count = db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.recipient_user_id == current_user.id,
            Notification.read_at.is_(None),
        )
    )
    return {"unread_count": count or 0}


@router.patch("/read-all")
def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, int]:
    result = db.execute(
        update(Notification)
        .where(
            Notification.recipient_user_id == current_user.id,
            Notification.read_at.is_(None),
        )
        .values(read_at=datetime.now(timezone.utc))
    )
    db.commit()
    return {"updated_count": result.rowcount or 0}


@router.get("/preferences", response_model=NotificationPreferencesResponse)
def get_notification_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationPreferencesResponse:
    return _preferences_response(
        db.get(NotificationPreference, current_user.id)
    )


@router.put("/preferences", response_model=NotificationPreferencesResponse)
def update_notification_preferences(
    payload: NotificationPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationPreferencesResponse:
    preference = db.get(NotificationPreference, current_user.id)
    if preference is None:
        preference = NotificationPreference(user_id=current_user.id)
        db.add(preference)

    preference.email_enabled = payload.email_enabled
    preference.in_app_enabled = payload.in_app_enabled
    preference.reminder_24h_enabled = payload.reminder_24h_enabled
    preference.reminder_1h_enabled = payload.reminder_1h_enabled
    preference.updated_at = datetime.now(timezone.utc)

    now = datetime.now(timezone.utc)
    if not preference.email_enabled:
        db.execute(
            update(NotificationJob)
            .where(
                NotificationJob.recipient_user_id == current_user.id,
                NotificationJob.channel == NotificationJobChannel.EMAIL.value,
                NotificationJob.status == NotificationJobStatus.PENDING.value,
            )
            .values(
                status=NotificationJobStatus.SKIPPED.value,
                last_error="email_disabled",
                next_attempt_at=None,
                completed_at=now,
                updated_at=now,
            )
        )
    refresh_reminder_jobs_for_user(
        db,
        user=current_user,
        preference=preference,
    )
    db.commit()
    db.refresh(preference)
    return _preferences_response(preference)


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Notification:
    notification = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.recipient_user_id == current_user.id,
        )
    )
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )
    if notification.read_at is None:
        notification.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(notification)
    return notification


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    result = db.execute(
        delete(Notification).where(
            Notification.id == notification_id,
            Notification.recipient_user_id == current_user.id,
        )
    )
    if not result.rowcount:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
