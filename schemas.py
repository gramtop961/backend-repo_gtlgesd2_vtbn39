from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal
from datetime import datetime

# NOTE: Each model name defines the collection name in lowercase
# User -> "user", Employee -> "employee", Log -> "log"

class User(BaseModel):
    email: EmailStr
    role: Literal["admin", "analyst"] = "analyst"
    created_at: Optional[datetime] = None

class Employee(BaseModel):
    name: str
    role: str
    location: str
    threatScore: int = Field(0, ge=0, le=100)
    created_at: Optional[datetime] = None

class Log(BaseModel):
    time: datetime
    event: str
    employee: str
    severity: Literal["low", "medium", "high"] = "low"
    created_at: Optional[datetime] = None
