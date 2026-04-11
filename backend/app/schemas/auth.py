from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    role: str = "student"
    preferred_language: str = "en"


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    preferred_language: str

    model_config = {"from_attributes": True}
