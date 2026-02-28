from typing import List, Optional

from sqlalchemy import select

from safecopy.db.models import BackupSchedules


class BackupSchedulesRepo:
    def __init__(self, session):
        self.session = session

    def get_all(self) -> List[BackupSchedules]:
        return list(self.session.scalars(select(BackupSchedules)).all())

    def get_by_uuid(self, uuid: str) -> Optional[BackupSchedules]:
        return self.session.get(BackupSchedules, uuid)

    def get_by_mapping_uuid(self, mapping_uuid: str) -> List[BackupSchedules]:
        stmt = select(BackupSchedules).where(
            BackupSchedules.mapping_uuid == mapping_uuid
        )
        return list(self.session.scalars(stmt).all())
