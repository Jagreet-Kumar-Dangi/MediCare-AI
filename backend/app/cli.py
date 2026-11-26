import argparse
import getpass
import sys

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import User, UserRole


def create_admin() -> int:
    try:
        email = str(
            TypeAdapter(EmailStr).validate_python(input("Admin email: "))
        ).lower()
    except ValidationError:
        print("A valid email address is required.", file=sys.stderr)
        return 2

    password = getpass.getpass("Admin password (12-128 characters): ")
    confirmation = getpass.getpass("Confirm admin password: ")
    if (
        len(password) < 12
        or len(password) > 128
        or not password.strip()
        or password != confirmation
    ):
        print(
            "Passwords must match, contain 12-128 characters, "
            "and include a non-space character.",
            file=sys.stderr,
        )
        return 2

    with SessionLocal() as db:
        if db.scalar(select(User.id).where(User.email == email)) is not None:
            print("An account with this email already exists.", file=sys.stderr)
            return 2
        db.add(
            User(
                email=email,
                password_hash=hash_password(password),
                role=UserRole.ADMIN,
            )
        )
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            print("Administrator account could not be created.", file=sys.stderr)
            return 2

    print("Administrator account created.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Trusted MediCare AI operations.")
    parser.add_argument("command", choices=["create-admin"])
    args = parser.parse_args()
    if args.command == "create-admin":
        return create_admin()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
