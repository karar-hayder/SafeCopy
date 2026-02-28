from typing import List, Optional

from safecopy.db.models import EmailSettings
from safecopy.db.repos.emailSettingsRepo import EmailSettingsRepo
from safecopy.db.session import get_session


class EmailSettingsService:
    def create_settings(self, **kwargs) -> EmailSettings:
        with get_session() as session:
            settings = EmailSettings(**kwargs)
            session.add(settings)
            session.flush()
            return settings

    def get_all_settings(self) -> List[EmailSettings]:
        with get_session() as session:
            repo = EmailSettingsRepo(session)
            return repo.get_all()

    def get_settings(self, uuid: str) -> Optional[EmailSettings]:
        with get_session() as session:
            repo = EmailSettingsRepo(session)
            return repo.get_by_uuid(uuid)

    def update_settings(self, uuid: str, **kwargs) -> Optional[EmailSettings]:
        with get_session() as session:
            repo = EmailSettingsRepo(session)
            settings = repo.get_by_uuid(uuid)
            if settings:
                for key, value in kwargs.items():
                    if hasattr(settings, key):
                        setattr(settings, key, value)
                return settings
            return None

    def delete_settings(self, uuid: str) -> bool:
        with get_session() as session:
            repo = EmailSettingsRepo(session)
            settings = repo.get_by_uuid(uuid)
            if settings:
                session.delete(settings)
                return True
            return False
