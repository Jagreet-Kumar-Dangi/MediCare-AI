import html
import smtplib
import ssl
from dataclasses import dataclass
from email.utils import formataddr
from email.message import EmailMessage
from urllib.parse import urljoin

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.notifications import NotificationType
from app.models import Appointment, NotificationJob, User, UserRole
from app.services.notification_service import clinic_time_label


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    text: str
    html: str


def smtp_is_configured() -> bool:
    return bool(settings.smtp_host and settings.smtp_from_email)


def render_appointment_email(
    db: Session,
    *,
    job: NotificationJob,
    recipient: User,
) -> RenderedEmail:
    appointment = db.scalar(
        select(Appointment)
        .options(
            selectinload(Appointment.patient).selectinload(User.patient_profile),
            selectinload(Appointment.doctor_profile),
        )
        .where(Appointment.id == job.appointment_id)
    )
    if appointment is None:
        raise LookupError("Appointment was not found for notification.")

    doctor_name = appointment.doctor_profile.full_name
    patient_profile = appointment.patient.patient_profile
    patient_name = (
        f"{patient_profile.first_name} {patient_profile.last_name}"
        if patient_profile is not None
        else "Patient"
    )
    is_patient = recipient.role == UserRole.PATIENT
    contact_name = doctor_name if is_patient else patient_name
    event_type = NotificationType(job.notification_type)
    event_subjects = {
        NotificationType.APPOINTMENT_BOOKED: "Appointment request received",
        NotificationType.APPOINTMENT_CONFIRMED: "Appointment confirmed",
        NotificationType.APPOINTMENT_CANCELLED: "Appointment cancelled",
        NotificationType.APPOINTMENT_RESCHEDULED: "Appointment rescheduled",
        NotificationType.APPOINTMENT_COMPLETED: "Appointment completed",
        NotificationType.APPOINTMENT_REMINDER_24H: "Appointment reminder",
        NotificationType.APPOINTMENT_REMINDER_1H: "Appointment reminder",
    }
    subject = event_subjects[event_type]
    appointment_time = clinic_time_label(job.appointment_start_at)
    status_label = (
        job.notification_type.removeprefix("APPOINTMENT_")
        if job.channel == "EMAIL"
        else appointment.status
    )
    headline = f"{subject}: {contact_name}"
    frontend_base = (
        str(settings.frontend_base_url).rstrip("/")
        if settings.frontend_base_url is not None
        else None
    )
    application_path = "/appointments" if is_patient else "/doctor/dashboard"
    link = (
        urljoin(f"{frontend_base}/", application_path.lstrip("/"))
        if frontend_base
        else None
    )
    text_lines = [
        "MediCare AI appointment update",
        "",
        headline,
        f"Appointment date and time: {appointment_time}",
        f"Status: {status_label}",
    ]
    if link:
        text_lines.extend(["", f"Open MediCare AI: {link}"])

    escaped_headline = html.escape(headline)
    escaped_contact = html.escape(contact_name)
    escaped_time = html.escape(appointment_time)
    escaped_status = html.escape(status_label)
    link_markup = (
        f'<p><a href="{html.escape(link, quote=True)}">Open MediCare AI</a></p>'
        if link
        else ""
    )
    html_body = (
        "<!doctype html><html><body>"
        '<main style="font-family:Arial,sans-serif;max-width:560px;margin:24px auto;'
        'padding:24px;color:#17233b;border:1px solid #dce5ef;border-radius:12px">'
        '<p style="color:#176b82;font-weight:bold">MediCare AI</p>'
        f"<h1 style=\"font-size:22px\">{escaped_headline}</h1>"
        f"<p>This appointment is with {escaped_contact}.</p>"
        f"<p><strong>Date and time:</strong> {escaped_time}</p>"
        f"<p><strong>Status:</strong> {escaped_status}</p>"
        "<p>This message contains no medical records or visit notes.</p>"
        f"{link_markup}</main></body></html>"
    )
    return RenderedEmail(
        subject=subject,
        text="\n".join(text_lines),
        html=html_body,
    )


def send_email(recipient_email: str, rendered: RenderedEmail) -> None:
    if not smtp_is_configured():
        raise RuntimeError("SMTP is not configured.")

    message = EmailMessage()
    message["From"] = formataddr((settings.smtp_from_name, str(settings.smtp_from_email)))
    message["To"] = recipient_email
    message["Subject"] = rendered.subject
    message.set_content(rendered.text)
    message.add_alternative(rendered.html, subtype="html")

    if settings.smtp_use_ssl:
        with smtplib.SMTP_SSL(
            settings.smtp_host,
            settings.smtp_port,
            timeout=15,
            context=ssl.create_default_context(),
        ) as server:
            if settings.smtp_username and settings.smtp_password:
                server.login(
                    settings.smtp_username,
                    settings.smtp_password.get_secret_value(),
                )
            server.send_message(message)
        return

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
        if settings.smtp_use_tls:
            server.starttls(context=ssl.create_default_context())
        if settings.smtp_username and settings.smtp_password:
            server.login(
                settings.smtp_username,
                settings.smtp_password.get_secret_value(),
            )
        server.send_message(message)
