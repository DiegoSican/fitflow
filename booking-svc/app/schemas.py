from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ClassResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    instructor: str
    capacity: int
    scheduled_at: datetime