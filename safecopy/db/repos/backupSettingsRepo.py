from typing import List, Optional

from sqlalchemy import select

from safecopy.db.models import BackupSettings


class BackupSettingsRepo:
    def __init__(self, session):
        self.session = session

    def get_all(self) -> List[BackupSettings]:
        return list(self.session.scalars(select(BackupSettings)).all())

    def get_by_key(self, key: str) -> Optional[BackupSettings]:
        stmt = select(BackupSettings).where(BackupSettings.key == key)
        return self.session.scalars(stmt).first()

    def get_by_uuid(self, uuid: str) -> Optional[BackupSettings]:
        return self.session.get(BackupSettings, uuid)
