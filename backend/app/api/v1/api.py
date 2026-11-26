from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin_doctor_credentials,
    admin_appointments,
    admin_doctors,
    appointments,
    auth,
    doctor_appointments,
    doctor_availability,
    doctor_credentials,
    doctors,
    health,
    medical_records,
    patients,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, tags=["authentication"])
api_router.include_router(doctors.router)
api_router.include_router(admin_doctors.router)
api_router.include_router(doctor_credentials.router)
api_router.include_router(admin_doctor_credentials.router)
api_router.include_router(doctor_availability.router)
api_router.include_router(appointments.router)
api_router.include_router(doctor_appointments.router)
api_router.include_router(admin_appointments.router)
api_router.include_router(patients.router)
api_router.include_router(medical_records.router)
