from typing import List, Optional

from safecopy.db.models import Mappings
from safecopy.db.repos.mappingsRepo import MappingsRepo
from safecopy.db.session import get_session


class MappingsService:
    def create_mapping(self, **kwargs) -> Mappings:
        with get_session() as session:
            mapping = Mappings(**kwargs)
            session.add(mapping)
            session.flush()
            return mapping

    def get_all_mappings(self) -> List[Mappings]:
        with get_session() as session:
            repo = MappingsRepo(session)
            return repo.get_all()

    def get_mapping(self, uuid: str) -> Optional[Mappings]:
        with get_session() as session:
            repo = MappingsRepo(session)
            return repo.get_by_uuid(uuid)

    def update_mapping(self, uuid: str, **kwargs) -> Optional[Mappings]:
        with get_session() as session:
            repo = MappingsRepo(session)
            mapping = repo.get_by_uuid(uuid)
            if mapping:
                for key, value in kwargs.items():
                    if hasattr(mapping, key):
                        setattr(mapping, key, value)
                return mapping
            return None

    def delete_mapping(self, uuid: str) -> bool:
        with get_session() as session:
            repo = MappingsRepo(session)
            mapping = repo.get_by_uuid(uuid)
            if mapping:
                session.delete(mapping)
                return True
            return False
