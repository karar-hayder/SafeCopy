from typing import List, Optional

from safecopy.db.models import BackupVerification
from safecopy.db.repos.backupVerificationRepo import BackupVerificationRepo
from safecopy.db.session import get_session


class BackupVerificationService:
    def create_verification(self, **kwargs) -> BackupVerification:
        with get_session() as session:
            verification = BackupVerification(**kwargs)
            session.add(verification)
            session.flush()
            return verification

    def get_all_verifications(self) -> List[BackupVerification]:
        with get_session() as session:
            repo = BackupVerificationRepo(session)
            return repo.get_all()

    def get_verification(self, uuid: str) -> Optional[BackupVerification]:
        with get_session() as session:
            repo = BackupVerificationRepo(session)
            return repo.get_by_uuid(uuid)

    def get_verifications_by_history(
        self, history_uuid: str
    ) -> List[BackupVerification]:
        with get_session() as session:
            repo = BackupVerificationRepo(session)
            return repo.get_by_history_uuid(history_uuid)

    def delete_verification(self, uuid: str) -> bool:
        with get_session() as session:
            repo = BackupVerificationRepo(session)
            verification = repo.get_by_uuid(uuid)
            if verification:
                session.delete(verification)
                return True
            return False
