from fastapi import APIRouter, Depends, HTTPException, Body, Query
from datetime import datetime
from collections import defaultdict
from typing import Optional
from pydantic import BaseModel

from app.core.firebase import db
from app.core.auth_dependency import get_current_user, get_admin_user
from app.models.reports import ReportCreate
import uuid
from firebase_admin import storage
from typing import List
router = APIRouter()
from fastapi import UploadFile, File, Form
from app.core.storage import upload_report_image



@router.post("/")
async def create_report(
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    urgency: str = Form(...),
    lat: float = Form(...),
    lng: float = Form(...),
    files: List[UploadFile] = File([]),
    user=Depends(get_current_user)
):
    try:
        # Upload images to Firebase Storage
        image_urls = []
        for file in files:
            if file.content_type.startswith("image/"):
                filename = f"reports/{uuid.uuid4().hex}_{file.filename}"
                blob = storage.bucket().blob(filename)
                blob.upload_from_file(file.file, content_type=file.content_type)
                blob.make_public()  # remove this in prod for private URLs
                image_urls.append(blob.public_url)

        # Create new report document
        new_report = {
            "title": title,
            "description": description,
            "category": category,
            "urgency": urgency,
            "status": "미시작",
            "location": {"lat": lat, "lng": lng},
            "user_id": user["uid"],
            "created_at": datetime.utcnow().isoformat(),
            "images": image_urls  # list of URLs
        }

        db.collection("reports").add(new_report)
        return {"message": "Report with image(s) submitted successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ✅ Public: Placeholder
@router.get("/")
def get_reports():
    return {"message": "Reports coming soon"}

# 📝 User: Submit new report
@router.post("/")
def create_report(report: ReportCreate, user=Depends(get_current_user)):
    try:
        new_report = {
            "title": report.title,
            "description": report.description,
            "category": report.category,
            "urgency": report.urgency,
            "status": "미시작",
            "location": {"lat": report.lat, "lng": report.lng},
            "user_id": user["uid"],
            "created_at": datetime.utcnow().isoformat()
        }
        db.collection("reports").add(new_report)
        return {"message": "Report submitted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 👤 User: Get my reports
@router.get("/mine")
def get_my_reports(user=Depends(get_current_user)):
    query = db.collection("reports").where("user_id", "==", user["uid"]).stream()
    reports = [{**doc.to_dict(), "doc_id": doc.id} for doc in query]
    return reports

# ✅ Public or Authenticated: View report by ID
@router.get("/{report_id}")
def get_report_detail(report_id: str):
    report_ref = db.collection("reports").document(report_id).get()
    if not report_ref.exists:
        raise HTTPException(status_code=404, detail="Report not found")
    return {**report_ref.to_dict(), "doc_id": report_id}

# ❌ User/Admin: Delete report
@router.delete("/{report_id}")
def delete_report(report_id: str, user=Depends(get_current_user)):
    doc_ref = db.collection("reports").document(report_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Report not found")

    doc_data = doc.to_dict()
    is_owner = doc_data.get("user_id") == user["uid"]
    is_admin = user.get("is_admin", False)

    if not is_owner and not is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to delete this report")

    doc_ref.delete()
    return {"message": "Report deleted successfully", "report_id": report_id}

# 🔐 Admin-only: All reports
@router.get("/admin/all")
def get_all_reports(admin=Depends(get_admin_user)):
    query = db.collection("reports").stream()
    reports = [{**doc.to_dict(), "doc_id": doc.id} for doc in query]
    return reports

# 🔐 Admin-only: Update status by path
@router.patch("/admin/{report_id}/status")
def update_report_status_by_path(
    report_id: str,
    status: str = Body(..., embed=True),
    admin=Depends(get_admin_user)
):
    report_ref = db.collection("reports").document(report_id)
    report = report_ref.get()
    if not report.exists:
        raise HTTPException(status_code=404, detail="Report not found")

    report_ref.update({"status": status})
    return {
        "message": "Status updated successfully",
        "report_id": report_id,
        "new_status": status
    }

# 🔐 Admin-only: Update status with embedded doc_id
@router.patch("/admin/update-status")
def update_status(
    doc_id: str = Body(..., embed=True),
    status: str = Body(..., embed=True),
    admin=Depends(get_admin_user)
):
    valid_statuses = ["미시작", "진행중", "완료"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")

    report_ref = db.collection("reports").document(doc_id)
    if not report_ref.get().exists:
        raise HTTPException(status_code=404, detail="Report not found")

    report_ref.update({"status": status})
    return {"message": "Status updated successfully"}

# 🔍 Admin-only: Filter reports
@router.get("/admin/filter")
def filter_reports(
    category: Optional[str] = Query(None),
    urgency: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    admin=Depends(get_admin_user)
):
    query_ref = db.collection("reports")
    if category:
        query_ref = query_ref.where("category", "==", category)
    if urgency:
        query_ref = query_ref.where("urgency", "==", urgency)
    if status:
        query_ref = query_ref.where("status", "==", status)

    query = query_ref.stream()
    reports = [{**doc.to_dict(), "doc_id": doc.id} for doc in query]
    return reports

# 📍 Admin-only: Map data
@router.get("/admin/map")
def map_reports(admin=Depends(get_admin_user)):
    query = db.collection("reports").stream()
    reports = []
    for doc in query:
        data = doc.to_dict()
        if "lat" in data and "lng" in data:
            reports.append({
                "doc_id": doc.id,
                "title": data.get("title", ""),
                "category": data.get("category", ""),
                "urgency": data.get("urgency", ""),
                "status": data.get("status", ""),
                "lat": data["lat"],
                "lng": data["lng"]
            })
    return reports

# 📊 Admin-only: Stats
@router.get("/admin/stats")
def get_report_stats(admin=Depends(get_admin_user)):
    reports = db.collection("reports").stream()
    status_count = defaultdict(int)
    category_count = defaultdict(int)
    for doc in reports:
        data = doc.to_dict()
        status_count[data.get("status", "Unknown")] += 1
        category_count[data.get("category", "Unknown")] += 1
    return {
        "status_summary": dict(status_count),
        "category_summary": dict(category_count)
    }

# 📍 Admin-only: Map data (another version)
@router.get("/admin/reports/map")
def get_reports_for_map(admin=Depends(get_admin_user)):
    reports = db.collection("reports").stream()
    map_data = []
    for doc in reports:
        data = doc.to_dict()
        if "location" not in data:
            continue
        map_data.append({
            "id": doc.id,
            "title": data.get("title", "No Title"),
            "category": data.get("category", "Unknown"),
            "status": data.get("status", "미시작"),
            "latitude": data["location"].get("latitude"),
            "longitude": data["location"].get("longitude")
        })
    return {"reports": map_data}

# 📄 Admin-only: Report detail
@router.get("/admin/reports/detail")
def get_report_detail_admin(doc_id: str = Query(...), admin=Depends(get_admin_user)):
    doc = db.collection("reports").document(doc_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Report not found")
    return doc.to_dict()

# 🛠️ Admin-only: Update with Pydantic model
class StatusUpdate(BaseModel):
    doc_id: str
    new_status: str  # ex: "미시작", "진행중", "완료"

@router.patch("/admin/reports/status")
def update_report_status(data: StatusUpdate, admin=Depends(get_admin_user)):
    doc_ref = db.collection("reports").document(data.doc_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Report not found")
    doc_ref.update({"status": data.new_status})
    return {"message": "Status updated successfully", "new_status": data.new_status}
