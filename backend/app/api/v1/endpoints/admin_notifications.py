from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.core.notifications import NotificationJobChannel, NotificationJobStatus
from app.db.session import get_db
from app.models import NotificationJob, User, UserRole
from app.schemas.notifications import (
    NotificationJobAdminListResponse,
    NotificationJobAdminResponse,
)

router = APIRouter(prefix="/admin/notifications", tags=["admin notifications"])
_require_admin = require_role(UserRole.ADMIN)


def _mask_email(email: str) -> str:
    local_part, separator, domain = email.partition("@")
    if not separator:
        return "***"
    return f"{local_part[:1]}***@{domain}"


@router.get(
    "/jobs",
    response_model=NotificationJobAdminListResponse,
)
def list_notification_jobs(
    job_status: NotificationJobStatus | None = Query(
        default=None,
        alias="status",
    ),
    channel: NotificationJobChannel | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_admin: User = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> NotificationJobAdminListResponse:
    del current_admin
    statement = select(NotificationJob, User.email).join(
        User,
        User.id == NotificationJob.recipient_user_id,
    )
    count_statement = (
        select(func.count())
        .select_from(NotificationJob)
        .join(User, User.id == NotificationJob.recipient_user_id)
    )
    if job_status is not None:
        condition = NotificationJob.status == job_status.value
        statement = statement.where(condition)
        count_statement = count_statement.where(condition)
    if channel is not None:
        condition = NotificationJob.channel == channel.value
        statement = statement.where(condition)
        count_statement = count_statement.where(condition)

    rows = db.execute(
        statement.order_by(
            NotificationJob.created_at.desc(),
            NotificationJob.id.desc(),
        )
        .limit(limit)
        .offset(offset)
    ).all()
    jobs = [
        NotificationJobAdminResponse(
            id=job.id,
            notification_type=job.notification_type,
            channel=job.channel,
            status=job.status,
            recipient_masked=_mask_email(email),
            scheduled_at=job.scheduled_at,
            attempt_count=job.attempt_count,
            next_attempt_at=job.next_attempt_at,
            last_error=job.last_error,
            created_at=job.created_at,
        )
        for job, email in rows
    ]
    return NotificationJobAdminListResponse(
        jobs=jobs,
        total=db.scalar(count_statement) or 0,
        limit=limit,
        offset=offset,
    )
