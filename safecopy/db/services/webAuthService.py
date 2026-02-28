from typing import Optional

from werkzeug.security import check_password_hash, generate_password_hash

from safecopy.db.models import WebAuth
from safecopy.db.repos.webAuthRepo import WebAuthRepo
from safecopy.db.services.baseService import BaseService
from safecopy.db.session import get_session


class WebAuthService(BaseService):
    def __init__(self):
        super().__init__(WebAuth, WebAuthRepo)

    def get_user_by_username(self, username: str) -> Optional[WebAuth]:
        with get_session() as session:
            repo = WebAuthRepo(session)
            return repo.get_by_username(username)

    def login(self, username: str, password: str) -> bool:
        with get_session() as session:
            repo = WebAuthRepo(session)
            user = repo.get_by_username(username)
            if user:
                password_check = check_password_hash(user.password, password)
                return password_check
            return False

    def register(self, username: str, password: str) -> bool:
        with get_session() as session:
            repo = WebAuthRepo(session)
            user = repo.get_by_username(username)
            if user:
                return False
            password_hash = generate_password_hash(password)
            user = WebAuth(username=username, password=password_hash)
            repo.add(user)
            return True

    def change_password(self, username: str, password: str) -> bool:
        with get_session() as session:
            repo = WebAuthRepo(session)
            user = repo.get_by_username(username)
            if user:
                password_hash = generate_password_hash(password)
                user.password = password_hash
                repo.update(user)
                return True
            return False
