from typing import Optional

from safecopy.db.models import BackupSettings
from safecopy.db.repos.backupSettingsRepo import BackupSettingsRepo
from safecopy.db.services.baseService import BaseService


class BackupSettingsService(BaseService):
    def __init__(self):
        super().__init__(BackupSettings, BackupSettingsRepo)

    def set_setting(self, key: str, value: str) -> BackupSettings:
        setting = self.get_one(key=key)
        if setting:
            setting.value = value
            self.update(setting.uuid, value=value)
        else:
            setting = self.create(key=key, value=value)
        return setting

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        setting = self.get_one(key=key)
        return setting.value if setting else default

    def delete_setting(self, key: str) -> bool:
        setting = self.get_one(key=key)
        if setting:
            return self.delete(setting.uuid)
        return False
