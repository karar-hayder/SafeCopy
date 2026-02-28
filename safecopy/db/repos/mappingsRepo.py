from typing import List, Optional

from sqlalchemy import select

from safecopy.db.models import Mappings


class MappingsRepo:
    def __init__(self, session):
        self.session = session

    def get_all(self) -> List[Mappings]:
        return list(self.session.scalars(select(Mappings)).all())

    def get_by_uuid(self, uuid: str) -> Optional[Mappings]:
        return self.session.get(Mappings, uuid)

    def get_by_source_and_destination(
        self, source: str, destination: str
    ) -> Optional[Mappings]:
        stmt = select(Mappings).where(
            Mappings.source == source, Mappings.destination == destination
        )
        return self.session.scalars(stmt).first()
