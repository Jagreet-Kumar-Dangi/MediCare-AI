from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_token_claims,
    get_current_user,
)
from app.core.config import settings
from app.core.security import AccessTokenClaims, create_access_token
from app.db.session import get_db
from app.models import RevokedToken, User
from app.schemas.auth import (
    DoctorRegistration,
    LoginRequest,
    PatientRegistration,
    TokenResponse,
)
from app.schemas.user import PublicUser
from app.services.auth_service import (
    DoctorRegistrationNumberAlreadyUsedError,
    EmailAlreadyRegisteredError,
    authenticate_user,
    register_doctor,
    register_patient,
)

router = APIRouter(prefix="/auth")


@router.post(
    "/register/patient",
    response_model=PublicUser,
    status_code=status.HTTP_201_CREATED,
)
def register_patient_account(
    registration: PatientRegistration,
    db: Session = Depends(get_db),
) -> User:
    try:
        return register_patient(
            db,
            email=str(registration.email),
            password=registration.password,
            first_name=registration.first_name,
            last_name=registration.last_name,
        )
    except EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from None


@router.post(
    "/register/doctor",
    response_model=PublicUser,
    status_code=status.HTTP_201_CREATED,
)
def register_doctor_account(
    registration: DoctorRegistration,
    db: Session = Depends(get_db),
) -> User:
    try:
        return register_doctor(
            db,
            email=str(registration.email),
            password=registration.password,
            full_name=registration.full_name,
            specialization=registration.specialization,
            qualification=registration.qualification,
            medical_registration_number=registration.medical_registration_number,
            years_of_experience=registration.years_of_experience,
            phone_number=registration.phone_number,
            clinic_or_hospital=registration.clinic_or_hospital,
            consultation_fee=registration.consultation_fee,
            biography=registration.biography,
        )
    except EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from None
    except DoctorRegistrationNumberAlreadyUsedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A doctor with this medical registration number already exists.",
        ) from None


@router.post("/login", response_model=TokenResponse)
def login(
    credentials: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    user = authenticate_user(
        db,
        email=str(credentials.email),
        password=credentials.password,
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(
        access_token=create_access_token(user.id),
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=PublicUser)
def get_authenticated_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    current_user: User = Depends(get_current_user),
    claims: AccessTokenClaims = Depends(get_current_token_claims),
    db: Session = Depends(get_db),
) -> Response:
    if current_user.id != claims.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    db.add(
        RevokedToken(
            token_id=str(claims.token_id),
            expires_at=claims.expires_at,
        )
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
