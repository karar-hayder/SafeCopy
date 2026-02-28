from typing import List

from sqlalchemy import select

from safecopy.db.models import EmailSettings
from safecopy.db.repos.baseRepo import BaseRepo


class EmailSettingsRepo(BaseRepo):
    def __init__(self, session):
        super().__init__(session, EmailSettings)

    def get_enabled(self) -> List[EmailSettings]:
        stmt = select(EmailSettings).where(EmailSettings.enabled == 1)
        return list(self.session.scalars(stmt).all())
