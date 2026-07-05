from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=1, max_length=255)
    timezone: str = "Asia/Saigon"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    name: str
    timezone: str
    role: str


class AuthResponse(BaseModel):
    user: UserResponse
