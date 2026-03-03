from typing import Optional

from werkzeug.security import check_password_hash, generate_password_hash

from safecopy.db.dtos.userDTOs import (
    UserCreateDTO,
    UserLoginDTO,
    UserResponseDTO,
    UserUpdateDTO,
)
from safecopy.db.enums import UserRole
from safecopy.db.models import User
from safecopy.db.repos.userRepo import UserRepo
from safecopy.db.services.baseService import BaseService
from safecopy.db.session import get_session


class UserService(BaseService):
    def __init__(self):
        super().__init__(User, UserRepo)
        self.dto_cls = {
            "create": UserCreateDTO,
            "update": UserUpdateDTO,
            "response": UserResponseDTO,
            "login": UserLoginDTO,
        }

    def get_user_by_username(self, username: str) -> Optional[UserResponseDTO]:
        with get_session() as session:
            repo = self._repo(session)
            obj = repo.get_by_username(username)
            if obj and self.dto_cls["response"]:
                return self.dto_cls["response"].model_validate(
                    obj, from_attributes=True
                )
            return None

    def get_user_model_by_username(self, username: str) -> Optional[User]:
        with get_session() as session:
            repo = self._repo(session)
            return repo.get_by_username(username)

    def login(self, dto: UserLoginDTO) -> bool:
        with get_session() as session:
            repo = self._repo(session)
            user = repo.get_by_username(dto.username)
            if user:
                password_check = check_password_hash(user.password, dto.password)
                return password_check
            return False

    def register(self, dto: UserCreateDTO) -> bool:
        with get_session() as session:
            repo = self._repo(session)
            user = repo.get_by_username(dto.username)
            if user:
                return False
            password_hash = generate_password_hash(dto.password)
            user = User(
                username=dto.username,
                password=password_hash,
                role=dto.role,
                settings=dto.settings,
            )
            repo.add(user)
            return True

    def change_password(self, dto: UserUpdateDTO) -> bool:
        with get_session() as session:
            repo = self._repo(session)
            user = repo.get_by_username(dto.username)
            if user:
                password_hash = generate_password_hash(dto.password)
                user.password = password_hash
                repo.update(user)
                return True
            return False

    def ensure_admin_exists(self):
        with get_session() as session:
            repo = self._repo(session)
            # Check if any admin exists instead of just count == 0
            admin = repo.get_one(role=UserRole.ADMIN)
            if not admin:
                self.register(
                    UserCreateDTO(
                        username="admin", password="adminpassword", role=UserRole.ADMIN
                    )
                )
