from typing import List, Optional, TypeVar

from sqlalchemy import asc, desc, select

T = TypeVar("T")


class BaseRepo:
    def __init__(self, session, model):
        self.session = session
        self.model = model

    def add(self, entity: T):
        self.session.add(entity)
        self.session.flush()
        return entity

    def update(self, entity: T):
        self.session.flush()
        return entity

    def delete(self, entity: T):
        self.session.delete(entity)
        self.session.flush()

    def get_by_uuid(self, uuid: str) -> T:
        return self.session.get(self.model, uuid)

    def get_all(
        self, order_by="-created_at", page=1, page_size=10, **filters
    ) -> List[T]:
        order_by = asc(order_by) if not order_by.startswith("-") else desc(order_by[1:])
        objs = None
        if filters:
            objs = self.session.scalars(
                select(self.model).filter_by(**filters).order_by(order_by)
            )
        else:
            objs = self.session.scalars(select(self.model).order_by(order_by))

        if page_size == 0:
            return objs
        return objs.limit(page_size).offset((page - 1) * page_size).all()

    def get_one(self, **filters) -> Optional[T]:
        return self.session.scalars(select(self.model).filter_by(**filters)).first()
