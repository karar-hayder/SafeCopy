from pydantic import BaseModel, ConfigDict, field_validator

from safecopy.db.enums import CompressionType, PasswdMode
from safecopy.utils.uuidUtils import is_valid_uuid


class MappingsBaseDTO(BaseModel):
    model_config = ConfigDict(extra="ignore", from_attributes=True)
    user_uuid: str
    source: str
    destination: str
    max_versions: int
    compression: CompressionType
    enabled: bool
    encrypted: bool
    passwd_mode: PasswdMode


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
        if not v.startswith("/"):
            raise ValueError("Path must start with /")
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

    @field_validator("compression")
    @classmethod
    def validate_compression(cls, v: CompressionType) -> CompressionType:
        if v not in [CompressionType.NONE, CompressionType.GZIP]:
            raise ValueError("Invalid compression type")
        return v


class MappingsUpdateDTO(MappingsBaseDTO):
    @field_validator("user_uuid")
    @classmethod
    def validate_user_uuid(cls, v: str) -> str:
        if not is_valid_uuid(v):
            raise ValueError("User UUID is not valid")
        return v

    @field_validator("source", "destination")
    @classmethod
    def validate_paths(cls, v: str) -> str:
        if not v.startswith("/"):
            raise ValueError("Path must start with /")
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

    @field_validator("compression")
    @classmethod
    def validate_compression(cls, v: CompressionType) -> CompressionType:
        if v not in [CompressionType.NONE, CompressionType.GZIP]:
            raise ValueError("Invalid compression type")
        return v


class MappingsResponseDTO(MappingsBaseDTO):
    uuid: str
