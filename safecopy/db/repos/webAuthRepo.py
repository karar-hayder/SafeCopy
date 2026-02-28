from typing import List, Optional

from sqlalchemy import select

from safecopy.db.models import WebAuth


class WebAuthRepo:
    def __init__(self, session):
        self.session = session

    def get_all(self) -> List[WebAuth]:
        return list(self.session.scalars(select(WebAuth)).all())

    def get_by_uuid(self, uuid: str) -> Optional[WebAuth]:
        return self.session.get(WebAuth, uuid)

    def get_by_username(self, username: str) -> Optional[WebAuth]:
        stmt = select(WebAuth).where(WebAuth.username == username)
        return self.session.scalars(stmt).first()
