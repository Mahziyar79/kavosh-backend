from pydantic import BaseModel, EmailStr, ConfigDict 
from typing import Optional
from datetime import datetime
from typing import Literal

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class SessionCreate(BaseModel):
    title: Optional[str] = None

class SessionOut(BaseModel):
    id: int
    title: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True) 

class MessageCreate(BaseModel):
    content: str
    role: Literal["user", "assistant"] = "user"

class MessageOut(BaseModel):
    id: int
    content: str
    role: Literal["user", "assistant"]
    user_id: int | None
    created_at: datetime
    class Config:
        from_attributes = True

class SessionUpdate(BaseModel):
    title: Optional[str] = None