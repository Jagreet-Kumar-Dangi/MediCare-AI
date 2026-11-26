from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import PatientProfile, RevokedToken, User


@pytest.fixture
def test_engine() -> Generator[Engine, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    expected_tables = {
        model.__tablename__ for model in (User, PatientProfile, RevokedToken)
    }
    Base.metadata.create_all(engine)
    assert expected_tables <= Base.metadata.tables.keys()
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(test_engine: Engine) -> Generator[TestClient, None, None]:
    test_session_factory = sessionmaker(
        bind=test_engine,
        autoflush=False,
        expire_on_commit=False,
    )

    def override_get_db() -> Generator:
        with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def patient_account(client: TestClient) -> dict[str, object]:
    registration = client.post(
        "/api/v1/auth/register/patient",
        json={
            "email": "patient@example.com",
            "password": "a-strong-password-123",
            "first_name": "Avery",
            "last_name": "Patient",
        },
    )
    assert registration.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "patient@example.com",
            "password": "a-strong-password-123",
        },
    )
    assert login.status_code == 200
    return {"user": registration.json(), "token": login.json()["access_token"]}
