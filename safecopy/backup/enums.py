from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class BackupStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class CompressionType(Enum):
    NONE = ("none", "")
    ZIP = ("zip", ".zip")
    TAR = ("tar", ".tar.gz")

    @property
    def value_name(self):
        return self.value[0]

    @property
    def extension(self):
        return self.value[1]


@dataclass
class BackupJobStatus:
    id: str = ""
    status: BackupStatus = BackupStatus.PENDING
    message: str = ""
    progress: float = 0.0
    start_time: float = 0.0
    end_time: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
