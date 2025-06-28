from pydantic import BaseModel, Field
from typing import Optional

class ReportCreate(BaseModel):
    title: str = Field(..., example="Broken Streetlight")
    description: str = Field(..., example="The streetlight near the main gate is not working.")
    category: str = Field(..., example="Infrastructure")
    urgency: str = Field(..., example="High")
    lat: float = Field(..., example=37.5665)
    lng: float = Field(..., example=126.9780)