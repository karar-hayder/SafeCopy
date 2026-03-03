from logging import Logger, getLogger
from typing import Any, List, Optional, Type, TypeVar

from pydantic import BaseModel
from sqlalchemy.orm import DeclarativeBase, Session

from safecopy.db.repos.baseRepo import BaseRepo
from safecopy.db.session import get_session

ModelType = TypeVar("ModelType", bound=DeclarativeBase)
CreateDTOType = TypeVar("CreateDTOType", bound=BaseModel)
UpdateDTOType = TypeVar("UpdateDTOType", bound=BaseModel)
ResponseDTOType = TypeVar("ResponseDTOType", bound=BaseModel)


class BaseService:
    def __init__(self, model_cls: Type[ModelType], repo_cls: Type[BaseRepo]):
        self.model_cls = model_cls
        self.repo_cls = repo_cls
        self.logger: Logger = getLogger(
            f"safecopy.db.services.{self.__class__.__name__}"
        )
        self.dto_cls: dict[str, Any] = {
            "create": None,
            "update": None,
            "response": None,
        }

    def _get_object_str(self, obj: ModelType) -> str:
        return f"{obj.__class__.__name__} {obj.uuid}"

    def get_all(
        self, order_by="-created_at", page=1, page_size=10, **filters
    ) -> List[ResponseDTOType | ModelType]:
        with get_session() as session:
            repo = self._repo(session)
            objs = repo.get_all(order_by, page, page_size, **filters)
            self.logger.debug(
                "Retrieved all %s with filters %s and order by %s",
                self.model_cls.__name__,
                filters,
                order_by,
            )
            if self.dto_cls["response"]:
                return [
                    self.dto_cls["response"].model_validate(obj, from_attributes=True)
                    for obj in objs
                ]
            return list(objs)

    def get_one(self, **filters) -> Optional[ResponseDTOType | ModelType]:
        with get_session() as session:
            repo = self._repo(session)
            obj = repo.get_one(**filters)
            self.logger.debug(
                "Retrieved one %s with filters %s", self.model_cls.__name__, filters
            )
            if obj and self.dto_cls["response"]:
                return self.dto_cls["response"].model_validate(
                    obj, from_attributes=True
                )
            return obj

    def get_by_uuid(self, uuid: str) -> Optional[ResponseDTOType | ModelType]:
        with get_session() as session:
            repo = self._repo(session)
            obj = repo.get_by_uuid(uuid)
            self.logger.debug(
                "Retrieved %s with uuid %s", self.model_cls.__name__, uuid
            )
            if obj and self.dto_cls["response"]:
                return self.dto_cls["response"].model_validate(
                    obj, from_attributes=True
                )
            return obj

    def get_model_by_uuid(self, uuid: str) -> Optional[ModelType]:
        with get_session() as session:
            repo = self._repo(session)
            return repo.get_by_uuid(uuid)

    def create(self, dto: CreateDTOType) -> ModelType | ResponseDTOType:
        with get_session() as session:
            repo = self._repo(session)
            obj = self.model_cls(**dto.model_dump(mode="python"))
            obj = repo.add(obj)
            self.logger.info("Created %s", self._get_object_str(obj))
            if self.dto_cls["response"]:
                return self.dto_cls["response"].model_validate(
                    obj, from_attributes=True
                )
            return obj

    def update(
        self, uuid: str, dto: UpdateDTOType
    ) -> Optional[ResponseDTOType | ModelType]:
        with get_session() as session:
            repo = self._repo(session)
            obj = repo.get_by_uuid(uuid)
            if obj:
                for key, value in dto.model_dump(
                    mode="python", exclude_unset=True
                ).items():
                    if hasattr(obj, key):
                        setattr(obj, key, value)
                repo.update(obj)
                self.logger.info("Updated %s", self._get_object_str(obj))
                if self.dto_cls["response"]:
                    return self.dto_cls["response"].model_validate(
                        obj, from_attributes=True
                    )
                return obj
            self.logger.debug("Object %s not found", uuid)
        return None

    def delete(self, uuid: str) -> bool:
        with get_session() as session:
            repo = self._repo(session)
            obj = repo.get_by_uuid(uuid)
            if obj:
                repo.delete(obj)
                self.logger.info("Deleted %s", self._get_object_str(obj))
                return True
            self.logger.debug("Object %s not found", uuid)
        return False

    def _repo(self, session: Session):
        return self.repo_cls(session, self.model_cls)
