from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

class Appointment(BaseModel):
    id: str
    session_id: str
    patient_name: str
    patient_age: Optional[int] = None
    patient_phone: Optional[str] = None
    symptoms: Optional[str] = None
    date: str = Field(description="Format YYYY-MM-DD")
    time: str = Field(description="Format HH:MM")
    status: Literal["booked", "rescheduled", "canceled"]
    created_at: datetime = Field(default_factory=datetime.utcnow)
