from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from safecopy.db.enums import BackupVerificationStatus, HashType
from safecopy.utils.uuidUtils import is_valid_uuid


class BackupVerificationDTOBase(BaseModel):
    model_config = ConfigDict(extra="ignore", from_attributes=True)
    backup_history_uuid: str
    checksum_type: HashType = HashType.MD5
    source_checksum: Optional[str] = None
    backup_checksum: Optional[str] = None
    verification_status: BackupVerificationStatus = (
        BackupVerificationStatus.NOT_VERIFIED
    )
    verification_msg: Optional[str] = None
    verified_at: Optional[datetime] = None


class BackupVerificationCreateDTO(BackupVerificationDTOBase):

    @field_validator("backup_history_uuid")
    @classmethod
    def validate_backup_history_uuid(cls, v: str) -> str:
        if not is_valid_uuid(v):
            raise ValueError("Backup history UUID is not valid")
        return v

    @field_validator("checksum_type")
    @classmethod
    def validate_checksum_type(cls, v: HashType) -> HashType:
        if v not in HashType:
            raise ValueError("Checksum type is not valid")
        return v

    @field_validator("verification_status")
    @classmethod
    def validate_verification_status(
        cls, v: BackupVerificationStatus
    ) -> BackupVerificationStatus:
        if v not in BackupVerificationStatus:
            raise ValueError("Verification status is not valid")
        return v


class BackupVerificationUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="ignore", from_attributes=True)
    backup_history_uuid: Optional[str] = None
    checksum_type: Optional[HashType] = None
    source_checksum: Optional[str] = None
    backup_checksum: Optional[str] = None
    verification_status: Optional[BackupVerificationStatus] = None
    verification_msg: Optional[str] = None
    verified_at: Optional[datetime] = None

    @field_validator("backup_history_uuid")
    @classmethod
    def validate_backup_history_uuid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not is_valid_uuid(v):
            raise ValueError("Backup history UUID is not valid")
        return v

    @field_validator("checksum_type")
    @classmethod
    def validate_checksum_type(cls, v: Optional[HashType]) -> Optional[HashType]:
        if v is not None and v not in HashType:
            raise ValueError("Checksum type is not valid")
        return v

    @field_validator("verification_status")
    @classmethod
    def validate_verification_status(
        cls, v: Optional[BackupVerificationStatus]
    ) -> Optional[BackupVerificationStatus]:
        if v is not None and v not in BackupVerificationStatus:
            raise ValueError("Verification status is not valid")
        return v


class BackupVerificationResponseDTO(BackupVerificationDTOBase):
    uuid: str
