from typing import List

from safecopy.db.models import BackupSchedules
from safecopy.db.repos.backupSchedulesRepo import BackupSchedulesRepo
from safecopy.db.services.baseService import BaseService


class BackupSchedulesService(BaseService):
    def __init__(self):
        super().__init__(BackupSchedules, BackupSchedulesRepo)

    def get_schedules_by_mapping(self, mapping_uuid: str) -> List[BackupSchedules]:
        return self.get_all(mapping_uuid=mapping_uuid)
