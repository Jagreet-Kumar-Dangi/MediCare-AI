from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

import app.cli as cli
from app.core.security import verify_password
from app.models import User, UserRole


def test_trusted_admin_provisioning_hashes_password(
    monkeypatch,
    test_engine: Engine,
) -> None:
    password = "trusted-admin-password-123"
    monkeypatch.setattr("builtins.input", lambda _prompt: "Admin@Example.com")
    monkeypatch.setattr(cli.getpass, "getpass", lambda _prompt: password)
    monkeypatch.setattr(cli, "SessionLocal", lambda: Session(test_engine))

    assert cli.create_admin() == 0
    with Session(test_engine) as db:
        admin = db.scalar(select(User).where(User.email == "admin@example.com"))

    assert admin is not None
    assert admin.role == UserRole.ADMIN
    assert verify_password(password, admin.password_hash)
