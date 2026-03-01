from typing import List

from safecopy.db.dtos.backupSchedulesDTOs import (
    BackupSchedulesCreateDTO,
    BackupSchedulesResponseDTO,
    BackupSchedulesUpdateDTO,
)
from safecopy.db.models import BackupSchedules
from safecopy.db.repos.backupSchedulesRepo import BackupSchedulesRepo
from safecopy.db.services.baseService import BaseService


class BackupSchedulesService(BaseService):
    def __init__(self):
        super().__init__(BackupSchedules, BackupSchedulesRepo)
        self.dto_cls = {
            "create": BackupSchedulesCreateDTO,
            "update": BackupSchedulesUpdateDTO,
            "response": BackupSchedulesResponseDTO,
        }

    def get_schedules_by_mapping(
        self, mapping_uuid: str
    ) -> List[BackupSchedulesResponseDTO | BackupSchedules]:
        return self.get_all(mapping_uuid=mapping_uuid)
