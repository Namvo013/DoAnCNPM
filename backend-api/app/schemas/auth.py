from enum import Enum

from pydantic import BaseModel, Field


class AdminRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    AREA_OPERATOR = "area_operator"
    CONTENT_EDITOR = "content_editor"
    ANALYTICS_VIEWER = "analytics_viewer"


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=1, max_length=1024)


class AdminCreate(BaseModel):
    email: str = Field(
        min_length=5,
        max_length=254,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    )
    display_name: str = Field(min_length=1, max_length=200)
    role: AdminRole
    password: str = Field(min_length=12, max_length=1024)


class AdminUpdate(BaseModel):
    email: str | None = Field(
        default=None,
        min_length=5,
        max_length=254,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    )
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    role: AdminRole | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=12, max_length=1024)


class AdminResponse(BaseModel):
    id: str
    email: str
    display_name: str
    role: AdminRole
    is_active: bool
    created_at: str


class AuthMessage(BaseModel):
    message: str


class AdminListResponse(BaseModel):
    items: list[AdminResponse]
    total: int
