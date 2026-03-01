import re
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, field_validator

from safecopy.db.enums import UserRole


class UserBaseDTO(BaseModel):
    model_config = ConfigDict(extra="ignore", from_attributes=True)
    username: str


class UserLoginDTO(BaseModel):
    model_config = ConfigDict(extra="ignore", from_attributes=True)
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_]{3,}$", v):
            raise ValueError(
                "Username must be alphanumeric (underscores allowed) and at least 3 characters long"
            )
        return v


class UserCreateDTO(UserBaseDTO):
    password: str
    role: UserRole = UserRole.USER
    settings: dict[str, Any] = {}

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_]{3,}$", v):
            raise ValueError(
                "Username must be alphanumeric (underscores allowed) and at least 3 characters long"
            )
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class UserUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="ignore", from_attributes=True)
    username: Optional[str] = None
    password: Optional[str] = None
    role: Optional[UserRole] = None
    settings: Optional[dict[str, Any]] = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not re.match(r"^[a-zA-Z0-9_]{3,}$", v):
            raise ValueError(
                "Username must be alphanumeric (underscores allowed) and at least 3 characters long"
            )
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class UserResponseDTO(UserBaseDTO):
    uuid: str
    role: UserRole
    settings: dict[str, Any]
    # Password explicitly omitted
