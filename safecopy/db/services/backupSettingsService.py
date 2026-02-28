from typing import List, Optional

from safecopy.db.models import BackupSettings
from safecopy.db.repos.backupSettingsRepo import BackupSettingsRepo
from safecopy.db.session import get_session


class BackupSettingsService:
    def set_setting(self, key: str, value: str) -> BackupSettings:
        with get_session() as session:
            repo = BackupSettingsRepo(session)
            setting = repo.get_by_key(key)
            if setting:
                setting.value = value
            else:
                setting = BackupSettings(key=key, value=value)
                session.add(setting)
            session.flush()
            return setting

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        with get_session() as session:
            repo = BackupSettingsRepo(session)
            setting = repo.get_by_key(key)
            return setting.value if setting else default

    def get_all_settings(self) -> List[BackupSettings]:
        with get_session() as session:
            repo = BackupSettingsRepo(session)
            return repo.get_all()

    def delete_setting(self, key: str) -> bool:
        with get_session() as session:
            repo = BackupSettingsRepo(session)
            setting = repo.get_by_key(key)
            if setting:
                session.delete(setting)
                return True
            return False
