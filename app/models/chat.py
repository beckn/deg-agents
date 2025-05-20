from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    query: str
    client_id: str


class ChatResponse(BaseModel):
    status: str
    query: str
    client_id: str
    message: str
    auth_state: Optional[str] = None
    token: Optional[str] = None
    meter_id: Optional[str] = None


class AuthRequest(BaseModel):
    meter_id: str
    otp: Optional[str] = None


class AuthResponse(BaseModel):
    status: str
    message: str
    token: Optional[str] = None
