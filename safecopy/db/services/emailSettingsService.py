from typing import List

from safecopy.db.models import EmailSettings
from safecopy.db.repos.emailSettingsRepo import EmailSettingsRepo
from safecopy.db.services.baseService import BaseService


class EmailSettingsService(BaseService):
    def __init__(self):
        super().__init__(EmailSettings, EmailSettingsRepo)

    def get_enabled(self) -> List[EmailSettings]:
        return self.get_all(enabled=1)
