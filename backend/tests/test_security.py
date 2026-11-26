import pytest

from app.core.security import hash_password, verify_password


def test_password_hash_verifies_only_matching_password() -> None:
    password_hash = hash_password("correct horse battery staple")

    assert password_hash.startswith("$argon2id$")
    assert password_hash != "correct horse battery staple"
    assert verify_password("correct horse battery staple", password_hash)
    assert not verify_password("incorrect password", password_hash)


def test_each_password_hash_uses_a_unique_salt() -> None:
    first_hash = hash_password("same password")
    second_hash = hash_password("same password")

    assert first_hash != second_hash
    assert verify_password("same password", first_hash)
    assert verify_password("same password", second_hash)


def test_malformed_hash_does_not_verify() -> None:
    assert not verify_password("password", "not-a-valid-hash")


def test_empty_password_is_rejected() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        hash_password("")
