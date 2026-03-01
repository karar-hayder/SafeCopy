from typing import Optional

from safecopy.db.dtos.mappingsDTOs import (
    MappingsCreateDTO,
    MappingsResponseDTO,
    MappingsUpdateDTO,
)
from safecopy.db.models import Mappings
from safecopy.db.repos.mappingsRepo import MappingsRepo
from safecopy.db.services.baseService import BaseService


class MappingsService(BaseService):
    def __init__(self):
        super().__init__(Mappings, MappingsRepo)
        self.dto_cls = {
            "create": MappingsCreateDTO,
            "update": MappingsUpdateDTO,
            "response": MappingsResponseDTO,
        }

    def get_by_source_and_destination(
        self, source: str, destination: str
    ) -> Optional[MappingsResponseDTO | Mappings]:
        return self.get_one(source=source, destination=destination)
