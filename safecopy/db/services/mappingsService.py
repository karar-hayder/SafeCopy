from typing import Optional

from safecopy.db.models import Mappings
from safecopy.db.repos.mappingsRepo import MappingsRepo
from safecopy.db.services.baseService import BaseService


class MappingsService(BaseService):
    def __init__(self):
        super().__init__(Mappings, MappingsRepo)

    def get_by_source_and_destination(
        self, source: str, destination: str
    ) -> Optional[Mappings]:
        self.logger.debug(
            "Get mapping by source and destination %s %s", source, destination
        )
        return self.get_one(source=source, destination=destination)
