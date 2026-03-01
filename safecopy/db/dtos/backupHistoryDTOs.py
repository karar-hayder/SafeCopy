from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from safecopy.db.enums import BackupStatus
from safecopy.utils.uuidUtils import is_valid_uuid


class BackupHistoryDTOBase(BaseModel):
    model_config = ConfigDict(extra="ignore", from_attributes=True)
    user_uuid: str
    mapping_uuid: str
    status: BackupStatus = BackupStatus.PENDING
    message: Optional[str] = None
    duration: float = 0.0
    size_bytes: int = 0
    backup_path: Optional[str] = None


class BackupHistoryCreateDTO(BackupHistoryDTOBase):
    @field_validator("user_uuid", "mapping_uuid")
    @classmethod
    def validate_uuids(cls, v: str) -> str:
        if not is_valid_uuid(v):
            raise ValueError("UUID is not valid")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: BackupStatus) -> BackupStatus:
        if v not in BackupStatus:
            raise ValueError("Status is not valid")
        return v

    @field_validator("duration")
    @classmethod
    def validate_duration(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Duration cannot be negative")
        return v

    @field_validator("size_bytes")
    @classmethod
    def validate_size_bytes(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Size cannot be negative")
        return v

    @field_validator("backup_path")
    @classmethod
    def validate_backup_path(cls, v: str) -> str:
        if not v:
            raise ValueError("Backup path cannot be empty")
        return v


class BackupHistoryUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="ignore", from_attributes=True)
    user_uuid: Optional[str] = None
    mapping_uuid: Optional[str] = None
    status: Optional[BackupStatus] = None
    message: Optional[str] = None
    duration: Optional[float] = None
    size_bytes: Optional[int] = None
    backup_path: Optional[str] = None

    @field_validator("user_uuid", "mapping_uuid")
    @classmethod
    def validate_uuids(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not is_valid_uuid(v):
            raise ValueError("UUID is not valid")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[BackupStatus]) -> Optional[BackupStatus]:
        if v is not None and v not in BackupStatus:
            raise ValueError("Status is not valid")
        return v

    @field_validator("duration")
    @classmethod
    def validate_duration(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("Duration cannot be negative")
        return v

    @field_validator("size_bytes")
    @classmethod
    def validate_size_bytes(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("Size cannot be negative")
        return v

    @field_validator("backup_path")
    @classmethod
    def validate_backup_path(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v:
            raise ValueError("Backup path cannot be empty")
        return v


class BackupHistoryResponseDTO(BackupHistoryDTOBase):
    uuid: str
    timestamp: datetime
    created_at: datetime
    updated_at: datetime
