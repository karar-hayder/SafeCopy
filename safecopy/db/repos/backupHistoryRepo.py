from typing import List, Optional

from sqlalchemy import select

from safecopy.db.models import BackupHistory


class BackupHistoryRepo:
    def __init__(self, session):
        self.session = session

    def get_all(self) -> List[BackupHistory]:
        return list(self.session.scalars(select(BackupHistory)).all())

    def get_by_uuid(self, uuid: str) -> Optional[BackupHistory]:
        return self.session.get(BackupHistory, uuid)

    def get_by_mapping_uuid(self, mapping_uuid: str) -> Optional[BackupHistory]:
        stmt = select(BackupHistory).where(BackupHistory.mapping_uuid == mapping_uuid)
        return self.session.scalars(stmt).first()

    def get_by_success(self, success: int) -> Optional[BackupHistory]:
        stmt = select(BackupHistory).where(BackupHistory.success == success)
        return self.session.scalars(stmt).first()
