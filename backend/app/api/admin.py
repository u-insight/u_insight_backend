# backend/app/api/admin.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def admin_root():
    return {"message": "Admin API placeholder"}
