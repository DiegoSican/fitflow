from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ClassResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    instructor: str
    capacity: int
    scheduled_at: datetime

class BookingCreate(BaseModel):
    class_id: int


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    class_id: int
    status: str
    created_at: datetime