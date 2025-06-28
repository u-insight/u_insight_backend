# backend/app/main.py
from fastapi import FastAPI
from app.api import auth, reports, admin

app = FastAPI()

# Register routers
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(reports.router, prefix="/reports", tags=["Reports"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
