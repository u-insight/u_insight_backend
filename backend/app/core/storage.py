import uuid
import firebase_admin
from firebase_admin import storage
from fastapi import UploadFile

def upload_report_image(file: UploadFile) -> str:
    bucket = storage.bucket()
    blob = bucket.blob(f"report_images/{uuid.uuid4()}.jpg")
    blob.upload_from_file(file.file, content_type=file.content_type)
    blob.make_public()
    return blob.public_url