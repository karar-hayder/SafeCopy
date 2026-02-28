from typing import Optional

from sqlalchemy import select

from safecopy.db.models import BackupSettings
from safecopy.db.repos.baseRepo import BaseRepo


class BackupSettingsRepo(BaseRepo):
    def __init__(self, session):
        super().__init__(session, BackupSettings)

    def get_by_key(self, key: str) -> Optional[BackupSettings]:
        stmt = select(BackupSettings).where(BackupSettings.key == key)
        return self.session.scalars(stmt).first()
