from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from safecopy.db.enums import ScheduleIntervalType, ScheduleType
from safecopy.utils.uuidUtils import is_valid_uuid


class BackupSchedulesDTOBase(BaseModel):
    model_config = ConfigDict(extra="ignore", from_attributes=True)
    user_uuid: str
    mapping_uuid: str
    schedule_type: ScheduleType
    schedule_interval: Optional[int] = None
    schedule_interval_type: Optional[ScheduleIntervalType] = None
    enabled: bool = True


class BackupSchedulesCreateDTO(BackupSchedulesDTOBase):
    @field_validator("user_uuid", "mapping_uuid")
    @classmethod
    def validate_uuids(cls, v: str) -> str:
        if not is_valid_uuid(v):
            raise ValueError("UUID is not valid")
        return v

    @field_validator("schedule_type")
    @classmethod
    def validate_schedule_type(cls, v: ScheduleType) -> ScheduleType:
        if v not in ScheduleType:
            raise ValueError("Schedule type is not valid")
        return v

    @field_validator("schedule_interval")
    @classmethod
    def validate_schedule_interval(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Schedule interval must be at least 1")
        return v

    @field_validator("schedule_interval_type")
    @classmethod
    def validate_schedule_interval_type(
        cls, v: ScheduleIntervalType
    ) -> ScheduleIntervalType:
        if v not in ScheduleIntervalType:
            raise ValueError("Schedule interval type is not valid")
        return v

    @field_validator("enabled")
    @classmethod
    def validate_enabled(cls, v: bool) -> bool:
        if v not in [True, False]:
            raise ValueError("Enabled must be True or False")
        return v


class BackupSchedulesUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="ignore", from_attributes=True)
    user_uuid: Optional[str] = None
    mapping_uuid: Optional[str] = None
    schedule_type: Optional[ScheduleType] = None
    schedule_interval: Optional[int] = None
    schedule_interval_type: Optional[ScheduleIntervalType] = None
    enabled: Optional[bool] = None

    @field_validator("user_uuid", "mapping_uuid")
    @classmethod
    def validate_uuids(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not is_valid_uuid(v):
            raise ValueError("UUID is not valid")
        return v

    @field_validator("schedule_type")
    @classmethod
    def validate_schedule_type(
        cls, v: Optional[ScheduleType]
    ) -> Optional[ScheduleType]:
        if v is not None and v not in ScheduleType:
            raise ValueError("Schedule type is not valid")
        return v

    @field_validator("schedule_interval")
    @classmethod
    def validate_schedule_interval(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 1:
            raise ValueError("Schedule interval must be at least 1")
        return v

    @field_validator("schedule_interval_type")
    @classmethod
    def validate_schedule_interval_type(
        cls, v: Optional[ScheduleIntervalType]
    ) -> Optional[ScheduleIntervalType]:
        if v is not None and v not in ScheduleIntervalType:
            raise ValueError("Schedule interval type is not valid")
        return v

    @field_validator("enabled")
    @classmethod
    def validate_enabled(cls, v: Optional[bool]) -> Optional[bool]:
        if v is not None and v not in [True, False]:
            raise ValueError("Enabled must be True or False")
        return v


class BackupSchedulesResponseDTO(BackupSchedulesDTOBase):
    uuid: str
