from typing import List

from sqlalchemy import select

from safecopy.db.models import BackupVerification
from safecopy.db.repos.baseRepo import BaseRepo


class BackupVerificationRepo(BaseRepo):
    def __init__(self, session, model=BackupVerification):
        super().__init__(session, model)

    def get_by_history_uuid(self, history_uuid: str) -> List[BackupVerification]:
        stmt = select(BackupVerification).where(
            BackupVerification.backup_history_uuid == history_uuid
        )
        return list(self.session.scalars(stmt).all())
