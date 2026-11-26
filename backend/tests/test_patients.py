from fastapi.testclient import TestClient


def test_patient_can_read_and_update_only_own_profile(
    client: TestClient,
    patient_account: dict,
) -> None:
    authorization = {"Authorization": f"Bearer {patient_account['token']}"}
    profile_response = client.get("/api/v1/patients/me", headers=authorization)

    assert profile_response.status_code == 200
    assert profile_response.json()["first_name"] == "Avery"
    assert profile_response.json()["last_name"] == "Patient"
    assert profile_response.json()["date_of_birth"] is None

    update_response = client.put(
        "/api/v1/patients/me",
        headers=authorization,
        json={
            "first_name": "Updated",
            "last_name": "Patient",
            "date_of_birth": "1990-04-15",
            "phone_number": "+1 555-0100",
        },
    )

    assert update_response.status_code == 200
    assert update_response.json()["first_name"] == "Updated"
    assert update_response.json()["date_of_birth"] == "1990-04-15"
    assert update_response.json()["phone_number"] == "+1 555-0100"


def test_non_patient_cannot_access_patient_profile(client: TestClient) -> None:
    registration = client.post(
        "/api/v1/auth/register/doctor",
        json={
            "email": "doctor@example.com",
            "password": "another-strong-password",
        },
    )
    assert registration.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "doctor@example.com",
            "password": "another-strong-password",
        },
    )

    response = client.get(
        "/api/v1/patients/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )

    assert response.status_code == 403


def test_profile_update_rejects_future_birth_date(
    client: TestClient,
    patient_account: dict,
) -> None:
    response = client.put(
        "/api/v1/patients/me",
        headers={"Authorization": f"Bearer {patient_account['token']}"},
        json={
            "first_name": "Avery",
            "last_name": "Patient",
            "date_of_birth": "2999-01-01",
            "phone_number": None,
        },
    )

    assert response.status_code == 422
