from typing import List, Optional

from sqlalchemy import select

from safecopy.db.models import BackupVerification


class BackupVerificationRepo:
    def __init__(self, session):
        self.session = session

    def get_all(self) -> List[BackupVerification]:
        return list(self.session.scalars(select(BackupVerification)).all())

    def get_by_uuid(self, uuid: str) -> Optional[BackupVerification]:
        return self.session.get(BackupVerification, uuid)

    def get_by_history_uuid(self, history_uuid: str) -> List[BackupVerification]:
        stmt = select(BackupVerification).where(
            BackupVerification.backup_history_uuid == history_uuid
        )
        return list(self.session.scalars(stmt).all())
