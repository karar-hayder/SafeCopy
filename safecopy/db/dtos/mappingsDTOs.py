from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, field_validator

from safecopy.db.enums import CompressionType, PasswdMode
from safecopy.utils.uuidUtils import is_valid_uuid


class MappingsBaseDTO(BaseModel):
    model_config = ConfigDict(extra="ignore", from_attributes=True)
    user_uuid: str
    source: str
    destination: str
    max_versions: int = 3
    compression: CompressionType = CompressionType.NONE
    enabled: bool = True
    encrypted: bool = False
    passwd_mode: PasswdMode = PasswdMode.NONE


class MappingsCreateDTO(MappingsBaseDTO):
    @field_validator("user_uuid")
    @classmethod
    def validate_user_uuid(cls, v: str) -> str:
        if not is_valid_uuid(v):
            raise ValueError("User UUID is not valid")
        return v

    @field_validator("source", "destination")
    @classmethod
    def validate_paths(cls, v: str) -> str:
        # Support Windows drive letters or standard absolute paths
        import os

        if not os.path.isabs(v) and not (
            len(v) > 2 and v[1:3] == ":/" or v[1:3] == ":\\"
        ):
            if not v.startswith("/"):
                raise ValueError("Path must be absolute")
        return v

    @field_validator("max_versions")
    @classmethod
    def validate_max_versions(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Max versions must be at least 1")
        return v

    @field_validator("enabled", "encrypted")
    @classmethod
    def validate_enabled_encrypted(cls, v: bool) -> bool:
        if v not in [True, False]:
            raise ValueError("Enabled and encrypted must be True or False")
        return v

    @field_validator("passwd_mode")
    @classmethod
    def validate_passwd_mode(cls, v: PasswdMode) -> PasswdMode:
        if v not in [PasswdMode.NONE, PasswdMode.PASSWORD, PasswdMode.SYSTEM]:
            raise ValueError("Invalid password mode")
        return v

    @field_validator("compression", mode="before")
    @classmethod
    def validate_compression(cls, v: Any) -> CompressionType:
        if v == "" or v is None:
            return CompressionType.NONE
        if isinstance(v, str):
            try:
                return CompressionType(v.lower())
            except ValueError:
                raise ValueError(f"Invalid compression type: {v}")
        return v


class MappingsUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="ignore", from_attributes=True)
    user_uuid: Optional[str] = None
    source: Optional[str] = None
    destination: Optional[str] = None
    max_versions: Optional[int] = None
    compression: Optional[CompressionType] = None
    enabled: Optional[bool] = None
    encrypted: Optional[bool] = None
    passwd_mode: Optional[PasswdMode] = None

    @field_validator("compression", mode="before")
    @classmethod
    def validate_compression(cls, v: Any) -> Optional[CompressionType]:
        if v == "" or v is None:
            return None  # Or CompressionType.NONE depending on intent, but Update usually means "keep as is" if None
        if isinstance(v, str):
            try:
                return CompressionType(v.lower())
            except ValueError:
                raise ValueError(f"Invalid compression type: {v}")
        return v

    @field_validator("user_uuid")
    @classmethod
    def validate_user_uuid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not is_valid_uuid(v):
            raise ValueError("User UUID is not valid")
        return v

    @field_validator("source", "destination")
    @classmethod
    def validate_paths(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            import os

            if not os.path.isabs(v) and not (
                len(v) > 2 and v[1:3] == ":/" or v[1:3] == ":\\"
            ):
                if not v.startswith("/"):
                    raise ValueError("Path must be absolute")
        return v

    @field_validator("max_versions")
    @classmethod
    def validate_max_versions(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 1:
            raise ValueError("Max versions must be at least 1")
        return v


class MappingsResponseDTO(MappingsBaseDTO):
    uuid: str
