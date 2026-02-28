from typing import List, Optional

from sqlalchemy import select

from safecopy.db.models import EmailSettings


class EmailSettingsRepo:
    def __init__(self, session):
        self.session = session

    def get_all(self) -> List[EmailSettings]:
        return list(self.session.scalars(select(EmailSettings)).all())

    def get_by_uuid(self, uuid: str) -> Optional[EmailSettings]:
        return self.session.get(EmailSettings, uuid)

    def get_enabled(self) -> List[EmailSettings]:
        stmt = select(EmailSettings).where(EmailSettings.enabled == 1)
        return list(self.session.scalars(stmt).all())
