from fastapi import APIRouter, HTTPException, Depends
from app.models.user import UserCreate, UserLogin
from app.core.security import hash_password, verify_password, create_access_token
from app.core.firebase import db
from app.core.auth_dependency import get_current_user, get_admin_user
from datetime import timedelta

router = APIRouter()

@router.post("/register")
def register(user: UserCreate):
    user_ref = db.collection("users").where("email", "==", user.email).stream()
    if any(user_ref):
        raise HTTPException(status_code=400, detail="User already exists")

    hashed = hash_password(user.password)
    new_user = {"email": user.email, "password": hashed, "is_admin": False}
    db.collection("users").add(new_user)
    return {"message": "User registered successfully"}

@router.post("/login")
def login(user: UserLogin):
    user_query = db.collection("users").where("email", "==", user.email).stream()
    user_doc = next(user_query, None)

    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    user_data = user_doc.to_dict()
    if not verify_password(user.password, user_data["password"]):
        raise HTTPException(status_code=401, detail="Incorrect password")

    token = create_access_token(data={
        "sub": user_doc.id,
        "is_admin": user_data.get("is_admin", False)
    })

    return {"access_token": token, "token_type": "bearer"}

@router.get("/me")
def get_profile(current_user=Depends(get_current_user)):
    return current_user

@router.get("/admin/data")
def get_admin_data(admin=Depends(get_admin_user)):
    return {"message": "You are an admin"}
