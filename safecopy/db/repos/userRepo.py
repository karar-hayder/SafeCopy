from typing import Optional

from sqlalchemy import select

from safecopy.db.models import User
from safecopy.db.repos.baseRepo import BaseRepo


class UserRepo(BaseRepo):
    def __init__(self, session):
        super().__init__(session, User)

    def get_by_username(self, username: str) -> Optional[User]:
        stmt = select(User).where(User.username == username)
        return self.session.scalars(stmt).first()
