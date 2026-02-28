from logging import DEBUG, FileHandler, Logger, StreamHandler, getLogger
from typing import List, Optional, Type, TypeVar

from sqlalchemy.orm import Session

from safecopy.db.repos.baseRepo import BaseRepo
from safecopy.db.session import get_session

T = TypeVar("T")


class BaseService:
    def __init__(self, model_cls: Type[T], repo_cls: Type[BaseRepo]):
        self.model_cls = model_cls
        self.repo_cls = repo_cls
        self.logger = self._set_logger(self.__class__.__name__)

    def _set_logger(self, name: str) -> Logger:
        logger = getLogger(f"safecopy.db.services.{name}")
        logger.setLevel(DEBUG)
        logger.addHandler(StreamHandler())
        logger.propagate = False
        logger.addHandler(FileHandler("safecopy.db.services.log"))
        return logger

    def _get_object_str(self, obj: T) -> str:
        return f"{obj.__class__.__name__} {obj.uuid}"

    def create(self, **kwargs) -> T:
        with get_session() as session:
            repo = self._repo(session)
            obj = self.model_cls(**kwargs)
            obj = repo.add(obj)
            self.logger.info("Created %s", self._get_object_str(obj))
            return obj

    def get_all(
        self, order_by="-created_at", page=1, page_size=10, **filters
    ) -> List[T]:
        with get_session() as session:
            repo = self._repo(session)
            self.logger.debug(
                "Retrieved all %s with filters %s and order by %s",
                self.model_cls.__name__,
                filters,
                order_by,
            )
            if filters:
                return list(repo.get_all(order_by, page, page_size, **filters))
            return list(repo.get_all(order_by, page, page_size))

    def get_one(self, **filters) -> Optional[T]:
        with get_session() as session:
            repo = self._repo(session)
            self.logger.debug(
                "Retrieved one %s with filters %s", self.model_cls.__name__, filters
            )
            return repo.get_one(**filters)

    def get_by_uuid(self, uuid: str) -> Optional[T]:
        with get_session() as session:
            repo = self._repo(session)
            self.logger.debug(
                "Retrieved %s with uuid %s", self.model_cls.__name__, uuid
            )
            return repo.get_by_uuid(uuid)

    def update(self, uuid: str, **kwargs) -> Optional[T]:
        with get_session() as session:
            repo = self._repo(session)
            obj = repo.get_by_uuid(uuid)
            if obj:
                for key, value in kwargs.items():
                    if hasattr(obj, key):
                        setattr(obj, key, value)
                repo.update(obj)
                self.logger.info("Updated %s", self._get_object_str(obj))
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
