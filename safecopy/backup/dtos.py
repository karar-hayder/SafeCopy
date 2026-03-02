from datetime import datetime

from pydantic import BaseModel, ConfigDict

from safecopy.backup.enums import BackupStatus, CompressionType


class BackupConfig(BaseModel):
    model_config = ConfigDict(extra="ignore", from_attributes=True)
    uuid: str
    user_uuid: str
    source: str
    destination: str
    encrypted: bool
    passwd: str
    compression: CompressionType
    max_versions: int


class BackupJob(BaseModel):
    id: str
    config: BackupConfig
    status: BackupStatus
    message: str
    progress: float
    created_at: datetime
    updated_at: datetime


class BackupResult(BaseModel):
    id: str
    config: BackupConfig
    status: BackupStatus
    message: str
    duration: float
    size: int
    created_at: datetime
    updated_at: datetime
