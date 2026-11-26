from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin_doctors,
    auth,
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
api_router.include_router(patients.router)
api_router.include_router(medical_records.router)
