from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ApiModel


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=200)


class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=10, max_length=200)


class UserOut(ApiModel):
    id: int
    email: str
    display_name: str
    roles: list[str]
    permissions: list[str]


class TokenOut(ApiModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut
