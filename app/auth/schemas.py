from pydantic import BaseModel, EmailStr
from app.models import RoleEnum

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: RoleEnum

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    name: str
    role: RoleEnum

class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: RoleEnum
    model_config = {"from_attributes": True}
