from typing import Optional

from safecopy.db.dtos.backupHistoryDTOs import (
    BackupHistoryCreateDTO,
    BackupHistoryResponseDTO,
    BackupHistoryUpdateDTO,
)
from safecopy.db.models import BackupHistory
from safecopy.db.repos.backupHistoryRepo import BackupHistoryRepo
from safecopy.db.services.baseService import BaseService


class BackupHistoryService(BaseService):
    def __init__(self):
        super().__init__(BackupHistory, BackupHistoryRepo)
        self.dto_cls = {
            "create": BackupHistoryCreateDTO,
            "update": BackupHistoryUpdateDTO,
            "response": BackupHistoryResponseDTO,
        }

    def get_by_mapping_uuid(
        self, mapping_uuid: str
    ) -> Optional[BackupHistoryResponseDTO | BackupHistory]:
        return self.get_one(mapping_uuid=mapping_uuid)

    def get_by_success(
        self, success: int
    ) -> Optional[BackupHistoryResponseDTO | BackupHistory]:
        return self.get_one(success=success)
