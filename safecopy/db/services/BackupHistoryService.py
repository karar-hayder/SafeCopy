from typing import Optional

from safecopy.db.models import BackupHistory
from safecopy.db.repos.backupHistoryRepo import BackupHistoryRepo
from safecopy.db.services.baseService import BaseService


class BackupHistoryService(BaseService):
    def __init__(self):
        super().__init__(BackupHistory, BackupHistoryRepo)

    def get_by_mapping_uuid(self, mapping_uuid: str) -> Optional[BackupHistory]:
        return self.get_one(mapping_uuid=mapping_uuid)

    def get_by_success(self, success: int) -> Optional[BackupHistory]:
        return self.get_one(success=success)
