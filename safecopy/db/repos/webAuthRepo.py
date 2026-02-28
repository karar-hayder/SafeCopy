from typing import Optional

from sqlalchemy import select

from safecopy.db.models import WebAuth
from safecopy.db.repos.baseRepo import BaseRepo


class WebAuthRepo(BaseRepo):
    def __init__(self, session):
        super().__init__(session, WebAuth)

    def get_by_username(self, username: str) -> Optional[WebAuth]:
        stmt = select(WebAuth).where(WebAuth.username == username)
        return self.session.scalars(stmt).first()
