from typing import List, Optional

from safecopy.db.models import WebAuth
from safecopy.db.repos.webAuthRepo import WebAuthRepo
from safecopy.db.session import get_session


class WebAuthService:
    def create_user(self, **kwargs) -> WebAuth:
        with get_session() as session:
            user = WebAuth(**kwargs)
            session.add(user)
            session.flush()
            return user

    def get_all_users(self) -> List[WebAuth]:
        with get_session() as session:
            repo = WebAuthRepo(session)
            return repo.get_all()

    def get_user(self, uuid: str) -> Optional[WebAuth]:
        with get_session() as session:
            repo = WebAuthRepo(session)
            return repo.get_by_uuid(uuid)

    def get_user_by_username(self, username: str) -> Optional[WebAuth]:
        with get_session() as session:
            repo = WebAuthRepo(session)
            return repo.get_by_username(username)

    def update_user(self, uuid: str, **kwargs) -> Optional[WebAuth]:
        with get_session() as session:
            repo = WebAuthRepo(session)
            user = repo.get_by_uuid(uuid)
            if user:
                for key, value in kwargs.items():
                    if hasattr(user, key):
                        setattr(user, key, value)
                return user
            return None

    def delete_user(self, uuid: str) -> bool:
        with get_session() as session:
            repo = WebAuthRepo(session)
            user = repo.get_by_uuid(uuid)
            if user:
                session.delete(user)
                return True
            return False
