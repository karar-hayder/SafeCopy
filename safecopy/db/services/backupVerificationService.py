from typing import List

from safecopy.db.dtos.backupVerificationDTOs import (
    BackupVerificationCreateDTO,
    BackupVerificationResponseDTO,
    BackupVerificationUpdateDTO,
)
from safecopy.db.models import BackupVerification
from safecopy.db.repos.backupVerificationRepo import BackupVerificationRepo
from safecopy.db.services.baseService import BaseService


class BackupVerificationService(BaseService):
    def __init__(self):
        super().__init__(BackupVerification, BackupVerificationRepo)
        self.dto_cls = {
            "create": BackupVerificationCreateDTO,
            "update": BackupVerificationUpdateDTO,
            "response": BackupVerificationResponseDTO,
        }

    def get_verifications_by_history(
        self, history_uuid: str
    ) -> List[BackupVerificationResponseDTO | BackupVerification]:
        return self.get_all(backup_history_uuid=history_uuid)
