from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, field_validator


class FindingSchema(BaseModel):
    parameter: Optional[str] = None
    component: Optional[str] = None
    finding: Optional[str] = None
    location: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    previous_value: Optional[float] = None
    normal_value: Optional[float] = None
    status: Optional[str] = None


class InspectionExtract(BaseModel):
    """Schema hasil ekstraksi LLM dari narasi chat."""
    equipment_tag: str
    inspection_date: date
    equipment_type: Optional[str] = None
    operating_status: Optional[str] = None
    findings: List[FindingSchema] = []

    @field_validator("equipment_tag")
    @classmethod
    def upper_tag(cls, v: str) -> str:
        return v.strip().upper()


class ChatRequest(BaseModel):
    message: str
    photo_path: Optional[str] = None
    ai_description: Optional[str] = None


class FindingOut(FindingSchema):
    id: int

    class Config:
        from_attributes = True


class PhotoUploadResponse(BaseModel):
    photo_path: str
    ai_description: str


class InspectionOut(BaseModel):
    id: int
    equipment_tag: str
    inspection_date: date
    equipment_type: Optional[str] = None
    operating_status: Optional[str] = None
    raw_narrative: str
    photo_path: Optional[str] = None
    ai_description: Optional[str] = None
    created_at: datetime
    findings: List[FindingOut] = []

    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    reply: str
    data: InspectionExtract
    saved_id: int
