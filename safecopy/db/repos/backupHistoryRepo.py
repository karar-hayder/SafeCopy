from typing import Optional

from sqlalchemy import select

from safecopy.db.models import BackupHistory
from safecopy.db.repos.baseRepo import BaseRepo


class BackupHistoryRepo(BaseRepo):
    def __init__(self, session):
        super().__init__(session, BackupHistory)

    def get_by_mapping_uuid(self, mapping_uuid: str) -> Optional[BackupHistory]:
        stmt = select(BackupHistory).where(BackupHistory.mapping_uuid == mapping_uuid)
        return self.session.scalars(stmt).first()

    def get_by_success(self, success: int) -> Optional[BackupHistory]:
        stmt = select(BackupHistory).where(BackupHistory.success == success)
        return self.session.scalars(stmt).first()
